# Implementation Plan — from paperwork to a flying mission

The sizing model closes, the requirements are baselined, and the ground station
display layer works. **The aircraft, the autonomy, the perception and the
failsafes do not exist.** This is the plan for those.

Schedule authority remains [`development-plan.md`](development-plan.md); this is
*what to build and how simple it can be*.

---

## Part 1 — Four simplifications that remove most of the work

Take these first. They change what has to be written at all, and each is
justified against the rubric rather than against elegance.

### 1.1 Let ArduPilot fly the search. Write no code for it.

**This is the largest saving available and it is not in the original plan.**

The search phase is a lawnmower pattern over a known polygon at a fixed
altitude and speed. ArduPilot already does that — it is what AUTO mode *is*.

```
GCS: load KML ─► partition into N strips ─► generate boustrophedon waypoints
                                          ─► upload as an AUTO mission per drone
Aircraft: fly AUTO.  No custom flight code for search.
```

Uploading a mission during setup is explicitly permitted (MB §3 lists
mission-file loading as one of four allowed operator actions). The aircraft then
executes it with no operator input, which is exactly what 8.16 requires.

**The only custom flight logic left is the delivery excursion**: leave AUTO, go
to the survivor, descend, release, resume. That is a GUIDED-mode sequence issued
by the *companion computer* — onboard autonomy, not an operator action, so it is
not manual intervention.

This collapses "mission state machine + coverage execution + path following"
into "waypoint generation on the ground, plus one excursion routine".

### 1.2 Partition on the ground, not in the air

Deterministic, inspectable, testable without an aircraft, and it means the three
aircraft cannot disagree about who owns what — because they were told.

The architecture already claims "centrally partitioned, decentrally executed".
This is that, taken literally.

### 1.3 Static equal-area partition instead of DARP

Split the polygon into N strips of equal area along its longest axis. ~150 lines
with a binary search on the cut position. DARP proper is weeks of work.

Rubric check — 4D-3 awards 50 marks for *"two or more drones operating as one
coordinated mission system with shared mission execution, common mission logic,
and no independent manual control."* **DARP is not mentioned.**

### 1.4 Greedy claim-and-lock instead of CBBA

Nearest free drone claims the next survivor; deterministic tie-break on lowest
system ID; a claim is a lock until released or it times out. ~80 lines, and
conflict-free by construction rather than by consensus proof.

CBBA is hundreds of lines whose failure modes appear precisely on the
partitioned mesh we expect. For 3 drones and 10 survivors, optimal versus greedy
differs by 10–20 % in travel time — on a mission using 26 % of its time budget.
**That difference is worth zero points.**

> **Implement simple, present sophisticated.** Show the DARP/CBBA design in the
> Design Review and explain that a deterministic partition was implemented
> because it is inspectable and verifiable in the time available. That reads as
> engineering maturity. Claiming CBBA and demonstrating a crash does not.

### 1.5 Most failsafes are parameters, not code

SYS-11 requires failsafes for low battery, C2 loss, geofence breach, mission
abort and RTH. **Four of the five are ArduPilot parameters:**

| Failsafe | Mechanism | Code? |
|---|---|---|
| Low battery | `BATT_LOW_VOLT`, `BATT_FS_LOW_ACT=2` (RTL) | none |
| Geofence | `FENCE_ENABLE`, `FENCE_TYPE`, `FENCE_ACTION=1` (RTL) | none |
| C2 link loss | `FS_GCS_ENABLE=1`, `FS_OPTIONS` | none |
| RTH | `RTL_ALT`, `RTL_SPEED` | none |
| **Mission abort / recall** | **Custom — see §4** | **yes** |

Writing them down as a parameter file is a day's work and it is verifiable by
inspection. **Do not write a custom battery monitor.**

---

## Part 2 — What to build

Effort is *days of one focused person*, assuming student pace and debugging.

### 2.1 Ground-side mission preparation — **no hardware needed, start now**

| Component | What it does | Days |
|---|---|---|
| `coverage/partition.py` | Polygon → N equal-area strips along the longest axis | 3 |
| `coverage/boustrophedon.py` | Strip → transect waypoints at swath × (1 − sidelap) | 2 |
| `coverage/mission_file.py` | Waypoints → ArduPilot mission (`MAV_CMD_NAV_WAYPOINT`), per drone | 2 |
| Tests | Adversarial polygons: long-thin, concave, rotated, high aspect | 2 |

**Total ~9 days, and every hour of it is testable on a laptop.** This is the
critical path for P4 and the first thing to write.

### 2.2 Onboard autonomy — the companion computer

| Component | What it does | Days |
|---|---|---|
| `mission_state.py` | Phase machine: SETUP → CLIMB → SEARCH → DELIVER → RTH → LANDED | 3 |
| `swarm_state.py` | Mesh broadcast + merge; claim/release survivors; lowest-ID tie-break | 4 |
| `delivery.py` | GUIDED excursion: goto → descend → null groundspeed → release → resume AUTO | 5 |
| **`mission_publisher.py`** | **The 5 Hz JSON the GCS already consumes — currently missing** | **1** |
| `failsafe.py` | Payload jam, mesh partition, RTK loss flagging | 2 |

**Total ~15 days.** `mission_publisher.py` is one day and unblocks demonstrating
the entire ground station — do it first, even before the rest works, feeding it
stub data.

### 2.3 Perception — the 250-point long pole

| Component | What it does | Days |
|---|---|---|
| `training/` | Fine-tune YOLO on HERIDAL/SARD, then on dummies | 8 |
| `tiling/` | SAHI-style tiled inference at 2 Hz | 3 |
| `geotagging/ray.py` | Ray–ground intersection, near-nadir gating (SYS-33) | 3 |
| `geotagging/fusion.py` | Multi-frame fusion, best-fix-wins | 2 |
| `calibration/` | Intrinsics + boresight + lever arm (SYS-48) | 4 |

**Total ~20 days, and the dataset has irreducible calendar cost on top.** Start
the data collection now; the code can follow.

### 2.4 Communications

| Component | Days |
|---|---|
| `mavlink-router` config, 3 SYSIDs → GCS | 1 |
| batman-adv mesh bring-up + link monitoring | 3 |
| 868 MHz safety link — see §4 | 3 |

### 2.5 Aircraft

Frame CAD → manufacture → assembly → thrust stand → first hover. Track A owns
this and it is gated on the orders being placed, not on any code.

---

## Part 3 — Do the testable things first

Roughly **35 of the ~55 engineering days need no aircraft**. In a programme whose
flight window opens in October, that ordering is the whole game:

**Now, on laptops:** partition, boustrophedon, mission-file generation, mission
publisher, perception training on public data, calibration tooling, SITL.

**Only with hardware:** thrust stand, vibration, RF range, drop trials, recall
range, and every P6+ verification.

If the aircraft slips three weeks, none of the above slips. If you wait for the
aircraft to start the autonomy, everything slips together.

---

## Part 4 — The abort chain, which does not exist

**`/api/safety/abort` currently sets a boolean that nothing reads.** It returns
200 and a green tick while the aircraft keep flying. Until §4 is built, that
button must be labelled **NOT IMPLEMENTED** in the UI.

Rules 8.19 and MB §8 require mission abort and emergency recall, and they are two
of only four permitted operator actions. The chain has to be real:

```
GCS abort ─► 868 MHz LoRa (NOT the mesh) ─► companion ─► FC mode change
                                                          abort  -> LOITER then RTL
                                                          recall -> RTL immediately
```

**Design constraints:**

1. **Separate radio from the mesh.** The reason to abort is often that the mesh
   has failed. An abort path that shares the failed link is not an abort path.
2. **Framed, sequenced, acknowledged.** LoRa is lossy and low-rate. Send a short
   framed command with a sequence number, repeat it for several seconds, and
   display per-aircraft acknowledgement on the GCS. The operator must see
   *which* aircraft accepted it.
3. **Independent of the companion where possible.** If the companion has hung,
   the abort must still work. Prefer the safety receiver driving the flight
   controller directly — an RC channel mapped to a flight mode is the simplest
   reliable form, and ArduPilot supports it natively via `RCn_OPTION`.
4. **Test by fault injection**, not by hoping: kill the mesh, kill the companion,
   kill the FC link, and confirm abort still recovers the aircraft.

**Effort ~3 days, and it is safety-critical.** It should be built before the
first autonomous flight, not after.

---

## Part 5 — Two aircraft is the baseline

Rule 8.8's minimum is **two**. Build and validate two properly; treat the third
as a stretch that gets built once the first two fly a full mission.

| | 3 aircraft | 2 aircraft |
|---|---|---|
| Rule compliance | ✔ | ✔ |
| Collaboration criterion (50 pts) | ✔ | ✔ |
| Sweep time per drone | 93 s | ~140 s |
| Mission total | 7.7 min | ~9 min *(vs a 15 min bonus threshold)* |
| Build + integration effort | 100 % | **67 %** |
| Spare airframe if one is lost | ✔ | ✘ |

The mission still finishes inside the fast-completion bonus with two. The real
cost is losing the spare, which argues for building the third **after** the first
two work — not in parallel with them.

---

## Part 6 — Milestones that mean something

| # | Milestone | Why it is the right gate |
|---|---|---|
| **M1** | GCS shows a synthetic mission end-to-end | Already done — `sim_mission.py` |
| **M2** | Partition + waypoints generated from a real KML, rendered on the GCS | Proves the ground half with no aircraft |
| **M3** | One SITL aircraft flies the generated mission autonomously | Proves the AUTO-mode simplification (§1.1) |
| **M4** | Detector finds dummies in field imagery at operational altitude | The 250-point long pole, on the ground |
| **M5** | Abort recovers a SITL aircraft with the mesh killed | Safety, before any real autonomous flight |
| **M6** | **One real aircraft: search → detect → geotag → drop, autonomously** | **~80 % of all technical risk. Target: end of October.** |
| M7 | Two aircraft, coordinated, one mission | Adds coordination to a proven single-aircraft stack |
| M8 | Third aircraft | Stretch |

**M6 is the milestone that matters.** Everything before it is preparation and
everything after it is multiplication. If M6 lands by the end of October, the
programme is in good shape. If it lands in December, it does not.

---

## Part 7 — Immediate order of work

1. **Place the hardware orders.** Nothing here substitutes for parts arriving.
2. **Label the abort button NOT IMPLEMENTED.**
3. **Write `mission_publisher.py`** — one day, unblocks demonstrating everything.
4. **Write the partition and boustrophedon** — ~5 days, testable on a laptop,
   critical path.
5. **Start perception data collection** — irreducible calendar cost.
6. **Write the ArduPilot parameter file** — a day, and it is four of five
   failsafes.

Items 3–6 need no hardware and can run in parallel with the build.
