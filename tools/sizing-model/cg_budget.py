"""CG budget -- where the heavy things go, and what moves when kits are dropped.

WHY THIS EXISTS
Two masses dominate this airframe and both are movable in CAD:

    battery pack    1449 g   22.8 % of MTOW
    survivor kits    800 g   12.6 %, and it LEAVES during the mission

A multirotor trims a CG offset with differential thrust. That is not free: it
costs control margin, it costs a little power, and -- the part that matters
here -- it CHANGES between drops. Delivery accuracy is worth 200 points and is
flown by an autopilot that has to re-trim after every release.

So the question CAD needs answered is not "where does the battery fit" but
"how much CG excursion is acceptable, and which magazine layout and release
order stay inside it".

Run:  python tools/sizing-model/cg_budget.py
"""
from __future__ import annotations

import itertools
import math

# --- from the sizing model's mass statement --------------------------------
MTOW_G = 6360.0
KIT_G = 200.0
N_KITS = 4
PACK_G = 1449.0
WHEELBASE_MM = 761.0          # motor-to-motor diagonal, 20 in clearance
ARM_R_MM = WHEELBASE_MM / 2   # rotor radius arm from centre
G = 9.81
W = 78


def rule(t=""):
    print("=" * W)
    if t:
        print(t)
        print("=" * W)


def cg_shift_mm(removed_g: float, offset_mm: float, total_g: float = MTOW_G) -> float:
    """CG movement when `removed_g` at `offset_mm` from the CG leaves.

    Removing mass m at distance d from the CG of total M moves the CG by
    -m*d/(M-m), away from where the mass was.
    """
    return -removed_g * offset_mm / (total_g - removed_g)


def trim_fraction(cg_mm: float, total_g: float) -> float:
    """Fraction of hover thrust that has to be traded between rotor pairs.

    Moment from the offset is W*d; it is reacted by a differential across the
    two rotor pairs at ARM_R_MM. Expressed against per-rotor hover thrust,
    which is what eats control margin.
    """
    weight_n = total_g / 1000.0 * G
    moment = weight_n * cg_mm / 1000.0
    diff_n = moment / (2 * ARM_R_MM / 1000.0)
    hover_per_rotor = weight_n / 4.0
    return diff_n / hover_per_rotor


rule("STATIC CG -- what a placement error costs")
print("  A build tolerance on where the pack sits is a permanent trim offset.")
print()
print(f"  {'pack offset':>13}{'CG shift':>11}{'trim':>9}   note")
for off in (0, 5, 10, 20, 40):
    shift = PACK_G * off / MTOW_G
    tf = trim_fraction(shift, MTOW_G)
    note = ""
    if off == 10:
        note = "a plausible build tolerance"
    if off == 40:
        note = "a pack seated the wrong way round in its tray"
    print(f"  {off:>10.0f} mm{shift:>10.1f} mm{tf:>8.1%}   {note}")
print()
print("  The pack is 22.8 % of MTOW, so its offset transfers to the CG at")
print("  roughly 0.23 mm per mm. That is forgiving -- but it is also why the")
print("  tray must be a REPEATABLE location, not a strap: a pack that seats")
print("  differently each flight re-trims the aircraft each flight.")

rule("KIT RELEASE -- the CG walks during the mission")
print("  800 g of the 6360 g leaves, one kit at a time, at whatever survivor")
print("  the mission finds. The airframe cannot choose when; it can only")
print("  choose the LAYOUT and the ORDER.")
print()

layouts = {
    "2x2 around the CG (+/-100, +/-55 mm)":
        [(-100.0, -55.0), (100.0, -55.0), (-100.0, 55.0), (100.0, 55.0)],
    "row of 4 fore-aft (+/-165, +/-55 mm)":
        [(0.0, -165.0), (0.0, -55.0), (0.0, 55.0), (0.0, 165.0)],
    "row of 4 across (+/-165, +/-55 mm)":
        [(-165.0, 0.0), (-55.0, 0.0), (55.0, 0.0), (165.0, 0.0)],
}


def worst_excursion(positions, order):
    """Largest CG offset seen at any point through a release order."""
    worst = 0.0
    remaining = list(range(len(positions)))
    total = MTOW_G
    for k in order:
        remaining.remove(k)
        total -= KIT_G
        # CG of what is left: only the kits are off-centre by construction
        mx = sum(positions[i][0] for i in remaining) * KIT_G
        my = sum(positions[i][1] for i in remaining) * KIT_G
        d = math.hypot(mx, my) / total
        worst = max(worst, d)
    return worst


for name, pos in layouts.items():
    best_order = min(itertools.permutations(range(N_KITS)),
                     key=lambda o: worst_excursion(pos, o))
    worst_order = max(itertools.permutations(range(N_KITS)),
                      key=lambda o: worst_excursion(pos, o))
    b = worst_excursion(pos, best_order)
    w = worst_excursion(pos, worst_order)
    print(f"  {name}")
    print(f"     best release order  {list(best_order)}   peak CG offset "
          f"{b:5.1f} mm  trim {trim_fraction(b, MTOW_G - KIT_G):4.1%}")
    print(f"     worst order         {list(worst_order)}   peak CG offset "
          f"{w:5.1f} mm  trim {trim_fraction(w, MTOW_G - KIT_G):4.1%}")
    print()

print("  READ THAT TABLE AGAIN BEFORE CONSTRAINING THE CAD.")
print()
print("  Layout barely matters: best-order peak excursion is 3.7 mm for both")
print("  rows and 4.0 mm for the 2x2. The row is marginally BETTER, which is")
print("  the opposite of the tidy answer, because a row lets you alternate")
print("  about the centre while a 2x2 forces a corner to be last.")
print()
print("  ORDER matters about twice as much as layout: 3.7 mm against 7.4 mm")
print("  on the same row, purely from which kit goes first.")
print()
print("  And every number here is small -- under 4 % of hover thrust in the")
print("  worst case. This is NOT a stability problem and it should NOT be")
print("  used to constrain the magazine geometry. Lay the magazine out for")
print("  PACKAGING and drop-path clearance; the CG will follow.")
print()
print("  What it IS: a repeatability nudge. Each release steps the trim and")
print("  the autopilot needs a moment to settle before the next drop is")
print("  accurate. That makes release ORDER an autonomy decision worth making")
print("  deliberately -- alternate about the centre rather than working along")
print("  the magazine -- and it costs nothing to get right.")

rule("VERTICAL CG -- the one that is easy to get wrong")
print("  The pack is the heaviest item and the most tempting to hang low for")
print("  'stability'. On a multirotor that is a myth worth naming: the rotors")
print("  are the control effectors, and a CG far BELOW the rotor plane makes")
print("  the airframe a pendulum that the controller has to fight, coupling")
print("  attitude into translation exactly during the slow, precise hover a")
print("  delivery needs.")
print()
print("  Keep the pack CG as close to the rotor plane as the geometry allows.")
print("  The magazine hangs below by necessity -- kits have to fall -- so the")
print("  pack should not add to that.")
print()
print("  Concrete consequence for the bay: the 6S3P block is 63 mm deep bare")
print("  against 42 mm for the superseded 6S2P. Those 21 mm should be taken")
print("  by making the tray WIDER or LONGER, not by dropping it 21 mm lower.")

rule("WHAT THIS MEANS FOR CAD")
print("  1. Side-loading battery tray with a captive latch and a hard stop.")
print("     Repeatability beats adjustability: the same pack in the same place")
print("     every flight is what keeps trim constant. It also keeps the swap")
print("     off the critical path -- see setup_budget.py -- and avoids")
print("     disturbing the parachute mount above or the magazine below.")
print("  2. Magazine geometry: choose it for PACKAGING and drop-path clearance,")
print("     not for CG. The sweep above says layout is worth 0.3 mm and order")
print("     is worth 3.7 mm, and all of it is under 4 % of hover thrust.")
print("     Centre the group on the CG and stop optimising there.")
print("  2a. Release ORDER is the part worth deciding: alternate about the")
print("     centre instead of working along the magazine. That is autonomy's")
print("     job, not CAD's, and it halves the peak excursion for free.")
print("  3. Pack CG in the rotor plane, not slung under it.")
print("  4. Current shunt for BATT_MONITOR=4 must be in the pack path and")
print("     reachable: BATT_RESISTANCE has to be MEASURED on the real pack")
print("     before first flight -- see battery_failsafe.py, where an unset")
print("     resistance had the low-battery failsafe firing at 53 % SoC.")
rule()
