# Questions for the team lead

Internal blockers — things another person on this team has to decide, where
guessing wrong is expensive and asking costs nothing. Separate from
[`requirements/organiser-questions.md`](requirements/organiser-questions.md),
which is for the organisers.

One question open. Two answered — recorded at the end.

---

## Q1 — SYS-46 asks for 2 Hz and 12 looks. On the sensor we are buying, at 40 m, those conflict.

Now that the camera is settled (see the answered section below), the along-track
footprint is narrower than the sizing chapter assumed, so targets cross the frame
faster and multi-frame fusion gets fewer independent observations.

| AGL | Along-track footprint | Dwell | Looks at 2 Hz | Rate needed for 12 | Inference load |
|--:|--:|--:|--:|--:|--:|
| 40 m | 31.4 m | 3.93 s | **7.9** | 3.06 Hz | **37/s** |
| 60 m | 47.1 m | 5.89 s | 11.8 | 2.04 Hz | 24/s |

At 8 m/s ground speed and 12 tiles per frame.

**Question:** at 40 m we are 35 % short of the 12 looks SYS-46 requires. Which
way do we close it?

- **Raise the capture rate to ~3.1 Hz** — costs about half again in inference
  load, 37/s against the 24 the compute was sized for. Published Orin Nano-class
  throughput spans 24–41 FPS, so this puts us near the top of the range with no
  margin for a heat-soaked module.
- **Fly slower** — a lower ground speed lengthens dwell, but costs sweep time
  against the 15-minute allowance.
- **Fly at 60 m** — closes the look count at 2 Hz exactly, but drops the target
  from 82 px to 55 px after downsampling, which moves it from COCO *medium* into
  *small*. Published small-object AP is routinely far below medium AP on the same
  model, so this is a real detection cost, not a rounding one.
- **Relax the look count** — legitimate if 12 was a conservative choice rather
  than a derived one, but it should be an explicit decision.

**Why it matters:** this is the altitude decision, and it is now genuinely
two-sided. Before this it looked like *lower is simply better for detection*.
It is not: lower gives more pixels on target but fewer looks and more compute
load. The recall-versus-target-size curve I am building settles one half of the
trade; the other half is a compute and mission-time budget that is not mine to
spend.

**What would settle it:** a benchmark of the actual model on the actual module,
hot, to find out whether 37 inferences/s is reachable at all. Until then the
answer is a judgement call about which requirement bends.

---

## Answered — recorded so they are not re-raised

### The camera, and its field of view

**Arducam IMX477**, type 1/2.3, 4056 x 3040 on a 1.55 um pitch, 6 mm S-mount
lens. Active area 6.287 x 4.712 mm, so:

**HFOV 55.3 deg, VFOV 42.9 deg, DFOV 66.4 deg.**

Note the earlier "about 65 degrees" was the **diagonal**. Horizontal is 55.3.

This is a different sensor from the one
[`sizing/sizing-calculations.md`](sizing/sizing-calculations.md) §8 assumes
(1/1.8 in, 1.82 um pitch). Same pixel *count*, different pixel *size*, so the
resolution on target is not what that chapter says. Consequences at 40 m:

| | IMX477 | Sizing chapter | Change |
|:--|--:|--:|--:|
| HFOV, deg | 55.3 | 63.2 | -12.5 % |
| GSD, cm/px | 1.03 | 1.21 | -14.8 % |
| Survivor along the long axis, px | 165 | 140 | **+17.4 %** |
| Swath, m | 41.9 | 49.2 | -14.8 % |
| Transects per drone | 7 | 6 | +16.7 % |
| Sweep time per drone, s | 195.8 | 166.9 | +17.3 % |

**We gain 17 % more pixels on target and pay 17 % more sweep time.** Against 250
marks for detection and an 1800 s budget, that trade favours the sensor we are
buying — but the sizing model still needs re-running so the documents stop
disagreeing with the hardware.

The tiling budget is untouched, because tile count depends on pixel count and
that did not change: 12 tiles per frame at 2x downsample, 24 inferences/s.

### Rolling shutter, and the readout time

**Rolling shutter, roughly 25 ms readout at full frame.** At 8 m/s the aircraft
moves **0.20 m** between the first and last row, which is 19 px of skew at 40 m.

- **For detection this is negligible** — a single target spans only a small part
  of the frame height, so the skew *within* one target is about 1.0 px, under the
  blur budget.
- **For geolocation it is not.** A detection's row position carries up to 20 cm of
  along-track bias depending on where in the frame it landed. That is systematic
  error sitting inside a 0.91 m budget, and it does not average out across frames.

**The fix is arithmetic**, and belongs in the geotag rather than in the detector:
effective capture time is `t_frame + (row / image_height) x 25 ms`. Worth
confirming with Platform that the geotag pipeline corrects for readout row; if it
does not, this is a free 20 cm.

Focus is not a concern: hyperfocal distance for this lens is 4.15 m, so
everything from about 2.1 m to infinity is acceptably sharp at our 30-60 m
operating band.
