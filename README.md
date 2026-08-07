# NIDAR RescueSwarm

> An autonomous multi-drone system for rapid flood survivor search, localization, and emergency aid delivery — built for communication-denied environments, and built in India.

<p align="center">
  <b>NIDAR 2.0 (2026–27) · Track 1: Drone Innovation</b><br>
  MeitY · Drone Federation of India · SwaYaan Initiative
</p>

<p align="center">
  <img src="https://img.shields.io/badge/fleet-3%20aircraft-informational" alt="fleet">
  <img src="https://img.shields.io/badge/fleet%20mass-15.2%20%2F%2025%20kg-success" alt="mass">
  <img src="https://img.shields.io/badge/mission-7.7%20%2F%2030%20min-success" alt="mission time">
  <img src="https://img.shields.io/badge/indigenous%20suppliers-95.5%25-orange" alt="indigenisation">
  <img src="https://img.shields.io/badge/status-Phase%200%20%C2%B7%20requirements-blue" alt="status">
</p>

---

## Overview

RescueSwarm is a coordinated fleet of three autonomous drones designed for disaster response where no external network exists. The system collaboratively searches a flood-affected area, detects stranded survivors, geotags their positions, delivers emergency medical kits, and reports the entire mission through a single operator interface.

Everything after "start" is autonomous. The operator may load the mission file, press start, and abort or recall. Nothing else.

---

## Design Point

The system has been sized end-to-end. These are not targets — they are the outputs of a closed engineering model ([`docs/sizing/`](docs/sizing/)).

> ### Scoring-driven baseline — [`docs/requirements/`](docs/requirements/)
>
> The design is now baselined against the NIDAR 2026–27 Rulebook rather than against round numbers. What that changed:
>
> - **Delivery scores by zone — ≤1 m = 20 pts, ≤2 m = 14, ≤3 m = 8.** The old ≤3 m target was the *worst* zone, and the old SYS-15 ("within 5.0 m of tag") was outside every zone and scored **zero**.
> - **Geolocation gates 450 of the 600 flight points.** Kits are scored from the survivor, so a drop is no better than the tag it aimed at — geotag is **75–83 % of delivery error variance**. RTK is worth **82 delivery points** alone; fusion and ground-plane calibration add **20** more.
> - **Speed is worth 50 points and is already won** (≤15 min needed, 7.7 min flown). Time is the one surplus resource — spend it on recall.
> - **Rule 8.14 needs a feed from every drone, and compliance is free:** three 480p15 feeds cost 1.80 Mbps, exactly what one 720p30 feed cost.
>
> **Documents:** [requirements baseline](docs/requirements/requirements-baseline.md) · [rulebook compliance](docs/requirements/rulebook-compliance.md) · [schedule baseline](docs/schedule-baseline.md) · [business strategy](docs/business/README.md)
>
> ⚠ **Registration closes in the 2nd week of August 2026** and the finals are **January 2027** — the old 30-week plan overran by ~8 weeks. See [`docs/schedule-baseline.md`](docs/schedule-baseline.md).

> **Configuration decision and constraint review** — [`docs/sizing/configuration-trade.md`](docs/sizing/configuration-trade.md). **Coaxial is rejected**: sized to the reserve policy it costs +61–84 % hover power and +26–34 % fleet mass, and has the worst attitude bandwidth of any option. **Stay quad** — 4 arms protects setup, the only constraint under 20 % margin. **Prop diameter provisionally 18 in** (lower gust sensitivity and 38 % less rotor inertia), arms designed to accept 16–20 in and confirmed on a bench in P5. Three constraints bind and none is a stated requirement yet: **VRS on descent** (the current 2.5 m/s sits on the onset boundary — a flight-profile fix, not a hardware one), **wind penetration**, and **detection recall**. The design point below is unchanged until those are adopted.

| Parameter | Value |
|---|---|
| Fleet | **3 aircraft**, identical |
| Configuration | Quadrotor · 20 in props · 6S2P 21700 Li-ion |
| MTOW per aircraft | **5.05 kg** (4 kits loaded) |
| **Fleet all-up weight** | **15.2 kg** vs 25 kg limit → **39 % margin** |
| Battery | 12 cells, 966 g, **194 Wh**, 9.0 Ah, 21.6 V nominal |
| Hover power | 601 W electrical (426 W shaft) · disk loading 6.2 kg/m² |
| Hover endurance | **15.5 min** at 80 % DoD |
| Design mission | **7.7 min** — 26 % of the 30 min allowance |
| Thrust-to-weight | 2.0 static · hover at 50 % of max thrust |
| Search altitude / speed | 60 m AGL / 8 m/s **groundspeed** |
| Ground sample distance | 1.82 cm/px → a person is ~93 px long |
| Sweep time (10 ha, 3 drones) | ~93 s per drone including turns |
| Geotag accuracy target | **CEP50 ≤ 0.75 m** with RTK (0.91 m RSS) — *scoring-derived* |
| Delivery accuracy target | **≥ 60 % within 2 m, ≥ 30 % within 1 m** of the survivor — *scoring-derived* |
| Link margin | ≥ 13 dB at 600 m · offered load 2.5 Mbps |

---

## Five Findings That Shaped the Design

**1. The mission is not coverage-limited.** Three drones sweep 10 ha in about three minutes against a 30-minute ceiling. Coverage is the problem everyone optimises and nobody is constrained by. The real constraints, in order, are detection recall, delivery time, deconfliction, and setup.

**2. The 5-minute setup window is the only tight constraint in the system.** Modelled boot-to-launch is ~285 s with two people working in parallel — **15 seconds of margin**. Everything else has 25–55 % reserve. Cold-boot timing is the highest-priority measurement in the programme.

**3. Release velocity dominates drop accuracy, not altitude.** 1 m/s of residual groundspeed costs 1.06 m of miss; 2 m of altitude error costs 7 cm. A multirotor can null its groundspeed — a fixed-wing cannot. Hence: hover at 6 m, gate release below 0.3 m/s, accept 12 extra seconds per drop.

**4. The ground-height assumption is the largest geotag error term without RTK** — 2.76 m, bigger than GNSS itself, because a height error scales the projection ray by 37 m at frame edge. Systematic terms do not average out across frames. **Calibrate first, then fuse.**

**5. Hold constant groundspeed, not airspeed.** At 6 m/s wind, constant-airspeed sweeps take 191 s instead of 83 s. Constant groundspeed makes sweep time wind-independent for 8 % more energy — and keeps motion blur constant, which matters for detection.

---

## Mission Flow

```text
Launch (sequenced, one aircraft at a time)
   │
   ▼
Load Mission Boundary ──► DARP equal-area partition
   │
   ▼
Climb to 60 m · altitude-stratified per aircraft
   │
   ▼
Parallel Boustrophedon Sweep  ◄── constant groundspeed, wind-compensated
   │
   ▼
Detect Survivor ──► candidate
   │
   ▼
Confirm (≥3 frames or 2 agents) ──► confirmed survivor
   │
   ▼
Geotag ──► ray–ground intersection + multi-frame fusion
   │
   ▼
CBBA Auction ──► delivery task assigned to one drone
   │
   ▼
Transit · Descend to 6 m · Null groundspeed · Release
   │
   ▼
Next task, or Return to Home
   │
   ▼
Sequenced Recovery into the 3.66 m box
```

Search and delivery **overlap**. Drones do not wait for the sweep to finish before beginning deliveries.

---

## System Architecture

```
                    Ground Control Station
                    (read-only + abort/recall)
                              │
                    5.8 GHz mesh  ·  868 MHz safety link
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
     Drone A               Drone B               Drone C
        │                     │                     │
        └───── batman-adv mesh · replicated state ──┘
                  Search • Detect • Deliver
```

**The GCS is a view, not a controller.** Rules §3 and §4 make any GCS-originated retasking a manual intervention, so the ground station is built read-only by construction — the violation is structurally impossible, not merely avoided by discipline.

**Autonomy topology is hybrid:** centrally partitioned on the ground (deterministic, inspectable, fast), decentrally executed in the air (survives link loss). A drone that loses the mesh for 10 s continues its assigned bundle; at 60 s it returns home. **No behaviour requires the link to make progress.**

---

## Proven Methods

Every algorithmic choice traces to published work rather than intuition.

| Layer | Method | Source |
|---|---|---|
| Area partitioning | **DARP** — equal-area, connected sub-regions anchored to a common launch point | Kapoutsis, Chatzichristofis & Kosmatopoulos, *JINT* 86 (2017) |
| Coverage within a region | **Boustrophedon cellular decomposition**, sweep along the longest axis | Choset, *Autonomous Robots* (2000) |
| Delivery task allocation | **CBBA** — consensus-based bundle auction, provably conflict-free over local comms | Choi, Brunet & How, *IEEE T-RO* 25(4) (2009) |
| Dynamic reallocation | Partial replanning variant, bounded reassignment on new detections | Buckman, Choi & How, *AIAA SciTech* (2019) |
| Small-object detection | **SAHI** tiled inference — recovers recall that whole-frame resizing destroys | Akyon, Altinuc & Temizel, *ICIP* (2022) |
| Detector training data | **HERIDAL** + **SARD** for pre-training, Indian field data for fine-tuning | Božić-Štulić et al.; Sambolek & Ivašić-Kos, *IEEE Access* (2021) |
| Airdrop error model | Release-velocity dominance in ballistic dispersion | Mathisen et al., *Autonomous Robots* (2020) |
| Mesh comms | **batman-adv** L2 mesh + sub-GHz safety channel | Marchese et al., *Drones* 5(2) (2021) |
| Propulsion sizing | Momentum theory with figure of merit (FM = 0.60) | Standard rotorcraft practice |
| Systems process | V-model with TRL gates, spiral overlay on high-uncertainty subsystems | NASA SE Handbook SP-2016-6105 |

---

## Perception

A COCO-pretrained person detector will fail here. Aerial SAR targets occupy ~0.1 % of frame area, lying prone or partially covered — a distribution general detectors have never seen.

- **Pre-train** on HERIDAL and SARD; reproduce published baselines (YOLOv5L reaches ~0.90 P / ~0.89 R on HERIDAL) to prove the pipeline before trusting your own data.
- **Fine-tune on Indian field data.** HERIDAL and SARD are European — wrong terrain, wrong vegetation, wrong clothing, wrong sun angle. Target ≥ 2,000 annotated frames from our own camera at our own altitudes, with mannequins in supine, prone, seated and partially-occluded postures.
- **Tiled inference** at 2× downsample, 640 px tiles, 20 % overlap, 2 Hz.
- **Exploit the frame surplus.** At 8 m/s and 60 m the along-track footprint is 56 m, so even 2 Hz gives ~14 frames per target per pass. Multi-frame fusion is free — use it for temporal confirmation and geolocation averaging.
- **Gate on body rate.** Suppress inference above 15 °/s: the imagery is smeared and the ground-plane assumption is worst in a bank. The turns are outside the search region anyway.

**Detection recall is the long pole of the whole programme.** Field data collection starts in week 6, well before the aircraft are polished.

---

## Indigenisation

NIDAR 2.0 exists to move India "from drone assembly to manufacturing the drone's brain in India." This build takes that seriously, and reports it honestly.

| Basis | Score |
|---|---|
| Line items with an Indian supplier | **95.5 %** |
| Programme value that is Indian | **60.2 %** |
| Flight-hardware value that is Indian | **56.8 %** |
| Payload, kits and ground-truth targets | **100 %** |

The gap between 95 % and 60 % is not evasion. An Indian flight controller or camera module is Indian design, Indian firmware and Indian manufacture on imported silicon; the BOM scores those at 60 % rather than 100 %. **State which basis you are quoting.**

**Two indigenisation choices that improve the system rather than compromise it:**

- **NavIC.** ISRO's constellation sits directly overhead India — more satellites, faster time-to-first-fix (which directly buys margin in the 5-minute setup window), and a fallback if GPS is degraded or jammed.
- **C-DAC VEGA.** The free RISC-V dev kits run the payload-release controller and failsafe watchdog — real Indian silicon flying, on a subsystem with a hardware bypass, off the flight-critical path.

**Four things have no Indian option and are declared as such:** AI inference silicon (~20 TOPS class), high-drain 21700 cells at 45 A, 802.11/LoRa RF chipsets, and high-current connectors.

Suppliers: Bharath Components · Mechtex · Flameback Tech · S R Aerospace · Agam Robotics · Zuppa · Teravolt Labs · Accord Software · e-con Systems · FxUAV Technologies · Kineco · Sundram Fasteners. Full BOM in [`hardware/bom/`](hardware/bom/).

---

## Mission Constraints

| Requirement | Value | Our design |
|---|---|---|
| Minimum drones | 2 | **3** — one can fail and we stay compliant |
| Search area | Up to 10 ha | 10 ha in ~93 s/drone |
| Mission time | ≤ 30 min | **7.7 min** design mission |
| Total fleet weight | ≤ 25 kg | **15.2 kg** |
| Payload | 200 g, 200 × 100 × 50 mm | 4 kits/aircraft = 12 capacity for 10 survivors |
| Launch / landing area | 12 × 12 ft (3.66 m) | Sequenced launch and recovery |
| Setup to launch | 5 min | **~285 s modelled — 15 s margin** ⚠ |
| Human operators | 1 operator, 2 setup crew | Rehearsed two-person choreography |
| External network | Not allowed | Team-owned RF only; offline map tiles cached |

---

## Safety

| Failsafe | Response |
|---|---|
| Low battery | Abort current task, return to home, sequenced landing |
| C2 link loss | Continue assigned bundle autonomously; RTH at 60 s |
| Mesh partition | Deterministic tie-break (lowest system ID); no task left unclaimed |
| Geofence breach | Immediate hold, then return to home |
| GPS degradation | Hold, climb for reacquisition, RTH on timeout |
| Payload jam | Flag the task for reallocation; continue mission |
| Mission abort | All aircraft hold, then sequenced recovery |
| Emergency recall | Immediate RTH on the 868 MHz link |

Deconfliction is layered: altitude stratification during search (55/60/65 m), exclusive spatial locks around each survivor during delivery, reciprocal velocity-obstacle avoidance as a runtime backstop, and strictly sequenced launch and recovery through the 3.66 m box.

**Payload release requires a positive mechanical lock independent of servo power.** A brownout must not drop a kit.

---

## Development Roadmap

| Phase | Milestone | Gate criterion | Week |
|---|---|---|---|
| P0 | Requirements baselined | Every rule clause maps to a testable requirement | 2 |
| P1 | Architecture frozen | ICDs signed, long-lead items ordered | 5 |
| P2/P3 | Design complete | Software and electronics pass review | 9 |
| P4 | Simulation validated | ≥ 95 % completion over 200 Monte Carlo runs | 13 |
| P5 | Bench prototype | Cold-boot < 180 s, RF and payload validated | 14 |
| P6 | First autonomous flight | Stable auto waypoint flight, failsafes demonstrated | 18 |
| P7 | Perception validated | Recall ≥ 0.90, geotag CEP ≤ 3 m | 20 |
| P8 | Single-drone mission | 5 consecutive autonomous end-to-end missions | 21 |
| P9 | Swarm operational | 3 consecutive 3-drone 10 ha missions | 25 |
| P10 | Competition ready | 13/15 repeatability, setup ≤ 3:30, config frozen | 30 |

Critical path runs P0 → P1 → P2 → P4 → P8 → P9 → P10, with **P7 (perception) as the parallel long pole**. Three weeks of unallocated buffer sit before P10.

> ⚠ **This 30-week plan overruns the competition.** Registration closes in the 2nd week of August 2026 and the finals are in **January 2027** — roughly 22 weeks. Fixed interior checkpoints the plan does not account for: **Progress Review 1 (2nd week Oct 2026)** and **Progress Review 2 (2nd week Dec 2026)**, both mandatory. The plan needs re-baselining against real dates. See [`docs/requirements/rulebook-compliance.md`](docs/requirements/rulebook-compliance.md) §0.

Full plan: [`docs/development-plan.md`](docs/development-plan.md)

---

## Verification Targets

| ID | Requirement | Method | Verified in |
|---|---|---|---|
| SYS-01 | Fleet AUW ≤ 24.0 kg fully loaded | Test (calibrated scale) | P6 |
| SYS-07 | ≥ 90 % survivor detection at operational altitude | Test | P7, P9 |
| SYS-12 | Geotag CEP50 ≤ **0.75 m** (RTK), 0.91 m RSS | Test vs surveyed ground truth | P7 |
| SYS-15 | ≥ 60 % of drops within **2.0 m** and ≥ 30 % within **1.0 m** of the survivor | Test (≥ 30 drops) | P8 |
| SYS-27 | Three concurrent video feeds within the link budget (rule 8.14) | Analysis + test | P5 |
| SYS-36 | Pass the Pre-Flight Inspection first attempt (Pass/Fail, one retry) | Inspection | P10 |
| SYS-19 | Zero operator input beyond load/start/abort/recall | Demonstration | P9 |
| SYS-21 | Setup to launch ≤ 240 s | Demonstration (20 timed runs) | P10 |
| SYS-23 | No external network used at any point | Inspection + analysis | P9 |
| SYS-28 | Autonomous continuation on C2 loss; RTH at 60 s | Test (fault injection) | P4, P9 |

---

## Repository Structure

The project is in **Phase 0 (requirements)**. The layout below is the target structure; `✔` marks what exists in the repository today — everything else is planned and not yet written.

```text
.
├── firmware/                 # Autopilot params, VEGA co-processor firmware
│   ├── ardupilot-params/
│   └── vega-payload-ctrl/
├── autonomy/                 # Mission logic
│   ├── coverage-planner/     # DARP partition + boustrophedon
│   ├── task-allocation/      # CBBA + partial replanning
│   ├── mission-state/        # State machine, failsafe matrix
│   ├── shared-state/         # Replicated mission state, gossip sync
│   └── deconfliction/        # Altitude layers, spatial locks, ORCA
├── perception/
│   ├── models/               # Weights registry, TensorRT engines
│   ├── training/             # Fine-tuning pipeline, augmentation
│   ├── tiling/               # SAHI-style inference
│   ├── geotagging/           # Ray–ground intersection, multi-frame fusion
│   └── calibration/          # Intrinsics + boresight extrinsics
├── communication/
│   ├── mesh/                 # batman-adv config, link monitoring
│   ├── mavlink-router/       # 3 SYSIDs → one GCS
│   └── safety-link/          # 868 MHz abort/recall
├── ground-station/
│   ├── frontend/             # Read-only mission view
│   ├── backend/              # Telemetry ingest, video switching
│   └── replay/               # Post-mission playback
├── simulations/
│   ├── sitl/                 # Multi-instance SITL + Gazebo
│   ├── monte-carlo/          # 200-run campaign harness
│   └── fault-injection/      # Link loss, drone loss, payload jam
├── hardware/
│   ├── cad/                  # Frame, magazine, mounts
│   ├── electronics/          # Wiring, power tree, PDB
│   ├── bom/               ✔  # Indian BOM + indigenisation scorecard
│   └── payload/              # Release mechanism, kit spec
├── datasets/
│   ├── field-campaign/       # Our Indian SAR imagery + annotations
│   └── benchmarks/           # HERIDAL / SARD evaluation scripts
├── tools/
│   ├── sizing-model/      ✔  # Closed engineering model (Python)
│   └── flight-log-analysis/
├── tests/
├── docs/
│   ├── development-plan.md      ✔
│   ├── schedule-baseline.md     ✔  # Re-baselined against the real calendar
│   ├── requirements/            ✔  # Requirements baseline + rulebook compliance
│   ├── business/                ✔  # Phase 4B strategy + cost sheet (200 pts)
│   ├── sizing/                  ✔  # Calculations + committed model outputs
│   ├── checklists/                 # Setup choreography, pre-flight, contingency
│   └── diagrams/
└── README.md                    ✔
```

---

## Getting Started

**Runnable today** — the sizing model is the only executable artefact in Phase 0:

```bash
git clone https://github.com/tetraethylmethane/NIDAR-RescueSwarm.git && cd NIDAR-RescueSwarm

# Run the sizing model — every number in this README comes from here
pip install -r tools/sizing-model/requirements.txt
python3 tools/sizing-model/rescueswarm_sizing_model.py

# Configuration trade: quad vs hex vs octo vs coaxial X8, and the T/W sweep
python3 tools/sizing-model/config_trade.py

# Delivery accuracy against the NIDAR scoring zones — sets SYS-12 and SYS-15
python3 tools/sizing-model/delivery_accuracy.py

# Search altitude, geotag error structure, and the three-feed downlink budget
python3 tools/sizing-model/mission_profile.py
```

Committed outputs are [`docs/sizing/model-output.txt`](docs/sizing/model-output.txt) and [`docs/sizing/config-trade-output.txt`](docs/sizing/config-trade-output.txt); the derivation and assumptions are in [`docs/sizing/sizing-calculations.md`](docs/sizing/sizing-calculations.md) and [`docs/sizing/configuration-trade.md`](docs/sizing/configuration-trade.md). **If you change the model, re-run it and commit the new output in the same commit** — the README and the sizing documents are both checked against those files. `config_trade.py` imports its constants live from the sizing model, so it cannot drift from the design point.

**Planned once the corresponding subsystems exist** (none of these run yet):

```bash
docker compose build            # identical container for SITL and aircraft
docker compose up sitl
ros2 launch autonomy swarm_mission.launch.py drones:=3 area:=configs/10ha_test.yaml
python3 simulations/monte-carlo/run_campaign.py --runs 200 --report
cd ground-station && npm install && npm run dev
```

**Rule for the team: no new autonomy code touches a real airframe until it has run 20 consecutive clean SITL missions.** SITL cycles cost minutes; a crash costs weeks.

Every real flight runs a tagged commit, logged in the flight log with the tag.

---

## Technologies

**Flight** — ArduPilot / PX4 · MAVLink 2 · C-DAC VEGA (RISC-V)
**Autonomy** — ROS 2 · Fast DDS · DARP · CBBA
**Perception** — YOLO-class detector · TensorRT · SAHI tiling · OpenCV calibration
**Communication** — batman-adv mesh · 5.8 GHz + 868 MHz dual-band · mavlink-router
**Navigation** — NavIC (L1 + L5) · RTK · dual-antenna heading
**Ground** — React · offline ISRO Bhuvan tiles · mission replay
**Simulation** — Gazebo · multi-instance SITL · Monte Carlo + fault injection

---

## Open Questions to Organisers

Two of the original seven are now **answered by the rulebook** — scoring weights (§9 of the rulebook) and video feeds (rule 8.14 requires a feed from *each* drone). The revised list, in priority order, is maintained in [`docs/requirements/rulebook-compliance.md`](docs/requirements/rulebook-compliance.md) §5:

1. Is delivery accuracy measured from the **true survivor position or the tagged position**? — gates 200 points.
2. Is a team-owned **local RTK base station** permitted, given corrections travel on our own local link and not the internet? — now scoring-critical.
3. Is **pre-booting** of onboard computers permitted before the 5-minute window begins?
4. Will survivors be **real humans, dummies, or both**, in what postures and clothing, and under partial cover?
5. What **shape, aspect ratio and file format** should we expect for the boundary polygon?
6. Is a **ballistic parachute** permitted, and is motor-out tolerance separately required?
7. Is there a **maximum wind** condition under which the mission runs?

---

## Project Goal

Develop a fully autonomous multi-drone rescue system capable of locating flood survivors and delivering emergency aid quickly, safely, and without reliance on external communication networks — built, wherever possible, in India.

---

<p align="center">
  <sub>Built for NIDAR 2.0 · MeitY · Drone Federation of India</sub>
</p>
