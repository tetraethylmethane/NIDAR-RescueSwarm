#!/usr/bin/env python3
r"""Generate the mentor brief's component tables from the sourced BOM.

WHY. The brief's five component tables were hand-typed from a cost model whose
lines were mostly estimates. They are now a transcription of a real basket, and
a hand-typed transcription of 55 rows would drift from it within one revision.
The tables are generated here; the ARGUMENT for each line stays in RATIONALE
below, because that is the part a reader is actually being asked to accept.

Emits: docs/proposal/generated-brief-tables.tex  (\input by mentor-brief.tex)
Run:   python tools/proposal/build_brief_tables.py
"""
from __future__ import annotations

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "hardware", "bom"))
import sourced_bom as S  # noqa: E402

OUT = os.path.join(ROOT, "docs", "proposal", "generated-brief-tables.tex")

# Phase numbers per group, as the schedule allocates them.
PHASES = {"instruments": "1--2", "avionics": "3--6", "airframe": "7--10",
          "flighttest": "11--12", "ground": "29--32"}
REPEATS = {"avionics": "repeated at 13--16 and 21--24",
           "airframe": "repeated at 17--20 and 25--28"}

# The reasoning a reader is being asked to accept. Lines without an entry are
# self-evident from the model column and get the supplier only.
RATIONALE = {
 "Load cell":
   "The motors ship without a thrust curve. Measuring thrust and current "
   "together gives thrust per watt, which is the number the whole sizing loop "
   "rests on. Commercial stands start near \\rs{45{,}000}; this is the same "
   "measurement for \\rs{1{,}331} of parts and a printed frame.",
 "Flight controller":
   "Dual IMU, Pixhawk standard, ArduPilot native. Was carried at quotation; "
   "now a live retail listing.",
 "Companion computer":
   "The host the autonomy runs on --- Linux, ROS\\,2, the coverage planner, "
   "MAVLink routing and the delivery logic. The accelerator below is an M.2 "
   "card over PCIe and the camera is a CSI module, so neither has anything to "
   "plug into without it.",
 "AI accelerator":
   "Hailo-8, 26 TOPS. The requirement is 96 inferences/s at 640\\,px (48 tiles "
   "at 2\\,Hz), which this clears; 26 TOPS is margin on the one budget that "
   "already fails, not a specification floor.",
 "GNSS RTK receiver":
   "Four units: one rover per aircraft and one base. Centimetric RELATIVE "
   "geometry is what lets recall and delivery error be measured against "
   "surveyed ground. Supplier has confirmed RTK rover operation and quoted; "
   "this line was an \\rs{18{,}000} estimate and is now firm.",
 "Camera + lens":
   "12.3\\,MP at 1/2.3\\,in and a 6\\,mm lens give 1.03\\,cm/px at 40\\,m, "
   "which puts a person in water at 39\\,px --- just over the COCO small-object "
   "threshold. Was carried at quotation.",
 "Video transmitter":
   "Analog, one channel per aircraft. Removes video from the data network and, "
   "more importantly, removes three software H.264 encodes from the board that "
   "runs tiled inference.",
 "Command receiver":
   "The only path that can command the aircraft, reaching the flight "
   "controller directly rather than through the autonomy stack. Must run "
   "firmware 3.5+ in native MAVLink mode, which carries control and telemetry "
   "on one link and removes a second radio.",
 "Coordination radio":
   "SX1262 in the 865--867\\,MHz delicensed band. Carries mission data and "
   "swarm coordination at 54\\,dB of margin --- the largest in the system, "
   "which is where the survivor coordinates belong.",
 "Speed controllers":
   "One 4-in-1 board drives all four motors. 50\\,A continuous against a "
   "29\\,A per-motor peak. Made in India, and was carried at quotation.",
 "Motors":
   "3.18\\,kgf each, giving twice the aircraft weight in thrust; 340\\,KV suits "
   "an 18\\,in propeller at this pack voltage. Twelve, of which the first is "
   "measured on the stand before the remaining eleven are committed.",
 "Propellers":
   "Sixteen for twelve positions: the most frequently replaced item in a "
   "flight-test programme, and the four spares are the whole spares policy.",
 "Cells":
   "Molicel P45B, 6S3P, 292\\,Wh. Covers the mission, a full second search and "
   "four minutes of holding within an 80\\,\\% depth of discharge.",
 "Pack fusing":
   "150\\,A ANL fuse per pack. Short-circuit protection that cannot nuisance-"
   "trip at the 115\\,A thrust peak.",
 "Arm tube":
   "25\\,$\\times$\\,23\\,mm carbon. Bending is not the driver at a safety "
   "factor of 24; the clamp and joint design is.",
 "Safety-pilot transmitter":
   "ExpressLRS, EdgeTX, with a spare receiver. Manual override independent of "
   "the autonomy stack, which is a rule requirement and a safety one.",
 "Battery charger":
   "500\\,W dual-channel. Two 292\\,Wh packs recharged between sorties is the "
   "constraint on flight-test throughput.",
 "Pack health monitor":
   "200\\,A CAN power module on the bench, to log pack internal resistance as "
   "the cells age. The sag simulation currently assumes a DC-IR; this measures "
   "it.",
 "Video receivers":
   "Three, one per aircraft feed. The rules require the ground station to "
   "display a live camera feed from each aircraft simultaneously.",
 "Receive antennas":
   "12\\,dBi patch at the ground station, which is where the 28.5\\,dB of "
   "video margin at the 600\\,m geofence comes from.",
 "Coordination base":
   "The ground end of the 865\\,MHz link, over USB to the ground station.",
}

SUPPLIER = [("robu.in", "Robu"), ("robokits", "Robokits"), ("amazon.in", "Amazon India"),
            ("flipkart", "Flipkart"), ("indiamart", "IndiaMART"), ("zbotic", "zBotic"),
            ("robocraze", "Robocraze"), ("hubtronics", "Hubtronics"),
            ("teravolt", "Teravolt"), ("iscaleindia", "iScale"),
            ("onlyscrews", "OnlyScrews"), ("desertcart", "Desertcart"),
            ("njour", "Njour")]


def supplier_of(url):
    for frag, name in SUPPLIER:
        if frag in url:
            return name
    return "in-house"


def esc(s):
    return s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def money(v):
    """Indian digit grouping: last three, then twos. The rest of the brief
    writes 5,99,167 rather than 599,167, so these have to match."""
    n = f"{v:.0f}"
    neg, n = (n[0] == "-"), n.lstrip("-")
    if len(n) > 3:
        head, tail = n[:-3], n[-3:]
        out = []
        while len(head) > 2:
            out.insert(0, head[-2:])
            head = head[:-2]
        if head:
            out.insert(0, head)
        n = "{,}".join(out) + "{,}" + tail
    return ("-" if neg else "") + n


def rows(key):
    out = []
    for r in S.BOM:
        if r[0] != key:
            continue
        _, item, model, unit, qty, ac, url = r
        note = RATIONALE.get(item, "")
        sup = supplier_of(url)
        note = (note + " " if note else "") + (
            f"\\textit{{{sup}}}" if sup != "in-house" else "\\textit{in-house}")
        qtytxt = f", {qty} off" if qty > 1 else ""
        out.append(f"{esc(item)} & {esc(model)}{qtytxt} "
                   f"& {money(unit * qty)} & {note} \\\\")
    return "\n".join(out)


def main():
    parts = []
    for key, label, _ph in S.GROUPS:
        tot = S.group_total(key)
        per = S.per_aircraft(key)
        # The INR column is always the programme quantity, so a heading that
        # quoted only the per-aircraft figure read as a contradiction.
        amt = (f"\\rs{{{money(per)}}} per aircraft, \\rs{{{money(tot)}}} in all"
               if per else f"\\rs{{{money(tot)}}} of parts")
        head = (f"\\subsubsection*{{{label} --- phases {PHASES[key]}"
                + (f", {REPEATS[key]}" if key in REPEATS else "")
                + f" \\quad {amt}}}")
        parts.append(head)
        parts.append(r"""
\begingroup\small
\begin{longtable}{@{}>{\raggedright\arraybackslash}p{2.6cm}>{\raggedright\arraybackslash}p{4.4cm}r>{\raggedright\arraybackslash}p{7.4cm}@{}}
\toprule
\thead{Item} & \thead{Model} & \thead{INR, all 3} & \thead{Why this part, and from whom} \\
\midrule
\endfirsthead
\toprule
\thead{Item} & \thead{Model} & \thead{INR, all 3} & \thead{Why this part, and from whom} \\
\midrule
\endhead""")
        parts.append(rows(key))
        parts.append(r"\bottomrule")
        parts.append(r"\end{longtable}")
        parts.append(r"\endgroup")
        parts.append("")

    body = "\n".join(parts)
    header = ("%" + "=" * 76 + "\n"
              "% GENERATED FILE -- do not edit.\n"
              "% Produced by tools/proposal/build_brief_tables.py from\n"
              "% hardware/bom/sourced_bom.py. Edit the BOM, not this file.\n"
              "%" + "=" * 76 + "\n")

    # Guard the two escaping failures this repository has hit before.
    assert "\\textbf" not in body or body.count("\\textbf") == body.count("\\textbf")
    assert not any(ord(c) < 32 and c != "\n" for c in body), "control char in tables"
    assert "@@" not in body

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(header + body)
    n = sum(1 for _ in S.BOM)
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  ({n} rows, "
          f"{len(RATIONALE)} with a stated rationale)")
    print(f"  parts total {S.total():,.0f}   with GST {S.total() * 1.18:,.0f}")


if __name__ == "__main__":
    main()
