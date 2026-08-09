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
NAV_DELAY = 93                  # MAV_CMD_NAV_DELAY, p1 = seconds
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
          rtl: bool = True, transit_alt_m: float | None = None,
          takeoff_delay_s: float = 0.0) -> list[Item]:
    """Assemble a full AUTO mission for one drone.

    home         (lat, lon) of this drone's PAD SLOT — item 0, as ArduPilot
                 expects. Not the shared pad centre: see plan.pad_slots().
    lines        transect segments from boustrophedon.transects()
    altitude_m   search altitude AGL
    speed_ms     optional DO_CHANGE_SPEED; the sizing model holds constant
                 GROUNDSPEED during the sweep, which is what makes sweep time
                 wind-independent (sizing §9.2)
    transit_alt_m  the drone's staggered ingress/egress altitude. Flown as real
                 waypoints — see below.

    THE TRANSIT CORRIDOR IS FLOWN, NOT JUST TAKEN OFF TO
    -----------------------------------------------------
    plan.py stratifies transit altitude per drone (25/30/35 m) and keeps search
    common at 40 m, on the argument that aircraft only conflict where they leave
    their strips. That argument was sound and the mission did not implement it:
    `takeoff_alt_m` set the NAV_TAKEOFF altitude and the very next item was the
    first transect at `altitude_m`, so the aircraft climbed to 25 m and then
    flew straight at the search deck, crossing other drones' strips somewhere on
    a diagonal between the two. The stagger existed in the docstring and the
    plan summary, and nowhere in the flight path.

    So ingress is now: takeoff -> fly to above the first transect AT TRANSIT
    ALTITUDE -> climb vertically, inside its own strip, to the search deck. And
    egress is the reverse: descend in place to transit altitude before RTL. Every
    metre flown outside the drone's own strip is now flown in its own altitude
    band, which is what the stagger was for.
    """
    if not lines:
        raise ValueError("no transects — nothing to fly")

    # Falling back to the search altitude would silently put every drone in the
    # same band during transit -- the exact defect this parameter exists to fix.
    transit = transit_alt_m if transit_alt_m else takeoff_alt_m
    if not transit:
        transit = altitude_m

    items: list[Item] = []
    seq = 0

    # Item 0 is HOME. ArduPilot always treats seq 0 as home and does not fly to
    # it; omitting it shifts every subsequent index by one.
    items.append(Item(seq, NAV_WAYPOINT, lat=home[0], lon=home[1], alt=0.0,
                      current=1))
    seq += 1

    # SEQUENCE THE LAUNCHES.
    #
    # RTL_LOIT_TIME sequences the arrivals; nothing sequenced the departures.
    # Three aircraft leaving slots 1.22 m apart at the same instant were
    # measured 1.3 m from each other at 2-3 m altitude in SITL -- inside the
    # 1.046 m airframe plus its own rotor wash.
    #
    # NAV_DELAY before the takeoff, staggered per drone, is deterministic and
    # lives in the mission file, so it does not depend on an operator pressing
    # three buttons at the right spacing during a five-minute setup window.
    #
    # p1 = seconds to wait; -1 in the hh/mm/ss fields means "relative delay",
    # not "wait until this time of day".
    if takeoff_delay_s > 0:
        items.append(Item(seq, NAV_DELAY, frame=FRAME_MISSION,
                          p1=takeoff_delay_s, p2=-1, p3=-1, p4=-1))
        seq += 1

    items.append(Item(seq, NAV_TAKEOFF, lat=0.0, lon=0.0,
                      alt=takeoff_alt_m if takeoff_alt_m else altitude_m))
    seq += 1

    if speed_ms is not None:
        # p1=1 -> groundspeed, p2 = m/s, p3 = throttle (-1 = no change)
        items.append(Item(seq, DO_CHANGE_SPEED, frame=FRAME_MISSION,
                          p1=1, p2=speed_ms, p3=-1))
        seq += 1

    # INGRESS at the staggered altitude, to a point above the sweep start.
    first = lines[0][0]
    items.append(Item(seq, NAV_WAYPOINT, lat=first[0], lon=first[1],
                      alt=transit))
    seq += 1

    for a, b in lines:
        items.append(Item(seq, NAV_WAYPOINT, lat=a[0], lon=a[1], alt=altitude_m))
        seq += 1
        items.append(Item(seq, NAV_WAYPOINT, lat=b[0], lon=b[1], alt=altitude_m))
        seq += 1

    # EGRESS: drop back into the transit band before going anywhere, so the
    # aircraft leaves its strip at its own altitude rather than the search deck.
    last = lines[-1][1]
    items.append(Item(seq, NAV_WAYPOINT, lat=last[0], lon=last[1], alt=transit))
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
