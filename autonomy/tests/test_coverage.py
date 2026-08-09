"""Coverage planner tests, written against the polygons that break planners.

A 10 ha rectangle is the easy case and proves almost nothing. These cover the
shapes an organiser might actually hand over during a 5-minute window: long and
thin, rotated off-axis, concave, and a triangle where equal-area strips are
nowhere near equal-width.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage_planner import boustrophedon as bou  # noqa: E402
from coverage_planner import mission as mis  # noqa: E402
from coverage_planner.geo import Frame, area, is_convex  # noqa: E402
from coverage_planner.partition import PartitionError, report, split  # noqa: E402
from coverage_planner.plan import plan_mission  # noqa: E402

LAT0, LON0 = 13.0, 80.0
HOME = (LAT0 - 0.0005, LON0 - 0.0005)


def rect(w_m, h_m, lat0=LAT0, lon0=LON0, rot_deg=0.0):
    """Rectangle w x h metres, optionally rotated, as (lat, lon)."""
    f = Frame(lat0, lon0)
    pts = [(0, 0), (w_m, 0), (w_m, h_m), (0, h_m)]
    cx, cy = w_m / 2, h_m / 2
    t = math.radians(rot_deg)
    out = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        out.append(f.to_latlon(cx + dx * math.cos(t) - dy * math.sin(t),
                               cy + dx * math.sin(t) + dy * math.cos(t)))
    return out


TEN_HA = rect(400, 250)          # the nominal mission area


# ----------------------------------------------------------------- partition
def test_ten_hectare_area_is_right():
    f = Frame.from_points(TEN_HA)
    assert area(f.poly_to_xy(TEN_HA)) == pytest.approx(100_000, rel=0.01)


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_strips_have_equal_area(n):
    strips = split(TEN_HA, n)
    r = report(TEN_HA, strips)
    assert len(strips) == n
    assert r["max_imbalance"] < 0.01, f"imbalance {r['max_imbalance']:.2%}"
    assert r["sum_matches_total"], "strips do not tile the boundary"


def test_two_drone_fallback_is_supported():
    """Rule 8.8's minimum is two, and the de-scope plan relies on this."""
    strips = split(TEN_HA, 2)
    r = report(TEN_HA, strips)
    assert r["max_imbalance"] < 0.01
    assert all(a == pytest.approx(50_000, rel=0.02) for a in r["areas_m2"])


@pytest.mark.parametrize("rot", [0, 17, 45, 73, 90, 128])
def test_rotation_invariant(rot):
    """A boundary drawn at any bearing must partition just as evenly."""
    poly = rect(400, 250, rot_deg=rot)
    r = report(poly, split(poly, 3))
    assert r["max_imbalance"] < 0.01, f"rot {rot}: {r['max_imbalance']:.2%}"
    assert r["total_ha"] == pytest.approx(10.0, rel=0.02)


def test_long_thin_boundary():
    """800 x 125 m — the adversarial case named in sizing-calculations §18."""
    poly = rect(800, 125)
    r = report(poly, split(poly, 3))
    assert r["max_imbalance"] < 0.01
    assert r["total_ha"] == pytest.approx(10.0, rel=0.02)


def test_triangle_equal_area_is_not_equal_width():
    """Equal AREA strips of a triangle have very different widths. A planner
    that splits the bounding box instead would fail this."""
    f = Frame(LAT0, LON0)
    tri = [f.to_latlon(0, 0), f.to_latlon(600, 0), f.to_latlon(300, 400)]
    r = report(tri, split(tri, 3))
    assert r["max_imbalance"] < 0.02
    assert r["areas_m2"][0] == pytest.approx(r["areas_m2"][2], rel=0.02)


def test_concave_boundary_warns_but_still_tiles():
    f = Frame(LAT0, LON0)
    ell = [f.to_latlon(0, 0), f.to_latlon(400, 0), f.to_latlon(400, 100),
           f.to_latlon(150, 100), f.to_latlon(150, 300), f.to_latlon(0, 300)]
    assert not is_convex([f.to_xy(*p) for p in ell])
    with pytest.warns(UserWarning, match="concave"):
        strips = split(ell, 3)
    assert len(strips) == 3


def test_degenerate_inputs_raise():
    with pytest.raises(PartitionError):
        split([(13.0, 80.0), (13.0, 80.1)], 3)          # only 2 vertices
    with pytest.raises(PartitionError):
        split(TEN_HA, 0)
    with pytest.raises(PartitionError):                  # zero area
        split([(13.0, 80.0), (13.0, 80.1), (13.0, 80.2)], 2)


# ------------------------------------------------------------- boustrophedon
def test_line_spacing_matches_the_sizing_model():
    """40 m, 63.3 deg, 30 % sidelap -> the swath in mission_profile.py."""
    assert bou.swath_width(40, 63.3) == pytest.approx(49.3, rel=0.01)
    assert bou.line_spacing(40, 63.3, 0.30) == pytest.approx(34.5, rel=0.01)


def test_transects_cover_the_strip_with_no_gaps():
    """Every point of the strip must be within half a swath of some line.

    This is the test that matters: a gap is an undetected survivor, worth 25
    points plus up to 20 more in delivery.
    """
    strip = split(TEN_HA, 3)[1]
    f = Frame.from_points(strip)
    alt, hfov = 40.0, 63.3
    lines = bou.transects(strip, alt, hfov, 0.30, frame=f)
    half = bou.swath_width(alt, hfov) / 2.0

    xy = f.poly_to_xy(strip)
    segs = [(f.to_xy(*a), f.to_xy(*b)) for a, b in lines]
    xs = [p[0] for p in xy]
    ys = [p[1] for p in xy]

    def covered(px, py):
        for (ax, ay), (bx, by) in segs:
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px-ax)*dx + (py-ay)*dy) / L2))
            if math.dist((px, py), (ax + t*dx, ay + t*dy)) <= half + 1e-6:
                return True
        return False

    # sample the interior on a grid, skipping points outside the strip
    def inside(px, py):
        c = False
        n = len(xy)
        for i in range(n):
            x1, y1 = xy[i]
            x2, y2 = xy[(i + 1) % n]
            if ((y1 > py) != (y2 > py)) and \
               (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-15) + x1):
                c = not c
        return c

    misses = 0
    tested = 0
    for i in range(30):
        for j in range(30):
            px = min(xs) + (max(xs) - min(xs)) * (i + 0.5) / 30
            py = min(ys) + (max(ys) - min(ys)) * (j + 0.5) / 30
            if not inside(px, py):
                continue
            tested += 1
            if not covered(px, py):
                misses += 1
    assert tested > 100, "sampling failed"
    assert misses == 0, f"{misses}/{tested} interior points uncovered"


def test_zero_sidelap_leaves_wider_spacing():
    assert bou.line_spacing(40, 63.3, 0.0) > bou.line_spacing(40, 63.3, 0.30)
    with pytest.raises(ValueError):
        bou.line_spacing(40, 63.3, 1.0)


def test_alternating_directions_avoid_ferry_legs():
    """Consecutive transects must run opposite ways, or the aircraft flies the
    length of the strip empty between every pass."""
    strip = split(TEN_HA, 3)[0]
    f = Frame.from_points(strip)
    lines = bou.transects(strip, 40, 63.3, frame=f)
    assert len(lines) >= 2
    for i in range(len(lines) - 1):
        end = f.to_xy(*lines[i][1])
        nxt = f.to_xy(*lines[i + 1][0])
        assert math.dist(end, nxt) < 60, "turn is longer than a line spacing"


def test_sweep_time_is_in_the_expected_range():
    # ONE pass. mission_profile.py puts a 40 m sweep at ~149 s per drone; strips
    # round the line count up per drone, so expect somewhat more, not less.
    p = plan_mission(TEN_HA, HOME, 3, altitude_m=40.0, passes=1)
    assert 120 < p.longest_sweep_s < 260, f"{p.longest_sweep_s:.0f} s"


def test_a_second_pass_costs_a_second_sweep():
    """The geotag benefit of the reverse pass is not free, and the cost is the
    whole sweep again. Anyone raising `passes` needs to see that in the number,
    because for the full competition area two passes do not fit one battery."""
    one = plan_mission(TEN_HA, HOME, 3, altitude_m=40.0, passes=1)
    two = plan_mission(TEN_HA, HOME, 3, altitude_m=40.0, passes=2)
    assert two.longest_sweep_s > 1.9 * one.longest_sweep_s
    for a, b in zip(one.drones, two.drones):
        assert len(b.lines) == 2 * len(a.lines)
        assert b.path_m == pytest.approx(2 * a.path_m, rel=0.02)


def test_the_second_pass_is_flown_in_reverse():
    """Opposite heading is the entire point: it flips the sign of the
    along-track boresight bias so the two passes cancel it rather than
    accumulate it. A second pass in the SAME direction would double the frames
    and keep the bias, which is the mistake this guards against."""
    p = plan_mission(TEN_HA, HOME, 3, altitude_m=40.0, passes=2)
    for d in p.drones:
        half = len(d.lines) // 2
        fwd, rev = d.lines[:half], d.lines[half:]
        # last line of pass 1 and first of pass 2 are the same ground, opposite
        assert rev[0][0] == pytest.approx(fwd[-1][1])
        assert rev[0][1] == pytest.approx(fwd[-1][0])
        # and the whole double pass returns to where pass 1 began
        assert rev[-1][1] == pytest.approx(fwd[0][0])


# -------------------------------------------------------- ArduPilot mission
def test_mission_structure():
    p = plan_mission(TEN_HA, HOME, 3)
    m = p.drones[0].items
    assert m[0].command == mis.NAV_WAYPOINT and m[0].current == 1, "item 0 = HOME"
    assert m[0].lat == pytest.approx(HOME[0])
    assert any(i.command == mis.NAV_TAKEOFF for i in m)
    assert m[-1].command == mis.NAV_RETURN_TO_LAUNCH
    assert [i.seq for i in m] == list(range(len(m)))


def test_every_generated_mission_validates():
    for n in (2, 3):
        p = plan_mission(TEN_HA, HOME, n)
        for d in p.drones:
            assert d.problems == [], f"drone {d.drone_id}: {d.problems}"


def test_waypoints_use_relative_altitude_frame():
    """frame 3, not 0. Frame 0 is AMSL and at a 300 m field would fly the
    mission 300 m higher than intended."""
    p = plan_mission(TEN_HA, HOME, 3)
    for i in p.drones[0].items:
        if i.command == mis.NAV_WAYPOINT and i.seq > 0:
            assert i.frame == mis.FRAME_GLOBAL_RELATIVE_ALT


def test_wpl_round_trip():
    p = plan_mission(TEN_HA, HOME, 3)
    text = p.drones[0].wpl
    assert text.startswith("QGC WPL 110")
    back = mis.parse_wpl(text)
    orig = p.drones[0].items
    assert len(back) == len(orig)
    for a, b in zip(orig, back):
        assert a.command == b.command and a.seq == b.seq
        assert a.lat == pytest.approx(b.lat, abs=1e-7)
        assert a.lon == pytest.approx(b.lon, abs=1e-7)
        assert a.alt == pytest.approx(b.alt, abs=1e-4)


def test_validate_catches_a_broken_mission():
    """The validator must have teeth."""
    p = plan_mission(TEN_HA, HOME, 3)
    items = list(p.drones[0].items)
    assert mis.validate(items) == []
    for i in items:
        if i.command == mis.NAV_WAYPOINT and i.seq > 1:
            i.frame = 0                      # AMSL — the dangerous mistake
            break
    assert any("frame" in s for s in mis.validate(items))


def test_search_altitude_is_uniform_so_gsd_is_uniform():
    """Every drone searches at the SAME altitude.

    Staggering the search altitude for deconfliction silently changes swath and
    therefore GSD: a drone 10 m higher covers its strip in fewer lines because
    it sees a survivor with ~20 % fewer pixels. Detection is 250 points; nothing
    should quietly cost recall. The strips already separate the aircraft
    laterally during the sweep.
    """
    p = plan_mission(TEN_HA, HOME, 3, altitude_m=40.0, alt_stagger_m=5.0)
    assert {d.altitude_m for d in p.drones} == {40.0}
    counts = {len(d.lines) for d in p.drones}
    assert len(counts) == 1, f"uneven transect counts {counts} — GSD differs"


def test_transit_altitude_is_stratified():
    """Separation is applied where aircraft actually leave their strips."""
    # 20/25/30 under the 40 m deck. This used to assert 25/30/35, which left
    # the top band 5 m under aircraft that were still searching -- plan_mission
    # now refuses that outright, so asserting it here would be asserting the
    # defect.
    p = plan_mission(TEN_HA, HOME, 3, transit_alt_m=20.0, alt_stagger_m=5.0)
    transits = [d.transit_alt_m for d in p.drones]
    assert transits == [20.0, 25.0, 30.0]
    assert len(set(transits)) == 3
    # takeoff climbs to the drone's own transit altitude
    for d in p.drones:
        to = next(i for i in d.items if i.command == mis.NAV_TAKEOFF)
        assert to.alt == pytest.approx(d.transit_alt_m)


def test_plan_is_deterministic():
    """Same input, same mission — every time. Two aircraft cannot disagree
    about who owns what if the partition is reproducible."""
    a = plan_mission(TEN_HA, HOME, 3)
    b = plan_mission(TEN_HA, HOME, 3)
    for da, db in zip(a.drones, b.drones):
        assert da.wpl == db.wpl


def test_plan_is_fast_enough_for_the_setup_window():
    """SYS-38: parse, partition and render inside a 30 s allowance."""
    import time
    t0 = time.perf_counter()
    for _ in range(20):
        plan_mission(TEN_HA, HOME, 3)
    per = (time.perf_counter() - t0) / 20
    assert per < 0.5, f"{per*1000:.0f} ms per plan"
