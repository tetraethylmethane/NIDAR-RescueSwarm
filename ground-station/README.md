# ground-station

The **Drikr NIDAR Ground Station** — mission view, telemetry, video, abort.

Code lives in [`tetraethylmethane/NIDAR-GSC`](https://github.com/tetraethylmethane/NIDAR-GSC);
this directory holds the engineering record. Mission-build rules that must not be
undone are in [`MISSION.md`](https://github.com/tetraethylmethane/NIDAR-GSC/blob/main/MISSION.md).

Requirements: **SYS-20, SYS-23, SYS-25, SYS-26, SYS-27** — see
[`../docs/requirements/requirements-baseline.md`](../docs/requirements/requirements-baseline.md).

```bash
cd server && python -m pytest mission_tests -q     # 89 tests
./scripts/check-no-network.sh                      # rule 8.4 guard
python scripts/sim_mission.py --speed 8            # 3 drones, no aircraft
```

---

## Status

| Requirement | State |
|---|---|
| No external network (SYS-23, rule 8.4) | ✅ Poller removed, CI-guarded |
| No mission-altering commands (SYS-20, rule 8.16) | ✅ `MISSION_MODE` split + 403 on 31 legacy routes |
| Single unified interface, 3 drones (SYS-25, rule 8.13) | ✅ MAVLink ingest, 3 SYSIDs → one `Fleet` |
| All eight rule 8.14 displays (SYS-26) | ✅ Built **and rendered** |
| Three video feeds (SYS-27, rule 8.14) | ✅ Built · ⚠ never run |
| Abort and recall (rule 8.19) | ✅ Transmitting · ⚠ **no radio attached** |

---

## What is left

### Nothing has run as a system

Everything is unit-tested. **None of it has been executed end to end.**

- **No React component has ever rendered.** The client *builds* — that proves it
  compiles, not that it works. No browser has loaded the page.
- **MediaMTX has never been run.** The video path is unproven.
- **Never connected to a real autopilot, or even SITL.** `mavlink_ingest` is
  tested against synthetic pymavlink messages.
- **The safety radio is not connected**, which abort correctly reports as
  `NO_RADIO` rather than pretending otherwise.

### Three concrete gaps

**1. The server cannot start on Python 3.10+.**
`app.py` → `groundstation.py` → `handlers/uav.py` → `dronekit`, and DroneKit does
`collections.MutableMapping`, removed in 3.10. The smoke test stubs it; the real
server will not boot on a modern interpreter.

The fix is better than pinning Python 3.9: **in mission mode the legacy
`UAVHandler` is redundant**, because `mavlink_ingest` already provides telemetry
through pymavlink. Skipping `GroundStation` in mission mode drops DroneKit from
the mission path entirely.

**2. No offline tiles are cached.**
`client/public/map` does not exist, so with the network down the map is **blank**.
`slippy_map_getter.py` solves this, but it has to be run **weeks ahead** over a
generous region around the venue — the mission area is not known until the KML
arrives during setup.

**3. Dev UI still ships in the mission build.**
`Servo`, `FlightPlanToolbar` and `Params` still render. The server 403s them so no
rule is broken, but the "one stray click" argument that removed the map's
waypoint insert applies equally, and controls that silently do nothing are their
own hazard. Gate them on `mission_mode` like the arm buttons.

### Needs hardware, versus does not

| Needs hardware | Does not |
|---|---|
| Safety radio bridge + aircraft receiver | Dropping DroneKit from the mission path |
| Real autopilot / SITL telemetry | Offline tile pre-cache |
| Video end to end through MediaMTX | Gating the dev UI on mission mode |
| Field validation | Component tests · a full-stack local run |

**The right next step is a full-stack local run** — `MISSION_MODE=1 python app.py`,
`npm start` and `sim_mission.py` together, and actually look at the page. That is
the first time this exists as a system rather than as parts, and it needs no
aircraft.

---

## How it works

**Two ingest paths, deliberately separate.** MAVLink via mavlink-router carries
position, mode, battery and GNSS fix. A 5 Hz JSON document over the mesh carries
region, task, detections and deliveries — MAVLink has no message for *"survivor
at lat/lon, confidence 0.91, confirmed over 7 frames, RTK-fixed"*, and bending
`NAMED_VALUE_FLOAT` into that shape is a trap.

**Mission mode is structural, not a flag.** `MISSION_MODE=1` (the default, so the
safe build is the default) never imports the command blueprint, and refuses every
state-changing method on the legacy `/uav` routes. A flag can be flipped by a
config file; an unimported module cannot be reached.

**Survivor dedup prefers fix quality over recency.** Two aircraft can see the same
survivor, and a later `RTK_FLOAT` tag is metres worse than an earlier
`RTK_FIXED` one. Ranking is fix → frames → confidence; confidence is last because
it is worth nothing in position terms.

**Abort is the secondary path.** The primary is `RC7_OPTION=4` driving the flight
controller directly, which survives a hung companion — and a hung companion is a
reason to abort. This layer adds addressing, acknowledgement and an audit trail.

---

## Verified without hardware

`sim_mission.py` flies three synthetic drones including the awkward cases — a
drone dropping off the mesh, a survivor re-tagged with a better fix by a
different aircraft, and a tag taken without RTK. Against a real `Fleet` and a
real socket:

```
datagrams accepted : 5287      rejected : 0
survivors found    : 6         kits delivered : 6
survivor 3 fix     : RTK_FIXED (drone 3)   ← dedup preferred fix over recency
warnings           : survivor 6 tagged without RTK (3D)
```

Both safety guards were verified to **fail** when the fault is reintroduced: a
command route forced into the mission build fails three tests, and a restored
ArcGIS URL fails the network check. A guard that cannot fail is not a guard.

---

## History

The inherited codebase and the three blockers it shipped with are archived in
[`../docs/gcs-inherited-review.md`](../docs/gcs-inherited-review.md). Worth
reading before adopting any other codebase written for a different competition.
