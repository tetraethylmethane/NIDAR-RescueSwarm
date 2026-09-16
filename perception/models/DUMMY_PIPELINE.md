# Target-dummy fine-tune pipeline

The last-mile step: adapt the water detector (`finetunev1-3-weights/best.pt`) to the
real competition target — a **human-shaped dummy in muddy floodwater, seen near-nadir**.
No target photos will be shot by hand; the images are **found or AI-generated**. This
doc is the ready-to-run pipeline for whenever ~40–50 target images exist.

## The dataset you need to produce

A YOLO set, single class `person`, ~40–50 images (an 80/20 train/val split is fine):

```
/workspace/data/dummies/
  images/train/*.jpg   images/val/*.jpg
  labels/train/*.txt   labels/val/*.txt     # one line per dummy: "0 cx cy w h" (normalised)
  data.yaml            # path: <root>  train: images/train  val: images/val  nc: 1  names: [person]
```

Then one command trains it:

```bash
python perception/models/finetune_dummies.py \
    --model finetunev1-3-weights/best.pt \
    --data  /workspace/data/dummies/data.yaml \
    --name  dummies-finetune-v1
```

## Route A — AI-generated scenes (text-to-image), then label

1. **Generate ~50 images.** Vary aggressively — altitude, water colour, dummy pose,
   lighting, partial submersion. Prompts that match the target:
   - "top-down aerial drone photo of a human mannequin floating face-up in brown muddy
     floodwater, only head and shoulders above the surface, turbid water, overcast light"
   - "near-nadir view from a drone of a human dummy lying in shallow muddy flood water,
     low contrast, debris around, monsoon lighting"
   - "overhead shot of a life-size rescue dummy half-submerged in turbid brown river
     water, seen from 40 metres, small in frame"
   Push variety: some barely visible, some clearer, different crops/scales.
2. **Reality-check them.** Discard any that look nothing like an overhead flood scene —
   a bad synthetic image teaches a bad prior. Quality over count.
3. **Label them.** For ~50 images this is 20 minutes in any tool — Roboflow (export
   "YOLOv8"), `labelImg`, or CVAT. One box per dummy. Export to the layout above.

**Caveat:** text-to-image dummies are a *prior*, not ground truth. They help the model
expect "human shape in brown water" but can bake in generator artefacts. Keep them a
minority ingredient and lean on the augmented water model underneath.

## Route B — copy-paste synthesis (auto-labelled, more reliable)

Instead of generating whole scenes, paste **person/dummy cut-outs** onto **muddy-water
backgrounds** at random positions and scales — the paste box IS the label, so the set is
labelled for free and perfectly. This needs:
  - a handful of muddy-water background images (AI-gen a few, or crop any flood footage), and
  - person/dummy cut-outs (from SARD/SeaDronesSee crops, or dummy stock).

This is the sturdier route because it is auto-labelled and controllable. A compositor
script is not built yet — ask and it gets written (`seadronessee_to_yolo.py` already has
the tiling half; this adds the paste half).

## Why this works even with only 50 images

`finetune_dummies.py` freezes the backbone and fine-tunes gently, so 50 images move the
detection head toward the muddy-dummy appearance without overwriting the water features
already learned. It is adaptation, not training from scratch — the 44k water tiles did the
heavy lifting; these 50 aim it at the target.
