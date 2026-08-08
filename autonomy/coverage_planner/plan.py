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
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import boustrophedon as bou
from . import mission as mis
from .geo import Frame, area
from .partition import report, split


@dataclass
class DronePlan:
    drone_id: int
    region: list[tuple[float, float]]
    lines: list[list[tuple[float, float]]]
    altitude_m: float
    transit_alt_m: float = 0.0
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
                 transit_alt_m: float = 25.0,
                 turn_s: float = 6.0) -> MissionPlan:
    """Plan the whole mission. Deterministic: same input, same output, always.

    Defaults follow the project design point: 40 m recommended search altitude,
    63.3 deg HFOV derived from the sensor (NOT the 70 deg hardcoded in the old
    sweep planner), 30 % sidelap, 8 m/s groundspeed.
    """
    frame = Frame.from_points(boundary)
    strips = split(boundary, n_drones, frame=frame)
    bal = report(boundary, strips, frame=frame)

    drones: list[DronePlan] = []
    for i, strip in enumerate(strips):
        # SEARCH altitude is identical for every drone, so every drone gets the
        # same GSD and the same detection recall. See the module docstring.
        alt = altitude_m
        # TRANSIT altitude is staggered, because that is where aircraft leave
        # their strips and could actually conflict.
        transit = transit_alt_m + i * alt_stagger_m
        lines = bou.transects(strip, alt, hfov_deg, sidelap, frame=frame,
                              start_far_side=bool(i % 2))
        items = mis.build(home, lines, alt, speed_ms=speed_ms,
                          takeoff_alt_m=transit)
        drones.append(DronePlan(
            drone_id=i + 1,
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
