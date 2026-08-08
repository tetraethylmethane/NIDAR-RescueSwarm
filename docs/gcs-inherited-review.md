# Inherited Ground Station — Review at `5d0a687`

**Historical.** Every blocker below is fixed. This is kept because the reasoning
is worth more than the conclusions: it records *why* an inherited codebase from
a different competition was dangerous here, and what to check if another one is
ever adopted.

Current state: [`../../ground-station/README.md`](../ground-station/README.md).

| Blocker | Fixed in |
|---|---|
| 1 — internet poller every 5 s | NIDAR-GSC `ab8c09d` |
| 2 — single-vehicle by construction | `ab8c09d` backend, `f331e36` client |
| 3 — a controller, not a view | `ab8c09d`, completed `f331e36` |
| Gap — no rule 8.14 displays | `f331e36`, rendered `955ae3f` |

---

## Review of the inherited codebase at commit `5d0a687` — the state that prompted the work

*Historical. Blockers 1 and 3 are fixed as of `ab8c09d`; blocker 2's backend is done.*

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
[`../docs/system-overview.md`](system-overview.md) — that the violation is
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

## Recommendation: one codebase, two deployments

### Why remove the command paths at all

**Not because having them is illegal.** Rule 8.16 penalises the *action* —
"manual waypoint modification… during mission execution" — not the capability. A
ground station full of controls that nobody touches is fully compliant. Any
argument that the rules *require* a command-free GCS is overstated.

The real reason is **accident prevention**, and it is concrete here.
`FlightMap.js:200` inserts a waypoint at `event.latlng` on a map click:

```js
let point = { lat: event.latlng.lat, lng: event.latlng.lng, ...,
              cmd: Commands[props.getters.placementType] }
```

The operator watches that map for eight minutes, under competition pressure,
with jurors present. **One stray click is −50 points** — more than the entire
fast-completion bonus — and it cannot be rehearsed to zero.

Two secondary reasons, both real but weaker:

- **Design Review item 7** (Autonomous Mission Execution, 30 pts): "the GCS
  cannot retask, here is the source" is *verifiable*; "we did not touch it" is a
  promise. Rule 8.6 lets the jury check.
- **Pre-Flight Inspection** is Pass/Fail with one retry. Demonstrable absence is
  easier to pass than arguing intent.

### It is not "read-only"

Safety abort and emergency recall are explicitly permitted (8.16, MB §3) and
required (8.19). The correct framing is **no mission-altering commands** — abort
and recall stay.

### Do NOT build two ground stations

An earlier version of this recommendation said to build a separate mission GCS.
**That is the wrong answer.** In a 21-week programme with an 8-week flight window
you would develop and test against the dev build and compete on the less-tested
one — the classic "worked in testing" failure, and a worse risk than the one it
solves.

**Instead: one codebase, one client, one test suite.** Put the command endpoints
in a server module that the mission deployment does not load. Same map, same
telemetry, same UI flown behind all season — the mission build simply has no route
that can insert a waypoint.

| | Dev deployment | Mission deployment |
|---|---|---|
| Map, tiles, telemetry, video | ✔ | ✔ |
| Abort / recall | ✔ | ✔ *(required by 8.19)* |
| Waypoint insert, mode change, arm, params, servos | ✔ | **module not loaded** |

That satisfies SYS-20 by source review, carries no divergence risk, and is about
a day of architecture rather than weeks of duplication.

**Until this is done, treat SYS-20 and SYS-23 as failing**, not pending.
