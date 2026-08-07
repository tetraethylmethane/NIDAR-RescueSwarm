# RescueSwarm — Rulebook Compliance and Scoring Strategy
### Source: NIDAR Rulebook 2026–27 v2.0 (13 July 2026) · Annexure 1 Mission Brief — M1 RescueSwarm

Derived directly from the rulebook and mission brief. Where this document
disagrees with `sizing-calculations.md`, the README or `configuration-trade.md`,
**the rulebook wins** and the other document is wrong.

---

## 0. Urgent — schedule

| Milestone | Date | Notes |
|---|---|---|
| **Application & registration deadline** | **2nd week August 2026** | **INR 5,000 fee, non-refundable. Needs institution approval letter, team details with Govt + College ID, payment proof.** |
| Verification | 3rd week Aug 2026 | M1 teams auto-shortlisted (4.12) — no concept proposal required |
| Online Presentation & Shortlisting | 3rd week Sept 2026 | Not a filter for M1 |
| **Progress Review 1** | **2nd week Oct 2026** | Attendance mandatory (4.14), non-eliminating (4.16) |
| **Progress Review 2** | **2nd week Dec 2026** | Attendance mandatory |
| **Finals 4A–4D** | **January 2027** | Design Review, Business Strategy, Pre-Flight Inspection, Final Mission |

### 0.1 The development plan overruns the competition

`docs/development-plan.md` runs a **30-week** programme with P10 "competition
ready". Finals are **January 2027**, roughly **22 weeks** from registration in
August 2026. **The plan is ~8 weeks longer than the competition allows.**

The plan must be re-baselined against these dates, not against a 30-week
abstraction. Two fixed interior checkpoints now exist that the plan does not
acknowledge: **Progress Review 1 in October** and **Progress Review 2 in
December**.

---

## 1. Scoring structure — and what it overturns

**Total 1000 points.**

| Phase | Max | Share |
|---|---|---|
| 4A Design Review Presentation | 200 | 20 % |
| 4B Business Strategy Presentation | 200 | 20 % |
| 4C Pre-Flight Inspection | **Pass/Fail** | gate, one retry only (4C table) |
| 4D Final Mission (flight) | 600 | 60 % |

### 1.1 Final Mission — 600 points

| # | Criterion | Method | Max |
|---|---|---|---|
| 1 | **Survivor Detection & Geotagging** | 25 per survivor correctly detected **and** correctly geotagged on the GCS. Max 10. | **250** |
| 2 | **Survivor Kit Delivery Accuracy** | Per drop, by zone. Max 10 drops. **Zone A ≤1 m: 20** · **Zone B ≤2 m: 14** · **Zone C ≤3 m: 8** | **200** |
| 3 | Multi-Drone Collaborative Execution | Binary — all-or-nothing | 50 |
| 4 | Single GCS / Mission Planner Interface | Binary | 50 |
| 5 | Fast Completion Bonus | Binary — mission within **half** the permitted time (**≤15 min**) | 50 |

**Penalties** (capped at 150 total, except safety-critical which may terminate or
disqualify): landing outside zone −10/drone · geofence breach −20/instance ·
repeat breach by same drone −20 · **manual input or reset −50/instance** ·
**crash −50/crash**.

### 1.2 Three conclusions that change the design

**(a) The ≤3 m delivery target is the worst-scoring zone.**
The current design target — "≤ 3 m CEP from a 6 m hover-and-drop" — lands in
**Zone C, worth 8 points of an available 20**. Across 10 drops that is 80 points
instead of 200. **The delivery requirement must be re-baselined to ≤1 m.**

**(b) Geolocation accuracy gates 450 of the 600 flight points, not 250.**
Detection + geotag is 250 directly. But the delivery zones are measured from the
survivor, so **a kit can be no more accurate than the tag it was aimed at**: total
delivery error is the geotag error compounded with the release dispersion. With
geotag CEP50 at 2.0 m, Zone A is unreachable no matter how good the drop is.

This makes geolocation the single highest-leverage engineering objective in the
programme, and it makes **RTK a scoring requirement rather than an optimisation**.
The error budget in `sizing-calculations.md` §11 already shows the path: case D
(RTK + multi-frame fusion + calibrated ground plane) reaches 0.91 m RSS, which is
the only case that puts Zone A in reach.

**(c) Speed is worth 50 points and is already won.**
The bonus needs only ≤15 min against a **7.7 min** design mission — roughly
double the margin required. Speed beyond that scores **nothing** (it breaks ties
only, 9.3). The programme has been optimising a resource that is both abundant
and nearly worthless.

**Spend the time margin on accuracy.** Flying lower, flying slower, taking more
frames per target, and hovering longer before release all convert surplus time
into the 450 points that geolocation gates. This strongly reinforces the altitude
recommendation in `configuration-trade.md` §5.3 — and the budget supports going
below 40 m, since even a 30 m sweep (187 s/drone) leaves the mission far inside
the 15 min bonus threshold.

### 1.3 Business Strategy is 200 points and is not addressed anywhere

| # | Parameter | Max |
|---|---|---|
| 1 | Problem Understanding & Real-World Relevance | 30 |
| 2 | Target Users, Customers & Beneficiaries | 20 |
| 3 | Market Sizing & Deployment Potential | 30 |
| 4 | Business Model & Revenue Approach | 30 |
| 5 | Expenditure Breakdown & Resource Planning | 20 |
| 6 | Funds Raised, Sponsorships & Resource Mobilisation | 20 |
| 7 | Competitive Advantage & Differentiation | 20 |
| 8 | Go-to-Market Strategy & Partnership | 20 |
| 9 | Regulatory, Safety & Adoption Readiness | 10 |

**This is worth exactly as much as the entire Design Review, and the repository
contains nothing addressing it.** A detailed cost sheet and BOM are required
deliverables (7.5) — the BOM exists in `hardware/bom/`, the cost sheet does not.
Item 6 (funds raised, sponsorships) has lead time and cannot be produced the week
before finals.

### 1.4 Design Review — 200 points

| # | Parameter | Max |
|---|---|---|
| 1 | Introduction, Team Composition & Domain Diversity | 10 |
| 2 | Overall Mission Architecture & System Design | 20 |
| 3 | Technical Approach, Drone Design & Indigenisation Strategy | 20 |
| 4 | Multi-Drone Collaboration & Task Allocation | 30 |
| 5 | Survivor Detection, Geotagging & Accuracy | 30 |
| 6 | Payload Delivery & Drop Accuracy | 25 |
| 7 | Autonomous Mission Execution & Time Efficiency | 30 |
| 8 | GCS, Mission Map & Multi-Drone Status Reporting | 20 |
| 9 | Fail-Safe Features & Safety | 15 |

The existing sizing and architecture work maps well onto items 2–7. Item 1
requires **domain diversity** — see §3 on team composition.

---

## 2. Compliance matrix

| Rule | Requirement | Status | Where |
|---|---|---|---|
| 8.8 / brief 1 | ≥2 drones as one coordinated system | **OK** — 3 aircraft | README |
| 8.9 / brief 2 | Combined AUW ≤ 25 kg | **OK** — 15.18 kg, 39 % margin | model-output |
| 8.2 / brief 2 | **No COTS ready-to-fly airframes**; components OK | **OK by intent** — custom frame | needs explicit design evidence for 4A |
| brief 2 | Payload exactly **200 g, 200×100×50 mm rectangular box** | **OK** | sizing §payload |
| 8.10 / brief 7 | Take off and land within 12 ft × 12 ft | **OK** — 1046 mm footprint, 3/row | model STEP 11 |
| brief 7 | **No part of any drone outside the box** during launch/landing | **OK** but tight with 3 airframes — verify staging geometry | — |
| 8.11 | Autonomously detect and geotag up to 10 survivors, display on GCS | Designed | perception/ |
| 8.12 | Autonomous kit delivery, 200 g, 20×10×5 cm | Designed | payload |
| 8.13 | Single GCS, unified operator interface | Designed | ground-station/ |
| **8.14** | GCS displays **live camera feed from EACH drone** | **⚠ CONFLICT — see §4.1** | RF budget assumes one switched feed |
| 8.15 | Collaborative execution: area allocation, task distribution, coordination, consolidated reporting | Designed — DARP + CBBA | autonomy/ |
| 8.16 / brief 3 | Manual waypoint change, flight-path correction, payload-release command, survivor tagging, replanning = **manual intervention** (−50 each) | **OK by construction** — read-only GCS | README architecture |
| 8.17 / brief 5 | No external network for execution, coordination or data exchange | **OK** — team-owned RF | comms |
| 8.5 / brief 5 | **No optical fibre, wired links, tethers or any cable connected to a drone in flight** | **OK** | — |
| 8.18 | Remain within mission boundary | Designed — geofence | failsafe matrix |
| 8.19 / brief 8 | RTH, comms-loss recovery, low-battery failsafe, geofence protection, mission abort | Designed | failsafe matrix |
| brief 3 | Mission file provided **during** setup, not before | **OK** — 30 s parse/partition modelled | setup budget |
| brief 3 | ≤5 min setup | **⚠ 285 s modelled, 15 s margin, unmeasured** | setup budget |
| brief 3 | ≤30 min flight time | **OK** — 7.7 min | mission segments |
| brief 3 | **No component swapped, replaced or added after mission start** | **OK** — no battery swap in plan | — |
| brief 6 / 4.34 | **Max 2 team members** for setup; C2 station operated/supervised by max 2 | **OK** — two-person choreography | setup |
| brief 6 | No assistance from any other member during setup, mission, recovery | Process constraint — rehearse accordingly | — |
| 4.29–4.32 | **Pre-Flight Inspection is a Pass/Fail gate, ONE retry only** | **Not yet planned for** | see §4.2 |
| 3.6–3.8 | Team 4–10 members, **interdisciplinary**, **one faculty member** | Verify | §3 |
| 7.5 | **Cost sheet + BOM** are required deliverables | BOM exists, **cost sheet missing** | hardware/bom/ |

---

## 3. Team eligibility (3.4–3.9)

- 4–10 student members; **must be interdisciplinary** — at least one member from a
  different branch (3.7). Design Review item 1 scores "Domain Diversity" directly.
- **One faculty member** in addition to students (3.8).
- All participants enrolled through to the Finals (3.9).
- A member may join only one team and one problem statement (3.1); no sharing of
  members, hardware, software or deliverables between teams (3.3).

---

## 4. Conflicts to resolve

### 4.1 Live video from every drone (8.14) breaks the RF budget

Rule 8.14 requires the GCS to display "**Live camera feed from each drone**". The
mission brief §4 says only "Live video feed display", but 8.14 is the specific and
binding text.

`sizing-calculations.md` §12.1 budgets **one switched 720p30 feed at 1.8 Mbps**,
for a 2.5 Mbps offered load, and explicitly warns that three simultaneous feeds
(5.4 Mbps) "would still fit at MCS3 but destroy the margin you are buying".

**This closes open question 6 unfavourably.** The RF design must carry three
concurrent feeds. Options, in rough order of preference:

1. Drop per-feed resolution/framerate (e.g. 480p15 per drone) so three feeds cost
   what one 720p30 feed does. Detection runs onboard — the downlink is for the
   judges, not for perception, so image quality is a scoring-display concern only.
2. Widen the channel or accept a lower link margin at a higher MCS.
3. Keep 720p but reduce framerate aggressively.

Option 1 preserves the deliberate low-MCS margin strategy, which remains right.
**Re-run §12.1 with a three-feed load before Design Review.**

### 4.2 Pre-Flight Inspection is an unplanned hard gate

4.29–4.32: a designated Flight Inspector verifies safety, readiness and compliance
of the drone system, C2 station and associated equipment. **Only one retry is
permitted**, and failing it means not flying at all — forfeiting the entire 600
points. A model checklist is to be released separately (4.31).

**PROPOSED:** treat this as a formal internal gate before the finals, and track the
model checklist's release. Nothing in the development plan currently corresponds
to it.

### 4.3 Delivery measurement datum still ambiguous

The zones are stated as "within 1 / 2 / 3 metres" but the rulebook does not say
**measured from what** — the true survivor position or the team's tagged position.
This materially changes the error budget: measuring from the true position means
geotag error and drop dispersion compound (§1.2b); measuring from the tag would
isolate drop dispersion alone.

**Still an open question for the organisers** — and now a higher-priority one,
because it determines whether 200 points depend on geolocation or not.

---

## 5. Open questions — revised

Answered by the rulebook, and to be removed from the list:

- ~~Scoring weights across mission time, detection, delivery, autonomy~~ → §1.
- ~~Automatic switching of a single video feed, or all feeds simultaneously?~~ →
  8.14 requires a feed from **each** drone.

Still open, in priority order:

1. **Is delivery accuracy measured from the true survivor position or the tagged
   position?** (§4.3 — gates 200 points.)
2. **Is a team-owned local RTK base station permitted**, given corrections travel
   on our own local link and not an external network? (Now scoring-critical, §1.2b.)
3. Is **pre-booting** of onboard computers permitted before the 5-minute window
   opens? (Setup has 15 s of modelled margin.)
4. Will survivors be **real humans, dummies, or both** — in what postures, clothing
   and degree of cover? (Brief says "real humans or dummies".)
5. What **shape, aspect ratio and file format** should the boundary polygon be?
6. Is a **ballistic parachute** permitted, and is motor-out tolerance separately
   required? (See `configuration-trade.md` §5.4.)
7. Is there a **maximum wind** condition under which the mission runs, or is it
   flown in whatever weather occurs? (See `configuration-trade.md` §5.2.)
