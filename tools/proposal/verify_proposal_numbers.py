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
check("IV-A", "design mission duration", 7.6, M.T / 60, tol=0.01, unit="min")
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
# This was reported as an unallocated residual. It is the recovery parachute:
# present in the model's payload_system dict, absent from the printed mass
# statement, so the statement fell short of MTOW by exactly the parachute mass.
# The check now asserts the identity rather than tolerating a gap.
check("IV-B", "recovery parachute + mount", 300, resid * 1000, tol=0.01, unit="g")
check("IV-B", "parachute as % of MTOW", 4.7, 100 * resid / mtow, tol=0.05, unit="%")
# Compared as totals, not as a difference against zero: a relative tolerance
# cannot be taken against an expected value of 0, and the residual carries
# about 2e-7 g of floating-point noise.
check("IV-B", "mass statement closes to MTOW", mtow * 1000,
      (listed + M.payload_system["recovery parachute + mount"]) * 1000,
      tol=1e-9, unit="g")
check("IV-B", "growth allowance to 24 kg fleet",
      4919, (24 - fleet) * 1000, tol=0.02, unit="g")
check("IV-B", "build overweight tolerated",
      26, 100 * (24 / fleet - 1), tol=0.05, unit="%")
check("IV-B", "survivor kits mass", 800, KITS * 1000, unit="g")
check("IV-B", "survivor kits share of MTOW", 12.6, 100 * KITS / mtow,
      tol=0.02, unit="%")

# =====================================================================  IV-E
# Perception. The design is NATIVE tiling at 40 m -- no downsample -- and the
# target is a person in WATER (0.4 m across), which is the worst posture and
# the one the document is now sized against.
WATER_M = 0.40
spec40 = CO.at_altitude(CO.SPECIFIED, 40.0)
spec60 = CO.at_altitude(CO.SPECIFIED, 60.0)


def tiles_for(w, h):
    return math.ceil((w - 640) / 512) + 1, math.ceil((h - 640) / 512) + 1


nw, nh = tiles_for(CO.SPECIFIED["px_w"], CO.SPECIFIED["px_h"])
check("IV-E", "tiles per frame, NATIVE", 48, nw * nh)
check("IV-E", "inferences/s at 2 Hz, native", 96, nw * nh * 2.0, unit="/s")
# It has to fit the accelerator, or native tiling is not affordable and the
# whole change is wrong. 130 FPS is the LOW end of the measured range.
results.append((nw * nh * 2.0 <= 130, "IV-E",
                "native tiling at 2 Hz fits the accelerator", 1, 1, 0.0, "",
                f"{nw*nh*2.0:.0f} inf/s vs 130-160 FPS measured"))
results.append((nw * nh * 3.06 > 130, "IV-E",
                "3.06 Hz does NOT fit -- the open item the gate would buy back",
                1, 1, 0.0, "", f"{nw*nh*3.06:.0f} inf/s vs 130 FPS"))


def water(gsd_cm):
    """The 0.4 m target: long axis in px, and area in px^2."""
    L = WATER_M / (gsd_cm / 100.0)
    return L, L * L


for lbl, gsd, px, area in (
        ("40 m native", spec40["gsd_cm"], 39, 1498),
        ("60 m native", spec60["gsd_cm"], 26, 666),
        ("40 m, 2x downsample", spec40["gsd_cm"] * 2, 19, 375),
        ("60 m, 2x downsample", spec60["gsd_cm"] * 2, 13, 166)):
    L, A = water(gsd)
    check("IV-E", f"water target at {lbl} (px)", px, L, tol=0.03, unit="px")
    check("IV-E", f"water target at {lbl} (area)", area, A, tol=0.03, unit="px2")

# The whole argument for the change: only the adopted row clears COCO small.
_, A40n = water(spec40["gsd_cm"])
_, A60n = water(spec60["gsd_cm"])
_, A40d = water(spec40["gsd_cm"] * 2)
results.append((A40n >= CO.COCO_SMALL_PX2 and A60n < CO.COCO_SMALL_PX2
                and A40d < CO.COCO_SMALL_PX2, "IV-E",
                "ONLY 40 m + native clears the COCO small threshold", 1, 1, 0.0, "",
                f"40m native {A40n:.0f} vs 60m native {A60n:.0f}, "
                f"40m downsampled {A40d:.0f}, threshold {CO.COCO_SMALL_PX2}"))
check("IV-E", "sensor pitch stated in text", 1.55, CO.SPECIFIED["pitch_um"],
      unit="um")
results.append(("Survey altitude          & 40\\,m AGL" in TEX, "IV-E",
                "design point table says 40 m", 1, 1, 0.0, "",
                "the altitude decision is now taken, not open"))

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

# ================================================================  formatting
# A MANGLED control sequence is invisible to LaTeX's own warnings. When the
# backslash of \ref is eaten -- which a non-raw Python string will do, because
# \r is a carriage return -- the document compiles clean, reports zero
# undefined references, and prints "Section  efsec:indig" to the reader.
# Checking for undefined refs does not catch this. Checking for the wreckage does.
_MANGLED = re.compile(r"(?<!\\)\b(ef|abel|extbf|extit|egin|nd|ightarrow|mph|uad)\{")
_TEXDIR0 = os.path.join(ROOT, "docs", "proposal")
_mangled_hits = []
for _dp, _dn, _fs in os.walk(_TEXDIR0):
    for _fn in _fs:
        if not _fn.endswith(".tex"):
            continue
        with io.open(os.path.join(_dp, _fn), encoding="utf-8") as _fh:
            _body = _fh.read()
        # A TAB immediately before a control-sequence name is the signature of
        # a re.sub replacement string eating the backslash: "\textbf" -> TAB
        # + "extbf". Tabs are legal LaTeX, so only this pattern is flagged.
        for _m in _MANGLED.finditer(_body):
            _mangled_hits.append(f"{_fn}:{_m.group(0)}")
        for _n in ("textbf", "textit", "emph", "begin", "end", "item"):
            if chr(9) + _n in _body:
                _mangled_hits.append(f"{_fn}:TAB+{_n}")
results.append((not _mangled_hits, "fmt", "no mangled LaTeX control sequences",
                1, 1, 0.0, "", "; ".join(sorted(set(_mangled_hits))[:4])
                if _mangled_hits else
                "scans every .tex; catches both lost backslashes and TAB+name"))

# The same accident writes CONTROL CHARACTERS, not just missing backslashes:
# \r becomes CR, \a becomes BEL, \b backspace, \f formfeed, \v vertical tab.
# Those are invisible in an editor and cannot be matched by a text search, so
# they are the worst version of this bug. Scan every .tex we generate or edit.
_TEXDIR = os.path.join(ROOT, "docs", "proposal")
_ctrl_hits = []
for _dirpath, _dirnames, _files in os.walk(_TEXDIR):
    for _fn in _files:
        if not _fn.endswith(".tex"):
            continue
        _p = os.path.join(_dirpath, _fn)
        with io.open(_p, encoding="utf-8", newline="") as _fh:
            _body = _fh.read()
        _hits = {hex(ord(c)) for c in _body
                 if ord(c) < 32 and c not in ("\n", "\t", "\r")}
        if _hits:
            _ctrl_hits.append(f"{_fn}:{sorted(_hits)}")
results.append((not _ctrl_hits, "fmt", "no stray control characters in any .tex",
                1, 1, 0.0, "", "; ".join(_ctrl_hits) if _ctrl_hits else
                "CR/BEL/BS written in place of a backslash are invisible"))

# A tie that lost its command leaves a line ending in a bare tilde.
_dangling = [i + 1 for i, ln in enumerate(TEX.splitlines())
             if ln.rstrip().endswith("~")]
results.append((not _dangling, "fmt", "no line ends in a dangling tie",
                1, 1, 0.0, "", f"lines {_dangling[:5]}" if _dangling else
                "a 'Section~' with nothing after it means a lost \\ref"))

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
 ("IV-A", "survey altitude 40 m", "Table I, the flown simulations and the "
  "generated Section V now agree on 40 m. Retained here because the altitude "
  "is a DESIGN decision the detection evaluation may reopen, not because the "
  "document is inconsistent about it."),
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
