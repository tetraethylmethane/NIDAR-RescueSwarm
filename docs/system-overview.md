# RescueSwarm — System Overview

The long-form description of how the system works. The README is the summary;
this is the detail behind it.

---

## Mission flow

```text
Launch (sequenced, one aircraft at a time)
   │
   ▼
Load Mission Boundary ──► DARP equal-area partition
   │
   ▼
Climb to search altitude · altitude-stratified per aircraft
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

Search and delivery overlap. Drones don't wait for the sweep to finish before
starting deliveries.

---

## Architecture

```text
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

**The GCS is a view, not a controller.** Rule 8.16 makes any GCS-originated
retask a manual intervention worth −50 points, so the ground station is built
read-only by construction. The violation is structurally impossible rather than
avoided by discipline.

**Autonomy is hybrid:** centrally partitioned on the ground (deterministic,
inspectable, fast), decentrally executed in the air (survives link loss). A drone
that loses the mesh for 10 s continues its assigned bundle; at 60 s it returns
home. No behaviour requires the link to make progress.

---

## Methods and sources

Every algorithmic choice traces to published work rather than intuition.

| Layer | Method | Source |
|---|---|---|
| Area partitioning | DARP — equal-area, connected sub-regions anchored to a common launch point | Kapoutsis, Chatzichristofis & Kosmatopoulos, *JINT* 86 (2017) |
| Coverage within a region | Boustrophedon cellular decomposition, sweep along the longest axis | Choset, *Autonomous Robots* (2000) |
| Delivery task allocation | CBBA — consensus-based bundle auction, conflict-free over local comms | Choi, Brunet & How, *IEEE T-RO* 25(4) (2009) |
| Dynamic reallocation | Partial replanning variant, bounded reassignment on new detections | Buckman, Choi & How, *AIAA SciTech* (2019) |
| Small-object detection | SAHI tiled inference — recovers recall that whole-frame resizing destroys | Akyon, Altinuc & Temizel, *ICIP* (2022) |
| Detector training data | HERIDAL + SARD for pre-training, Indian field data for fine-tuning | Božić-Štulić et al.; Sambolek & Ivašić-Kos, *IEEE Access* (2021) |
| Airdrop error model | Release-velocity dominance in ballistic dispersion | Mathisen et al., *Autonomous Robots* (2020) |
| Mesh comms | batman-adv L2 mesh + sub-GHz safety channel | Marchese et al., *Drones* 5(2) (2021) |
| Propulsion sizing | Momentum theory with figure of merit (FM = 0.60) | Standard rotorcraft practice |
| Systems process | V-model with TRL gates, spiral overlay on high-uncertainty subsystems | NASA SE Handbook SP-2016-6105 |

---

## Perception

> **Terminology.** "SAR" in the dataset names below means **Search And Rescue**,
> not Synthetic Aperture Radar. HERIDAL and SARD are public aerial *photographic*
> datasets of people in search-and-rescue scenarios. **There is no radar on this
> aircraft.**

### Why a plain RGB camera

The only sensor is a **12 MP RGB camera with a 6 mm lens** (BOM tab 01, rows
35–36). That is a deliberate choice, not a default:

| Alternative | Why not |
|---|---|
| **Synthetic aperture radar** | Tens of kg and hundreds of watts. The whole aircraft is 5.88 kg with a 200 g payload allowance. Not physically possible in this class. |
| **Thermal / LWIR** | **It would fail on the actual targets.** The organisers confirmed survivors are *human-looking dummies*. A mannequin sits at ambient temperature, so a thermal camera sees no body-heat signature to separate it from the ground. Thermal detects the one thing these targets do not have. |
| **Lidar** | Gives structure, not identity. A prone human and a log are similar point clouds; and it adds mass and power for a problem RGB already solves. |

RGB also happens to be **required anyway**: rule 8.14 obliges the GCS to display a
live camera feed from every drone, so a camera is on the aircraft regardless of
what detects the survivors. And the mission is flown "under standard daylight
conditions" (MB §7), which removes the usual reason to reach for thermal or radar
— night capability.

Resolution is not the constraint either. CNN detectors need 20–30 px on target;
at 40 m this camera gives **140 px on a prone adult**, clearing that by 5×.

> **Product-roadmap note, not a competition change.** For *real* flood response,
> thermal is genuinely valuable — live humans emit heat and it works at night. The
> reason it is wrong here is specific to dummies being scored in daylight. Worth
> saying explicitly in the business pitch (§7 competitive advantage, §9 adoption
> readiness) rather than letting a jury assume RGB-only was an oversight.

### The detection problem

A COCO-pretrained person detector will fail here. Aerial search-and-rescue targets occupy
~0.1 % of frame area, lying prone or partially covered — a distribution general
detectors have never seen.

- **Pre-train** on HERIDAL and SARD, and reproduce the published baselines
  (YOLOv5L reaches ~0.90 P / ~0.89 R on HERIDAL) to prove the pipeline before
  trusting our own data.
- **Fine-tune on Indian field data.** HERIDAL and SARD are European — wrong
  terrain, vegetation, clothing and sun angle. Target ≥2,000 annotated frames
  from our own camera at our own altitude, with mannequins supine, prone, seated
  and partially occluded.
- **Tiled inference** at 2× downsample, 640 px tiles, 20 % overlap, 2 Hz.
- **Exploit the frame surplus.** At 8 m/s and 40 m the along-track footprint
  gives roughly a dozen looks per target per pass, so multi-frame fusion is
  effectively free — use it for temporal confirmation and for geolocation
  averaging.
- **Gate on body rate.** Suppress inference above 15 °/s: the imagery is smeared
  and the ground-plane assumption is worst in a bank. The turns fall outside the
  search region anyway.
- **Prefer near-nadir detections for geotagging.** The ground-height error term
  is `Δh·tan θ`, so a detection at the frame edge carries 0.62× the height error
  while one within 20° carries 0.36×. With a dozen looks available, edge
  detections can be discarded and re-acquired near nadir for free.

Detection recall is the long pole of the programme and is worth 250 of the 600
flight points. Field data collection starts in P1, not P5.

---

## Indigenisation

NIDAR exists to move India "from drone assembly to manufacturing the drone's
brain in India". This build takes that seriously and reports it honestly.

| Basis | Score |
|---|---|
| Line items with an Indian supplier | 95.5 % |
| Programme value that is Indian | 60.2 % |
| Flight-hardware value that is Indian | 56.8 % |
| Payload, kits and ground-truth targets | 100 % |

The gap between 95 % and 60 % isn't evasion. An Indian flight controller or
camera module is Indian design, firmware and manufacture on imported silicon, and
the BOM scores that at 60 % rather than 100 %. Always state which basis you're
quoting.

Two indigenisation choices that improve the system rather than compromise it:

- **NavIC.** ISRO's constellation sits directly overhead India — more satellites,
  faster time-to-first-fix (which buys margin in the setup window), and a
  fallback if GPS is degraded or jammed.
- **C-DAC VEGA.** The free RISC-V dev kits run the payload-release controller and
  failsafe watchdog — real Indian silicon flying, on a subsystem with a hardware
  bypass, off the flight-critical path.

Four things have no Indian option and are declared as such: AI inference silicon
(~20 TOPS class), high-drain 21700 cells at 45 A, 802.11/LoRa RF chipsets, and
high-current connectors.

Suppliers: Bharath Components · Mechtex · Flameback Tech · S R Aerospace · Agam
Robotics · Zuppa · Teravolt Labs · Accord Software · e-con Systems · FxUAV
Technologies · Kineco · Sundram Fasteners. Full BOM in
[`../hardware/bom/`](../hardware/bom/).

---

## Safety and failsafes

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

Deconfliction is layered: altitude stratification during search, exclusive
spatial locks around each survivor during delivery, reciprocal velocity-obstacle
avoidance as a runtime backstop, and strictly sequenced launch and recovery
through the 3.66 m box.

**Payload release requires a positive mechanical lock independent of servo
power.** A brownout must not drop a kit.

Vortex ring state is a live hazard on every delivery — the descent to 6 m is
near-vertical with nulled groundspeed, which is exactly the condition VRS needs.
See [`sizing/configuration-trade.md`](sizing/configuration-trade.md) §5.1.

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

## Working rules

- No new autonomy code touches a real airframe until it has run 20 consecutive
  clean SITL missions. SITL cycles cost minutes; a crash costs weeks.
- Every real flight runs a tagged commit, logged in the flight log with the tag.
- If a document disagrees with `docs/sizing/model-output.txt`, re-run the model
  and fix the document — not the reverse.
