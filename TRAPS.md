# Traps

Defects this project has already paid for, grouped by the shape of the mistake
rather than by the subsystem it happened in. **Read this before adding a config
file, a generated artifact, or a test.**

This was §5 of `HANDOFF.md`. It moved because it is the section that only grows,
it is the most reusable thing here, and it was competing with the project status
for a new reader's first five minutes. `HANDOFF.md` §5 now points here.

Every entry follows the same shape: what looked right, what was actually true,
and what now prevents it. If you add one, keep that shape — an entry that only
says what broke teaches nobody.

---

## 1. Configs that are not in the execution path

**The most expensive class of defect on this project. Six instances so far.**

Each of these reviewed clean, had passing tests around it, and configured
nothing.

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
- `GPS_TYPE2 = 1` — committed for a moving-baseline receiver the budget defers,
  while the SITL harness forced it to 0 at runtime. The committed parameters
  were never the flown parameters, and flashed as-is the aircraft would not arm
  (`GPS 2: was not found`). Now 0 in both, with the harness comment explaining
  why it stays.

The only thing that catches this class is running the real artifact end to end
and **reading the values back off the running system.**

---

## 2. Numbers that agree with each other and with nothing else

Where §1 is about artifacts that are not in the execution path, this is about
figures that are internally consistent and externally wrong. Found by reviewing
the funding proposal three times.

- The proposal asserted **45 % indigenous content** in four places. It agreed
  with itself everywhere and was wrong everywhere — the computed figure is
  **35.5 %**. Nobody had ever run the calculation.
- It paired **2 cm/px with "roughly fifty pixels"**. At 2 cm/px a 1.7 m person
  is 85 px; the 47 px figure belongs to the 2× downsampled image. Two correct
  numbers from `sizing-calculations.md` §8, joined into a false statement.
- `HANDOFF.md` itself carried **92.12 m** for launch separation while the
  figure, `README.md` and the raw telemetry all said 64.80 m.
- `rescueswarm_sizing_model.py` hardcoded the camera as a 1/1.8" sensor on a
  1.82 µm pitch, a part the programme does not buy. Every field of view, GSD,
  transect count and blur figure downstream was computed for the wrong part.
  The block now derives the sensor from its pitch so the substitution cannot be
  made silently again.

**The lesson is narrower than "check your numbers": internal consistency is not
evidence.** A figure repeated in four places is not corroborated, it is copied.
Check each number against the thing that *generates* it — the model output, the
telemetry, the arithmetic — and never against the other places it appears.

`validate()` in `params.py` now rejects a table of known-phantom parameter
names, because `BATT_RESISTANCE` sat in the parameter files for weeks doing
nothing: it is a PX4 name, ArduPilot estimates internal resistance itself, and
`.parm` drops unknown names in silence.

---

## 3. A sum that is complete against an incomplete list

The 29 approval letters were asserted to sum to the parts total exactly, and
did. That proves nothing about whether the parts list is right, and it was not:

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
  uncorrected, with no ground truth surveyable until the programme was nearly
  over.

**The lesson: assert the sum *and* diff the list against the design.** Both
missing components were found by comparing `sourced_bom.py` against the mass
statement and against the cost model it replaced, not by any arithmetic check.

---

## 4. A generated file, edited by hand

**Added 2026-09-04. This one shipped a measured safety breach back into the
repository and every test stayed green.**

`RTL_LOIT_TIME` sequences the descents onto the shared 3.66 m pad — each
aircraft holds at its return altitude while the one below it lands. It was set
to 0/20/40 s before any descent had been timed.

1. Commit `bcf3127` re-flew the mission at `SIM_SPEEDUP 1` and **measured** the
   descent at 53 s. At a 20 s stagger, drone 2 began descending 27.3 s before
   drone 1 had landed, and the two closed to **3.10 m** against a 5 m minimum.
2. That commit fixed it — by editing `rescueswarm-drone*.parm` **by hand**, to
   0/60/120 s. It did not touch `params.py`, which generates those files.
3. Commit `5a1ab73` regenerated the `.parm` files for an unrelated fix.
   `params.py` still said 20 s. The breach came back, in a diff that looked like
   routine regeneration, and its commit message never mentions it.
4. `test_params.py` asserted `loiters == [0, 20000, 40000]` — the literal
   reverted value — so the test suite went green on the reverted configuration
   and stayed green for two weeks.

**Three separate things had to be true for this to survive**, and all three are
now closed:

| What let it through | What now stops it |
|---|---|
| A generated file was hand-edited | CI regenerates the `.parm` files and fails on any diff |
| The generator was never updated | `rtl_loiter_stagger_s` defaults to 60 s in `params.py` |
| The test asserted a literal, not a relationship | `test_the_stagger_covers_the_measured_descent` asserts the stagger ≥ the measured 53 s descent |

**The general rule: if a file is generated, the only correct place to fix it is
the generator, and CI must regenerate it.** A hand-edit to a generated artifact
is not a fix, it is a fix with a deletion scheduled for the next person who runs
the generator.

**The second rule: a test that asserts a literal cannot detect a revert to that
literal.** Assert the relationship that makes the value correct — here, that the
queue spacing covers the descent it has to cover. See
`autonomy/tests/test_params.py`.

---

## 5. A check that only looks one way

**Added 2026-09-04.**

`verify_flight.py` tests recording integrity with
`big = [g for g in gaps if g > MAX_CLOCK_GAP_S]`. That only ever sees the clock
jumping **forward**.

The speedup-3 recording has a 453.93 s forward jump, which this caught. The
speedup-1 recording that replaced it was then reported as having a clean clock
on the strength of "max gap 0.55 s across 1201 samples" — and its clock steps
**backwards 17 times**, worst −2.14 s. One clock defect was fixed and a
different one was never looked for.

A backward step is not greater than 5, so it passed in silence. The check was
real; it was not checking the thing that broke. `verify_flight.py` now tests
both directions.

**When you write a threshold check, ask what the value looks like when it fails
in the other direction.**

---

## 6. Matching samples by a clock that is not monotonic

**Added 2026-09-04. Found by writing the script in §7 and getting it wrong.**

`tools/separation/recompute_separation.py` first paired the three aircraft by
nearest timestamp. Against a clock that repeats and reverses (see §5) that
silently pairs samples from completely different parts of the flight: it
reported a 27 m minimum separation where the true figure is **5.34 m** — an
error of the size that would have hidden a real conflict.

The recorder writes one row per aircraft per poll, so **index `k` is the same
poll for every aircraft**. Pair by index, and assert that the tracks are equal
length and share a timestamp sequence rather than assuming it.

**The timestamps in these recordings are labels on samples, not mission times.**
Do not quote a `t=` from them as an elapsed time without re-establishing the
clock first.

---

## 7. Prose beside a formula

A number written next to the code that should compute it will diverge from it.

- `simulations/sitl/proof_figures.py:350` carries a separation result as a
  **hardcoded string inside a caption** rather than computing it from the
  telemetry the figure plots — in the script that generates the project's
  evidence.
- Three separation results lived in `HANDOFF.md` as prose and two did not
  reproduce. They were marked "definition-sensitive", which is honest about a
  number and a bad place to leave one: neither the document nor the recording
  could settle it without re-deriving the definition from scratch.

The definitions now live in `tools/separation/recompute_separation.py`, applied
to the committed recordings, with the output compared byte for byte by CI. A
disagreement between a document and a recording is now a build failure rather
than an argument.

---

## 8. LaTeX that compiles cleanly and is still wrong

- A too-wide title inside `\begin{center}` **wraps silently** — no overfull
  warning, no error. A clean build is not proof of layout. **Render pages to
  images and look at them.**
- `\begin{center}` around a table adds its own vertical skip, which pushed nine
  one-page letters onto a second sheet carrying only signatures. Use a
  full-width `\makebox` to centre without the skip.
- A blank line inside `\caption{}` breaks it with an error far from the cause.

---

## 9. The editing path into this repo mangles backslashes

Writing LaTeX or regex through a shell heredoc has repeatedly turned `\textbf`
into a TAB and `\footnotesize` into a form feed — both of which LaTeX swallows
in silence.

`build_approval_letters.py` therefore writes every `\f` sequence through a token
and asserts the per-letter counts before emitting anything.

**Prefer an editor over a heredoc for anything containing backslashes, and
assert after writing.**

---

## 10. Other things that bite

- `FENCE_RADIUS` is 600 m, chosen for the link budget. It caps how far the
  search area can sit from launch. A first sim run had all three aircraft
  breach and RTL three seconds into the sweep.
- `SIM_BATT_CAP_AH` set at **runtime** does not drive the SITL battery model.
  Set it at boot via `--defaults` or the pack never sags.
- `--defaults` in ArduPilot SITL takes a **comma-separated list**, applied left
  to right. Verified, not assumed.
- `SIM_BATT_VOLTAGE` must be set too, or the vehicle boots below its own
  `BATT_LOW_VOLT` and can never arm.
- SITL holds pack voltage **constant** at 25.20 V in every recording here, so
  only the capacity threshold can ever trip. **The `BATT_LOW_VOLT` path is
  untested** and cannot be tested in this harness.
- Seeding anything from `hash()` on a string makes it non-reproducible: Python
  randomises string hashing per process. Use `zlib.crc32`.
- Generating a committed output with PowerShell `>` adds a UTF-8 BOM that
  `--strip-trailing-cr` will not strip, and the reproduce job fails on line 1.
  Generate through a shell that writes raw bytes.
- Non-ASCII characters in a committed generated output will not survive a
  Windows console redirect. Keep generated text ASCII.
- Run tests the way CI runs them — from inside `autonomy/` and `perception/`,
  not from the repo root, which hides import errors CI then catches.
- The `reproduce` job silently failed for weeks over CRLF before anyone
  noticed. **A green tick is only worth what the job actually checks.**
  `.gitattributes` now normalises the compared outputs to LF.
