#!/usr/bin/env python3
"""Fetch SeaDronesSee, and refuse to proceed if what arrives cannot answer the question.

WHY THE VERIFY HALF MATTERS MORE THAN THE FETCH HALF. This experiment depends on
two per-image fields that a re-hosted copy has no reason to preserve:

    altitude      -- lets us pick frames near our operating band
    gimbal pitch  -- lets us EXCLUDE oblique frames

Our geolocation is near-nadir only. A swimmer photographed at 45 degrees shows a
body outline; ours shows head and shoulders. If the gimbal field is missing we
cannot tell the two apart, every oblique frame silently enters the training set,
and the measured recall belongs to an easier problem than the one we fly. The
result would look good and mean nothing.

Third-party mirrors are frequently format conversions -- COCO flattened to YOLO
text files, metadata dropped as unused. So this script checks for the fields
rather than assuming them, and says plainly whether Stage 1 can run.

HONESTY NOTE. The download path has NOT been executed by its author: it needs
Kaggle credentials and 12.7 GB. The verification path is exercised by tests
against synthetic COCO. Treat the fetch as a convenience and the verify as the
part to trust.

    python -m perception.cascade.fetch_data --dest data/seadronessee
    python -m perception.cascade.fetch_data --verify-only --dest data/seadronessee
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    from perception.cascade import dataset as D
else:
    from . import dataset as D

KAGGLE_SLUG = "ubiratanfilho/sds-dataset"
OFFICIAL = "https://seadronessee.cs.uni-tuebingen.de/dataset"

# Published split sizes, for a sanity check against a truncated download.
EXPECTED = {"train": 8930, "val": 1547, "test": 3750}
# Fraction of images that must carry usable gimbal metadata for the oblique
# filter to mean anything. Below this the filter is cosmetic.
MIN_META_COVERAGE = 0.50


def _find_annotations(root: str) -> list[str]:
    hits = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".json") and "annot" in (dirpath + fn).lower() \
                    or fn.startswith("instances"):
                hits.append(os.path.join(dirpath, fn))
    return sorted(hits)


def fetch(dest: str) -> None:
    if shutil.which("kaggle") is None:
        raise SystemExit(
            "The kaggle CLI is not on PATH.\n"
            "  pip install kaggle\n"
            "  then put an API token at ~/.kaggle/kaggle.json "
            "(Kaggle > Account > Create New API Token)\n"
            f"Or download manually from {OFFICIAL} and re-run with --verify-only.")
    os.makedirs(dest, exist_ok=True)
    print(f"  downloading {KAGGLE_SLUG} -> {dest}  (12.7 GB, this takes a while)")
    r = subprocess.run(["kaggle", "datasets", "download", "-d", KAGGLE_SLUG,
                        "-p", dest, "--unzip"])
    if r.returncode != 0:
        raise SystemExit(
            f"kaggle download failed (exit {r.returncode}).\n"
            f"The mirror may have moved. The authoritative source is {OFFICIAL} "
            "-- download there and re-run with --verify-only.")


def verify(dest: str) -> bool:
    """Report on what is present. Returns True only if Stage 1 can proceed."""
    ok = True
    if not os.path.isdir(dest):
        print(f"  FAIL  {dest} does not exist")
        return False

    anns = _find_annotations(dest)
    print(f"  annotation files found: {len(anns)}")
    for a in anns[:10]:
        print(f"    {os.path.relpath(a, dest)}")
    if not anns:
        print("  FAIL  no COCO json found. A YOLO-format mirror cannot be used:")
        print("        the per-image altitude and gimbal fields do not survive")
        print("        that conversion, and the oblique filter depends on them.")
        return False

    for ann in anns:
        print(f"\n  --- {os.path.relpath(ann, dest)}")
        try:
            with open(ann, encoding="utf-8") as fh:
                coco = json.load(fh)
        except Exception as exc:                       # noqa: BLE001
            print(f"    FAIL  will not parse: {exc}")
            ok = False
            continue

        imgs = coco.get("images", [])
        cats = [c.get("name") for c in coco.get("categories", [])]
        print(f"    images {len(imgs):,}   annotations "
              f"{len(coco.get('annotations', [])):,}")
        print(f"    categories: {cats}")

        person = [c for c in cats
                  if any(h in (c or "").lower() for h in D.PERSON_CATEGORY_HINTS)]
        if not person:
            print("    FAIL  no person-like category. Update "
                  "PERSON_CATEGORY_HINTS in dataset.py to the real name.")
            ok = False
        else:
            print(f"    person-like category: {person}")

        metas = [i.get("meta", i) for i in imgs]
        n_alt = sum(1 for m in metas if m.get("altitude") is not None)
        n_pitch = sum(1 for m in metas if D._raw_pitch(m) is not None)
        cov = n_pitch / len(imgs) if imgs else 0.0
        conv = D.infer_pitch_convention(metas)
        print(f"    altitude present     {n_alt:,}/{len(imgs):,}")
        print(f"    gimbal pitch present {n_pitch:,}/{len(imgs):,}  ({cov:.0%})")
        print(f"    pitch convention     {conv}")

        if cov < MIN_META_COVERAGE or conv == "unknown":
            print("    FAIL  without gimbal pitch we cannot exclude oblique")
            print("          frames, and the measured recall would belong to an")
            print("          easier problem than the one we fly.")
            ok = False

        for split, n in EXPECTED.items():
            if split in os.path.basename(ann).lower() and imgs and len(imgs) != n:
                print(f"    WARN  expected {n:,} images for '{split}', found "
                      f"{len(imgs):,} -- truncated download or a different release")

    print()
    if ok:
        print("  READY. Stage 1 can proceed:")
        print("    python perception/cascade/run_experiment.py --ann <the train json>")
    else:
        print("  NOT READY. Fix the failures above before spending GPU time.")
    return ok


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", default="data/seadronessee")
    ap.add_argument("--verify-only", action="store_true",
                    help="skip the download; check what is already on disk")
    args = ap.parse_args()

    if not args.verify_only:
        fetch(args.dest)
    sys.exit(0 if verify(args.dest) else 1)


if __name__ == "__main__":
    main()
