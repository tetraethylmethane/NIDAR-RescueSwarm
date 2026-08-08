"""The battery failsafe fired at 53 % SoC. These stop it coming back.

BATT_FS_VOLTSRC=1 asks ArduPilot to reconstruct resting voltage as
`measured + current * BATT_RESISTANCE`. BATT_RESISTANCE was never set, so it
defaulted to 0, the reconstruction was a no-op, and BATT_LOW_VOLT -- read off a
RESTING discharge curve -- was compared against a LOADED voltage.

    BATT_LOW_VOLT (RTL)              fired at ~53 % SoC, intended 20 %
    BATT_CRT_VOLT (land immediately) fired at ~30 % SoC, intended 10 %

An RTL at 53 % aborts the search mid-mission and destroys the 2.0x endurance
reserve the whole pack sizing rests on. It shipped in the committed .parm files
and was found by reading the parameters against the pack model, not by any test.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "firmware", "ardupilot-params"))
sys.path.insert(0, os.path.join(ROOT, "tools", "sizing-model"))

import params as P  # noqa: E402
from battery_pack import (  # noqa: E402
    S, loaded_voltage, pack_ocv, pack_resistance, soc_at_loaded_voltage,
)

I_HOVER = 913.0 / (S * 3.6)


# ------------------------------------------------------- the physics itself
def test_the_original_thresholds_really_did_fire_early():
    """Not a regression test -- a record that the defect was real.

    If this stops holding, the pack model changed and the finding needs
    revisiting rather than quietly disappearing.
    """
    soc_low = soc_at_loaded_voltage(20.4, I_HOVER)
    soc_crt = soc_at_loaded_voltage(19.2, I_HOVER)
    assert soc_low > 0.45, f"BATT_LOW_VOLT=20.4 fired at {soc_low:.0%}, expected ~53%"
    assert soc_crt > 0.25, f"BATT_CRT_VOLT=19.2 fired at {soc_crt:.0%}, expected ~30%"


def test_sag_compensation_recovers_the_intended_trip_point():
    """With BATT_RESISTANCE set, ArduPilot's reconstruction should land back on
    the resting curve -- which is the whole point of Option A."""
    soc = 0.20
    r = pack_resistance(0.50, 25.0)
    measured = loaded_voltage(soc, I_HOVER)
    reconstructed = measured + I_HOVER * r      # what ArduPilot computes
    resting = pack_ocv(soc)
    assert abs(reconstructed - resting) < 0.35, (
        f"reconstruction {reconstructed:.2f} V vs true resting {resting:.2f} V"
    )


def test_pack_resistance_is_in_a_physically_sane_band():
    r = pack_resistance(0.50, 25.0)
    assert 0.02 < r < 0.08, f"{r} ohm is not plausible for a 6S3P 21700 pack"


def test_resistance_rises_as_the_pack_empties_and_cools():
    """Both matter: the failsafe lives at low SoC, and the competition is in
    January."""
    assert pack_resistance(0.20, 25.0) > pack_resistance(0.50, 25.0)
    assert pack_resistance(0.20, 12.0) > pack_resistance(0.20, 25.0)


# -------------------------------------------------------- the shipped params
def test_the_shipped_parameters_are_now_consistent():
    for sysid in (1, 2, 3):
        p = P.for_drone(sysid) if hasattr(P, "for_drone") else dict(P.BASE)
        assert P.validate(p) == [], f"drone {sysid}: {P.validate(p)}"


def test_validator_catches_voltsrc_without_resistance():
    """The exact defect. A guard that cannot fail is not a guard."""
    bad = dict(P.BASE)
    bad["BATT_RESISTANCE"] = 0
    problems = P.validate(bad)
    assert any("BATT_RESISTANCE" in x for x in problems), problems


def test_validator_catches_the_correction_applied_twice():
    """Setting the resistance AND lowering the threshold onto the loaded curve
    pushes the failsafe dangerously late -- the opposite mistake."""
    bad = dict(P.BASE)
    bad["BATT_LOW_VOLT"] = 18.48        # the Option B value, wrongly combined
    problems = P.validate(bad)
    assert any("twice" in x or "too late" in x for x in problems), problems


def test_validator_catches_a_weakened_capacity_backstop():
    """Coulomb counting is the one failsafe independent of resistance, sag and
    temperature. It must not be weakened to paper over a voltage threshold."""
    bad = dict(P.BASE)
    bad["BATT_LOW_MAH"] = 500
    problems = P.validate(bad)
    assert any("BATT_LOW_MAH" in x for x in problems), problems


@pytest.mark.parametrize("key,expected", [
    ("BATT_RESISTANCE", 0.040),
    ("BATT_LOW_TIMER", 10),
    ("BATT_FS_VOLTSRC", 1),
    ("BATT_LOW_VOLT", 20.4),      # unchanged: correct once compensation works
    ("BATT_CRT_VOLT", 19.2),
])
def test_option_a_is_what_shipped(key, expected):
    assert P.BASE[key] == pytest.approx(expected)
