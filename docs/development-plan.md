# RescueSwarm — Phase-to-Phase Development Plan
### NIDAR 2026–27 · Track 1 · Mission 1 · Registered August 2026

**This is the single schedule authority.** Where anything else disagrees, this
governs. *What* to build and how simple it can be is in
[`implementation-plan.md`](implementation-plan.md). Requirements live in
[`requirements/requirements-baseline.md`](requirements/requirements-baseline.md);
architecture rationale lives in [`system-overview.md`](system-overview.md); this
document is *when* and *in what order*.

---

## Part 1 — What actually shapes this schedule

A 21-week calendar is not the binding constraint. Three others are, and they are
the reason this plan is not a uniform Gantt chart.

### 1.1 The flight-test window is about eight weeks, not twenty-one

| Period | Condition | What can happen |
|---|---|---|
| **Aug – late Sep** | **Monsoon** | Bench, simulation, software, perception on public datasets, procurement, build. **Assume no reliable outdoor flying.** |
| **Oct – end Nov** | Post-monsoon, pre-exam | **The flight window.** Everything that needs air happens here. |
| **Dec** | End-semester exams + Progress Review 2 | Reduced engineering capacity. Integration, documentation, presentations. |
| **Late Dec – early Jan** | Holidays | Rehearsal and freeze. |

**Consequence: the aircraft must be built, integrated and bench-tested during the
monsoon so it can fly the day the weather clears.** A plan that schedules "first
flight" for November has already failed — by November you should be validating
perception, not discovering that the airframe vibrates.

> **Assumptions to confirm in week 0:** monsoon withdrawal date for your region,
> and your university's end-semester exam dates. Both move this plan. If exams
> fall in November rather than December, phases P5–P6 compress and the
> de-scope list in §4.2 comes into play early.

### 1.2 Fixed external dates

| Date | Event | Consequence of missing it |
|---|---|---|
| ~~2nd week Aug 2026~~ | ~~Registration~~ | ✅ **Done** |
| **2nd week Oct 2026** | **Progress Review 1** — attendance mandatory (4.14) | Non-eliminating (4.16), but required |
| **2nd week Dec 2026** | **Progress Review 2** — attendance mandatory | As above |
| **January 2027** | **Finals** — 4A Design Review · 4B Business Strategy · 4C Pre-Flight Inspection · 4D Mission | — |

Plan for the **first week of January**. It costs nothing if the event lands later.

### 1.3 Team and workstreams

Rules 3.6–3.8: 4–10 students, interdisciplinary, plus one faculty member. This
plan assumes **~7 students in four tracks**, because more parallel tracks than
people is how student programmes stall.

| Track | People | Owns |
|---|---|---|
| **A — Air vehicle** | 2 | Frame, propulsion, power, payload mechanism, assembly |
| **B — Avionics & comms** | 1–2 | Flight controller, companion computer, GNSS/RTK, mesh, safety link, video |
| **C — Autonomy & GCS** | 2 | Coverage planner, task allocation, state machine, ground station, SITL |
| **D — Perception** | 1–2 | Detector, tiling, geotagging, calibration, dataset |
| **Business & docs** | shared + faculty | 4B pitch, cost sheet, design review deck, sponsorship |

**Business is not a phase — it runs continuously from week 0**, because
sponsorship evidence is worth 20 points and cannot be produced in the final week.

---

## Part 2 — Phases

Weeks counted from **10 August 2026**. Finals at ~W21.

### P0 · Mobilisation — W0–1 (10–23 Aug) · monsoon

| Track | Work |
|---|---|
| All | Assign roles; confirm exam and monsoon dates (§1.1) |
| All | **Send organiser questions** ([drafted](requirements/organiser-questions.md)) |
| A | Frame CAD started to [frame-design-constraints](frame-design-constraints.md) |
| B | **Resolve the BOM-vs-design-point conflict before any order** — [`bom_reconcile.py`](../tools/sizing-model/bom_reconcile.py). The BOM is right; the model needs Indian masses fed back |
| B | Order everything the frame and pack decisions don't touch (motors, ESCs, FC, GNSS, compute, camera, radios, RTK base) |
| C | Repo structure, CI, SITL environment stood up |
| D | Public flood and search-and-rescue image datasets acquired; pipeline scaffold |
| Biz | First sponsorship approaches |

**Gate:** every rule clause maps to a testable requirement ✅ · **design point
reconciled with the BOM** · orders placed for long-lead items · roles assigned.

> **P0 blocker found.** The BOM and the sizing model describe different aircraft,
> and the BOM is the correct one — with real Indian component masses the 6S2P pack
> fails the 2× endurance reserve at 1.78×. Republish the design point at **6S3P**
> before ordering cells, and re-run the model with Indian masses. Motors, ESCs,
> avionics, compute and comms are unaffected and should be ordered now.

### P1 · Architecture freeze & procurement — W2–4 (24 Aug – 13 Sep) · monsoon

| Track | Work |
|---|---|
| A | Frame design complete; manufacture started; payload magazine and release built |
| B | **Long-lead orders placed**: compute, camera + lens, radios, GNSS/RTK, cells, connectors |
| C | DARP partition + boustrophedon in SITL, single aircraft; **KML parser** (SYS-38) |
| C | **GCS multi-vehicle data model + delete the internet poller** — see [`../ground-station/PLAN.md`](../ground-station/PLAN.md). Retrofitting multi-vehicle later means building every display twice |
| D | Detector pre-trained on HERIDAL/SARD; pipeline runs on the real camera + SBC |
| A/D | **Build the dummies** — two is enough to start |

**Gate:** ICDs agreed · all long-lead items ordered · SITL flying one aircraft ·
detector reproduces a published baseline.

> **Why the baseline reproduction matters:** it proves the pipeline before you
> trust it on your own data. If you cannot hit published numbers on HERIDAL, the
> problem is your pipeline, not your dataset.

### P2 · Bench integration & the measurement that matters — W5–7 (14 Sep – 4 Oct) · monsoon ends

| Track | Work |
|---|---|
| A | Airframe assembled; thrust-stand runs; **prop diameter settled** (16/18/20 in) |
| B | Full avionics stack on the bench; mesh between 3 nodes + GCS; video at 3 × 480p15 |
| B | **COLD-BOOT AND SETUP TIMING MEASURED** — including RTK base set up *inside* the window (SYS-42/43) |
| C | Task allocation (CBBA) in SITL; GCS command module split so the mission build has no retask path (SYS-20) |
| C | Mission-state ingest; MediaMTX video gateway proven with 3 SITL sources |
| D | Field data collection with dummies at 40 m and 60 m — *ground-based, no aircraft needed* |

**Gate:** setup-to-launch **measured**, not modelled · one aircraft complete and
powered · SITL running 3 aircraft.

> **This is the highest-risk gate in the programme.** Setup has 15 s of modelled
> margin and has never been timed. If it fails here, you have October to fix it in
> software. If you discover it in December, you don't.

### P3 · Progress Review 1 & first flight — W8–9 (5–18 Oct) · flight window opens

| Track | Work |
|---|---|
| All | **Progress Review 1** (2nd week Oct) — architecture, sizing, bench evidence |
| A/B | **First flight**: manual → stabilised → altitude/position hold → auto waypoint |
| A/B | Vibration and thermal characterisation; failsafe bench injection |
| C | Mission state machine end-to-end in SITL |
| D | Fine-tune on dummy imagery; first geotag trials against surveyed markers |

**Gate:** PR1 delivered · stable autonomous waypoint flight · failsafes
demonstrated on the bench.

### P4 · Perception & delivery validation — W10–12 (19 Oct – 8 Nov) · **prime flight window**

The most valuable eight weeks of the programme start here. **450 of the 600 flight
points are won or lost in this phase.**

| Track | Work |
|---|---|
| D | Recall measured at operational altitude → **sets the final search altitude** |
| D | Boresight and lever-arm calibration (SYS-48); geotag CEP against surveyed truth |
| A/B | **≥30 drop trials** — release gate, wind compensation, distribution vs zones |
| B | RTK convergence timing in flight; float-then-fixed re-fusion (SYS-43) |
| C | Deconfliction and spatial locks in SITL; Monte Carlo harness |

**Gate:** recall ≥ 0.90 · geotag CEP50 ≤ 0.75 m · SYS-15 delivery distribution met.

### P5 · Single-aircraft full mission — W13–14 (9–22 Nov)

| Track | Work |
|---|---|
| All | End-to-end autonomous mission, one aircraft, mission file to recovery |
| C | Fault injection: link loss, GNSS degradation, payload jam, geofence |
| A | Second and third airframes completed |

**Gate:** **5 consecutive clean autonomous missions**, single aircraft.

### P6 · Swarm — W15–16 (23 Nov – 6 Dec)

| Track | Work |
|---|---|
| All | 3-aircraft coordinated missions over 10 ha |
| C | CBBA under real link conditions; mesh partition and rejoin |
| C | Monte Carlo campaign, 200 runs, overnight |
| A/B | Sequenced launch and recovery through the 3.66 m box |

**Gate:** **3 consecutive 3-aircraft 10 ha missions** · ≥ 95 % completion over the
Monte Carlo campaign.

### P7 · Progress Review 2 & documentation — W17–18 (7–20 Dec) · **exams**

Engineering capacity is reduced here by design. Plan documentation-heavy work.

| Track | Work |
|---|---|
| All | **Progress Review 2** (2nd week Dec) |
| Biz | Business strategy pitch complete; **cost sheet finalised**; sponsorship evidence collated |
| All | Design review deck built from the evidence gathered in P4–P6 |
| B | Spares, cabling looms, field kit, transport cases |

**Gate:** PR2 delivered · both finals presentations drafted and rehearsed once.

### P8 · Rehearsal & freeze — W19–21 (21 Dec – 10 Jan)

| Track | Work |
|---|---|
| All | **20 timed setup runs** with the real two-person choreography |
| All | 15 repeatability missions |
| All | **Mock Pre-Flight Inspection** against the model checklist (4.31) |
| All | **Configuration freeze** — no code touches an airframe after this |
| All | Travel, contingency spares, rehearsed Q&A for both presentations |

**Gate:** 13/15 repeatability · setup ≤ 240 s over 20 runs · mock inspection
passed · config frozen.

---

## Part 3 — Critical path

```text
P0 ── P1 ── P2 ──┬── P3 ── P4 ── P5 ── P6 ── P8
   procurement   │  first   perception  swarm   freeze
   and build     │  flight   ▲
                 │           │
                 └───────────┘
              D-track dataset runs from P1 and is the long pole
```

**The critical path is procurement → build → first flight → perception.** The
single-point failure is **P2**: if the aircraft isn't flying by mid-October, every
subsequent phase compresses into the exam period.

**Perception (track D) is the parallel long pole** and does not depend on the
aircraft until P4. It must run continuously from P1. Any week that D is idle is a
week that cannot be recovered.

---

## Part 4 — Risk and contingency

### 4.1 Risk register

| Risk | Trigger | Response |
|---|---|---|
| **Setup timing fails at P2** | Measured > 300 s | Software boot optimisation; TensorRT warm cache; GNSS almanac cache. Escalate immediately — October is the only time to fix it |
| **Monsoon extends past September** | No flying by W9 | Move first flight to any available dry window; compress P3 into P4; do not compress P4 |
| **Exams fall in November** | Confirmed in W0 | Front-load P5–P6 into October; accept a 2-aircraft demonstration (§4.2) |
| **Recall misses 0.90 at P4** | Measured | Drop altitude further (30 m costs 187 s of a 900 s budget); add an oblique second pass over low-confidence candidates |
| **Q3 forces a hexacopter** | Organiser answer | ~3–4 weeks of frame and propulsion rework. Payload, avionics and ground segment carry over unchanged. Absorb by cutting the Monte Carlo count and the third airframe |
| **An airframe is lost in testing** | Crash | Fly two. The rules require a **minimum of two drones** — see §4.2 |

### 4.2 De-scope order — what to cut, in this order

If the schedule slips, cut from the top. Each of these is chosen because it costs
few or no points.

1. **Monte Carlo run count** — 200 → 50. Costs nothing scored.
2. **Wind-penetration requirement (SYS-37)** — accept the 8 m/s cliff and hope for
   a calm day. Costs nothing *unless* it is windy.
3. **Altitude optimisation** — stay at 60 m. Costs detection recall, which is 250
   points, so this is already painful.
4. **The third aircraft — fly two.** Rules require a minimum of two drones (8.8),
   so a two-aircraft fleet is fully compliant. Coverage takes ~1.5× longer, which
   a 74 % time margin absorbs easily, and the 50-point collaboration criterion is
   satisfied by two.

**Do not cut:** the drop trials, the geotag calibration, or the timed setup runs.
Those are 450 points and the pass/fail gate respectively.

### 4.3 Working rules

- **No new autonomy code touches a real airframe until it has run 20 consecutive
  clean SITL missions.** SITL cycles cost minutes; a crash costs weeks — and in
  this calendar, a crash in November costs the programme.
- Every real flight runs a tagged commit, logged with the tag.
- If a document disagrees with `docs/sizing/model-output.txt`, re-run the model and
  fix the document.
- **Weekly**: one 30-minute cross-track sync. Track D reports recall; track B
  reports setup time. Those two numbers are the programme's health.

---

## Part 5 — Superseded content

Earlier revisions of this document carried a requirements decode and an
architecture-decision rationale. Both have moved and are maintained there now:

| Was | Now |
|---|---|
| Part 0 — requirements decode | [`requirements/requirements-baseline.md`](requirements/requirements-baseline.md) and [`requirements/rulebook-compliance.md`](requirements/rulebook-compliance.md) |
| Part 2 — architecture decisions | [`system-overview.md`](system-overview.md) and [`sizing/configuration-trade.md`](sizing/configuration-trade.md) |
| Calendar re-baseline | This document, Part 1 |
