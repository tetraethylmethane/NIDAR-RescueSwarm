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
| Aircraft separation in flight | **Measured in sim** — 6.77 m worst airborne pair | `simulations/recordings/` |
| Three aircraft land safely on one pad | **FALSE.** Measured 0.82 m between 1.046 m airframes | §4.1 |
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
cd autonomy   && python -m pytest tests -q     # 119
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

### 4.1 Three aircraft cannot land on one 12 ft pad

The one that matters. Rule 8.10 gives a single 3.66 m pad, and
`docs/requirements/rulebook-compliance.md` argues three 1.046 m airframes fit
"3 per row". That is true for **parking** them by hand and false for
**landing** them:

| phase | min separation | |
|---|---|---|
| both airborne | 6.77 m | fine — the `RTL_ALT` stagger works |
| one landing, one parked | 1.83 m | thin |
| both parked after landing | **0.82 m** | airframes overlap |

Slots are 1.22 m apart and touchdown dispersion is roughly ±0.5 m, so the
geometry allows 0.17 m of error and the aircraft need about three times that.
Sequencing the descents (`RTL_LOIT_TIME` 0/20/40 s) does not help: this is
static geometry, not timing.

Options, none of which I should pick for you:

1. **Precision landing** — IR-LOCK beacon or RTK precision loiter. Buys the
   accuracy directly, costs money and integration time.
2. **Recover one at a time**, with ground crew clearing each aircraft before
   the next descends. Free, needs a rule check that it is permitted.
3. **Land off-pad** and accept −10 per aircraft.

Until this is decided, treat the pad as a launch surface only.

### 4.2 Takeoff is not sequenced

Cheap and unambiguous, just not done: all three launch together, and the
mission run measured 1.3 m between aircraft at 2–3 m altitude. A staggered
`NAV_DELAY` as the first mission item fixes it deterministically. Say the word.

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
