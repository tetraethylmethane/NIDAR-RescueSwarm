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
    BASE, PACK_MAH, REQUIRED_FAILSAFES, WORST_MEASURED_DESCENT_S, for_drone,
    to_parm, validate,
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
    assert loiters == [0, 60000, 120000]                 # milliseconds
    assert len(set(loiters)) == 3, "coincident descents onto a 3.66 m pad"
    assert loiters[0] == 0, "the first aircraft home should not wait"


def test_the_stagger_covers_the_measured_descent():
    """The value that matters, asserted against the thing that sets it.

    This test exists because the bare-number assertion above did not catch a
    revert. RTL_LOIT_TIME was corrected to 0/60/120 s by hand in the .parm
    files after a SITL re-fly measured a 3.10 m approach at 0/20/40 s, but
    params.py -- the generator -- was never updated, so the next regeneration
    silently put 0/20/40 back and the tests stayed green on it.

    A stagger shorter than the descent it has to cover means the next aircraft
    enters the corridor before the one below it has landed, which is exactly
    the geometry that produced the breach. Assert the relationship, not the
    number.
    """
    step_s = (for_drone(2)["RTL_LOIT_TIME"] - for_drone(1)["RTL_LOIT_TIME"]) / 1000.0
    assert step_s >= WORST_MEASURED_DESCENT_S, (
        f"each aircraft waits {step_s:.0f} s for a descent measured at "
        f"{WORST_MEASURED_DESCENT_S:.0f} s — the queue overlaps by "
        f"{WORST_MEASURED_DESCENT_S - step_s:.0f} s over a 3.66 m pad")


def test_the_loiter_stagger_is_affordable_from_the_reserve():
    """A sequencing fix that eats the reserve would trade one failure for another.

    The bound here is deliberately weaker than it was. At 0/20/40 s this
    asserted spend < reserve/3, which the collision-safe 0/60/120 s does not
    meet: the last aircraft now holds 120 s = 30.4 Wh of a 58.4 Wh reserve,
    52 % of it, where 40 s spent 17 %.

    That is a real loss of margin and it is recorded rather than hidden. What
    the reserve must still guarantee is a LANDING, so that is what is asserted:
    the worst-placed aircraft must be able to hold its queue slot and still
    fly its own descent, with the remainder kept at twice the descent cost so
    a single unmodelled event does not consume it. Buying the margin back means
    raising LAND_SPEED to shorten the descent, not shortening the queue -- see
    the note in params.for_drone.

    IT CURRENTLY PASSES BY 1.08 Wh OF 58.40, which is 1.9 %. That is not a
    comfortable margin and it is not meant to read as one: the queue is very
    nearly as long as the reserve can pay for, and a stagger of 61 s would fail
    this. If you are here because this test just went red, the answer is almost
    certainly LAND_SPEED (HANDOFF.md section 4.8), not a larger threshold.
    """
    HOVER_W, PACK_WH = 913.0, 292.0
    worst_wait_s = max(for_drone(i)["RTL_LOIT_TIME"] for i in (1, 2, 3)) / 1000.0
    spent_wh = HOVER_W * worst_wait_s / 3600.0
    descent_wh = HOVER_W * WORST_MEASURED_DESCENT_S / 3600.0
    reserve_wh = PACK_WH * (BASE["BATT_LOW_MAH"] / PACK_MAH)
    headroom_wh = reserve_wh - spent_wh - 2 * descent_wh
    assert headroom_wh > 0, (
        f"last aircraft waits {worst_wait_s:.0f} s = {spent_wh:.1f} Wh, then "
        f"needs {descent_wh:.1f} Wh to land, against a {reserve_wh:.1f} Wh "
        f"reserve — over by {-headroom_wh:.1f} Wh. The queue no longer leaves "
        f"room to come down; shorten the DESCENT (LAND_SPEED), not the queue")


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
