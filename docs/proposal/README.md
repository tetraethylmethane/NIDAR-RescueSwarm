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

## Separation numbers: HANDOFF.md is stale

Writing the figure captions meant recomputing the separation results from
[`mission-telemetry.json`](../../simulations/recordings/). **Three numbers in
`HANDOFF.md` §2 do not reproduce**, and one of them is definitively wrong:

| Claim | HANDOFF.md | Reproduced from telemetry | Also says |
|---|--:|--:|---|
| Separation at launch | 92.12 m | **64.80 m** | `README.md` and the figure itself both say 64.80 m |
| Separation en route | 34.00 m | 29.19 m | definition-sensitive |
| Stacked over the pad | 6.52 m | 5.51 m | hardcoded as a caption string in `proof_figures.py:350` |

The launch figure is not a definition question: `README.md`, `proof-1-launch.png`
and the raw telemetry all agree on **64.80 m**, and only `HANDOFF.md` says
92.12 m. That one has been corrected in place.

The other two depend on how the phase boundary is drawn — my "en route" excludes
a 60 m radius around the pad — so they are **left alone pending a decision on the
definition**, not silently overwritten. The recovery figure is worth attention
because `proof_figures.py` carries it as a hardcoded string in a caption rather
than computing it, which is the failure mode this repository is organised
against.

The proposal uses only the reproducible figures.

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
