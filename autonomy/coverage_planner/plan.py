"""End-to-end: KML boundary in, one AUTO mission per drone out.

This is what the GCS calls when the organisers hand over the mission file during
the 5-minute setup window. It must run in well under the 30 s allowance in the
setup budget (SYS-38), so everything here is pure geometry with no I/O.

    boundary (lat, lon)  ->  N equal-area strips
                         ->  boustrophedon transects per strip
                         ->  QGC WPL 110 mission per drone

DECONFLICTION, AND WHY THE SEARCH ALTITUDE IS **NOT** STRATIFIED
---------------------------------------------------------------
An earlier version of this module staggered the search altitude per drone (40 /
45 / 50 m) as a cheap deconfliction layer. That was wrong, and the planner's own
output exposed it: swath scales with altitude, so drone 3 at 50 m needed fewer
transects than drone 1 at 40 m — **because its ground sample distance was
coarser**. It was flying the same area with 20 % fewer pixels on a survivor
(112 px against 140 px), across a third of the search region, to buy separation
that was not needed.

Detection and geotagging are worth 250 points. Nothing should quietly cost GSD.

The strips already provide the separation: during the sweep each aircraft is
inside its own non-overlapping region, so they cannot conflict laterally.
Altitude separation is only needed where aircraft leave their strips — transit,
delivery excursions and recovery — so that is where it is applied:

  search   every drone at the SAME altitude -> uniform GSD, uniform recall
  transit  staggered per drone (`transit_alt_m` + `alt_stagger_m` * i)
  RTL      set per drone via the ArduPilot RTL_ALT parameter, not a waypoint

THE PAD IS SHARED, SO THE PAD SLOTS ARE NOT
-------------------------------------------
Rule 8.10 gives one 12 ft x 12 ft pad -- 3.66 m -- and the compliance argument
for fitting three 1046 mm aircraft on it is "3 per row". This module used to
pass a single `home` to all three missions, so all three RTLs terminated at the
identical lat/lon: the planner contradicted the compliance argument, and three
aircraft descending on one point is a collision, not a landing.

`pad_slots()` places them in that row. Separation alone is not enough at 1.22 m
spacing, so the descents are also SEQUENCED, by a staggered RTL_LOIT_TIME in
firmware/ardupilot-params/params.py. That is a parameter and not code on
purpose: the battery failsafe RTL is a mode change inside the flight
controller, so a mission-item sequence would not cover the case that matters
most -- three aircraft on one pack design hitting low battery within seconds of
each other and all turning for home at once.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field

from . import boustrophedon as bou
from . import mission as mis
from .geo import Frame, area
from .partition import report, split


PAD_SIDE_M = 3.66               # 12 ft, rule 8.10
AIRFRAME_FOOTPRINT_M = 1.046    # motor-to-motor across, model STEP 11

# How far the highest transit band must sit below the common search deck.
#
# This is the constraint that makes the stratification mean anything, and it
# was implicit and violated. With transit at 25/30/35 under a 40 m deck, the
# top band had 5 m of clearance -- and once sweeps were re-ordered to finish
# near the pad, the longer ingress legs put a transiting aircraft directly
# under a searching one at exactly that 5 m. Measured, not hypothesised.
#
# 10 m is about 10x the altitude-hold error of a barometric multirotor, and
# costs nothing: the band is set by obstacle clearance at the bottom, not by
# the deck at the top.
DECK_CLEARANCE_M = 10.0


# Touchdown dispersion, one sigma-ish, per aircraft. Two aircraft can each
# drift this far TOWARD each other, so the slot spacing has to absorb twice it.
# Measured: aircraft aiming at slots 1.22 m apart came to rest 0.83 m apart.
TOUCHDOWN_DISPERSION_M = 0.5


def pad_slots(home: tuple[float, float], n: int, frame: Frame,
              bearing_deg: float = 90.0,
              pad_side_m: float = PAD_SIDE_M,
              dispersion_m: float = TOUCHDOWN_DISPERSION_M
              ) -> list[tuple[float, float]]:
    """N landing points on the shared pad, placed as far apart as it allows.

    Returned in drone order, so drone 1 gets slot 0. The aircraft must be placed
    on -- and armed on -- its own slot, because ArduPilot takes HOME from the
    arming position and RTL returns there regardless of what item 0 says.

    A ROW IS THE WORST POSSIBLE PACKING, AND THAT IS WHAT THIS USED TO DO
    --------------------------------------------------------------------
    rulebook-compliance.md argues three 1046 mm airframes fit the 12 ft pad
    "3 per row", and this function implemented exactly that: 1.22 m spacing,
    0.17 m of clearance. It does not survive contact with a real landing. In
    SITL, three aircraft aiming at those slots came to rest 0.83 m apart --
    an overlap, because the geometry allowed 0.17 m of error and touchdown
    dispersion is around half a metre.

    Centres must stay half an airframe inside the pad edge, so they live in a
    square of side (pad - footprint) = 2.614 m. Putting three of them in a ROW
    across that square gives 1.31 m at best. Putting them at its CORNERS gives
    the full 2.614 m -- twice the separation, on the same pad, for free:

        row of 3, full width      1.307 m   ->  overlaps under dispersion
        3 corners                 2.614 m   ->  1.61 m apart at worst case

    The corners also help in the air: the aircraft hold and descend over points
    2.6 m apart instead of 1.2 m, which is what lifts the stacked-over-the-pad
    separation back above the 5 m minimum when combined with the RTL_ALT band.
    """
    if n < 1:
        raise ValueError("need at least one drone")
    if n > 4:
        raise ValueError(
            f"{n} aircraft cannot be placed on one {pad_side_m:.2f} m pad with "
            f"useful separation; four corners is the limit")

    half = (pad_side_m - AIRFRAME_FOOTPRINT_M) / 2.0
    if half <= 0:
        raise ValueError(
            f"a {AIRFRAME_FOOTPRINT_M:.3f} m airframe does not fit inside a "
            f"{pad_side_m:.2f} m pad at all")

    # Corner-first, because the corners of the usable square are the furthest
    # apart any set of points on it can be.
    layouts = {
        1: [(0.0, 0.0)],
        2: [(-half, -half), (half, half)],
        3: [(-half, -half), (half, -half), (0.0, half)],
        4: [(-half, -half), (half, -half), (half, half), (-half, half)],
    }
    local = layouts[n]

    if n > 1:
        worst = min(math.dist(a, b)
                    for i, a in enumerate(local) for b in local[i + 1:])
        need = AIRFRAME_FOOTPRINT_M + 2 * dispersion_m
        if worst < need:
            raise ValueError(
                f"{n} aircraft on a {pad_side_m:.2f} m pad give {worst:.2f} m "
                f"between slots. A {AIRFRAME_FOOTPRINT_M:.3f} m airframe with "
                f"{dispersion_m:.2f} m touchdown dispersion each needs "
                f"{need:.2f} m, or they can touch down overlapping. Rule 8.10 "
                f"requires landing inside the pad -- this needs a decision "
                f"(precision landing, one at a time, or land off-pad), not a "
                f"tighter number.")

    # Frame is x=east, y=north; rotate the layout to the pad's orientation.
    b = math.radians(bearing_deg - 90.0)
    cb, sb = math.cos(b), math.sin(b)
    hx, hy = frame.to_xy(home[0], home[1])
    return [frame.to_latlon(hx + (lx * cb - ly * sb), hy + (lx * sb + ly * cb))
            for lx, ly in local]


def _repeat(lines, passes: int):
    """Fly the strip `passes` times, reversing direction each time.

    WHY A SECOND PASS, AND WHY REVERSED
    Not for coverage -- one pass already covers the strip with 30 % sidelap and
    no gaps. It is for the geotag.

    Boresight misalignment is SYSTEMATIC: it puts the survivor in the same wrong
    place, in the aircraft's own frame, on every frame of a pass. Averaging more
    frames from one heading cannot remove it, which is why the error budget
    carries it at 0.16 m after fusion. Fly the same ground on the OPPOSITE
    heading and the along-track component of that bias flips sign, so averaging
    the two passes cancels it instead of accumulating it.

    A second pass also doubles the frames on every survivor and gives the
    detector a second look from a different sun angle and background.

    It is not free: it doubles the sweep. plan_mission reports the sweep time so
    the endurance reserve can be checked against it -- for the full competition
    area two passes will not fit one battery, and that is a real constraint, not
    a rounding error.

    The reversal keeps the path continuous: pass 1 ends at the far end of the
    last transect, and pass 2 begins there.
    """
    if passes < 1:
        raise ValueError("passes must be >= 1")
    out = list(lines)
    for p in range(1, passes):
        # An entry is normally the two ends of a transect, but carries extra
        # detour waypoints when the sweep had to route around a concave notch.
        # Reverse whatever length it is rather than unpacking two.
        out += [list(reversed(ln)) for ln in reversed(out[-len(lines):])]
    return out


@dataclass
class DronePlan:
    drone_id: int
    region: list[tuple[float, float]]
    lines: list[list[tuple[float, float]]]
    altitude_m: float
    transit_alt_m: float = 0.0
    pad_slot: tuple[float, float] = (0.0, 0.0)
    items: list[mis.Item] = field(default_factory=list)
    area_ha: float = 0.0
    path_m: float = 0.0
    sweep_s: float = 0.0
    problems: list[str] = field(default_factory=list)

    @property
    def wpl(self) -> str:
        return mis.to_wpl(self.items)


@dataclass
class MissionPlan:
    drones: list[DronePlan]
    balance: dict
    total_ha: float
    longest_sweep_s: float

    def summary(self) -> str:
        out = [f"{self.total_ha:.2f} ha across {len(self.drones)} drones, "
               f"imbalance {self.balance['max_imbalance']:.2%}"]
        for d in self.drones:
            out.append(
                f"  drone {d.drone_id}: {d.area_ha:.2f} ha · {len(d.lines)} lines "
                f"· {d.path_m:,.0f} m · {d.sweep_s:.0f} s · search {d.altitude_m:.0f} m "
                f"· transit {d.transit_alt_m:.0f} m"
                + (f"  ⚠ {len(d.problems)} problems" if d.problems else "")
            )
        out.append(f"  longest sweep: {self.longest_sweep_s:.0f} s")
        return "\n".join(out)


def plan_mission(boundary: list[tuple[float, float]], home: tuple[float, float],
                 n_drones: int = 3, altitude_m: float = 40.0,
                 hfov_deg: float = 63.3, sidelap: float = 0.30,
                 speed_ms: float = 8.0, alt_stagger_m: float = 5.0,
                 # 20/25/30 under a 40 m deck. Was 25/30/35, which left the top
                 # band 5 m below aircraft that were still searching.
                 transit_alt_m: float = 20.0,
                 pad_bearing_deg: float = 90.0,
                 takeoff_stagger_s: float = 15.0,
                 passes: int = 2,
                 turn_s: float = 6.0) -> MissionPlan:
    """Plan the whole mission. Deterministic: same input, same output, always.

    Defaults follow the project design point: 40 m recommended search altitude,
    63.3 deg HFOV derived from the sensor (NOT the 70 deg hardcoded in the old
    sweep planner), 30 % sidelap, 8 m/s groundspeed.
    """
    frame = Frame.from_points(boundary)
    strips = split(boundary, n_drones, frame=frame)
    bal = report(boundary, strips, frame=frame)

    # Refuse a plan whose own stratification does not separate anything. The
    # top transit band under the search deck is the whole basis for saying
    # aircraft cannot conflict while transiting, and it is easy to erode by
    # nudging an altitude default.
    top_transit = transit_alt_m + (n_drones - 1) * alt_stagger_m
    if altitude_m - top_transit < DECK_CLEARANCE_M:
        raise ValueError(
            f"transit band tops out at {top_transit:.0f} m under a "
            f"{altitude_m:.0f} m search deck — {altitude_m - top_transit:.0f} m "
            f"of clearance, against the {DECK_CLEARANCE_M:.0f} m minimum. A "
            f"transiting aircraft would cross directly under a searching one. "
            f"Lower transit_alt_m, reduce alt_stagger_m, or raise altitude_m.")

    # One slot per drone across the shared pad, so RTL does not send all three
    # to the same point. Drone i+1 gets slot i, and must be ARMED there.
    slots = pad_slots(home, len(strips), frame, bearing_deg=pad_bearing_deg)

    drones: list[DronePlan] = []
    for i, strip in enumerate(strips):
        # SEARCH altitude is identical for every drone, so every drone gets the
        # same GSD and the same detection recall. See the module docstring.
        alt = altitude_m
        # TRANSIT altitude is staggered, because that is where aircraft leave
        # their strips and could actually conflict.
        transit = transit_alt_m + i * alt_stagger_m

        # FINISH THE SWEEP NEAREST HOME.
        #
        # A sweep ends at the opposite end of the strip from where it started
        # when the transect count is odd, and the same end when it is even. So
        # which end you start at decides where the aircraft is standing when the
        # sweep completes -- which is the moment it has the least battery left.
        #
        # This used to be `start_far_side=bool(i % 2)`, keyed on the drone
        # index. That is arbitrary: it made drone 2 finish 115 m from the pad
        # and drones 1 and 3 finish 514 m and 540 m away, on the lowest state of
        # charge of the flight. Two out of three aircraft were as far from home
        # as they would ever be at exactly the wrong moment.
        #
        # `start_far_side` alone cannot do this. It reverses which COLUMN the
        # sweep begins at, not which END of the strip: with an odd transect
        # count the aircraft finishes at the same end either way. The other
        # degree of freedom is the along-track direction, and reversing every
        # segment flips both ends while preserving boustrophedon continuity --
        # each line still starts where the previous one finished.
        #
        # Four combinations, pick the one that ends nearest the pad. Enumerating
        # beats reasoning about parity, which is what got this wrong before.
        slot_xy = frame.to_xy(*slots[i])
        best = None
        for far in (False, True):
            # Clip to the mission boundary as well as the strip. On a concave
            # boundary the equal-area split can overhang the notch, and without
            # this the sweep legs run over excluded ground.
            base = bou.transects(strip, alt, hfov_deg, sidelap, frame=frame,
                                 start_far_side=far, clip_to=boundary)
            if not base:
                continue
            for flip in (False, True):
                cand = [[b, a] for a, b in base] if flip else base
                cand = _repeat(cand, passes)
                d_end = math.dist(slot_xy, frame.to_xy(*cand[-1][-1]))
                if best is None or d_end < best[0]:
                    best = (d_end, cand)
        lines = best[1] if best else []
        # Route the hops LAST, once the sweep order is settled. Doing it any
        # earlier means the flip above reverses entries that already carry
        # detours, putting them on the wrong side of their transect.
        lines = bou.route_legs(lines, boundary, frame=frame)

        items = mis.build(slots[i], lines, alt, speed_ms=speed_ms,
                          takeoff_alt_m=transit, transit_alt_m=transit,
                          takeoff_delay_s=i * takeoff_stagger_s)
        drones.append(DronePlan(
            drone_id=i + 1,
            pad_slot=slots[i],
            region=strip,
            lines=lines,
            altitude_m=alt,
            transit_alt_m=transit,
            items=items,
            area_ha=area(frame.poly_to_xy(strip)) / 10_000.0,
            path_m=bou.path_length_m(lines, frame=frame),
            sweep_s=bou.sweep_time_s(lines, speed_ms, turn_s, frame=frame),
            problems=mis.validate(items),
        ))

    _warn_on_turn_excursion(boundary, drones, frame, alt)

    return MissionPlan(
        drones=drones,
        balance=bal,
        total_ha=bal["total_ha"],
        longest_sweep_s=max(d.sweep_s for d in drones) if drones else 0.0,
    )


def _point_outside_m(poly_xy, pt):
    """Metres outside the polygon; 0.0 if inside."""
    x, y = pt
    c = False
    for i in range(len(poly_xy)):
        x1, y1 = poly_xy[i]
        x2, y2 = poly_xy[(i + 1) % len(poly_xy)]
        if ((y1 > y) != (y2 > y)) and \
           (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1):
            c = not c
    if c:
        return 0.0
    best = float("inf")
    for i in range(len(poly_xy)):
        x1, y1 = poly_xy[i]
        x2, y2 = poly_xy[(i + 1) % len(poly_xy)]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0,
                                             ((x - x1) * dx + (y - y1) * dy) / L2))
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


def _warn_on_turn_excursion(boundary, drones, frame, alt, tol_m: float = 5.0):
    """Warn if a TURN between transects leaves the search area.

    Transects themselves are clipped to the boundary, so the swept ground is
    always inside. The turn between two of them is a straight line, and across
    a concave notch that line can cut the corner -- measured from 9.6 m on a
    shallow notch to 48.7 m on a deep one, scaling with notch depth.

    Closing it properly needs boustrophedon cell decomposition: cover one side
    of the notch completely before crossing. That is a real piece of work, so
    until it exists this at least refuses to let the excursion be a surprise
    discovered from a flight log. Convex boundaries never trigger it.
    """
    bxy = frame.poly_to_xy(boundary)
    worst = 0.0
    for d in drones:
        pts = [frame.to_xy(it.lat, it.lon) for it in d.items
               if abs(it.lat) > 1 and abs(it.alt - alt) < 0.5]
        # transects are even-indexed legs; the odd ones are the turns
        for i in range(1, len(pts) - 1, 2):
            a, b = pts[i], pts[i + 1]
            n = max(2, int(math.dist(a, b) / 5.0))
            for j in range(n + 1):
                t = j / n
                worst = max(worst, _point_outside_m(
                    bxy, (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)))
    if worst > tol_m:
        warnings.warn(
            f"turn legs between transects leave the search area by up to "
            f"{worst:.0f} m. The swept transects are inside; it is the "
            f"straight turn across a concave notch that cuts the corner. "
            f"Verify on the GCS, or use a convex boundary.",
            stacklevel=3,
        )
    return worst
