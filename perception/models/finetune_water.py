#!/usr/bin/env python3
"""Domain-robust fine-tune of the overhead-person detector on water tiles.

WHY. The v1 fine-tune learned SeaDronesSee's BLUE ocean water. The competition
target is a person in BROWN, turbid, low-contrast floodwater. With no target
imagery available, the only defence against that domain gap is augmentation that
DESTROYS the model's reliance on water colour and contrast, forcing it to key on
human SHAPE instead:

  - large HSV hue/value jitter  -> blue ocean becomes indistinguishable from brown
    flood, so colour cannot be a feature the detector leans on;
  - vertical flip (flipud)      -> near-nadir aerial imagery has no intrinsic
    up/down, so this is a free doubling of orientation variety;
  - rotation / mosaic / mixup   -> scene and heading variety, regularisation.

This does not simulate muddy water exactly (a targeted colour transform would be a
stronger follow-up), but it stops the model overfitting to ocean appearance, which
is the failure mode that would sink recall on flood day.

BOX NOTE. `/dev/shm` is locked at 1 GB read-only on the NGC container, so DataLoader
workers Bus-error. `workers=0` (main-process loading) is mandatory here — see
context.md. It is slow (~8 min/epoch) but it is the only thing that runs.

Run (from a general overhead-person baseline, the most transferable start):
  python perception/models/finetune_water.py \
      --model /workspace/NIDAR-RescueSwarm/perception/models/heridal_s_benchmark.pt \
      --data  /workspace/data/train_mix/sds/data.yaml \
      --name  sds-finetune-v2-aug
"""
import argparse

from ultralytics import YOLO


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="baseline checkpoint to fine-tune")
    ap.add_argument("--data", required=True, help="YOLO data.yaml")
    ap.add_argument("--name", default="finetune-v2-aug")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--project", default="/workspace/runs")
    ap.add_argument("--workers", type=int, default=0, help="0 on the box: /dev/shm is 1GB")
    a = ap.parse_args()

    YOLO(a.model).train(
        data=a.data, imgsz=a.imgsz, epochs=a.epochs, batch=a.batch,
        workers=a.workers, device=0, project=a.project, name=a.name,
        patience=15,
        # ---- domain-shift augmentation: break reliance on water colour/contrast ----
        hsv_h=0.10,     # 0.015 default -> 0.10: large hue jitter, blue<->brown
        hsv_s=0.70,     # saturation jitter (turbid vs clear)
        hsv_v=0.50,     # brightness/contrast jitter
        flipud=0.50,    # valid for near-nadir aerial; v1 had this at 0
        fliplr=0.50,
        degrees=10.0,   # arbitrary aerial heading
        translate=0.10, scale=0.50,
        mosaic=1.0, mixup=0.10,
    )


if __name__ == "__main__":
    main()
