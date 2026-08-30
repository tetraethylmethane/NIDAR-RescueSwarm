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
    ("Neil Mathur",    r"Mechanical Engineering",                   "1024080017"),
]
BATCH = "2024--2028"
SUBMITTER = ("Swastik Kumar",
             r"Department of Electronics \& Communication Engineering",
             "1024060150")

N = len(SCHEDULE)


def gate_sentence(ph, gate):
    """What must already be true before this phase is released."""
    plain = gate.replace(r"\textbf{", "").replace("}", "")
    if ph == 1:
        return "This is the first step, and is gated only on this approval."
    return ("It falls due only once the previous step has produced its stated "
            "result: \\emph{" + plain.lower() + "}.")


TEMPLATE = r"""
\clearpage
\thispagestyle{fancy}
\begingroup
\small
\setlength{\parskip}{0.34em}

\begin{center}\textbf{Fund Request --- Phase PHASE of NTOTAL}\end{center}

\noindent
To\\
The Dean, Student Affairs (DoSA)\\
\emph{Through:} President, Thapar Amateur Astronomers Society (TAAS)\\
Thapar Institute of Engineering \& Technology, Patiala

\noindent\textbf{Subject:} Fund Request under TAAS Society for the RescueSwarm
Project --- Phase PHASE of NTOTAL, OBJECTIVE

\noindent Respected Ma'am,

We, a team of students of Thapar Institute of Engineering \& Technology, are
working under the guidance of MENTORA and MENTORB on \textbf{RescueSwarm}, an
autonomous multi-UAV system for post-disaster search, survivor localisation and
payload delivery. The software and simulation framework is complete, and the
programme is now in hardware integration and testing. It is funded in NTOTAL
steps rather than as one grant, so that each step is approved only once the
previous one has produced a stated result.

\noindent\textbf{This request is Phase PHASE of NTOTAL: OBJECTIVE.} GATESENT
We request funding for the following components:

{\footnotesize
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{3.1cm}>{\raggedright\arraybackslash}p{7.0cm}rr@{}}
\toprule
\textbf{Component} & \textbf{Model} & \textbf{Qty} & \textbf{Cost (INR)} \\
\midrule
COMPROWS
\midrule
\multicolumn{3}{@{}r}{\textbf{Total}} & \textbf{TOTALAMT} \\
\bottomrule
\end{tabular}
}

\noindent We kindly request approval and financial support of
\textbf{\rs{TOTALAMT}} under TAAS Society for the procurement of the components
above. This is the parts cost of this phase; the programme schedule additionally
carries tax where it is still owed, and a 15\,\% contingency.

\noindent\textbf{Team Members}\quad\emph{Mentors:} MENTORA and MENTORB

{\footnotesize
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{3.0cm}>{\raggedright\arraybackslash}p{6.2cm}ll@{}}
\toprule
\textbf{Name} & \textbf{Department} & \textbf{Batch} & \textbf{Roll No.} \\
\midrule
TEAMROWS
\bottomrule
\end{tabular}
}

\vspace{2mm}
\noindent\textbf{Approvals \& Signatures}

\vspace{9mm}
\noindent
\begin{tabular}{@{}p{5.2cm}p{5.2cm}p{5.4cm}@{}}
\hrulefill & \hrulefill & \hrulefill \\
MENTORA & MENTORB & President, TAAS \\
\end{tabular}

\vspace{3mm}
\noindent\textbf{Submitted by:} SUBNAME, SUBDEPT,
Thapar Institute of Engineering \& Technology, Roll No. SUBROLL
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
                     ("SUBROLL", SUBMITTER[2])):
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
    # The escaping hazards this repository keeps hitting: a lost backslash
    # turns \textbf into a TAB and \begin into a backspace, and both compile.
    want = TEMPLATE.count(r"\textbf") * len(out)
    assert body.count(r"\textbf") == want, \
        f"lost a backslash: {body.count(chr(92) + 'textbf')} of {want}"
    assert not any(ord(c) < 32 and c != "\n" for c in body), "control character"
    assert "PHASE" not in body and "TOTALAMT" not in body, "unreplaced key"

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
