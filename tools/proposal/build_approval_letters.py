#!/usr/bin/env python3
r"""Generate one DoSA approval letter per phase, appended after the brief.

WHY GENERATED. There are 30 of them and each carries its own component list and
total. Typed by hand they would disagree with the schedule within one revision,
and a letter asking for a figure the brief does not show is the one thing that
must never happen in a funding document.

Every component list and every total is read from hardware/bom/sourced_bom.py,
the same source as the brief's tables and schedule, and the thirty letters are
asserted to sum to the whole parts list exactly.

NOTE ON THE AMOUNTS. A letter asks for the PARTS cost of its phase -- the sum of
the components it lists -- following the specimen letter, which totals its
component table and requests exactly that. The schedule in the brief quotes the
RELEASED figure, which is the same parts cost plus tax still owed plus 15 %
contingency. The two differ on purpose, and each letter says which it is.

Emits: docs/proposal/generated-approval-letters.tex
Run:   python tools/proposal/build_approval_letters.py
"""
from __future__ import annotations

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "hardware", "bom"))
sys.path.insert(0, os.path.join(ROOT, "tools", "proposal"))
import sourced_bom as S                                # noqa: E402
from build_brief_tables import SCHEDULE, money, esc    # noqa: E402

OUT = os.path.join(ROOT, "docs", "proposal", "generated-approval-letters.tex")

MENTORS = ["Dr. Surbhi Sharma", "Dr. Mamata Gulati"]

TEAM = [
    ("Swastik Kumar",  r"Electronics \& Communication Engineering", "1024060150"),
    ("Samuel Masih",   r"Computer Science \& Engineering",          "1024170044"),
    ("Prabhjot Singh", r"Robotics and Artificial Intelligence Engg.", "1024230021"),
    ("Manan Kapoor",   r"Computer Science \& Engineering",          "1024030467"),
    ("Manav Pansari",  r"Electronics \& Communication Engineering", "1024060151"),
    ("Ravi Kant Raja", r"Robotics and Artificial Intelligence Engg.", "1024230032"),
    ("Neil Kishore",   r"Mechanical Engineering",                   "1024080017"),
]
BATCH = "2024--2028"
SUBMITTER = ("Swastik Kumar",
             r"Department of Electronics \& Communication Engineering",
             "1024060150")

N = len(SCHEDULE)

# LaTeX control sequences starting with \f are written through this token. The
# editing path into this file has more than once turned a literal backslash-f
# into a form feed, which LaTeX then swallows silently; SMALLFONT and BOXRULE
# keep those two sequences out of the source text entirely.
FN = chr(92) + "footnotesize"
FB = chr(92) + "fbox"


def gate_sentence(ph, gate):
    """What must already be true before this phase is released."""
    plain = gate.replace(r"\textbf{", "").replace("}", "")
    if ph == 1:
        return "This is the first step, and is gated only on this approval."
    return ("It falls due only once the previous step has produced its stated "
            "result: \\emph{" + plain.lower() + "}.")


TEMPLATE = r"""
\clearpage
\thispagestyle{empty}
\begingroup
SMALLFONT
\setlength{\parskip}{0.26em}
% The brief sets loose table spacing for readability; a letter has to fit one
% page, so it is reset here rather than globally.
\setlength{\extrarowheight}{0pt}
\renewcommand{\arraystretch}{1.02}

% ---- letterhead, matching the brief's ---------------------------------------
\noindent
\raisebox{-0.5\height}{\includegraphics[height=11mm]{brainwave.pdf}}%
\hfill
\raisebox{-0.5\height}{\includegraphics[height=10mm]{thapar_logo.png}}

\vspace{2mm}\hrule\vspace{2.5mm}

\begin{center}
{\large\bfseries RescueSwarm}\\[1.1mm]
{\normalsize\bfseries An Autonomous Multi-UAV System for Post-Disaster\\[0.4mm]
Search, Localisation and Payload Delivery}
\end{center}

\vspace{1mm}\hrule\vspace{2.5mm}

\noindent\begin{minipage}[t]{0.62\textwidth}
To\\
The Dean, Student Affairs (DoSA)\\
\emph{Through:} President, Thapar Amateur Astronomers Society (TAAS)\\
Thapar Institute of Engineering \& Technology, Patiala
\end{minipage}\hfill
\begin{minipage}[t]{0.34\textwidth}
\raggedleft
Ref.: RS/PH-PHASE\\[2.2mm]
Date: \rule{28mm}{0.4pt}
\end{minipage}

\vspace{1mm}
\noindent\textbf{Subject:} Fund Request under TAAS Society for the RescueSwarm
Project --- Phase PHASE of NTOTAL, OBJECTIVE

\noindent Respected Ma'am,

We, a team of students of Thapar Institute of Engineering \& Technology, are
working under the guidance of MENTORA and MENTORB on \textbf{RescueSwarm}, an
autonomous multi-UAV system for post-disaster search, survivor localisation and
payload delivery. The software and simulation framework is complete, and the
programme is now in hardware integration and testing, funded in NTOTAL steps so
that each is approved only once the previous has produced a stated result.

\noindent\textbf{This request is Phase PHASE of NTOTAL: OBJECTIVE.} GATESENT
We request funding for the following components:

\noindent\makebox[\textwidth][c]{%
\scriptsize
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{3.1cm}>{\raggedright\arraybackslash}p{6.9cm}rr@{}}
\toprule
\textbf{Component} & \textbf{Model} & \textbf{Qty} & \textbf{Cost (INR)} \\
\midrule
COMPROWS
\midrule
\multicolumn{3}{@{}r}{\textbf{Total}} & \textbf{TOTALAMT} \\
\bottomrule
\end{tabular}}

\noindent We kindly request approval and financial support of
\textbf{\rs{TOTALAMT}} under TAAS Society for the procurement of the components
above. This is the parts cost of this phase; the programme schedule additionally
carries tax where it is still owed, and a 15\,\% contingency.

\noindent\textbf{Team Members}\quad\emph{Mentors:} MENTORA and MENTORB

\noindent\makebox[\textwidth][c]{%
\scriptsize
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{3.0cm}>{\raggedright\arraybackslash}p{6.1cm}ll@{}}
\toprule
\textbf{Name} & \textbf{Department} & \textbf{Batch} & \textbf{Roll No.} \\
\midrule
TEAMROWS
\bottomrule
\end{tabular}}

\vspace{1.5mm}
\noindent\textbf{Approvals \& Signatures}

\vspace{8mm}
\noindent
\begin{tabular}{@{}p{5.3cm}p{5.3cm}p{5.4cm}@{}}
\hrulefill & \hrulefill & \hrulefill \\
\textbf{MENTORA} & \textbf{MENTORB} & \textbf{President, TAAS} \\
{SMALLFONT Mentor} & {SMALLFONT Mentor} &
{SMALLFONT Thapar Amateur Astronomers Society} \\
\end{tabular}

\vspace{5.5mm}
\noindent
\begin{tabular}{@{}p{8.2cm}p{8.2cm}@{}}
\hrulefill & \hrulefill \\
\textbf{SUBNAME} & \textbf{Date} \\
{SMALLFONT SUBDEPT, Roll No. SUBROLL} & \\
{SMALLFONT Submitted on behalf of the team} & \\
\end{tabular}

\vspace{2.5mm}
\noindent BOXRULE{\begin{minipage}{0.968\textwidth}
\vspace{0.8mm}
{SMALLFONT \textbf{For office use --- Office of the Dean, Student Affairs}}

\vspace{6mm}
\begin{tabular}{@{}p{4.6cm}p{5.5cm}p{5.3cm}@{}}
\hrulefill & \hrulefill & \hrulefill \\
{SMALLFONT Amount sanctioned (INR)} & {SMALLFONT Signature} &
{SMALLFONT Date} \\
\end{tabular}
\vspace{0.8mm}
\end{minipage}}
\endgroup
"""


def letter(ph, objective, gate, lines, total):
    rows = "\n".join(
        f"{esc(item)} & {esc(model)} & {q} & {money(tot)} " + r"\\"
        for item, model, q, _unit, tot in lines)
    team = "\n".join(
        f"{name} & {dept} & {BATCH} & {roll} " + r"\\"
        for name, dept, roll in TEAM)
    obj = objective.replace("---", "--")
    out = TEMPLATE
    for key, val in (("COMPROWS", rows), ("TEAMROWS", team),
                     ("GATESENT", gate_sentence(ph, gate)),
                     ("OBJECTIVE", obj), ("TOTALAMT", money(total)),
                     ("NTOTAL", str(N)), ("PHASE", str(ph)),
                     ("MENTORA", MENTORS[0]), ("MENTORB", MENTORS[1]),
                     ("SUBNAME", SUBMITTER[0]), ("SUBDEPT", SUBMITTER[1]),
                     ("SUBROLL", SUBMITTER[2]),
                     ("SMALLFONT", FN), ("BOXRULE", FB)):
        out = out.replace(key, val)
    return out


def main():
    lines_by_phase = S.phase_lines()
    alloc = S.phase_alloc()
    assert {p for p, _, _ in SCHEDULE} == set(lines_by_phase), \
        "schedule and BOM disagree about which phases exist"

    out, grand = [], 0.0
    for ph, objective, gate in SCHEDULE:
        lines = lines_by_phase[ph]
        total = sum(x[4] for x in lines)
        assert abs(total - alloc[ph]) < 0.01, f"phase {ph}: {total} vs {alloc[ph]}"
        grand += total
        out.append(letter(ph, objective, gate, lines, total))

    assert abs(grand - S.total()) < 1.0, \
        f"letters total {grand:.2f} but the BOM is {S.total():.2f}"

    body = "".join(out)
    # The escaping hazards this repository keeps hitting: a lost backslash turns
    # \textbf into a TAB and \footnotesize into a form feed, and both compile.
    want = TEMPLATE.count(r"\textbf") * len(out)
    assert body.count(r"\textbf") == want, \
        f"lost a backslash: {body.count(chr(92) + 'textbf')} of {want}"
    assert body.count(FN) == TEMPLATE.count("SMALLFONT") * len(out), "lost a font"
    assert not any(ord(c) < 32 and c != "\n" for c in body), "control character"
    for key in ("PHASE", "TOTALAMT", "SMALLFONT", "BOXRULE", "OBJECTIVE"):
        assert key not in body, f"unreplaced key: {key}"

    header = ("%" + "=" * 76 + "\n"
              "% GENERATED FILE -- do not edit.\n"
              "% Produced by tools/proposal/build_approval_letters.py from\n"
              "% hardware/bom/sourced_bom.py. Edit the BOM, not this file.\n"
              "%" + "=" * 76 + "\n")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(header + body)
    print(f"  wrote {os.path.relpath(OUT, ROOT)}")
    print(f"  {len(out)} letters, {grand:,.2f} total -- reconciles with the BOM")


if __name__ == "__main__":
    main()
