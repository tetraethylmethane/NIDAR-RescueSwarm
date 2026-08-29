#!/usr/bin/env python3
"""The cascade experiment, in the order the questions should be asked.

Three stages, cheapest first, each able to kill the idea before the next one
costs anything:

  STAGE 0  CEILING.  What fraction of tiles contain no person at all? That is
           the most a perfect gate could ever reject. If it sits below the
           break-even rejection rate, the cascade cannot pay for itself no
           matter how good the model is, and nobody needs to train anything.
           Costs: reading the annotations. No images, no GPU.

  STAGE 1  GATE.  Train the gate, measure rejection at the operating threshold
           and recall on held-out data. Costs: the dataset and a GPU.

  STAGE 2  VERDICT.  Apply the decision rule fixed in economics.py, which was
           written before any result was seen.

Stage 0 runs today. Stages 1 and 2 need SeaDronesSee on disk; they fail with a
clear message rather than a stack trace when it is absent.

WHY THE ORDER MATTERS. It is very easy to spend a fortnight training a gate and
then discover the arithmetic never worked. Stage 0 is half an hour and answers
the question that gates the fortnight.
"""
from __future__ import annotations

import argparse
import os
import sys

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


def stage0_analytic() -> dict:
    """The ceiling, from our own mission geometry rather than borrowed data.

    Ten survivors is the rulebook cap for a 10 ha area searched by three
    aircraft. A single frame covers a small part of that, so almost every frame
    contains no survivor at all and almost every tile in the frames that do
    contain one is still empty.
    """
    tiles = len(G.tile_grid(4056, 3040, 640, 0.20))
    tgt = G.target_px(D.OUR_TARGET_M, D.OUR_ALT_M, D.OUR_PITCH_UM, D.OUR_F_MM)
    # A target this size falls inside one tile, or two where it straddles the
    # shared margin. Two is the pessimistic assumption and the one used here.
    tiles_per_target = 2
    rows = []
    for n_in_frame in (0, 1, 2, 3):
        pos = min(n_in_frame * tiles_per_target, tiles)
        rows.append((n_in_frame, pos, tiles - pos, 1.0 - pos / tiles))
    return {"n_tiles": tiles, "target_px": tgt, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ann", help="COCO json for a SeaDronesSee split "
                                  "(omit to run Stage 0 only)")
    args = ap.parse_args()

    cascade = E.cascade_at(640)          # see economics: gate cost barely matters
    be = E.break_even_rejection(E.DOWNSAMPLED, cascade)

    print("=" * 78)
    print("STAGE 0  --  IS THE CEILING ABOVE THE FLOOR?")
    print("=" * 78)
    a = stage0_analytic()
    print(f"  {a['n_tiles']} tiles per frame, target {a['target_px']:.0f} px, "
          "assuming a target can straddle two tiles")
    print(f"  {'survivors in frame':>20}{'positive':>10}{'negative':>10}{'max rejection':>15}")
    for n, pos, neg, frac in a["rows"]:
        print(f"  {n:>20}{pos:>10}{neg:>10}{frac:>14.1%}")
    print()
    print(f"  break-even rejection needed: {be:.1%}")
    worst = a["rows"][-1][3]
    if worst >= be:
        print(f"  CEILING CLEARS THE FLOOR even with three survivors in one frame "
              f"({worst:.1%} >= {be:.1%}).")
        print("  So the cascade is not limited by how many empty tiles exist.")
        print("  It is limited by whether a gate can FIND them at recall ~1.0,")
        print("  which is Stage 1 and needs data.")
    else:
        print("  CEILING IS BELOW THE FLOOR. Stop here; no gate can pay for this.")

    if not args.ann:
        print()
        print("=" * 78)
        print("STAGE 1  --  needs SeaDronesSee")
        print("=" * 78)
        print("  Re-run with --ann /path/to/instances_train.json once the")
        print("  dataset is on disk. Stage 1 measures, on held-out frames:")
        print("    rejection rate at the operating threshold")
        print("    per-TARGET recall, and whether misses correlate across looks")
        print()
        print("=" * 78)
        print("DECISION RULE  --  fixed in advance, in economics.py")
        print("=" * 78)
        v = E.verdict(rejection=be, gate_recall=0.90, baseline=E.DOWNSAMPLED,
                      cascade=cascade)
        print(f"  adopt only if rejection >= {v['break_even_rejection']:.1%}")
        print("  AND per-target recall >= 90 % with gate failures assumed")
        print("  FULLY CORRELATED across the pass.")
        print(f"  Prize if it holds: target goes {E.DOWNSAMPLED.target_px:.0f} px "
              f"-> {cascade.target_px:.0f} px for the same compute "
              f"({v['target_px_gain']:.1f}x).")
        return

    print()
    print("=" * 78)
    print("STAGE 0b  --  THE CEILING IN THE ACTUAL TEST DATA")
    print("=" * 78)
    frames = D.load_split(args.ann)
    kept, reasons = D.select(frames)
    print(f"  frames read {len(frames)}, usable {len(kept)}")
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"    dropped {n:>6}  {why}")
    wanted = G.target_px(D.OUR_TARGET_M, D.OUR_ALT_M, D.OUR_PITCH_UM, D.OUR_F_MM)
    tot = pos = orph = 0
    for f in kept:
        p = D.plan_tiles(f, wanted)
        if p["usable"]:
            tot += p["n_tiles"]
            pos += p["n_positive"]
            orph += p["orphaned_targets"]
    if not tot:
        raise SystemExit("no usable tiles -- check the annotation path and categories")
    print(f"  tiles {tot:,}, positive {pos:,} ({pos/tot:.1%}), "
          f"max rejection {1-pos/tot:.1%} vs break-even {be:.1%}")
    if orph:
        print(f"  WARNING: {orph} targets sliced by every tile -- overlap too narrow")


if __name__ == "__main__":
    main()
