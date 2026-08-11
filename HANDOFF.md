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
| Separation en route | **Measured in sim** — 34.00 m worst pair | `proof-2-sweep.png` |
| Separation during recovery | **6.52 m**, up from 3.99 m | `proof-4-pad.png` |
| Three aircraft land safely on one pad | **Measured 2.27 m minimum, clear by 1.22 m** — corner slots, not a row | `proof-4-pad.png` |
| Endurance, hover power, mass budget | **Modelled** — no aircraft has flown | `docs/sizing/model-output.txt` |
| Detection recall, boresight, RTK accuracy | **Assumed** — no real imagery, no calibration, no hardware | — |

Nothing in this project has flown on real hardware. Every "measured" above
means measured in simulation or in software, which rules out whole classes of
error and rules out none of the physical ones.

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
values back off the running system**. `validate()` in `params.py` now rejects a
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
| What was inherited in the GCS and what was wrong with it | `docs/gcs-inherited-review.md` |
