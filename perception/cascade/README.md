# Cascade experiment — can a cheap gate buy us native-resolution tiling?

## The question

Our pipeline downsamples 2× before tiling, which cuts 48 crops to 12 but puts a
survivor at **~19 px** — TinyPerson's `tiny3` band, the hardest scale the
literature reports. Tiling at native resolution puts them at **~39 px**, outside
that band entirely, but costs 4× the compute.

**The proposal:** pay for native resolution by not running the detector on empty
water. A cheap binary gate looks at every tile and decides which are worth the
expensive pass.

**The question this experiment answers:** can a gate reject enough tiles to make
native tiling cost what downsampled tiling costs today, without dropping
survivors?

## Run it

```bash
python perception/cascade/run_experiment.py            # Stage 0, needs nothing
python perception/cascade/economics.py                 # the decision rule
python -m pytest perception/tests/test_cascade.py -q   # 22 tests, no GPU
```

## The decision rule, fixed before any result

Adopt **only if both hold** on held-out data:

1. **Tile rejection ≥ 80.5%** — below that the cascade costs more than the
   downsampled pipeline it replaces.
2. **Per-target recall ≥ 90%** (SYS-07) with gate failures assumed **fully
   correlated** across the pass.

The second condition is the one that matters. Twelve *independent* looks at 50%
recall find 99.98% of targets; twelve *correlated* looks at 50% find 50%. A
survivor whose appearance the gate reads as water reads as water in every frame
— so fusion rescues nothing, and the failure is invisible from the air and
unrecoverable afterwards. **Report per-target recall, never per-tile.**

## What Stage 0 already told us

The rejection *ceiling* is not the constraint. With 48 tiles per frame and a
target spanning at most two, even three survivors in one frame leaves **87.5%**
of tiles empty, against an 80.5% break-even. There are plenty of empty tiles.

**The open question is whether a gate can find them at recall ≈ 1.0.** That
needs data.

## Two results worth knowing before designing the gate

**Gate cost barely matters.** Break-even moves 75.3% → 80.5% across a 16×
range of gate cost, because the detector dominates so completely. There is
therefore **no reason to cripple the gate's input resolution** to save compute.

That matters because a 128×160 MCU-class gate turns our 39 px target into
**9.7 px** — it would make an unrecoverable decision at the resolution where
published AP is worst. Use a 640-input gate; it costs 5 points of rejection and
sees the target at full size. This is why the cascade runs on the Hailo and
**not** on a microcontroller.

**25% overlap costs +12.5%, not +31%.** The naive `ceil(H/stride)` overcounts,
because the last tile covers a full tile rather than a stride. Correct count is
`ceil((H−tile)/stride)+1`: 48 → 54 tiles. SAHI's 25% recommendation is much
cheaper than it first appears. A test asserts this.

## Data

[SeaDronesSee ODv2](https://github.com/Ben93kie/SeaDronesSee) — 12.7 GB, 14,227
images, COCO JSON, humans in open water with per-frame altitude and gimbal
pitch. Test-set ground truth is withheld, so held-out evaluation must come from
the val split or a re-split of train.

`dataset.py` does two things that make borrowed data mean something:

- **Excludes oblique frames** (>20° off nadir). Our geolocation is near-nadir
  only; a swimmer at 45° shows a body outline, ours shows head and shoulders.
  Keeping them would measure a problem we do not have.
- **Rescales every frame** so its targets are *our* pixel size. Upscaling adds
  no detail, so a gate measured this way can only look worse than it will on our
  optics — the right direction for an error to point.

## Status

| Part | State |
|---|---|
| `geometry.py` — tiling, scale matching, tile labelling | done, tested |
| `economics.py` — break-even, correlated-recall model, decision rule | done, tested |
| `dataset.py` — SeaDronesSee loader and frame selection | done, tested on synthetic COCO |
| `run_experiment.py` Stage 0 — rejection ceiling | done, runs |
| Stage 1 — train the gate, measure recall | **needs the dataset and a GPU** |

Stage 1 is the part that costs a fortnight. Stage 0 costs half an hour and is
what decides whether the fortnight is worth spending — which is why it runs
first and why the decision rule was written before any result existed.
