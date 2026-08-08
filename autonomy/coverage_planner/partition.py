"""Equal-area partition of the mission boundary — implementation-plan.md §1.3.

Splits the polygon into N sub-regions of equal area by cutting perpendicular to
its long axis, so each strip stays long and thin.

WHY THIS RATHER THAN DARP. Rule 4D-3 awards 50 marks for "two or more drones
operating as one coordinated mission system with shared mission execution,
common mission logic, and no independent manual control". It names no algorithm.
A deterministic partition satisfies that, is inspectable, and is testable on a
laptop. DARP is weeks of work for coverage-time savings on a mission that uses
26 % of its time budget.

WHY CUT ACROSS THE LONG AXIS. Transect count is what costs turns, and it equals
strip width divided by line spacing — where "width" is measured PERPENDICULAR to
the transects. Cutting across the short axis leaves each strip long in the
transect direction and narrow across it, which minimises turns:

    400 x 250 m, 3 drones, 34.5 m line spacing

    cut across short axis -> strips 400 x 83 m -> 3 transects each, 2 turns
    cut across long axis  -> strips 133 x 250 m -> 4 transects each, 3 turns

Same ground covered either way; the first costs one turn less per drone, and a
turn is 6 s in the mission model.
"""
from __future__ import annotations

import math
import warnings

from .geo import Frame, area, clip_halfplane, is_convex, principal_axis, rotate


class PartitionError(ValueError):
    pass


def _bisect_cut(poly_rot, target_area: float, lo: float, hi: float,
                tol: float = 1e-4, iters: int = 80) -> float:
    """Find the y-offset whose lower half-plane cuts off `target_area`."""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        a = area(clip_halfplane(poly_rot, (0.0, 1.0), mid, keep_below=True))
        if abs(a - target_area) < tol * max(target_area, 1.0):
            return mid
        if a < target_area:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def split(boundary: list[tuple[float, float]], n: int = 3,
          frame: Frame | None = None) -> list[list[tuple[float, float]]]:
    """Split a (lat, lon) boundary into `n` equal-area (lat, lon) sub-regions.

    Strips are returned in order along the cut axis, which is deterministic:
    drone i always gets strip i, so two aircraft cannot disagree about who owns
    what — because they were told, not because they negotiated.
    """
    if n < 1:
        raise PartitionError("n must be >= 1")
    if len(boundary) < 3:
        raise PartitionError("boundary needs at least 3 vertices")

    frame = frame or Frame.from_points(boundary)
    xy = frame.poly_to_xy(boundary)
    if area(xy) <= 0:
        raise PartitionError("boundary has zero area")

    if not is_convex(xy):
        warnings.warn(
            "boundary is concave; half-plane clipping can bridge across a "
            "notch. Verify the rendered strips on the GCS before flying.",
            stacklevel=2,
        )
    if n == 1:
        return [list(boundary)]

    # Rotate so the LONG axis lies along x. Cutting at constant y then divides
    # across the short axis, leaving long thin strips.
    theta = principal_axis(xy)
    rot = rotate(xy, -theta)

    total = area(rot)
    ys = [p[1] for p in rot]
    lo, hi = min(ys), max(ys)

    cuts = [_bisect_cut(rot, total * (i + 1) / n, lo, hi) for i in range(n - 1)]

    strips = []
    lower = lo - 1.0
    for cut in [*cuts, hi + 1.0]:
        piece = clip_halfplane(rot, (0.0, 1.0), cut, keep_below=True)
        piece = clip_halfplane(piece, (0.0, 1.0), lower, keep_below=False)
        if len(piece) < 3:
            raise PartitionError(
                f"empty strip between {lower:.1f} and {cut:.1f} m — the "
                f"boundary may be degenerate for {n} drones"
            )
        strips.append(rotate(piece, theta))
        lower = cut

    return [frame.poly_to_latlon(s) for s in strips]


def report(boundary, strips, frame: Frame | None = None) -> dict:
    """Areas and balance, for the GCS to display and for tests to assert on."""
    frame = frame or Frame.from_points(boundary)
    total = area(frame.poly_to_xy(boundary))
    areas = [area(frame.poly_to_xy(s)) for s in strips]
    ideal = total / len(strips) if strips else 0.0
    worst = max(abs(a - ideal) / ideal for a in areas) if ideal else 0.0
    return {
        "total_m2": total,
        "total_ha": total / 10_000.0,
        "areas_m2": areas,
        "areas_ha": [a / 10_000.0 for a in areas],
        "ideal_m2": ideal,
        "max_imbalance": worst,          # fraction, e.g. 0.004 = 0.4 %
        "sum_matches_total": abs(sum(areas) - total) / total < 1e-6,
    }
