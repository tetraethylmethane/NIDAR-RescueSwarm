# RescueSwarm — Phase-to-Phase Development Plan
### NIDAR 2026–27, Track 1 (Drone Innovation): Autonomous Multi-Drone Survivor Search & Aid Delivery

**Document type:** Engineering Development Plan + Product Roadmap
**Basis:** *Mission Brief — NIDAR RescueSwarm* (nidar.org.in, Missions 2026)
**Status:** v1.0 — baseline for team review

> **Before you start:** this plan is built entirely from the published Mission Brief. The official NIDAR Rulebook (v1.1) carries the **scoring weights** — how many points go to speed vs. detection accuracy vs. delivery proximity vs. autonomy vs. documentation. Several decisions below (§3.6, §3.8) flip depending on those weights. Pull the rulebook and re-run the two decisions marked **[SCORE-DEPENDENT]** before freezing the architecture.

---

## Part 0 — Decoding the mission into engineering requirements

Most teams lose this competition in the first two weeks, by starting to build before converting the brief into numbers. Do this first.

### 0.1 Hard constraints extracted from the brief

| # | Constraint | Source | Engineering consequence |
|---|---|---|---|
| C1 | ≥ 2 drones, one collaborative mission system | §1, §2 | Fleet sizing decision (§3.1) |
| C2 | Combined all-up weight of **all** drones ≤ 25 kg | §2 | Fleet-level mass budget, not per-drone |
| C3 | No market-ready / RTF airframes | §2 | Custom frame design is mandatory, not optional |
| C4 | Search area ≤ 10 ha (100,000 m²) | §1 | Coverage path planning problem |
| C5 | Up to 10 survivors, geotagged | §1 | Detection + georeferencing pipeline |
| C6 | 1 payload per survivor: 200 g, 200×100×50 mm rigid box | §2 | Up to 2.0 kg of payload distributed across the fleet, plus release hardware |
| C7 | Mission file provided **only at setup**; 5 min to load and launch | §3 | Boot-to-launch must be < 5 min including GNSS convergence |
| C8 | Max 30 min flight time, launch → return | §3 | Endurance requirement with reserve |
| C9 | Operator may only: load file, start, safety-abort, emergency recall | §3, §4 | Zero in-flight human decisions. No manual retasking. |
| C10 | Single GCS, single operator, one unified interface | §4, §6 | One MAVLink/telemetry hub; no per-drone GCS |
| C11 | GCS must display: boundary, all drone positions/status, survivor tags, per-drone delivery status, mission progress, **live video** | §4 | Non-trivial GCS scope — treat as a first-class subsystem |
| C12 | No GSM/LTE/5G/public Wi-Fi/internet/cloud. No tethers or fibre. | §5 | Team-owned RF link only. Air-gapped design. |
| C13 | Max 2 people for setup; 1 operator; no other assistance | §6 | Setup choreography is a designed, rehearsed procedure |
| C14 | Launch and land inside a 12 ft × 12 ft (3.66 m × 3.66 m) box | §7 | **Sequenced** launch and recovery; landing precision requirement |
| C15 | Outdoors, daylight | §7 | RGB is sufficient; thermal is optional (§3.5) |
| C16 | Per-drone RTH; failsafes for low battery, C2 link loss, geofence breach, abort, recall | §8 | Failsafe matrix must be designed and demonstrated |

### 0.2 Derived performance numbers (do this arithmetic before buying anything)

Assume a worst-case 10 ha rectangle of 400 m × 250 m and a 4K camera (3840×2160) with 70° horizontal FOV.

Swath width `W = 2·h·tan(HFOV/2) = 1.40·h`  ·  Ground sample distance `GSD = W / 3840`

| AGL height | Swath W | GSD | Pixels on a 1.7 m person | Line spacing @ 30 % sidelap |
|---|---|---|---|---|
| 40 m | 56 m | 1.46 cm/px | ~117 px | 39 m |
| 50 m | 70 m | 1.82 cm/px | ~93 px | 49 m |
| **60 m** | **84 m** | **2.19 cm/px** | **~78 px** | **59 m** |
| 70 m | 98 m | 2.55 cm/px | ~67 px | 69 m |
| 80 m | 112 m | 2.92 cm/px | ~58 px | 78 m |

**Coverage time at 60 m, 30 % sidelap:** 250 m / 59 m ≈ 5 transects × 400 m = **2,000 m of track**. Split across 3 drones ≈ 667 m each. At 8 m/s that is **~85 s of transect plus turn overhead** — call it 2.5–3 minutes of search.

**This is the single most important result in the plan: the mission is not coverage-limited.** You have roughly 30 minutes and you need about 3 for the sweep. The binding constraints are, in order:

1. **Probability of detection (Pd)** — a missed survivor is unrecoverable within the mission
2. **Delivery routing and drop time** — 10 descents/drops dominate the timeline
3. **Deconfliction and safe sequencing** at launch, at the drop points, and at recovery
4. **The 5-minute setup window** — cold-boot, GNSS convergence, mission upload

Spend the surplus time budget on (1) and (2). Fly lower and slower than you can, not faster.

**Delivery time model:** mean inter-target transit ~150 m ≈ 20 s; descend, align, drop, climb ≈ 20–25 s. Per delivery ≈ 45 s. 10 deliveries across 3 drones ≈ 3.4 each ≈ 150 s per drone.

**Target mission timeline (design goal, against a 30 min ceiling):**

| Segment | Budget |
|---|---|
| Arm, sequenced launch, climb to search altitude | 60 s |
| Coordinated area sweep | 180 s |
| Delivery phase (overlapped with tail of sweep) | 180 s |
| Sequenced RTH, approach, land in 3.66 m box | 120 s |
| **Total** | **≈ 9 min** |
| Reserve against the 30 min cap | 21 min (>200 %) |

**Endurance requirement:** design for ≥ 20 min usable flight at mission weight (≈ 2.2× the 9 min design mission), landing with ≥ 25 % battery.

### 0.3 Requirement register

Convert the above into a numbered, testable requirement list before Phase 1 closes. Each requirement gets: ID, statement, source (brief clause), verification method (Analysis / Inspection / Demonstration / Test), and the phase in which it is verified. Example rows:

| ID | Requirement | Verif. | Verified in |
|---|---|---|---|
| SYS-01 | Fleet combined AUW, fully loaded, ≤ 24.0 kg (4 % margin below the 25 kg limit) | Test (weigh-in) | P6, P11 |
| SYS-07 | System detects ≥ 9 of 10 supine/prone human-sized targets in a representative 10 ha field, ≤ 1 false positive per mission | Test | P9 |
| SYS-12 | Geotag error ≤ 3.0 m CEP against RTK ground truth | Test | P9 |
| SYS-15 | Payload lands ≤ 5.0 m from the tagged survivor position, 90 % of drops | Test | P9 |
| SYS-21 | Boot-to-launch ≤ 240 s from cold, 2 operators, including mission file upload | Demonstration | P10 |
| SYS-28 | On C2 link loss > 10 s, drone completes assigned tasks autonomously or executes RTH; no loiter-and-wait | Test | P8, P9 |

---

## Part 1 — Development methodology

### 1.1 Why a V-model core

Use the **systems-engineering V-model** (NASA SE Handbook lineage) as the spine: requirements decompose down the left arm into subsystem specs, and each level has a matching verification activity on the right arm. It exists precisely for the failure mode this competition punishes — subsystems that each work but do not integrate.

- Left arm: mission requirements → system architecture → subsystem specs → detailed design
- Right arm: unit test → subsystem test → integration test → system validation → operational validation

### 1.2 Spiral / incremental overlay for the risky parts

A pure V-model is too rigid for perception and swarm logic, where you cannot specify your way to a working detector. Overlay **spiral development** on the three high-uncertainty subsystems — computer vision, swarm coordination, payload release — with 2-week build/measure/learn iterations against a fixed metric. Everything else (power, structure, comms plumbing) runs as a straight V.

### 1.3 Technology Readiness Level gates

Track each subsystem on a TRL 1–9 scale and refuse to integrate anything below TRL 5 (validated in a relevant environment). This prevents the classic failure of integrating a promising-but-unproven vision model two weeks before finals.

### 1.4 Simulation-first discipline

Every behaviour is proven in SITL before it flies. Rule for the team: **no new autonomy code touches a real airframe until it has run 20 consecutive clean SITL missions.** SITL cycles cost minutes; a crash costs weeks.

### 1.5 Configuration control

- Single monorepo; everything (firmware params, model weights hashes, GCS build, mission configs) versioned
- Flight-tagged releases: every real flight runs a tagged commit, logged in the flight log with the tag
- Automated log capture (ArduPilot/PX4 .bin + ROS bag + camera) on every flight, archived by flight number
- A written **Flight Test Card** per sortie: objective, config, pass criteria, abort criteria

### 1.6 Team structure (6–10 people)

| Sub-team | Owns |
|---|---|
| Systems / PM | Requirements, interfaces, schedule, gates, documentation, rulebook compliance |
| Airframe & Propulsion | Frame, motors, props, mass and thrust budgets, vibration, structural tests |
| Avionics & Power | FC, wiring, power distribution, ESCs, battery, EMI, payload actuator electronics |
| Autonomy & Swarm | Coverage planning, task allocation, mission state machine, failsafes |
| Perception | Detection model, dataset, georeferencing, onboard inference optimisation |
| Comms & GCS | RF link, mesh, MAVLink routing, ground control station UI, video |
| Test & Safety | Test plans, flight test conduct, safety officer, checklists, range logistics |

---

## Part 2 — Architecture decisions, with justification

These are the decisions that determine whether the rest of the plan succeeds. Each one gives the recommendation, the reasoning, the alternatives rejected, and what would change the answer.

### 2.1 Fleet size: **3 drones**

The brief requires ≥ 2. Choose 3.

- **Redundancy under the rule itself:** with 3 airframes, a single pre-flight or in-flight loss still leaves you compliant with the ≥ 2 requirement and able to fly a degraded mission. With 2, one failure ends the attempt.
- **Coverage:** the sweep is already fast with 2; going 3 → 4 buys little search time but adds a fourth boot sequence into a 5-minute window, a fourth node to the mesh, and a fourth aircraft to sequence through a 3.66 m landing box.
- **Mass:** 3 × ~7 kg ≈ 21 kg leaves real margin under the 25 kg fleet cap. 4 × 6 kg = 24 kg leaves almost none, and the weigh-in includes batteries, payloads and every accessory.

**Reconsider if:** the rulebook awards points explicitly for fleet size or for parallel task execution, or if your airframe lands under 5 kg comfortably.

### 2.2 Autonomy topology: **hybrid — centrally partitioned, decentrally executed**

- **At mission start (on the ground, within the 5-min window):** the boundary polygon from the organiser's mission file is partitioned centrally. Deterministic, inspectable, fast.
- **In flight:** each drone runs the same mission state machine over a **replicated shared mission state**. Delivery tasks are allocated by a decentralised market/auction mechanism so that the system keeps working when a link degrades.
- **The GCS is a view, not a controller.** This is a rules-driven decision: §3 and §4 make any GCS-originated retasking a manual intervention. Build the GCS as read-only plus abort/recall, and you make that violation structurally impossible.

### 2.3 Area partitioning and coverage: **DARP-style equal-area division + boustrophedon sweep**

- **Divide Areas based on Robots' Initial Positions (DARP)** (Kapoutsis, Chatzichristofis & Kosmatopoulos, *J. Intell. Robot. Syst.* 86, 2017) divides a gridded area into equal, connected, non-backtracking sub-regions anchored to each robot's start position — which is exactly your situation, since all three launch from the same 12 ft box. Reference implementation is open-source.
- Within each sub-region, use **boustrophedon ("lawnmower") cell decomposition** (Choset, 2000), the standard for UAV survey coverage. Sweep direction should be chosen along the sub-region's longest axis to minimise turns; turns, not straights, dominate small-area survey time.
- Optional refinement if you have time: solve the inter-cell traversal order as a Generalized TSP (Bähnemann et al.) rather than naive graph traversal.

**Reject:** frontier-based or random exploration (no completeness guarantee), and pure Voronoi partitioning (does not equalise workload, so one drone finishes late and sets the mission clock).

### 2.4 Task allocation for deliveries: **CBBA (Consensus-Based Bundle Algorithm)**

Choi, Brunet & How, *IEEE Trans. Robotics* 25(4), 2009. Each drone builds a bundle of tasks by greedy bidding, then a consensus routine resolves conflicting claims over local communication. It provably converges to a conflict-free assignment with bounded worst-case performance, and it is the standard in the multi-UAV SAR literature. Open-source Python implementations exist to prototype against.

- **Bid function:** score each survivor task on `w1·(travel time) + w2·(payloads remaining) + w3·(battery margin) − w4·(detection confidence)`. Tune weights in simulation.
- **Handle the dynamic case:** survivors appear during the sweep. Use a replanning variant (CBBA with local/partial replanning) so a newly found survivor triggers a bounded reassignment instead of a full global reallocation.
- **Degraded mode:** if consensus cannot be reached within N seconds (link loss), each drone falls back to a deterministic tie-break — lowest system ID wins the contested task. Never leave a task unclaimed.

### 2.5 Flight stack: **ArduPilot or PX4 + companion computer, MAVLink 2 with distinct SYSIDs**

- Flight controller runs the proven autopilot; a companion computer (Jetson-class) runs perception, the swarm agent, and the mission state machine, talking to the FC over MAVLink 2 or uXRCE-DDS.
- Every aircraft gets a **unique MAVLink SYSID**; a single router (mavlink-router / MAVProxy) on the ground multiplexes all three into **one** GCS process. This is how you satisfy "one Ground Control Station" without writing an autopilot.
- Use **ROS 2 with DDS** for the swarm layer over the mesh. DDS's discovery and QoS handling map well to a lossy, mobile network. Aerostack2 and similar ROS 2 multi-UAV frameworks are worth studying before writing your own.

**Note for NIDAR 2.0 specifically:** the competition's Component track centres on the indigenous VEGA (RISC-V) flight controller. Check whether the Drone Innovation track awards any indigenisation credit; if so, evaluate a VEGA-based FC as a stretch goal on a separate branch, never on the critical path.

### 2.6 Communications: **dual-band — broadband mesh primary, narrowband command backup** [SCORE-DEPENDENT on video quality expectations]

Constraint C12 forbids any external network. So:

- **Primary:** a team-owned Wi-Fi-based ad-hoc/mesh link (802.11s or a mesh radio module) carrying telemetry, shared mission state, and video. In India, **5.825–5.875 GHz is delicensed specifically for drone use**; 2.4 GHz ISM is also delicensed. Verify current WPC/DoT SRRF exemption terms and power limits, and confirm your radio has **Equipment Type Approval (ETA)**.
- **Backup / safety channel:** a low-rate sub-GHz link (India's delicensed 865–867 MHz band) carrying only heartbeat, abort and recall. The hybrid Wi-Fi-mesh + LoRa architecture is well documented for UAV swarms (Marchese et al., *Drones* 5(2), 2021): 802.11s gives low latency and throughput at short-to-mid range, LoRa gives range and resilience at low rate. Safety commands belong on the resilient link.
- **Video budget is the hard part.** C11 requires a live feed on the GCS. Do not attempt three simultaneous 4K streams. Stream **one** low-bitrate (720p, 1–2 Mbps, H.264/H.265 hardware-encoded) feed from the drone currently in the most operationally interesting state, switched automatically by the mission state machine, plus detection thumbnails from all three. Measure your actual link throughput in Phase 4 and size accordingly.
- **Design the whole system to survive link loss.** Requirement SYS-28: a drone that loses the mesh for 10 s continues its assigned bundle autonomously; at 60 s it RTHs. Never build a behaviour that requires the link to make progress.

### 2.7 Perception: **RGB + tiled YOLO-class detector, trained on SAR-specific data**

- **Do not use a COCO-pretrained detector off the shelf.** Aerial SAR targets occupy roughly 0.1 % of the frame and appear in atypical postures — lying, kneeling, partially occluded. General person detectors fail on exactly this distribution.
- **Datasets to train/fine-tune on:** **HERIDAL** (~1,650 high-res UAV images, ~3,200 person annotations, built with SAR-expert input), **SARD** (~1,980 FHD frames from 15–75 m altitude with subjects simulating injured/exhausted postures), and **WiSARD** (synchronised RGB + thermal). Published baselines: YOLOv5L reaches ~0.90 precision / ~0.89 recall on HERIDAL; specialised networks report higher. Use these as your sanity benchmark — if you are far below, your training is wrong, not the task.
- **Then collect your own dataset in the actual conditions.** Flood-affected semi-urban ground, Indian daylight, your camera, your altitudes, mannequins in the postures the organisers are likely to use. Target 2,000+ annotated frames. This is the highest-leverage work in the whole project and it takes months, so start it in Phase 2, not Phase 7.
- **Tiled inference:** use **SAHI** (Slicing Aided Hyper Inference, Akyon et al., ICIP 2022) or an equivalent tiling scheme. Resizing a 4K frame to 640×640 destroys small targets; slicing into overlapping tiles (~20 % overlap) and merging detections recovers them, with large reported recall gains on small-object aerial imagery.
- **Inference rate is not your bottleneck — exploit that.** At 8 m/s and 60 m AGL the along-track footprint is ~46 m, so 2–5 Hz gives massive frame overlap. That budget lets you afford tiling. A Jetson Orin Nano running a TensorRT-optimised YOLO at 640×640 achieves ~24–40 FPS depending on model; a 4-tile scheme at 5 Hz needs 20 tile-inferences/sec, which fits.
- **Suppress false positives with temporal and cross-agent confirmation:** require the same ground position to be detected in ≥ 3 frames (or by 2 agents) before it is promoted from *candidate* to *confirmed survivor* and becomes a biddable delivery task. This is the main defence against wasting a finite payload on a rock.
- **Thermal:** genuinely helpful for SAR, but the brief specifies daylight outdoor conditions, and thermal costs mass, money and a second calibration pipeline. Treat as a Phase-10 stretch enhancement, not baseline.

### 2.8 Geotagging: **ray–ground intersection + multi-frame fusion**

Compute the survivor's ground position by projecting the detection's image coordinates through the camera intrinsics, rotating by the aircraft/gimbal attitude, and intersecting with a local ground plane (or DEM if available) at the launch-site elevation.

- **Error budget:** GNSS position error (±2.5 m standard, ±0.03 m RTK), attitude error (magnetometer disturbance is the usual culprit — an attitude error of 1° at 60 m AGL is ~1 m of ground error), camera calibration, and terrain-height assumption. Published monocular UAV geolocation work sees several metres of error dominated by GNSS and attitude.
- **Fuse across frames.** A single-frame estimate is noisy; run a Kalman/least-squares filter over the 10–30 frames in which the target is visible during a pass. This is essentially free and typically halves the error.
- **Strongly consider a local RTK base station** at the launch site. It converts GNSS from the dominant error term to a negligible one, improving both geotag accuracy and drop accuracy, and it is a **team-owned local link** — not GSM, not internet, not cloud. **Confirm with the organisers in writing** that a local RTK base is permitted under §5 before you build around it; NTRIP-over-internet corrections would clearly violate the rule.
- **Calibrate the camera properly** (OpenCV checkerboard, full intrinsics + distortion) and **calibrate the camera-to-body extrinsic mount angles** by flying over surveyed ground markers and solving for the residual. Teams routinely skip the second one and eat a systematic 3–5 m bias.

### 2.9 Payload delivery: **stop-and-drop from low hover, servo release** [SCORE-DEPENDENT]

Two options:

| Approach | Accuracy | Time cost | Complexity |
|---|---
