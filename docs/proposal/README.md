# Funding proposal

`rescueswarm-proposal.tex` — IEEEtran conference format, 7 pages.

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
