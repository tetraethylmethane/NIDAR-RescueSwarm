# autonomy

Mission logic. Per [`../docs/implementation-plan.md`](../docs/implementation-plan.md),
deliberately much simpler than the original plan: **ArduPilot flies the search**,
so there is no coverage-execution or path-following code at all.

## Built

### `coverage_planner/` — boundary in, ArduPilot missions out

Runs on the GCS during the 5-minute setup window (SYS-38). Pure geometry, no I/O,
~2 ms per plan.

| Module | Does |
|---|---|
| `geo.py` | Local metric frame, area, centroid, principal axis, half-plane clipping |
| `partition.py` | Equal-area strips across the long axis (§1.3 — not DARP) |
| `boustrophedon.py` | Transects at swath × (1 − sidelap), alternating direction |
| `mission.py` | QGC WPL 110 ArduPilot missions, with a pre-upload validator |
| `plan.py` | End-to-end: boundary → strips → transects → one mission per drone |

```bash
cd autonomy && python -m pytest tests -q      # 31 tests
```

**10 ha, 3 drones, 40 m:** 3.33 ha each, 0.01 % imbalance, 3 lines each,
169 s sweep. **2 drones:** 5.00 ha each, 230 s — still far inside the 15 min
fast-completion threshold, which is what makes the two-aircraft fallback real.

### Two decisions worth knowing

**Cut across the short axis.** Transect count is strip width ÷ line spacing,
measured perpendicular to the transects, so long thin strips mean fewer turns.
For 400 × 250 m and 3 drones that is 3 transects each instead of 4.

**Search altitude is *not* stratified.** An earlier version staggered it
40/45/50 m for deconfliction, and the planner's own output exposed the problem:
swath scales with altitude, so the highest drone covered its strip in fewer
lines *because its GSD was coarser* — 112 px on a survivor against 140 px, over
a third of the search area, for separation the strips already provide. Detection
is 250 points. Search altitude is now uniform; **transit** altitude is staggered,
since that is where aircraft leave their strips.

## Not built

`mission_state`, `swarm_state` (greedy claim-and-lock), `delivery` (the GUIDED
excursion), `mission_publisher` (the 5 Hz feed the GCS already consumes), and the
ArduPilot parameter file that provides four of the five failsafes. See the
implementation plan, Part 2.
