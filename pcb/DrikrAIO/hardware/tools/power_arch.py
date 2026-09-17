#!/usr/bin/env python3
"""Power architecture calculations: budget table and high-current path table.

Device ratings are quoted from the datasheets committed in
hardware/KiCad-Library/datasheet/. Anything not verifiable there is marked
OPEN rather than assumed to pass.

Run:  python hardware/tools/power_arch.py
"""
import math

# ---------------- frozen system inputs ----------------
V_MIN, V_NOM, V_MAX = 18.0, 21.6, 25.2
I_CONT, I_PEAK = 42.0, 115.0
N_CH = 4
I_CH_CONT, I_CH_PEAK = I_CONT / N_CH, I_PEAK / N_CH
I_PH_HOVER, I_PH_PEAK = 21.0, 28.75

# ---------------- copper / stackup ----------------
RHO_CU = 1.72e-8
OZ = 34.8e-6
T_OUT, T_IN = 2 * OZ, 1 * OZ
BUS_W = 20e-3                      # effective bus width, m
VIA_A = math.pi * (0.3e-3 + 25e-6) * 25e-6
VIA_R = RHO_CU * 1.6e-3 / VIA_A

# ---------------- DATASHEET ratings ----------------
# (part, role, Vin_abs_max, Vin_rec_max, I_rated, source)
DEVICES = [
    ("BSC014N06NS", "motor bridge FET x24", 60.0, 60.0, 257.0,
     "Infineon Rev 2.6 T2 (257 A at Tc=25 C, NOT a board rating)"),
    ("LMR51430", "FC 10 V and 5 V bucks", 38.0, 36.0, 3.0,
     "TI SLUSEF4A T7.1/7.3"),
    ("LMR54406", "ESC 10 V gate rail", 45.0, 36.0, 0.6,
     "TI SLUSEG8E T6.1/6.3 (50 V <=1 s at <=0.01% duty)"),
    ("INA186A3", "battery current sense", None, None, None, "OPEN - not read"),
    ("TLV76733", "ESC 3V3 LDO", None, None, None, "OPEN - not read"),
    ("LP5912", "FC 3V3 and 1V8 LDOs", None, None, None, "OPEN - not read"),
    ("DSK24", "5 V diode-OR x2", None, None, None, "OPEN - not read"),
    ("SM08B-SRSS-TB", "J1 signal connector", 50.0, 50.0, 0.7,
     "JST SR series: 0.7 A per contact, 50 V"),
]

RAILS = [
    # rail, V, I_cont, I_peak, source, load, protection, note
    ("VBAT", "18-25.2", "42 A", "115 A", "battery via U3 pads",
     "4 bridges + both bucks", "0.1 mOhm shunt + INA186; NO fuse, NO reverse "
     "protection", "peak duration OPEN"),
    ("+10V (ESC)", "10", "~0.1 A", "~0.2 A", "LMR54406 0.6 A",
     "4x NSG2065Q gate drivers", "buck current limit only",
     "ungated by design"),
    ("+3V3 (ESC)", "3.3", "~0.1 A", "~0.15 A", "TLV76733 from +10V",
     "4x AT32F421, INA186, RX", "LDO current limit", "OPEN: LDO rating"),
    ("+10V (FC)", "10", "<=3 A", "<=3 A", "LMR51430",
     "external VTX", "MCU-gated via 10V_ENABLE", "VTX is off-board"),
    ("+5V (FC)", "5", "<=3 A", "<=3 A", "LMR51430",
     "5 V pads, diode-OR to +4V5", "always-on", ""),
    ("+4V5", "4.5", "<0.5 A", "<0.5 A", "DSK24 OR of +5V and +5V_USB",
     "3V3 and 1V8 LDOs", "none", "no pass element by design"),
    ("+3.3V (FC)", "3.3", "<0.5 A", "<0.5 A", "LP5912-3.3 500 mA",
     "MCU IO, IMU IO, microSD, OSD", "LDO current limit",
     "DIFFERENT NET from +3V3"),
    ("+1.8V", "1.8", "<0.05 A", "<0.05 A", "LP5912-1.8",
     "IMU analog only", "LDO current limit",
     "deliberately separate from 3V3"),
]


def r_layer(t_cu, w=BUS_W, length=25e-3):
    return RHO_CU * length / (w * t_cu)


def rule(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def main():
    rule("DEVICE VOLTAGE / CURRENT VERIFICATION AGAINST 25.2 V AND 115 A")
    print(f"  {'part':<16}{'role':<26}{'Vabs':>6}{'Vrec':>6}"
          f"{'margin@25.2':>12}  status")
    print("  " + "-" * 74)
    opens = []
    for part, role, vabs, vrec, irated, src in DEVICES:
        if vabs is None:
            print(f"  {part:<16}{role:<26}{'?':>6}{'?':>6}{'?':>12}  OPEN")
            opens.append(f"{part} ({role}) - rating not verified")
            continue
        marg = vabs - V_MAX
        st = "OK" if marg > 0 else "FAIL"
        print(f"  {part:<16}{role:<26}{vabs:6.0f}{vrec or 0:6.0f}"
              f"{marg:11.1f}V  {st}")
    print("\n  Sources:")
    for part, _, _, _, _, src in DEVICES:
        print(f"    {part:<16} {src}")

    rule("TRANSIENT HEADROOM ON THE VBAT BUS -- THE BINDING DEVICE")
    didt = I_PH_PEAK / 11e-9
    print(f"  di/dt at FET turn-off: {I_PH_PEAK:.2f} A / 11 ns"
          f" = {didt/1e9:.2f} A/ns  [CALCULATED]")
    print(f"\n  {'device':<14}{'Vabs':>6}{'spike to Vabs':>15}"
          f"{'spike to 80%':>14}{'L for 80%':>12}")
    print("  " + "-" * 62)
    for part, vabs in (("BSC014N06NS", 60.0), ("LMR54406", 45.0),
                       ("LMR51430", 38.0)):
        s_abs = vabs - V_MAX
        s_80 = vabs * 0.8 - V_MAX
        l80 = s_80 / didt * 1e9 if s_80 > 0 else float("nan")
        print(f"  {part:<14}{vabs:6.0f}{s_abs:14.1f}V{s_80:13.1f}V"
              f"{l80:11.2f}nH")
    print("\n  THE FET IS NOT THE LOWEST-RATED DEVICE ON THIS BUS.")
    print("  LMR51430 abs max is 38 V, only 12.8 V above the 25.2 V rail.")
    print("  The 8.72 nH budget governs V_DS AT THE FET, inside the local")
    print("  commutation loop. The regulators sit on the BULK-DECOUPLED bus")
    print("  and see an attenuated transient -- but 'attenuated' is not a")
    print("  number, and no attenuation factor is computed here because it")
    print("  depends on final geometry and bulk ESL.")
    print("  => OPEN: VBAT bus transient at the regulator inputs.")
    opens.append("VBAT bus transient at LMR51430 inputs (38 V abs max)")

    rule("POWER BUDGET")
    hdr = ("rail", "V", "I cont", "I peak", "source", "load", "protection")
    print(f"  {hdr[0]:<12}{hdr[1]:<10}{hdr[2]:<9}{hdr[3]:<9}"
          f"{hdr[4]:<22}{hdr[5]:<34}{hdr[6]}")
    print("  " + "-" * 130)
    for r in RAILS:
        print(f"  {r[0]:<12}{r[1]:<10}{r[2]:<9}{r[3]:<9}{r[4]:<22}"
              f"{r[5]:<34}{r[6]}")
    print("\n  Notes:")
    for r in RAILS:
        if r[7]:
            print(f"    {r[0]:<12} {r[7]}")

    rule("HIGH-CURRENT PATH TABLE")
    r_out = r_layer(T_OUT)
    r_in = r_layer(T_IN)
    # four layers in parallel: L1, L6 at 2 oz; L3, L4 at 1 oz
    r_bus = 1.0 / (2 / r_out + 2 / r_in)
    a_bus = 2 * BUS_W * T_OUT + 2 * BUS_W * T_IN
    share_out = (1 / r_out) / (2 / r_out + 2 / r_in)
    share_in = (1 / r_in) / (2 / r_out + 2 / r_in)
    print(f"  VBAT bus, {BUS_W*1e3:.0f} mm effective width, 25 mm long,"
          f" four layers L1/L3/L4/L6")
    print(f"    copper area      {a_bus*1e6:.2f} mm2  [CALCULATED]")
    print(f"    R per outer layer {r_out*1e3:.3f} mOhm, per inner {r_in*1e3:.3f} mOhm")
    print(f"    R bus (parallel)  {r_bus*1e6:.2f} uOhm")
    print(f"    current sharing   outer {100*share_out:.1f}% each,"
          f" inner {100*share_in:.1f}% each  [CALCULATED, ideal stitching]")
    print()
    print(f"  {'path':<26}{'I':>8}{'R':>11}{'V drop':>10}{'P loss':>10}"
          f"{'layers':>9}")
    print("  " + "-" * 76)
    rows = [
        ("VBAT bus continuous", I_CONT, r_bus, "L1/L3/L4/L6"),
        ("VBAT bus peak", I_PEAK, r_bus, "L1/L3/L4/L6"),
        ("shunt (0.1 mOhm) cont", I_CONT, 0.1e-3, "L6"),
        ("shunt (0.1 mOhm) peak", I_PEAK, 0.1e-3, "L6"),
    ]
    for name, i, r, lay in rows:
        print(f"  {name:<26}{i:7.1f}A{r*1e3:10.3f}m{i*r*1e3:9.2f}mV"
              f"{i*i*r:9.2f}W{lay:>9}")
    # per-channel branch
    r_branch = RHO_CU * 12e-3 / (6.6e-3 * (T_OUT + T_IN))
    for name, i in (("channel branch cont", I_CH_CONT),
                    ("channel branch peak", I_CH_PEAK)):
        print(f"  {name:<26}{i:7.1f}A{r_branch*1e3:10.3f}m"
              f"{i*r_branch*1e3:9.2f}mV{i*i*r_branch:9.2f}W{'L6+L4':>9}")
    # phase
    r_phase = RHO_CU * 10e-3 / (6.6e-3 * T_OUT)
    for name, i in (("motor phase hover", I_PH_HOVER),
                    ("motor phase peak", I_PH_PEAK)):
        print(f"  {name:<26}{i:7.1f}A{r_phase*1e3:10.3f}m"
              f"{i*r_phase*1e3:9.2f}mV{i*i*r_phase:9.2f}W{'L6':>9}")

    rule("VIA ARRAYS")
    print(f"  0.3 mm drill, 25 um plating: {VIA_R*1e3:.2f} mOhm per via"
          f"  [CALCULATED]")
    for name, i, per in (("VBAT transition, cont", I_CONT, 1.5),
                         ("VBAT transition, peak", I_PEAK, 3.0),
                         ("phase transition", I_PH_PEAK, 3.0),
                         ("FET thermal pad", 0, 0)):
        if per:
            n = math.ceil(i / per)
            print(f"    {name:<24}{i:6.1f} A at {per} A/via -> >= {n:3d} vias"
                  f"   R_array {VIA_R/n*1e6:6.2f} uOhm")
    print(f"    {'FET thermal pad':<24}{'thermal, not current':>26}"
          f" -> >=  9 vias")

    rule("OPEN ITEMS -- NOT ASSUMED TO PASS")
    for i, o in enumerate(opens, 1):
        print(f"  {i}. {o}")
    for extra in (
        "115 A peak duration and repetition rate (frozen OPEN)",
        "Airflow boundary condition (frozen OPEN)",
        "Reverse-polarity protection: NONE present in the design",
        "Input fuse / current limiting: NONE present",
        "UV/OV protection: none beyond regulator UVLO",
        "Bulk electrolytic 470 uF is user-installed, off-board",
        "X5R capacitance at 25.2 V DC bias",
    ):
        print(f"  {len(opens)+1}. {extra}")
        opens.append(extra)


if __name__ == "__main__":
    main()
