#!/usr/bin/env python3
"""Turn SeaDronesSee into tiles that stand in for what our aircraft will see.

WHY BORROWED DATA NEEDS WORK BEFORE IT MEANS ANYTHING. SeaDronesSee is humans
in open water shot from 5-260 m across 0-90 degrees of viewing angle. Our
aircraft flies one altitude band, near-nadir, on a different sensor. Handing the
raw dataset to a gate and reporting the recall would measure a detector on a
problem we do not have, and would flatter it in two specific ways:

  1. OBLIQUE FRAMES ARE EASIER. A swimmer seen from 45 degrees shows a body
     outline. From directly overhead they are a head and shoulders. Our
     geolocation pipeline is near-nadir only, so oblique frames must be
     excluded or the measured recall is not ours to claim.

  2. LOW-ALTITUDE FRAMES ARE EASIER. A target at 5 m is hundreds of pixels
     across. Ours is about 39. Pixels on target -- not metres, not altitude --
     is what a detector responds to, so every frame is rescaled until its
     targets are OUR size.

Rescaling upward does not invent detail. It makes the target occupy our pixel
count while carrying the source frame's real resolution, so a gate measured this
way can only look WORSE than it will on our optics, never better. That is the
right direction for an error to point.

WHAT THIS MODULE DOES NOT DO. It does not train anything and imports no deep
learning framework. It reads COCO JSON, selects usable frames, and emits tile
crops with labels. Keeping it framework-free means the selection logic can be
reviewed and tested without a GPU in the room.

Run:  python -m perception.cascade.dataset --root /path/to/seadronessee
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field

from . import geometry as G

# Our operating point, from tools/sizing-model/camera_optics.py.
OUR_PITCH_UM, OUR_F_MM = 1.55, 6.0
OUR_ALT_M = 40.0
# Head-and-shoulders in water, which is the worst posture and therefore the one
# the design must be sized against. A supine adult on a rooftop is easier.
OUR_TARGET_M = 0.40

# Near-nadir only. Our ray-ground intersection assumes it and the geolocation
# budget's 0.62 m height term depends on it.
MAX_OFF_NADIR_DEG = 20.0
# Below this the source frame carries too little real detail to be rescaled up
# to our size without the result being mostly interpolation.
MIN_SOURCE_TARGET_PX = 12.0

PERSON_CATEGORY_HINTS = ("swimmer", "person", "human", "floater")


@dataclass
class Frame:
    """One usable source image, with what we need to rescale and tile it."""
    image_id: int
    file_name: str
    width: int
    height: int
    altitude_m: float | None
    off_nadir_deg: float | None
    boxes: list[tuple[float, float, float, float]] = field(default_factory=list)

    @property
    def median_target_px(self) -> float:
        if not self.boxes:
            return 0.0
        longs = sorted(max(x1 - x0, y1 - y0) for x0, y0, x1, y1 in self.boxes)
        return longs[len(longs) // 2]


# SeaDronesSee writes these in the DJI flight-log style, with the unit in the
# key name. The bare forms are kept as fallbacks for any re-hosted copy that
# normalised them.
PITCH_KEYS = ("gimbal_pitch(degrees)", "gimbal_pitch", "gimbal_pitch_deg", "pitch")
ALTITUDE_KEYS = ("height_above_takeoff(meter)", "altitude")


def _altitude(meta: dict) -> float | None:
    for key in ALTITUDE_KEYS:
        if meta.get(key) is not None:
            return float(meta[key])
    return None


def _raw_pitch(meta: dict) -> float | None:
    for key in PITCH_KEYS:
        if meta.get(key) is not None:
            return float(meta[key])
    return None


def infer_pitch_convention(metas) -> str:
    """Which way the dataset writes gimbal pitch: 'nadir_at_-90' or 'nadir_at_0'.

    This MUST be decided once for the whole split, not per value. The two
    conventions overlap across [-90, 0], so a lone -45 is ambiguous -- it is
    45 degrees off nadir under one convention and meaningless under the other.
    Deciding per value silently mislabels every oblique frame as "no metadata",
    which quietly deletes the hard examples and flatters the result.
    """
    vals = [p for p in (_raw_pitch(m) for m in metas) if p is not None]
    if not vals:
        return "unknown"
    return "nadir_at_-90" if min(vals) < -45.0 else "nadir_at_0"


def _off_nadir(meta: dict, convention: str = "nadir_at_-90") -> float | None:
    """Degrees away from straight down, under a convention fixed by the caller."""
    p = _raw_pitch(meta)
    if p is None or convention == "unknown":
        return None
    if convention == "nadir_at_-90":
        return abs(p + 90.0)
    return abs(p)


def _person_category_ids(coco: dict) -> set[int]:
    ids = {c["id"] for c in coco.get("categories", [])
           if any(h in c.get("name", "").lower() for h in PERSON_CATEGORY_HINTS)}
    if not ids:
        names = [c.get("name") for c in coco.get("categories", [])]
        raise SystemExit(
            "No person-like category found. Categories present: "
            f"{names}\nEdit PERSON_CATEGORY_HINTS once you can see the real names.")
    return ids


def load_split(ann_path: str) -> list[Frame]:
    """Read one COCO split and keep only frames this experiment can use."""
    with open(ann_path, encoding="utf-8") as fh:
        coco = json.load(fh)
    person_ids = _person_category_ids(coco)

    by_image = defaultdict(list)
    for a in coco.get("annotations", []):
        if a.get("category_id") in person_ids and not a.get("iscrowd", 0):
            x, y, w, h = a["bbox"]                      # COCO: x, y, w, h
            if w > 0 and h > 0:
                by_image[a["image_id"]].append((x, y, x + w, y + h))

    # SeaDronesSee carries per-image metadata under "meta", but writes it as an
    # explicit null on frames that have none (2,718 of 8,930 in train). A missing
    # OR null meta must become an empty dict, not the image record itself -- the
    # image record has no pitch key, so falling back to it would only hide the
    # gap. These frames then drop out cleanly in select() as "no usable gimbal".
    metas = [img.get("meta") or {} for img in coco.get("images", [])]
    convention = infer_pitch_convention(metas)

    frames = []
    for img, meta in zip(coco.get("images", []), metas):
        frames.append(Frame(
            image_id=img["id"], file_name=img["file_name"],
            width=img["width"], height=img["height"],
            altitude_m=_altitude(meta),
            off_nadir_deg=_off_nadir(meta, convention),
            boxes=by_image.get(img["id"], []),
        ))
    return frames


def select(frames: list[Frame]) -> tuple[list[Frame], dict]:
    """Keep frames that can honestly stand in for ours, and say what was cut."""
    kept, reasons = [], defaultdict(int)
    for f in frames:
        if not f.boxes:
            reasons["no annotated person"] += 1
            continue
        if f.off_nadir_deg is None:
            reasons["no usable gimbal metadata"] += 1
            continue
        if f.off_nadir_deg > MAX_OFF_NADIR_DEG:
            reasons[f"oblique (>{MAX_OFF_NADIR_DEG:.0f} deg off nadir)"] += 1
            continue
        if f.median_target_px < MIN_SOURCE_TARGET_PX:
            reasons[f"target under {MIN_SOURCE_TARGET_PX:.0f} px in source"] += 1
            continue
        kept.append(f)
    return kept, dict(reasons)


def plan_tiles(frame: Frame, wanted_px: float, tile: int = 640,
               overlap: float = 0.20) -> dict:
    """Rescale one frame to our target size and work out its tiles and labels.

    Returns the geometry only -- no pixels are touched here, so this is testable
    and reviewable without the images present.
    """
    scale = G.scale_to_match(frame.median_target_px, wanted_px)
    W, H = int(round(frame.width * scale)), int(round(frame.height * scale))
    if W < tile or H < tile:
        return {"usable": False, "reason": "rescaled frame smaller than one tile"}

    tiles = G.tile_grid(W, H, tile, overlap)
    boxes = [(x0 * scale, y0 * scale, x1 * scale, y1 * scale)
             for x0, y0, x1, y1 in frame.boxes]

    positive, orphaned = set(), 0
    per_target = []
    for b in boxes:
        idx = G.tiles_for_box(tiles, b)
        per_target.append(idx)
        if not idx:
            orphaned += 1            # sliced by every tile: a geometry failure
        positive.update(idx)

    return {
        "usable": True, "scale": scale, "width": W, "height": H,
        "n_tiles": len(tiles), "positive_tiles": sorted(positive),
        "n_positive": len(positive),
        "n_negative": len(tiles) - len(positive),
        "targets": per_target, "orphaned_targets": orphaned,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ann", required=True, help="COCO json for one split")
    ap.add_argument("--target-px", type=float, default=None,
                    help="default: our own target size at 40 m")
    args = ap.parse_args()

    wanted = args.target_px or G.target_px(OUR_TARGET_M, OUR_ALT_M,
                                           OUR_PITCH_UM, OUR_F_MM)
    frames = load_split(args.ann)
    kept, reasons = select(frames)

    print(f"  frames read          {len(frames)}")
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"    dropped {n:>6}  {why}")
    print(f"  frames usable        {len(kept)}")
    print(f"  rescaling so targets are {wanted:.1f} px "
          f"(our 0.40 m target at {OUR_ALT_M:.0f} m)")

    tot_t = tot_p = tot_orph = 0
    unusable = 0
    for f in kept:
        p = plan_tiles(f, wanted)
        if not p["usable"]:
            unusable += 1
            continue
        tot_t += p["n_tiles"]
        tot_p += p["n_positive"]
        tot_orph += p["orphaned_targets"]
    if tot_t:
        print(f"  tiles                {tot_t:,}")
        print(f"    positive           {tot_p:,}  ({tot_p/tot_t:.1%})")
        print(f"    negative           {tot_t-tot_p:,}  ({1-tot_p/tot_t:.1%})"
              "   <- the gate's rejection headroom")
        print(f"  targets sliced by every tile: {tot_orph}"
              "   (must be 0; otherwise the overlap is too narrow)")
    if unusable:
        print(f"  frames too small once rescaled: {unusable}")


if __name__ == "__main__":
    main()
