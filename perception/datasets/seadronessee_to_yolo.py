#!/usr/bin/env python3
"""SeaDronesSee (COCO) -> YOLO detector tiles: a person-in-water training set.

WHY THIS EXISTS. The detector is trained on HERIDAL + SARD, which are people on
LAND, mostly full body and high contrast. The competition target is a person in
floodwater -- head and shoulders, low contrast, seen from above. SeaDronesSee is
the closest public match (people in open water from a UAV), so tiling its
`swimmer` class into the same 640 px YOLO format the land sets use lets the
detector learn the water appearance it has never seen.

WHAT IT DOES. Reads a COCO split, tiles every frame at NATIVE resolution
(640 px, 20 % overlap -- no rescale, so the detector sees targets at their true
size exactly as the HERIDAL tiler does), remaps the swimmer boxes into each
tile, writes real cropped JPEGs + YOLO labels, and samples a few empty tiles per
frame as negatives for false-alarm suppression.

WHAT IT IS NOT. This is the DETECTOR pipeline, not the cascade gate. It does not
rescale to our pixel size and does not apply the near-nadir filter -- more water
imagery at more angles is better training for a detector, and the mission-size
question is answered separately by the recall-vs-size curve.

Run:
  python -m perception.datasets.seadronessee_to_yolo \
      --coco-root /workspace/data/seadronessee --out /workspace/data/sds_yolo
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

# Always import the shared code by absolute path, so this runs the same whether
# invoked as a module or a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from perception.cascade import dataset as D  # noqa: E402
from perception.cascade import geometry as G  # noqa: E402

TILE = 640
OVERLAP = 0.20


def _write(im, t, boxes, img_out: Path, lbl_out: Path, stem: str) -> None:
    """Crop one tile and write its image + YOLO label file."""
    name = f"{stem}_{t.x0}_{t.y0}"
    im.crop((t.x0, t.y0, t.x1, t.y1)).save(img_out / f"{name}.jpg", quality=90)
    lines = []
    for (x0, y0, x1, y1) in boxes:
        # clip the box to the tile, then normalise to the tile
        cx0, cy0 = max(x0, t.x0), max(y0, t.y0)
        cx1, cy1 = min(x1, t.x1), min(y1, t.y1)
        bw, bh = cx1 - cx0, cy1 - cy0
        if bw <= 1 or bh <= 1:
            continue
        ncx = (cx0 + cx1) / 2 - t.x0
        ncy = (cy0 + cy1) / 2 - t.y0
        lines.append(f"0 {ncx / TILE:.6f} {ncy / TILE:.6f} "
                     f"{bw / TILE:.6f} {bh / TILE:.6f}")
    (lbl_out / f"{name}.txt").write_text("".join(s + "\n" for s in lines))


def tile_split(coco_root: Path, out: Path, split: str, neg_ratio: float,
               seed: int) -> tuple[int, int]:
    """Tile one COCO split into YOLO tiles. Returns (positives, negatives)."""
    from PIL import Image

    rng = random.Random(seed)
    ann = coco_root / "annotations" / f"instances_{split}.json"
    images_dir = coco_root / "images" / split
    frames = D.load_split(str(ann))

    img_out = out / "images" / split
    lbl_out = out / "labels" / split
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)

    pos = neg = 0
    total = len(frames)
    for done, f in enumerate(frames, 1):
        if done % 50 == 0 or done == total:
            print(f"    {split}: {done}/{total} frames, {pos} pos / {neg} neg tiles",
                  file=sys.stderr, flush=True)
        if not f.boxes or f.width < TILE or f.height < TILE:
            continue
        path = images_dir / f.file_name
        if not path.exists():
            continue

        tiles = G.tile_grid(f.width, f.height, TILE, OVERLAP)
        per_tile: dict[int, list] = defaultdict(list)
        for box in f.boxes:
            for ti in G.tiles_for_box(tiles, box):
                per_tile[ti].append(box)

        pos_idx = [i for i in range(len(tiles)) if per_tile.get(i)]
        if not pos_idx:                    # every box was a boundary sliver
            continue
        neg_idx = [i for i in range(len(tiles)) if not per_tile.get(i)]

        im = Image.open(path).convert("RGB")   # one NFS read per frame
        stem = Path(f.file_name).stem
        for ti in pos_idx:
            _write(im, tiles[ti], per_tile[ti], img_out, lbl_out, stem)
            pos += 1
        rng.shuffle(neg_idx)
        for ti in neg_idx[:int(round(len(pos_idx) * neg_ratio))]:
            _write(im, tiles[ti], [], img_out, lbl_out, stem)
            neg += 1

    return pos, neg


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coco-root", required=True, type=Path,
                    help="dir with annotations/ and images/{train,val}/")
    ap.add_argument("--out", required=True, type=Path, help="YOLO tile output dir")
    ap.add_argument("--neg-ratio", type=float, default=0.5,
                    help="empty tiles per positive tile (default 0.5)")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    print("=" * 78)
    print(f"SeaDronesSee -> YOLO tiles  ({TILE}px, {int(OVERLAP * 100)}% overlap, "
          f"native resolution)")
    print("=" * 78)
    grand_pos = grand_neg = 0
    for split in ("train", "val"):
        p, n = tile_split(a.coco_root, a.out, split, a.neg_ratio, a.seed)
        print(f"  {split:5}: {p:6} positive  {n:6} negative")
        grand_pos += p
        grand_neg += n

    (a.out / "data.yaml").write_text(
        f"path: {a.out.resolve()}\n"
        f"train: images/train\nval: images/val\n"
        f"nc: 1\nnames: [person]\n"
    )
    print(f"\n  {grand_pos} positive + {grand_neg} negative tiles")
    print(f"  data.yaml -> {a.out / 'data.yaml'}")


if __name__ == "__main__":
    main()
