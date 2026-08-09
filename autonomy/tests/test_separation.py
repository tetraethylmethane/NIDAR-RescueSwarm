"""Deconfliction and recovery: the two things a simulation run showed going wrong.

Both symptoms reported from the sim video -- aircraft passing close, and no
return-to-pad on low battery -- turn out to meet at the pad. Three aircraft on
one pack design flying one mission of equal length reach the low-battery
threshold within seconds of each other, and every one of them then flies to a
3.66 m pad. Making the failsafe work without sequencing the arrivals makes the
first symptom worse, so these are tested together.
"""
from __future__ import annotations

import os
import sys

import pytest

# Match the other tests in this directory: CI runs pytest with
# working-directory: autonomy, so the repo root is NOT on the path and
# `from autonomy.coverage_planner import ...` does not resolve there.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage_planner import mission as mis  # noqa: E402
from coverage_planner import separation as sep  # noqa: E402
from coverage_planner.geo import Frame  # noqa: E402
from coverage_planner.plan import (  # noqa: E402
    AIRFRAME_FOOTPRINT_M, DECK_CLEARANCE_M, PAD_SIDE_M, pad_slots, plan_mission,
)

BOUNDARY = [(13.0000, 80.0000), (13.0000, 80.00553),
            (13.00540, 80.00553), (13.00540, 80.0000)]
HOME = (12.99950, 80.00276)


@pytest.fixture(scope="module")
def frame():
    return Frame.from_points(BOUNDARY)


@pytest.fixture(scope="module")
def plan():
    return plan_mission(BOUNDARY, HOME, n_drones=3)


# ----------------------------------------------------------------- pad slots
def test_pad_slots_are_distinct_points(frame):
    slots = pad_slots(HOME, 3, frame)
    assert len({(round(a, 9), round(b, 9)) for a, b in slots}) == 3


def test_pad_slots_fit_inside_the_pad(frame):
    """Rule 8.10: take off and land inside 12 ft x 12 ft."""
    slots = pad_slots(HOME, 3, frame)
    for lat, lon in slots:
        x, y = frame.to_xy(lat, lon)
        hx, hy = frame.to_xy(*HOME)
        # slot centre plus half an airframe must stay inside the pad
        assert abs(x - hx) + AIRFRAME_FOOTPRINT_M / 2 <= PAD_SIDE_M / 2 + 1e-9
        assert abs(y - hy) + AIRFRAME_FOOTPRINT_M / 2 <= PAD_SIDE_M / 2 + 1e-9


def test_pad_slots_refuse_to_overlap_airframes(frame):
    """Four 1046 mm aircraft do not fit in a row on 3.66 m. Say so, loudly."""
    with pytest.raises(ValueError, match="do not fit"):
        pad_slots(HOME, 4, frame)


def test_each_drone_gets_its_own_slot_as_home(plan):
    """The regression: a single shared `home` sent every RTL to one point."""
    homes = [d.items[0] for d in plan.drones]
    assert len({(round(h.lat, 9), round(h.lon, 9)) for h in homes}) == 3
    for d in plan.drones:
        assert (d.items[0].lat, d.items[0].lon) == pytest.approx(d.pad_slot)


# ---------------------------------------------------------- transit corridor
def test_ingress_and_egress_are_flown_at_transit_altitude(plan):
    """The defect: transit altitude was applied to NAV_TAKEOFF and nowhere else.

    The aircraft climbed to 25 m over the pad and then flew straight at the
    40 m search deck, crossing other strips on the diagonal. There must now be
    a real waypoint at transit altitude on the way out and on the way back.
    """
    for d in plan.drones:
        wps = [i for i in d.items if i.command == mis.NAV_WAYPOINT and i.seq > 0]
        at_transit = [w for w in wps if w.alt == pytest.approx(d.transit_alt_m)]
        assert len(at_transit) >= 2, (
            f"drone {d.drone_id} has {len(at_transit)} waypoints at its "
            f"{d.transit_alt_m:.0f} m transit altitude; ingress and egress "
            f"both need one or the stagger is not flown")
        # first and last positional waypoints bracket the sweep
        assert wps[0].alt == pytest.approx(d.transit_alt_m)
        assert wps[-1].alt == pytest.approx(d.transit_alt_m)


def test_search_altitude_is_common_but_transit_is_not(plan):
    """Uniform GSD during the sweep; separated where they leave their strips."""
    assert len({d.altitude_m for d in plan.drones}) == 1
    assert len({d.transit_alt_m for d in plan.drones}) == len(plan.drones)


def test_transit_bands_clear_the_search_deck(plan):
    """Every transit altitude must sit below the common search altitude."""
    search = plan.drones[0].altitude_m
    for d in plan.drones:
        assert d.transit_alt_m < search


# -------------------------------------------------------------- separation
def test_flight_paths_stay_apart_away_from_the_pad(plan, frame):
    conflicts = sep.min_separation(plan.drones, frame)
    worst = min(c.distance_m for c in conflicts)
    assert worst >= 5.0, sep.report(plan.drones, frame)


def test_the_pad_is_the_tight_spot_and_needs_sequencing(plan, frame):
    """Documents WHY slot separation alone is not the fix.

    If this ever passes with a comfortable margin, the pad has grown or the
    aircraft has shrunk, and the RTL_LOIT_TIME stagger could be revisited.
    Until then it is load-bearing.
    """
    conflicts = sep.min_separation(plan.drones, frame, ignore_pad_radius_m=0.0)
    worst = min(c.distance_m for c in conflicts)
    assert worst < AIRFRAME_FOOTPRINT_M * 2, (
        "paths over the pad are further apart than expected — if the pad "
        "geometry changed, re-check whether descents still need sequencing")


def test_segment_distance_against_hand_computed_cases():
    """The geometry kernel, on cases with obvious answers."""
    d, _, _ = sep._seg_seg_distance((0, 0, 0), (10, 0, 0), (0, 5, 0), (10, 5, 0))
    assert d == pytest.approx(5.0)                       # parallel, 5 m apart
    d, _, _ = sep._seg_seg_distance((0, 0, 0), (10, 0, 0), (5, -5, 3), (5, 5, 3))
    assert d == pytest.approx(3.0)                       # crossing, 3 m of alt
    d, _, _ = sep._seg_seg_distance((0, 0, 0), (1, 0, 0), (9, 0, 0), (10, 0, 0))
    assert d == pytest.approx(8.0)                       # collinear, disjoint
    d, _, _ = sep._seg_seg_distance((0, 0, 0), (0, 0, 0), (3, 4, 0), (3, 4, 0))
    assert d == pytest.approx(5.0)                       # both degenerate


def test_a_shared_altitude_across_crossing_paths_is_caught(frame):
    """Falsify the checker: if it cannot see a real conflict it proves nothing.

    This used to build the conflict with plan_mission(transit_alt_m=40), which
    plan_mission now refuses -- so the synthetic conflict is built directly.
    That is the better test anyway: it exercises the checker rather than the
    planner, and it cannot be silently defused by a change to planner defaults.
    """
    class FakePlan:
        def __init__(self, did, items, slot):
            self.drone_id, self.items, self.pad_slot = did, items, slot

    def leg(x0, y0, x1, y1, alt):
        a = frame.to_latlon(x0, y0)
        b = frame.to_latlon(x1, y1)
        return [mis.Item(0, mis.NAV_WAYPOINT, lat=a[0], lon=a[1], alt=alt),
                mis.Item(1, mis.NAV_WAYPOINT, lat=b[0], lon=b[1], alt=alt)]

    far = frame.to_latlon(9000.0, 9000.0)     # pads nowhere near the crossing
    plans = [FakePlan(1, leg(-100, 0, 100, 0, 40.0), far),
             FakePlan(2, leg(0, -100, 0, 100, 40.0), far)]
    conflicts = sep.min_separation(plans, frame)
    assert conflicts, "no pairs evaluated"
    assert min(c.distance_m for c in conflicts) < 1.0, (
        "two paths crossing at the same altitude must register as a conflict; "
        "the checker missed it")


# --------------------------------------------------- strategy, not just safety
def test_every_sweep_finishes_near_the_pad(plan, frame):
    """The sweep ends at the aircraft's lowest state of charge.

    This was keyed on the drone index -- `start_far_side=bool(i % 2)` -- which
    is arbitrary, and left drones 1 and 3 finishing 516 m and 540 m from home
    while drone 2 finished at 116 m. Two of three aircraft were as far away as
    they would ever be at exactly the wrong moment.
    """
    import math
    for d in plan.drones:
        slot = frame.to_xy(*d.pad_slot)
        end = frame.to_xy(*d.lines[-1][1])
        start = frame.to_xy(*d.lines[0][0])
        d_end, d_start = math.dist(slot, end), math.dist(slot, start)
        assert d_end <= d_start, (
            f"drone {d.drone_id} finishes {d_end:.0f} m from the pad having "
            f"started {d_start:.0f} m away — it is running the sweep backwards")


def test_reordering_the_sweep_does_not_lengthen_it(plan, frame):
    """Finishing near home must be free. If it costs distance, it is a trade."""
    lens = {d.drone_id: d.path_m for d in plan.drones}
    assert max(lens.values()) - min(lens.values()) < 1.0, lens


def test_sweep_stays_continuous_after_reordering(plan, frame):
    """Each transect must begin where the previous one ended.

    Reversing every segment flips both ends and preserves this; reversing only
    some of them would leave the aircraft flying the length of the strip
    between transects, and the path length test above would not catch it
    because all three drones would be equally wrong.
    """
    import math
    for d in plan.drones:
        for k in range(len(d.lines) - 1):
            gap = math.dist(frame.to_xy(*d.lines[k][1]),
                            frame.to_xy(*d.lines[k + 1][0]))
            assert gap < 60.0, (
                f"drone {d.drone_id} flies {gap:.0f} m between transects "
                f"{k} and {k+1}; the sweep is not a boustrophedon")


def test_launches_are_sequenced(plan):
    """Three aircraft leaving 1.22 m slots at once measured 1.3 m apart in SITL."""
    delays = []
    for d in plan.drones:
        nd = [i for i in d.items if i.command == mis.NAV_DELAY]
        delays.append(nd[0].p1 if nd else 0.0)
    assert delays == sorted(delays) and len(set(delays)) == len(delays), delays
    assert delays[0] == 0.0, "the first aircraft should not wait"
    # A NAV_DELAY must come BEFORE the takeoff or it delays nothing.
    for d in plan.drones:
        cmds = [i.command for i in d.items]
        if mis.NAV_DELAY in cmds:
            assert cmds.index(mis.NAV_DELAY) < cmds.index(mis.NAV_TAKEOFF)


def test_transit_band_keeps_clear_of_the_search_deck():
    """The stratification is the argument; this is the argument's premise."""
    with pytest.raises(ValueError, match="clearance"):
        plan_mission(BOUNDARY, HOME, n_drones=3,
                     transit_alt_m=25.0, alt_stagger_m=5.0, altitude_m=40.0)


def test_the_shipped_defaults_satisfy_the_clearance(plan):
    top = max(d.transit_alt_m for d in plan.drones)
    assert plan.drones[0].altitude_m - top >= DECK_CLEARANCE_M
