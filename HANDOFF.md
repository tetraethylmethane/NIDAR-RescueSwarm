# Handoff

For whoever picks this up next — a teammate, a reviewer, or me in three weeks
having forgotten all of it.

`README.md` says what the system **is**: design point, scoring, decisions, open
risks. This says what state the work is **in** — what is proven, what is only
modelled, what is waiting on a human, and which traps have already cost days.
Read this one first if you are about to change something.

---

## 1. The two repositories

| | |
|---|---|
| **NIDAR-RescueSwarm** (this repo) | Systems engineering: requirements, sizing models, autonomy, perception, firmware parameters, CAD brief, business case. |
| **[NIDAR-GSC](https://github.com/tetraethylmethane/NIDAR-GSC)** | Ground station and the SITL harnesses. Inherited from an earlier project, substantially rewritten. |

They are separate repos and the sim scripts cross the boundary. GSC finds this
one via `NIDAR_SYS`, defaulting to a sibling directory:

```sh
export NIDAR_SYS=/path/to/Drikr-NIDAR
```

If that is wrong, `sim-flight.sh` **refuses to launch** rather than quietly
flying stock parameters. That refusal is deliberate — see §5.

---

## 2. Evidence status — the important table

The single most useful thing to know here is which numbers are **measured**,
which are **modelled**, and which are **assumed**. Treating one for another is
how this project has lost most of its time.

| Claim | Status | Where |
|---|---|---|
| Battery failsafe returns the aircraft to the pad | **Measured** — SITL, RTL at 10809 mAh of a 10800 mAh trip, three aircraft | `NIDAR-GSC/scripts/test-battery-failsafe.sh` |
| mavlink-router carries three SYSIDs to one GCS port | **Measured** — three SITL, all three arrive | `NIDAR-GSC/scripts/test-mavlink-router.sh` |
| Geotag projection is self-consistent | **Measured** — two independent formulations agree to 7.8e-10 m | `perception/geotagging/accuracy.py` §1 |
| Geotag CEP50 | **Modelled** — Monte Carlo whose *inputs* are budget assumptions. Reconciles with the analytic budget to +1 % | `docs/sizing/geotag-accuracy-output.txt` |
| Separation at launch | **Measured in sim** — 64.80 m, up from 1.31 m | `proof-1-launch.png` |
| Separation en route | **34.00 m claimed here; 29.19 m recomputed.** Definition-sensitive — see §2b | `proof-2-sweep.png` |
| Separation during recovery | **6.52 m claimed here; 5.51 m recomputed.** Hardcoded in a caption string — see §2b | `proof-4-pad.png` |
| Three aircraft land safely on one pad | **Measured 2.27 m minimum, clear by 1.22 m** — corner slots, not a row | `proof-4-pad.png` |
| Endurance, hover power, mass budget | **Modelled** — no aircraft has flown | `docs/sizing/model-output.txt` |
| Detection recall, boresight, RTK accuracy | **Assumed** — no real imagery, no calibration, no hardware | — |

Nothing in this project has flown on real hardware. Every "measured" above
means measured in simulation or in software, which rules out whole classes of
error and rules out none of the physical ones.

### 2b. Three numbers in this table did not reproduce

Writing figure captions for the funding proposal meant recomputing the
separation results from `simulations/recordings/mission-telemetry.json`. The
launch figure was **wrong and is corrected**: this file said 92.12 m, while
`README.md`, `proof-1-launch.png` and the raw telemetry all say **64.80 m**.

The other two are **definition-sensitive and left alone deliberately** — my
"en route" excludes a 60 m radius around the pad, which may not be the boundary
the original used:

| | claimed | recomputed |
|---|--:|--:|
| en route | 34.00 m | 29.19 m |
| stacked over the pad | 6.52 m | 5.51 m |

**Worth fixing at the source:** `simulations/sitl/proof_figures.py:350` carries
the 6.52 m as a **hardcoded string inside a caption** rather than computing it.
That is prose beside a formula — the same defect §5 is organised against, in the
script that generates the evidence.

### 2b-2. The take-off delays are not visible in the telemetry as commanded

The mission file sets `NAV_DELAY` to **0/15/30 s**, and the autopilots log
`Delaying 15 sec` / `Delaying 30 sec`. The aircraft are observed leaving the pad
at **0.0 / 3.5 / 10.0 s**. Aircraft 3 served 9.2 s of a commanded 30; aircraft 2
served 2.7 s of a commanded 15 — inconsistent ratios, so not a clean
`SIM_SPEEDUP` conversion.

**The deconfliction result stands** (1.31 m -> 64.80 m is measured). The
*mechanism* does not: §4.2 attributes the spacing to a 0/15/30 s stagger and the
recording does not show those delays being served. Re-fly at `SIM_SPEEDUP 1`
before quoting the mechanism. Full detail in `docs/proposal/README.md`.

### 2c. The mass statement does not close

`docs/sizing/model-output.txt` lists **6,061 g of items against a 6,360 g
MTOW** — a 299 g (4.7 %) unallocated residual, and its own percentages sum to
95.3 %. Nothing downstream is wrong because structure is derived as
`0.235 × MTOW` rather than summed, but a reader adding the bars up finds 299 g
missing. The proposal now shows the residual as its own bar rather than hiding
it. **Attributing it is a P1 action.**

---

## 3. Running things

All verified working as written. WSL Ubuntu, ArduPilot built from source at
`~/ardupilot`.

```sh
# Models. Every committed number in docs/sizing/ regenerates from these, and
# CI fails if a committed output drifts from its model.
python tools/sizing-model/rescueswarm_sizing_model.py
python perception/geotagging/accuracy.py

# Tests. NOTE the working directory -- CI runs them from inside each package,
# and running from the repo root hides import errors that CI then catches.
cd autonomy   && python -m pytest tests -q     # 125
cd perception && python -m pytest tests -q     #  17

# Firmware parameters, regenerated and validated
cd firmware/ardupilot-params && python params.py --drones 3 --out .

# SITL: prove the battery failsafe brings it home
NIDAR_SYS=$PWD ../NIDAR-GSC/scripts/test-battery-failsafe.sh

# SITL: three aircraft flying the planned missions, recorded
python3 simulations/sitl/fly_and_record.py     # -> telemetry.json
python3 simulations/sitl/fly_endurance.py      # -> telemetry_endurance.json
python3 simulations/sitl/render.py telemetry.json out.gif "title" "subtitle"
```

`simulations/recordings/*.json` is committed telemetry from real SITL runs. The
GIFs are gitignored and regenerate from it.

**Do not use `NIDAR-GSC/scripts/run-sim.sh`.** It launches `-v ArduPlane` — a
fixed wing — with no project parameters, and `scripts/README.md` still points at
it. It now refuses to run without an explicit override.

---

## 4. Decisions waiting on a human

These are not blocked on work. They are blocked on someone choosing.

### 4.1 Pad recovery — RESOLVED by moving the slots to the corners

Was: three aircraft aiming at slots 1.22 m apart came to rest **0.83 m** apart,
an overlap of 1.046 m airframes, and stacked **3.99 m** apart in the air over
the pad. `rulebook-compliance.md` had argued three airframes fit the 12 ft pad
"3 per row", and `pad_slots()` implemented exactly that.

A row is the worst possible packing on a square. Centres must stay half an
airframe inside the pad edge, so they live in a 2.61 m square; a row across it
gives 1.31 m at best, its **corners** give the full 2.61 m — twice the
separation, same pad, no cost.

| | row of 3 | 3 corners |
|---|---|---|
| slot spacing | 1.22 m | **2.61 m** |
| worst case, ±0.5 m dispersion each | −0.13 m (overlap) | **1.61 m** |
| measured, closest at any time | 0.83 m (overlap) | **2.27 m** |
| measured, stacked over the pad | 3.99 m | **6.52 m** |

Four aircraft also fit, at the four corners. Five do not, and `pad_slots()`
raises rather than returning something that overlaps.

**Still worth confirming with the organisers:** the aircraft now sit at the pad
corners rather than in a line, and brief 7 requires no part of any drone
outside the box during launch and landing. Slot centres are half an airframe
inside the edge by construction, so this is satisfied geometrically — but the
staging photo will look different from what a marshal might expect.

### 4.2 Takeoff sequencing — done

Was: all three launched together and the mission run measured 1.3 m between
aircraft at 2–3 m altitude. Now a staggered `NAV_DELAY` (0/15/30 s) sits before
each `NAV_TAKEOFF`, so the spacing lives in the mission file rather than in an
operator's timing. Re-flown at SIM_SPEEDUP 3 so the stagger is legible:
**closest pair during launch went 1.31 m to 64.80 m.** Both telemetry sets and
the figure are in `simulations/recordings/`.

An earlier claim of 21.17 m here was from a 15x run whose coarser sampling
missed the closest approach. The finer run is the one to trust, and it also
moved the tightest point of the whole flight into recovery — see §4.1.

### 4.2b `mission_backend` exists twice, and the copies have drifted

`ground-station/mission_backend/` in this repo and `server/mission_backend/` in
NIDAR-GSC are the same package, maintained in two places. Five files are
byte-identical. Three are not:

| file | here | NIDAR-GSC |
|---|--:|--:|
| `mavlink_ingest.py` | 186 lines, **0** `SET_MESSAGE_INTERVAL` | 304 lines, **7** |
| `api.py` | 117 lines | 156 lines |
| `__init__.py` | — | 6 lines differ |

The gap in `mavlink_ingest.py` is the stream-request fix: ArduPilot sends a
passive listener nothing but heartbeats unless it asks, so every reading sits
at its initialised 0.0. That was fixed in the GSC copy and never came back
here. **The GSC copy is what flies; this copy is what CI tests** — 67 green
tests against code that is not deployed, including the SYS-20 evidence.

Both copies still enforce SYS-20, so the requirement is not unmet. But it is
being verified against the wrong artifact, which is this project's most
frequent defect wearing a different hat.

Three ways out, and it is a structural choice rather than a fix:

1. **Vendor one way.** Make NIDAR-GSC import the systems-repo copy (git
   submodule or a package), so there is one source and CI tests the deployed
   code. Cleanest, most plumbing.
2. **Move it wholly to NIDAR-GSC** and keep only the evidence here. Loses the
   systems repo's CI gate on SYS-20 unless that job learns to check out both.
3. **Keep both and add a drift check** that fails CI when the two diverge.
   Cheapest, and does not fix the split — only makes it loud.

Until one is chosen, sync the copies before trusting either test suite.

### 4.3 Organiser questions are drafted and unsent

`docs/requirements/organiser-questions.md`. Several downstream numbers depend
on the answers — particularly whether prior site access allows surveying the
pad, which is worth ~0.4 m of geotag budget.

### 4.4 Parts order

Cells are unblocked: the design point is **6S3P, 18 cells per aircraft, 54 for
the fleet**. See `docs/sizing/model-output.txt`, which is authoritative over any
prose including this file.

### 4.5 Which BOM is authoritative — RESOLVED, but with a consequence

`hardware/bom/RescueSwarm_BOM_India_Verified.xlsx` **wins** and is now tracked.
It had been sitting untracked — one `rm` from gone — while being the best
artifact in the folder. Its own README says why: *"The previous BOM named
suppliers. This one names PARTS."* 41 lines, exact model numbers, 28 live
product links, per-line status, thrust validated against published bench data.

It disagrees with `RescueSwarm_BOM_India.xlsx` by **₹26,146 per aircraft**, and
the direction is upward:

| | India BOM | Verified |
|---|--:|--:|
| Flight controller | 26,000 | **42,000** — the Agam Full Set incl. 5 % GST, and it bundles the power module |
| Power module | 2,800 | **0** — inside the Full Set; buying it separately double-counts |
| Motor | 7,000 | **9,099** — listed price with published thrust; 7,000 was never sourced |
| **Per aircraft** | **2,64,400** | **2,90,546** |

**The consequence nobody has signed off:** the Verified BOM is a **17 in**
aircraft, not 18 in, and bottom-up mass drops 6,236 g → 5,780 g. `docs/sizing/`,
`cost_model.py` and `bom_reconcile.py` all still describe the 18 in aircraft, as
does the funding proposal. Adopting it means **re-running the sizing model, not
editing a price.**

### 4.6 The funding ask has moved a long way — and the workbook is now stale

`docs/proposal/` holds an IEEEtran funding proposal (15 pages, 12 figures,
committed as PDF). The ask went **₹28.74 L → ₹8.24 L (−71 %)** across several
passes, driven by team decisions recorded in `docs/proposal/README.md`.

The adopted configuration is **₹1,57,800 per aircraft**: hobby-grade where the
failure mode is visible and the spec is easy to verify; professional for the
autopilot, RTK receiver, accelerator, camera, matched cells and structure.

`hardware/bom/RescueSwarm_Cost_Study.xlsx` **had** drifted out of agreement with
the proposal. It is now **generated** by `hardware/bom/build_cost_study.py`,
which imports every figure from `docs/proposal/figures/competition_budget.py` —
the same module the proposal's budget and charts derive from. Nothing is
restated in two places, so the two artifacts cannot disagree again. Re-run the
script after any configuration change; do not edit the workbook by hand.

**Three things gate the ask and are not decided:**

1. **Insurance** was deferred at team direction. Third-party cover is commonly
   mandatory for Indian UAV operations. **Confirm before any flight.**
2. **Duty and GST were double-counted — now corrected.** The audit is done:
   every line is classified tax-inclusive (₹4.66 L), ex-GST (₹1.82 L) or exempt
   (₹0.05 L) in `competition_budget.py`, and tax applies only to the middle
   bucket. **₹1.64 L removed; the ask fell ₹10.12 L → ₹8.24 L.** Residual risk
   is only that a line marked ex-GST is in fact inclusive, which would reduce
   the ask further. Confirm with each supplier in tranche 1.
3. **Indigenous content is 36 %, not the 45 % first asserted.** Computed from
   per-line fractions. This matters beyond presentation: duty is levied on the
   imported residual, so the wrong figure understated the duty.

---

## 5. Traps that have already cost time

Read this section before adding any config file.

**Configs that are not in the execution path.** Four instances so far, and the
most expensive class of defect on this project:

- `mediamtx.yml` — parsed clean, served nothing.
- `mavlink-router.conf` — `Mode = Normal` routed **zero** messages when the
  aircraft initiates. Started without complaint for weeks.
- `firmware/ardupilot-params/*.parm` — a validated, unit-tested failsafe set
  that **no simulation ever loaded**. Every SITL script used stock defaults,
  where `BATT_FS_LOW_ACT = 0`. Found by a teammate watching a video, not by any
  test.
- `plan.py`'s transit-altitude stagger — applied to `NAV_TAKEOFF` only, so the
  documented deconfliction was never flown.
- `plan.py`'s sweep direction — `start_far_side=bool(i % 2)`, keyed on the drone
  index rather than on anything physical, left two of three aircraft finishing
  their sweep 516 m and 540 m from the pad on the lowest state of charge of the
  flight. `plan_mission` now enumerates the four start/direction combinations
  and keeps the one that ends nearest home; all three now finish inside 130 m,
  at identical path length.

Each reviewed clean and had passing tests around it. The only thing that
catches this class is running the real artifact end to end and **reading the
values back off the running system**.

**A second class, found by reviewing the funding proposal three times.** Where
§5 is about artifacts that are not in the execution path, this one is about
*numbers that agree with each other and with nothing else*:

- The proposal asserted **45 % indigenous content** in four places. It agreed
  with itself everywhere and was wrong everywhere — the computed figure is
  **35.5 %**. Nobody had ever run the calculation.
- It paired **2 cm/px with "roughly fifty pixels"**. At 2 cm/px a 1.7 m person
  is 85 px; the 47 px figure belongs to the 2× downsampled image. Two correct
  numbers from `sizing-calculations.md` §8, joined into a false statement.
- `HANDOFF.md` itself carried **92.12 m** for launch separation while the
  figure, `README.md` and the raw telemetry all said 64.80 m.

The lesson is narrower than "check your numbers": **internal consistency is not
evidence.** A figure repeated in four places is not corroborated, it is copied.
Check each number against the thing that *generates* it — the model output, the
telemetry, the arithmetic — and not against the other places it appears. `validate()` in `params.py` now rejects a
table of known-phantom names, because `BATT_RESISTANCE` sat in the parameter
files for weeks doing nothing — it is a PX4 name, ArduPilot estimates internal
resistance itself, and `.parm` drops unknown names in silence.

**Other things that bite:**

- `FENCE_RADIUS` is 600 m, chosen for the link budget. It caps how far the
  search area can sit from launch. A first sim run had all three aircraft
  breach and RTL three seconds into the sweep.
- `SIM_BATT_CAP_AH` set at **runtime** does not drive the SITL battery model.
  Set it at boot via `--defaults` or the pack never sags.
- `--defaults` in ArduPilot SITL takes a **comma-separated list**, applied left
  to right. Verified, not assumed.
- Seeding anything from `hash()` on a string makes it non-reproducible: Python
  randomises string hashing per process. Use `zlib.crc32`.
- Generating a committed output with PowerShell `>` adds a UTF-8 BOM that
  `--strip-trailing-cr` will not strip, and the reproduce job fails on line 1.
  Generate through a shell that writes raw bytes.
- Run tests the way CI runs them (from inside `autonomy/`, `perception/`), not
  from the repo root.

---

## 6. The CI contract

`.github/workflows/model-check.yml` — jobs: `requirements`, `ground-station`,
`reproduce`, `links`, `perception`, `autonomy`. GSC has `mission-build.yml`.

The rule the `reproduce` job enforces: **every published number regenerates
from its model, and changing a model means committing the regenerated output in
the same commit.** 13 outputs in `docs/sizing/` are compared byte for byte.

This job silently failed for weeks over CRLF before anyone noticed, which is
worth remembering — a green tick is only worth what the job actually checks.
`.gitattributes` now normalises the outputs to LF.

---

## 7. Blocked on hardware or venue

Not actionable until something physical exists: 868 MHz safety radio link,
venue map tiles, boresight calibration, detection recall on real imagery,
pack internal resistance by bench discharge, and every flight-test line in
`docs/development-plan.md`.

---

## 8. Where to look

| Question | File |
|---|---|
| What is the system, what did we decide, what are the risks | `README.md` |
| Why every number is what it is | `docs/sizing/sizing-calculations.md` |
| What the rulebook requires and whether we meet it | `docs/requirements/rulebook-compliance.md` |
| Requirement IDs (`SYS-*`) | `docs/requirements/requirements-baseline.md` |
| Plan of work and schedule | `docs/development-plan.md` |
| What the CAD designer needs | `hardware/cad/CAD-BRIEF.md` |
| What the perception owner needs | `docs/perception-integration-plan.md` |
| Cost and indigenisation | `docs/business/cost-and-economics.md` |
| The funding proposal, and its correction record | `docs/proposal/` — read the README before the PDF |
| What the aircraft is actually built from | `hardware/bom/RescueSwarm_BOM_India_Verified.xlsx` |
| What was inherited in the GCS and what was wrong with it | `docs/gcs-inherited-review.md` |
