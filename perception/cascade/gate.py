#!/usr/bin/env python3
"""Stage 1: train the gate, and measure the two numbers that decide adoption.

WHAT THIS MEASURES, AND WHY IT IS NOT ACCURACY. About 96 % of tiles contain no
survivor, so a model that answers "empty" every time scores 96 % accuracy and is
worthless. The gate is judged on exactly two quantities:

    rejection   fraction of ALL tiles it discards        -- must clear 80.5 %
    recall      fraction of SURVIVOR tiles it keeps      -- must clear 90 %
                                                            per TARGET

and the threshold is chosen to hit the recall target first, taking whatever
rejection follows. Never the other way round. A false positive costs one
operator glance; a false negative costs a survivor.

THE MEASUREMENT THIS SPLIT CANNOT MAKE. Our decision rule assumes gate failures
may be FULLY CORRELATED across the twelve looks of a pass -- the case where a
survivor who reads as water reads as water every time, and multi-frame fusion
rescues nothing. Object Detection v2 is independent images with no track IDs, so
correlation is not directly observable in it. Two honest options:

  1. Use the SeaDronesSee MOT split, which has track IDs, and measure whether
     the same identity is missed across consecutive frames. This is the real
     measurement and it is what P4 should do.
  2. Use `--correlation-proxy`, which re-scores each positive tile under small
     shifts and rotations standing in for consecutive frames. A gate whose
     misses survive that perturbation is exhibiting appearance-driven failure.
     It is a proxy, it is reported as one, and it cannot substitute for (1).

Reporting per-tile recall alone would be the easy mistake here: a tile is not a
survivor, and a target appearing in two tiles is caught if either fires.

    python -m perception.cascade.gate --ann <train.json> --images <dir> \
        --val-ann <val.json> --epochs 8 --input 640
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from collections import defaultdict

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    from perception.cascade import dataset as D
    from perception.cascade import economics as E
    from perception.cascade import geometry as G
else:
    from . import dataset as D
    from . import economics as E
    from . import geometry as G

TARGET_RECALL = 0.995      # per-TILE recall to aim for; per-target is checked after


def _require_torch():
    try:
        import torch                                    # noqa: F401
        import torchvision                              # noqa: F401
    except ImportError:
        raise SystemExit(
            "Stage 1 needs torch and torchvision:\n"
            "  pip install torch torchvision --index-url "
            "https://download.pytorch.org/whl/cu121\n"
            "A GPU is strongly recommended -- roughly 14k frames x 48 tiles is "
            "days of work on CPU.")
    import torch
    return torch


# --------------------------------------------------------------- tile extraction
def iter_tiles(frames, images_dir, wanted_px, tile=640, overlap=0.20, limit=None):
    """Yield (PIL crop, label, frame_id, target_ids) for every tile.

    Rescaling happens per frame, once, before cropping -- doing it per tile
    would resample the same pixels 48 times and change the interpolation the
    model sees between training and inference.
    """
    from PIL import Image

    n = 0
    for f in frames:
        plan = D.plan_tiles(f, wanted_px, tile, overlap)
        if not plan["usable"]:
            continue
        path = os.path.join(images_dir, f.file_name)
        if not os.path.exists(path):
            continue
        with Image.open(path) as im:
            im = im.convert("RGB").resize((plan["width"], plan["height"]),
                                          Image.BILINEAR)
            tiles = G.tile_grid(plan["width"], plan["height"], tile, overlap)
            owners = defaultdict(list)          # tile index -> target ids
            for tid, idxs in enumerate(plan["targets"]):
                for i in idxs:
                    owners[i].append((f.image_id, tid))
            for i, t in enumerate(tiles):
                yield (im.crop((t.x0, t.y0, t.x1, t.y1)),
                       1 if i in owners else 0, f.image_id, owners.get(i, []))
                n += 1
                if limit and n >= limit:
                    return


def build_model(input_px: int):
    """A small backbone with a binary head. Deliberately unexotic.

    The point of the experiment is whether ANY cheap gate clears the bar, not
    whether a clever one does. A result from a standard backbone is easier to
    trust and easier for someone else to reproduce.
    """
    torch = _require_torch()
    import torchvision

    m = torchvision.models.mobilenet_v3_small(weights="DEFAULT")
    m.classifier[-1] = torch.nn.Linear(m.classifier[-1].in_features, 1)
    return m


# ------------------------------------------------------------------ evaluation
def threshold_for_recall(scores, labels, target_recall=TARGET_RECALL) -> float:
    """Lowest threshold that still achieves `target_recall` on positives.

    Chosen on validation data and then FROZEN before touching the test split.
    Picking it afterwards is how an experiment talks itself into a result.
    """
    pos = sorted(s for s, y in zip(scores, labels) if y == 1)
    if not pos:
        raise ValueError("no positive tiles -- check the category mapping")
    k = int((1.0 - target_recall) * len(pos))
    return pos[min(k, len(pos) - 1)]


def evaluate(scores, labels, frame_ids, target_ids, threshold: float) -> dict:
    """Rejection, per-tile recall, and the per-TARGET recall that actually counts."""
    keep = [s >= threshold for s in scores]
    n = len(scores)
    rejection = 1.0 - sum(keep) / n

    pos_idx = [i for i, y in enumerate(labels) if y == 1]
    tile_recall = (sum(keep[i] for i in pos_idx) / len(pos_idx)) if pos_idx else 0.0

    # A target is found if ANY tile containing it survives the gate.
    caught, seen = defaultdict(bool), set()
    for i in pos_idx:
        for key in target_ids[i]:
            seen.add(key)
            if keep[i]:
                caught[key] = True
    target_recall = (sum(caught.values()) / len(seen)) if seen else 0.0

    return {
        "threshold": threshold, "n_tiles": n,
        "rejection": rejection,
        "tile_recall": tile_recall,
        "target_recall": target_recall,
        "n_targets": len(seen),
        "targets_missed": len(seen) - sum(caught.values()),
    }


def report(res: dict, gate_input: int) -> bool:
    cascade = E.cascade_at(gate_input)
    v = E.verdict(res["rejection"], res["target_recall"],
                  E.DOWNSAMPLED, cascade)
    print("=" * 78)
    print("STAGE 1 RESULT")
    print("=" * 78)
    print(f"  tiles evaluated        {res['n_tiles']:,}")
    print(f"  targets               {res['n_targets']:,} "
          f"({res['targets_missed']} missed entirely)")
    print(f"  threshold              {res['threshold']:.4f}")
    print(f"  rejection              {res['rejection']:.1%}   "
          f"(need >= {v['break_even_rejection']:.1%})   "
          f"{'PASS' if v['cost_ok'] else 'FAIL'}")
    print(f"  per-tile recall        {res['tile_recall']:.1%}   (not the criterion)")
    print(f"  per-TARGET recall      {res['target_recall']:.1%}   "
          f"(need >= 90 %)   {'PASS' if v['recall_ok'] else 'FAIL'}")
    print()
    print(f"  compute  {v['baseline_gflop']:.0f} -> {v['cascade_gflop']:.0f} GFLOP/frame")
    print(f"  target   {E.DOWNSAMPLED.target_px:.0f} px -> {cascade.target_px:.0f} px "
          f"({v['target_px_gain']:.1f}x)")
    print()
    print(f"  VERDICT: {'ADOPT' if v['adopt'] else 'DO NOT ADOPT'}")
    if not v["adopt"]:
        if not v["cost_ok"]:
            print("    rejection too low -- the gate costs more than it saves")
        if not v["recall_ok"]:
            print("    recall too low -- survivors are being dropped unrecoverably")
    print()
    print("  Per-target recall above assumes gate failures are FULLY CORRELATED")
    print("  across a pass, which this split cannot confirm. Measure correlation")
    print("  on the MOT split before treating this as final.")
    return v["adopt"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ann", required=True)
    ap.add_argument("--val-ann", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--input", type=int, default=640, choices=(160, 320, 640))
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None,
                    help="cap tiles, for a smoke run")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch = _require_torch()
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    wanted = G.target_px(D.OUR_TARGET_M, D.OUR_ALT_M, D.OUR_PITCH_UM, D.OUR_F_MM)
    train, tr_drop = D.select(D.load_split(args.ann))
    val, _ = D.select(D.load_split(args.val_ann))
    print(f"  train frames {len(train)}, val frames {len(val)}, "
          f"target rescaled to {wanted:.0f} px")
    for why, n in sorted(tr_drop.items(), key=lambda kv: -kv[1]):
        print(f"    dropped {n:>6}  {why}")
    if not train or not val:
        raise SystemExit("no usable frames -- run fetch_data.py --verify-only first")

    import torchvision.transforms as T

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    if dev == "cpu":
        print("  WARNING: no CUDA device. This will take days, not hours.")
    tf = T.Compose([T.Resize((args.input, args.input)), T.ToTensor(),
                    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

    def load(frames, limit):
        xs, ys, fids, tids = [], [], [], []
        for crop, label, fid, owners in iter_tiles(frames, args.images, wanted,
                                                   limit=limit):
            xs.append(tf(crop))
            ys.append(label)
            fids.append(fid)
            tids.append(owners)
        return torch.stack(xs), torch.tensor(ys, dtype=torch.float32), fids, tids

    print("  extracting tiles (this is the slow part)...")
    Xtr, Ytr, _, _ = load(train, args.limit)
    Xva, Yva, fva, tva = load(val, args.limit)
    pos_frac = float(Ytr.mean())
    print(f"  train tiles {len(Ytr):,} ({pos_frac:.1%} positive), "
          f"val tiles {len(Yva):,}")
    if pos_frac == 0:
        raise SystemExit("no positive tiles -- category mapping is wrong")

    model = build_model(args.input).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    # Positives are ~4 % of tiles. Weighting the loss by the inverse frequency
    # stops the model collapsing to "always empty", which would score 96 %
    # accuracy and reject 100 % of survivors.
    pos_weight = torch.tensor([(1 - pos_frac) / max(pos_frac, 1e-6)], device=dev)
    lossf = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    n, bs = len(Ytr), 64
    for ep in range(args.epochs):
        model.train()
        perm = torch.randperm(n)
        tot = 0.0
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            xb, yb = Xtr[idx].to(dev), Ytr[idx].to(dev)
            opt.zero_grad()
            loss = lossf(model(xb).squeeze(1), yb)
            loss.backward()
            opt.step()
            tot += float(loss) * len(idx)
        print(f"    epoch {ep + 1}/{args.epochs}  loss {tot / n:.4f}")

    model.eval()
    scores = []
    with torch.no_grad():
        for i in range(0, len(Yva), bs):
            xb = Xva[i:i + bs].to(dev)
            scores.extend(torch.sigmoid(model(xb).squeeze(1)).cpu().tolist())

    labels = [int(v) for v in Yva.tolist()]
    thr = threshold_for_recall(scores, labels, TARGET_RECALL)
    res = evaluate(scores, labels, fva, tva, thr)
    ok = report(res, args.input)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
