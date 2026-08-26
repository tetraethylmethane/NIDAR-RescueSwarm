"""Messy public datasets in, one clean YOLO corpus out.

WHAT THIS MODULE IS
Annotation conversion and splitting. Standard library only -- no numpy, no
Pillow -- so it runs anywhere and the perception CI job stays dependency-free.

WHAT THIS IS NOT
It does not tile, train, or resize. Tiling is tile.py, and it reads what this
writes.

The three things here that are not obvious, each of which silently caps recall
if got wrong:

1. An image with NO annotation file is NOT an image with no people in it. HERIDAL
   ships 1684 JPEGs and 1650 XMLs. Treating the 34 orphans as empty labels
   teaches the detector that people are background. They are SKIPPED and counted.

2. HERIDAL's published split is 1546 trainval / 101 test, and every published
   HERIDAL score -- including the ~0.90 P / ~0.89 R we benchmark against -- is
   measured on that exact 101-image test set. We drive off ImageSets/Main rather
   than the directory listing so the split is preserved exactly and the strays
   are excluded for free.

3. HERIDAL's XML puts <object> BEFORE <size> and <filename>, gives <filename>
   with no extension, and orders the box xmin/xmax/ymin/ymax rather than
   xmin/ymin/xmax/ymax. Everything is read by tag name, never by position.

Run:  python perception/datasets/prep.py --src <voc_root> --out <corpus_dir>
"""
from __future__ import annotations

import argparse
import csv
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

# A box smaller than this on either side is an annotation slip, not a person.
MIN_SIDE_PX = 2.0
# A person seen from above is never this elongated. Catches corner-order bugs.
MAX_ASPECT = 12.0


def jpeg_size(path: Path) -> tuple[int, int] | None:
    """Read (width, height) from a JPEG's SOF marker. Header bytes only.

    Exists because 562 of HERIDAL's annotation files are a bare <annotation/>
    with no <size> at all. Stdlib has no image-size reader -- imghdr never
    returned dimensions and is gone in 3.13 -- and pulling in Pillow just to
    read four bytes is not worth it.
    """
    SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    with path.open("rb") as f:
        if f.read(2) != b"\xff\xd8":
            return None
        while True:
            b = f.read(1)
            while b and b != b"\xff":      # scan to the next marker
                b = f.read(1)
            while b == b"\xff":            # markers may be padded with FFs
                b = f.read(1)
            if not b:
                return None
            if b[0] in SOF:
                f.read(3)                  # precision byte + segment length
                h = int.from_bytes(f.read(2), "big")
                w = int.from_bytes(f.read(2), "big")
                return w, h
            seg = int.from_bytes(f.read(2), "big")
            if seg < 2:
                return None
            f.seek(seg - 2, 1)


def parse_voc(xml_path: Path) -> tuple[int, int, list[tuple[float, float, float, float]]]:
    """Return (width, height, [(xmin, ymin, xmax, ymax), ...]) from a VOC file.

    Reads strictly by tag name. HERIDAL's element order is not the VOC norm and
    a positional parser returns plausible nonsense on it.
    """
    root = ET.parse(xml_path).getroot()

    size = root.find("size")
    if size is None:
        w = h = 0                          # caller falls back to the JPEG header
    else:
        w = int(float(size.findtext("width")))
        h = int(float(size.findtext("height")))

    boxes = []
    for obj in root.findall("object"):
        name = (obj.findtext("name") or "").strip().lower()
        if name != "person":
            continue
        bb = obj.find("bndbox")
        if bb is None:
            continue
        boxes.append((
            float(bb.findtext("xmin")), float(bb.findtext("ymin")),
            float(bb.findtext("xmax")), float(bb.findtext("ymax")),
        ))
    return w, h, boxes


def to_yolo(box, w: int, h: int) -> tuple[float, float, float, float] | None:
    """(xmin,ymin,xmax,ymax) pixels -> (cx,cy,bw,bh) normalised, or None if junk.

    Clips to the frame first: a box a few pixels over the edge is a real target
    sloppily labelled, and clipping keeps it. What gets rejected is a box with no
    area, or one so elongated it implies a coordinate bug.
    """
    xmin, ymin, xmax, ymax = box
    if xmax < xmin:
        xmin, xmax = xmax, xmin
    if ymax < ymin:
        ymin, ymax = ymax, ymin

    xmin, xmax = max(0.0, xmin), min(float(w), xmax)
    ymin, ymax = max(0.0, ymin), min(float(h), ymax)

    bw, bh = xmax - xmin, ymax - ymin
    if bw < MIN_SIDE_PX or bh < MIN_SIDE_PX:
        return None
    if max(bw / bh, bh / bw) > MAX_ASPECT:
        return None

    return ((xmin + bw / 2) / w, (ymin + bh / 2) / h, bw / w, bh / h)


def find_image(jpeg_dir: Path, stem: str) -> Path | None:
    for ext in (".jpg", ".JPG", ".jpeg", ".JPEG", ".png"):
        p = jpeg_dir / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def convert_heridal(src: Path, out: Path, keep_stubs: bool = False) -> list[dict]:
    """Walk the official split lists and emit YOLO labels. Returns box rows."""
    jpeg_dir, ann_dir, sets = src / "JPEGImages", src / "Annotations", src / "ImageSets" / "Main"

    # trainval.txt is train.txt + val.txt; take the finer division and keep the
    # 101-image test set completely untouched.
    split_files = {"train": "train.txt", "val": "val.txt", "test": "test.txt"}

    rows, tally = [], Counter()
    for split, fname in split_files.items():
        listing = sets / fname
        if not listing.exists():
            raise SystemExit(f"missing split list: {listing}")

        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
        (out / "images" / split).mkdir(parents=True, exist_ok=True)

        for stem in sorted(listing.read_text().split()):
            img = find_image(jpeg_dir, stem)
            if img is None:
                tally[f"{split}: image missing"] += 1
                continue

            xml = ann_dir / f"{stem}.xml"
            if not xml.exists():
                # NOT an empty label. See module docstring, point 1.
                tally[f"{split}: annotation MISSING (skipped)"] += 1
                continue

            try:
                w, h, boxes = parse_voc(xml)
            except (ET.ParseError, ValueError, TypeError) as e:
                tally[f"{split}: xml unreadable ({type(e).__name__})"] += 1
                continue

            size_missing_stub = (not w or not h)
            if size_missing_stub:
                dims = jpeg_size(img)
                if dims is None:
                    tally[f"{split}: no size in xml OR jpeg header"] += 1
                    continue
                w, h = dims
                tally[f"{split}: size from jpeg header"] += 1

            # A bare <annotation/> carries no size, no filename and no objects.
            # That is a stub, not a confirmed empty frame, so we do not assume it
            # is a negative -- see --keep-stub-negatives.
            if not boxes and not keep_stubs and size_missing_stub:
                tally[f"{split}: empty stub skipped"] += 1
                continue

            kept = []
            for b in boxes:
                y = to_yolo(b, w, h)
                if y is None:
                    tally[f"{split}: box rejected"] += 1
                    continue
                kept.append(y)
                rows.append({
                    "source": "heridal", "group": stem, "split": split,
                    "img_w": w, "img_h": h,
                    "x": round(b[0], 1), "y": round(b[1], 1),
                    "w": round(b[2] - b[0], 1), "h": round(b[3] - b[1], 1),
                    "pose": "",
                })

            # Symlink rather than copy: these are 4000x3000 frames and the corpus
            # would otherwise double the disk for no reason.
            link = out / "images" / split / img.name
            if not link.exists():
                link.symlink_to(img.resolve())

            label = out / "labels" / split / f"{stem}.txt"
            label.write_text("".join(f"0 {a:.6f} {b_:.6f} {c:.6f} {d:.6f}\n"
                                     for a, b_, c, d in kept))

            tally[f"{split}: images"] += 1
            tally[f"{split}: boxes"] += len(kept)
            if not kept:
                tally[f"{split}: negative frames (no boxes)"] += 1

    for k in sorted(tally):
        print(f"  {k:<44} {tally[k]:>6}")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path, help="VOC root (has JPEGImages/)")
    ap.add_argument("--out", required=True, type=Path, help="corpus output dir")
    ap.add_argument("--keep-stub-negatives", action="store_true",
                    help="treat HERIDAL's 562 bare <annotation/> files as confirmed "
                         "empty frames and include them as negatives. Only pass this "
                         "after eyeballing a sample and seeing no people in them.")
    a = ap.parse_args()

    print("=" * 78)
    print("HERIDAL -> YOLO")
    print("=" * 78)
    rows = convert_heridal(a.src, a.out, keep_stubs=a.keep_stub_negatives)

    manifest = a.out / "boxes.csv"
    with manifest.open("w", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=[
            "source", "group", "split", "img_w", "img_h", "x", "y", "w", "h", "pose"])
        wtr.writeheader()
        wtr.writerows(rows)

    (a.out / "data.yaml").write_text(
        f"path: {a.out.resolve()}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"test: images/test\n"
        f"nc: 1\n"
        f"names: [person]\n"
    )

    print(f"\n  {len(rows)} boxes -> {manifest}")
    print(f"  data.yaml -> {a.out / 'data.yaml'}")

    # The split is the whole benchmark. Assert it rather than hope.
    n_test = sum(1 for r in rows if r["split"] == "test")
    print(f"\n  sanity: {n_test} boxes in the frozen 101-image test set")


if __name__ == "__main__":
    main()
