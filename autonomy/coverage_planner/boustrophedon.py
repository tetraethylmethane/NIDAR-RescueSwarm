"""Boustrophedon (lawnmower) transects within one drone's strip.

Generates the parallel search lines that ArduPilot flies in AUTO mode. Per
implementation-plan.md §1.1 there is no custom flight code for the search phase
at all — these waypoints are uploaded during setup and the autopilot executes
them.

LINE SPACING comes from the camera, not from taste:

    swath   = 2 * altitude * tan(HFOV / 2)
    spacing = swath * (1 - sidelap)

Sidelap exists because attitude wobble, altitude error and lens distortion all
move the real footprint around. 30 % is the project default (sizing §8). Setting
it to zero leaves gaps between passes, and a gap is a survivor worth 25 points
plus up to 20 more in delivery.

THE EDGE CASE THAT MATTERS: the first and last transects are inset by half a
spacing from the strip edge, so the swath — not the flight line — reaches the
boundary. Putting a line exactly on the edge wastes half its swath outside the
region and leaves an uncovered sliver inside it.
"""
from __future__ import annotations

import math

from .geo import Frame, area, clip_halfplane, principal_axis, rotate


def swath_width(altitude_m: float, hfov_deg: float) -> float:
    """Ground width imaged across-track."""
    return 2.0 * altitude_m * math.tan(math.radians(hfov_deg) / 2.0)


def line_spacing(altitude_m: float, hfov_deg: float, sidelap: float = 0.30) -> float:
    if not 0.0 <= sidelap < 1.0:
        raise ValueError("sidelap must be in [0, 1)")
    return swath_width(altitude_m, hfov_deg) * (1.0 - sidelap)


def _clip_segment_to_poly(poly, y: float):
    """Intersect the horizontal line y=const with a convex polygon.

    Returns (x_min, x_max) or None. Works on the rotated frame where transects
    are horizontal.
    """
    xs = []
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 - y) * (y2 - y) > 0:            # both strictly one side
            continue
        if abs(y2 - y1) < 1e-12:               # horizontal edge on the line
            xs.extend([x1, x2])
            continue
        t = (y - y1) / (y2 - y1)
        if -1e-9 <= t <= 1 + 1e-9:
            xs.append(x1 + t * (x2 - x1))
    if len(xs) < 2:
        return None
    lo, hi = min(xs), max(xs)
    return None if hi - lo < 1e-6 else (lo, hi)


def transects(strip: list[tuple[float, float]], altitude_m: float,
              hfov_deg: float, sidelap: float = 0.30,
              frame: Frame | None = None,
              start_far_side: bool = False) -> list[list[tuple[float, float]]]:
    """Alternating transects covering `strip`, as (lat, lon) line segments.

    `start_far_side` flips which end the sweep begins at, so adjacent drones can
    be given opposing sweep directions and end up further apart rather than
    converging on a shared edge at the same moment.
    """
    frame = frame or Frame.from_points(strip)
    xy = frame.poly_to_xy(strip)
    if area(xy) <= 0:
        return []

    theta = principal_axis(xy)
    rot = rotate(xy, -theta)                   # long axis now along x
    ys = [p[1] for p in rot]
    y_lo, y_hi = min(ys), max(ys)
    span = y_hi - y_lo

    spacing = line_spacing(altitude_m, hfov_deg, sidelap)
    if spacing <= 0:
        raise ValueError("line spacing must be positive")

    # Number of lines needed to cover `span` with the swath, then inset by half
    # a spacing so the SWATH reaches the edges rather than the flight line.
    n_lines = max(1, math.ceil(span / spacing))
    if n_lines == 1:
        line_ys = [0.5 * (y_lo + y_hi)]
    else:
        step = span / n_lines
        line_ys = [y_lo + step * (i + 0.5) for i in range(n_lines)]

    if start_far_side:
        line_ys.reverse()

    out = []
    for i, y in enumerate(line_ys):
        seg = _clip_segment_to_poly(rot, y)
        if seg is None:
            continue
        x0, x1 = seg
        if i % 2:                              # alternate direction: no ferry legs
            x0, x1 = x1, x0
        pts = rotate([(x0, y), (x1, y)], theta)
        out.append(frame.poly_to_latlon(pts))
    return out


def path_length_m(lines, frame: Frame | None = None) -> float:
    """Total flown distance including the turns between transects."""
    if not lines:
        return 0.0
    frame = frame or Frame.from_points([p for ln in lines for p in ln])
    total = 0.0
    prev_end = None
    for ln in lines:
        a = frame.to_xy(*ln[0])
        b = frame.to_xy(*ln[1])
        if prev_end is not None:
            total += math.dist(prev_end, a)
        total += math.dist(a, b)
        prev_end = b
    return total


def sweep_time_s(lines, speed_ms: float, turn_s: float = 6.0,
                 frame: Frame | None = None) -> float:
    """Sweep duration at constant groundspeed, plus a fixed cost per turn."""
    if not lines:
        return 0.0
    return path_length_m(lines, frame) / speed_ms + turn_s * (len(lines) - 1)
