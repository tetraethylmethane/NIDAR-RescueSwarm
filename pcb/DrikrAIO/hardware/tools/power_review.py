#!/usr/bin/env python3
"""Electrical design review calculations for DrikrAIO.

Every number in docs/electrical-design-review.md comes from here. Device
parameters are quoted from the committed datasheets in
hardware/KiCad-Library/datasheet/ and are cited inline. Anything not sourced
is marked UNKNOWN and is NOT given a value.

Run:  python hardware/tools/power_review.py
"""

# ---------------------------------------------------------------- inputs ----
# Battery, from docs/sizing/model-output.txt
V_NOM, V_MIN, V_MAX = 21.6, 18.0, 25.2
I_CONT, I_PEAK = 42.0, 115.0          # whole board, A
N_CH = 4

# SP40N01GHNK, Siliup, datasheet Ver-1.1 (committed)
RDSON_TYP, RDSON_MAX = 1.2e-3, 1.5e-3  # ohm, VGS=10V
RDSON_HOT_MULT = 1.6                   # normalised Rdson at TJ=125C, fig p3
VDSS = 40.0
RTH_JC = 0.96                          # C/W
TJ_MAX = 150.0
QG, QGD = 126e-9, 15.5e-9              # C
COSS, QRR = 1950e-12, 113e-9
TR, TF = 5e-9, 9.5e-9                  # s, at Rg=3ohm ID=30A VDD=20V
ID_TC100 = 80.0                        # A, package limit at Tc=100C

# JST SM08B-SRSS-TB, SR series datasheet (committed)
JST_I_RATED = 0.7                      # A per contact
JST_V_RATED = 50.0
JST_R_CONTACT = 20e-3                  # ohm initial, 40 mohm after env test

# Current sense, from OpenESC-30x30
R_SHUNT = 0.1e-3                       # 2 x 0.2 mohm in parallel

# Copper
RHO_CU = 1.72e-8                       # ohm.m at 20C
RHO_CU_TC = 0.00393                    # per K
CU_DENSITY, CU_CP = 8960.0, 385.0      # kg/m3, J/kgK
OZ = 34.8e-6                           # m per oz of copper
T_OUTER, T_INNER = 2 * OZ, 1 * OZ      # current proposed stackup

# Thermal / environment
T_AMB = 40.0                           # C, assumed ambient. UNVERIFIED.
DT_ALLOW = 20.0                        # C copper rise budget

# Switching. AM32 default PWM. FLAGGED: not verified against our config.
F_PWM = 24e3


def ipc2221_current(area_m2, dt_c, external=True):
    """IPC-2221 external/internal trace current for a temperature rise."""
    k = 0.048 if external else 0.024
    area_mil2 = area_m2 * 1.550e9
    return k * (dt_c ** 0.44) * (area_mil2 ** 0.725)


def ipc2221_width(current_a, thickness_m, dt_c, external=True):
    """Trace width needed to carry a current at a given rise."""
    k = 0.048 if external else 0.024
    area_mil2 = (current_a / (k * dt_c ** 0.44)) ** (1 / 0.725)
    area_m2 = area_mil2 / 1.550e9
    return area_m2 / thickness_m


def adiabatic_rate(current_a, area_m2):
    """Temperature rise rate, C/s, ignoring all heat spreading."""
    return (current_a ** 2 * RHO_CU) / (area_m2 ** 2 * CU_DENSITY * CU_CP)


def rule(t):
    print("\n" + "=" * 74)
    print(t)
    print("=" * 74)


def main():
    rule("1. OPERATING POINT")
    print(f"  battery          {V_NOM} V nom, {V_MIN}-{V_MAX} V")
    print(f"  whole board      {I_CONT} A continuous, {I_PEAK} A peak")
    print(f"  per channel      {I_CONT/N_CH:.1f} A cont, {I_PEAK/N_CH:.1f} A peak"
          f"   (battery side)")
    # Phase current. At high duty the phase RMS approaches the battery current;
    # at ~50% duty it is roughly double it for the same power. Both are given
    # because the ESC lives at both.
    i_ph_hover = 2 * I_CONT / N_CH
    i_ph_peak = I_PEAK / N_CH
    print(f"  phase RMS        {i_ph_hover:.0f} A hover (50% duty assumption),"
          f" {i_ph_peak:.0f} A peak (full duty)")

    rule("2. MOSFET LOSS AND JUNCTION TEMPERATURE  (SP40N01GHNK)")
    rds_hot = RDSON_MAX * RDSON_HOT_MULT
    print(f"  Rds(on) 25C max  {RDSON_MAX*1e3:.2f} mohm")
    print(f"  Rds(on) 125C     {rds_hot*1e3:.2f} mohm  (x{RDSON_HOT_MULT} per datasheet fig)")
    for lbl, iph in (("hover", i_ph_hover), ("peak", i_ph_peak)):
        p_cond_fet = iph ** 2 * rds_hot
        e_sw = 0.5 * V_MAX * iph * (TR + TF)
        p_sw = e_sw * F_PWM
        p_coss = 0.5 * COSS * V_MAX ** 2 * F_PWM
        p_qrr = QRR * V_MAX * F_PWM
        p_fet = p_cond_fet + p_sw + p_coss + p_qrr
        # two devices conduct in series at any instant
        p_chan = 2 * p_cond_fet + 6 * (p_sw + p_coss + p_qrr)
        print(f"\n  --- {lbl}: I_phase = {iph:.0f} A RMS")
        print(f"      conduction / FET   {p_cond_fet:6.2f} W")
        print(f"      switching  / FET   {p_sw:6.3f} W  (f={F_PWM/1e3:.0f} kHz, ASSUMED)")
        print(f"      Coss+Qrr   / FET   {p_coss+p_qrr:6.3f} W")
        print(f"      total      / FET   {p_fet:6.2f} W")
        print(f"      per channel (6 FET){p_chan:6.2f} W")
        print(f"      all 4 channels     {4*p_chan:6.2f} W")
        rth_needed = (125.0 - T_AMB) / p_fet
        print(f"      Rth(j-a) needed for TJ<125C at {T_AMB:.0f}C amb:"
              f" {rth_needed:5.1f} C/W")
    print(f"\n  Rth(j-c) is {RTH_JC} C/W. Rth(c-a) is a LAYOUT property and is")
    print("  UNKNOWN until the copper under the pad is drawn. That is the")
    print("  number that decides whether these parts survive, not Rds(on).")

    rule("3. COPPER: WHAT 2 oz OUTER ACTUALLY CARRIES")
    for w_mm in (1.0, 2.0, 5.0, 10.0, 20.0):
        a = (w_mm * 1e-3) * T_OUTER
        i20 = ipc2221_current(a, 20.0)
        i40 = ipc2221_current(a, 40.0)
        print(f"  {w_mm:5.1f} mm of 2 oz outer -> {i20:6.1f} A @20C rise,"
              f" {i40:6.1f} A @40C rise")
    print()
    print("  Width required, 2 oz outer, 20 C rise:")
    for lbl, i in (("phase hover", i_ph_hover), ("phase peak", i_ph_peak),
                   ("bus continuous", I_CONT), ("bus peak", I_PEAK)):
        w = ipc2221_width(i, T_OUTER, DT_ALLOW) * 1e3
        note = "  <-- WIDER THAN THE 50 mm BOARD" if w > 50 else ""
        print(f"    {lbl:<16} {i:6.1f} A -> {w:8.1f} mm{note}")

    rule("4. THE 115 A EVENT IS NOT A STEADY STATE")
    print("  Duration is UNDEFINED. Nothing in the firmware, the sizing model")
    print("  or the ArduPilot parameters bounds how long T/W=2 may be held.")
    print("  Adiabatic rise rate at 115 A (no heat spreading, worst case):\n")
    for lbl, layers in (("2 oz outer only, 20 mm wide", [(20e-3, T_OUTER)]),
                        ("2 outer + 4 inner, 20 mm wide",
                         [(20e-3, T_OUTER)] * 2 + [(20e-3, T_INNER)] * 4)):
        a = sum(w * t for w, t in layers)
        rate = adiabatic_rate(I_PEAK, a)
        print(f"    {lbl:<32} A={a*1e6:5.2f} mm2  {rate:6.2f} C/s"
              f"  -> 30 C in {30/rate:5.1f} s")
    a_all = 2 * 20e-3 * T_OUTER + 4 * 20e-3 * T_INNER
    r_per_mm = RHO_CU * 1e-3 / a_all
    print(f"\n  6-layer bus, 20 mm wide: {r_per_mm*1e6:.2f} uohm/mm")
    for lbl, i in (("42 A", I_CONT), ("115 A", I_PEAK)):
        print(f"    {lbl:>6} over 25 mm: drop {i*r_per_mm*25*1e3:5.2f} mV,"
              f" loss {i**2*r_per_mm*25:5.2f} W")

    rule("5. SHUNT AND CONNECTOR")
    print(f"  shunt {R_SHUNT*1e3:.2f} mohm:"
          f" {I_CONT:.0f} A -> {I_CONT**2*R_SHUNT:.2f} W,"
          f" {I_PEAK:.0f} A -> {I_PEAK**2*R_SHUNT:.2f} W")
    print(f"  shunt drop:      {I_CONT*R_SHUNT*1e3:.1f} mV / {I_PEAK*R_SHUNT*1e3:.1f} mV")
    print(f"\n  J1 JST SM08B-SRSS-TB: {JST_I_RATED} A per contact,"
          f" {JST_V_RATED} V, {JST_R_CONTACT*1e3:.0f} mohm")
    print(f"  J1 pin 1 is +BATT. It is a BREAKOUT ONLY -- at {JST_I_RATED} A it is")
    print(f"  {I_CONT/JST_I_RATED:.0f}x under the continuous bus current and"
          f" {I_PEAK/JST_I_RATED:.0f}x under peak.")

    rule("6. VIAS")
    d, plate, h = 0.3e-3, 25e-6, 1.6e-3
    a_via = 3.14159 * (d + plate) * plate
    r_via = RHO_CU * h / a_via
    print(f"  0.3 mm drill, 25 um plating: A={a_via*1e6:.4f} mm2,"
          f" R={r_via*1e3:.2f} mohm per via")
    for lbl, i, per in (("bus continuous", I_CONT, 1.5),
                        ("bus peak", I_PEAK, 3.0),
                        ("phase hover", i_ph_hover, 1.5),
                        ("phase peak", i_ph_peak, 3.0)):
        n = i / per
        print(f"    {lbl:<16} {i:6.1f} A at {per} A/via -> {n:5.0f} vias minimum")

    rule("7. TRANSIENT VOLTAGE -- THE REAL CONSTRAINT ON 40 V PARTS")
    didt = i_ph_peak / TF
    print(f"  di/dt at turn-off: {i_ph_peak:.0f} A / {TF*1e9:.1f} ns"
          f" = {didt/1e9:.2f} A/ns")
    headroom = VDSS - V_MAX
    print(f"  headroom: {VDSS:.0f} V VDSS - {V_MAX} V rail = {headroom:.1f} V")
    for derate, lbl in ((1.00, "to absolute VDSS"), (0.80, "to 80% of VDSS")):
        allowed = VDSS * derate - V_MAX
        l_max = allowed / didt
        print(f"    {lbl:<18} allowed spike {allowed:5.1f} V ->"
              f" loop L must be < {l_max*1e9:5.2f} nH")
    print("\n  For scale: 1 nH is roughly 1 mm of trace. A 10 nH loop -- a few")
    print("  millimetres of sloppy routing -- puts the spike at"
          f" {10e-9*didt:.0f} V on top of the rail.")

    rule("8. BOARD-LEVEL THERMAL: DOES IT NEED AIRFLOW?")
    # Other dissipation: shunt, bus copper, the two ESC regulators and the FC
    # rails. 3 W is an ESTIMATE for the avionics side and is not sourced.
    p_avionics = 3.0
    for lbl, p_fets, i in (("hover", 12.67, I_CONT), ("peak", 20.89, I_PEAK)):
        p_tot = p_fets + i ** 2 * R_SHUNT + i ** 2 * r_per_mm * 25 + p_avionics
        area_cm2 = 2 * (50 * 50) / 100.0
        print(f"\n  --- {lbl}: {p_tot:.1f} W total on {area_cm2:.0f} cm2"
              f" (both sides of 50x50)")
        for h, cond in ((0.0075, "still air, natural convection"),
                        (0.030, "propwash, forced ~5 m/s")):
            dt = p_tot / (area_cm2 * h)
            verdict = "OK" if T_AMB + dt < 85 else "TOO HOT"
            print(f"      {cond:<32} dT {dt:5.1f} C ->"
                  f" board {T_AMB+dt:5.1f} C   {verdict}")
    print("\n  h values are textbook ranges, not measured. The conclusion that")
    print("  survives the uncertainty: this board is cooled by the props, and")
    print("  bench-testing it at peak in still air will overheat it.")

    rule("9. CAN A TVS PROTECT THE 40 V PARTS?")
    print("  A TVS must stand off the rail and clamp below the FET rating:")
    print(f"    Vrwm  > {V_MAX} V  (else it conducts in normal operation)")
    print(f"    Vclamp < {VDSS*0.8:.0f} V  (80% derating of {VDSS:.0f} V VDSS)")
    print("  Real TVS clamping ratio is about 1.5-1.6x Vrwm, so the lowest")
    print(f"  standoff that survives the rail, 26 V, clamps near"
          f" {26*1.6:.0f} V -- above VDSS.")
    print("  CONCLUSION: no standard TVS fits this window. This is why")
    print("  OpenESC-30x30 rev3 REMOVED its input clamp diodes rather than")
    print("  resizing them. Protection has to come from loop geometry.")
    print()
    for v in (40.0, 60.0):
        allowed = v * 0.8 - V_MAX
        print(f"    with {v:.0f} V FETs: allowed spike {allowed:5.1f} V ->"
              f" loop L < {allowed/didt*1e9:5.2f} nH"
              f"{'   <-- very hard to guarantee' if v == 40 else '   achievable'}")

    rule("10. 60 V FET SELECTION  (decision: 60 V minimum)")
    # (label, VDSS, Rds(on) max @10V, source-confidence)
    CANDIDATES = [
        ("SP40N01GHNK  (fitted, 40 V)", 40.0, 1.5e-3,
         "committed datasheet Ver-1.1"),
        ("NCEP60T15G", 60.0, 3.1e-3,
         "third-party database, NOT the manufacturer datasheet"),
        ("BSC028N06NS", 60.0, 2.8e-3, "Infineon product page"),
        ("BSC014N06NS", 60.0, 1.45e-3, "Infineon product page"),
    ]
    print(f"  {'part':<28} {'VDSS':>5} {'Rmax':>7} {'Rhot':>7} "
          f"{'Pcond/FET':>10} {'4ch':>7} {'Lloop':>7}")
    print(f"  {'':<28} {'V':>5} {'mohm':>7} {'mohm':>7} "
          f"{'W @29A':>10} {'W':>7} {'nH':>7}")
    print("  " + "-" * 76)
    for name, vdss, rmax, src in CANDIDATES:
        rhot = rmax * RDSON_HOT_MULT
        p_cond = i_ph_peak ** 2 * rhot
        p_sw6 = 6 * (0.5 * V_MAX * i_ph_peak * (TR + TF) * F_PWM
                     + 0.5 * COSS * V_MAX ** 2 * F_PWM + QRR * V_MAX * F_PWM)
        p_4ch = 4 * (2 * p_cond + p_sw6)
        l_loop = (vdss * 0.8 - V_MAX) / didt
        print(f"  {name:<28} {vdss:5.0f} {rmax*1e3:7.2f} {rhot*1e3:7.2f} "
              f"{p_cond:10.2f} {p_4ch:7.1f} {l_loop*1e9:7.2f}")
    print("\n  Switching terms above reuse the SP40N01GHNK timings; each")
    print("  candidate's own tr/tf/Coss/Qrr are UNKNOWN until its datasheet is")
    print("  read. Conduction dominates here, so the ranking holds, but the")
    print("  absolute numbers for the 60 V rows are provisional.")
    print()
    print("  BSC014N06NS is 60 V at LOWER Rds(on) than the fitted 40 V part.")
    print("  Moving to 60 V therefore need not cost conduction loss at all --")
    print("  it costs unit price, and it needs the SuperSO8 land pattern")
    print("  checked against PDFN-8L_L6.0-W5.0-P1.27. The OpenDrone catalogue")
    print("  already lists an Infineon SuperSO8 (BSC010N04LS6) as landing on")
    print("  this footprint, which is good evidence but is not a substitute")
    print("  for the drawing arithmetic.")
    for name, vdss, rmax, src in CANDIDATES:
        rhot = rmax * RDSON_HOT_MULT
        p_fet = i_ph_peak ** 2 * rhot + 0.21
        print(f"    {name:<28} Rth(j-a) budget at peak:"
              f" {(125.0-T_AMB)/p_fet:5.1f} C/W   [{src}]")

    rule("11. WHAT THIS MEANS")
    print("  - 2 oz outer copper ALONE cannot carry the bus. Use all six")
    print("    layers in parallel, stitched with a via array.")
    print("  - The 'Phase' netclass at 1.0 mm track is far short of the phase")
    print("    current; it came from a much smaller aircraft.")
    print("  - The 115 A duration is an UNRESOLVED PARAMETER and gates the")
    print("    thermal design. It must be defined, not assumed.")
    print("  - Rth(c-a) under each FET is the number that decides survival.")
    print("  - A TVS cannot protect a 40 V part on a 25.2 V rail: see the doc.")


if __name__ == "__main__":
    main()
