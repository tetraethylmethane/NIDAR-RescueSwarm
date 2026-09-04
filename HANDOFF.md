# Handoff

For whoever picks this up next — a teammate, a reviewer, or me in three weeks
having forgotten all of it.

`README.md` says what the system **is**: design point, scoring, decisions, open
risks. This says what state the work is **in** — what is proven, what is only
modelled, what is waiting on a human, and which traps have already cost days.
Read this one first if you are about to change something.

---

## 0. Where it stands today

**2026-09-04**, at `fa3495c`. Nothing has flown. Every performance figure is
calculated or simulated; the evidence table in §2 says which is which.

| | |
|---|---|
| Funding ask | **INR 6,85,532**, in 29 staged releases, first is INR 3,733 |
| Parts | **INR 5,81,034**, 59 lines, every one a live listing with a URL |
| Technical proposal | 22 pages, 64 automated checks passing |
| Mentor brief | 37 pages: 7 of brief, then 29 DoSA approval letters, one per phase |
| Ground station | Runs; captured live for the paper with synthetic telemetry |

**The three things to pick up first:**

1. **Two BOM systems have diverged** (§4.5). `sourced_bom.py` feeds the brief
   and the letters; the older `competition_budget.py` chain still feeds the
   technical proposal's budget and has not been updated for any recent work.
   Nothing forces them to agree.
2. **The 12 mm lens is uncosted and untested** (§4.8). It would move the survey
   from 40 m to 80 m with identical detection, which is the only credible answer
   to obstacles on unsurveyed ground. Buy the Arducam lens kit and test it.
3. **The ring-aware clipper is six lines and was prototyped, not committed**
   (§4.8). It makes declared obstacles routable around.

**The thing most likely to embarrass us:** the aircraft cannot see a building,
and the mass statement carries relief kits and a parachute the BOM does not buy.
Both are stated in the documents; neither is solved.

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

Documents. **Nothing in these is typed by hand — edit the model, not the .tex.**
The generated files carry a "GENERATED FILE, do not edit" header for a reason.

```sh
# Regenerate everything the BOM feeds, in this order
python hardware/bom/sourced_bom.py               # totals, and the transcription guard
python tools/proposal/build_brief_tables.py      # brief tables + phase schedule
python tools/proposal/build_approval_letters.py  # the 29 DoSA letters
python tools/proposal/build_sizing_section.py    # the proposal's Section V

# Check every numeric claim against the model that owns it
python tools/proposal/verify_proposal_numbers.py   # 64 checks, exits non-zero on any failure

# MATLAB: independent re-derivation, figures, simulations
python matlab/export_model.py                    # Python primitives -> matlab/data/model.json
matlab -batch "cd matlab; run_all"               # verify + figs + sims

# Build the PDFs. TWICE -- the first pass writes the cross-references,
# the second reads them back.
cd docs/proposal
pdflatex -interaction=nonstopmode mentor-brief.tex        # x2  -> 37 pages
pdflatex -interaction=nonstopmode rescueswarm-proposal.tex # x2 -> 22 pages
```

**A clean LaTeX build is not proof the document is right.** See §5: too-wide
content wraps silently inside `center`. Render pages to images and look.

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

### 4.5 Which BOM is authoritative — `sourced_bom.py`, and there are still two

`hardware/bom/sourced_bom.py` **wins**. 59 lines, every one a live listing from
a named Indian supplier with a URL, transcribed from the team's own sourcing
sheet. It is a Python module, not a workbook, because three documents generate
from it and a spreadsheet cannot be asserted against.

```
parts        5,81,034      released   6,85,532      29 phases
```

It carries a **transcription guard**: the module asserts its own total equals
the source sheet's stated total, plus the rows that sheet's SUM range misses,
plus what has been added since. If a line is mistyped, dropped or
double-counted, importing the module raises. That guard is how the sheet's own
arithmetic faults were found (see §5).

Everything downstream generates from it and reconciles by assertion:

| Generated | By | Asserts |
|---|---|---|
| Brief component tables | `tools/proposal/build_brief_tables.py` | every row has a rationale; no orphans |
| Phase schedule | same | per-phase allocation sums to the parts total |
| 29 DoSA approval letters | `tools/proposal/build_approval_letters.py` | the 29 letters sum to the parts total exactly |

**The unresolved part.** The older system — `docs/proposal/figures/competition_budget.py`,
`tools/proposal/build_bom.py`, `BOM.md`, `RescueSwarm_BOM.csv` and the xlsx
workbooks — still exists and still feeds the technical proposal's budget
figures. It has **not** been updated for any of the receiver, obstacle or
missing-component work. The two have diverged. Nothing currently forces them to
agree, and this is the single largest known defect in the repository. Reconcile
before either document goes out alongside the other.

### 4.6 The funding ask, and what moved it

The ask is **₹6,85,532** against **₹5,81,034** of parts. The released figure is
parts plus tax where tax is still owed plus 15 % contingency — *not* duty plus
GST on everything, which is what an earlier revision did and which overstated
the ask by about a lakh. These are Indian retail listings; a listed retail price
is already GST-paid and the duty was paid by whoever put the part on a domestic
shelf. Only supplier quotations and B2B listings carry GST.

Against the ₹7,43,004 the brief once asked, the reduction is about ₹57,000, and
it came entirely from correcting our own arithmetic and one design decision, not
from cutting capability.

**Still open and gating:**

1. **Insurance** was deferred at team direction. Third-party cover is commonly
   mandatory for Indian UAV operations. **Confirm before any flight.**
2. **Relief kits, recovery parachutes and ground-truth apparatus** are deferred
   at team direction (2026-08-18) and are *not* in the BOM. But the mass
   statement still carries the kits at 800 g and the parachute at 300 g per
   aircraft, and the proposal describes both. **The aircraft is designed to lift
   payload the programme does not buy.** The kits are the delivered payload; the
   ground-truth apparatus is what detection recall would be measured against.
   Decisions to revisit, not omissions to patch.
3. Seven phases once exceeded a ₹30 k cap. Re-check against the current
   schedule before assuming that still holds — the phase structure has changed
   twice since.

### 4.7 Receivers — RESOLVED as a hybrid, and the reasoning is in the paper

Two Teravolt AeroNav-Pro RTK (₹25,000 each: **one rover on aircraft 1, one
ground base**) and two Holybro Micro M9N (₹6,939 each, aircraft 2 and 3).

The argument, derived in §IV-D and backed by `matlab/sim/sim_receivers.m`:
everything in the geolocation budget except the receiver sums to 0.88 m, so a
5 m delivery requirement caps the receiver's own error at **2.75 m**. SBAS
clears at 1.85 m CEP95; NavIC's published standalone accuracy fails at 8.79 m.
RTK is retained as *instrumentation*, not for mission accuracy — and an
instrument characterises a design, so one instrumented aircraft is enough. What
P7–P8 measure is where a kit landed, surveyed on the ground, not what the
aircraft believed at the time.

**NavIC is not an alternative to RTK** — it is a constellation, RTK is a
correction technique. Worth having as an *additional* constellation if a module
already tracks it. Ask Teravolt whether the AeroNav-Pro does; it costs nothing.

### 4.8 Obstacles — the scope limit, and the way out nobody has costed

**Nothing on the aircraft can see a building.** There is no forward sensor. The
aircraft flies where a human said it was safe, and if that human missed a
structure it will fly into it. This is now stated in §IV-K rather than left
silent.

Altitude is the only real mitigation, and the sweep is at 40 m — which clears a
rural flood plain and does **not** clear urban building. Worse, it cannot simply
be raised: the survey altitude is pinned by detection, 1498 px² of target at
40 m against 959 px² at 50 m, so climbing over a tall structure costs the
detection the mission exists for.

**The way out, and it is not a sensor.** The 40 m ceiling comes from the *6 mm
lens*, not from physics. The Arducam is CS-mount. A **12 mm lens at 80 m is
identical in every detection term** — same 1.03 cm GSD, same 38.7 px target,
same 41.9 m swath, same 7 transects, same 196 s sweep — at twice the height.
16 mm reaches 120 m.

| | 6 mm at 40 m | 12 mm at 80 m |
|---|---|---|
| Geolocation CEP95 | 1.53 m | 1.62 m — still passes |
| Body-rate gate for 1 px blur | 13.6 °/s | **7.4 °/s** |

The blur gate is the real cost: half the angular pixel scale halves the
tolerable body rate, so turns need tighter detection suppression. **This is
costed nowhere and tested nowhere.** Robu stocks an Arducam LK004 kit
(6/8/12/16/25 mm) — buy one, test, then three of whichever wins.

**Two further things, both small:**

- `autonomy/coverage_planner/boustrophedon.py` uses even-odd scanline fill with
  cell decomposition, which is the right algorithm for routing *around* an
  obstacle, and `_decompose` already groups disjoint runs. It cannot take a hole
  only because `_clip_segment_to_poly` treats its input as one ring. A
  ring-aware version is **six lines** and was prototyped correctly this session
  but **not committed**. Do it — it makes declared obstacles avoidable for free.
- A 360° lidar was priced and is **not recommended**. The 12 m units
  (RPLIDAR A1M8, ₹6,777) only buy an emergency stop, and at 8 m/s stopping needs
  14.7 m. The 40 m RPLIDAR S1 that would let you route around is **₹62,400
  each** — ₹1.87 L for three, a third of the programme. If anything, buy one for
  a P6 experiment; do not fly three untested at a competition.

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

**A third class: a sum that is complete against an incomplete list.** The 29
approval letters were asserted to sum to the parts total exactly, and did. That
proves nothing about whether the parts list is right, and it was not:

- **Frame plate stock** was missing entirely. The arms are carbon tube; nothing
  bought the plate they bolt to. It had been inside a single "Structure,
  in-house fabrication" line in the old cost model, and itemising that line lost
  it.
- **The autopilot log card** was missing. The Pixhawk 6C Mini ships without one
  and records nothing without it; the 128 GB card in the BOM is the companion
  computer's, a different slot on a different board.
- **Phase 2 bought a motor and nothing to spin it.** The phase whose entire
  purpose is measuring thrust had no propeller, no speed controller and no
  throttle source — the safety-pilot transmitter is not bought until phase 11.
  It funded something that could not be switched on.
- **The RTK base was bought 24 phases after the rover.** A rover without its
  base is an ordinary receiver, so aircraft 1 would have flown the whole build
  uncorrected with no ground truth surveyable until the programme was nearly
  over.

The lesson: assert the sum *and* diff the list against the design. Both of the
missing components were found by comparing `sourced_bom.py` against the mass
statement and against the cost model it replaced, not by any arithmetic check.

**A fourth: LaTeX that compiles cleanly and is still wrong.**

- A too-wide title inside `\begin{center}` **wraps silently** — no overfull
  warning, no error. A clean build is not proof of layout. Render pages to
  images and look at them.
- `\begin{center}` around a table adds its own vertical skip, which pushed nine
  one-page letters onto a second sheet carrying only signatures. Use a
  full-width `\makebox` to centre without the skip.
- A blank line inside `\caption{}` breaks it with an error far from the cause.

**A fifth: the editing path into this repo mangles backslashes.** Writing LaTeX
or regex through a shell heredoc has repeatedly turned `\textbf` into a TAB and
`\footnotesize` into a form feed — both of which LaTeX swallows in silence.
`build_approval_letters.py` therefore writes every `\f` sequence through a token
and asserts the per-letter counts before emitting anything. Prefer the editor
over heredocs for anything containing backslashes, and assert after writing.

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
| What the aircraft is actually built from | `hardware/bom/sourced_bom.py` — the xlsx workbooks are superseded, see §4.5 |
| Why each part was chosen | `tools/proposal/build_brief_tables.py`, `RATIONALE` |
| Analysis status: what is done, partial or todo | `matlab/CHECKLIST.md` |
| What was inherited in the GCS and what was wrong with it | `docs/gcs-inherited-review.md` |
