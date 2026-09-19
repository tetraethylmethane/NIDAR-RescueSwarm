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
    ("Power", "6S LiPo; ESC current sensor to FC; 8 A UBEC for Pi, "
              "3 A UBEC for video radio, separate servo UBEC"),
]

OPEN_ITEMS = [
    r"\textbf{LiPo capacity.} The 12\,Ah pack is a placeholder. The landing-queue "
    r"reserve needs $\geq$\,287\,Wh ($\approx$\,13\,Ah at 6S), which it misses. "
    r"Size the pack from the final AUW and hover current.",
    r"\textbf{Failsafe parameters.} \texttt{params.py} and the pack model still "
    r"describe the Li-ion pack. Update them with the LiPo, and before flying it.",
    r"\textbf{ESC.} 65\,A vs 50\,A is decided on the thrust stand: desync, current "
    r"and temperature on 18\,in props with 340\,KV motors.",
    r"\textbf{Confirm in the cart:} the GenX F9P Air's bands (L1/L2), the LiPo's "
    r"capacity (10 vs 12\,Ah on the listing), and the survey antenna's connector.",
    r"\textbf{Not yet in this BOM:} the ground directional antenna and a powered "
    r"USB hub for the three video receivers.",
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
