#!/usr/bin/env python3
r"""Generate the printable BOM (LaTeX -> PDF) from sourced_bom.py.

WHY GENERATED. A hand-typed BOM document disagrees with the BOM it copies
within one revision. Every line, quantity, price and total here is read from
sourced_bom.py, and the totals are asserted against it before anything is
written. The only hand-written text is the short architecture summary and the
open items, which are decisions rather than numbers.

Emits: hardware/bom/rescueswarm-bom.tex (and .pdf, if pdflatex is on PATH)
Run:   python hardware/bom/build_bom_pdf.py
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "proposal"))
import sourced_bom as S                                    # noqa: E402
from build_brief_tables import money, supplier_of          # noqa: E402

OUT = os.path.join(HERE, "rescueswarm-bom.tex")
REVISION = "2026-09-19"

GROUP_TITLE = {
    "instruments": "Test instruments",
    "avionics":    "Avionics, sensing and RTK",
    "airframe":    "Airframe, propulsion and power",
    "flighttest":  "Flight-test support",
    "ground":      "Ground station",
}

# Decisions, not numbers -- the one part of this document that is hand-written.
ARCHITECTURE = [
    ("Flight controller", "Holybro Kakute H7 V1.5 (ArduPilot), stacked on a 4-in-1 ESC"),
    ("Companion", "Raspberry Pi 5 4 GB + AI HAT+ 26 TOPS; Arducam 12.3 MP, 6 mm lens"),
    ("Positioning", "ZED-F9P RTK on every aircraft (GenX F9P Air, compass built in); "
                    "local F9P base, RTCM over E22 LoRa, no NTRIP"),
    ("Video", "Digital, wfb-ng on Pi OS (BL-M8812EU2), CV overlay on the feed; "
              "one ground receiver per aircraft"),
    ("Links", "ELRS 2.4 GHz safety pilot (TX12 MKII); E22 868 MHz primarily for RTCM"),
    ("Power", "6S 16 Ah HV LiPo; ESC current sensor to FC; 8 A UBEC for Pi, "
              "3 A UBEC for video radio, separate servo UBEC"),
]

# Model results behind the battery choice (sourced_bom.py carries the table).
BATTERY_TABLE = [
    # pack, mass g, Wh, MTOW kg, T/W, endurance x mission, landing-queue reserve Wh
    ("Li-ion 6S3P (previous)", "1449", "292", "6.36", "2.00", "2.02", "+1.1"),
    ("LiPo 12 Ah", "1424", "266", "6.34", "2.01", r"1.85 \textbf{fail}", r"$-$3.7 \textbf{fail}"),
    ("LiPo 13 Ah", r"$\sim$1519", "289", "6.43", "1.98", r"1.96 \textbf{fail}", r"$-$0.5 \textbf{fail}"),
    ("LiPo 14 Ah", r"$\sim$1636", "311", "6.55", "1.94", "2.06", "+2.5"),
    (r"\textbf{LiPo 16 Ah HV (chosen)}", "1880--2211", "365", "6.8--7.1",
     "1.8--1.9", "2.1--2.3", "+5 to +9"),
]

OPEN_ITEMS = [
    r"\textbf{Battery: weigh it.} GenX publishes no mass; 1880--2211\,g is "
    r"bracketed from 165--194\,Wh/kg. The cost of 16\,Ah is thrust-to-weight: "
    r"1.8--1.9 on the same motors unless the stand shows $\geq$\,3.55\,kgf per "
    r"motor. Charge it as LiHV. Its AS150 plug needs AS150 mates, not XT90S. The "
    r"150\,A fuse is now the tightest margin against a $\sim$136\,A peak.",
    r"\textbf{Failsafe parameters.} \texttt{params.py} and the pack model still "
    r"describe the Li-ion pack. Once the LiPo arrives, measure its sag curve, then "
    r"update both. Do not fly before that.",
    r"\textbf{ESC.} The 65\,A is a candidate. It is confirmed on the thrust stand for "
    r"current, temperature and desync with 18\,in props and 340\,KV motors.",
    r"\textbf{Base antenna cable.} The LS-125-A has a TNC connector. The U.FL$\to$SMA "
    r"pigtail needs a TNC-male to SMA-male RG58 cable (3--5\,m) to the tripod. "
    r"No Indian listing with a price was found, so it is not yet a line.",
    r"\textbf{Ground directional antenna.} Still open: no Indian listing was found. "
    r"The omnis are the placeholder. Also check the USB hub adapter's rating when "
    r"it arrives.",
    r"\textbf{Confirmed:} the GenX F9P Air is dual-band (GPS L1/L2, Galileo E1/E5b, "
    r"BDS B1/B2, GLONASS G1/G2), with a QMC5883 compass.",
]


def tex(s: str) -> str:
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("_", r"\_"), ("#", r"\#"), ("$", r"\$"), ("~", r"$\sim$")):
        s = s.replace(a, b)
    return s


def url(u: str) -> str:
    return u.replace("%", r"\%").replace("#", r"\#").replace("~", r"\~{}")


def rs(v: float) -> str:
    return money(v)


def group_rows(key):
    rows, n = [], 0
    for r in S.BOM:
        if r[0] != key:
            continue
        n += 1
        _, item, model, unit, qty, ac, link = r
        sup = supplier_of(link) if link else "local"
        if sup == "in-house":
            sup = "local"
        src = rf"\href{{{url(link)}}}{{{sup}}}" if link else sup
        acq = str(ac) if ac else "--"
        rows.append(rf"{tex(item)} & {tex(model)} & {acq} & {qty} & "
                    rf"{rs(unit)} & {rs(unit * qty)} & {src} \\")
    return rows, n


def main():
    total = S.total()
    released = sum(S.phase_released().values())
    per_ac = sum(r[3] * r[5] for r in S.BOM)
    ex = sum(S.line_total(r) for r in S.BOM if S.is_ex_gst(r[6]))
    assert abs(sum(S.group_total(k) for k in GROUP_TITLE) - total) < 0.01
    assert abs(released - S.released(total - ex, ex)) < 1.0, "phase sum disagrees"

    body = []
    for key in GROUP_TITLE:
        rows, n = group_rows(key)
        body.append(rf"\grouphead{{{GROUP_TITLE[key]}}}{{{rs(S.group_total(key))}}}")
        body.extend(rows)
    lines = len(S.BOM)

    arch = "\n".join(rf"\textbf{{{a}}} & {b} \\" for a, b in ARCHITECTURE)
    opens = "\n".join(rf"\item {t}" for t in OPEN_ITEMS)
    batt = "\n".join(" & ".join(r) + r" \\" for r in BATTERY_TABLE)
    summary = "\n".join(
        rf"{GROUP_TITLE[k]} & {sum(1 for r in S.BOM if r[0] == k)} & "
        rf"{rs(S.per_aircraft(k)) if S.per_aircraft(k) else '--'} & "
        rf"{rs(S.group_total(k))} \\" for k in GROUP_TITLE)

    doc = rf"""%{'=' * 76}
% GENERATED FILE -- do not edit.
% Produced by hardware/bom/build_bom_pdf.py from hardware/bom/sourced_bom.py.
%{'=' * 76}
\documentclass[10pt,a4paper]{{article}}
\usepackage[T1]{{fontenc}}
\usepackage[scaled=0.92]{{helvet}}
\renewcommand{{\familydefault}}{{\sfdefault}}
\usepackage[margin=14mm,top=16mm,bottom=18mm]{{geometry}}
\usepackage{{booktabs,longtable,array,tabularx}}
\usepackage{{xcolor}}
\usepackage{{enumitem}}
\usepackage{{fancyhdr,lastpage}}
\usepackage[hidelinks]{{hyperref}}
\definecolor{{accent}}{{HTML}}{{1F4E79}}
\newcolumntype{{L}}[1]{{>{{\raggedright\arraybackslash}}p{{#1}}}}
\newcolumntype{{R}}[1]{{>{{\raggedleft\arraybackslash}}p{{#1}}}}
\newcommand{{\grouphead}}[2]{{\multicolumn{{5}}{{@{{}}l}}{{\rule{{0pt}}{{13pt}}\textbf{{\color{{accent}}#1}}}} & \multicolumn{{2}}{{r@{{}}}}{{\textbf{{\color{{accent}}#2}}}} \\ \cmidrule{{1-7}}}}
\pagestyle{{fancy}}\fancyhf{{}}
\renewcommand{{\headrulewidth}}{{0pt}}
\fancyfoot[L]{{\footnotesize NIDAR RescueSwarm --- Bill of Materials, rev.\ {REVISION}}}
\fancyfoot[R]{{\footnotesize \thepage\ / \pageref{{LastPage}}}}
\setlength{{\parindent}}{{0pt}}

\begin{{document}}

{{\LARGE\bfseries\color{{accent}} NIDAR RescueSwarm --- Bill of Materials}}\\[2pt]
{{\large Three-aircraft programme \quad$\cdot$\quad Revision {REVISION} \quad$\cdot$\quad all prices INR}}

\vspace{{8pt}}
\begin{{tabularx}}{{\textwidth}}{{@{{}}Xr@{{\hspace{{18pt}}}}Xr@{{}}}}
\toprule
Parts, three aircraft & \textbf{{{rs(total)}}} & Parts per aircraft & \textbf{{{rs(per_ac)}}} \\
Released (tax where owed $+$ {S.CONTINGENCY * 100:.0f}\,\% contingency) & \textbf{{{rs(released)}}} & Line items & \textbf{{{lines}}} \\
\bottomrule
\end{{tabularx}}

\vspace{{10pt}}
{{\large\bfseries\color{{accent}} Architecture}}\\[3pt]
\begin{{tabularx}}{{\textwidth}}{{@{{}}L{{3.0cm}}X@{{}}}}
{arch}
\end{{tabularx}}

\vspace{{10pt}}
{{\large\bfseries\color{{accent}} Summary by group}}\\[3pt]
\begin{{tabularx}}{{\textwidth}}{{@{{}}XR{{1.4cm}}R{{2.6cm}}R{{2.6cm}}@{{}}}}
\toprule
\textbf{{Group}} & \textbf{{Lines}} & \textbf{{Per aircraft}} & \textbf{{Programme}} \\
\midrule
{summary}
\midrule
\textbf{{Total parts}} & \textbf{{{lines}}} & \textbf{{{rs(per_ac)}}} & \textbf{{{rs(total)}}} \\
\bottomrule
\end{{tabularx}}

\vspace{{10pt}}
{{\large\bfseries\color{{accent}} Line items}}\\[3pt]
{{\footnotesize
\setlength{{\tabcolsep}}{{3.5pt}}
\begin{{longtable}}{{@{{}}L{{2.9cm}}L{{6.2cm}}R{{0.7cm}}R{{0.8cm}}R{{1.4cm}}R{{1.6cm}}L{{2.6cm}}@{{}}}}
\toprule
\textbf{{Item}} & \textbf{{Part}} & \textbf{{/AC}} & \textbf{{Qty}} & \textbf{{Unit}} & \textbf{{Total}} & \textbf{{Source}} \\
\midrule
\endfirsthead
\toprule
\textbf{{Item}} & \textbf{{Part}} & \textbf{{/AC}} & \textbf{{Qty}} & \textbf{{Unit}} & \textbf{{Total}} & \textbf{{Source}} \\
\midrule
\endhead
\midrule \multicolumn{{7}}{{r@{{}}}}{{\emph{{continued}}}} \\
\endfoot
\bottomrule
\endlastfoot
{chr(10).join(body)}
\midrule
\multicolumn{{5}}{{@{{}}l}}{{\textbf{{Total parts, three aircraft}}}} & \multicolumn{{2}}{{r@{{}}}}{{\textbf{{{rs(total)}}}}} \\
\end{{longtable}}}}

{{\footnotesize \textit{{/AC}} = fitted per aircraft (-- = bought once for the programme).
\textit{{Qty}} = programme quantity, including spares. Retail listings are
GST-inclusive; GST is added only to quotation and B2B lines
({rs(ex)} of parts). Every source name links to the listing the price came from.}}

\vspace{{10pt}}
{{\large\bfseries\color{{accent}} Battery selection}}\\[3pt]
{{\footnotesize Each pack was run through the sizing model at its own mass,
with the motors fixed. \emph{{Endurance}} is hover time over mission time, and
the policy needs $\geq$\,2.0. \emph{{Queue}} is the 20\,\% reserve left after the
third aircraft's 120\,s hold plus two 53\,s descents.}}\\[3pt]
{{\footnotesize
\begin{{tabularx}}{{\textwidth}}{{@{{}}XR{{1.7cm}}R{{0.9cm}}R{{1.5cm}}R{{1.3cm}}R{{2.2cm}}R{{2.3cm}}@{{}}}}
\toprule
\textbf{{Pack}} & \textbf{{Mass, g}} & \textbf{{Wh}} & \textbf{{MTOW, kg}} & \textbf{{T/W}} & \textbf{{Endurance, $\times$}} & \textbf{{Queue, Wh}} \\
\midrule
{batt}
\bottomrule
\end{{tabularx}}}}

\vspace{{10pt}}
{{\large\bfseries\color{{accent}} Open before ordering}}
\begin{{itemize}}[leftmargin=14pt,itemsep=2pt,topsep=3pt]
{opens}
\end{{itemize}}

\end{{document}}
"""
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(doc)
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  ({lines} lines, parts {total:,.0f}, "
          f"released {released:,.0f})")

    if shutil.which("pdflatex"):
        for _ in range(2):          # second pass resolves the page count
            r = subprocess.run(["pdflatex", "-interaction=nonstopmode",
                                "-halt-on-error", os.path.basename(OUT)],
                               cwd=HERE, capture_output=True, text=True)
            if r.returncode:
                sys.exit(r.stdout[-3000:])
        for ext in (".aux", ".log", ".out"):
            p = OUT[:-4] + ext
            if os.path.exists(p):
                os.remove(p)
        print(f"  wrote {os.path.relpath(OUT[:-4] + '.pdf', ROOT)}")


if __name__ == "__main__":
    main()
