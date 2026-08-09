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

### 0.1 The development plan overran the competition — RESOLVED

The original plan ran a **30-week** programme against a **~21-week** calendar,
never mentioned registration, and ignored both mandatory progress reviews.

**Rewritten as [`../development-plan.md`](../development-plan.md)**, which is now
the single schedule authority. The reviews are phases **P3** and **P7**. The
binding constraint turned out not to be the 21 weeks at all, but the
**~8-week flight-test window** left once monsoon and end-semester exams are
accounted for.

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
instead of 200. **RESOLVED.** Re-baselined in [`requirements-baseline.md`](requirements-baseline.md).
The right requirement is not a single "≤1 m" figure but a distribution — see
[`../sizing/delivery-accuracy-output.txt`](../sizing/delivery-accuracy-output.txt),
which converts total error into expected points. Case C (RTK + fusion +
calibrated ground plane) yields **1.00 m total RSS → 17.7 pts/drop, 177 of 200**;
no RTK yields 3.09 m → **75 of 200**.

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

**This is worth exactly as much as the entire Design Review.** A detailed cost
sheet and BOM are required deliverables (7.5) — the BOM exists in
`hardware/bom/`, the cost sheet did not.

**PARTLY RESOLVED:** structure and preparation sequence in
[`../business/README.md`](../business/README.md), cost-sheet template in
[`../business/cost-sheet.md`](../business/cost-sheet.md). These are skeletons —
the content still has to be gathered, and **items 6 and 8 (funds raised,
partnerships) have lead time that cannot be recovered in January**.

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
| 8.9 / brief 2 | Combined AUW ≤ 25 kg | **OK** — 17.65 kg, 29 % margin | model-output |
| 8.2 / brief 2 | **No COTS ready-to-fly airframes**; components OK | **OK by intent** — custom frame | needs explicit design evidence for 4A |
| brief 2 | Payload exactly **200 g, 200×100×50 mm rectangular box** | **OK** | sizing §payload |
| 8.10 / brief 7 | Take off and land within 12 ft × 12 ft | **OK — at the CORNERS, not in a row.** 1046 mm footprint, slots 2.61 m apart, measured 2.27 m minimum in SITL | `simulations/recordings/proof-4-pad.png` |
| brief 7 | **No part of any drone outside the box** during launch/landing | **OK** — slot centres sit half an airframe inside the edge by construction | `autonomy/coverage_planner/plan.py` `pad_slots()` |
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

**RESOLVED — compliance is free.** Re-run in
[`../sizing/mission-profile-output.txt`](../sizing/mission-profile-output.txt) §3:
**three 480p15 H.265 feeds cost 1.80 Mbps, exactly what one 720p30 feed cost.**
Total offered load stays at the 2.5 Mbps the link was designed around (18 %
utilisation at MCS3), so the deliberate low-MCS margin strategy survives intact.
Three *720p30* feeds would push utilisation past 40 %, which is where latency and
jitter on a shared mesh begin to bite. Captured as **SYS-27**.

### 4.2 Pre-Flight Inspection is an unplanned hard gate

4.29–4.32: a designated Flight Inspector verifies safety, readiness and compliance
of the drone system, C2 station and associated equipment. **Only one retry is
permitted**, and failing it means not flying at all — forfeiting the entire 600
points. A model checklist is to be released separately (4.31).

**RESOLVED:** added as **SYS-36** in
[`requirements-baseline.md`](requirements-baseline.md) and as a mock inspection in
P8 of [`../development-plan.md`](../development-plan.md). The model checklist
(4.31) is still to be released — track it.

### 4.3 Delivery measurement datum — ANSWERED

**Delivery is measured from the survivor**, confirmed by the organisers.

Geotag error and release dispersion therefore compound, exactly as §1.2b assumed.
The budget in [`../sizing/delivery-accuracy-output.txt`](../sizing/delivery-accuracy-output.txt)
stands unchanged, and geolocation genuinely gates 450 of the 600 flight points.

### 4.4 RTK — ANSWERED, and now a committed design item

**A team-owned local RTK base station is permitted**, confirmed by the organisers.

Consequences, all of which were assumed and are now committed:

- **Case C (0.91 m RSS geotag) is reachable**, so SYS-12 at CEP50 ≤ 0.75 m stands
  and delivery is worth **177 of 200** rather than 75.
- The **RTK base station, survey tripod and ground radio move from conditional to
  required** in the BOM and cost sheet — see
  [`../business/cost-sheet.md`](../business/cost-sheet.md) §B.
- SYS-13 (degraded mode flagged on the GCS when RTK is unavailable) remains, as a
  failsafe rather than a planned operating mode.
- **Residual sub-question:** the setup budget assumes the base is *surveyed and
  running before* the 5-minute window opens, on the grounds that it is ground
  equipment rather than a drone. MB §6 covers "drones, payloads, communication
  systems, and associated equipment", which is ambiguous about the base. Worth
  confirming — the setup budget has only 15 s of modelled margin, and surveying
  inside the window would consume far more than that.

### 4.5 New: what point *on* the survivor is the datum?

Now that delivery is measured from the survivor, this matters more than it did.
A prone adult is ~1.7 m long, so head, torso-centre and feet differ by up to
**0.85 m — comparable to the entire 1 m Zone A radius**. The sizing document
already carries a 0.50 m "target extent / centroid" term for this, which is the
**second-largest contributor in case C** (31 % of variance, behind only the 0.70 m
unmodelled allowance).

If the organisers score from a marked point on the dummy, our detector's centroid
must be biased toward that point rather than the blob centre. **This is cheap to
fix if known, and unfixable on the day if not.**

---

## 5. Open questions — revised

**Answered — closed:**

| Question | Answer | Consequence |
|---|---|---|
| Scoring weights | Rulebook §9 | §1 above |
| One switched video feed or all? | Feed from **each** drone (8.14) | Free — §4.1 |
| Delivery measured from tag or survivor? | **From the survivor** | Errors compound — §4.3 |
| Local RTK base permitted? | **Yes** | Case C reachable — §4.4 |
| Maximum wind? | **None. Wind is natural, not induced.** | No cap to design to, and no guarantee of calm — §6.1 |
| Ballistic parachute? | **No blast of any kind in the air** | Pyrotechnic/CO₂ deployment ruled out — §6.2 |
| Boundary polygon format? | **KML file** | Parser requirement — §6.3 |
| Survivors — real or dummies? | **Human-looking dummies** | Dataset domain shift — §6.4 |
| Pre-booting onboard computers? | **No** | Removes a setup mitigation — §6.5 |
| Delivery datum on the survivor? | **"On the survivor, ideally"** | Aim at torso centroid — §6.6 |

| May the RTK base start before the window? | **No** | Setup must absorb it — §6.7 |

**Still open:**

1. **How is "correctly geotagged" verified** — displayed coordinates against
   surveyed truth, and to what tolerance? Decides whether the base's ~1–2 m
   absolute error costs us anything against 250 points (§6.8).
2. **Is a recovery-canopy descent scored as an emergency landing (−10, or exempt)
   or as a crash (−50)?** Worth 40 points per incident. The rules define a crash as
   "uncontrolled ground impact, collision resulting in loss of flight, or crash
   landing", and a canopy descent is arguably none of those (§6.2).
3. **Is motor-out tolerance separately required?** Ties directly to the open
   rotor-count decision at `../sizing/configuration-trade.md` §2.3.
4. **Is prior site access available** to survey the launch pad? Only matters if
   the answer to (1) makes absolute accuracy count.

---

## 6. Second round of answers

### 6.1 Wind: natural, uncapped

There is **no maximum wind** and no artificial wind. The mission runs in whatever
weather occurs.

This makes `../sizing/configuration-trade.md` §5.2 a **requirement, not a
suggestion**. Search groundspeed is 8 m/s, so at 8 m/s of natural wind the
aircraft cannot make headway at all and the mission fails outright. Nothing in the
rules protects us from that.

**PROPOSED SYS-37:** the aircraft shall retain positive headway at a sustained
wind of **10 m/s**, sizing search *airspeed* accordingly while flying 8 m/s
*groundspeed* nominally. Penetrating at 12 m/s costs 105 W of a 603 W hover draw —
the power is available; the requirement simply has to be written down.

Finals are in January, when much of India is comparatively calm, so the *expected*
case is benign. That is luck, not design margin.

### 6.2 Parachutes: two different questions, two different answers

The first exchange conflated them; both are now settled.

**(a) Aircraft recovery parachute — PERMITTED, ballistic deployment included.**
Pyrotechnic and CO₂ units are allowed. The "no blast in the air" answer referred
to the *kit*, not the airframe. The attached condition is that the aircraft **must
land on the landing pad**.

That condition **cannot be met under canopy**: drift is `wind × h / v_descent`, so
from 60 m at 3 m/s wind a 5 m/s canopy drifts 36 m against a 3.66 m pad. Staying
on the pad needs deployment below 3 m — well under the ~15–20 m a canopy of this
class needs to inflate.

**Fit one regardless.** A crash costs −50; landing outside the zone costs −10. So
deploying is worth ~40 points even accepting the penalty, before counting the
airframe and the safety case. Full analysis in
[`../sizing/configuration-trade.md`](../sizing/configuration-trade.md) §5.4.

**(b) Parachuting the kit** — what the organisers answered on, warning it would
drift badly in wind.

**(b) Parachuting the kit** — what the organisers answered, warning it would drift
badly in wind. **They are right, and it is not our design.** The kit is a
free-fall ballistic drop from 6 m:

| Delivery method | Fall time | Drift at 3 m/s wind |
|---|---|---|
| **Free fall from 6 m (our design)** | 1.11 s | **0.34 m** |
| Parachute descent at ~4 m/s | ~1.5 s | ~4 m+ |

A parachuted kit would land outside Zone C in almost any wind. The hover-and-drop
design already avoids this, and the organisers' warning confirms the choice.

### 6.3 Boundary: KML

The mission boundary arrives as a **KML file** during the setup window.

**PROPOSED SYS-38:** the GCS shall parse a KML polygon and partition it without
operator editing, within the setup budget's 30 s allowance.

Two implementation notes worth writing down now, because both are classic sources
of silent failure:

- **KML coordinates are `longitude,latitude[,altitude]`** — longitude first. The
  reversed convention is the single most common KML bug.
- KML is WGS84 by definition; confirm the datum matches the RTK solution.

Test against a real KML export before the finals, not a hand-written one.

### 6.4 Survivors: human-looking dummies

Confirmed as **human-looking dummies**, not live people. Postures and cover were
not specified — assume varied and plan for the worst.

This is a **domain-shift risk for perception**. HERIDAL and SARD are imagery of
real humans; the competition targets are mannequins, which differ in texture,
thermal signature, pose realism and material reflectance.

**PROPOSED SYS-39:** the fine-tuning dataset shall consist principally of imagery
of **human-looking dummies** at operational altitude, not live people. Pre-train on
HERIDAL/SARD, then fine-tune on dummies.

This is fortunate for logistics — dummies can be left in a field for hours, in any
posture, in any weather.

### 6.5 No pre-booting

Onboard computers **may not be booted before the setup window**.

The setup budget was already built this way — "aircraft out of case, battery in,
power on (×3, serialised)" sits inside the window — so **the 285 s figure and its
15 s of margin are unchanged**. What is lost is a mitigation: the sizing model
listed "ask whether power-on may precede the window" as one of five ways to buy
margin. That one is now closed.

Remaining mitigations, in order of value:

1. **Get the RTK base running early** (§6.7) — worth up to 60 s, and now the only
   structural relief left.
2. **Pre-load the TensorRT engine into a warm cache**; never JIT-build at boot.
3. **Cache the GNSS almanac** for a hot start — saves 30–40 s over a cold start.
4. **Cut companion boot time** (75 s) — the single largest software line.

Companion boot and GNSS/RTK convergence together account for 180 s of a 285 s
budget. **They are the setup problem.**

### 6.6 Delivery datum: "on the survivor, ideally"

The kit should land **on the survivor**. This resolves the aim point: target the
**torso centroid** of the detected dummy, which is what a detector's bounding-box
centre naturally gives.

It does not fully resolve whether scoring measures from the dummy's centre or its
nearest part — but aiming at the centroid is correct under either reading, and the
0.50 m target-extent term in the error budget covers the residual. **No change to
SYS-15.**

One consequence to note: a 200 g kit falling 6 m arrives at ~9.7 m/s carrying
about 9.4 J. That is harmless to a mannequin and would not be harmless to a person.
Since the targets are confirmed dummies this is fine, but **the aim-at-the-body
rule must never be carried over to a live-subject trial** without revisiting the
release altitude.

### 6.7 RTK base station — ANSWERED: NO

**The base may not be positioned, surveyed or started before the setup window.**
It must be set up inside the 5 minutes, alongside the aircraft.

This is the hardest answer received so far, because it lands on the only
constraint that had no margin. Modelled in
[`../../tools/sizing-model/setup_budget.py`](../../tools/sizing-model/setup_budget.py),
output in [`../sizing/setup-budget-output.txt`](../sizing/setup-budget-output.txt).
Figures below are calibrated against the main model's 285 s baseline:

| Case | Launch | Verdict |
|---|---|---|
| **A** Base pre-started *(no longer allowed)* | 285 s | OK — the old baseline |
| **B** Base in-window, 90 s survey-in, RTK fix before launch | **475 s** | **Fails by 175 s** |
| **C** Base declares its first 3D fix, RTK fix before launch | **390 s** | **Fails by 90 s** |
| **D** As C, RTK converges *in flight* | **285 s** | **OK — fully recovers** |

Two changes together absorb the ruling completely:

**(1) Do not survey-in. Declare the base's first 3D fix as its reference.**
Survey-in buys absolute accuracy, and §6.8 shows we barely need it. Saves ~90 s.

**(2) Stop gating launch on an RTK fix.** The rule constrains setup-to-**launch**;
nothing requires an RTK fix at takeoff. RTK only has to be fixed before the first
*geotag*, which is after the launch queue, climb and transit. Saves ~105 s.

**PROPOSED SYS-42:** the RTK base is positioned, powered and set to a fixed
reference from its first 3D fix, inside the setup window, without survey-in.
**PROPOSED SYS-43:** launch is gated on a 3D fix, not an RTK fix. The first geotag
is gated on RTK-fixed; detections made before that are geotagged in float and
re-fused once fixed.

**Residual gap.** RTK fixes ~30 s after the first sweep line begins, so roughly
the first third of the sweep is float-quality. Float is typically 0.3–0.5 m
horizontal — well short of fixed, but far better than standalone, and the ~12
looks per target make re-fusing after the fix nearly free. **Verify in P7 that a
re-fused float-then-fixed track meets SYS-12.**

### 6.8 Does RTK need an external network? — an honest answer

Asked directly, and the earlier answer was incomplete.

**The corrections link needs no network.** A team-owned base computes corrections
and transmits them to the aircraft over our own radio. Nothing touches GSM, LTE,
the internet, or an NTRIP caster. This is what rules 8.4 and 8.17 prohibit, and we
are clear of it.

**But the base's own position is a separate question**, and the earlier phrasing
glossed it:

| How the base gets its position | Network? | Absolute accuracy |
|---|---|---|
| Self-survey (averaging its own fix) | **No** | ~1–2 m |
| Declared from first 3D fix (SYS-42) | **No** | ~1–2 m |
| Surveyed benchmark | No, but needs prior site access | cm |
| NTRIP / network-corrected fix | **Yes — prohibited** | cm |

So a precise *absolute* position would normally involve a network or prior
surveying. **We use neither, and accept ~1–2 m absolute.**

**Why that is acceptable — and where it isn't.** RTK provides *relative* precision.
A base position error shifts every aircraft by the same vector, so:

- **Delivery (200 points): the error cancels exactly.** The survivor is geotagged
  by a drone carrying the shift, and the delivery drone flies to that coordinate
  carrying the same shift, so the kit lands on the true survivor.
- **Geotag score (250 points): it may not cancel.** If judges compare our
  *displayed* coordinates against surveyed truth, a 1–2 m common-mode bias is a
  real error against that check.

**NEW QUESTION FOR THE ORGANISERS:** how is "correctly geotagged" verified — by
comparing our displayed coordinates against a surveyed truth position, and if so
to what tolerance? If the tolerance is tight, the base's absolute accuracy matters
for 250 points and prior site access to survey the pad becomes valuable.

### 6.9 Original elaboration, as sent

*Draft text for the organisers:*

> Our system uses a team-owned RTK base station to improve survivor geotagging
> accuracy. This is **ground equipment** — a GNSS receiver on a surveyed tripod
> beside the ground control station, connected to our own local radio link. It
> does not fly, is not carried by any drone, and uses no external network: the
> corrections travel only over our own equipment.
>
> Before it can supply corrections, the base must self-survey its own position,
> which takes several minutes of continuous observation. If that must happen
> inside the 5-minute setup window, it consumes most of the window on its own.
>
> **Question:** may the RTK base station be positioned, surveyed and left running
> *before* the setup window begins — in the same way the Ground Control Station
> and its antennas are positioned under rule 4.34 — given that it is ground
> equipment rather than part of the drone system?
>
> We are not asking to pre-boot any onboard computer. All three aircraft would
> remain unpowered until the window opens.

**Why this matters:** rule 4.34 requires the C2 station and "all associated
equipment such as antennas, displays, computers" to be *positioned* in the
designated area, and does not place that inside the 5-minute window — 4.36 applies
the window to setup. Mission brief §6 covers "drones, payloads, communication
systems, and associated equipment" during setup, which is where the ambiguity
lies. The distinction we are drawing is between **ground infrastructure** and
**the drone system**.
