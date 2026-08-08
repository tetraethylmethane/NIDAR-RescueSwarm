"""Generate the SolidWorks equations file that drives the frame.

WHY
The battery bay in frame-design-constraints.md specified a 12-cell 6S2P pack
when the design point is 18 cells and 6S3P. It got there by being TRANSCRIBED
from the model into a document, after which the model moved and the document
did not. A markdown table is cheap to correct. A frame is not.

CAD is the next place that class of error lands, so the frame should read its
driving dimensions from a generated file rather than from someone's memory of
a number.

HOW IT WORKS IN SOLIDWORKS
SolidWorks supports global variables and equations, and an equation set can be
LINKED TO AN EXTERNAL TEXT FILE:

    Tools -> Equations -> "Link to external file" -> pick this .txt

Once linked, the variables appear in the Equations dialog as read-only and are
re-read on rebuild. Sketch dimensions are then driven by expression rather than
typed, e.g. a motor-mount circle placed at

    = "wheelbase_diag" / 2

Change the pack, re-run this script, rebuild: the frame follows. Nobody
retypes 761.

The file is plain text, so it lives in git next to everything else, and the
reproduce job checks it still matches the model -- the same loop that already
guards eleven other outputs.

Run:  python tools/sizing-model/cad_equations.py
Emits: hardware/cad/rescueswarm-frame-equations.txt
"""
from __future__ import annotations

import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))      # tools/sizing-model
ROOT = os.path.dirname(os.path.dirname(HERE))          # repo root
MODEL_OUT = os.path.join(ROOT, "docs", "sizing", "model-output.txt")
OUT_DIR = os.path.join(ROOT, "hardware", "cad")
OUT_FILE = os.path.join(OUT_DIR, "rescueswarm-frame-equations.txt")

# --- design inputs ----------------------------------------------------------
# Arms are sized for the LARGEST prop they must accept, not the current choice.
# 18 in is provisional and settles on a bench in P5 (constraint #2); late
# binding is free now and expensive later.
PROP_MAX_IN = 20.0
PROP_NOW_IN = 18.0
TIP_CLEARANCE_MM = 30.0

# 21700 cell, 6S3P. Bare block is cells only; packaged adds holders, wrap, BMS,
# leads. The third row is the +21 mm that the superseded 6S2P entry did not have.
CELL_D_MM, CELL_L_MM = 21.0, 70.0
S_CELLS, P_PAR = 6, 3
PACK_PAD_MM = 14.0          # holders/wrap/BMS around the block
PACK_GROWTH = 0.15          # spare on the depth axis

KIT_L_MM, KIT_W_MM, KIT_H_MM = 200.0, 100.0, 50.0
N_KITS = 4

# Boresight: 0.153 deg over an 80 mm fastener spacing is 0.21 mm of allowed
# differential movement, for life. See boresight_budget.py.
CAM_FASTENER_SPACING_MM = 80.0
BORESIGHT_TOL_DEG = 0.153

LAUNCH_BOX_MM = 3660.0
N_AIRCRAFT = 3


def mm(inches: float) -> float:
    return inches * 25.4


# --- derived geometry -------------------------------------------------------
prop_max_mm = mm(PROP_MAX_IN)
# Adjacent motors sit wheelbase/sqrt(2) apart on a quad in X. Tips clear when
# that spacing is at least one prop diameter plus the clearance.
adjacent_mm = prop_max_mm + TIP_CLEARANCE_MM
wheelbase_mm = adjacent_mm * math.sqrt(2.0)
footprint_mm = adjacent_mm + prop_max_mm          # overall square, tip to tip
arm_length_mm = wheelbase_mm / 2.0

cells_across, cells_deep = S_CELLS, P_PAR
pack_bare_l = cells_across * CELL_D_MM
pack_bare_w = CELL_L_MM
pack_bare_d = cells_deep * CELL_D_MM
bay_l = pack_bare_l + PACK_PAD_MM
bay_w = pack_bare_w + PACK_PAD_MM
bay_d = pack_bare_d * (1.0 + PACK_GROWTH)

mag_l = 2 * KIT_L_MM
mag_w = 2 * KIT_W_MM
mag_h = KIT_H_MM

cam_tol_mm = CAM_FASTENER_SPACING_MM * math.tan(math.radians(BORESIGHT_TOL_DEG))
fleet_span_mm = N_AIRCRAFT * footprint_mm


# --- cross-check against the committed model output -------------------------
def model_says() -> dict:
    """Pull the few stable numbers out of the authoritative model output.

    Parsing prose is fragile, which is the point: if the model output changes
    shape this fails loudly rather than silently generating a frame for the
    wrong aircraft.
    """
    if not os.path.exists(MODEL_OUT):
        sys.exit(f"model output not found: {MODEL_OUT}")
    txt = open(MODEL_OUT, encoding="utf-8").read()
    out = {}
    m = re.search(r"(\d+)\s*in props,\s*(\d+)S(\d+)P", txt)
    if not m:
        sys.exit("could not find 'NN in props, XSYP' in the model output")
    out["prop_in"] = float(m.group(1))
    out["S"], out["P"] = int(m.group(2)), int(m.group(3))
    m = re.search(r"Pack\s*:\s*(\d+) cells", txt)
    if not m:
        sys.exit("could not find the cell count in the model output")
    out["cells"] = int(m.group(1))
    return out


ms = model_says()
problems = []
if ms["S"] != S_CELLS or ms["P"] != P_PAR:
    problems.append(f"pack topology: model {ms['S']}S{ms['P']}P, this script "
                    f"{S_CELLS}S{P_PAR}P")
if ms["cells"] != S_CELLS * P_PAR:
    problems.append(f"cell count: model {ms['cells']}, this script "
                    f"{S_CELLS * P_PAR}")
if ms["prop_in"] > PROP_MAX_IN:
    problems.append(f"model prop {ms['prop_in']:.0f} in exceeds the "
                    f"{PROP_MAX_IN:.0f} in the arms are sized for")
if problems:
    print("CAD EQUATIONS DO NOT MATCH THE MODEL:")
    for p in problems:
        print("  ", p)
    sys.exit(1)


# --- emit -------------------------------------------------------------------
LINES = [
    ("Generated by tools/sizing-model/cad_equations.py -- DO NOT EDIT BY HAND.", None),
    ("Link this file: Tools > Equations > Link to external file.", None),
    ("Regenerate after any change to the sizing model, and commit both.", None),
    (None, None),
    ("PROPULSION GEOMETRY  (arms sized for the LARGEST prop, not the current one)", None),
    ("prop_dia_max", prop_max_mm),
    ("prop_dia_now", mm(PROP_NOW_IN)),
    ("tip_clearance", TIP_CLEARANCE_MM),
    ("motor_spacing_adjacent", adjacent_mm),
    ("wheelbase_diag", wheelbase_mm),
    ("arm_length", arm_length_mm),
    ("footprint_square", footprint_mm),
    (None, None),
    ("BATTERY BAY  6S3P, 18 x 21700  (was 6S2P/12 -- see frame-design-constraints #3)", None),
    ("cell_dia", CELL_D_MM),
    ("cell_length", CELL_L_MM),
    ("pack_block_length", pack_bare_l),
    ("pack_block_width", pack_bare_w),
    ("pack_block_depth", pack_bare_d),
    ("bay_length", bay_l),
    ("bay_width", bay_w),
    ("bay_depth", bay_d),
    (None, None),
    ("PAYLOAD MAGAZINE  4 kits, 2x2, centred on the CG", None),
    ("kit_length", KIT_L_MM),
    ("kit_width", KIT_W_MM),
    ("kit_height", KIT_H_MM),
    ("magazine_length", mag_l),
    ("magazine_width", mag_w),
    ("magazine_height", mag_h),
    (None, None),
    ("CAMERA MOUNT  boresight 0.153 deg -> this much differential, for life", None),
    ("cam_fastener_spacing", CAM_FASTENER_SPACING_MM),
    ("cam_max_differential", cam_tol_mm),
    (None, None),
    ("CHECKS  (not for driving geometry -- for asserting against)", None),
    ("fleet_span_side_by_side", fleet_span_mm),
    ("launch_box", LAUNCH_BOX_MM),
]

os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as fh:
    for name, val in LINES:
        if name is None:
            fh.write("\n")
        elif val is None:
            fh.write(f"' {name}\n")
        else:
            fh.write(f'"{name}"= {val:.3f}\n')

W = 78
print("=" * W)
print("SOLIDWORKS EQUATIONS  -  generated from the sizing model")
print("=" * W)
print(f"  model says : {ms['prop_in']:.0f} in props, {ms['S']}S{ms['P']}P, "
      f"{ms['cells']} cells   [cross-check PASSED]")
print(f"  written to : hardware/cad/rescueswarm-frame-equations.txt")
print()
for name, val in LINES:
    if name is None:
        print()
    elif val is None:
        print(f"  {name}")
    else:
        print(f'    "{name}"= {val:.3f}')
print()
print("=" * W)
print("SANITY")
print("=" * W)
ok = fleet_span_mm <= LAUNCH_BOX_MM
print(f"  3 aircraft side by side : {fleet_span_mm:.0f} mm vs {LAUNCH_BOX_MM:.0f} mm "
      f"box  [{'OK' if ok else 'OVER'}]  {LAUNCH_BOX_MM - fleet_span_mm:.0f} mm spare")
print(f"  camera differential     : {cam_tol_mm:.3f} mm over "
      f"{CAM_FASTENER_SPACING_MM:.0f} mm -- an M3 clearance hole is 0.2-0.4 mm,")
print("                            which is why this is a dowel or a bond")
print(f"  bay depth vs 6S2P       : {bay_d:.0f} mm against "
      f"{(2 * CELL_D_MM) * (1 + PACK_GROWTH):.0f} mm -- take it WIDER, not deeper")
print("=" * W)
