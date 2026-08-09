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


def pad_slots(home: tuple[float, float], n: int, frame: Frame,
              bearing_deg: float = 90.0,
              pad_side_m: float = PAD_SIDE_M) -> list[tuple[float, float]]:
    """N landing points in a row across the shared pad, centred on `home`.

    Returned in drone order, so drone 1 gets slot 0. The aircraft must be placed
    on -- and armed on -- its own slot, because ArduPilot takes HOME from the
    arming position and RTL returns there regardless of what item 0 says.

    Spacing is the pad divided by N, which for the 3-drone case is 1.22 m
    against a 1046 mm airframe: about 17 cm of rotor clearance. That is enough
    to park on and nowhere near enough to land on simultaneously, which is why
    the descents are sequenced rather than merely separated.
    """
    if n < 1:
        raise ValueError("need at least one drone")
    spacing = pad_side_m / n
    if n > 1 and spacing < AIRFRAME_FOOTPRINT_M:
        raise ValueError(
            f"{n} aircraft at {spacing:.2f} m spacing do not fit on a "
            f"{pad_side_m:.2f} m pad with a {AIRFRAME_FOOTPRINT_M:.3f} m "
            f"airframe -- rule 8.10 needs take-off and landing inside the pad")

    # Frame is x=east, y=north, so a bearing offset is (sin, cos) in that order.
    b = math.radians(bearing_deg)
    hx, hy = frame.to_xy(home[0], home[1])
    out = []
    for i in range(n):
        off = (i - (n - 1) / 2.0) * spacing
        out.append(frame.to_latlon(hx + off * math.sin(b),
                                   hy + off * math.cos(b)))
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
            base = bou.transects(strip, alt, hfov_deg, sidelap, frame=frame,
                                 start_far_side=far)
            if not base:
                continue
            for flip in (False, True):
                cand = [[b, a] for a, b in base] if flip else base
                d_end = math.dist(slot_xy, frame.to_xy(*cand[-1][1]))
                if best is None or d_end < best[0]:
                    best = (d_end, cand)
        lines = best[1] if best else []

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

    return MissionPlan(
        drones=drones,
        balance=bal,
        total_ha=bal["total_ha"],
        longest_sweep_s=max(d.sweep_s for d in drones) if drones else 0.0,
    )
