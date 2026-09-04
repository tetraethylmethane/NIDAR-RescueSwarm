#!/usr/bin/env python3
"""Derive the canonical BSC014N06NS footprint from the verified OpenESC land.

The electrical land pattern already PASSES against PG-TDSON-8-U04: 1.27 mm
pitch, 0.58 x 1.08 lead pads covering a 0.26-0.54 x 0.45-0.72 lead, drain land
4.40 mm against a recommended 4.41, pin topology 1-3 S / 4 G / 5-8 D. None of
that is touched.

What is wrong is the STENCIL. The 4.40 x 4.10 mm thermal pad carries a single
solid paste aperture of 18.04 mm2. Infineon Figure 2 specifies a windowpane.
A solid aperture that size deposits far too much solder: the part floats, tilts
and voids, which destroys the thermal path the pad exists to provide -- on a
board where the thermal path is the binding constraint.

Fix: the thermal pad keeps its copper and mask opening but loses its own paste,
and four paste-only apertures are added in its place.

Geometry, chosen to land near Infineon's own ~52% and inside the 50-70% band:

    aperture   1.70 x 1.55 mm, four off
    gap        0.40 mm between apertures
    inset      0.30 mm from the pad edge
    coverage   4 x 1.70 x 1.55 / (4.40 x 4.10) = 58.4%

Run:  python hardware/tools/make_fet_footprint.py
"""
import io
import os
import re

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HW, "4in1ESC-30x30.pretty",
                   "PDFN-8L_L6.0-W5.0-P1.27.kicad_mod")
DST = os.path.join(HW, "lib.pretty", "BSC014N06NS_PG-TDSON-8.kicad_mod")

NAME = "BSC014N06NS_PG-TDSON-8"
PAD_W, PAD_H = 4.40, 4.10          # thermal pad copper, unchanged
PAD_CX, PAD_CY = 0.0, -0.69        # its centre, unchanged
AP_W, AP_H = 1.70, 1.55            # one paste window
GAP = 0.40


def block_end(s, start):
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unbalanced")


def main():
    txt = io.open(SRC, encoding="utf-8", errors="ignore").read()

    # 1. rename
    txt = re.sub(r'\(footprint\s+"[^"]+"', f'(footprint "{NAME}"', txt, count=1)

    # 2. find the thermal pad (the 4.40 x 4.10 one) and drop F.Paste from it
    target, t0, t1 = None, None, None
    pos = 0
    while True:
        k = txt.find("(pad ", pos)
        if k < 0:
            break
        end = block_end(txt, k)
        body = txt[k:end]
        if re.search(r"\(size 4\.4 4\.1\)", body):
            target, t0, t1 = body, k, end
            break
        pos = end
    if target is None:
        raise SystemExit("thermal pad 4.4 x 4.1 not found -- footprint changed?")

    fixed = re.sub(r'\(layers([^)]*)\)',
                   lambda m: "(layers" + m.group(1).replace(' "F.Paste"', '') + ")",
                   target, count=1)
    if "F.Paste" in fixed:
        raise SystemExit("failed to strip F.Paste from the thermal pad")
    txt = txt[:t0] + fixed + txt[t1:]

    # 3. add four paste-only apertures in its place
    dx = (AP_W + GAP) / 2.0
    dy = (AP_H + GAP) / 2.0
    wins = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = PAD_CX + sx * dx
            cy = PAD_CY + sy * dy
            wins.append(
                f'\n\t(pad "3" smd rect\n'
                f"\t\t(at {cx:.4g} {cy:.4g})\n"
                f"\t\t(size {AP_W} {AP_H})\n"
                f'\t\t(layers "F.Paste")\n'
                f"\t)")
    # 4. add a courtyard. The donor footprint has NONE -- its only layers are
    #    F.Cu, F.Fab, F.Mask, F.Paste and F.Silkscreen. Without a courtyard the
    #    courtyard-overlap DRC has nothing to test, which is part of why
    #    overlapping placements went unnoticed on OpenAIO.
    #
    #    Extent: the union of the max body (5.35 x 6.10 from Figure 1) and the
    #    pad field (4.40 x 6.74), plus 0.25 mm excess.
    cx, cy = 2.93, 3.62
    court = (f'\n\t(fp_rect\n'
             f"\t\t(start {-cx} {-cy})\n\t\t(end {cx} {cy})\n"
             f"\t\t(stroke (width 0.05) (type solid))\n"
             f"\t\t(fill none)\n"
             f'\t\t(layer "F.CrtYd")\n\t)')

    close = txt.rstrip()
    assert close.endswith(")")
    txt = close[:-1] + court + "".join(wins) + "\n)\n"

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    io.open(DST, "w", encoding="utf-8", newline="\n").write(txt)

    pad_area = PAD_W * PAD_H
    ap_area = 4 * AP_W * AP_H
    print(f"wrote {os.path.basename(DST)}")
    print(f"   thermal pad   {PAD_W} x {PAD_H} mm = {pad_area:.2f} mm2 copper")
    print(f"   paste windows 4 x {AP_W} x {AP_H} mm = {ap_area:.2f} mm2")
    print(f"   coverage      {100*ap_area/pad_area:.1f} %")
    print(f"   gap {GAP} mm, inset "
          f"{(PAD_W - 2*AP_W - GAP)/2:.2f} x {(PAD_H - 2*AP_H - GAP)/2:.2f} mm")


if __name__ == "__main__":
    main()
