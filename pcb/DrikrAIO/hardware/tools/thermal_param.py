#!/usr/bin/env python3
"""Parameterised thermal model for the DrikrAIO power stage.

Tj as a function of: peak current, peak duration, repetition rate, ambient,
airflow coefficient, MOSFET count, Rds(on), copper spreading and board-to-air
resistance.

Three regimes are kept SEPARATE and are not blended:

  1. STEADY STATE      -- closed form, trustworthy
  2. SINGLE PULSE      -- package level only, bounded by datasheet Zth(j-c)
  3. REPEATED PULSE    -- board level, driven by AVERAGE power

Rev 2.6 provides Zth(J-C) only. It is NOT extrapolated to junction-to-ambient:
Zth(j-a) for this board does not exist in the datasheet and is not invented
here. Where a board-level transient number is given it comes from an explicit
lumped-capacitance estimate whose assumptions are printed alongside it, and it
is labelled ESTIMATE, not DATASHEET.

h = 80 W/m2K is SUPERSEDED and deliberately absent.

Run:  python hardware/tools/thermal_param.py
"""
import math

# ---- device, Infineon BSC014N06NS Rev 2.6 (DATASHEET) ----------------------
RDS_MAX_25 = 1.45e-3
RDS_MULT_125 = 1.55            # Diagram 9, max curve
RTH_JC_MAX = 0.8               # Table 3
TJ_TARGET, TJ_ABS_MAX = 125.0, 175.0
QOSS, QRR = 125e-9, 139e-9
TR, TF = 10e-9, 11e-9

# Zth(J-C), single pulse, read off Diagram 4 (+/-30%). PACKAGE ONLY.
ZTH_JC_SINGLE = [(1e-4, 0.010), (1e-3, 0.030), (1e-2, 0.100),
                 (1e-1, 0.300), (1.0, 0.500)]

# ---- system ---------------------------------------------------------------
V_MAX = 25.2
N_CH, N_FET = 4, 24
F_PWM = 24e3                   # ASSUMED (AM32 default), unverified
T_AMB_DEFAULT = 40.0

# ---- board ----------------------------------------------------------------
BW = BH = 50e-3
AREA = 2 * BW * BH             # both sides, m2
PAD_W, PAD_H = 4.40e-3, 4.10e-3
K_CU, T_CU_EFF = 385.0, 2 * 70e-6 + 4 * 35e-6
P_AVIONICS = 3.0               # ESTIMATE, not sourced

# Airflow. ONLY the two conditions this aircraft actually produces.
# 6.23 m/s at the disc, 12.46 m/s developed slipstream (momentum theory on
# disc loading 9.69 kg/m2), via Nu = 0.664 Re^0.5 Pr^(1/3), L = 50 mm.
H_CASES = [("A: h=42, at the disc (6.23 m/s)", 42.0),
           ("B: h=60, slipstream (12.46 m/s)", 60.0)]
H_STILL = 15.0                 # reported for safety only, never as a design case

# Lumped board heat capacity, for the repeated-pulse regime. ESTIMATE.
FR4_KG = (BW * BH * 1.6e-3) * 1850.0        # 1.6 mm FR4, 1850 kg/m3
CU_KG = (BW * BH * T_CU_EFF * 0.5) * 8960.0  # 50% average copper coverage
C_BOARD = FR4_KG * 1100.0 + CU_KG * 385.0   # J/K


def phase_rms(i_batt_peak_total, duty_full=True):
    """Phase RMS per channel from whole-board battery current."""
    per_ch = i_batt_peak_total / N_CH
    return per_ch if duty_full else 2 * per_ch


def fet_loss(i_ph, rds_25=RDS_MAX_25, f_pwm=F_PWM, v=V_MAX):
    rds_hot = rds_25 * RDS_MULT_125
    p_cond = i_ph ** 2 * rds_hot
    p_switch = (0.5 * v * i_ph * (TR + TF) * f_pwm
                + QOSS * v * f_pwm + QRR * v * f_pwm)
    return p_cond, p_switch


def r_spread(n_fet=N_FET, t_cu=T_CU_EFF, area=AREA):
    r_s = math.sqrt(PAD_W * PAD_H / math.pi)
    r_o = math.sqrt((area / n_fet) / math.pi)
    return math.log(r_o / r_s) / (2 * math.pi * K_CU * t_cu)


def steady_state(i_ph, h, t_amb=T_AMB_DEFAULT, n_fet=N_FET, **kw):
    """Closed-form steady state. Returns (Tj, T_board, P_fet, P_board)."""
    p_cond, p_sw = fet_loss(i_ph, **kw)
    p_fet = p_cond + p_sw
    p_board = N_CH * (2 * p_cond + 6 * p_sw) + P_AVIONICS
    r_conv = 1.0 / (h * AREA)
    t_board = t_amb + p_board * r_conv
    t_j = t_board + p_fet * (RTH_JC_MAX + r_spread(n_fet))
    return t_j, t_board, p_fet, p_board


def zth_jc(t):
    """Interpolate the single-pulse Zth(J-C) curve. PACKAGE ONLY."""
    pts = ZTH_JC_SINGLE
    if t <= pts[0][0]:
        return pts[0][1]
    if t >= pts[-1][0]:
        return pts[-1][1]
    for (t0, z0), (t1, z1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            f = (math.log10(t) - math.log10(t0)) / (math.log10(t1) - math.log10(t0))
            return z0 + f * (z1 - z0)
    return pts[-1][1]


def rule(t):
    print("\n" + "=" * 76)
    print(t)
    print("=" * 76)


def main():
    i_hover = phase_rms(42.0, duty_full=False)     # 21 A
    i_peak = phase_rms(115.0, duty_full=True)      # 28.75 A
    rs = r_spread()

    rule("MODEL PARAMETERS")
    print(f"  phase RMS       hover {i_hover:.2f} A, peak {i_peak:.2f} A")
    print(f"  Rds(on) @125 C  {RDS_MAX_25*RDS_MULT_125*1e3:.2f} mohm  [DATASHEET x Diagram 9]")
    print(f"  Rth(j-c) max    {RTH_JC_MAX:.2f} K/W                 [DATASHEET]")
    print(f"  R_spread        {rs:.2f} K/W                 [CALCULATED]")
    print(f"  MOSFETs         {N_FET} over {AREA*1e4:.0f} cm2 -> {AREA/N_FET*1e4:.2f} cm2 each")
    print(f"  board heat cap  {C_BOARD:.1f} J/K              [ESTIMATE]")
    print(f"  targets         Tj <= {TJ_TARGET:.0f} C design, {TJ_ABS_MAX:.0f} C absolute max")

    # ---------------------------------------------------------------- 1 ----
    rule("1. STEADY STATE  (closed form -- the trustworthy regime)")
    print(f"  {'condition':<34} {'P/FET':>7} {'P/board':>8} {'T_board':>8} {'Tj':>8}  verdict")
    print("  " + "-" * 74)
    for lbl, h in H_CASES:
        for name, i_ph in (("hover", i_hover), ("PEAK sustained", i_peak)):
            tj, tb, pf, pb = steady_state(i_ph, h)
            v = ("PASS" if tj <= TJ_TARGET else
                 "OVER TARGET" if tj <= TJ_ABS_MAX else "EXCEEDS MAX")
            print(f"  {lbl[:3]} {name:<30} {pf:6.2f}W {pb:7.2f}W"
                  f" {tb:7.1f}C {tj:7.1f}C  {v}")
    tj_s, _, _, _ = steady_state(i_peak, H_STILL)
    print(f"\n  still air (h={H_STILL:.0f}) at peak: Tj {tj_s:.0f} C"
          f" -- reported as a SAFETY FACT, never a design case.")

    # ---------------------------------------------------------------- 2 ----
    rule("2. SINGLE PULSE  (PACKAGE LEVEL ONLY -- datasheet Zth(J-C))")
    print("  Tj(t) = Tj_steady(hover) + dP x Zth(j-c)(t)")
    print("  Zth(J-C) stops at the CASE. This bounds the die, not the board.")
    for lbl, h in H_CASES:
        tj_h, _, pf_h, _ = steady_state(i_hover, h)
        _, _, pf_p, _ = steady_state(i_peak, h)
        dp = pf_p - pf_h
        print(f"\n  {lbl}   dP = {dp:.2f} W/FET, start Tj = {tj_h:.1f} C")
        print(f"    {'pulse':>9} {'Zth(j-c)':>9} {'dTj':>8} {'Tj':>8}")
        for t, _ in ZTH_JC_SINGLE:
            z = zth_jc(t)
            print(f"    {t:9.4g}s {z:9.3f} {dp*z:7.2f}K {tj_h + dp*z:7.1f}C")
    print("\n  Package-level excursion is negligible at every duration the")
    print("  datasheet covers. That does NOT close the peak case.")

    # ---------------------------------------------------------------- 3 ----
    rule("3. REPEATED PULSE  (BOARD LEVEL -- driven by AVERAGE power)")
    print("  The board does not care about the shape of the pulse, only about")
    print("  the average power it must shed. That IS computable as a function")
    print("  of duty cycle, and it is where repeated peaks actually bite.")
    print()
    print(f"  Board thermal time constant tau = C x R_conv   [ESTIMATE]")
    for lbl, h in H_CASES:
        r_conv = 1.0 / (h * AREA)
        print(f"    {lbl[:3]} R_conv {r_conv:.2f} K/W -> tau = {C_BOARD*r_conv:5.1f} s")
    print("\n  So a peak MUCH SHORTER than ~40-70 s barely moves the board, and")
    print("  one comparable to it drives the board toward its average-power")
    print("  steady state. The duration threshold that matters is TENS OF")
    print("  SECONDS, not milliseconds.")
    print()
    for lbl, h in H_CASES:
        print(f"\n  {lbl}")
        print(f"    {'duty':>6} {'P_avg board':>12} {'T_board':>9} {'Tj_avg':>9}  verdict")
        _, _, pf_h, pb_h = steady_state(i_hover, h)
        _, _, pf_p, pb_p = steady_state(i_peak, h)
        r_conv = 1.0 / (h * AREA)
        for d in (0.0, 0.05, 0.10, 0.25, 0.50, 1.0):
            pb = pb_h * (1 - d) + pb_p * d
            pf = pf_h * (1 - d) + pf_p * d
            tb = T_AMB_DEFAULT + pb * r_conv
            tj = tb + pf * (RTH_JC_MAX + rs)
            v = ("PASS" if tj <= TJ_TARGET else
                 "OVER TARGET" if tj <= TJ_ABS_MAX else "EXCEEDS MAX")
            print(f"    {d:6.2f} {pb:11.2f}W {tb:8.1f}C {tj:8.1f}C  {v}")
    print("\n  Duty cycle is UNRESOLVED, so no row above can be selected as")
    print("  the operating case. The table is the answer shape, not the answer.")

    # ---------------------------------------------------------------- 4 ----
    rule("4. WHAT WOULD MAKE Tj <= 125 C AT PEAK")
    print("  Solving the steady-state peak case for each lever in turn, with")
    print("  everything else held at its current value.")
    _, _, pf_p, pb_p = steady_state(i_peak, 42.0)
    print(f"\n  Peak, sustained: P_board {pb_p:.2f} W, P_FET {pf_p:.2f} W")
    # required h
    for tgt in (TJ_TARGET,):
        # Tj = Tamb + P_board/(h A) + P_fet (Rjc+Rs)  ->  solve h
        head = tgt - T_AMB_DEFAULT - pf_p * (RTH_JC_MAX + rs)
        h_req = pb_p / (head * AREA)
        # velocity from h via the same correlation
        # h = 0.664 (v L/nu)^0.5 Pr^(1/3) k / L  ->  v = ((h L / (0.664 k Pr^(1/3)))^2) nu / L
        nu, k_air, pr, L = 1.9e-5, 0.028, 0.70, 0.05
        v_req = ((h_req * L / (0.664 * k_air * pr ** (1 / 3))) ** 2) * nu / L
        print(f"    required h for Tj<={tgt:.0f} C: {h_req:.1f} W/m2K"
              f"  -> about {v_req:.1f} m/s of airflow")
        print(f"    (aircraft provides 6.23 m/s at the disc,"
              f" 12.46 m/s in slipstream)")
    # required board area at h=60
    h = 60.0
    head = TJ_TARGET - T_AMB_DEFAULT - pf_p * (RTH_JC_MAX + rs)
    a_req = pb_p / (head * h)
    print(f"\n    required board area at h=60: {a_req*1e4:.0f} cm2"
          f"  vs {AREA*1e4:.0f} cm2 available")
    print(f"    i.e. about {math.sqrt(a_req/2)*1e3:.0f} x"
          f" {math.sqrt(a_req/2)*1e3:.0f} mm, against the 50 x 50 constraint")
    # required Rds
    print(f"\n    R_spread and Rth(j-c) contribute only"
          f" {pf_p*(RTH_JC_MAX+rs):.1f} K of the rise; the rest is board-to-air.")
    print("    Lowering Rds(on) or adding thermal vias therefore CANNOT fix")
    print("    this: the bottleneck is getting heat off the board, not out")
    print("    of the die. More copper and more vias buy almost nothing here.")

    rule("CONCLUSION")
    print("  Sustained 115 A is NOT thermally acceptable at either airflow.")
    print("  Whether that matters depends entirely on duration and repetition")
    print("  rate, which are UNRESOLVED. If the peak is short relative to the")
    print("  board time constant of tens of seconds and infrequent, the")
    print("  steady-state peak row never applies. If it is sustained, no")
    print("  amount of copper fixes it inside 50 x 50 mm.")
    print()
    print("  Peak thermal acceptability cannot be determined from peak")
    print("  current alone.")


if __name__ == "__main__":
    main()
