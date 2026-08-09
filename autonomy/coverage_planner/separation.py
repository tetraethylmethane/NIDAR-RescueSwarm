"""How close do the three aircraft actually get?

plan.py argues they cannot conflict: the strips are non-overlapping laterally,
and transit is stratified by altitude. That argument was written before the
mission builder implemented it, and it was wrong for a while without anything
noticing -- the stagger was applied to NAV_TAKEOFF only, so every aircraft flew
its ingress diagonally through the search deck. An argument in a docstring is
not a separation minimum. This measures one.

TIME-INDEPENDENT, ON PURPOSE
The obvious check is to fly all three on a clock and watch the distance. That
answers a weaker question than it appears to: the schedule holds only if the
wind, the turn time and the arming order all behave. Sweep times differ between
drones by design, so phasing drifts through the flight and a nominal-timing pass
says little about the real one.

So the primary check ignores time and asks the stronger question: how close do
the flight PATHS come, at any point, on any pair? If that number is safe, no
amount of schedule drift can cause a conflict. It is a conservative bound --
two aircraft passing the same point ten minutes apart are counted as a near
miss -- so a failure here is a prompt to look, not proof of a collision.

WHAT IT FOUND
The search plan is clean: 14.3 m worst pair across the whole sweep. The pad is
not. With the pad included the three paths come within 1.20 m of each other,
because that is the slot spacing, and each aircraft climbs and descends in a
vertical column directly above its own slot. Slot separation is a parking
arrangement, not a landing one -- which is why RTL_LOIT_TIME in
firmware/ardupilot-params/params.py sequences the descents, and why that
parameter matters more than any geometry in this file.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .geo import Frame

# MAVLink command IDs that carry a position we actually fly to.
NAV_WAYPOINT = 16
NAV_TAKEOFF = 22


@dataclass
class Conflict:
    drone_a: int
    drone_b: int
    distance_m: float
    at_a: tuple[float, float, float]   # x, y, alt in local metres
    at_b: tuple[float, float, float]

    def describe(self) -> str:
        return (f"drones {self.drone_a} and {self.drone_b} pass "
                f"{self.distance_m:.1f} m apart "
                f"(alt {self.at_a[2]:.0f} m vs {self.at_b[2]:.0f} m)")


def path_xyz(plan, frame: Frame) -> list[tuple[float, float, float]]:
    """A drone's flight path as (x_east, y_north, alt) vertices in metres.

    Takes the positional mission items in order. NAV_TAKEOFF carries no
    position -- it climbs over the pad -- so it contributes the pad slot at its
    own altitude, which is what makes the vertical climb off the pad visible to
    the segment check.
    """
    pts: list[tuple[float, float, float]] = []
    for it in plan.items:
        if it.command == NAV_TAKEOFF:
            if pts:
                x, y, _ = pts[0]
                pts.append((x, y, it.alt))
            continue
        if it.command != NAV_WAYPOINT:
            continue
        x, y = frame.to_xy(it.lat, it.lon)
        pts.append((x, y, it.alt))
    return pts


def _seg_seg_distance(p1, q1, p2, q2) -> tuple[float, tuple, tuple]:
    """Shortest distance between 3D segments p1q1 and p2q2, and the points.

    Standard clamped-parameter solution. The degenerate cases -- either segment
    a point, or the two parallel -- fall out of the denominator guard rather
    than needing their own branches.
    """
    d1 = [q1[i] - p1[i] for i in range(3)]
    d2 = [q2[i] - p2[i] for i in range(3)]
    r = [p1[i] - p2[i] for i in range(3)]
    a = sum(v * v for v in d1)
    e = sum(v * v for v in d2)
    f = sum(d2[i] * r[i] for i in range(3))

    if a <= 1e-12 and e <= 1e-12:
        s = t = 0.0
    elif a <= 1e-12:
        s, t = 0.0, min(1.0, max(0.0, f / e))
    elif e <= 1e-12:
        c = sum(d1[i] * r[i] for i in range(3))
        s, t = min(1.0, max(0.0, -c / a)), 0.0
    else:
        c = sum(d1[i] * r[i] for i in range(3))
        b = sum(d1[i] * d2[i] for i in range(3))
        denom = a * e - b * b
        s = min(1.0, max(0.0, (b * f - c * e) / denom)) if denom > 1e-12 else 0.0
        t = (b * s + f) / e
        if t < 0.0:
            t, s = 0.0, min(1.0, max(0.0, -c / a))
        elif t > 1.0:
            t, s = 1.0, min(1.0, max(0.0, (b - c) / a))

    ca = tuple(p1[i] + d1[i] * s for i in range(3))
    cb = tuple(p2[i] + d2[i] * t for i in range(3))
    return math.dist(ca, cb), ca, cb


def min_separation(plans, frame: Frame, ignore_pad_radius_m: float = 8.0):
    """Closest approach between every pair of flight PATHS, ignoring time.

    The pad is excluded within `ignore_pad_radius_m`: three aircraft parked in a
    row 1.22 m apart are 1.22 m apart by design, and counting that as a conflict
    would drown the signal from the part of the flight where separation is
    earned rather than assigned. Ground separation on the pad is a sequencing
    problem -- RTL_LOIT_TIME -- not a geometry one.
    """
    paths = {p.drone_id: path_xyz(p, frame) for p in plans}
    pads = {p.drone_id: frame.to_xy(p.pad_slot[0], p.pad_slot[1])
            for p in plans}

    def near_pad(pt, pad):
        return math.hypot(pt[0] - pad[0], pt[1] - pad[1]) < ignore_pad_radius_m

    out: list[Conflict] = []
    ids = sorted(paths)
    for ia in range(len(ids)):
        for ib in range(ia + 1, len(ids)):
            a_id, b_id = ids[ia], ids[ib]
            pa, pb = paths[a_id], paths[b_id]
            best = None
            for i in range(len(pa) - 1):
                for j in range(len(pb) - 1):
                    d, ca, cb = _seg_seg_distance(pa[i], pa[i + 1],
                                                  pb[j], pb[j + 1])
                    if near_pad(ca, pads[a_id]) and near_pad(cb, pads[b_id]):
                        continue
                    if best is None or d < best[0]:
                        best = (d, ca, cb)
            if best is not None:
                out.append(Conflict(a_id, b_id, best[0], best[1], best[2]))
    out.sort(key=lambda c: c.distance_m)
    return out


def report(plans, frame: Frame, minimum_m: float = 5.0) -> str:
    """Human-readable separation summary; the number, then the verdict."""
    cs = min_separation(plans, frame)
    lines = [f"closest approach between flight paths (time-independent, "
             f"minimum {minimum_m:.0f} m):"]
    for c in cs:
        ok = "ok  " if c.distance_m >= minimum_m else "TIGHT"
        lines.append(f"  {ok} {c.describe()}")
    worst = min((c.distance_m for c in cs), default=float("inf"))
    lines.append(f"  worst pair: {worst:.1f} m")
    return "\n".join(lines)
