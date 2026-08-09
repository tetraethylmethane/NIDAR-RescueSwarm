"""ArduPilot parameter tests — the failsafes must be real, not merely present.

Every check here corresponds to a way a parameter file can look complete and
still leave the aircraft unprotected: an action set to "report and do nothing",
an altitude in the wrong unit, arming checks disabled during debugging and never
re-enabled.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "firmware", "ardupilot-params"))
from params import (  # noqa: E402
    BASE, PACK_MAH, REQUIRED_FAILSAFES, for_drone, to_parm, validate,
)


def test_default_set_is_valid():
    assert validate(for_drone(1)) == []


@pytest.mark.parametrize("drone_id", [1, 2, 3])
def test_sysid_is_per_drone(drone_id):
    """mavlink-router and Fleet both key on the source system id. Three
    aircraft sharing SYSID 1 would appear as one drone."""
    assert for_drone(drone_id)["SYSID_THISMAV"] == drone_id


def test_rtl_altitudes_are_staggered():
    alts = [for_drone(i)["RTL_ALT"] for i in (1, 2, 3)]
    assert alts == [2500, 3000, 3500]         # centimetres
    assert len(set(alts)) == 3, "three aircraft returning at once, coplanar"


def test_rtl_descents_are_sequenced_not_just_separated():
    """RTL_ALT separates the cruise home; it does nothing at the pad.

    All three aircraft share a pack design and fly missions of near-equal
    length, so they reach BATT_LOW_MAH within seconds of each other and turn
    for home together. The pad is 3.66 m and the slots are 1.22 m apart, which
    is a parking arrangement, not a landing one. RTL_LOIT_TIME holds each
    aircraft at RTL_ALT so only one descends at a time.
    """
    loiters = [for_drone(i)["RTL_LOIT_TIME"] for i in (1, 2, 3)]
    assert loiters == [0, 20000, 40000]                  # milliseconds
    assert len(set(loiters)) == 3, "coincident descents onto a 3.66 m pad"
    assert loiters[0] == 0, "the first aircraft home should not wait"


def test_the_loiter_stagger_is_affordable_from_the_reserve():
    """A sequencing fix that eats the reserve would trade one failure for another."""
    HOVER_W, PACK_WH = 913.0, 292.0
    worst_wait_s = max(for_drone(i)["RTL_LOIT_TIME"] for i in (1, 2, 3)) / 1000.0
    spent_wh = HOVER_W * worst_wait_s / 3600.0
    reserve_wh = PACK_WH * (BASE["BATT_LOW_MAH"] / PACK_MAH)
    assert spent_wh < reserve_wh / 3, (
        f"last aircraft waits {worst_wait_s:.0f} s = {spent_wh:.1f} Wh against "
        f"a {reserve_wh:.1f} Wh reserve — too much of the margin goes to queuing")


def test_rtl_alt_is_centimetres_and_the_validator_knows():
    """RTL_ALT is in cm. Writing 25 means 25 cm and the aircraft returns home
    at ankle height. This is the classic ArduPilot unit trap."""
    p = for_drone(1)
    assert p["RTL_ALT"] == 2500
    p["RTL_ALT"] = 25
    problems = validate(p)
    assert any("CENTIMETRES" in s for s in problems)


def test_battery_thresholds_match_the_pack():
    p = for_drone(1)
    assert p["BATT_CAPACITY"] == PACK_MAH == 13500
    assert p["BATT_LOW_MAH"] == pytest.approx(2700)    # land with 20 %
    assert p["BATT_LOW_VOLT"] == pytest.approx(20.4)   # 6S x 3.40 V
    assert p["BATT_CRT_VOLT"] < p["BATT_LOW_VOLT"]
    assert p["BATT_FS_LOW_ACT"] == 2                   # RTL
    assert p["BATT_FS_CRT_ACT"] == 1                   # Land


def test_an_rc_channel_maps_to_rtl_so_abort_survives_a_dead_companion():
    """Constraint 3 of the abort design: the safety receiver must be able to
    recover the aircraft with no software of ours in the path."""
    p = for_drone(1)
    assert any(p.get(f"RC{n}_OPTION") == 4 for n in range(5, 17))
    for n in range(5, 17):
        p.pop(f"RC{n}_OPTION", None)
    assert any("companion being alive" in s for s in validate(p))


@pytest.mark.parametrize("key,bad,fragment", [
    ("ARMING_CHECK", 0, "pre-arm"),
    ("FENCE_ENABLE", 0, "FENCE_ENABLE"),
    ("FENCE_ACTION", 0, "does nothing"),
    ("BATT_FS_LOW_ACT", 0, "no action on low battery"),
    ("FS_GCS_ENABLE", 0, "FS_GCS_ENABLE"),
])
def test_validator_catches_disabled_failsafes(key, bad, fragment):
    """Each of these looks like a normal parameter and silently removes a
    failsafe SYS-11 requires."""
    p = for_drone(1)
    p[key] = bad
    problems = validate(p)
    assert any(fragment in s for s in problems), f"{key}={bad} not caught"


def test_validator_catches_a_missing_failsafe():
    for key in REQUIRED_FAILSAFES:
        p = for_drone(1)
        p.pop(key, None)
        assert any(key in s for s in validate(p)), f"{key} removal not caught"


def test_fence_altitude_is_above_the_search_altitude():
    p = for_drone(1)
    assert p["FENCE_ALT_MAX"] > 60
    p["FENCE_ALT_MAX"] = 40                # below a 40 m search -> instant RTL
    assert any("search altitude" in s for s in validate(p))


def test_gcs_timeout_matches_the_architecture():
    """10 s of mesh loss continues the bundle; 60 s returns home. A short GCS
    timeout would abort a mission that is behaving correctly."""
    assert BASE["FS_GCS_TIMEOUT"] == 60


def test_parm_format_is_loadable():
    text = to_parm(for_drone(2))
    lines = [ln for ln in text.splitlines() if ln]
    assert all("," in ln for ln in lines)
    assert lines == sorted(lines), "Mission Planner diffs are easier sorted"
    d = {k: float(v) for k, v in (ln.split(",") for ln in lines)}
    assert d["SYSID_THISMAV"] == 2
    assert d["RTL_ALT"] == 3000
    assert "e+" not in text and "e-" not in text, "no scientific notation"


def test_capacity_thresholds_are_ordered():
    p = for_drone(1)
    assert p["BATT_CRT_MAH"] < p["BATT_LOW_MAH"] < p["BATT_CAPACITY"]
