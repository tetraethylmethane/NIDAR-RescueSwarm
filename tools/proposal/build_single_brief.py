#!/usr/bin/env python3
r"""Generate the SINGLE-AIRCRAFT variant of the mentor brief's tables.

WHY A SECOND GENERATOR AND NOT A SECOND BOM. The one-aircraft ask is not a
different basket, it is the same basket truncated: phases 1--12 of the
three-aircraft schedule already buy exactly one aircraft, the instruments that
measure it and the flight-test support that flies it. Phases 13--28 replicate
it twice and are simply not asked for. So the quantities here are DERIVED from
hardware/bom/sourced_bom.py by the same allocation rule, not re-entered --- a
second hand-typed parts list would disagree with the first within one revision,
which is the failure this whole toolchain exists to prevent.

Two things do change rather than truncate:

  1. The ground segment (phase 29 of 29 in the full programme) is scaled from
     three video chains to one, and renumbered 13. One aircraft needs one
     digital receiver and its two antennas; the coordination base and the
     tripod are single-unit either way.

  2. Nothing else changes: every aircraft now carries the same F9P rover, and
     phase 5 already buys the RTK base alongside aircraft 1's.

Emits: docs/proposal/generated-single-schedule.tex
       docs/proposal/generated-single-tables.tex
       docs/proposal/generated-single-letters.tex
Run:   python tools/proposal/build_single_brief.py
"""
from __future__ import annotations

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "hardware", "bom"))
sys.path.insert(0, os.path.join(ROOT, "tools", "proposal"))
import sourced_bom as S                                             # noqa: E402
from build_brief_tables import (RATIONALE, SCHEDULE, esc, money,    # noqa: E402
                                supplier_of)
from build_approval_letters import letter                           # noqa: E402
import build_approval_letters as L                                  # noqa: E402

OUT_TABLES = os.path.join(ROOT, "docs", "proposal", "generated-single-tables.tex")
OUT_SCHED = os.path.join(ROOT, "docs", "proposal", "generated-single-schedule.tex")
OUT_LETTERS = os.path.join(ROOT, "docs", "proposal", "generated-single-letters.tex")

# The phases of the full schedule that build ONE aircraft. 13--28 replicate it.
KEPT = tuple(range(1, 13))
GROUND_PHASE = 13          # the full programme's phase 29, renumbered

# Ground-segment quantities for a one-aircraft system. Three video chains
# become one; the base radio and the tripod were single units already.
GROUND_QTY = {"Video receivers": 1, "Receive antennas": 2,
              "Coordination base": 1, "Base station mount": 1}

PHASES = {"instruments": "1--2", "avionics": "3--6", "airframe": "7--10",
          "flighttest": "11--12", "ground": "13"}


def single_qty(r):
    """Programme quantity for the one-aircraft build, by the BOM's own rule."""
    group, item, _model, _unit, _qty, _ac, _url = r
    if group == "ground":
        return GROUND_QTY[item]
    return sum(q for p, q in S._alloc(r).items() if p in KEPT)


SINGLE = [(r, single_qty(r)) for r in S.BOM]
SINGLE = [(r, q) for r, q in SINGLE if q]


def group_total(key):
    return sum(r[3] * q for r, q in SINGLE if r[0] == key)


def total():
    return sum(r[3] * q for r, q in SINGLE)


# ---------------------------------------------------------------------------
# Schedule. Phases 1--12 keep their objectives and gates verbatim from the full
# programme -- they are the same steps buying the same parts. Only the ground
# phase is restated, because it now serves one aircraft rather than three.
GROUND_ROW = (GROUND_PHASE, "Ground station: video feed, data link, base mount",
              "Aircraft flying")


def schedule_rows():
    rel = S.phase_released()
    rows = [(ph, obj, gate, rel[ph]) for ph, obj, gate in SCHEDULE if ph in KEPT]
    assert len(rows) == len(KEPT), "lost a phase between SCHEDULE and KEPT"

    # The ground phase is priced here rather than read from phase_released(),
    # because its quantities changed. Every ground line is Indian retail, so
    # the tax is already paid and only contingency applies -- asserted, not
    # assumed, so a future ex-GST supplier on one of these lines fails loudly.
    ground = [(r, q) for r, q in SINGLE if r[0] == "ground"]
    assert not any(S.is_ex_gst(r[6]) for r, _ in ground), \
        "a ground line is now ex-GST; price it through S.released() instead"
    amt = S.released(sum(r[3] * q for r, q in ground), 0.0)
    rows.append(GROUND_ROW + (amt,))
    return rows


ROWS = schedule_rows()
N = len(ROWS)


def schedule_table():
    body = "\n".join(f"{ph} & {obj} & {money(amt)} & {gate} \\\\"
                     for ph, obj, gate, amt in ROWS)
    return body, sum(amt for _, _, _, amt in ROWS)


# ---------------------------------------------------------------------------
def rows_for(key):
    out = []
    for r, q in SINGLE:
        if r[0] != key:
            continue
        _, item, model, unit, _qty, _ac, url = r
        sup = supplier_of(url)
        note = RATIONALE[item] + " " + (
            f"\\textit{{{sup}}}" if sup != "in-house" else "\\textit{in-house}")
        qtytxt = f", {q} off" if q > 1 else ""
        out.append(f"{esc(item)} & {esc(model)}{qtytxt} "
                   f"& {money(unit * q)} & {note} \\\\")
    return "\n".join(out)


TABLE_HEAD = r"""
\begingroup\small
\begin{longtable}{@{}>{\raggedright\arraybackslash}p{2.6cm}>{\raggedright\arraybackslash}p{4.4cm}r>{\raggedright\arraybackslash}p{7.4cm}@{}}
\toprule
\thead{Item} & \thead{Model} & \thead{INR} & \thead{Why this part, and from whom} \\
\midrule
\endfirsthead
\toprule
\thead{Item} & \thead{Model} & \thead{INR} & \thead{Why this part, and from whom} \\
\midrule
\endhead"""

HEADER = ("%" + "=" * 76 + "\n"
          "% GENERATED FILE -- do not edit.\n"
          "% Produced by tools/proposal/build_single_brief.py from\n"
          "% hardware/bom/sourced_bom.py. Edit the BOM, not this file.\n"
          "%" + "=" * 76 + "\n")


def write_tables():
    parts = []
    for key, label, _ph in S.GROUPS:
        parts.append(f"\\subsubsection*{{{label} --- phases {PHASES[key]}"
                     f" \\quad \\rs{{{money(group_total(key))}}} of parts}}")
        parts.append(TABLE_HEAD)
        parts.append(rows_for(key))
        parts.append(r"\bottomrule")
        parts.append(r"\end{longtable}")
        parts.append(r"\endgroup")
        parts.append("")
    body = "\n".join(parts)
    assert not any(ord(c) < 32 and c != "\n" for c in body), "control char in tables"
    io.open(OUT_TABLES, "w", encoding="utf-8", newline="\n").write(HEADER + body)


def write_schedule():
    body, grand = schedule_table()
    assert body.count("\\textbf") == 1, "schedule: lost a backslash"
    pre = (r"""\begingroup
\footnotesize
\setlength{\extrarowheight}{1.5pt}
\begin{longtable}{@{}>{\bfseries}r>{\raggedright\arraybackslash}p{7.3cm}r>{\raggedright\arraybackslash}p{5.6cm}@{}}
\toprule
\thead{\#} & \thead{Objective} & \thead{INR} & \thead{Released only after} \\
\midrule
\endfirsthead
\toprule
\thead{\#} & \thead{Objective} & \thead{INR} & \thead{Released only after} \\
\midrule
\endhead
\midrule
\multicolumn{2}{@{}r}{\thead{Total}} & \thead{""" + money(grand) + r"""} & \\
\bottomrule
\endlastfoot
""")
    io.open(OUT_SCHED, "w", encoding="utf-8", newline="\n").write(
        HEADER + pre + body + "\n" + r"\end{longtable}" + "\n" + r"\endgroup" + "\n")
    return grand


def write_letters():
    """One letter per phase, on the one-aircraft quantities.

    build_approval_letters.letter() renders N from its module global, which is
    29 there and 13 here, so it is rebound for the duration.
    """
    by_phase = {}
    for r, q in SINGLE:
        _, item, model, unit, _qty, _ac, _url = r
        if r[0] == "ground":
            by_phase.setdefault(GROUND_PHASE, []).append((item, model, q, unit, unit * q))
            continue
        for p, pq in S._alloc(r).items():
            if p in KEPT and pq:
                by_phase.setdefault(p, []).append((item, model, pq, unit, unit * pq))
    by_phase = {p: sorted(v, key=lambda x: -x[4]) for p, v in by_phase.items()}
    assert set(by_phase) == {ph for ph, _, _, _ in ROWS}, \
        "schedule and BOM disagree about which phases exist"

    saved, L.N = L.N, N
    try:
        out, grand = [], 0.0
        for ph, objective, gate, _amt in ROWS:
            lines = by_phase[ph]
            tot = sum(x[4] for x in lines)
            grand += tot
            out.append(letter(ph, objective, gate, lines, tot))
    finally:
        L.N = saved

    assert abs(grand - total()) < 1.0, \
        f"letters total {grand:.2f} but the single-aircraft BOM is {total():.2f}"
    body = "".join(out)
    assert not any(ord(c) < 32 and c != "\n" for c in body), "control character"
    for key in ("PHASE", "TOTALAMT", "SMALLFONT", "BOXRULE", "OBJECTIVE"):
        assert key not in body, f"unreplaced key: {key}"
    io.open(OUT_LETTERS, "w", encoding="utf-8", newline="\n").write(HEADER + body)
    return grand


BRIEF = os.path.join(ROOT, "docs", "proposal", "mentor-brief-single.tex")

# LaTeX control sequences beginning \r are written through this token. Spelled
# literally in a non-raw string, "\rs" is a carriage return followed by "s" --
# which is a silent mismatch here and a swallowed macro in the .tex, and is the
# escaping failure build_approval_letters.py already guards against twice.
RS = chr(92) + "rs"


def _full_released():
    """What the FULL three-aircraft programme releases, so the brief's 'two
    more aircraft would cost' figure is a real remainder rather than a
    subtraction someone did by hand once."""
    incl = sum(S.line_total(r) for r in S.BOM if not S.is_ex_gst(r[6]))
    ex = sum(S.line_total(r) for r in S.BOM if S.is_ex_gst(r[6]))
    return S.released(incl, ex)


def check_prose(grand, parts):
    """The brief quotes six totals in running text, and nothing else would
    catch it if a price moved underneath them.

    This repository's recurring defect is a correct, generated number that the
    prose does not actually use, so the prose is checked against the generated
    figures rather than trusted. Each entry is the exact argument as it appears
    inside the document's currency macro.
    """
    if not os.path.exists(BRIEF):          # first run, before the .tex exists
        return
    text = io.open(BRIEF, encoding="utf-8").read()
    full = _full_released()
    want = {
        "released, one aircraft":  grand,
        "parts, one aircraft":     parts,
        "phase 1":                 ROWS[0][3],
        "phases 1 and 2":          sum(a for ph, _, _, a in ROWS if ph in (1, 2)),
        "released, three aircraft": full,
        "the remaining two aircraft": full - grand,
    }
    missing = [f"{label} ({money(v)})" for label, v in want.items()
               if RS + "{" + money(v) + "}" not in text]
    assert not missing, (
        "mentor-brief-single.tex does not quote: " + ", ".join(missing)
        + " -- the prose has drifted from the generated tables")


def main():
    write_tables()
    grand = write_schedule()
    parts = write_letters()
    check_prose(grand, parts)
    rel = os.path.relpath
    print(f"  wrote {rel(OUT_SCHED, ROOT)}  ({N} phases, {grand:,.0f} released)")
    print(f"  wrote {rel(OUT_TABLES, ROOT)}  ({len(SINGLE)} rows)")
    print(f"  wrote {rel(OUT_LETTERS, ROOT)}  ({N} letters)")
    print(f"  parts {parts:,.0f}   released {grand:,.0f}   "
          f"against {S.total():,.0f} / three aircraft")


if __name__ == "__main__":
    main()
