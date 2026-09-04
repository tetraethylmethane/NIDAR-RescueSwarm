# Funding proposal

`rescueswarm-proposal.tex` — IEEEtran conference format, **9 pages, 6 figures**.

## Figures

| Fig. | Content | Source |
|---|---|---|
| 1 | System architecture | TikZ, drawn in the document |
| 2 | Autonomous mission sequence | TikZ, drawn in the document |
| 3 | Launch deconfliction, before/after | [`proof-1-launch.png`](../../simulations/recordings/) |
| 4 | Recovery pad slot geometry | [`proof-4-pad.png`](../../simulations/recordings/) |
| 5 | Coverage decomposition and return geometry | [`proof-2-sweep.png`](../../simulations/recordings/) |
| 6 | Ground control station | [`gcs-running.png`](../../ground-station/) |

Figures 3–6 are committed simulation output, referenced in place via
`\graphicspath` rather than duplicated into this directory. Figure 6 is used
**uncropped**, including the panel showing that abort/recall is not yet wired to
a safety radio; the proposal states this in §VI-C rather than hiding it.

## Building

```sh
cd docs/proposal
pdflatex rescueswarm-proposal.tex
pdflatex rescueswarm-proposal.tex   # second pass resolves cross-references
```

Compiles clean: **0 errors, 0 overfull boxes, 7 pages.** Build artefacts
(`.pdf`, `.aux`, `.log`, `.out`) are gitignored and regenerate from the source,
the same convention the simulation GIFs use.

**Dependencies.** `IEEEtran`, `amsmath`, `amssymb`, `graphicx`, `booktabs`,
`array`, `url`, `hyperref`. On a minimal MiKTeX install, `mpm --update-db`
followed by `mpm --require=<pkg>` resolves them; `hyperref` pulls a long
dependency chain. `cite` and `balance` are deliberately **not** required — both
are optional conveniences, and omitting them keeps the document compilable on a
stock installation.

## Before sending it anywhere

Two `TODO` markers are live in the source:

| Location | What is needed |
|---|---|
| `\author{...}` | Names, department, institution, city, emails |
| `\section*{Acknowledgment}` | Institutional support, mentors, suppliers who provided evaluation hardware |

## Cost options: corrected on review, 2026-08-12

The first cost pass was reviewed and **four errors were found**. They are
recorded here, and in §VII-C of the proposal itself, because a corrections
record is worth more than a clean-looking table.

| | First pass | Corrected |
|---|--:|--:|
| B — efficiency only | 2,59,001 | **2,63,401** |
| C — + indigenisation trade | 2,07,295 | **2,37,081** |
| D — floor | 1,29,632 | **1,83,640** |

**1. Option C was labelled with the wrong penalty.** It was marked as losing
~125 geolocation points. It does not: C keeps RTK and only deletes the
*moving-baseline heading* receiver. Substituting the magnetometer-class attitude
allocation from `sizing-calculations.md` §11 into the case-C budget moves the
total from **1.304 m to 1.322 m** — an 18 mm degradation. The 125-point penalty
belongs to Option D, which deletes RTK itself.

**2. The motor saving was circular.** It booked ₹8,396 by pricing the motor at
₹7,000 — a figure the same study argues is *below the lowest listing found*
(₹9,099). Withdrawn; the motor is now 9,099 in every column.

**3. The ESC saving was a specification failure.** ₹1,600 was booked against a
part whose catalogue advertises 30–45 A for a 60 A requirement. Withdrawn.

**4. Compliance was treated as optional.** The sub-GHz radio was priced at
₹1,560 (a 433 MHz kit) in the lowest option while the same document argued that
figure does not buy a compliant 865–867 MHz link. The compliant ₹19,355 is now
carried in **every** column — a legal band is not an option-level choice.

Net effect: the floor moved **up** by ₹54,008. That strengthens the conclusion
rather than weakening it — an aircraft that flies this mission is further from
₹1,00,000 than the first estimate suggested.

**One finding survived and improved.** Option B raises indigenous content from
58 % to 61 %, because the line it shrinks is the imported accelerator. Cost
reduction and indigenisation are usually opposed; on this one step they are not.

## The abort path names its mechanism, and the mechanism has a trap

Deleting the sub-GHz safety radio rests entirely on the ExpressLRS link carrying
**both** safety-pilot control and the abort path. The proposal asserted that and
never said how, which left a load-bearing claim uncheckable.

It now names the mode, because **only one of the two available modes actually
works this way**:

| ELRS mode | RC control | MAVLink telemetry | Verdict |
|---|---|---|---|
| **Native MAVLink (3.5+)** | yes | yes | **required** — one link, one UART |
| AirPort (older) | **no** | yes | **breaks the deferral** |

AirPort is a transparent serial bridge that *consumes* the link. A build
configured that way has telemetry and no control, and needs a **second radio**
to fly. That is not theoretical: the widely-followed build video "Building a sub
250g Autonomous Drone with Ardupilot and ExpressLRS AirPort Telemetry" hits this
exact wall and solves it by buying a second ELRS pair **at 868 MHz** — which is
the sub-gigahertz set this budget deletes.

**So: configured wrongly, the deferral is not a saving, it is a defect** — and
it surfaces at integration, not at review. The requirement is recorded on the
receiver line in `competition_budget.py` so it travels with the BOM rather than
living only in prose.

Native MAVLink is independently tested to 126 km without failsafe, against our
600 m geofence.

**Consequence now stated in the proposal:** the abort path inherits the link's
availability. An outage removes the operator's fastest intervention until the
link returns or the 60 s link-loss timer fires the autonomous return. The
aircraft is never without *a* recovery path; it can be briefly without an
*operator-commanded* one. Measuring outage against range and attitude is a P6
objective.

## Flight-controller options, priced

There are no development mules in the funded build — the three aircraft *are*
the competition set — so "cheap board on the mules" does not map to a budget
line. What does map is the deferred spare.

| | Ask | vs. status quo | Spare-FC risk |
|---|--:|--:|---|
| **A** Pixhawk x3, spare deferred *(current)* | 8.24 L | — | accepted |
| **B** Matek x3, spare deferred | **7.81 L** | −0.43 L | accepted |
| **C** Pixhawk x3 + one Matek **as the spare** | 8.36 L | +0.12 L | **retired** |
| **D** Matek x3 + one Matek spare | 7.92 L | −0.32 L | **retired** |

Holybro Pixhawk 6C Mini **₹22,600** against Matek H743-WING/SLIM
**₹8,999–10,656** — same STM32H743 at 480 MHz, same ArduPilot feature set, 7
UARTs. The real trade is the Pixhawk connector standard and on-board IMU
vibration isolation, not capability. Radiolink CrossFlight was checked and is
**₹30,400** — more expensive than what we already have, so it is not a candidate.

**Option C is the interesting one**: it retires an accepted risk (`Spare flight
controller — 26,000 — DEFERRED`) for ₹10,000 rather than ₹26,000, and the spare
doubles as the bench board. It costs 0.12 L instead of saving 0.43 L.

## Battery failsafe is staged

Reserve threshold commands RTL; a second, lower threshold commands immediate
landing where the aircraft stands. A pack that cannot reach the pad should land
under control at the point it admits this, rather than descend uncommanded
partway home.

## Two text defects visible in the ground-station screenshot

The proposal now uses the restyled dashboard (`ground-station/gcs-dashboard.png`,
copied from `frontend/public/Drikr NIDAR Dashboard.png` under a filename LaTeX
can handle). It is a real capture of the running system — Leaflet attribution,
live tiles, three decoded feeds — not a render, which is why it is usable as
evidence at all.

**Two strings in the UI need fixing in NIDAR-GSC before this goes to a sponsor.
They are visible at full size in the figure.**

| Shown | Should read |
|---|---|
| `NSSSION WINDOW` | `MISSION WINDOW` |
| `MTI EMERGENCY: Bus safety route configured.` | something coherent — the previous build read `NOT IMPLEMENTED — no safety radio configured` |

The second matters more than a typo. The old wording stated a real limitation
clearly; the new one is garbled, and a reviewer reading "Bus safety route
configured" next to a disabled ABORT button will not know what is being claimed.
The rest of that panel is still correct and admirably blunt: *"These buttons
record intent to the mission log but transmit nothing. Recover the aircraft with
the safety pilot's RC."*

**The frontend source is not in this repository.** `ground-station/frontend/`
holds only `.gitkeep` and `public/`; the UI lives in NIDAR-GSC. These two fixes
have to be made there.

## The take-off delays — RESOLVED, and NAV_DELAY is vindicated

> **Resolved 2026-08-18 in commit `bcf3127`, by re-flying at `SIM_SPEEDUP 1`.**
> Lift-off is observed at **0 / 15.5 / 31.7 s** against a commanded 0 / 15 / 30,
> the residual being climb time to 2 m. The recording is committed at
> `simulations/recordings/mission-telemetry-speedup1.json`.
>
> The 0 / 2.8 / 9.4 s figures below were a **speedup-3 sampling artifact**,
> exactly as the SITL harness's own comment predicted. `NAV_DELAY` does what the
> mission file says, and the proposal's launch-deconfliction *mechanism* is
> verified, not merely its result.
>
> The investigation is kept below because its reasoning was sound and its
> conclusion was wrong, which is worth being able to re-read. **Everything from
> here to the end of this section describes the superseded recording.**


Re-rendering the launch figure from the raw recording surfaced this. The mission
file sets `NAV_DELAY` to **0 / 15 / 30 s** before each take-off, and the
autopilots log it — `Delaying 15 sec`, `Delaying 30 sec`. But the aircraft are
observed leaving the pad at:

| aircraft | commanded | logged take-off | first altitude > 2 m |
|---|--:|--:|--:|
| 1 | 0 s | 0.00 s | 0.00 s |
| 2 | 15 s | 2.80 s | 3.50 s |
| 3 | 30 s | 9.40 s | 10.01 s |

Aircraft 3 delayed 9.2 s against a commanded 30; aircraft 2 delayed 2.7 s
against a commanded 15. The ratios are not consistent with each other, so this
is not simply a `SIM_SPEEDUP` time-base conversion.

**The supporting argument here was wrong and has been replaced.** This
previously read "`done_at` of 626 s is consistent with `t` being simulated
seconds." That figure is an artifact. Building the dashboard replay surfaced
**exactly one interval in the 346-sample recording that exceeds 5 s: index 328
jumps 453.93 s**, against a median interval of 0.500 s. The aircraft state does
not jump with it — drone 3 descends 13.9 → 11.6 m across the boundary, the same
2.25 m per sample it was doing either side, while drones 1 and 2 sit frozen at
identical altitude and identical mAh. The recorder's clock moved; the vehicles
did not. **Physical duration is 172.4 s, not 626 s.**

The conclusion survives on better evidence. Drone 3 drew **2,082 mAh**. Over
172 s that is 43.5 A average, the right order for hovering a 6.36 kg aircraft;
over 626 s it would be 12 A, which that aircraft cannot hover on. So the mAh
counter — which integrates over *simulated* time — independently puts the flight
at about 172 s, and `t` does track simulated seconds after all.

**That makes the NAV_DELAY finding stronger, not weaker.** If `t` is simulated
seconds, commanded delays of 0/15/30 s should appear as take-offs at 0/15/30 s.
They appear at 0/2.8/9.4. There is no time-base conversion left to explain it
away: the delays are genuinely not being served.

**The deconfliction still works** — closest airborne pair goes 1.31 m → 64.80 m,
and that is measured, not assumed. What is unverified is the *mechanism*: the
document says the spacing comes from a 0/15/30 s stagger, and the recording does
not show those delays being served.

The figure therefore plots **observed** lift-off, not commanded. Two things were
worth doing before this could be quoted as evidence of the mechanism, and both
have since been done:

1. ~~Establish whether `t` is simulated or wall-clock time.~~ It tracks
   simulated seconds, as the mAh argument above concluded. But the clock is
   **not monotonic** in either recording — see the note below.
2. ~~Re-fly at `SIM_SPEEDUP 1`.~~ Done, `bcf3127`. The delays are served
   correctly, so this was a simulation artefact and not a fifth instance of the
   defect class in `TRAPS.md` §1.

**A note the re-fly added rather than closed.** The speedup-1 recording was
reported as having a clean clock on the strength of "max gap 0.55 s across 1201
samples". Its clock steps **backwards 17 times**, worst −2.14 s;
`verify_flight.py` only tested forward gaps and passed it in silence. It now
tests both directions. No separation result is affected, because those pair
samples by index — but **no `t=` from either recording is a mission time.**
`TRAPS.md` §5 and §6.

## Separation numbers — this document owns the correction record

**This section is canonical.** `HANDOFF.md` §2.1 carries a summary and points
here. Do not maintain both.

Writing the figure captions meant recomputing the separation results from
[`mission-telemetry.json`](../../simulations/recordings/). **Three numbers in
`HANDOFF.md` §2 did not reproduce**, and one was definitively wrong:

| Claim | HANDOFF.md said | Reproduced from telemetry | Also said |
|---|--:|--:|---|
| Separation at launch | 92.12 m | **64.80 m** | `README.md` and the figure itself both say 64.80 m |
| Separation en route | 34.00 m | 29.19 m | definition-sensitive |
| Stacked over the pad | 6.52 m | 5.51 m | hardcoded as a caption string in `proof_figures.py:350` |

The launch figure was not a definition question: `README.md`,
`proof-1-launch.png` and the raw telemetry all agree on **64.80 m**, and only
`HANDOFF.md` said 92.12 m. Corrected in place.

**The other two are no longer "definition-sensitive and left alone".** That was
an honest thing to say about a number and a bad place to leave it: neither the
document nor the recording could settle the disagreement without re-deriving the
definition from scratch. The definitions now live in
[`tools/separation/recompute_separation.py`](../../tools/separation/recompute_separation.py)
— pad radius, ground threshold, phase boundaries, all arguments in one file —
applied to the committed recordings, with the output committed at
`simulations/recordings/separation-output.txt` and compared byte for byte by CI.
A disagreement between this document and a recording is now a build failure.

Recomputed for both recordings:

| Phase | speedup-3 *(superseded)* | speedup-1 *(current)* |
|---|--:|--:|
| launch | 64.80 m | 26.96 m |
| en route | 29.19 m | 35.16 m |
| recovery | 5.51 m | **5.34 m** |

**The proposal should stop quoting 64.80 m as the launch separation.** That
figure comes from the superseded recording, flown at `SIM_SPEEDUP 3` with the
old 0/20/40 s descent stagger. The current configuration gives **26.96 m**.
Deconfliction still works emphatically — it was 1.31 m before any sequencing
existed — but the number in the document is not the number the current aircraft
produces.

`proof_figures.py:350` still carries a separation result as a hardcoded caption
string rather than computing it, and the four `proof-*.png` figures are rendered
from the superseded recording. Both are stale until the mission is re-recorded.

The proposal uses only the reproducible figures.

## The proposal flies at 60 m; the simulation flies at 40 m

Adding the processing-pipeline section surfaced this. The design point table
says **Survey altitude 60 m AGL**, the geolocation budget is computed at 60 m,
and Fig. 5 draws the sweep as "60 m AGL". But every committed recording was
flown at **40 m** — `fly_and_record.py` passes `altitude_m=40.0`, the telemetry
carries `search_alt: 40.0`, and the median cruise altitude is 40.6 m.

So the flight evidence in Section VI does not describe the aircraft in Table I.

**Neither number is obviously wrong, which is why this is recorded rather than
patched.** `docs/sizing/configuration-trade.md` §5.3 explicitly *proposes*
re-baselining to 40 m — it buys 50 % more pixels on target (140 px against
93 px) for 56 s of an 1800 s budget — but marks it **PROPOSED pending a P7
recall-vs-GSD measurement**, not adopted. The simulation harness appears to
have moved to the proposed value while the proposal stayed on the old one.

Changing it is not a one-line edit. Survey altitude sets swath, which sets line
spacing, transect count, sweep time and the whole geolocation error budget, and
the perception subsection's 2 cm/px → 85 px → 47 px chain is computed at 60 m.
**Whichever way this resolves, Table I, Section IV-C, Section IV-D and Fig. 5
have to move together.**

## Open issues a reader should know about

**The design point is contested.** This document uses the **18 in / 6.36 kg**
configuration from [`docs/sizing/`](../sizing/). The verified BOM
([`RescueSwarm_BOM_India_Verified.xlsx`](../../hardware/bom/)) describes a
**17 in / 5.78 kg** aircraft, and its README says the design point was "revised
to fit real Indian parts". A header comment in the `.tex` flags this. **If the
17 in configuration is adopted, Table I and Section VII must change together** —
and the sizing model needs re-running, not just the numbers editing.

**Two references need checking against what was actually read.**
`mathisen2020airdrop` cites the deep-stall landing paper; the release-velocity
sensitivity result attributed to it in Section III-D should be verified against
the specific source before submission. `zhu2021visdrone` should be checked for
the correct volume and page range.

## Where the numbers come from

| Section | Source |
|---|---|
| Design point (Table I) | [`docs/sizing/model-output.txt`](../sizing/model-output.txt) |
| Geolocation budget (Table II) | [`docs/sizing/geotag-accuracy-output.txt`](../sizing/geotag-accuracy-output.txt) |
| Phases (Table III) | [`docs/development-plan.md`](../development-plan.md) |
| Cost options (Table IV) | [`RescueSwarm_Cost_Study.xlsx`](../../hardware/bom/) |
| Programme cost (Table V) | [`docs/sizing/cost-model-output.txt`](../sizing/cost-model-output.txt) |
| Preliminary results | [`HANDOFF.md`](../../HANDOFF.md) §2 evidence table |

Every figure in the proposal traces to one of these. If one of them moves, the
proposal is stale — there is no CI gate on this document, unlike the model
outputs it draws from.
