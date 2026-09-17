# Handoff

For whoever picks this up next — a teammate, a reviewer, or me in three weeks
having forgotten all of it.

`README.md` says what the system **is**: design point, scoring, decisions, open
risks. This says what state the work is **in** — what is proven, what is only
modelled, and what is waiting on a human. Read this one first if you are about
to change something.

`TRAPS.md` says what has already gone wrong and what now prevents it. **Read
that one before adding a config file, a generated artifact, or a test.**

Unfamiliar abbreviation? §9 is a glossary.

---

## 0. Where it stands today

**2026-09-04.** Nothing has flown. Every performance figure is calculated or
simulated; the evidence table in §2 says which is which.

> This section deliberately carries **no commit hash**. It used to, and it was
> wrong within one commit of being written, because the commit that updates this
> file is never the commit it can name. `git log -1` is authoritative about where
> the repository is; this section is authoritative about where the *work* is.

| | |
|---|---|
| Funding ask | **INR 6,85,532**, in 29 staged releases, first is INR 3,733 |
| Parts | **INR 5,81,034**, 59 lines, every one a live listing with a URL |
| Technical proposal | 22 pages, 64 automated checks passing |
| Mentor brief | 37 pages: 7 of brief, then 29 DoSA approval letters, one per phase |
| Ground station | Runs; captured live for the paper with synthetic telemetry |
| Tests | 158 autonomy, 49 perception, 64 proposal-number checks |

### The five things to pick up first

Everything marked **P1** anywhere in this document appears in this list. If you
add a P1 elsewhere, add it here too — a priority marker that only exists in the
section it describes is not a priority, it is a note.

1. **P1 — Two BOM systems have diverged** (§4.6). `sourced_bom.py` feeds the
   brief and the letters; the older `competition_budget.py` chain still feeds
   the technical proposal's budget and has not been updated for any recent work.
   Nothing forces them to agree. **The single largest known defect in the
   repository.**
2. **P1 — Attribute the 299 g mass residual** (§2.3). The mass statement lists
   6,061 g against a 6,360 g MTOW and its own percentages sum to 95.3 %.
   Nothing downstream is wrong, but a reader adding the bars up finds 299 g
   missing.
3. **P1 — Confirm insurance before any flight** (§4.7). Third-party cover is
   commonly mandatory for Indian UAV operations. It was deferred at team
   direction; deferring it is a decision that expires the moment anything flies.
4. **Buy and test the 12 mm lens** (§4.9). It moves the survey from 40 m to
   80 m with identical detection, which is the only credible answer to
   obstacles on unsurveyed ground. It is costed nowhere and tested nowhere.
5. **Commit the ring-aware clipper** (§4.9). Six lines, prototyped correctly
   and never committed. It makes declared obstacles routable around, for free.

**The thing most likely to embarrass us:** the aircraft cannot see a building
(§4.9), and the mass statement carries relief kits and a parachute the BOM does
not buy (§4.7). Both are stated in the documents; neither is solved.

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
flying stock parameters. That refusal is deliberate — see `TRAPS.md` §1.

**No GSC commit is pinned anywhere.** Every "measured in SITL" result below was
produced against whatever GSC was checked out at the time, and nothing records
what that was. Worth fixing the next time a result is recorded.

---

## 2. Evidence status — the important table

The single most useful thing to know here is which numbers are **measured**,
which are **modelled**, and which are **assumed**. Treating one for another is
how this project has lost most of its time.

| Claim | Status | When | Where |
|---|---|---|---|
| Battery failsafe returns the aircraft to the pad | **Measured** — SITL, RTL at 10809 mAh of a 10800 mAh trip, three aircraft. Capacity threshold only — see the caveat below | not recorded | `NIDAR-GSC/scripts/test-battery-failsafe.sh` |
| mavlink-router carries three SYSIDs to one GCS port | **Measured** — three SITL, all three arrive | not recorded | `NIDAR-GSC/scripts/test-mavlink-router.sh` |
| Geotag projection is self-consistent | **Measured** — two independent formulations agree to 7.8e-10 m | current | `perception/geotagging/accuracy.py` §1 |
| Geotag CEP50 | **Modelled** — Monte Carlo whose *inputs* are budget assumptions. Reconciles with the analytic budget to +1 % | current | `docs/sizing/geotag-accuracy-output.txt` |
| Separation, all phases | **Measured in sim** — recomputed from committed telemetry by script, compared by CI | 2026-08-18 | `simulations/recordings/separation-output.txt` |
| Take-off stagger is served as commanded | **Measured in sim** — 0/15/30 s commanded, 0/15.5/31.7 s observed at `SIM_SPEEDUP 1` | 2026-08-18 | §2.2 |
| Three aircraft land safely on one pad | **Measured 5.34 m closest airborne approach**, corner slots, sequenced descents | 2026-08-18 | §2.1 |
| Endurance, hover power, mass budget | **Modelled** — no aircraft has flown | current | `docs/sizing/model-output.txt` |
| Detection recall, boresight, RTK accuracy | **Assumed** — no real imagery, no calibration, no hardware | — | — |

Nothing in this project has flown on real hardware. Every "measured" above
means measured in simulation or in software, which rules out whole classes of
error and rules out none of the physical ones.

> **Caveat on the battery failsafe.** SITL holds pack voltage **constant** at
> 25.20 V in every recording here, so only `BATT_LOW_MAH` can ever trip. The
> `BATT_LOW_VOLT` path is **untested and untestable in this harness**, and
> `verify_flight.py` reports it as such rather than passing it silently.

### 2.1 The separation numbers now come from a script

Three separation results used to live here as prose and two did not reproduce.
The launch figure was wrong (this file said 92.12 m against a true 64.80 m) and
the other two were marked "definition-sensitive and left alone" — honest about
the number, and a bad place to leave it.

**The definitions now live in `tools/separation/recompute_separation.py`**,
applied to the committed recordings, with the output committed at
`simulations/recordings/separation-output.txt` and compared byte for byte by CI.
The phase boundaries (a 60 m pad radius, a 1 m ground threshold, pairing by
sample index) are arguments in that file. If you disagree with a definition,
change it there and the documents follow.

Current results, both recordings:

| Phase | speedup-3 recording *(superseded)* | speedup-1 recording *(current)* |
|---|--:|--:|
| launch | 64.80 m | 26.96 m |
| en route | 29.19 m | 35.16 m |
| recovery | 5.51 m | **5.34 m** |

**Read the columns, not just the bold number.** The widely quoted **64.80 m**
launch separation comes from the **superseded** recording, flown at
`SIM_SPEEDUP 3` with the old descent stagger. The current recording gives
**26.96 m** at launch. Deconfliction still works emphatically — it was 1.31 m
before any sequencing existed — but 64.80 m is not the current configuration's
number and should stop being quoted as one.

**The fullest correction record is `docs/proposal/README.md`**, which owns this
history including the 60 m/40 m survey-altitude conflict. This section is a
summary and a pointer; that document is canonical. Do not maintain both.

`simulations/sitl/proof_figures.py:350` still carries a separation result as a
**hardcoded string inside a caption** rather than computing it. See `TRAPS.md`
§7. The four `proof-*.png` figures are rendered from the superseded recording
and are stale until the mission is re-recorded.

### 2.2 The take-off delays — RESOLVED, and this file was two weeks behind

This section used to say the commanded `NAV_DELAY` of 0/15/30 s was not visible
in the telemetry, that the deconfliction *mechanism* was therefore unverified,
and that someone should re-fly at `SIM_SPEEDUP 1`.

**That re-fly happened on 2026-08-18, in commit `bcf3127`, and settled it.** The
recording has been committed at
`simulations/recordings/mission-telemetry-speedup1.json` ever since. Lift-off is
observed at **0 / 15.5 / 31.7 s** against a commanded 0 / 15 / 30, the residual
being climb time to 2 m. The events log carries `Delaying 15 sec` and
`Delaying 30 sec` and the aircraft serve them.

The 0/3.5/10.0 s figures this file used to quote were a **speedup-3 sampling
artifact**, exactly as the harness's own comment predicted. `NAV_DELAY` does
what the mission file says and the proposal's launch-deconfliction mechanism is
verified.

> Two weeks of "someone should check this" sat on top of a committed recording
> that had already checked it. When you close a question, close it in this file
> in the same commit.

### 2.3 The mass statement does not close — **P1**

`docs/sizing/model-output.txt` lists **6,061 g of items against a 6,360 g
MTOW** — a 299 g (4.7 %) unallocated residual, and its own percentages sum to
95.3 %. Nothing downstream is wrong, because structure is derived as
`0.235 × MTOW` rather than summed, but a reader adding the bars up finds 299 g
missing. The proposal now shows the residual as its own bar rather than hiding
it. **Attributing it is a P1 action.**

### 2.4 Neither recording has a clean clock

Both committed recordings have a broken timebase, in different ways, and the
check that was supposed to catch it only looked one way:

| Recording | Max forward gap | Backward steps |
|---|--:|--:|
| speedup-3 *(superseded)* | **453.93 s** | 0 |
| speedup-1 *(current)* | 0.55 s | **17**, worst −2.14 s |

The speedup-1 recording was reported as having a clean clock on the strength of
"max gap 0.55 s across 1201 samples". `verify_flight.py` tested only
`gap > 5 s`, so 17 backward steps passed in silence. It now checks both
directions and reports the backward steps as a WARN.

**This does not affect any separation result** — those pair samples by index,
not by timestamp, which is the only correct choice against a clock like this.
It does mean that **every `t=` in these recordings is a label on a sample, not a
mission time.** Do not quote one as an elapsed duration. See `TRAPS.md` §5 and
§6.

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
cd autonomy   && python -m pytest tests -q     # 158
cd perception && python -m pytest tests -q     #  49

# Firmware parameters. GENERATED -- edit params.py, never the .parm files.
# CI regenerates these and fails on any diff. See TRAPS.md §4 for why.
cd firmware/ardupilot-params && python params.py --drones 3 --out .

# Separation, recomputed from the committed telemetry. Exits non-zero if any
# current recording puts two airborne aircraft closer than 5 m.
python tools/separation/recompute_separation.py

# Is the recorded flight autonomous and clean? Parses the harness AST to prove
# no MAVLink transmit occurs after set_mode(AUTO), then checks separation,
# geofence, failsafes, energy, clock integrity and fix validity.
python simulations/sitl/verify_flight.py simulations/recordings/mission-telemetry-speedup1.json

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

**A clean LaTeX build is not proof the document is right.** Too-wide content
wraps silently inside `center`. Render pages to images and look. `TRAPS.md` §8.

`simulations/recordings/*.json` is committed telemetry from real SITL runs. The
GIFs are gitignored and regenerate from it.

**Do not use `NIDAR-GSC/scripts/run-sim.sh`.** It launches `-v ArduPlane` — a
fixed wing — with no project parameters, and `scripts/README.md` still points at
it. It now refuses to run without an explicit override.

---

## 4. Decisions waiting on a human

These are not blocked on work. They are blocked on someone choosing.

**Nobody owns any of them.** The Owner and Decide-by columns are empty on
purpose: the gap is real, and writing it down is the first step to closing it.
Fill these in — a decision with no name against it does not get made.

| # | Decision | Owner | Decide by |
|---|---|---|---|
| 4.3 | Send the organiser questions | — unassigned — | |
| 4.4 | Confirm corner pad slots with the organisers | — unassigned — | |
| 4.5 | Resolve the `mission_backend` split (3 options) | — unassigned — | |
| 4.6 | **P1** Which BOM is authoritative — reconcile the two | — unassigned — | |
| 4.7 | **P1** Insurance, before any flight | — unassigned — | |
| 4.7 | Relief kits, parachutes, ground-truth apparatus | — unassigned — | |
| 4.8 | `LAND_SPEED` vs the landing reserve | — unassigned — | |
| 4.9 | Buy and test the 12 mm lens | — unassigned — | |

### 4.1 Pad recovery — RESOLVED by moving the slots to the corners

Was: three aircraft aiming at slots 1.22 m apart came to rest **0.83 m** apart,
an overlap of 1.046 m airframes. `rulebook-compliance.md` had argued three
airframes fit the 12 ft pad "3 per row", and `pad_slots()` implemented exactly
that.

A row is the worst possible packing on a square. Centres must stay half an
airframe inside the pad edge, so they live in a 2.61 m square; a row across it
gives 1.31 m at best, its **corners** give the full 2.61 m — twice the
separation, same pad, no cost.

| | row of 3 | 3 corners |
|---|---|---|
| slot spacing | 1.22 m | **2.61 m** |
| worst case, ±0.5 m dispersion each | −0.13 m (overlap) | **1.61 m** |
| measured, closest at any time | 0.83 m (overlap) | **2.27 m** |

Four aircraft also fit, at the four corners. Five do not, and `pad_slots()`
raises rather than returning something that overlaps.

Geometry was only half of it — see §4.2 for the sequencing that had to go with
it.

### 4.2 The descent stagger — a real breach, fixed, reverted, and fixed again

**This is the most instructive defect in the repository. `TRAPS.md` §4 has the
full anatomy.**

Corner slots separate where the aircraft *land*. They do nothing about three
aircraft arriving over one pad at once, and all three hit `BATT_LOW_MAH` within
seconds of each other because they share a pack design and fly missions of
near-equal length. `RTL_LOIT_TIME` holds each aircraft at its return altitude so
only one is descending at a time.

It was set to **0/20/40 s before any descent had been timed.** The
`SIM_SPEEDUP 1` re-fly then measured the descent at **53 s**, so drone 2 began
descending 27.3 s before drone 1 had landed and the two closed to **3.10 m**
against a 5 m minimum.

The fix — 0/60/120 s — was applied **by hand to the generated `.parm` files**
and never to `params.py`. The next regeneration silently put the breach back,
and `test_params.py` asserted the reverted literal, so the suite stayed green on
it for two weeks.

**Now closed three ways:** `params.py` defaults to a 60 s stagger; CI
regenerates the `.parm` files and fails on any diff; and the test asserts that
the stagger covers the measured descent rather than asserting a number.

| | 0/20/40 s | 0/60/120 s |
|---|--:|--:|
| closest airborne approach | 3.10 m — **breach** | **5.34 m** |
| worst-case hold | 40 s | 120 s |
| energy spent queuing | 10.1 Wh, 17 % of the reserve | 30.4 Wh, **52 %** of the reserve |

That last row is the new problem, and it is §4.8.

### 4.3 Organiser questions are drafted and unsent

`docs/requirements/organiser-questions.md`. Several downstream numbers depend
on the answers — particularly whether prior site access allows surveying the
pad, which is worth ~0.4 m of geotag budget.

### 4.4 Confirm the corner layout with the organisers

The aircraft now sit at the pad corners rather than in a line, and brief 7
requires no part of any drone outside the box during launch and landing. Slot
centres are half an airframe inside the edge by construction, so this is
satisfied geometrically — but the staging photo will look different from what a
marshal might expect. Worth asking rather than discovering on the day.

### 4.5 `mission_backend` exists twice, and the copies have drifted

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

### 4.6 Which BOM is authoritative — `sourced_bom.py`, and there are still two — **P1**

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
arithmetic faults were found (`TRAPS.md` §3).

Everything downstream generates from it and reconciles by assertion:

| Generated | By | Asserts |
|---|---|---|
| Brief component tables | `tools/proposal/build_brief_tables.py` | every row has a rationale; no orphans |
| Phase schedule | same | per-phase allocation sums to the parts total |
| 29 DoSA approval letters | `tools/proposal/build_approval_letters.py` | the 29 letters sum to the parts total exactly |

**The unresolved part.** The older system —
`docs/proposal/figures/competition_budget.py`, `tools/proposal/build_bom.py`,
`BOM.md`, `RescueSwarm_BOM.csv` and the xlsx workbooks — still exists and still
feeds the technical proposal's budget figures. It has **not** been updated for
any of the receiver, obstacle or missing-component work. The two have diverged.
Nothing currently forces them to agree, and this is the single largest known
defect in the repository. **Reconcile before either document goes out alongside
the other.**

### 4.7 The funding ask, and what moved it

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

1. **P1 — Insurance** was deferred at team direction. Third-party cover is
   commonly mandatory for Indian UAV operations. **Confirm before any flight.**
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

### 4.8 `LAND_SPEED` versus the landing reserve — new, and unowned

The descent stagger that fixes the pad conflict (§4.2) now spends **52 % of the
landing reserve** on the last aircraft in the queue: 120 s of hold at the 913 W
design hover power is 30.4 Wh of a 58.4 Wh reserve. It still lands — the
remainder is roughly 110 s of hover against a 34 s descent — but the margin fell
from about 6× to about 1.9×.

**The alternative is to shorten the descent rather than lengthen the queue.**
ArduPilot's default `LAND_SPEED` is 0.5 m/s, which is what makes the descent
53 s. Raising it fixes the same conflict for less energy.

It is **deliberately untouched**: descending faster changes control authority
near the ground, and that is a claim simulation is poor at settling. It wants a
flight test before it is adopted, which makes it a decision and not a tuning
value.

`test_the_loiter_stagger_is_affordable_from_the_reserve` documents the trade and
will fail if the queue grows past what the reserve can pay for. **It currently
passes by 1.08 Wh of 58.40 — 1.9 %.** A 61 s stagger would fail it. Read that as
the real state of the margin rather than as a test comfortably passing: the
queue is very nearly as long as the reserve can fund, and the next thing that
needs a second of hold has nowhere to take it from.

### 4.9 Obstacles — the scope limit, and the way out nobody has costed

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
  ring-aware version is **six lines** and was prototyped correctly but **not
  committed**. Do it — it makes declared obstacles avoidable for free.
- A 360° lidar was priced and is **not recommended**. The 12 m units
  (RPLIDAR A1M8, ₹6,777) only buy an emergency stop, and at 8 m/s stopping needs
  14.7 m. The 40 m RPLIDAR S1 that would let you route around is **₹62,400
  each** — ₹1.87 L for three, a third of the programme. If anything, buy one for
  a P6 experiment; do not fly three untested at a competition.

### 4.10 Parts order — unblocked

Cells are unblocked: the design point is **6S3P, 18 cells per aircraft, 54 for
the fleet**. See `docs/sizing/model-output.txt`, which is authoritative over any
prose including this file.

---

## 5. Traps — moved to `TRAPS.md`

The traps section lives in **[`TRAPS.md`](TRAPS.md)** now. It is the section
that only grows and the most reusable thing in this repository, and it was
competing with the project status for a new reader's attention.

Ten classes, each with what looked right, what was true, and what now prevents
it:

| | |
|---|---|
| §1 | Configs that are not in the execution path — **six instances**, the most expensive class here |
| §2 | Numbers that agree with each other and with nothing else |
| §3 | A sum that is complete against an incomplete list |
| §4 | A generated file, edited by hand — shipped a measured safety breach back in |
| §5 | A check that only looks one way |
| §6 | Matching samples by a clock that is not monotonic |
| §7 | Prose beside a formula |
| §8 | LaTeX that compiles cleanly and is still wrong |
| §9 | The editing path into this repo mangles backslashes |
| §10 | Other things that bite |

---

## 6. The CI contract

`.github/workflows/model-check.yml` — jobs: `requirements`, `ground-station`,
`reproduce`, `links`, `perception`, `autonomy`. GSC has `mission-build.yml`.

The rule the `reproduce` job enforces: **every published number regenerates
from its model, and changing a model means committing the regenerated output in
the same commit.** 13 outputs in `docs/sizing/` are compared byte for byte.

It also now regenerates and diffs:

- `simulations/recordings/separation-output.txt` — the separation results,
  recomputed from the committed telemetry.
- `firmware/ardupilot-params/*.parm` — the generated parameter files. This was
  the last generated artifact nothing compared, and a hand-edit to it reverted a
  safety fix for two weeks (§4.2).

This job silently failed for weeks over CRLF before anyone noticed, which is
worth remembering — **a green tick is only worth what the job actually checks.**
`.gitattributes` normalises the compared outputs to LF.

---

## 7. Blocked on hardware or venue

Not actionable until something physical exists: 868 MHz safety radio link,
venue map tiles, boresight calibration, detection recall on real imagery,
pack internal resistance by bench discharge, `LAND_SPEED` validation (§4.8),
and every flight-test line in `docs/development-plan.md`.

---

## 8. Where to look

| Question | File |
|---|---|
| What is the system, what did we decide, what are the risks | `README.md` |
| What has already gone wrong, and what stops it now | `TRAPS.md` |
| Why every number is what it is | `docs/sizing/sizing-calculations.md` |
| What the rulebook requires and whether we meet it | `docs/requirements/rulebook-compliance.md` |
| Requirement IDs (`SYS-*`) | `docs/requirements/requirements-baseline.md` |
| Plan of work and schedule | `docs/development-plan.md` |
| What the CAD designer needs | `hardware/cad/CAD-BRIEF.md` |
| What the perception owner needs | `docs/perception-integration-plan.md` |
| Cost and indigenisation | `docs/business/cost-and-economics.md` |
| The funding proposal, and its correction record | `docs/proposal/` — read the README before the PDF |
| What the aircraft is actually built from | `hardware/bom/sourced_bom.py` — the xlsx workbooks are superseded, see §4.6 |
| Why each part was chosen | `tools/proposal/build_brief_tables.py`, `RATIONALE` |
| Analysis status: what is done, partial or todo | `matlab/CHECKLIST.md` |
| What was inherited in the GCS and what was wrong with it | `docs/gcs-inherited-review.md` |
| Separation, recomputed from telemetry | `tools/separation/recompute_separation.py` |

---

## 9. Glossary

Everything this document uses without explaining. A teammate knows these; a
reviewer does not, and §0 is written for both.

| Term | What it means here |
|---|---|
| **AGL** | Above ground level, as opposed to above sea level. |
| **BOM** | Bill of materials — the parts list. §4.6 is about there being two. |
| **CEP50 / CEP95** | Circular error probable: the radius containing 50 % / 95 % of position fixes. The delivery requirement is stated as a CEP. |
| **DoSA** | Dean of Student Affairs — the office that approves each funding release. One approval letter per phase, 29 of them. |
| **GSD** | Ground sample distance — how many centimetres of ground one pixel covers. Sets whether a person is detectable. |
| **GSC** | Ground Station Computer — the other repository (§1). |
| **MTOW** | Maximum take-off weight. 6,360 g here; §2.3 is about 299 g of it being unattributed. |
| **NavIC** | India's regional satellite navigation constellation. A constellation, **not** an alternative to RTK (§4.9's sibling argument in `docs/proposal/`). |
| **P1 … P11** | Programme phases — the 29 staged funding releases group into these. "P7 recall measurement" means the flight test in phase 7. |
| **RTK** | Real-time kinematic — a correction technique using a ground base station to bring GNSS error to centimetres. Needs a base *and* a rover. |
| **SBAS** | Satellite-based augmentation — a weaker correction than RTK, needing no ground station. |
| **SITL** | Software in the loop — ArduPilot flying a simulated aircraft. Every "measured" result here is SITL. |
| **SYS-nn** | A requirement ID from `docs/requirements/requirements-baseline.md`. SYS-20 is the one §4.5 is verified against. |
| **brief 7** | Item 7 of the competition mission brief: no part of any drone outside the pad during launch and landing (§4.4). |
| **boustrophedon** | The back-and-forth "as the ox ploughs" survey pattern the coverage planner flies. |
