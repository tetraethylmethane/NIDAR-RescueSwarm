"""Pixel to lat/lon. The 450-point half of the mission.

Detection and geotagging are one scored item worth 250 points (SYS-07, SYS-12),
and delivery accuracy is a further 200 aimed using the geotag. So this file
gates 450 of the 600 flight points, and the difference between doing it naively
and doing it properly is about 102 of them:

    A  no RTK, single frame               geotag 3.09 m ->  75 / 200
    B  RTK, single frame                         1.36 m -> 157 / 200
    C  RTK + multi-frame fusion + calibrated     1.00 m -> 177 / 200

None of that gap is recoverable by a better detector.

WHAT THIS MODULE IS
Pure geometry, no I/O, no camera, no autopilot. A detection plus the aircraft's
pose goes in; a lat/lon with an uncertainty comes out. Everything here is
testable on a laptop, and against Gazebo it can be scored to centimetres
because the simulator knows the true position of every object.

THE PIECE THAT MATTERS MOST
`t_capture` must be the camera EXPOSURE time, not when the frame was received.
At 8 m/s a 100 ms timestamp error is 0.8 m on the ground -- comparable to the
entire 0.91 m budget. Pose is interpolated to that instant; if the timestamp is
wrong, nothing downstream can recover it.

See docs/perception-integration-plan.md for the interface contract this
implements.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# WGS-84, and the local-tangent-plane approximation the rest of the repo uses.
# Over a 400 x 250 m search box the flat-earth error is millimetres, far below
# every other term in the budget.
R_LAT_M = 111_132.0


def m_per_deg_lon(lat_deg: float) -> float:
    return 111_320.0 * math.cos(math.radians(lat_deg))


# --------------------------------------------------------------- inputs
@dataclass(frozen=True)
class Camera:
    """Intrinsics. hfov/vfov are the full field of view, degrees."""

    width_px: int
    height_px: int
    hfov_deg: float
    vfov_deg: float

    @property
    def fx(self) -> float:
        return (self.width_px / 2.0) / math.tan(math.radians(self.hfov_deg) / 2.0)

    @property
    def fy(self) -> float:
        return (self.height_px / 2.0) / math.tan(math.radians(self.vfov_deg) / 2.0)


@dataclass(frozen=True)
class Pose:
    """Aircraft state at the exposure instant, in the local tangent plane.

    roll/pitch/yaw are the usual aircraft conventions in degrees: yaw is
    clockwise from north, pitch positive nose-up, roll positive right-wing-down.
    `agl_m` is height above the GROUND under the target, not above the launch
    point -- on a flood plain those differ, and the difference is a pure scale
    error on the whole offset.
    """

    lat: float
    lon: float
    agl_m: float
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    fix: str = "NONE"


@dataclass(frozen=True)
class Detection:
    """What the vision model emits. See the integration plan, section 3."""

    frame_id: int
    t_capture: float
    bbox: tuple[float, float, float, float]      # x, y, w, h in FULL-RES pixels
    confidence: float = 0.0
    class_id: int = 0
    camera_id: int = 0

    @property
    def centroid(self) -> tuple[float, float]:
        x, y, w, h = self.bbox
        return x + w / 2.0, y + h / 2.0


@dataclass(frozen=True)
class Geotag:
    lat: float
    lon: float
    fix: str
    sigma_m: float
    off_nadir_deg: float
    frames: int = 1
    confidence: float = 0.0


class GeotagError(ValueError):
    pass


# ------------------------------------------------------- the geometry
def camera_ray(cam: Camera, px: float, py: float) -> tuple[float, float, float]:
    """Pixel -> unit ray in the CAMERA frame (x right, y down, z forward).

    A nadir-pointing camera has z pointing at the ground.
    """
    cx, cy = cam.width_px / 2.0, cam.height_px / 2.0
    x = (px - cx) / cam.fx
    y = (py - cy) / cam.fy
    n = math.sqrt(x * x + y * y + 1.0)
    return x / n, y / n, 1.0 / n


def _rotate_body_to_ned(v, roll_deg, pitch_deg, yaw_deg):
    """Body -> NED by the standard 3-2-1 (yaw, pitch, roll) sequence."""
    r, p, y = (math.radians(a) for a in (roll_deg, pitch_deg, yaw_deg))
    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    x, yy, z = v
    # R = Rz(yaw) @ Ry(pitch) @ Rx(roll)
    n = (cy * cp) * x + (cy * sp * sr - sy * cr) * yy + (cy * sp * cr + sy * sr) * z
    e = (sy * cp) * x + (sy * sp * sr + cy * cr) * yy + (sy * sp * cr - cy * sr) * z
    d = (-sp) * x + (cp * sr) * yy + (cp * cr) * z
    return n, e, d


def project(det: Detection, pose: Pose, cam: Camera,
            gimbal_pitch_deg: float = -90.0,
            max_off_nadir_deg: float = 20.0,
            lever_arm_m: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> Geotag:
    """Intersect the detection's ray with the ground plane.

    gimbal_pitch_deg is the camera's pitch relative to the airframe; -90 is
    straight down, which is what NIDAR searches at. The camera frame is rotated
    into the body frame, then the body frame into NED.

    SYS-33: detections beyond `max_off_nadir_deg` are REJECTED rather than
    tagged where they lie. Off-nadir error grows as h*tan(theta) and the
    ground-height term stops cancelling, so an edge-of-frame tag is worth less
    than no tag -- it still consumes a delivery.
    """
    if pose.agl_m <= 0.0:
        raise GeotagError(f"AGL must be positive, got {pose.agl_m}")

    rx, ry, rz = camera_ray(cam, *det.centroid)

    # Camera -> body, in two steps.
    #
    # 1. With the gimbal at zero the camera looks forward, so the camera axes
    #    (x right, y down, z forward) map onto body FRD (x forward, y right,
    #    z down) as (z, x, y).
    bx0, by0, bz0 = rz, rx, ry
    #
    # 2. Rotate about the body Y (right) axis by the gimbal pitch. At -90 deg
    #    a centre pixel comes out as (0, 0, 1) -- straight down -- and the
    #    bottom of the image points AFT, which is what a nadir camera does.
    g = math.radians(gimbal_pitch_deg)
    cg, sg = math.cos(g), math.sin(g)
    bx = bx0 * cg + bz0 * sg
    by = by0
    bz = -bx0 * sg + bz0 * cg

    n, e, d = _rotate_body_to_ned((bx, by, bz),
                                  pose.roll_deg, pose.pitch_deg, pose.yaw_deg)

    off_nadir = math.degrees(math.acos(max(-1.0, min(1.0, d))))
    if d <= 1e-6:
        raise GeotagError("ray does not point at the ground "
                          f"(off-nadir {off_nadir:.1f} deg)")
    if off_nadir > max_off_nadir_deg:
        raise GeotagError(
            f"off-nadir {off_nadir:.1f} deg exceeds the {max_off_nadir_deg:.0f} "
            f"deg gate (SYS-33) -- re-acquire nearer nadir")

    # Scale the ray until it reaches the ground.
    s = pose.agl_m / d
    north_m = n * s + lever_arm_m[0]
    east_m = e * s + lever_arm_m[1]

    lat = pose.lat + north_m / R_LAT_M
    lon = pose.lon + east_m / m_per_deg_lon(pose.lat)

    return Geotag(lat=lat, lon=lon, fix=pose.fix,
                  sigma_m=sigma_for(pose.fix, pose.agl_m, off_nadir),
                  off_nadir_deg=off_nadir, frames=1,
                  confidence=det.confidence)


# ------------------------------------------------------- uncertainty
# From the case-C stack in sizing-calculations.md section 11. These are the
# terms that do NOT average out across frames; GNSS noise does and is handled
# separately by the fix quality.
SYSTEMATIC_M = math.sqrt(0.70 ** 2 + 0.50 ** 2 + 0.16 ** 2 + 0.10 ** 2)
FIX_SIGMA_M = {
    "RTK_FIXED": 0.03,
    "RTK_FLOAT": 0.40,
    "DGPS": 1.00,
    "3D": 2.50,
    "2D": 8.00,
    "NONE": 50.0,
}


def sigma_for(fix: str, agl_m: float, off_nadir_deg: float) -> float:
    """1-sigma horizontal, for fusion weighting and for the operator's display.

    Attitude error projects as agl*tan(err), and grows off-nadir, so the same
    attitude uncertainty costs more at the edge of frame than at the centre.
    """
    gnss = FIX_SIGMA_M.get(fix, FIX_SIGMA_M["NONE"])
    att = agl_m * math.tan(math.radians(0.5)) / max(0.2, math.cos(
        math.radians(off_nadir_deg)))
    return math.sqrt(gnss ** 2 + att ** 2 + SYSTEMATIC_M ** 2)


# ------------------------------------------------------------ fusion
FIX_RANK = {"NONE": 0, "2D": 1, "3D": 2, "DGPS": 3, "RTK_FLOAT": 4, "RTK_FIXED": 5}


@dataclass
class Survivor:
    """One physical person, built from repeated observations."""

    survivor_id: int
    lat: float
    lon: float
    fix: str
    sigma_m: float
    frames: int = 1
    confidence: float = 0.0
    _w_lat: float = field(default=0.0, repr=False)
    _w_lon: float = field(default=0.0, repr=False)
    _w: float = field(default=0.0, repr=False)


class SurvivorTracker:
    """Cluster geotags into survivors and fuse them.

    This is the B -> C step and it is worth about 20 points per drop. Two
    deliberate choices:

    * Inverse-variance weighting, so an RTK_FIXED observation dominates a 3D
      one instead of being averaged into it.
    * The reported FIX is the BEST ever seen for that survivor, not the latest.
      The ground station ranks competing observations on fix quality first for
      the same reason: a later RTK_FLOAT tag is metres worse than an earlier
      RTK_FIXED one, and reporting the newer one throws away the better.
    """

    def __init__(self, gate_m: float = 8.0, confirm_frames: int = 3) -> None:
        self.gate_m = gate_m
        self.confirm_frames = confirm_frames
        self.survivors: dict[int, Survivor] = {}
        self._next = 1

    def _distance_m(self, s: Survivor, g: Geotag) -> float:
        dn = (g.lat - s.lat) * R_LAT_M
        de = (g.lon - s.lon) * m_per_deg_lon(s.lat)
        return math.hypot(dn, de)

    def add(self, g: Geotag) -> Survivor:
        best, best_d = None, self.gate_m
        for s in self.survivors.values():
            d = self._distance_m(s, g)
            if d < best_d:
                best, best_d = s, d

        w = 1.0 / max(g.sigma_m, 1e-3) ** 2
        if best is None:
            s = Survivor(self._next, g.lat, g.lon, g.fix, g.sigma_m,
                         frames=1, confidence=g.confidence)
            s._w_lat, s._w_lon, s._w = g.lat * w, g.lon * w, w
            self.survivors[self._next] = s
            self._next += 1
            return s

        best._w_lat += g.lat * w
        best._w_lon += g.lon * w
        best._w += w
        best.lat = best._w_lat / best._w
        best.lon = best._w_lon / best._w
        best.sigma_m = 1.0 / math.sqrt(best._w)
        best.frames += 1
        best.confidence = max(best.confidence, g.confidence)
        if FIX_RANK.get(g.fix, 0) > FIX_RANK.get(best.fix, 0):
            best.fix = g.fix
        return best

    def confirmed(self) -> list[Survivor]:
        """Only survivors seen enough times. A single frame is a maybe."""
        return [s for s in self.survivors.values()
                if s.frames >= self.confirm_frames]
