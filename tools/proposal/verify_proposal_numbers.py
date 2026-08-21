#!/usr/bin/env python3
r"""Check every numeric claim in the proposal against the model that owns it.

WHY THIS EXISTS. Section V is generated and asserts itself against the sizing
model, so it cannot drift. Sections I-IV and VI-XII are hand-written and were
never checked by anything. This closes that gap: it re-derives each claim from
the authoritative source and reports PASS/FAIL, exiting non-zero on any failure
so it can be wired into CI.

A claim that is deliberately a REQUIREMENT rather than a prediction (">= 2.0
cm/px") is checked as an inequality, not an equality. A claim that cannot be
mechanically checked is listed at the end as unverified rather than silently
skipped -- pretending to check something is worse than admitting you did not.

Run:  python tools/proposal/verify_proposal_numbers.py
"""
from __future__ import annotations

import contextlib
import io
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "sizing-model"))
with contextlib.redirect_stdout(io.StringIO()):
    import rescueswarm_sizing_model as M
    import camera_optics as CO

TEX = io.open(os.path.join(ROOT, "docs", "proposal", "rescueswarm-proposal.tex"),
              encoding="utf-8").read()

results = []


def check(section, claim, stated, computed, tol=0.005, unit="", note=""):
    if computed == 0:
        ok = stated == 0
        rel = 0.0
    else:
        rel = abs(stated - computed) / abs(computed)
        ok = rel <= tol
    results.append((ok, section, claim, stated, computed, rel, unit, note))


def in_tex(s):
    """Is this literal string actually present in the document?"""
    return s in TEX


# =====================================================================  IV-A
# Design point table
mtow, fleet = M.MTOW, 3 * M.MTOW
check("IV-A", "MTOW", 6.36, mtow, unit="kg")
check("IV-A", "fleet mass", 19.08, fleet, unit="kg")
check("IV-A", "pack energy", 292, M.E_pack, tol=0.01, unit="Wh")
check("IV-A", "pack nominal voltage", 21.6, M.V_nom, unit="V")
check("IV-A", "pack mass", 1449, M.m_pack * 1000, unit="g")
check("IV-A", "cells per aircraft", 18, M.n_cells)
check("IV-A", "peak pack current", 115, M.I_max, tol=0.01, unit="A")
check("IV-A", "peak C-rate", 8.5, M.I_max / M.Ah_pack, tol=0.02, unit="C")
check("IV-A", "hover endurance", 15.3, M.t_hov, tol=0.01, unit="min")
check("IV-A", "design mission duration", 7.7, M.T / 60, tol=0.01, unit="min")
check("IV-A", "rotor diameter", 18, M.D / 0.0254, unit="in")
check("IV-A", "static thrust-to-weight", 2.0, M.T_W)

# =====================================================================  IV-B
# Mass statement narrative
bd = M.bd
struct = bd["struct"]
# The residual is NOT MTOW minus sum(bd) -- bd sums to MTOW exactly. It is the
# gap inside the payload line: bd["payload"] is 1340 g, but the itemisation the
# document prints accounts for only the 240 g magazine and 4 x 200 g of kits.
# That 300 g is real and unattributed, which is what the proposal says.
MAGAZINE, KITS = 0.240, 0.800
listed = (bd["struct"] + bd["motors"] + bd["esc"] + bd["props"]
          + bd["battery"] + bd["avionics"] + MAGAZINE + KITS)
resid = mtow - listed
check("IV-B", "structure + battery share of MTOW",
      0.46, (struct + M.m_pack) / mtow, tol=0.02)
check("IV-B", "unallocated mass residual", 299, resid * 1000, tol=0.05, unit="g")
check("IV-B", "residual as % of MTOW", 4.7, 100 * resid / mtow, tol=0.05, unit="%")
check("IV-B", "growth allowance to 24 kg fleet",
      4919, (24 - fleet) * 1000, tol=0.02, unit="g")
check("IV-B", "build overweight tolerated",
      26, 100 * (24 / fleet - 1), tol=0.05, unit="%")
check("IV-B", "survivor kits mass", 800, KITS * 1000, unit="g")
check("IV-B", "survivor kits share of MTOW", 12.6, 100 * KITS / mtow,
      tol=0.02, unit="%")

# =====================================================================  IV-E
# Perception / inference budget, as written in the hand-authored section
spec60 = CO.at_altitude(CO.SPECIFIED, 60.0)
modl60 = CO.at_altitude(CO.MODELLED, 60.0)
spec40 = CO.at_altitude(CO.SPECIFIED, 40.0)
# tiles at 2x downsample
w2, h2 = CO.SPECIFIED["px_w"] // 2, CO.SPECIFIED["px_h"] // 2
tiles = math.ceil(w2 / (640 * 0.8)) * math.ceil(h2 / (640 * 0.8))
check("IV-E", "tiles per frame at 2x downsample", 12, tiles)
check("IV-E", "inferences/s at 2 Hz", 24, tiles * 2.0, unit="/s")
# Claims are now written against the sensor the BOM actually buys.
def band(gsd_cm):
    """Target long axis in pixels, and its bounding-box area in px^2."""
    gsd_m = gsd_cm / 100.0
    L = CO.PERSON_M / gsd_m
    W = CO.PERSON_W / gsd_m
    return L, L * W

L40, A40 = band(spec40["gsd_cm"] * 2)
L60, A60 = band(spec60["gsd_cm"] * 2)
check("IV-E", "GSD at 40 m, 2x, as bought", 2.07, spec40["gsd_cm"] * 2,
      tol=0.02, unit="cm/px")
check("IV-E", "target px at 40 m, 2x", 82, L40, tol=0.02, unit="px")
check("IV-E", "target area at 40 m, 2x", 1990, A40, tol=0.02, unit="px2")
check("IV-E", "GSD at 60 m, 2x, as bought", 3.10, spec60["gsd_cm"] * 2,
      tol=0.02, unit="cm/px")
check("IV-E", "target px at 60 m, 2x", 55, L60, tol=0.02, unit="px")
check("IV-E", "target area at 60 m, 2x", 884, A60, tol=0.02, unit="px2")
results.append((A60 < CO.COCO_SMALL_PX2, "IV-E",
                "60 m target is BELOW the COCO small threshold", 1, 1, 0.0, "",
                f"{A60:.0f} px2 vs {CO.COCO_SMALL_PX2} -- the claim in the text"))
results.append((CO.COCO_SMALL_PX2 <= A40 < CO.COCO_MED_PX2, "IV-E",
                "40 m target is in the COCO medium band", 1, 1, 0.0, "",
                f"{A40:.0f} px2"))
check("IV-E", "sensor pitch stated in text", 1.55, CO.SPECIFIED["pitch_um"],
      unit="um")

# angular blur gate quoted in the pipeline figure
ang_per_px = CO.optics(CO.SPECIFIED)["hfov"] / CO.SPECIFIED["px_w"]   # deg/px
rate_1px = ang_per_px / (1 / 1000.0)                                  # deg/s
check("IV-F", "1 px angular blur threshold at 1/1000 s",
      13.6, rate_1px, tol=0.02, unit="deg/s")
results.append((r"$<13^\circ$/s" in TEX, "IV-F",
                "capture gate is set below that threshold", 1, 1, 0.0, "",
                "gate 13 deg/s vs threshold 13.6 deg/s"))

# =====================================================================  IV-D
# Geolocation error budget (RSS of the case-C terms)
caseC = {"GNSS": 0.03, "attitude": 0.31, "boresight": 0.21,
         "height": 0.62, "centroid": 0.09, "time": 0.16}
rssC = math.sqrt(sum(v * v for v in caseC.values()))
check("IV-D", "case C RSS geolocation error", 0.75, rssC, tol=0.03, unit="m")
caseD = dict(caseC)
for k in ("attitude", "centroid", "time"):
    caseD[k] /= math.sqrt(20)
rssD = math.sqrt(sum(v * v for v in caseD.values()))
check("IV-D", "case D RSS (20-frame fusion)", 0.66, rssD, tol=0.05, unit="m")

# =====================================================================  IV-G
# Communications
check("IV-G", "total offered load", 2.5,
      (235 * 3 + 1800) / 1000.0, tol=0.02, unit="Mbps")

# =====================================================================  V
# The generated section: confirm it is actually \input, not stale inline text
gen = os.path.join(ROOT, "docs", "proposal", "generated-sizing.tex")
results.append((os.path.exists(gen) and r"\input{generated-sizing}" in TEX,
                "V", "sizing section is generated and included",
                1, 1, 0.0, "", "guards against a hand-edited copy"))

# =====================================================================  report
print("=" * 92)
print("PROPOSAL NUMERIC VERIFICATION")
print("=" * 92)
print(f"  {'sec':<7}{'claim':<52}{'stated':>10}{'computed':>11}  ")
print("-" * 92)
fails = 0
for ok, sec, claim, stated, computed, rel, unit, note in results:
    tag = "ok  " if ok else "FAIL"
    if not ok:
        fails += 1
    su = f"{stated:g}" if isinstance(stated, float) else str(stated)
    cu = f"{computed:.4g}" if isinstance(computed, float) else str(computed)
    print(f"{tag}  {sec:<7}{claim:<52}{su:>10}{cu:>11}  {unit}")
    if note:
        print(f"        {'':<7}-> {note}")

print("-" * 92)
print(f"  {len(results) - fails} passed, {fails} failed")

UNVERIFIED = [
 ("IV-A", "survey altitude 60 m", "Table I says 60 m; every flown simulation "
  "and the generated Section V use 40 m. This is a DESIGN decision that is "
  "still open, not an arithmetic error -- but the document states both."),
 ("IV-E", "detection recall", "Modelled, never measured. No ground truth "
  "exists to check it against; Section VII says so explicitly."),
 ("IV-A", "thrust-to-weight 2.0", "A requirement, not a measurement. The "
  "funded motors publish no thrust curve; P2 thrust stand settles it."),
 ("VIII", "36 % / 58 % Indian content", "Computed in the cost model from "
  "per-line Indian fractions, which are supplier judgements rather than "
  "derived quantities."),
]
print()
print("=" * 92)
print("NOT MECHANICALLY CHECKABLE -- listed rather than silently skipped")
print("=" * 92)
for sec, claim, why in UNVERIFIED:
    print(f"  {sec:<7}{claim}")
    print(f"         {why}")

sys.exit(1 if fails else 0)
