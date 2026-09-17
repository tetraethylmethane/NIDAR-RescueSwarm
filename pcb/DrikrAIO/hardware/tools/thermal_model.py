#!/usr/bin/env python3
"""Thermal model for the DrikrAIO power stage.

Deliberately NOT "6 cm2 x 24 = 144 cm2, therefore impossible". That argument is
wrong: the datasheet's 50 K/W is a REFERENCE CONDITION for one device on a
40x40 board in still air, and thermal resistance does not scale linearly with
area. It is decomposed here instead:

    Rth(j-a) = Rth(j-c) + R_spread + R_conv

Rth(j-c) is a datasheet value. R_spread is conduction outward through the
copper from the thermal pad. R_conv is the board shedding heat to air, and it
is the term that dominates and the term that depends on whether the propellers
are turning.

All device parameters are Infineon BSC014N06NS Rev 2.6.

Run:  python hardware/tools/thermal_model.py
"""
import math

# ---- device, DATASHEET Rev 2.6 --------------------------------------------
RDS_MAX_25 = 1.45e-3            # T4, VGS=10V ID=50A
RDS_MULT_125 = 1.55             # Diagram 9
RTH_JC_MAX = 0.8                # T3
TJ_MAX = 175.0                  # T2
TJ_TARGET = 125.0               # conservative design target
QOSS, QRR = 125e-9, 139e-9      # T6 max, T7 typ
TR, TF = 10e-9, 11e-9           # T5

# ---- system ----------------------------------------------------------------
V_MAX = 25.2
I_PH_HOVER, I_PH_PEAK = 21.0, 29.0
N_FET, N_CH = 24, 4
F_PWM = 24e3                    # ASSUMED, AM32 default, unverified
T_AMB = 40.0

# ---- board -----------------------------------------------------------------
BW = BH = 50e-3                                  # m
AREA_BOTH_SIDES = 2 * BW * BH                    # m2
PAD_W, PAD_H = 4.40e-3, 4.10e-3                  # thermal pad
K_CU = 385.0                                     # W/m.K
T_OUTER, T_INNER = 70e-6, 35e-6
T_CU_EFF = 2 * T_OUTER + 4 * T_INNER             # all six layers, via-stitched
P_AVIONICS = 3.0                                 # W, ESTIMATE, not sourced

# Convection coefficients, W/m2.K.
#
# "Propwash cooled" is not a boundary condition, so it is derived here.
#
# Disc loading is 9.69 kg/m2 (docs/sizing/model-output.txt, 18 in quad design
# point). Momentum theory gives the induced velocity at the disc:
#     v_i = sqrt(DL.g / 2.rho) = 6.23 m/s
# and the fully developed slipstream below it is 2.v_i = 12.46 m/s. The board
# sits between those two, depending where it is mounted relative to the disc.
#
# Flat-plate forced convection, L = 50 mm board edge, air at ~60 C
# (nu = 1.9e-5 m2/s, k = 0.028 W/m.K, Pr = 0.70):
#     Nu = 0.664 . Re^0.5 . Pr^(1/3),  h = Nu.k/L
#         6.23 m/s -> h = 42 W/m2K     (at the disc)
#        12.46 m/s -> h = 60 W/m2K     (fully developed slipstream)
#
# The earlier model used h = 80, which needs 22.4 m/s -- almost double this
# aircraft's own slipstream. It was optimistic and is not used any more.
DISC_LOADING = 9.69                  # kg/m2
V_INDUCED, V_SLIPSTREAM = 6.23, 12.46
H_STILL = 15.0      # natural convection + radiation, small vertical PCB
H_PROP_LOW = 42.0   # at the disc, 6.23 m/s
H_PROP_HIGH = 60.0  # fully developed slipstream, 12.46 m/s
H_PROP = H_PROP_LOW  # design against the WORSE of the two


def fet_loss(i_ph):
    rds_hot = RDS_MAX_25 * RDS_MULT_125
    p_cond = i_ph ** 2 * rds_hot
    p_sw = 0.5 * V_MAX * i_ph * (TR + TF) * F_PWM
    p_oss = QOSS * V_MAX * F_PWM
    p_qrr = QRR * V_MAX * F_PWM
    return p_cond, p_sw + p_oss + p_qrr


def spreading_resistance():
    """Radial spreading in a thin plate, pad outward to its share of board.

    R = ln(r_o/r_s) / (2.pi.k.t), with the copper treated as all six layers in
    parallel because the drain pad is stitched into them by the via array.
    """
    a_pad = PAD_W * PAD_H
    r_s = math.sqrt(a_pad / math.pi)
    a_share = AREA_BOTH_SIDES / N_FET
    r_o = math.sqrt(a_share / math.pi)
    return math.log(r_o / r_s) / (2 * math.pi * K_CU * T_CU_EFF), r_s, r_o


def main():
    print("THERMAL MODEL -- DrikrAIO power stage")
    print("=" * 74)

    r_spread, r_s, r_o = spreading_resistance()
    print(f"  thermal pad          {PAD_W*1e3:.2f} x {PAD_H*1e3:.2f} mm"
          f"  -> equivalent radius {r_s*1e3:.2f} mm")
    print(f"  copper per FET       {AREA_BOTH_SIDES/N_FET*1e4:.2f} cm2"
          f"  -> outer radius {r_o*1e3:.2f} mm")
    print(f"  effective copper     {T_CU_EFF*1e6:.0f} um"
          f"  (2 x {T_OUTER*1e6:.0f} outer + 4 x {T_INNER*1e6:.0f} inner)")
    print(f"  R_spread             {r_spread:6.2f} K/W")
    print(f"  Rth(j-c) max         {RTH_JC_MAX:6.2f} K/W   [DATASHEET]")
    print("\n  Copper spreading is CHEAP. The board-to-air term is not.")

    for lbl, i_ph in (("HOVER", I_PH_HOVER), ("PEAK", I_PH_PEAK)):
        p_cond, p_other = fet_loss(i_ph)
        p_fet = p_cond + p_other
        p_fets_total = N_CH * (2 * p_cond + 6 * p_other)
        p_board = p_fets_total + P_AVIONICS
        print("\n" + "-" * 74)
        print(f"  {lbl}: I_phase = {i_ph:.0f} A RMS")
        print(f"    per FET            cond {p_cond:5.2f} W + other {p_other:5.3f} W"
              f" = {p_fet:5.2f} W")
        print(f"    24 FETs (2 of 6 conducting per channel) {p_fets_total:6.2f} W")
        print(f"    board total (+{P_AVIONICS:.0f} W avionics)          {p_board:6.2f} W")

        for hlbl, h in (("still air", H_STILL),
                        ("prop @disc", H_PROP_LOW),
                        ("prop slipstr", H_PROP_HIGH)):
            r_conv = 1.0 / (h * AREA_BOTH_SIDES)
            dt_board = p_board * r_conv
            t_board = T_AMB + dt_board
            # junction sits above the local board temperature
            r_ja = RTH_JC_MAX + r_spread + r_conv * N_FET  # per-device share
            t_j = t_board + p_fet * (RTH_JC_MAX + r_spread)
            ok125 = "OK" if t_j <= TJ_TARGET else "OVER"
            ok175 = "OK" if t_j <= TJ_MAX else "OVER LIMIT"
            print(f"      {hlbl:<13} h={h:5.1f} W/m2K R_conv={r_conv:6.2f} K/W"
                  f"  board {t_board:6.1f} C")
            print(f"                 -> Tj {t_j:6.1f} C   "
                  f"vs 125 C target: {ok125:4}   vs 175 C limit: {ok175}")
            print(f"                 -> effective Rth(j-a) per device"
                  f" {(t_j - T_AMB)/p_fet:6.1f} K/W")

    print("\n" + "=" * 74)
    print("  REQUIRED Rth(j-a), verified rather than assumed:")
    for lbl, i_ph in (("hover", I_PH_HOVER), ("peak", I_PH_PEAK)):
        p_cond, p_other = fet_loss(i_ph)
        p_fet = p_cond + p_other
        for tj in (TJ_TARGET, TJ_MAX):
            print(f"    {lbl:<6} P={p_fet:4.2f} W, Tj<{tj:.0f} C, Ta={T_AMB:.0f} C"
                  f"  -> Rth(j-a) <= {(tj - T_AMB)/p_fet:5.1f} K/W")

    print("\n  The ~38 K/W requirement for the peak case at a 125 C target is")
    print("  confirmed. It is NOT a property of the device -- it is what the")
    print("  board must achieve, and R_conv decides it.")
    print()
    print("  " + "!" * 68)
    print("  THE EARLIER 'PASS UNDER PROPWASH' VERDICT DOES NOT SURVIVE THIS.")
    print("  " + "!" * 68)
    print("  That verdict used h = 80 W/m2K, which needs 22.4 m/s. This")
    print("  aircraft's fully developed slipstream is 12.46 m/s (h = 60) and at")
    print("  the disc it is 6.23 m/s (h = 42). Against its own airflow:")
    print()
    print("    hover, slipstream   Tj 103 C   -> meets the 125 C target")
    print("    hover, at the disc  Tj 129 C   -> MISSES the 125 C target")
    print("    peak,  slipstream   Tj 134 C   -> MISSES the 125 C target")
    print("    peak,  at the disc  Tj 171 C   -> 3.6 C from the 175 C LIMIT")
    print()
    print("  Nothing here exceeds the 175 C absolute maximum, so the design is")
    print("  not disqualified -- but it does NOT meet the conservative 125 C")
    print("  target at peak under any airflow this aircraft actually produces.")
    print("  Mounting position relative to the disc is now a thermal design")
    print("  parameter, not a mechanical convenience.")
    print()
    print("  SENSITIVITY: h remains the dominant uncertainty and is calculated,")
    print("  not measured. Rth(j-a) must be measured on the first board.")

    # ---------------- parameterised peak, duration UNKNOWN -----------------
    print("\n" + "=" * 74)
    print("  115 A PEAK -- PARAMETERISED. DURATION IS UNRESOLVED.")
    print("=" * 74)
    print("  Tj(t) = Tj_steady_hover + P_peak_step x Zth(t)")
    print()
    print("  Zth(j-c) read from Rev 2.6 Diagram 4, single-pulse curve.")
    print("  These are read off a log-log plot: treat as +/-30%.")
    # single-pulse Zth,JC read from Diagram 4
    ZTH_JC = [(1e-4, 0.010), (1e-3, 0.030), (1e-2, 0.10),
              (1e-1, 0.30), (1.0, 0.50)]
    p_cond_h, p_oth_h = fet_loss(I_PH_HOVER)
    p_cond_p, p_oth_p = fet_loss(I_PH_PEAK)
    p_step = (p_cond_p + p_oth_p) - (p_cond_h + p_oth_h)
    r_spread, _, _ = spreading_resistance()
    tj_hover_prop = (T_AMB + (N_CH * (2 * p_cond_h + 6 * p_oth_h) + P_AVIONICS)
                     / (H_PROP * AREA_BOTH_SIDES)
                     + (p_cond_h + p_oth_h) * (RTH_JC_MAX + r_spread))
    print(f"\n  Step in per-FET dissipation, hover -> peak: {p_step:.2f} W")
    print(f"  Starting junction (hover, propwash):        {tj_hover_prop:.1f} C")
    print(f"\n  {'pulse t':>10}  {'Zth(j-c)':>9}  {'dTj':>7}  {'Tj':>7}")
    for t, z in ZTH_JC:
        dtj = p_step * z
        print(f"  {t:10.4g}  {z:9.3f}  {dtj:6.2f} K  {tj_hover_prop+dtj:6.1f} C")
    print("\n  Within the die and package the peak is nearly free: even a full")
    print("  second adds under a degree. That is NOT the answer, because")
    print("  Zth(j-c) stops at the case. Beyond roughly 1 s the PCB and the")
    print("  air take over, and Zth(j-a) for THIS board is UNKNOWN -- the")
    print("  datasheet only gives the steady-state 50 K/W reference.")
    print()
    print("  115 A PEAK-DURATION REQUIREMENT UNRESOLVED.")
    print()
    print("  Cannot be closed without duration AND repetition rate:")
    for item in ("MOSFET transient thermal response beyond ~1 s",
                 "PCB copper temperature rise (adiabatic only bounds short pulses)",
                 "connector and pad heating",
                 "capacitor ripple-current stress and self-heating",
                 "power-plane temperature",
                 "repeated-peak accumulation -- needs duty cycle, not duration alone"):
        print(f"    - {item}")


if __name__ == "__main__":
    main()
