#!/usr/bin/env python3
"""Check the board's stackup and fine-feature compatibility. READ ONLY.

Does not modify the board. Reports where the board file disagrees with
docs/stackup.md, and where copper weight collides with the finest features
actually placed.

Run with KiCad's Python:
    "C:/Program Files/KiCad/10.0/bin/python.exe" verify_stackup.py
"""
import os
import re
import sys

import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HW, "DrikrAIO.kicad_pcb")

TARGET_THICKNESS_MM = 1.60
THICKNESS_TOL = 0.10
OUTER_OZ = 2                    # frozen requirement
OZ_UM = 34.8

# Typical low-cost capability. Fabricator must confirm; these are the numbers
# the design is being checked against, not a guarantee.
MIN_FEATURE_BY_OZ = {1: 0.15, 2: 0.20, 3: 0.25}

ok, warn, bad = [], [], []


def chk(cond, msg, hard=True):
    if cond:
        ok.append(msg)
        print(f"  PASS  {msg}")
    elif hard:
        bad.append(msg)
        print(f"  FAIL  {msg}")
    else:
        warn.append(msg)
        print(f"  WARN  {msg}")


def main():
    txt = open(PCB, encoding="utf-8", errors="ignore").read()
    i = txt.find("(stackup")
    if i < 0:
        print("  FAIL  board has no stackup block")
        return 2
    blk = txt[i:txt.find("(pad_to_mask_clearance", i)]

    print("STACKUP CONSISTENCY CHECK")
    print("=" * 70)

    cu = re.findall(r'\(layer "((?:F|B|In\d+)\.Cu)"\s*\(type "copper"\)\s*'
                    r'\(thickness ([\d.]+)\)', blk)
    diel = [float(t) for t in re.findall(
        r'\(type "(?:prepreg|core)"\)\s*\(thickness ([\d.]+)\)', blk)]
    total = sum(float(t) for _, t in cu) + sum(diel)

    chk(len(cu) == 6, f"6 copper layers declared (found {len(cu)})")

    outer = {n: float(t) for n, t in cu if n in ("F.Cu", "B.Cu")}
    inner = {n: float(t) for n, t in cu if n.startswith("In")}
    want_outer = OUTER_OZ * OZ_UM / 1000.0
    for n, t in outer.items():
        chk(abs(t - want_outer) < 0.005,
            f"{n} is {t*1000:.0f} um ({t/OZ_UM*1000:.1f} oz), "
            f"frozen requirement {OUTER_OZ} oz")
    chk(all(abs(t - OZ_UM / 1000.0) < 0.005 for t in inner.values()),
        f"inner layers 1 oz (found {sorted({round(t*1000) for t in inner.values()})} um)")

    chk(abs(total - TARGET_THICKNESS_MM) <= THICKNESS_TOL,
        f"finished thickness {total:.2f} mm vs {TARGET_THICKNESS_MM} mm "
        f"+/- {THICKNESS_TOL}", hard=False)

    # the two thin prepregs the RF reference and commutation loop depend on
    thin = [d for d in diel if d <= 0.12]
    chk(len(thin) >= 2,
        f"at least two <=0.12 mm prepregs for L1-L2 and L5-L6 "
        f"(found {len(thin)}: {thin})")

    fin = re.search(r'\(copper_finish "([^"]*)"\)', blk)
    chk(fin is not None and fin.group(1) == "ENIG",
        f"surface finish ENIG (found {fin.group(1) if fin else 'unset'})")

    dc = re.search(r'\(dielectric_constraints (yes|no)\)', blk)
    chk(dc is not None and dc.group(1) == "yes",
        "impedance control declared (dielectric_constraints)", hard=False)

    # ---- fine features vs copper weight --------------------------------
    print("\nFINE-FEATURE COMPATIBILITY")
    print("-" * 70)
    board = pcbnew.LoadBoard(PCB)
    limit = MIN_FEATURE_BY_OZ[OUTER_OZ]
    offenders = {"F.Cu": [], "B.Cu": []}
    degenerate = []
    for fp in board.Footprints():
        layer = "B.Cu" if fp.GetLayer() == pcbnew.B_Cu else "F.Cu"
        smallest = None
        for p in fp.Pads():
            ls = p.GetLayerSet()
            if not (ls.Contains(pcbnew.F_Cu) or ls.Contains(pcbnew.B_Cu)):
                continue
            d = min(p.GetSize().x, p.GetSize().y) / 1e6
            if d <= 0:
                continue
            smallest = d if smallest is None else min(smallest, d)
        if smallest is None:
            continue
        if smallest < 0.05:
            degenerate.append((fp.GetReference(), fp.GetValue()[:26], smallest))
        elif smallest < limit:
            offenders[layer].append((fp.GetReference(), fp.GetValue()[:26], smallest))

    print(f"  {OUTER_OZ} oz outer assumed capability: {limit:.2f} mm min feature")
    for side in ("F.Cu", "B.Cu"):
        n = len(offenders[side])
        chk(n == 0,
            f"{side}: {n} part(s) with pads below {limit:.2f} mm", hard=False)
        for r, v, d in sorted(offenders[side], key=lambda x: x[2])[:6]:
            print(f"           {d:.3f} mm  {r:<9} {v}")

    chk(not degenerate,
        f"no footprints with sub-0.05 mm copper pads "
        f"({len(degenerate)} found)")
    for r, v, d in sorted(degenerate, key=lambda x: x[2]):
        print(f"           {d:.4f} mm  {r:<9} {v}   UNMANUFACTURABLE")

    print("=" * 70)
    print(f"  {len(ok)} pass, {len(warn)} warn, {len(bad)} fail")
    if bad:
        print("\n  Stackup is NOT consistent with the board as it stands.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
