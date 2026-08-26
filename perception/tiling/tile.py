"""Big frames -> 640 px tiles. The reason small-object detection is tractable.

WHAT THIS MODULE IS
Cut a YOLO-format corpus of large images into overlapping 640 px tiles, remap
the boxes, and write REAL cropped JPEGs (not symlinks) so the tile corpus is
self-contained and can be zipped into a portable dataset.

WHAT THIS IS NOT
It does not resize a whole frame down to 640 -- that is the mistake this exists
to avoid, since it would shrink a 165 px person to 26 px. It tiles at native
resolution instead.

The box maths lives in `tile_boxes`, which is pure and stdlib-only so the test
can import it without Pillow. Only the file I/O below needs Pillow.

Run:  python perception/tiling/tile.py --src <corpus> --out <tiles> [--neg-ratio 1.0]
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

TILE = 640
OVERLAP = 0.20
STRIDE = int(TILE * (1 - OVERLAP))     # 512

# A box must be at least this visible in a tile to be labelled there. The 20%
# overlap guarantees every target is >=this-visible in at least one tile.
KEEP_VISIBLE = 0.40
# A tile holding a box between these two fractions shows a fragment of a person
# too small to label honestly and too big to ignore -- so the whole tile is
# dropped rather than training on an ambiguous sliver.
SLIVER_LOW = 0.10


def tile_origins(size: int, tile: int = TILE, stride: int = STRIDE) -> list[int]:
    """Left/top edges of tiles covering `size`, last one flush to the far edge."""
    if size <= tile:
        return [0]
    xs = list(range(0, size - tile + 1, stride))
    if xs[-1] != size - tile:
        xs.append(size - tile)
    return xs


def tile_boxes(boxes_norm, img_w, img_h, ox, oy, tile=TILE):
    """Map full-image YOLO boxes into one tile at origin (ox, oy).

    boxes_norm: list of (cx, cy, w, h) normalised to the FULL image.
    Returns (kept, verdict):
      kept    -- list of (cx, cy, w, h) normalised to the TILE
      verdict -- "positive", "negative", or "drop" (ambiguous sliver present)

    This is the whole coordinate-bug surface, so it is pure and tested.
    """
    kept = []
    for cx, cy, w, h in boxes_norm:
        # to absolute pixel corners
        x1, y1 = (cx - w / 2) * img_w, (cy - h / 2) * img_h
        x2, y2 = (cx + w / 2) * img_w, (cy + h / 2) * img_h
        area = (x2 - x1) * (y2 - y1)
        if area <= 0:
            continue

        # intersect with this tile
        ix1, iy1 = max(x1, ox), max(y1, oy)
        ix2, iy2 = min(x2, ox + tile), min(y2, oy + tile)
        iw, ih = ix2 - ix1, iy2 - iy1
        if iw <= 0 or ih <= 0:
            continue

        visible = (iw * ih) / area
        if visible < SLIVER_LOW:
            continue                       # negligible corner, ignore
        if visible < KEEP_VISIBLE:
            return [], "drop"              # ambiguous fragment -> discard tile

        # clip into the tile and renormalise to tile size
        kept.append((
            (ix1 + iw / 2 - ox) / tile,
            (iy1 + ih / 2 - oy) / tile,
            iw / tile,
            ih / tile,
        ))

    return kept, ("positive" if kept else "negative")


def _read_yolo_label(path: Path):
    out = []
    if path.exists():
        for line in path.read_text().split("\n"):
            p = line.split()
            if len(p) == 5:
                out.append(tuple(float(v) for v in p[1:]))
    return out


def run(src: Path, out: Path, neg_ratio: float, seed: int) -> None:
    from PIL import Image                  # only the I/O path needs Pillow

    rng = random.Random(seed)
    for split in ("train", "val", "test"):
        img_dir = src / "images" / split
        if not img_dir.exists():
            continue
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)

        pos = neg = dropped = 0
        neg_tiles = []                     # (img_path, ox, oy) held back for sampling

        for img_path in sorted(img_dir.glob("*")):
            if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            label = src / "labels" / split / f"{img_path.stem}.txt"
            boxes = _read_yolo_label(label)

            try:
                im = Image.open(img_path)
                W, H = im.size
            except Exception:
                continue

            for oy in tile_origins(H):
                for ox in tile_origins(W):
                    kept, verdict = tile_boxes(boxes, W, H, ox, oy)
                    if verdict == "drop":
                        dropped += 1
                        continue
                    if verdict == "negative":
                        neg_tiles.append((img_path, ox, oy))   # decide later
                        continue

                    _write_tile(im, out, split, img_path.stem, ox, oy, kept)
                    pos += 1

        # sample negatives to neg_ratio x positives -- an all-negative corpus of
        # empty terrain would drown the few positives.
        want = int(pos * neg_ratio)
        rng.shuffle(neg_tiles)
        for img_path, ox, oy in neg_tiles[:want]:
            im = Image.open(img_path)
            _write_tile(im, out, split, img_path.stem, ox, oy, [])
            neg += 1

        print(f"  {split:5}: {pos:6} positive  {neg:6} negative  "
              f"({len(neg_tiles)} available, {dropped} dropped as slivers)")

    (out / "data.yaml").write_text(
        f"path: {out.resolve()}\n"
        f"train: images/train\nval: images/val\ntest: images/test\n"
        f"nc: 1\nnames: [person]\n"
    )
    print(f"\n  data.yaml -> {out / 'data.yaml'}")


def _write_tile(im, out: Path, split: str, stem: str, ox: int, oy: int, boxes) -> None:
    name = f"{stem}_{ox}_{oy}"
    im.crop((ox, oy, ox + TILE, oy + TILE)).convert("RGB").save(
        out / "images" / split / f"{name}.jpg", quality=90)
    (out / "labels" / split / f"{name}.txt").write_text(
        "".join(f"0 {a:.6f} {b:.6f} {c:.6f} {d:.6f}\n" for a, b, c, d in boxes))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path, help="YOLO corpus from prep.py")
    ap.add_argument("--out", required=True, type=Path, help="tile output dir")
    ap.add_argument("--neg-ratio", type=float, default=1.0,
                    help="negative tiles per positive tile (default 1.0)")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    print("=" * 78)
    print(f"TILE {TILE}px, {int(OVERLAP*100)}% overlap, stride {STRIDE}")
    print("=" * 78)
    run(a.src, a.out, a.neg_ratio, a.seed)


if __name__ == "__main__":
    main()
