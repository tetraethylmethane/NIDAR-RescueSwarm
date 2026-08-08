"""Turn transects into an ArduPilot mission — implementation-plan.md §1.1.

This is the module that removes the search-phase flight code entirely. The GCS
partitions the boundary, generates the lawnmower, and uploads it as an AUTO
mission during setup. The aircraft then flies the search with no operator input
and no custom autonomy: AUTO mode is a lawnmower executor already.

Uploading a mission during setup is explicitly permitted — MB §3 lists
mission-file loading as one of four allowed operator actions — and the aircraft
receives nothing further, which is what rule 8.16 requires.

OUTPUT FORMAT is `QGC WPL 110`, the plain-text waypoint file ArduPilot, Mission
Planner, MAVProxy and QGroundControl all read. Text on purpose: it can be
diffed, reviewed and archived with the flight log, and a jury can read it.

    index  current  frame  command  p1 p2 p3 p4  x(lat) y(lon) z(alt)  autocontinue

`frame` 3 is MAV_FRAME_GLOBAL_RELATIVE_ALT — altitude above the HOME point, not
above sea level. Getting this wrong by using frame 0 would fly the mission at
the field's AMSL elevation above the ground, which at 300 m elevation means
360 m AGL instead of 60.
"""
from __future__ import annotations

from dataclasses import dataclass

# MAVLink command IDs
NAV_WAYPOINT = 16
NAV_LOITER_TIME = 19
NAV_RETURN_TO_LAUNCH = 20
NAV_TAKEOFF = 22
DO_CHANGE_SPEED = 178

FRAME_GLOBAL_RELATIVE_ALT = 3
FRAME_MISSION = 2               # for DO_ commands, which have no position


@dataclass
class Item:
    seq: int
    command: int
    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0
    p1: float = 0.0
    p2: float = 0.0
    p3: float = 0.0
    p4: float = 0.0
    frame: int = FRAME_GLOBAL_RELATIVE_ALT
    current: int = 0
    autocontinue: int = 1

    def to_wpl(self) -> str:
        return (
            f"{self.seq}\t{self.current}\t{self.frame}\t{self.command}\t"
            f"{self.p1:.8f}\t{self.p2:.8f}\t{self.p3:.8f}\t{self.p4:.8f}\t"
            f"{self.lat:.8f}\t{self.lon:.8f}\t{self.alt:.6f}\t{self.autocontinue}"
        )


def build(home: tuple[float, float], lines, altitude_m: float,
          speed_ms: float | None = None, takeoff_alt_m: float | None = None,
          rtl: bool = True) -> list[Item]:
    """Assemble a full AUTO mission for one drone.

    home         (lat, lon) of the launch pad — item 0, as ArduPilot expects
    lines        transect segments from boustrophedon.transects()
    altitude_m   search altitude AGL
    speed_ms     optional DO_CHANGE_SPEED; the sizing model holds constant
                 GROUNDSPEED during the sweep, which is what makes sweep time
                 wind-independent (sizing §9.2)
    """
    if not lines:
        raise ValueError("no transects — nothing to fly")

    items: list[Item] = []
    seq = 0

    # Item 0 is HOME. ArduPilot always treats seq 0 as home and does not fly to
    # it; omitting it shifts every subsequent index by one.
    items.append(Item(seq, NAV_WAYPOINT, lat=home[0], lon=home[1], alt=0.0,
                      current=1))
    seq += 1

    items.append(Item(seq, NAV_TAKEOFF, lat=0.0, lon=0.0,
                      alt=takeoff_alt_m if takeoff_alt_m else altitude_m))
    seq += 1

    if speed_ms is not None:
        # p1=1 -> groundspeed, p2 = m/s, p3 = throttle (-1 = no change)
        items.append(Item(seq, DO_CHANGE_SPEED, frame=FRAME_MISSION,
                          p1=1, p2=speed_ms, p3=-1))
        seq += 1

    for a, b in lines:
        items.append(Item(seq, NAV_WAYPOINT, lat=a[0], lon=a[1], alt=altitude_m))
        seq += 1
        items.append(Item(seq, NAV_WAYPOINT, lat=b[0], lon=b[1], alt=altitude_m))
        seq += 1

    if rtl:
        items.append(Item(seq, NAV_RETURN_TO_LAUNCH, frame=FRAME_MISSION))
        seq += 1

    return items


def to_wpl(items: list[Item]) -> str:
    """Serialise to the QGC WPL 110 text format."""
    return "\n".join(["QGC WPL 110", *(i.to_wpl() for i in items)]) + "\n"


def parse_wpl(text: str) -> list[Item]:
    """Read a QGC WPL 110 file back. Used by tests to prove a round trip."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines or not lines[0].startswith("QGC WPL"):
        raise ValueError("not a QGC WPL file")
    out = []
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) < 12:
            raise ValueError(f"malformed waypoint line: {ln!r}")
        out.append(Item(
            seq=int(f[0]), current=int(f[1]), frame=int(f[2]), command=int(f[3]),
            p1=float(f[4]), p2=float(f[5]), p3=float(f[6]), p4=float(f[7]),
            lat=float(f[8]), lon=float(f[9]), alt=float(f[10]),
            autocontinue=int(f[11]),
        ))
    return out


def validate(items: list[Item], max_alt_m: float = 120.0) -> list[str]:
    """Pre-upload checks. Returns problems; empty means the mission is sane."""
    problems: list[str] = []
    if not items:
        return ["mission is empty"]

    if items[0].seq != 0 or items[0].current != 1:
        problems.append("item 0 must be HOME with current=1")

    seqs = [i.seq for i in items]
    if seqs != list(range(len(items))):
        problems.append("sequence numbers are not contiguous from 0")

    if not any(i.command == NAV_TAKEOFF for i in items):
        problems.append("no NAV_TAKEOFF — the aircraft will not climb")

    nav = [i for i in items if i.command == NAV_WAYPOINT and i.seq > 0]
    if not nav:
        problems.append("no navigation waypoints")

    for i in nav:
        if i.frame != FRAME_GLOBAL_RELATIVE_ALT:
            problems.append(
                f"item {i.seq} uses frame {i.frame}; waypoints must be frame 3 "
                f"(relative alt), or the mission flies at AMSL"
            )
        if not -90 <= i.lat <= 90 or not -180 <= i.lon <= 180:
            problems.append(f"item {i.seq} has an out-of-range coordinate")
        if i.lat == 0.0 and i.lon == 0.0:
            problems.append(f"item {i.seq} is at null island (0, 0)")
        if i.alt <= 0:
            problems.append(f"item {i.seq} has altitude {i.alt} m")
        elif i.alt > max_alt_m:
            problems.append(f"item {i.seq} altitude {i.alt} m exceeds "
                            f"{max_alt_m} m")
    return problems
