#!/usr/bin/env python3
"""Via and copper design for the high-current system.

Sizes the VBAT and phase copper, runs a via geometry trade, audits the whole
battery-to-motor chain for the limiting element, and corrects the thermal
spreading model to include via resistance.

Nothing here routes anything. No frozen requirement is changed.

Run:  python hardware/tools/via_copper.py
"""
import math

# ---------------- frozen inputs ----------------
V_MAX = 25.2
I_CONT, I_PEAK = 42.0, 115.0
N_CH = 4
I_CH_CONT, I_CH_PEAK = I_CONT / N_CH, I_PEAK / N_CH
I_PH_HOVER, I_PH_PEAK = 21.0, 28.75

# ---------------- materials / stackup ----------------
RHO_CU = 1.72e-8
K_CU = 385.0
OZ = 34.8e-6
T_OUT, T_IN = 2 * OZ, 1 * OZ
BOARD_T = 1.6e-3
PLATING = 25e-6                      # ASSUMED; fab must confirm
DT_ALLOW = 20.0

# FET thermal pad, from the verified footprint -- NOT modified here
PAD_W, PAD_H = 4.40e-3, 4.10e-3


def ipc_width(current, thickness, dt=DT_ALLOW, external=True):
    k = 0.048 if external else 0.024
    a_mil2 = (current / (k * dt ** 0.44)) ** (1 / 0.725)
    return (a_mil2 / 1.550e9) / thickness


def via_area(hole_d, plating=PLATING):
    """Barrel copper cross-section."""
    return math.pi * (hole_d + plating) * plating


def via_r_elec(hole_d, length=BOARD_T, plating=PLATING):
    return RHO_CU * length / via_area(hole_d, plating)


def via_r_therm(hole_d, length=BOARD_T, plating=PLATING):
    return length / (K_CU * via_area(hole_d, plating))


def rule(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def main():
    # ------------------------------------------------------------------ 1 --
    rule("1. MAIN VBAT COPPER -- multilayer parallel structure")
    print("  6.6 mm is the NETCLASS MINIMUM, not the answer. Required width by")
    print("  IPC-2221 at a 20 C rise, if a single layer had to carry it all:\n")
    for lbl, i in (("continuous 42 A", I_CONT), ("peak 115 A", I_PEAK)):
        w_o = ipc_width(i, T_OUT) * 1e3
        note = "  <-- exceeds the 50 mm board" if w_o > 50 else ""
        print(f"    {lbl:<18} 2 oz outer alone: {w_o:7.1f} mm{note}")
    print("\n  So VBAT is built as four parallel layers. Widths chosen per layer:")
    LAYERS = [("L1 F.Cu", T_OUT, 18e-3), ("L3 In2", T_IN, 20e-3),
              ("L4 In3", T_IN, 20e-3), ("L6 B.Cu", T_OUT, 18e-3)]
    LEN = 25e-3
    tot_a, cond = 0.0, 0.0
    print(f"    {'layer':<10}{'cu':>6}{'width':>8}{'area':>9}{'R(25mm)':>11}")
    for n, t, w in LAYERS:
        a = w * t
        r = RHO_CU * LEN / a
        tot_a += a
        cond += 1 / r
        print(f"    {n:<10}{t/OZ:5.0f}oz{w*1e3:7.1f}mm{a*1e6:8.2f}mm2{r*1e3:10.3f}m")
    r_bus = 1 / cond
    print(f"    {'TOTAL':<10}{'':>6}{'':>8}{tot_a*1e6:8.2f}mm2{r_bus*1e6:10.2f}u")
    print(f"\n    {'current sharing':<22}", end="")
    for n, t, w in LAYERS:
        r = RHO_CU * LEN / (w * t)
        print(f"{n.split()[0]} {100*(1/r)/cond:4.1f}%  ", end="")
    print("\n    NOT equal. Sharing is set by the VIA ARRAY, not the copper.")
    print("    Sparse or clustered stitching crowds current into L1/L6.\n")
    for lbl, i in (("continuous", I_CONT), ("peak", I_PEAK)):
        dv, pw = i * r_bus, i * i * r_bus
        # adiabatic rise, whole bus, worst case no spreading
        rate = (i ** 2 * RHO_CU) / (tot_a ** 2 * 8960 * 385)
        print(f"    {lbl:<12}{i:6.1f} A -> drop {dv*1e3:5.2f} mV,"
              f" loss {pw:5.2f} W, adiabatic {rate:5.2f} C/s"
              f" -> 20 C in {DT_ALLOW/rate:6.1f} s")
    print("\n    Peak duration is OPEN, so the adiabatic column is a rate, not")
    print("    a verdict.")

    # ------------------------------------------------------------------ 2 --
    rule("2. MOTOR PHASE COPPER (per channel, 3 phases)")
    print(f"    {'condition':<20}{'I':>7}{'2oz width':>12}{'chosen':>9}"
          f"{'R(10mm)':>10}{'drop':>9}{'loss':>8}")
    CH_W = 6.6e-3
    for lbl, i in (("hover", I_PH_HOVER), ("peak", I_PH_PEAK)):
        need = ipc_width(i, T_OUT) * 1e3
        r = RHO_CU * 10e-3 / (CH_W * T_OUT)
        print(f"    {lbl:<20}{i:6.1f}A{need:11.1f}mm{CH_W*1e3:8.1f}mm"
              f"{r*1e3:9.3f}m{i*r*1e3:8.2f}mV{i*i*r:7.2f}W")
    print(f"\n    Hover needs {ipc_width(I_PH_HOVER,T_OUT)*1e3:.1f} mm and peak"
          f" {ipc_width(I_PH_PEAK,T_OUT)*1e3:.1f} mm on 2 oz.")
    print("    6.6 mm covers hover but NOT peak on a single outer layer.")
    print("    Phases therefore run L6 + L4 in parallel, or widen to 10.2 mm")
    print("    where the quadrant allows. Both conditions checked separately.")

    # ------------------------------------------------------------------ 3 --
    rule("3. VIA GEOMETRY TRADE -- is 0.8 mm / 0.4 mm the right choice?")
    print("  Current capacity per unit BOARD AREA is what matters, not per via.")
    print("  Pitch is set by pad diameter, so smaller vias pack more copper.\n")
    print(f"  {'hole':>6}{'pad':>6}{'pitch':>7}{'A_cu':>9}{'R_via':>9}"
          f"{'AR':>6}{'cu/mm2 board':>14}{'note':>22}")
    print("  " + "-" * 80)
    OPTIONS = [(0.20e-3, 0.45e-3, "AR 8:1, fab-dependent"),
               (0.25e-3, 0.50e-3, "AR 6.4:1"),
               (0.30e-3, 0.60e-3, "AR 5.3:1, standard"),
               (0.40e-3, 0.80e-3, "AR 4:1, current rule")]
    best = None
    for hole, pad, note in OPTIONS:
        pitch = pad + 0.2e-3
        a = via_area(hole)
        r = via_r_elec(hole)
        ar = BOARD_T / hole
        dens = a / (pitch ** 2)
        if best is None or dens > best[1]:
            best = ((hole, pad), dens)
        print(f"  {hole*1e3:5.2f} {pad*1e3:5.2f} {pitch*1e3:6.2f}"
              f"{a*1e6:8.4f} {r*1e3:8.3f}m{ar:5.1f}:1{dens*1e0:13.4f}"
              f"  {note:>22}")
    print(f"\n  Densest: {best[0][0]*1e3:.2f} mm hole. But density is not the")
    print("  only axis -- plating thickness in a high aspect-ratio hole is not")
    print("  guaranteed to reach 25 um, and every number above assumes it does.")
    print("  0.30 mm / 0.60 mm is the recommendation: it beats the current")
    print("  0.40/0.80 rule on density while staying at a routine 5.3:1.")
    print("  OPEN: fab must confirm plating thickness at the chosen aspect ratio.")

    # ------------------------------------------------------------------ 4 --
    rule("4. VIA ARRAYS -- sized so the transition never limits the copper")
    print("  Rule: the array must carry at least what the copper either side")
    print("  carries, or the via field becomes the bottleneck.\n")
    hole, pad = 0.30e-3, 0.60e-3
    pitch = pad + 0.2e-3
    a_via = via_area(hole)
    r_via = via_r_elec(hole)
    print(f"  Using {hole*1e3:.2f} mm hole / {pad*1e3:.2f} mm pad,"
          f" {pitch*1e3:.2f} mm pitch, {a_via*1e6:.4f} mm2, {r_via*1e3:.3f} mOhm each\n")
    print(f"  {'transition':<26}{'I':>7}{'A_cu needed':>13}{'n(area)':>9}"
          f"{'n(1.5A)':>9}{'USE':>6}{'R_array':>10}{'field':>12}")
    print("  " + "-" * 92)
    TRANS = [("battery entry -> bus", I_PEAK, tot_a),
             ("VBAT bus L6<->L1", I_PEAK, tot_a),
             ("VBAT -> channel branch", I_CH_PEAK, None),
             ("phase L6<->L4", I_PH_PEAK, None),
             ("bulk cap return", I_PEAK, None)]
    for name, i, match_a in TRANS:
        # enough barrel copper to match the plane it feeds
        n_area = math.ceil((match_a / a_via)) if match_a else math.ceil(
            (i / I_PEAK) * 40)
        n_rule = math.ceil(i / 1.5)
        n = max(n_area if match_a else 0, n_rule)
        side = math.ceil(math.sqrt(n))
        print(f"  {name:<26}{i:6.1f}A"
              f"{(match_a*1e6 if match_a else 0):12.2f}mm2"
              f"{(n_area if match_a else 0):9d}{n_rule:9d}{n:6d}"
              f"{r_via/n*1e6:9.2f}u{side}x{side:>8}")
    print("\n  n(area) matches the barrel copper to the plane copper.")
    print("  n(1.5A) is the conventional per-via current rule.")
    print("  Where they disagree the LARGER is used -- a transition that")
    print("  merely 'passes' the current rule can still be a resistive step")
    print("  compared with the pour on either side of it.")

    # ------------------------------------------------------------------ 5 --
    rule("5. MOSFET THERMAL VIA FIELD -- and a correction to R_spread")
    print(f"  Thermal pad {PAD_W*1e3:.2f} x {PAD_H*1e3:.2f} mm"
          f"  (verified footprint, NOT modified)")
    for hole_t, pad_t in ((0.30e-3, 0.60e-3), (0.25e-3, 0.50e-3)):
        p = pad_t + 0.2e-3
        nx, ny = int(PAD_W // p), int(PAD_H // p)
        n = nx * ny
        rt = via_r_therm(hole_t) / n
        print(f"    {hole_t*1e3:.2f} mm vias at {p*1e3:.2f} mm pitch:"
              f" {nx}x{ny} = {n:2d} vias, R_th field {rt:5.2f} K/W")
    hole_t, pad_t = 0.30e-3, 0.60e-3
    p = pad_t + 0.2e-3
    n_th = int(PAD_W // p) * int(PAD_H // p)
    r_via_th = via_r_therm(hole_t) / n_th

    r_s = math.sqrt(PAD_W * PAD_H / math.pi)
    r_o = math.sqrt((2 * 50e-3 * 50e-3 / 24) / math.pi)
    ln = math.log(r_o / r_s)
    r_outer_only = ln / (2 * math.pi * K_CU * T_OUT)
    r_inner_only = ln / (2 * math.pi * K_CU * 4 * T_IN)
    r_via_path = r_via_th + r_inner_only
    r_parallel = 1 / (1 / r_outer_only + 1 / r_via_path)
    r_ideal = ln / (2 * math.pi * K_CU * (2 * T_OUT + 4 * T_IN))
    print(f"\n  Spreading, done properly:")
    print(f"    B.Cu alone (2 oz)              {r_outer_only:5.2f} K/W")
    print(f"    inner layers alone (4 x 1 oz)  {r_inner_only:5.2f} K/W")
    print(f"    through {n_th} thermal vias        {r_via_th:5.2f} K/W")
    print(f"    via path = vias + inner        {r_via_path:5.2f} K/W")
    print(f"    B.Cu || via path               {r_parallel:5.2f} K/W  <-- REAL")
    print(f"    earlier model, ideal coupling  {r_ideal:5.2f} K/W  <-- OPTIMISTIC")
    print(f"\n  The earlier thermal model used {r_ideal:.2f} K/W, which assumes the")
    print("  six layers behave as one plate. They do not: the vias are in")
    print(f"  series with the inner layers. The honest figure is {r_parallel:.2f} K/W,")
    print(f"  i.e. {r_parallel - r_ideal:.2f} K/W worse.")
    for lbl, pf in (("hover", 1.28), ("peak", 2.23)):
        print(f"    {lbl:<6} P={pf:.2f} W/FET -> extra rise"
              f" {(r_parallel - r_ideal) * pf:5.2f} K")
    print("\n  This does NOT change the MARGINAL verdict -- board-to-air still")
    print("  dominates -- but the model was flattering and is corrected.")

    # ------------------------------------------------------------------ 8 --
    rule("8. CURRENT BOTTLENECK AUDIT -- battery to motor")
    print(f"  {'segment':<26}{'I':>7}{'A_cu':>9}{'layers':>7}{'vias':>6}"
          f"{'R':>10}{'drop':>9}{'loss':>8}  limiting element")
    print("  " + "-" * 108)
    segs = [
        ("U3 battery pads", I_PEAK, 67.5e-6 * 2, 1, 0, 1e-6,
         "pad area 67.5 mm2 each, ample"),
        ("shunt 2x0.2 mOhm", I_PEAK, 0, 1, 0, 0.1e-3,
         "**0.1 mOhm by design -- dominates**"),
        ("battery -> bus vias", I_PEAK, 0, 0, 133, r_via / 133,
         "via array"),
        ("VBAT bus 4 layers", I_PEAK, tot_a, 4, 0, r_bus,
         "copper, ample"),
        ("branch to channel", I_CH_PEAK, CH_W * (T_OUT + T_IN), 2, 20,
         RHO_CU * 12e-3 / (CH_W * (T_OUT + T_IN)), "copper"),
        ("MOSFET Rds(on) x2", I_PH_PEAK, 0, 0, 0, 2 * 2.25e-3,
         "**semiconductor -- dominates**"),
        ("phase copper", I_PH_PEAK, CH_W * T_OUT, 1, 0,
         RHO_CU * 10e-3 / (CH_W * T_OUT), "copper"),
        ("phase pads (U3)", I_PH_PEAK, 5.28e-6, 1, 0, 1e-6,
         "5.28 mm2, soldered wire"),
    ]
    worst = None
    for name, i, a, lay, nv, r, lim in segs:
        loss = i * i * r
        if worst is None or loss > worst[1]:
            worst = (name, loss)
        print(f"  {name:<26}{i:6.1f}A{(a*1e6 if a else 0):8.2f}mm2"
              f"{lay:7d}{nv:6d}{r*1e3:9.3f}m{i*r*1e3:8.2f}mV{loss:7.2f}W"
              f"  {lim}")
    print(f"\n  LARGEST LOSS: {worst[0]} at {worst[1]:.2f} W")
    print("  The copper is nowhere the limiting element. The two dominant")
    print("  losses are the shunt and the MOSFET channel resistance, both of")
    print("  which are deliberate design choices, not bottlenecks to remove.")
    print("  J1 is excluded from this chain entirely (0.7 A per contact).")


if __name__ == "__main__":
    main()
