# geotagging

**Pixel to lat/lon. This gates 450 of the 600 flight points.**

Detection and geotagging are one scored item worth 250 (SYS-07, SYS-12), and
delivery accuracy is a further 200 aimed *using* the geotag. The difference
between doing this naively and doing it properly is about **102 points**:

| case | geotag | pts/drop | 10 drops |
|:--|--:|--:|--:|
| A — no RTK, single frame | 3.09 m | 7.5 | 75 |
| B — RTK, single frame | 1.36 m | 15.7 | 157 |
| C — RTK + fusion + calibrated | 1.00 m | 17.7 | **177** |

**None of that gap is recoverable by a better detector.**

## What is here

`geotag.py` — pure geometry. No I/O, no camera, no autopilot.

```python
tag = project(detection, pose, camera)       # -> lat, lon, fix, sigma
tracker.add(tag)                             # cluster + inverse-variance fuse
tracker.confirmed()                          # survivors seen >= 3 times
```

- **`project()`** — pixel → camera ray → body → NED → intersect the ground
  plane → lat/lon. Enforces the **SYS-33 20° off-nadir gate** by refusing the
  detection rather than tagging it badly: a bad tag still consumes a delivery,
  so it is worth less than no tag.
- **`sigma_for()`** — 1σ horizontal for fusion weighting and the operator's
  display. Floored by the systematic terms (0.70 unmodelled, 0.50 target
  extent, 0.16 boresight, 0.10 lever arm) because **multi-frame fusion cannot
  average those away**.
- **`SurvivorTracker`** — the B → C step, worth ~20 points per drop.
  Inverse-variance weighted, and the reported fix is the **best ever seen**,
  not the latest — a later `RTK_FLOAT` tag is metres worse than an earlier
  `RTK_FIXED` one, and the ground station ranks on fix quality for the same
  reason.

## What is NOT here

- **Calibration (SYS-48).** Boresight and lever arm must be measured before any
  accuracy claim is valid. The mount tolerance that makes it hold is
  [`boresight_budget.py`](../../tools/sizing-model/boresight_budget.py):
  **0.21 mm over an 80 mm fastener spacing, for life.**
- **The detector.** Owned separately — see
  [`perception-integration-plan.md`](../../docs/perception-integration-plan.md)
  for the `Detection` contract this consumes.
- **Terrain.** The ground is a plane at `pose.agl_m`. On a flood plain that is
  reasonable; it is an assumption, not a fact.

## The thing most likely to be got wrong

**`t_capture` must be the camera exposure time, not when the frame arrived.**
At 8 m/s a 100 ms timestamp error is **0.8 m** on the ground — comparable to the
entire 0.91 m budget. Pose is interpolated to that instant, and nothing
downstream can recover a wrong one.

## Tests

```
cd perception && python -m pytest tests -q      # 17 tests
```

A projection bug does not crash — it puts the survivor somewhere plausible and
wrong. So every test has a hand-computable answer, and the suite was
**falsified against three injected bugs**: swapped camera axes, flipped east
sign, and yaw ignored. It caught all three (5, 3 and 1 failures respectively).

Next step for verification: score `project()` against **Gazebo ground truth**.
The simulator knows the true position of every object, so the geotag can be
checked to centimetres automatically — see
[`gz-flight.sh`](https://github.com/tetraethylmethane/NIDAR-GSC/blob/main/scripts/gz-flight.sh).
