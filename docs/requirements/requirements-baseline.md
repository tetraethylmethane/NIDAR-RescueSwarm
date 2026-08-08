# RescueSwarm — Requirements Baseline
### Phase 0 gate deliverable · every rule clause maps to a testable requirement

**Traceability.** Every requirement below traces to a rulebook clause (`8.x`),
mission-brief section (`MB §n`), or a scoring criterion (`4D-n`). Requirements
marked **[SCORED]** have their target derived from the scoring structure rather
than chosen as a round number — see
[`rulebook-compliance.md`](rulebook-compliance.md) §1 and
[`../sizing/delivery-accuracy-output.txt`](../sizing/delivery-accuracy-output.txt).

**Verification methods:** T = Test · D = Demonstration · A = Analysis · I = Inspection

---

## 1. Changed requirements

Three targets in the previous baseline were wrong against the rulebook. Recorded
here explicitly because they were quoted in the README and in the sizing document.

| ID | Was | Now | Why |
|---|---|---|---|
| SYS-12 | Geotag CEP50 ≤ 2.0 m (RTK) | **CEP50 ≤ 0.75 m (0.91 m RSS)** | At 2.0 m, Zone A is unreachable regardless of drop quality. Geotag is 75–83 % of delivery error variance. |
| SYS-15 | ≥ 90 % of drops within **5.0 m of tag** | **≥ 60 % within 2.0 m and ≥ 30 % within 1.0 m of the survivor** | 5.0 m is outside every scoring zone and scores **zero**. Measurement datum is the survivor, not the tag. |
| SYS-21 | Setup to launch ≤ 240 s | ≤ 240 s *(unchanged — internal target against a 300 s rule)* | Retained; 15 s modelled margin is unmeasured. |

---

## 2. Mission performance **[SCORED]**

| ID | Requirement | Source | Method | Phase |
|---|---|---|---|---|
| SYS-01 | Fleet all-up weight ≤ 25.0 kg fully loaded, including batteries, sensors, comms and payload mechanisms | 8.9, MB §2 | T (calibrated scale) | P6 |
| SYS-02 | Deploy ≥ 2 drones operating as one coordinated mission system | 8.8, MB §1 | D | P9 |
| SYS-03 | Airframe shall not be a commercially available market-ready or ready-to-fly complete drone | **8.2** | I (design evidence) | P1 |
| SYS-05 | Search the full assigned area up to 10 ha within the mission window | 8.11, MB §1 | T | P9 |
| SYS-07 | **[SCORED 250]** Detect ≥ 90 % of survivors present, up to 10 | 4D-1, 8.11 | T | P7, P9 |
| SYS-12 | **[SCORED 250]** Geotag each detected survivor to **CEP50 ≤ 0.75 m** (0.91 m RSS), displayed on the GCS | 4D-1, 8.11 | T vs surveyed ground truth | P7 |
| SYS-13 | Geotag shall use RTK corrections; degraded mode without RTK shall be flagged on the GCS | 4D-1, derived | T | P7 |
| SYS-15 | **[SCORED 200]** Of ≥ 30 test drops in ≤ 3 m/s wind, **≥ 60 % land within 2.0 m** and **≥ 30 % within 1.0 m** of the survivor | 4D-2 | T | P8 |
| SYS-16 | Deliver a kit of exactly 200 g, 200 × 100 × 50 mm rectangular box | 8.12, MB §2 | I | P5 |
| SYS-17 | Payload deployment shall be fully autonomous | 8.12, MB §3 | D | P8 |
| SYS-31 | Release gated at ≤ 0.30 m/s residual groundspeed | derived (4D-2) | T | P8 |
| SYS-32 | Release aim point compensated for estimated wind drift, ≥ 70 % of drift removed | derived (4D-2) | T | P8 |
| SYS-33 | Geotag only detections within ≤ 20° off-nadir; edge detections re-acquired near nadir | derived (4D-1) | A + T | P7 |
| SYS-34 | Field ground elevation surveyed or measured during setup; ground-plane assumption error ≤ 1.0 m | derived (4D-1) | T | P7 |
| SYS-35 | **[SCORED 50]** Complete the mission within 15 min (half the permitted 30) | 4D-5 | D | P9 |
| SYS-37 | Retain positive headway at **10 m/s sustained wind**; size search *airspeed* for it while flying 8 m/s *groundspeed* nominally | derived — wind is natural and uncapped | T | P6 |
| SYS-38 | Parse a **KML** boundary polygon and partition it without operator editing, inside the 30 s setup allowance | organiser answer | T | P4 |
| SYS-39 | Fine-tune the detector principally on imagery of **human-looking dummies** at operational altitude, not live people | organiser answer | T | P7 |
| SYS-40 | Kit delivered by **free-fall from 6 m**, not under a canopy | derived (4D-2) | T | P8 |

## 3. Autonomy and control

| ID | Requirement | Source | Method | Phase |
|---|---|---|---|---|
| SYS-19 | **[SCORED −50 each]** Zero operator input beyond mission-file load, start, safety abort, emergency recall | 8.16, MB §3 | D | P9 |
| SYS-20 | GCS shall be incapable of originating a retask, waypoint change or drop command by construction. **Abort and recall are exempt** — permitted by 8.16 and required by 8.19 | 8.16 | I (source review) | P2 |
| SYS-21 | Setup to launch ≤ 240 s internal target against the 300 s rule, with 2 people | MB §3, MB §6 | D (20 timed runs) | P10 |
| SYS-22 | Mission file received during setup, parsed, partitioned and rendered without operator editing | MB §3 | D | P9 |
| SYS-42 | RTK base positioned, powered and set to a fixed reference from its **first 3D fix**, inside the setup window, **without survey-in** | organiser answer + setup budget | T | P5 |
| SYS-43 | Launch gated on a **3D fix, not an RTK fix**. First geotag gated on RTK-fixed; earlier detections geotagged in float and re-fused once fixed | derived — setup budget | T | P7 |
| SYS-24 | **[SCORED 50]** Collaborative execution: area allocation, task distribution, coordination, consolidated reporting | 4D-3, 8.15 | D | P9 |
| SYS-28 | Autonomous continuation on C2 loss; RTH at 60 s | 8.19, MB §8 | T (fault injection) | P4, P9 |
| SYS-29 | No component swapped, replaced or added after mission start | MB §3 | I | P9 |

## 4. Ground control station

| ID | Requirement | Source | Method | Phase |
|---|---|---|---|---|
| SYS-25 | **[SCORED 50]** Single GCS and unified operator interface; no separate GCS per drone | 4D-4, 8.13, MB §4 | D | P9 |
| SYS-26 | GCS displays: mission status · **live camera feed from each drone** · position of each drone · assigned area/task per drone · geotagged survivors · kit delivery status · comms and system health · consolidated progress | **8.14** | D | P9 |
| SYS-27 | Downlink shall carry three concurrent video feeds within the link budget; per-feed rate reduced rather than feeds switched | 8.14, derived | A + T | P5 |

## 5. Communications

| ID | Requirement | Source | Method | Phase |
|---|---|---|---|---|
| SYS-23 | No GSM, LTE, 5G, public Wi-Fi, internet or cloud used at any point in the mission | 8.4, 8.17, MB §5 | I + A | P9 |
| SYS-30 | No optical fibre, wired link, tether or any cable connected to a drone in flight | **8.5**, MB §5 | I | P6 |

## 6. Safety, launch and recovery

| ID | Requirement | Source | Method | Phase |
|---|---|---|---|---|
| SYS-08 | **[SCORED −10/drone]** All drones launch from and land within the 12 ft × 12 ft area, no part outside during launch or landing | 8.10, MB §7 | D | P9 |
| SYS-09 | **[SCORED −20/instance]** All drones remain within the mission boundary | 8.18, MB §7 | T | P9 |
| SYS-10 | **[SCORED −50/crash]** No crash, uncontrolled ground impact or crash landing | 4D-penalty | D | P9 |
| SYS-11 | Failsafes for: low battery · C2 link loss · geofence breach · mission abort · emergency recall · RTH. Four are ArduPilot parameters ([`firmware/ardupilot-params/`](../../firmware/ardupilot-params/)); abort and recall are the [safety link](../../communication/safety_link/) — **built, radio not yet connected** | 8.19, MB §8 | T (fault injection) | P6 |
| SYS-18 | Payload release requires a positive mechanical lock independent of servo power | derived (safety) | T | P5 |
| SYS-41 | Each aircraft carries a recovery parachute, armed above 20 m AGL and inhibited below it | organiser answer + derived | T | P6 |
| SYS-36 | Pass the Pre-Flight Inspection on the first attempt | **4.29–4.32** | I | P10 |

## 7. Programme and deliverables

| ID | Requirement | Source | Method | Phase |
|---|---|---|---|---|
| PRG-01 | Team of 4–10 students, **interdisciplinary** (≥1 from another branch), plus **one faculty member** | 3.6–3.8 | I | P0 |
| PRG-02 | Registration submitted with institution approval letter, team details, ID proofs and fee | 4.5–4.6 | I | **P0 — immediate** |
| PRG-03 | Attend Progress Review 1 (Oct 2026) and Progress Review 2 (Dec 2026); both mandatory | 4.14 | D | P3, P6 |
| PRG-04 | **[SCORED 200]** Design Review presentation covering the nine scored parameters | 4A | D | P10 |
| PRG-05 | **[SCORED 200]** Business Strategy presentation covering the nine scored parameters | 4B | D | P10 |
| PRG-06 | Bill of Materials **and cost sheet** submitted | **7.5** | I | P10 |

---

## 8. Engineering requirements from the sizing model

These come from §17 of [`../sizing/sizing-calculations.md`](../sizing/sizing-calculations.md),
which maintained a **second, colliding SYS-xx register**. Reconciled here; that
document now points at these IDs rather than defining its own.

| ID | Requirement | Source | Method | Phase |
|---|---|---|---|---|
| SYS-04 | Thrust-to-weight ≥ 2.0 static at MTOW; hover throttle 45–55 % | sizing §6 | T (thrust stand) | P5 |
| SYS-06 | Peak current capability ≥ 90 A; ESC ≥ 50 A each; 10 AWG mains | sizing §6 | T | P5 |
| SYS-14 | Hover endurance ≥ 15 min at MTOW; land with ≥ 25 % SoC | sizing §4, §9.1 | T | P6 |
| SYS-44 | Search altitude held to ±5 m; GSD ≤ 2.0 cm/px ⚠ *altitude under review — 40 m recommended* | sizing §8 | T | P7 |
| SYS-45 | Shutter ≤ 1/1000 s; inference gated at body rate < 15 °/s | sizing §8.1 | T | P7 |
| SYS-46 | Detection at ≥ 2 Hz with ≥ 12 frames per target per pass | sizing §8.2 | T | P7 |
| SYS-47 | Constant **groundspeed** 8 m/s during sweep, wind-compensated | sizing §9.2 | T | P6 |
| SYS-48 | Boresight and lever-arm calibration completed before any accuracy claim | sizing §11 | I + T | P7 |
| SYS-49 | Payload released at 6 m AGL | sizing §10 | T | P8 |
| SYS-50 | Kit survives a 9.7 m/s impact | sizing §10 | T | P5 |
| SYS-51 | Link margin ≥ 13 dB at 600 m; offered load ≤ 3 Mbps | sizing §12 | A + T | P5 |
| SYS-52 | Sequenced launch and recovery, one aircraft at a time through the box | sizing §13 | D | P9 |
| SYS-53 | Compute-bay forced-air cooling active from power-on | sizing §14 | T | P5 |

### 8.1 Superseded by the rulebook

The old sizing register contained four requirements that the scoring structure
has since overturned. They are listed here so that anyone who read the sizing
document before this reconciliation can see what changed.

| Old sizing ID | Old text | Superseded by |
|---|---|---|
| SYS-12 | Geotag CEP50 ≤ 2.0 m (RTK) | **SYS-12** — CEP50 ≤ 0.75 m. Zone A is unreachable at 2.0 m. |
| SYS-15 | Delivery CEP ≤ 3 m | **SYS-15** — ≥ 60 % within 2 m, ≥ 30 % within 1 m. 3 m is the worst-scoring zone. |
| SYS-20 | "…one video feed" | **SYS-26/27** — rule 8.14 requires a feed from *each* drone. |
| SYS-17 | Mission ≤ 12 min | **SYS-35** — ≤ 15 min is what the bonus actually needs. |

`SYS-01` also appeared in both registers with different numbers: the sizing
document's **≤ 24.0 kg** is an internal build-margin target against the rulebook's
**≤ 25.0 kg** limit. Both stand; SYS-01 here carries the rule, and 24.0 kg is the
internal target the fleet is designed to.

---

## 9. Requirements with no verification yet planned

Honest gaps, to be closed before the P0 gate can be called complete:

| ID | Gap |
|---|---|
| SYS-21 | Setup timing is **modelled, not measured**. 15 s of margin on the binding constraint. Bench measurement is the highest-priority test in the programme. |
| SYS-07 | Recall target of 90 % is asserted, not demonstrated. Needs field data at the chosen altitude. |
| SYS-12 | **RTK confirmed permitted**, so 0.91 m RSS is reachable and the target stands. Remaining risk is the 0.70 m *unmodelled* allowance, now the largest single term in case C (60 % of variance) — it shrinks only by measuring in P7. |
| SYS-15 | **Datum confirmed as the survivor**, so geotag and dispersion compound as budgeted. Open: *which point* on the survivor — up to 0.85 m of ambiguity for a prone adult against a 1 m Zone A. See [`rulebook-compliance.md`](rulebook-compliance.md) §4.5. |
| SYS-33 | The 0.50 m target-extent/centroid term is the second-largest in case C (31 % of variance) and is partly irreducible until the datum question above is answered. |
| SYS-36 | Model Pre-Flight Inspection checklist is "to be released separately" (4.31) and is not yet available. |
| SYS-20 | **Resolved, structurally.** In a mission build the legacy `/uav` blueprint is **not registered at all** — its 31 routes are absent from the URL map rather than refused. The 403 guard remains as defence in depth. Enforced against the live app by `test_app_smoke.py`. |
| SYS-23 | **Resolved for the GCS.** Poller removed in NIDAR-GSC `ab8c09d`; `scripts/check-no-network.sh` guards it. Tile-cache tooling repaired in `9f904a7` — it previously cached error pages as tiles, which would have shown a blank map on the day. **No tiles are cached yet**: needs venue coordinates, and must be run weeks ahead. Still to verify: the aircraft side, and the whole system with interfaces physically down (P9). |
| SYS-25/26/27 | **Resolved and demonstrated.** Verified against three real ArduCopter SITL autopilots with a browser on the page: all eight 8.14 displays, three live H.264 feeds through MediaMTX, offline tiles rendering, abort acknowledged end to end (NIDAR-GSC `aab36ec`). 118 server + 22 render tests + a browser check, all in CI. **The ingest was receiving no telemetry at all** until it began requesting streams — ArduPilot sends a passive listener only heartbeats. Outstanding: flight validation. |
