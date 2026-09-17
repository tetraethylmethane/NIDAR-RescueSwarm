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
OUT_SCHED = os.path.join(ROOT, "docs", "proposal", "generated-brief-schedule.tex")

# Phase numbers per group, as the schedule allocates them.
PHASES = {"instruments": "1--2", "avionics": "3--6", "airframe": "7--10",
          "flighttest": "11--12", "ground": "29--32"}
REPEATS = {"avionics": "repeated at 13--16 and 21--24",
           "airframe": "repeated at 17--20 and 25--28"}

# The reasoning a reader is being asked to accept. Lines without an entry are
# self-evident from the model column and get the supplier only.
RATIONALE = {
 # Plain English, one line. The reader is a faculty mentor deciding whether to
 # fund this, not an engineer reviewing the electrical design -- the numbers
 # that justify each choice live in the technical proposal, not here.
 "Load-cell amplifier": "Turns the load cell's signal into a reading we can log.",
 "Throttle source":
   "A motor on a stand needs something to command it. The safety-pilot "
   "transmitter is not bought until phase 11, long after this test.",
 "Load cell":
   "The motors ship without a thrust curve, so we measure it ourselves. "
   "Ready-made stands cost around ten times this.",
 "Thrust-stand mast":
   "Holds the motor clear of the bench, so its own draught does not flatter "
   "the reading.",
 "Fasteners": "A carbon airframe is bolted, not glued.",
 "Threadlocker":
   "Stops bolts working loose under motor vibration. Medium strength, so a "
   "joint can still be undone.",

 "Flight controller":
   "The autopilot: flies the aircraft and runs its safety behaviours. "
   "Previously a quotation, now ordinary retail.",
 "Autopilot log card":
   "The autopilot ships without one and records nothing without it. This is a "
   "different slot on a different board from the computer's card above.",
 "Frame plate stock":
   "The arms are tubes; this is the plate they bolt to. One sheet yields the "
   "top and bottom of a centre section at this size.",
 "FC vibration mount":
   "Isolates the autopilot from propeller vibration, which otherwise confuses "
   "its sensors.",
 "Companion computer":
   "The computer the autonomy runs on. The accelerator and the camera both "
   "plug into it, so neither works without it.",
 "AI accelerator":
   "Runs the person-detection model fast enough to search at flying speed.",
 "Compute cooling":
   "The hottest moment is the setup on the ground, before the propellers are "
   "turning and cooling it.",
 "Storage":
   "Records every frame and detection for a whole mission. Ordinary cards wear "
   "out at that rate.",
 "GNSS RTK receiver":
   "Centimetre positioning for aircraft 1 and the ground station it corrects "
   "against. Only one aircraft carries it: all three are the same machine, so "
   "measuring one against surveyed ground is what tells us how well the design "
   "works. Quoted by the supplier; this line was an estimate before.",
 "GNSS receiver":
   "Positioning for aircraft 2 and 3, accurate to about two metres against a "
   "five metre requirement. Carries the compass the flight controller needs, "
   "and plugs straight into it.",
 "Height rangefinder":
   "Measures true height above whatever is below --- water, ground or a "
   "rooftop. The kit is released at 6 m, and the barometer measures height "
   "above the launch point, which over floodwater is a different thing.",
 "Camera + lens":
   "The search sensor, chosen so a person in water is large enough in the "
   "picture to be found.",
 "Video transmitter":
   "Sends the live picture down, one channel per aircraft.",
 "Command receiver":
   "Carries the safety pilot's control and the aircraft's reporting on a "
   "single link, which saves a second radio.",
 "Coordination radio":
   "How the three aircraft tell each other what they have found. The most "
   "robust link on the aircraft, which is where survivor positions belong.",
 "Power module":
   "Reports battery voltage and current to the autopilot, which is what "
   "triggers a low-battery return.",
 "BEC, primary":
   "Powers the computer. Deliberately oversized: losing it in flight is the "
   "failure this line exists to prevent.",
 "BEC, secondary":
   "A separate supply for the servos, so a jammed servo cannot disturb the "
   "autopilot.",

 "Motors":
   "Twelve. The first is measured on the stand before the other eleven are "
   "bought.",
 "Propellers":
   "Sixteen for twelve positions. The item most often broken in flight "
   "testing, and the whole of our spares policy.",
 "Speed controllers":
   "One board drives all four motors. Made in India, and previously a "
   "quotation.",
 "Arm tube":
   "The four arms. Carbon, and comfortably strong --- the joints, not the "
   "tubes, are what limit the airframe.",
 "Motor mounts":
   "Joins motor to arm without machining the tube. This joint is the part that "
   "has to be right.",
 "Arm clamps":
   "Bolted rather than bonded, so an arm damaged in a heavy landing is swapped "
   "in the field instead of scrapping the frame.",
 "Landing gear":
   "Gives clearance underneath for the kit magazine, and a stance wide enough "
   "for an untidy landing.",
 "Suspension springs":
   "Let the legs absorb a hard landing rather than pass it into the arms and "
   "the battery.",
 "Printed parts":
   "Filament for the magazine, mounts and covers. Holds its shape in the sun, "
   "which cheaper filament does not.",
 "Release servos":
   "Open the four kit stations. Metal gears, because a plastic one can drop a "
   "kit without anyone knowing.",
 "Cells":
   "The battery: enough for the mission, a second full search, and four "
   "minutes in hand.",
 "Cell holders":
   "Hold the cells in place and keep them apart, so one failing cell does not "
   "take its neighbours with it.",
 "Pack interconnect":
   "Joins the cells. Pure nickel, because the cheaper plated strip runs hot at "
   "the current this battery delivers.",
 "Group interconnect": "Joins the battery's groups, where the current is highest.",
 "Balance leads":
   "How the charger checks each cell. With no battery board fitted, this is "
   "our only per-cell check --- and it happens on every charge.",
 "Pack fusing":
   "Protects against a short circuit without cutting power at full throttle.",
 "Pack retention":
   "Holds the battery down. It is a fifth of the aircraft's weight, so a strap "
   "that lets go is not a small problem.",
 "Main leads":
   "The main power cable, sized for the highest current the motors ever draw "
   "rather than the average.",
 "Power connectors":
   "Anti-spark, so connecting a battery this size does not burn the contacts.",
 "Signal connectors":
   "Keyed, so the wiring can only go back together one way after a repair.",
 "Antenna feeders":
   "Let the antennas mount on the airframe instead of hanging off the radios.",
 "Insulation":
   "Sleeving over the battery joints --- the one place on the aircraft where a "
   "rubbed wire is an immediate fire.",

 "Safety-pilot transmitter":
   "Manual override for the safety pilot, independent of the autonomy. A rule "
   "requirement and a safety one.",
 "Battery charger":
   "Two batteries recharged between flights is what sets how many tests fit "
   "into a day.",
 "Pack health monitor":
   "A bench instrument for tracking how the batteries age over the programme.",
 "Cable management": "Ties long enough to dress wiring around a one-metre airframe.",
 "Heat-shrink kit": "Insulates the signal wiring during assembly.",
 "Mounting tape":
   "Holds radios and receivers where a screw would need a fixing the printed "
   "part cannot carry.",
 "Hook and loop":
   "For the battery and anything else that must come out between flights "
   "without tools.",
 "Consumables":
   "Solder, abrasives, spare hardware, filament. A round figure, because "
   "itemising it would be false precision.",

 "Video receivers":
   "Three, so the ground station can show all three aircraft at once, which "
   "the rules require.",
 "Receive antennas":
   "The ground antennas. Most of the video range comes from these rather than "
   "from the transmitters.",
 "Video capture": "Brings the three pictures into the ground station computer.",
 "Coordination base":
   "The ground end of the link the aircraft use to report what they find.",
 "Base station mount":
   "Holds the ground receiver still during a mission. Survey-grade accuracy is "
   "unnecessary; not moving is what matters.",
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
        # The column header promises "why this part". A row with no rationale
        # answers only "from whom", which is how 33 of these once shipped.
        note = RATIONALE[item]
        sup = supplier_of(url)
        note = note + " " + (
            f"\\textit{{{sup}}}" if sup != "in-house" else "\\textit{in-house}")
        qtytxt = f", {qty} off" if qty > 1 else ""
        out.append(f"{esc(item)} & {esc(model)}{qtytxt} "
                   f"& {money(unit * qty)} & {note} \\\\")
    return "\n".join(out)



# The objective and the gate for each phase. Amounts are NOT here -- they are
# derived from the BOM by sourced_bom.phase_released(), so a price change moves
# the schedule instead of silently contradicting it.
SCHEDULE = [
 (1,  "Establish thrust and mass measurement capability", "Approval"),
 (2,  "Measure one motor, propeller and speed controller on the stand", "Instruments commissioned"),
 (3,  "Aircraft 1 --- autopilot and control link", r"\textbf{Thrust verified}"),
 (4,  "Aircraft 1 --- onboard computer and AI accelerator", "Autopilot bench-tested"),
 (5,  "Aircraft 1 --- centimetre positioning: RTK rover and ground base", "Compute stack operating"),
 (6,  "Aircraft 1 --- camera and the three radios", "Position fix acquired"),
 (7,  "Aircraft 1 --- airframe fabrication", "Avionics integrated"),
 (8,  "Aircraft 1 --- battery pack and power distribution", "Airframe fabricated"),
 (9,  "Aircraft 1 --- release servos and wiring", "Pack bench-discharged"),
 (10, "Aircraft 1 --- propulsion completed", "Drive train installed"),
 (11, "Charging, pack instrumentation and manual override", "Aircraft assembled and weighed"),
 (12, "Field consumables and assembly materials", "Charging verified"),
 (13, "Aircraft 2 --- autopilot and control link", r"\textbf{Aircraft 1 flew a full mission}"),
 (14, "Aircraft 2 --- onboard computer and AI accelerator", "Autopilot bench-tested"),
 (15, "Aircraft 2 --- satellite positioning and compass", "Compute stack operating"),
 (16, "Aircraft 2 --- camera and the three radios", "Position fix acquired"),
 (17, "Aircraft 2 --- airframe fabrication", "Avionics integrated"),
 (18, "Aircraft 2 --- battery pack and power distribution", "Airframe fabricated"),
 (19, "Aircraft 2 --- speed controllers, release servos, wiring", "Pack bench-discharged"),
 (20, "Aircraft 2 --- propulsion completed", "Drive train installed"),
 (21, "Aircraft 3 --- autopilot and control link", r"\textbf{Two aircraft, separation verified}"),
 (22, "Aircraft 3 --- onboard computer and AI accelerator", "Autopilot bench-tested"),
 (23, "Aircraft 3 --- satellite positioning and compass", "Compute stack operating"),
 (24, "Aircraft 3 --- camera and the three radios", "Position fix acquired"),
 (25, "Aircraft 3 --- airframe fabrication", "Avionics integrated"),
 (26, "Aircraft 3 --- battery pack and power distribution", "Airframe fabricated"),
 (27, "Aircraft 3 --- speed controllers, release servos, wiring", "Pack bench-discharged"),
 (28, "Aircraft 3 --- propulsion completed", "Drive train installed"),
 (29, "Ground station: three video feeds, data link, base mount", "Third aircraft flying"),
]


def schedule_table():
    rel = S.phase_released()
    assert set(rel) == {p for p, _, _ in SCHEDULE}, "phase set disagrees with BOM"
    out = []
    for ph, obj, gate in SCHEDULE:
        out.append(f"{ph} & {obj} & {money(rel[ph])} & {gate} \\\\")
    return "\n".join(out), sum(rel.values())


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

    # rows() indexes RATIONALE directly, so a row without an argument already
    # fails the build. This catches the other direction: a rationale left
    # behind for a part that is no longer bought.
    items = {r[1] for r in S.BOM}
    orphans = sorted(set(RATIONALE) - items)
    assert not orphans, f"rationale for parts no longer in the BOM: {orphans}"
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

    sched, sched_total = schedule_table()
    assert sched.count("\\textbf") == 3, "schedule: lost a backslash"
    assert not any(ord(c) < 32 and c != "\n" for c in sched), "schedule: control char"
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
\multicolumn{2}{@{}r}{\thead{Total}} & \thead{""" + money(sched_total)
           + r"""} & \\
\bottomrule
\endlastfoot
""")
    post = "\n" + r"""\end{longtable}
\endgroup""" + "\n"
    io.open(OUT_SCHED, "w", encoding="utf-8", newline="\n").write(
        header + pre + sched + post)
    print(f"  wrote {os.path.relpath(OUT_SCHED, ROOT)}  "
          f"({len(SCHEDULE)} phases, {sched_total:,.0f} released)")
    n = sum(1 for _ in S.BOM)
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  ({n} rows, "
          f"{len(RATIONALE)} with a stated rationale)")
    print(f"  parts total {S.total():,.0f}   with GST {S.total() * 1.18:,.0f}")


if __name__ == "__main__":
    main()
