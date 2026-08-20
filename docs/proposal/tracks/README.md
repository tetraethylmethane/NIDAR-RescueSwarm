# Track proposals

Four work-package proposals, one per delivery track, each with its own funding
ask. The master proposal (`../rescueswarm-proposal.pdf`) remains the integrated
system document and the thing a competition judge reads; these are what a track
lead is held to.

| Track | Owns | Ask |
|---|---|--:|
| **A — Air vehicle** | Frame, propulsion, power, payload mechanism, assembly | ₹3,25,397 |
| **B — Avionics & comms** | FC, companion computer, GNSS/RTK, mesh, safety link, video | ₹2,80,963 |
| **C — Autonomy & GCS** | Coverage planner, allocation, state machine, ground station, SITL | ₹2,324 |
| **D — Perception** | Detector, tiling, geotagging, calibration, dataset | ₹1,07,295 |
| *Shared* | Safety, statutory, field kit, consumables no single track owns | ₹49,450 |
| | **TOTAL** | **₹7,65,429** |

Track boundaries follow [`development-plan.md`](../../development-plan.md) §1.3.
The shared pool is not a track — it exists because some lines (safety equipment,
DGCA registration, field consumables) genuinely have no single owner, and
forcing them onto a track would misattribute them.

## The invariant

**Nothing here restates a rupee.** Every figure derives from
[`competition_budget.py`](../figures/competition_budget.py) via
[`track_budget.py`](../figures/track_budget.py), and the four track asks plus the
shared pool must equal the master ask *exactly*. That is asserted in code and
[runs in CI](../../../.github/workflows/model-check.yml).

Two guards, both negative-tested:

- A budget line with no track assignment raises `KeyError` rather than being
  silently absorbed into one track.
- A split that stops summing fails the reconciliation assert.

This matters because the failure mode for split budgets is not arithmetic — it
is four documents that each look right and no longer agree.

## Regenerating

```
python docs/proposal/figures/track_budget.py      # the split, with reconciliation
python tools/proposal/build_track_proposals.py    # writes the .tex and builds the PDFs
```

**Do not edit financial figures in the `.tex` files.** They are generated.
Change the master budget and regenerate, or the next run silently reverts you.

## Why Track C's ask is ₹2,324

It is not an error and not a small track. C's deliverables are software, its two
workstations are team-supplied, and its verification environment is
open-source. What remains is a fabricated sun hood and an observer monitor.

C's real cost is student time across the full programme, which a capital
request does not price. A funding split that shows a near-zero line invites the
assumption that the track is minor; it is inexpensive, which is a different
thing, and the schedule has to protect it accordingly.
