# ground-station

Read-only mission view, telemetry ingest, video, replay.

**Status: an existing codebase has been identified but not adopted.**
[`tetraethylmethane/NIDAR-GSC`](https://github.com/tetraethylmethane/NIDAR-GSC)
— "Team Sammpaati's Custom Ground Station", React client + Flask/DroneKit server.

Requirements this directory must satisfy: **SYS-20, SYS-25, SYS-26, SYS-27** — see
[`../docs/requirements/requirements-baseline.md`](../docs/requirements/requirements-baseline.md).

---

## Review of NIDAR-GSC, at commit `5d0a687`

It is a competent single-vehicle MAVLink ground station with clear AUVSI SUAS
lineage — ODLC image handling, airdrop/flight boundary icons, a Submissions tab,
UGV support. **That lineage is the problem: it was built for a different
competition with different rules.**

### 🔴 Blocker 1 — it polls the internet every 5 seconds

`client/src/components/FlightMap.js`:

```js
const checkInternet = () => {
    if (navigator.onLine) {
        fetch("https://g.co", { mode: "no-cors" }).then(() => {
            tileRef.current.setUrl("https://server.arcgisonline.com/.../{z}/{y}/{x}")
        }).catch(() => { tileRef.current.setUrl("/map/{z}/{x}/{y}.png") })
    } else { tileRef.current.setUrl("/map/{z}/{x}/{y}.png") }
}
useInterval(5000, checkInternet)
```

It probes `g.co` on a 5-second timer and **switches to online ArcGIS tiles
whenever connectivity exists**.

Rule **8.4** prohibits internet connectivity during mission execution outright.
Rule **8.17** prohibits relying on any external network. MB §5 makes use of an
external network interface "a violation or manual/external intervention". And
rule **8.6** gives the jury the right to inspect source configuration.

**This fails SYS-23 as written.** The fix is two lines — delete `checkInternet`
and hardcode `/map/{z}/{x}/{y}.png` — but it has to be found *before* the
Pre-Flight Inspection, which is Pass/Fail with a single retry.

Offline tiles are already supported: `server/utils/slippy_map_getter.py`
pre-downloads into `client/public/map`. **The capability is there; the default
behaviour is wrong.**

### 🔴 Blocker 2 — single-vehicle by construction

`grep -rn "sysid\|target_system\|vehicle_id"` across client and server returns
**nothing**. `apps/uav.py` and `handlers/uav.py` are singular, and the server
holds one vehicle object.

Rule **8.13** requires all drones through a single GCS and a unified operator
interface. That is worth **50 binary points**, and multi-drone collaborative
execution is a further **50**. Both are all-or-nothing.

This is not a patch. It is the central data-model assumption.

### 🔴 Blocker 3 — it is a controller, not a view

The command surface in `server/handlers/uav.py` includes:

`arm()` · `disarm()` · `set_flight_mode()` · **`insert_command(command, lat, lon, alt)`** ·
**`jump_to_command()`** · `clear_commands()` · `write_commands()` · `set_param()` ·
`set_params()` · `servos()` · `set_home()` · `calibrate()` · `restart()`

`insert_command` and `jump_to_command` are *precisely* the actions rule **8.16**
defines as manual intervention — "manual waypoint modification, flight-path
correction, payload-release command… or mission replanning during execution" —
at **−50 points each**.

**SYS-20 requires the GCS be "incapable of originating a retask, waypoint change
or drop command *by construction*", verified by source review.** This codebase is
the opposite of that requirement. The architecture claim in
[`../docs/system-overview.md`](../docs/system-overview.md) — that the violation is
"structurally impossible rather than avoided by discipline" — **is not currently
true of any code we have.**

### 🟡 Gap — none of rule 8.14's mission displays exist

Searching client and server for `survivor`, `geotag`, `delivery`, `detect`
returns **zero hits**. Rule 8.14 mandates the GCS display, at minimum:

| 8.14 requires | Present? |
|---|---|
| Mission status | partial |
| Live camera feed from **each** drone | single MJPEG stream only |
| Position of each drone | single vehicle |
| **Assigned search area or task per drone** | ✗ |
| **Detected and geotagged survivor locations** | ✗ |
| **Survival-kit delivery status** | ✗ |
| Communication and system health | partial |
| Consolidated mission progress | ✗ |

The ODLC image handling is AUVSI's analogue of survivor detection, but it talks to
an external imaging service over HTTP and is not wired to anything NIDAR needs.

### 🟢 Genuinely worth keeping

- **`slippy_map_getter.py`** — offline tile pre-download. Directly serves the
  no-external-network rule and is a solved problem we would otherwise repeat.
- Leaflet map with polygon, geofence, marker and waypoint drawing tools.
- MAVLink/DroneKit telemetry plumbing and the parameter UI.
- The React component library (`UIElements`, `Containers`, theming).
- SITL scripts — `scripts/run-sim.sh`, `sim.parm`, `sim_locations.txt`.

---

## Recommendation: two builds from one codebase

Do not try to make one ground station satisfy both jobs, and do not throw this
away.

**1. Test GCS — adopt NIDAR-GSC largely as-is.**
During P3–P6 you *want* arm/disarm, mode changes and manual waypoints; that is how
flight testing works. Fix the internet poller (it will otherwise leak into habits
and demos) and use it as the development ground station.

**2. Mission GCS — build read-only, sharing components.**
Reuse the map, tiles, telemetry ingest and component library. Omit every command
path at the *server* level, so SYS-20 can be verified by source review rather than
asserted. Add the 8.14 mission displays and multi-vehicle support, which are new
work regardless.

The shared layer is the map and telemetry; the divergence is the command surface.
Splitting there costs little and makes SYS-20 provable.

**Until this is done, treat SYS-20 and SYS-23 as failing**, not pending.
