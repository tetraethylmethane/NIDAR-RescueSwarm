#!/usr/bin/env python3
r"""Generate the Bill of Materials submitted to the faculty mentors (LaTeX -> PDF).

WHY GENERATED. A hand-typed BOM document disagrees with the BOM it copies
within one revision. Every line, quantity, price and total here is read from
sourced_bom.py, and the mentors, team and submitter are read from the approval
letter generator, so this document cannot disagree with either. The cost
breakdown is recomputed from its parts and asserted against the phase
schedule's total before anything is written.

The hand-written parts are decisions, not numbers: the system configuration
and the battery-selection table (model results).

With --single it emits the one-aircraft variant that accompanies
mentor-brief-single: the same lines at the quantities build_single_brief.py
derives, asserted against that brief's phase schedule instead.

Emits: hardware/bom/rescueswarm-bom.tex (and .pdf, if pdflatex is on PATH)
       hardware/bom/rescueswarm-bom-single.tex (and .pdf) with --single
Run:   python hardware/bom/build_bom_pdf.py [--single]
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
import build_approval_letters as L                         # noqa: E402

OUT_FULL = os.path.join(HERE, "rescueswarm-bom.tex")
OUT_SINGLE = os.path.join(HERE, "rescueswarm-bom-single.tex")
DATE = "21 September 2026"

GROUP_TITLE = {
    "instruments": "Test instruments",
    "avionics":    "Avionics, sensing and RTK positioning",
    "airframe":    "Airframe, propulsion and power",
    "flighttest":  "Flight-test support",
    "ground":      "Ground station",
}

CONFIG = [
    ("Airframe", "Quadrotor, 18\\,in carbon propellers, Tarot 5008 340\\,KV motors, "
                 "carbon-tube arms; about 7\\,kg take-off mass with four relief kits"),
    ("Flight control", "Holybro Kakute H7 V1.5 running ArduPilot, stacked on a "
                       "4-in-1 65\\,A speed controller"),
    ("Onboard computing", "Raspberry Pi 5 (4\\,GB) with AI HAT+ (26\\,TOPS) for "
                          "person detection; 12.3\\,MP camera, 6\\,mm lens"),
    ("Positioning", "Centimetre-level RTK on every aircraft (ZED-F9P, dual-band, "
                    "with compass); own ground base station, so no internet is needed"),
    ("Video", "Digital downlink (wfb-ng) carrying the camera feed with detections "
              "drawn on; one directional ground receiver per aircraft"),
    ("Links", "2.4\\,GHz ExpressLRS for the safety pilot; 868\\,MHz LoRa for RTK "
              "corrections"),
    ("Power", "6S 16\\,Ah LiHV lithium-polymer pack, charged on the LiHV profile "
              "(4.35\\,V per cell); AS150 connectors; separate regulators for the "
              "computer, the video radio and the servos"),
]

# Model results behind the battery choice. sourced_bom.py carries the same table.
BATTERY_TABLE = [
    ("Li-ion 6S3P, in-house (previous)", "1.45", "292", "6.36", "2.00", "2.02", "+1.1"),
    ("LiPo 12\\,Ah", "1.42", "266", "6.34", "2.01", "1.85$^\\ast$", "$-$3.7$^\\ast$"),
    ("LiPo 13\\,Ah", "1.52", "289", "6.43", "1.98", "1.96$^\\ast$", "$-$0.5$^\\ast$"),
    ("LiPo 14\\,Ah", "1.64", "311", "6.55", "1.94", "2.06", "+2.5"),
    ("\\textbf{LiPo 16\\,Ah LiHV (selected)}", "\\textbf{1.88--2.21}", "\\textbf{365}",
     "\\textbf{6.8--7.1}", "\\textbf{1.8--1.9}", "\\textbf{2.1--2.3}", "\\textbf{+5 to +9}"),
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


def bom_rows(items):
    out, n = [], 0
    for key, title in GROUP_TITLE.items():
        gt = sum(r[3] * q for r, q in items if r[0] == key)
        out.append(rf"\grouphead{{{title}}}{{{rs(gt)}}}")
        for r, qty in items:
            if r[0] != key:
                continue
            n += 1
            _, item, model, unit, _qty, ac, link = r
            if link:
                sup = supplier_of(link)
                src = rf"\href{{{url(link)}}}{{{sup}}}"
            else:
                src = r"Estimate$^\dagger$"
            acq = str(ac) if ac else "--"
            out.append(rf"{n} & {tex(item)} & {tex(model)} & {acq} & {qty} & "
                       rf"{rs(unit)} & {rs(unit * qty)} & {src} \\")
    return "\n".join(out), n


TEMPLATE = r"""%=============================================================================
% GENERATED FILE -- do not edit.
% Produced by hardware/bom/build_bom_pdf.py from hardware/bom/sourced_bom.py.
%=============================================================================
\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage[margin=19mm,top=22mm,bottom=22mm]{geometry}
\usepackage{array,booktabs,longtable,tabularx}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage{graphicx}
\usepackage{microtype}
\usepackage{titlesec}
\usepackage{fancyhdr,lastpage}
\usepackage[hidelinks]{hyperref}
\graphicspath{{../../docs/proposal/images/}}
\newcommand{\rs}[1]{\mbox{INR~#1}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}
\newcommand{\grouphead}[2]{\multicolumn{6}{@{}l}{\rule{0pt}{12pt}\textbf{#1}} & \multicolumn{2}{r@{}}{\textbf{#2}} \\ \cmidrule{1-8}}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.45em}
\titleformat{\section}{\large\bfseries}{\thesection.}{0.6em}{}
\titlespacing*{\section}{0pt}{12pt}{4pt}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{\small RescueSwarm --- Bill of Materials}
\fancyhead[R]{\small @@DATE@@}
\fancyfoot[C]{\small Page \thepage\ of \pageref{LastPage}}
\renewcommand{\headrulewidth}{0.4pt}
\fancypagestyle{plain}{\fancyhf{}\renewcommand{\headrulewidth}{0pt}\fancyfoot[C]{\small Page \thepage\ of \pageref{LastPage}}}

\begin{document}
\thispagestyle{plain}

\noindent
\raisebox{-0.5\height}{\includegraphics[height=16mm]{brainwave.pdf}}%
\hfill
\raisebox{-0.5\height}{\includegraphics[height=15mm]{thapar_logo.png}}

\vspace{3mm}\hrule\vspace{5mm}

\begin{center}
{\LARGE\bfseries Bill of Materials}\\[2mm]
{\large RescueSwarm: @@TITLE@@ for\\
Post-Disaster Search, Localisation and Payload Delivery}\\[3mm]
{\normalsize @@SCOPE@@ \quad$\cdot$\quad @@DATE@@}
\end{center}

\vspace{1mm}\hrule\vspace{4mm}

\noindent
\begin{tabularx}{\textwidth}{@{}L{3.2cm}X@{}}
\textbf{Submitted to} & @@MENTORS@@, Faculty Mentors \\
\textbf{Submitted by} & @@SUBMITTER@@, on behalf of the RescueSwarm team \\
\textbf{Accompanies} & @@BRIEFNAME@@ and its phase-wise approval letters \\
\end{tabularx}

\section{Purpose}

This document lists every component needed to build, test and operate
@@WHAT@@ and @@GSPOSS@@ ground station, with quantities, unit
prices and the supplier each price was taken from. Every price is from a dated
Indian listing, and each supplier name in Section~\ref{sec:bom} links to it,
except the consumables, which are a marked allowance. The totals are the same as
those in @@BRIEFREF@@ and the approval letters, because all three are
generated from one parts list.

\section{Cost summary}

\begin{center}
\begin{tabular}{@{}lr@{}}
\toprule
Parts at retail, GST already included (@@NINCL@@ lines) & @@INCL@@ \\
Parts quoted before GST, and estimates (@@NEX@@ lines) & @@EX@@ \\
\midrule
\textbf{Parts total, @@SCOPESHORT@@ (@@LINES@@ lines)} & \textbf{@@TOTAL@@} \\
GST at 18\,\% on the pre-GST lines only & @@GST@@ \\
Contingency, 15\,\% & @@CONT@@ \\
\midrule
\textbf{Total requested} & \textbf{\rs{@@REQ@@}} \\
\bottomrule
\end{tabular}
\end{center}

@@PERACTEXT@@ The request is
released in @@NPHASES@@ phases, each only after the previous one has produced its
result. The first release is \rs{@@PH1@@}, and nothing above \rs{26{,}000} is
spent until a motor has been measured on the thrust stand.@@NEXTSTEP@@

\begin{center}
\small
\begin{tabular}{@{}l@@GROUPCOLS@@@{}}
\toprule
@@GROUPHEAD@@
\midrule
@@GROUPS@@
\midrule
@@GROUPTOTAL@@
\bottomrule
\end{tabular}
\end{center}

\section{System configuration}

\noindent
\begin{tabularx}{\textwidth}{@{}L{3.2cm}X@{}}
\toprule
@@CONFIG@@
\bottomrule
\end{tabularx}

\section{Bill of materials}\label{sec:bom}

All prices are in INR. \emph{Per AC} is the number fitted to one aircraft; a
dash means the item is bought once for the whole @@ONCEFOR@@. \emph{Qty} is
@@QTYNOTE@@

{\footnotesize
\setlength{\tabcolsep}{3pt}
\begin{longtable}{@{}R{0.45cm}L{2.7cm}L{5.55cm}R{0.85cm}R{0.6cm}R{1.2cm}R{1.35cm}L{2.2cm}@{}}
\toprule
\textbf{\#} & \textbf{Item} & \textbf{Part} & \textbf{Per AC} & \textbf{Qty} & \textbf{Unit} & \textbf{Amount} & \textbf{Source} \\
\midrule
\endfirsthead
\toprule
\textbf{\#} & \textbf{Item} & \textbf{Part} & \textbf{Per AC} & \textbf{Qty} & \textbf{Unit} & \textbf{Amount} & \textbf{Source} \\
\midrule
\endhead
\midrule \multicolumn{8}{r@{}}{\emph{continued on next page}} \\
\endfoot
\bottomrule
\endlastfoot
@@ROWS@@
\midrule
\multicolumn{6}{@{}l}{\textbf{Parts total, @@SCOPESHORT@@}} & \multicolumn{2}{r@{}}{\textbf{@@TOTAL@@}} \\
\multicolumn{8}{@{}p{16.35cm}@{}}{\rule{0pt}{11pt}$^\dagger$\,No listing. Consumables are a round allowance,
carried as pre-GST with GST and contingency applied.} \\
\end{longtable}}

\section{Battery selection}

The battery is the largest single design decision in this parts list. The
previous design used a pack built in-house from eighteen cells. A bought
lithium-polymer pack avoids spot-welding cells in a student lab. It has to be
large enough to keep the mission's energy reserve \emph{after} its own extra
weight is counted, because a heavier aircraft needs more power to hover. Each
candidate was run through the project's sizing model at its own mass:

\begin{center}
\footnotesize
\begin{tabular}{@{}lrrrrrr@{}}
\toprule
\textbf{Pack} & \textbf{Mass} & \textbf{Energy} & \textbf{Take-off} & \textbf{Thrust/} & \textbf{Endurance} & \textbf{Landing} \\
 & \textbf{kg} & \textbf{Wh} & \textbf{mass, kg} & \textbf{weight} & \textbf{ratio} & \textbf{reserve, Wh} \\
\midrule
@@BATT@@
\bottomrule
\end{tabular}
\end{center}

{\footnotesize \emph{Endurance ratio} is hover time divided by mission time; the
design requires at least 2.0. \emph{Landing reserve} is the energy left after the
third aircraft waits its turn and descends, and must be positive. $^\ast$\,Fails
the requirement. The 16\,Ah pack's mass is a range because the maker does not
publish it.\par}

The 12 and 13\,Ah packs fail both requirements, and about 14\,Ah is the smallest
that passes. The 16\,Ah pack is the smallest suitable size on sale in India. Its
cost is weight: on the same motors, thrust-to-weight falls from 2.0 to about
1.8--1.9 unless the thrust stand measures at least 3.55\,kgf per motor. That
measurement is the first funded step.

\section{Basis of prices}

\begin{itemize}[leftmargin=14pt,itemsep=1pt,topsep=2pt]
\item Prices were taken from Indian supplier listings on 19--20 September 2026. Where
      a supplier blocked automated checking, the same part's price at another
      Indian retailer was used, and that retailer is the one linked.
\item Retail listings already include GST and are used as listed. Pre-GST quotations,
      B2B listings and estimates have 18\,\% GST added (\rs{@@GST@@}).
\item A 15\,\% contingency is applied to the whole, for price movement between
      now and each phase's purchase.
\item Customs duty does not apply: every part is bought from a supplier in India.
\end{itemize}

\section{Team and approval}

\noindent
\begin{center}
\footnotesize
\begin{tabular}{@{}L{3.2cm}L{6.4cm}ll@{}}
\toprule
\textbf{Name} & \textbf{Department} & \textbf{Batch} & \textbf{Roll No.} \\
\midrule
@@TEAM@@
\bottomrule
\end{tabular}
\end{center}

\vspace{12mm}
\noindent
\begin{tabular}{@{}p{5.4cm}p{5.4cm}p{5.4cm}@{}}
\hrulefill & \hrulefill & \hrulefill \\
\textbf{@@MENTORA@@} & \textbf{@@MENTORB@@} & \textbf{@@SUBNAME@@} \\
{\small Faculty Mentor} & {\small Faculty Mentor} & {\small Submitted on behalf of the team} \\
{\small Date:} & {\small Date:} & {\small Date:} \\
\end{tabular}

\end{document}
"""


def variant(single: bool):
    """Quantities, schedule and wording for the document being built.

    The single variant reads its quantities and phase schedule from
    build_single_brief, so this BOM and mentor-brief-single cannot disagree.
    """
    per_ac = sum(r[3] * r[5] for r in S.BOM)
    if not single:
        rel = S.phase_released()
        return dict(
            out=OUT_FULL, items=[(r, r[4]) for r in S.BOM],
            released=sum(rel.values()), ph1=rel[1], words={
                "TITLE": "An Autonomous Multi-UAV System",
                "SCOPE": "Three-aircraft programme",
                "SCOPESHORT": "three aircraft",
                "BRIEFNAME": "The programme brief",
                "BRIEFREF": "the programme brief",
                "WHAT": "the\nthree RescueSwarm aircraft", "GSPOSS": "their",
                "PERACTEXT": rf"The components fitted to one aircraft cost \rs{{{rs(per_ac)}}}.",
                "NPHASES": str(len(rel)), "NEXTSTEP": "",
                "ONCEFOR": "programme",
                "QTYNOTE": "the\nprogramme quantity, including spares.",
            })
    import build_single_brief as B
    released = sum(amt for *_, amt in B.ROWS)
    rest = B._full_released() - released
    return dict(
        out=OUT_SINGLE, items=B.SINGLE, released=released, ph1=B.ROWS[0][3], words={
            "TITLE": "An Autonomous UAV",
            "SCOPE": "Single-aircraft build",
            "SCOPESHORT": "one aircraft",
            "BRIEFNAME": "The single-aircraft brief",
            "BRIEFREF": "the single-aircraft brief",
            "WHAT": "one\nRescueSwarm aircraft", "GSPOSS": "its",
            "PERACTEXT": rf"Of the parts, \rs{{{rs(per_ac)}}} is fitted to the aircraft "
                         "itself; the rest is test instruments, the RTK base station, "
                         "flight-test support and the ground station.",
            "NPHASES": str(B.N),
            "NEXTSTEP": rf" If this aircraft meets its gates, two more like it would come "
                        rf"to about \rs{{{rs(rest)}}}; that would be a separate request.",
            "ONCEFOR": "build",
            "QTYNOTE": "the\nquantity bought for this aircraft, including spares.",
        })


def main():
    single = "--single" in sys.argv[1:]
    V = variant(single)
    OUT, items = V["out"], V["items"]
    total = sum(r[3] * q for r, q in items)
    ex = sum(r[3] * q for r, q in items if S.is_ex_gst(r[6]))
    incl = total - ex
    gst = ex * S.GST
    cont = (total + gst) * S.CONTINGENCY
    req = total + gst + cont
    released = V["released"]
    assert abs(req - released) < 1.0, f"breakdown {req:.2f} != phase schedule {released:.2f}"
    per_ac = sum(r[3] * r[5] for r in S.BOM)
    ph1 = V["ph1"]

    rows, n = bom_rows(items)
    assert n == len(items)

    def gtot(k):
        return sum(r[3] * q for r, q in items if r[0] == k)

    def nlines(k):
        return sum(1 for r, _ in items if r[0] == k)

    if single:
        groups = "\n".join(rf"{GROUP_TITLE[k]} & {nlines(k)} & {rs(gtot(k))} \\"
                           for k in GROUP_TITLE)
        gcols = "rr"
        ghead = r"\textbf{Group} & \textbf{Lines} & \textbf{Amount} \\"
        gtotal = rf"\textbf{{Total}} & \textbf{{{n}}} & \textbf{{{rs(total)}}} \\"
    else:
        groups = "\n".join(
            rf"{GROUP_TITLE[k]} & {nlines(k)} & "
            rf"{rs(S.per_aircraft(k)) if S.per_aircraft(k) else '--'} & "
            rf"{rs(gtot(k))} \\" for k in GROUP_TITLE)
        gcols = "rrr"
        ghead = (r"\textbf{Group} & \textbf{Lines} & \textbf{Per aircraft} & "
                 r"\textbf{All three} \\")
        gtotal = (rf"\textbf{{Total}} & \textbf{{{n}}} & \textbf{{{rs(per_ac)}}} & "
                  rf"\textbf{{{rs(total)}}} \\")
    config = "\n".join(rf"\textbf{{{a}}} & {b} \\" for a, b in CONFIG)
    batt = "\n".join(" & ".join(r) + r" \\" for r in BATTERY_TABLE)
    team = "\n".join(rf"{nm} & {dept} & {L.BATCH} & {roll} \\" for nm, dept, roll in L.TEAM)
    sub_name, _sub_dept, _sub_roll = L.SUBMITTER

    doc = TEMPLATE
    for k, v in {
        "GROUPCOLS": gcols, "GROUPHEAD": ghead, "GROUPTOTAL": gtotal,
        "DATE": DATE,
        "MENTORS": " and ".join(L.MENTORS),
        "MENTORA": L.MENTORS[0], "MENTORB": L.MENTORS[1],
        "SUBMITTER": sub_name, "SUBNAME": sub_name,
        "NINCL": str(sum(1 for r, _ in items if not S.is_ex_gst(r[6]))),
        "NEX": str(sum(1 for r, _ in items if S.is_ex_gst(r[6]))),
        "INCL": rs(incl), "EX": rs(ex), "TOTAL": rs(total), "GST": rs(gst),
        "CONT": rs(cont), "REQ": rs(req), "PH1": rs(ph1),
        "LINES": str(len(items)), "GROUPS": groups, "CONFIG": config,
        "ROWS": rows, "BATT": batt, "TEAM": team,
    }.items():
        doc = doc.replace(f"@@{k}@@", v)
    for k, v in V["words"].items():
        doc = doc.replace(f"@@{k}@@", v)
    assert "@@" not in doc, "unreplaced template key"
    assert not any(ord(c) < 32 and c != "\n" for c in doc), "control char in document"

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(doc)
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  ({len(items)} lines, parts {total:,.0f}, "
          f"requested {req:,.0f})")

    if shutil.which("pdflatex"):
        for _ in range(2):          # second pass resolves page count and references
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
