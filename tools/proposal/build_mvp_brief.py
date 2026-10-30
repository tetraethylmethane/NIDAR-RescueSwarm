#!/usr/bin/env python3
r"""Generate the MVP variant of the mentor brief's tables.

WHAT THE MVP IS. The smallest build that flies the mission end to end and
finds a person: survey planning, autonomous flight, detection, localisation,
descent, release, return. It is NOT a competition entry -- it drops the three
video feeds the rules require, and NIDAR wants two aircraft. Everything cut
below is cut because the MVP can demonstrate the concept without it, not
because it is unnecessary to the finished system.

DERIVED, NOT RE-ENTERED. The quantities come from build_single_brief.SINGLE,
which comes from hardware/bom/sourced_bom.py by its own allocation rule. This
file only removes rows, so a price change in the BOM moves all three briefs
together. (It used to swap the DIY Li-ion pack for a bought LiPo as well; since
2026-09-19 the LiPo is the BOM's own pack, so there is nothing left to swap.)

Emits: docs/proposal/generated-mvp-schedule.tex
       docs/proposal/generated-mvp-tables.tex
       docs/proposal/generated-mvp-letters.tex
Run:   python tools/proposal/build_mvp_brief.py
"""
from __future__ import annotations

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "hardware", "bom"))
sys.path.insert(0, os.path.join(ROOT, "tools", "proposal"))
import sourced_bom as S                                             # noqa: E402
import build_single_brief as One                                    # noqa: E402
from build_brief_tables import (RATIONALE, esc, money,              # noqa: E402
                                supplier_of)
from build_approval_letters import letter                           # noqa: E402
import build_approval_letters as L                                  # noqa: E402

OUT_TABLES = os.path.join(ROOT, "docs", "proposal", "generated-mvp-tables.tex")
OUT_SCHED = os.path.join(ROOT, "docs", "proposal", "generated-mvp-schedule.tex")
OUT_LETTERS = os.path.join(ROOT, "docs", "proposal", "generated-mvp-letters.tex")
BRIEF = os.path.join(ROOT, "docs", "proposal", "mentor-brief-mvp.tex")

RS = chr(92) + "rs"        # see build_single_brief: "\rs" in a plain string is CR

# ---------------------------------------------------------------------------
# WHAT THE MVP DOES NOT BUY, and why it can still fly the mission without it.
CUT = {
 "GNSS RTK base":       "the RTK base. The aircraft's own F9P rover, flown "
                        "uncorrected, gives about 2 m against a 5 m delivery "
                        "requirement; RTK exists to MEASURE geolocation "
                        "against surveyed ground, a publication objective",
 "GNSS antenna, base":  "antenna for the same base",
 "GNSS feeder, base":   "cable for the same base",
 "GNSS cable, base":    "cable for the same base",
 "GNSS cable extension, base": "cable for the same base",
 "RTK base radio":      "carries the base's corrections, and there is no base",
 "Video transmitter":   "digital downlink. The mission is autonomous -- "
                        "nothing has to watch it live",
 "Video antennas":      "antennas for the same downlink",
 "Video receivers":     "ground end of the same downlink",
 "Receive antennas":    "ground end of the same downlink",
 "Receiver USB hub":    "powers the ground end of the same downlink",
 "Receive panels":      "ground end of the same downlink",
 "Panel pigtails":      "ground end of the same downlink",
 "Coordination radio":  "aircraft-to-aircraft link, and there is one aircraft",
 "Coordination base":   "ground end of the same link. Telemetry reaches the "
                        "laptop over ExpressLRS native MAVLink instead",
 "Height rangefinder":  "gates the release at 6 m over water of unknown level. "
                        "The barometer suffices over dry ground, which is where "
                        "the MVP flies",
 "Base station mount":  "tripod for the RTK base that is no longer bought",
}

ALL_RATIONALE = RATIONALE

# ---------------------------------------------------------------------------
MVP = [(r, q) for r, q in One.SINGLE if r[1] not in CUT]


def total():
    return sum(r[3] * q for r, q in MVP)


def group_total(key):
    return sum(r[3] * q for r, q in MVP if r[0] == key)


def rel(rows):
    incl = sum(r[3] * q for r, q in rows if not S.is_ex_gst(r[6]))
    ex = sum(r[3] * q for r, q in rows if S.is_ex_gst(r[6]))
    return S.released(incl, ex)


# ---------------------------------------------------------------------------
# PHASES. Cutting rows empties phase 13 outright -- the MVP has no ground
# segment to buy, because the ground station is a laptop talking MAVLink over
# the ExpressLRS link the safety pilot already holds. Two other phases change
# what they are called, because what they buy changed.
RENAME = {
 5: "Aircraft --- satellite positioning and compass",
 6: "Aircraft --- camera and command link",
 8: "Aircraft --- battery pack and power distribution",
 11: "Charging and manual override",
}


def alloc_of(r, q):
    """{phase: qty} for one MVP row. Most rows sit in a single kept phase, but
    the motors, propellers and speed controllers are deliberately split -- one
    of each is bought in phase 2 and measured on the stand before the rest are
    committed, which is the whole point of the schedule."""
    item = r[1]
    a = {p: n for p, n in S._alloc(r).items() if p in One.KEPT and n}
    assert sum(a.values()) == q, f"{item}: {a} != {q}"
    return a


def lines_by_phase():
    out = {}
    for r, q in MVP:
        _, item, model, unit, _qty, _ac, _url = r
        for p, n in alloc_of(r, q).items():
            out.setdefault(p, []).append((item, model, n, unit, unit * n))
    return {p: sorted(v, key=lambda x: -x[4]) for p, v in sorted(out.items())}


def phase_amount(ph):
    rows = []
    for r, q in MVP:
        n = alloc_of(r, q).get(ph, 0)
        if n:
            rows.append((r, n))
    return rel(rows)


LINES = lines_by_phase()


def schedule_rows():
    rows = []
    for ph, obj, gate in One.SCHEDULE:
        if ph not in One.KEPT or ph not in LINES:
            continue                   # phase emptied by the cuts
        rows.append((ph, RENAME.get(ph, obj.replace("Aircraft 1", "Aircraft")),
                     gate, phase_amount(ph)))
    assert [p for p, _, _, _ in rows] == sorted(LINES), \
        "schedule and parts disagree about which phases exist"
    return rows


ROWS = schedule_rows()
N = len(ROWS)

HEADER = ("%" + "=" * 76 + "\n"
          "% GENERATED FILE -- do not edit.\n"
          "% Produced by tools/proposal/build_mvp_brief.py from\n"
          "% hardware/bom/sourced_bom.py. Edit the BOM, not this file.\n"
          "%" + "=" * 76 + "\n")


def write_schedule():
    body = "\n".join(f"{ph} & {obj} & {money(a)} & {gate} \\\\"
                     for ph, obj, gate, a in ROWS)
    grand = sum(a for _, _, _, a in ROWS)
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

PHASES = {"instruments": "1--2", "avionics": "3--6", "airframe": "7--10",
          "flighttest": "11--12"}


def write_tables():
    parts = []
    for key, label, _ph in S.GROUPS:
        if not group_total(key):
            continue                   # the ground segment, emptied by the cuts
        parts.append(f"\\subsubsection*{{{label} --- phases {PHASES[key]}"
                     f" \\quad \\rs{{{money(group_total(key))}}} of parts}}")
        parts.append(TABLE_HEAD)
        rows = []
        for r, q in MVP:
            if r[0] != key:
                continue
            _, item, model, unit, _qty, _ac, url = r
            sup = supplier_of(url)
            note = ALL_RATIONALE[item] + " " + (
                f"\\textit{{{sup}}}" if sup != "in-house" else "\\textit{in-house}")
            rows.append(f"{esc(item)} & {esc(model)}"
                        + (f", {q} off" if q > 1 else "")
                        + f" & {money(unit * q)} & {note} \\\\")
        parts.append("\n".join(rows))
        parts.append(r"\bottomrule")
        parts.append(r"\end{longtable}")
        parts.append(r"\endgroup")
        parts.append("")

    # What was deliberately NOT bought, and why. A brief that only lists what it
    # buys lets a reader assume the rest was forgotten.
    parts.append(r"\needspace{6\baselineskip}")
    parts.append(r"\subsubsection*{Deliberately not bought}")
    parts.append(r"""
\begingroup\small
\begin{longtable}{@{}>{\raggedright\arraybackslash}p{3.2cm}r>{\raggedright\arraybackslash}p{11.4cm}@{}}
\toprule
\thead{Item} & \thead{INR saved} & \thead{Why the MVP can fly without it} \\
\midrule
\endfirsthead
\toprule
\thead{Item} & \thead{INR saved} & \thead{Why the MVP can fly without it} \\
\midrule
\endhead""")
    cut_rows = [(r, q) for r, q in One.SINGLE if r[1] in CUT]
    parts.append("\n".join(
        f"{esc(r[1])} & {money(r[3] * q)} & {CUT[r[1]]} \\\\"
        for r, q in sorted(cut_rows, key=lambda x: -x[0][3] * x[1])))
    parts.append(r"\midrule")
    parts.append(r"\multicolumn{1}{@{}r}{\thead{Parts not bought}} & \thead{"
                 + money(sum(r[3] * q for r, q in cut_rows)) + r"} & \\")
    parts.append(r"\bottomrule")
    parts.append(r"\end{longtable}")
    parts.append(r"\endgroup")

    body = "\n".join(parts)
    assert not any(ord(c) < 32 and c != "\n" for c in body), "control char in tables"
    io.open(OUT_TABLES, "w", encoding="utf-8", newline="\n").write(HEADER + body)


def write_letters():
    saved, L.N = L.N, N
    try:
        out, grand = [], 0.0
        for ph, objective, gate, _amt in ROWS:
            lines = LINES[ph]
            tot = sum(x[4] for x in lines)
            grand += tot
            out.append(letter(ph, objective, gate, lines, tot))
    finally:
        L.N = saved
    assert abs(grand - total()) < 1.0, \
        f"letters total {grand:.2f} but the MVP parts list is {total():.2f}"
    body = "".join(out)
    assert not any(ord(c) < 32 and c != "\n" for c in body), "control character"
    for key in ("PHASE", "TOTALAMT", "SMALLFONT", "BOXRULE", "OBJECTIVE"):
        assert key not in body, f"unreplaced key: {key}"
    io.open(OUT_LETTERS, "w", encoding="utf-8", newline="\n").write(HEADER + body)
    return grand


def check_prose(grand, parts):
    """The brief quotes these totals in running text; nothing else would catch
    a price moving underneath them. See build_single_brief.check_prose."""
    if not os.path.exists(BRIEF):
        return
    text = io.open(BRIEF, encoding="utf-8").read()
    want = {
        "released, MVP":        grand,
        "parts, MVP":           parts,
        "phase 1":              ROWS[0][3],
        "phases 1 and 2":       sum(a for ph, _, _, a in ROWS if ph in (1, 2)),
        "released, one full aircraft": sum(a for _, _, _, a in One.ROWS),
        "released, three aircraft":    One._full_released(),
    }
    missing = [f"{k} ({money(v)})" for k, v in want.items()
               if RS + "{" + money(v) + "}" not in text]
    assert not missing, ("mentor-brief-mvp.tex does not quote: "
                         + ", ".join(missing) + " -- prose has drifted")


def main():
    write_tables()
    grand = write_schedule()
    parts = write_letters()
    check_prose(grand, parts)
    r = os.path.relpath
    print(f"  wrote {r(OUT_SCHED, ROOT)}  ({N} phases, {grand:,.0f} released)")
    print(f"  wrote {r(OUT_TABLES, ROOT)}  ({len(MVP)} rows, "
          f"{len(CUT)} listed as not bought)")
    print(f"  wrote {r(OUT_LETTERS, ROOT)}  ({N} letters)")
    print(f"  parts {parts:,.0f}   released {grand:,.0f}")
    print(f"  vs one full aircraft {sum(a for _, _, _, a in One.ROWS):,.0f}"
          f"   vs three {One._full_released():,.0f}")


if __name__ == "__main__":
    main()
