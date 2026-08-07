# Ground Station — Plan to Mission-Ready

What has to be true for the GCS to fly the Final Mission, in what order, and what
to reuse rather than rebuild.

**Owner:** Track C (2 people), who also own the coverage planner, task allocation
and SITL. **Scope control matters more than elegance here.**

---

## 1. What the GCS is worth

| | Points | How the GCS is involved |
|---|--:|---|
| Single GCS / unified interface (4D-4) | **50** | Binary. All three drones, one interface. |
| Multi-drone collaborative execution (4D-3) | **50** | Binary. Area allocation and task distribution must be *visible*. |
| Survivor detection + geotagging (4D-1) | *250* | Not scored by the GCS, but **"correctly geotagged on the GCS / mission map"** is how it is evidenced. No display, no marks. |
| Design Review item 8 | **20** | "GCS, Mission Map & Multi-Drone Status Reporting" |
| Manual input penalty (4D) | −50 each | Every avoidable control is a liability (see [README](README.md)) |

**100 binary points and the evidence path for 250 more.** This is not a
side-project.

---

## 2. Architecture

### 2.1 Two ingest paths, not one

The existing server assumes one MAVLink vehicle. The mission needs two distinct
data streams, and conflating them is the main design error to avoid:

```text
  3 aircraft
      │
      ├── MAVLink (SYSID 1/2/3) ──► mavlink-router ──► GCS: vehicle state
      │                                                 position, attitude, mode,
      │                                                 battery, armed, health
      │
      ├── mission state, 5 Hz UDP ────────────────────► GCS: mission state
      │                                                 assigned region, current task,
      │                                                 detections, delivery status
      │
      └── video, H.264 RTSP ──────► MediaMTX ─────────► browser via WebRTC
```

**Why mission state is not MAVLink.** There is no sensible MAVLink message for
"survivor detected at lat/lon, confidence 0.87, confirmed by 3 frames". Bending
`NAMED_VALUE_FLOAT` or `DEBUG_VECT` into that shape is a trap. Send a small JSON
document per drone at 5 Hz over the mesh.

This is already in the RF budget: `sizing-calculations.md` §12.1 allocates
**25 kbps swarm state + 150 kbps detection metadata** per drone, separate from
telemetry. The plan and the budget agree.

### 2.2 Video: use a gateway, and use H.264

Three simultaneous browser video streams is the one genuinely hard piece.

- **Do not** extend the current MJPEG `<img>` approach. MJPEG at 480p15 is
  roughly 1.5–2 Mbps *per feed*; three would blow the link budget the whole RF
  design is built around.
- **Do** run **MediaMTX** on the GCS box. Drones push RTSP; the browser consumes
  WebRTC. Low latency, no plugins, entirely local, no internet.

**Change H.265 → H.264.** `mission_profile.py` §3 budgeted 3 × 480p15 H.265 at
0.60 Mbps each. Browser H.265 support is patchy and hardware-dependent; H.264 is
universal. At ~0.9 Mbps each that is 2.7 Mbps video + 0.7 non-video = **3.4 Mbps,
about 24 % utilisation at MCS3** — still comfortably inside the margin strategy.
Worth the extra 0.9 Mbps to avoid a codec that may not render on the day.

### 2.3 One codebase, two deployments

Per [README §Recommendation](README.md): command endpoints live in a server
module the mission deployment does not load. Abort and recall stay in both — they
are required by 8.19.

---

## 3. Rule 8.14 compliance, component by component

Rule 8.14 lists eight mandatory displays. Current state and the work each needs:

| # | 8.14 requires | Now | Work |
|---|---|---|---|
| 1 | Mission status | partial | State machine mirror: SETUP → SEARCH → DELIVER → RTH → COMPLETE |
| 2 | **Live camera feed from each drone** | 1 MJPEG | MediaMTX + 3 WebRTC panes (§2.2) |
| 3 | Position of each drone | 1 vehicle | Multi-vehicle model (§4.1) |
| 4 | **Assigned search area / task per drone** | ✗ | Render DARP polygons, colour-coded per drone. **This is also the visible proof for the 50-point collaboration criterion** |
| 5 | **Detected + geotagged survivor locations** | ✗ | Survivor markers with ID, confidence, fix quality (RTK fixed/float) |
| 6 | **Kit delivery status** | ✗ | Per survivor: assigned → en route → released → confirmed |
| 7 | Comms + system health | partial | Per drone: link RSSI, mesh peers, GNSS fix type, battery, sat count |
| 8 | Consolidated mission progress | ✗ | "6/10 found · 4/10 delivered · 4:12 elapsed" |

Items 4, 5 and 6 are new concepts, not refactors. **They are also the three that
carry the points.**

---

## 4. Work breakdown

### 4.1 Multi-vehicle data model — do this first, everything depends on it

The server currently holds one vehicle object. Rekey all state on a drone ID.

- `handlers/uav.py` → a `Fleet` holding `{1: Drone, 2: Drone, 3: Drone}`
- Every API route becomes `/drone/<id>/...`, plus `/fleet/...` for aggregates
- Client state becomes a dict keyed by ID; components take a `droneId` prop
- Connection via **mavlink-router** with three SYSIDs, not three DroneKit
  connections

**Do not defer this.** Retrofitting multi-vehicle after the displays are built
means touching every component twice.

### 4.2 Mission-state ingest

New, small, and independent of the MAVLink path:

```json
{ "drone": 2, "t": 1723459200.4, "state": "SEARCH",
  "region": [[lat,lon], ...],
  "task": {"type": "DELIVER", "survivor": 4},
  "detections": [{"id": 4, "lat": .., "lon": .., "conf": 0.91,
                  "frames": 7, "fix": "RTK_FIXED"}],
  "deliveries": [{"survivor": 4, "state": "RELEASED", "t": ..}] }
```

UDP multicast on the mesh, 5 Hz, last-writer-wins per drone. The GCS merges three
of these into one consolidated view. **Merging is where the "single unified
interface" criterion is actually satisfied.**

### 4.3 KML mission file (SYS-38)

Parse a KML polygon, partition it, render it — **in under 30 s, with no operator
editing**, inside the setup window.

Two known traps:
- **KML is `longitude,latitude[,altitude]`** — longitude first. The most common
  KML bug there is.
- Test against a **real KML export**, not a hand-written one. Real exports carry
  namespaces, nested folders and `<MultiGeometry>`.

### 4.4 Offline tiles (SYS-23)

`slippy_map_getter.py` already works. Two operational points:

- **Delete the internet poller first** (README Blocker 1).
- **The mission area is unknown until the file arrives**, so pre-cache a generous
  region around the venue — not just the search box. Do this weeks ahead, not on
  the day.

### 4.5 Abort and recall

The only two controls in the mission build. Large, unmistakable, confirm-to-fire,
and wired to the 868 MHz safety link rather than the mesh.

---

## 5. Phasing

Against [`../docs/development-plan.md`](../docs/development-plan.md):

| Phase | Weeks | GCS work | Gate |
|---|---|---|---|
| **P1** | 2–4 | Delete internet poller · multi-vehicle data model · KML parser · fork/adopt decision | Three SITL vehicles on one map |
| **P2** | 5–7 | Mission-state ingest · MediaMTX + 3 feeds · survivor and task layers · module split for the mission build | 8.14 items 1–5 demonstrable in SITL |
| **P3** | 8–9 | Delivery status · health panel · consolidated progress · **PR1 demo** | All 8 items of 8.14 present |
| **P4–P6** | 10–16 | Harden against real flights; latency, reconnect, partial telemetry | Survives a real 3-drone mission |
| **P7** | 17–18 | Pre-flight checklist mode · source review for SYS-20 | SYS-20 verified by inspection |
| **P8** | 19–21 | Freeze · offline tile pre-cache · 20 setup rehearsals | Config frozen |

**P1 and P2 are the load-bearing phases.** If multi-vehicle is not done by W4,
every subsequent display is built twice.

---

## 6. Reuse vs rebuild

| Reuse as-is | Rebuild |
|---|---|
| Leaflet map, tile layer, marker/polygon rendering | Vehicle state model (single → fleet) |
| `slippy_map_getter.py` | Video path (MJPEG → WebRTC gateway) |
| React component library, theming, layout | Page structure (flight-plan editor → mission view) |
| MAVLink/DroneKit telemetry parsing | Connection layer (one vehicle → mavlink-router) |
| SITL scripts (`run-sim.sh`, `sim.parm`) | — |
| Params UI *(dev build only)* | — |

**Cut entirely:** the Submissions tab (AUVSI interop, no NIDAR analogue), UGV
support, and the ODLC external imaging service — detection runs onboard and
arrives via mission state.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Track C is 2 people also owning autonomy and SITL | GCS is a *view*. Resist features. The 8.14 list is the scope; nothing else. |
| Three WebRTC streams unproven on the GCS hardware | Prove MediaMTX with three SITL sources in **P2**, not at the first real flight |
| Multi-vehicle retrofit late | Non-negotiable in P1 |
| Internet poller survives into the mission build | Delete in P1; add a CI grep for `fetch(`/`http` in the mission bundle |
| Mission area not pre-cached | Cache the venue region at P7, verified offline with the network physically off |

---

## 8. Definition of done

The mission build, on a machine with **no network interface configured**:

1. Loads a real KML in < 30 s with no operator editing
2. Shows three drones, three colour-coded regions, three live video panes
3. Shows survivor markers with fix quality, and delivery state per survivor
4. Shows consolidated progress and per-drone health
5. Exposes **abort and recall, and nothing else**
6. Survives one drone dropping off the mesh and rejoining
7. Passes a `grep` for outbound network calls
