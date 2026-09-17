# Detector training — how the flood-dummy detector was built

The competition target is a **human-looking dummy in Indian floodwater, seen
near-nadir from a drone** — head-and-shoulders, low contrast, muddy brown water.
No imagery of the real target exists (it appears only at the September field
campaign, which did not happen in time). So the detector was built as a **three-stage
chain of fine-tunes**, each stage moving the model closer to that target using the
best proxy data available at that step, and each backed up in git.

```
HERIDAL land model  ──►  v1 water  ──►  v2 colour-robust  ──►  v3 muddy-dummy
(overhead person)       (SeaDronesSee)   (heavy aug)          (AI-gen dummies)
```

| Model | Weights | Trained from | On | Held-out result |
|---|---|---|---|---|
| **v1** | `finetunev1-3-weights/best.pt` | HERIDAL land baseline | SeaDronesSee water tiles | R 0.872 · mAP50 0.854 (SDS val) |
| **v2** | `finetunev2-aug-weights/best.pt` | v1 | SeaDronesSee + heavy augmentation | R 0.873 · mAP50 0.871 (SDS val) |
| **v3** | `finetunev3-dummies/best.pt` | v2 | 196 AI-generated muddy-dummy images | R 1.0 · mAP50 0.995 (synthetic test) |

**v3 is the default detector; keep v2 as the conservative fallback.**

> **Read the caveats section before quoting any number.** v3's ~1.0 is measured on
> synthetic data drawn from the same generator it trained on — it is **not** real
> competition recall.

---

## Stage 1 — v1: adapt an overhead-person model to water

**Why.** `heridal_s_benchmark.pt` is a YOLO11s already trained on HERIDAL (people
seen from above, on land). The mission is people *in water*, so fine-tune it on the
closest public match: **SeaDronesSee** (people in open water from a UAV).

**Data.** SeaDronesSee Object Detection v2 (Compressed Version, 9.3 GB) →
`perception/datasets/seadronessee_to_yolo.py` tiles it to 640 px, 20 % overlap,
native resolution (the `swimmer` class → `person`):

| split | positive tiles | negative tiles |
|---|--:|--:|
| train | 25,883 | 11,347 |
| val | 4,639 | 2,120 |

**Command.**
```bash
yolo detect train data=/workspace/data/train_mix/sds/data.yaml \
  model=perception/models/heridal_s_benchmark.pt \
  imgsz=640 epochs=60 patience=15 batch=64 workers=0 device=0 \
  project=/workspace/runs name=sds-finetune-v1
```

**Result** (SeaDronesSee val, 6,759 images / 9,609 swimmers): **P 0.861 · R 0.872 ·
mAP50 0.854 · mAP50-95 0.439.** 60 epochs, ~8 h. Recall on people-in-water beats the
land baselines (HERIDAL 0.774, HERIDAL+SARD 0.818).

---

## Stage 2 — v2: make it colour-invariant (the muddy-water hedge)

**Why.** v1 learned SeaDronesSee's **blue ocean** water. The target is **brown,
turbid flood** water. With no target imagery, the defence against that colour gap is
augmentation that *scrambles water colour every epoch* so the model stops relying on
it and keys on human **shape** instead. This is not "recolour to mud" — it is
"make water colour unreliable, so a colour it has never seen still works."

**Command** ([`finetune_water.py`](finetune_water.py)):
```bash
python perception/models/finetune_water.py \
  --model finetunev1-3-weights/best.pt \
  --data /workspace/data/train_mix/sds/data.yaml --name sds-finetune-v2-aug
```
Key augmentation: `hsv_h=0.10` (large hue jitter, blue↔brown), `hsv_s=0.70`,
`hsv_v=0.50`, `flipud=0.50` (valid for near-nadir aerial), `degrees=10`, `mosaic=1.0`,
`mixup=0.10`. `workers=0`, `batch=64`.

**Result** (SeaDronesSee val): **P 0.866 · R 0.873 · mAP50 0.871 · mAP50-95 0.445.**
53 epochs (early-stopped, best at 38), ~7.7 h. The augmentation acted as free
regularisation — it **held recall and improved mAP50** over v1 while adding colour
robustness whose flood-water payoff is unmeasurable until real targets exist.

---

## Stage 3 — v3: adapt to the actual target (muddy dummies)

**Why.** v2 still detects only ~60 % of muddy dummies (measured by running it on the
generated set) and mis-boxes debris — a large domain gap. So fine-tune it on images
of the real target.

**Data — AI-generated, since no real dummies exist.** ~200 images generated with
**FLUX.1-dev** (`diffusers`, on the box), then labelled. Generation details:
- **FLUX.1-schnell was too low-fidelity** (CGI/oblique). **FLUX.1-dev at 50 steps,
  `guidance_scale=3.5`** gave usable photorealistic near-nadir dummies.
- Prompt forces true top-down, small scale, inert dummy, flat light, photographic
  (not render) — full prompt + variety axes in [`DUMMY_PIPELINE.md`](DUMMY_PIPELINE.md).
- **Labelling:** on-box tools failed (Jupyter widget needs a server restart; a custom
  HTML labeler hit Jupyter's 403 origin block on writes) → fell back to **Roboflow**
  (upload → box each dummy → export YOLOv8). 196 images labelled: 157 train / 19 val /
  20 test.

**Command** ([`finetune_dummies.py`](finetune_dummies.py)):
```bash
python perception/models/finetune_dummies.py \
  --model finetunev2-aug-weights/best.pt \
  --data /workspace/data/dummies/data.yaml --name dummies-v3
```
Gentle, small-set adaptation: `freeze=10` (backbone frozen — 196 images can move a
head, not a backbone, without overfitting), `lr0=0.001`, `batch=16`, `workers=0`,
plus the same augmentation.

**Result** (held-out **synthetic** splits):
- val (19 imgs): P 1.00 · R 0.999 · mAP50 0.995 · mAP50-95 0.878
- test (20 imgs): P 0.996 · R 1.00 · mAP50 0.995 · mAP50-95 0.875

Consistent across both → the muddy-dummy appearance was **learned, not memorised**.
58 epochs (early-stopped, best at 38), ~2 min.

---

## Caveats — what these numbers do and do not mean

- **v3's ~1.0 is synthetic-trained and synthetic-tested** (same FLUX generator for
  train and val/test). It measures generalisation *within the synthetic distribution*,
  **not recall on real competition dummies.** Do not report it as the competition
  number. The synthetic→real transfer is unmeasured.
- **v1/v2 numbers are on SeaDronesSee (ocean), not the frozen HERIDAL land test**, so
  they are not comparable to HERIDAL's published ~0.90, and land performance may have
  drifted (no land imagery in the fine-tunes).
- Detection is worth **250 of 600** competition points; recall (not precision) is the
  scored quantity, since a missed survivor is far costlier than a false alarm.

## Reproducing / extending

- Tiling: `python -m perception.datasets.seadronessee_to_yolo --coco-root <sds> --out <dir>`
- Generation: `/workspace/gen_dummies.py` (FLUX.1-dev via `diffusers`), prompt in `DUMMY_PIPELINE.md`.
- **When real dummy imagery exists**, it is one command to adapt v3 to it:
  ```bash
  python perception/models/finetune_dummies.py \
    --model finetunev3-dummies/best.pt --data <real_dummies>/data.yaml --name dummies-real
  ```

## Environment gotchas (NGC PyTorch container on the H100 MIG slice)

- **`/dev/shm` is locked at 1 GB, read-only** → DataLoader workers `Bus error`. The
  fix that works is **`workers=0`** (main-process loading). Slow but reliable.
- **Do not reinstall torch** (NGC's build is H100-tuned). `pip install ultralytics`
  bumps numpy to 2.x and pulls opencv 5.x, both of which break NGC torch 2.4 — re-pin
  `numpy==1.24.4 opencv-python==4.7.0.72` afterward.
- **`diffusers` must be pinned to `0.30.3`** for FLUX on torch 2.4 (newer diffusers
  needs `torch.nn.attention.flex_attention`, which only exists in torch 2.5+).
