#!/usr/bin/env python3
"""Last-mile fine-tune on target-domain dummy images (found or AI-generated).

This adapts the water detector to the ACTUAL competition target: a human-shaped
dummy in muddy floodwater, near-nadir. It is the step the whole scaffolding was
built to make one command.

With only ~40-50 target images you CANNOT retrain a detector from scratch without
overfitting, so this fine-tunes GENTLY:
  - `freeze=10`  -> freeze the backbone; only the detection head adapts. 50 images
    can move a head, not a backbone.
  - `lr0=0.001`  -> low LR: shift toward the target appearance, do not overwrite the
    water features already learned.
  - heavy augmentation on top, because 50 images is tiny and every one must count.

Start from the water model (`finetunev1-3-weights/best.pt`, in git), NOT the land
baseline — you want the water features kept and only the muddy-dummy appearance added.

Dataset layout (YOLO, single class `person`):
  <root>/images/train  <root>/images/val
  <root>/labels/train  <root>/labels/val
  <root>/data.yaml   (nc: 1, names: [person])

Run:
  python perception/models/finetune_dummies.py \
      --model finetunev1-3-weights/best.pt \
      --data  /workspace/data/dummies/data.yaml \
      --name  dummies-finetune-v1
"""
import argparse

from ultralytics import YOLO


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="water-trained best.pt to adapt")
    ap.add_argument("--data", required=True, help="YOLO data.yaml for the dummy set")
    ap.add_argument("--name", default="dummies-finetune-v1")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--project", default="/workspace/runs")
    a = ap.parse_args()

    YOLO(a.model).train(
        data=a.data, imgsz=640, epochs=a.epochs, batch=16, workers=0, device=0,
        project=a.project, name=a.name, patience=20,
        freeze=10,      # backbone frozen: 40-50 imgs adapt the head only
        lr0=0.001,      # gentle adaptation, keep water features
        hsv_h=0.10, hsv_s=0.70, hsv_v=0.50,
        flipud=0.50, fliplr=0.50, degrees=10.0, translate=0.10, scale=0.50,
        mosaic=1.0,
    )


if __name__ == "__main__":
    main()
