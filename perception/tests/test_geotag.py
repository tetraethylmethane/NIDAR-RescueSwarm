"""Geotag geometry, checked against cases with a known right answer.

A projection bug does not crash. It puts the survivor somewhere plausible and
wrong, and you find out on the flight line -- or you do not find out, and lose
the delivery points quietly. So every test here has an answer computable by
hand, and several exist specifically to catch a flipped sign or a swapped axis,
which are the errors that look correct in a demo.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "geotagging"))

from geotag import (  # noqa: E402
    Camera, Detection, GeotagError, Pose, R_LAT_M, SurvivorTracker,
    m_per_deg_lon, project, sigma_for,
)

# The sizing model's camera: 63.3 deg HFOV, 50.0 deg VFOV.
CAM = Camera(width_px=4056, height_px=3040, hfov_deg=63.3, vfov_deg=50.0)
LAT0, LON0 = 13.0, 80.0
AGL = 60.0


def det_at(px, py, **kw):
    return Detection(frame_id=kw.pop("frame_id", 1), t_capture=0.0,
                     bbox=(px - 10, py - 10, 20, 20), **kw)


def centre():
    return det_at(CAM.width_px / 2, CAM.height_px / 2)


def offset_m(g, lat=LAT0, lon=LON0):
    """North, east metres of a geotag from a reference."""
    return ((g.lat - lat) * R_LAT_M, (g.lon - lon) * m_per_deg_lon(lat))


# --------------------------------------------------------- the easy one
def test_centre_pixel_straight_down_lands_under_the_aircraft():
    g = project(centre(), Pose(LAT0, LON0, AGL, fix="RTK_FIXED"), CAM)
    n, e = offset_m(g)
    assert abs(n) < 0.01 and abs(e) < 0.01
    assert g.off_nadir_deg < 0.01


# ------------------------------------------- axis and sign, the real risks
def test_image_right_maps_to_aircraft_right_when_facing_north():
    """Facing north, right is EAST. If this comes out west, the y axis is
    flipped and every tag is mirrored -- which looks entirely plausible."""
    px = CAM.width_px / 2 + CAM.width_px / 4
    g = project(det_at(px, CAM.height_px / 2),
                Pose(LAT0, LON0, AGL, yaw_deg=0.0, fix="RTK_FIXED"), CAM)
    n, e = offset_m(g)
    assert e > 1.0, f"expected east, got east={e:.2f}"
    assert abs(n) < 0.01


def test_image_bottom_maps_aft_when_facing_north():
    """A nadir camera sees BEHIND the aircraft at the bottom of the frame."""
    py = CAM.height_px / 2 + CAM.height_px / 4
    g = project(det_at(CAM.width_px / 2, py),
                Pose(LAT0, LON0, AGL, yaw_deg=0.0, fix="RTK_FIXED"), CAM)
    n, e = offset_m(g)
    assert n < -1.0, f"expected south (aft), got north={n:.2f}"
    assert abs(e) < 0.01


def test_yaw_rotates_the_offset():
    """Same pixel, aircraft turned 90 deg right: the offset must rotate with
    it. If yaw is ignored, tags are right only when heading north."""
    px = CAM.width_px / 2 + CAM.width_px / 4
    d = det_at(px, CAM.height_px / 2)
    north = project(d, Pose(LAT0, LON0, AGL, yaw_deg=0.0, fix="RTK_FIXED"), CAM)
    east = project(d, Pose(LAT0, LON0, AGL, yaw_deg=90.0, fix="RTK_FIXED"), CAM)
    n0, e0 = offset_m(north)
    n1, e1 = offset_m(east)
    assert e0 > 1.0 and abs(n0) < 0.01          # facing north -> east
    assert n1 < -1.0 and abs(e1) < 0.01         # facing east  -> south
    assert abs(math.hypot(n0, e0) - math.hypot(n1, e1)) < 0.01


def test_offset_scales_linearly_with_altitude():
    """The ground offset is agl * tan(angle). Double the height, double the
    offset. A bug that uses AMSL instead of AGL shows up here."""
    px = CAM.width_px / 2 + CAM.width_px / 4
    d = det_at(px, CAM.height_px / 2)
    a = project(d, Pose(LAT0, LON0, 40.0, fix="RTK_FIXED"), CAM)
    b = project(d, Pose(LAT0, LON0, 80.0, fix="RTK_FIXED"), CAM)
    _, ea = offset_m(a)
    _, eb = offset_m(b)
    assert abs(eb / ea - 2.0) < 1e-6


def test_known_angle_gives_the_hand_computed_offset():
    """Quarter-width from centre is a known angle; check the metres."""
    px = CAM.width_px / 2 + CAM.width_px / 4
    g = project(det_at(px, CAM.height_px / 2),
                Pose(LAT0, LON0, AGL, fix="RTK_FIXED"), CAM)
    _, e = offset_m(g)
    expect = AGL * (CAM.width_px / 4) / CAM.fx      # agl * tan(theta)
    assert abs(e - expect) < 0.01, f"{e:.3f} vs {expect:.3f}"


# ------------------------------------------------------ SYS-33, the gate
def test_off_nadir_beyond_20_deg_is_refused():
    """Rejecting an edge detection is deliberate: a bad tag still consumes a
    delivery, so it is worth less than no tag."""
    with pytest.raises(GeotagError, match="off-nadir"):
        project(det_at(CAM.width_px - 5, CAM.height_px / 2),
                Pose(LAT0, LON0, AGL, fix="RTK_FIXED"), CAM)


def test_off_nadir_is_reported_for_accepted_detections():
    g = project(det_at(CAM.width_px / 2 + 400, CAM.height_px / 2),
                Pose(LAT0, LON0, AGL, fix="RTK_FIXED"), CAM)
    assert 0.0 < g.off_nadir_deg <= 20.0


def test_zero_or_negative_agl_is_refused():
    with pytest.raises(GeotagError, match="AGL"):
        project(centre(), Pose(LAT0, LON0, 0.0, fix="RTK_FIXED"), CAM)


# ------------------------------------------------------------ uncertainty
def test_rtk_is_worth_metres_over_no_fix():
    assert sigma_for("RTK_FIXED", AGL, 0) < sigma_for("3D", AGL, 0)
    assert sigma_for("3D", AGL, 0) < sigma_for("NONE", AGL, 0)


def test_sigma_never_beats_the_systematic_floor():
    """Multi-frame fusion cannot average away boresight or target extent. A
    sigma below the systematic floor would make fusion over-confident and
    silently mis-weight everything."""
    assert sigma_for("RTK_FIXED", AGL, 0) > 0.85


def test_off_nadir_costs_accuracy():
    assert sigma_for("RTK_FIXED", AGL, 18) > sigma_for("RTK_FIXED", AGL, 0)


# ---------------------------------------------------------------- fusion
def test_repeated_observations_tighten_the_estimate():
    t = SurvivorTracker()
    pose = Pose(LAT0, LON0, AGL, fix="RTK_FIXED")
    first = t.add(project(centre(), pose, CAM))
    s0 = first.sigma_m
    for _ in range(9):
        s = t.add(project(centre(), pose, CAM))
    assert len(t.survivors) == 1
    assert s.frames == 10
    assert s.sigma_m < s0


def test_two_people_apart_are_two_survivors():
    t = SurvivorTracker(gate_m=8.0)
    pose_a = Pose(LAT0, LON0, AGL, fix="RTK_FIXED")
    pose_b = Pose(LAT0 + 50.0 / R_LAT_M, LON0, AGL, fix="RTK_FIXED")
    t.add(project(centre(), pose_a, CAM))
    t.add(project(centre(), pose_b, CAM))
    assert len(t.survivors) == 2


def test_the_best_fix_wins_not_the_latest():
    """The GCS ranks fix quality first for the same reason: a later RTK_FLOAT
    tag is metres worse than an earlier RTK_FIXED one."""
    t = SurvivorTracker()
    t.add(project(centre(), Pose(LAT0, LON0, AGL, fix="RTK_FIXED"), CAM))
    s = t.add(project(centre(), Pose(LAT0, LON0, AGL, fix="3D"), CAM))
    assert s.fix == "RTK_FIXED"


def test_a_good_fix_dominates_a_bad_one_in_the_average():
    """Inverse-variance weighting: a 3D observation 5 m away must not drag an
    RTK_FIXED estimate halfway to it."""
    t = SurvivorTracker(gate_m=20.0)
    good = Pose(LAT0, LON0, AGL, fix="RTK_FIXED")
    bad = Pose(LAT0 + 5.0 / R_LAT_M, LON0, AGL, fix="NONE")
    t.add(project(centre(), good, CAM))
    s = t.add(project(centre(), bad, CAM))
    pulled_m = (s.lat - LAT0) * R_LAT_M
    assert pulled_m < 1.0, f"the bad fix moved the estimate {pulled_m:.2f} m"


def test_one_frame_is_not_a_confirmed_survivor():
    t = SurvivorTracker(confirm_frames=3)
    pose = Pose(LAT0, LON0, AGL, fix="RTK_FIXED")
    t.add(project(centre(), pose, CAM))
    assert t.confirmed() == []
    t.add(project(centre(), pose, CAM))
    t.add(project(centre(), pose, CAM))
    assert len(t.confirmed()) == 1
