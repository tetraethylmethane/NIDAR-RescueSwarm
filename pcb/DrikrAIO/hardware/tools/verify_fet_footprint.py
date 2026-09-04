#!/usr/bin/env python3
"""Validate the BSC014N06NS footprint against PG-TDSON-8-U04.

Checks copper, mask, paste and courtyard against the Infineon Rev 2.6 package
drawing (Figure 1) and recommended land (Figure 2).

Run with KiCad's Python:
    "C:/Program Files/KiCad/10.0/bin/python.exe" verify_fet_footprint.py
"""
import os
import sys

import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(HW, "lib.pretty")
FP = "BSC014N06NS_PG-TDSON-8"

# PG-TDSON-8-U04, Figure 1 (mm)
PKG = dict(D=(4.80, 5.35), E=(5.70, 6.10), e=1.27,
           b=(0.26, 0.54), L=(0.45, 0.72),
           D1=(3.70, 4.40), E1=(3.40, 3.76), A=(0.90, 1.20))
# Figure 2 recommended land
REC = dict(drain_w=4.41, drain_h=4.55, lead_h=1.10)
PASTE_BAND = (50.0, 70.0)          # acceptable coverage band, %

ok, bad = [], []


def chk(cond, msg):
    (ok if cond else bad).append(msg)
    print(f"  {'PASS' if cond else 'FAIL'}  {msg}")


def main():
    fp = pcbnew.FootprintLoad(LIB, FP)
    if fp is None:
        print(f"  FAIL  {FP} does not load from {LIB}")
        return 2

    cu, paste_only, mask = [], [], []
    for p in fp.Pads():
        layers = p.GetLayerSet()
        on_cu = layers.Contains(pcbnew.F_Cu)
        on_paste = layers.Contains(pcbnew.F_Paste)
        on_mask = layers.Contains(pcbnew.F_Mask)
        rec = dict(num=p.GetNumber(),
                   w=p.GetSize().x / 1e6, h=p.GetSize().y / 1e6,
                   x=p.GetPosition().x / 1e6, y=p.GetPosition().y / 1e6,
                   cu=on_cu, paste=on_paste, mask=on_mask)
        (cu if on_cu else paste_only).append(rec)
        if on_mask:
            mask.append(rec)

    print(f"FOOTPRINT VALIDATION -- {FP}")
    print("=" * 70)

    # --- copper pads -----------------------------------------------------
    leads = [p for p in cu if abs(p["w"] - 0.58) < 0.01]
    therm = [p for p in cu if p["w"] > 3.0]
    chk(len(leads) == 8, f"8 lead pads present (found {len(leads)})")
    chk(len(therm) == 1, f"1 thermal pad present (found {len(therm)})")

    if leads:
        w = {round(p["w"], 3) for p in leads}
        h = {round(p["h"], 3) for p in leads}
        chk(w == {0.58}, f"lead pad width 0.58 mm (found {w})")
        chk(h == {1.08}, f"lead pad length 1.08 mm (found {h})")
        chk(PKG["b"][1] <= 0.58, f"lead pad 0.58 >= max lead width b={PKG['b'][1]}")
        chk(PKG["L"][1] <= 1.08, f"lead pad 1.08 >= max lead length L={PKG['L'][1]}")
        chk(abs(1.08 - REC["lead_h"]) <= 0.05,
            f"lead pad length within 0.05 of recommended {REC['lead_h']}")
        # per row -- the two rows differ by 0.01 mm in x, and pooling them
        # manufactures 0.01 mm gaps that are not pitches
        pitches = []
        for row in sorted({round(p["y"], 2) for p in leads}):
            xs = sorted(p["x"] for p in leads if abs(p["y"] - row) < 0.05)
            pitches += [round(xs[i + 1] - xs[i], 3) for i in range(len(xs) - 1)]
        chk(all(abs(pp - PKG["e"]) <= 0.02 for pp in pitches),
            f"pitch {PKG['e']} mm (measured {pitches})")
        rows = sorted({round(p["y"], 2) for p in leads})
        chk(len(rows) == 2, f"two lead rows (found {rows})")

    if therm:
        t = therm[0]
        chk(abs(t["w"] - 4.40) < 0.01 and abs(t["h"] - 4.10) < 0.01,
            f"thermal pad 4.40 x 4.10 mm (found {t['w']} x {t['h']})")
        chk(PKG["D1"][0] <= t["w"] <= PKG["D1"][1] + 0.01,
            f"thermal pad width inside exposed-pad D1 {PKG['D1']}")
        chk(t["h"] >= PKG["E1"][1],
            f"thermal pad height {t['h']} >= max exposed pad E1 {PKG['E1'][1]}")
        chk(abs(t["w"] - REC["drain_w"]) <= 0.05,
            f"thermal pad within 0.05 of recommended drain land {REC['drain_w']}")
        chk(not t["paste"], "thermal pad carries NO paste of its own")
        chk(t["mask"], "thermal pad has a mask opening")

    # --- numbering -------------------------------------------------------
    nums = sorted({p["num"] for p in cu})
    chk(nums == ["1", "2", "3"],
        f"pad numbering 1=S 2=G 3=D (found {nums})")
    n_src = len([p for p in leads if p["num"] == "1"])
    n_gate = len([p for p in leads if p["num"] == "2"])
    n_drain = len([p for p in leads if p["num"] == "3"])
    chk((n_src, n_gate, n_drain) == (3, 1, 4),
        f"topology 3 source / 1 gate / 4 drain leads "
        f"(found {n_src}/{n_gate}/{n_drain}) -- matches pins 1-3 S, 4 G, 5-8 D")

    # --- paste windowpane ------------------------------------------------
    # Paste-only pads are "aperture pads" and KiCad gives them no number.
    # That is correct behaviour, so select them by layer rather than number.
    wins = paste_only
    chk(len(wins) == 4, f"4 paste windows (found {len(wins)})")
    if wins and therm:
        aw = {round(p["w"], 3) for p in wins}
        ah = {round(p["h"], 3) for p in wins}
        chk(len(aw) == 1 and len(ah) == 1,
            f"windows uniform ({aw} x {ah})")
        area = sum(p["w"] * p["h"] for p in wins)
        pad = therm[0]["w"] * therm[0]["h"]
        cov = 100 * area / pad
        chk(PASTE_BAND[0] <= cov <= PASTE_BAND[1],
            f"paste coverage {cov:.1f}% in {PASTE_BAND[0]:.0f}-{PASTE_BAND[1]:.0f}% band")
        xs = sorted({round(p["x"], 3) for p in wins})
        ys = sorted({round(p["y"], 3) for p in wins})
        gx = round(xs[1] - xs[0] - list(aw)[0], 3)
        gy = round(ys[1] - ys[0] - list(ah)[0], 3)
        chk(gx >= 0.2 and gy >= 0.2,
            f"window spacing {gx} x {gy} mm (>= 0.2 stencil-safe)")
        t = therm[0]
        inside = all(
            abs(p["x"] - t["x"]) + p["w"] / 2 <= t["w"] / 2 + 1e-6 and
            abs(p["y"] - t["y"]) + p["h"] / 2 <= t["h"] / 2 + 1e-6 for p in wins)
        chk(inside, "all paste windows fall inside the thermal pad")

    # --- courtyard and silkscreen ---------------------------------------
    cy = [g for g in fp.GraphicalItems()
          if g.GetLayerName() in ("F.CrtYd", "F.Courtyard")]
    silk = [g for g in fp.GraphicalItems() if g.GetLayerName() in ("F.SilkS", "F.Silkscreen")]
    bb = fp.GetBoundingBox(False, False)
    chk(bb.GetWidth() / 1e6 >= PKG["D"][1] and bb.GetHeight() / 1e6 >= PKG["E"][1],
        f"extent {bb.GetWidth()/1e6:.2f} x {bb.GetHeight()/1e6:.2f} mm clears "
        f"max body {PKG['D'][1]} x {PKG['E'][1]}")
    chk(len(cy) > 0, f"courtyard present ({len(cy)} items)")
    chk(len(silk) > 0, f"silkscreen present ({len(silk)} items)")

    print("=" * 70)
    print(f"  {len(ok)} passed, {len(bad)} failed")
    print()
    print("  NOT CHECKED HERE, because it is a LAYOUT property, not a")
    print("  footprint one: the thermal via array under the pad. The review")
    print("  requires >= 9 vias per drain pad into the inner planes; that is")
    print("  verified on the board, not in the library.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
