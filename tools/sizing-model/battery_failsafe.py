"""Battery failsafe thresholds -- what the firmware should actually be set to.

Run:  python tools/sizing-model/battery_failsafe.py

The committed output is docs/sizing/battery-failsafe-output.txt and CI checks
it reproduces, like every other model output in this repository.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from battery_pack import (  # noqa: E402
    CELL_IMAX, N_CELLS, P, S, WIRING_R, cell_ir, i2r_loss_w, loaded_voltage,
    pack_ocv, pack_resistance, soc_at_loaded_voltage, temp_rise_k,
)

# Operating points from rescueswarm_sizing_model.py's final design point.
V_NOM = S * 3.6
P_HOVER_W = 913.0        # electrical, at MTOW
P_PEAK_W = 2480.0        # T/W = 2.0, P_shaft*(T_W**1.5)/eta + P_avio
P_AVIO_W = 55.0
SWEEP_S = 93.0
MISSION_S = 462.0        # 7.7 min

# What the firmware currently says (firmware/ardupilot-params/params.py).
CURRENT_LOW_V = 20.4     # 6 x 3.40, chosen as "~20 % SoC resting"
CURRENT_CRT_V = 19.2     # 6 x 3.20, "~10 %"

W = 78


def rule(title=""):
    print("=" * W)
    if title:
        print(title)
        print("=" * W)


rule("PACK ELECTRICAL MODEL  -  6S3P 21700, 45 A class")
print(f"  Cells                  : {N_CELLS} ({S}S{P}P), {CELL_IMAX:.0f} A continuous each")
print(f"  Cell IR  @50% SoC 25C  : {cell_ir(0.50, 25):.4f} ohm")
print(f"  Cell IR  @20% SoC 25C  : {cell_ir(0.20, 25):.4f} ohm   (cells stiffen as they empty)")
print(f"  Cell IR  @20% SoC 12C  : {cell_ir(0.20, 12):.4f} ohm   (a cold pack is a stiff pack)")
print(f"  Wiring / connectors    : {WIRING_R:.4f} ohm  (nickel, XT90, 10 AWG, BMS shunt)")
print()
print(f"  PACK R  @50% SoC 25C   : {pack_resistance(0.50, 25):.4f} ohm   <-- BATT_RESISTANCE")
print(f"  PACK R  @20% SoC 25C   : {pack_resistance(0.20, 25):.4f} ohm")
print(f"  PACK R  @20% SoC 12C   : {pack_resistance(0.20, 12):.4f} ohm")

rule("CURRENT DRAW AND OHMIC LOSS")
i_hov = P_HOVER_W / V_NOM
i_peak = P_PEAK_W / V_NOM
for label, i, in (("Hover", i_hov), ("Peak (T/W 2.0)", i_peak)):
    per_cell = i / P
    hdr = "  " if per_cell <= CELL_IMAX else "! "
    print(f"{hdr}{label:<16}: {i:6.1f} A pack, {per_cell:5.1f} A/cell "
          f"({per_cell / CELL_IMAX:.0%} of rating), "
          f"I2R {i2r_loss_w(i):5.0f} W")
print()
print(f"  Hover I2R is {i2r_loss_w(i_hov) / P_HOVER_W:.1%} of hover power. The sizing model's flat")
print("  Wh bucket does not account for it, so usable energy is optimistic by")
print("  roughly that fraction.")

rule("THE DEFECT: A THRESHOLD PICKED OFF THE WRONG CURVE")
print(f"  BATT_FS_VOLTSRC = 1 (sag-compensated), but BATT_RESISTANCE was unset,")
print("  so it defaults to 0 and the compensation does nothing. The failsafe")
print("  compares LOADED voltage against a threshold chosen from the RESTING")
print("  curve.")
print()
print(f"  {'threshold':<14}{'intended SoC':>14}{'SoC it ACTUALLY fires at':>28}")
for name, v, intended in (("BATT_LOW_VOLT", CURRENT_LOW_V, 0.20),
                          ("BATT_CRT_VOLT", CURRENT_CRT_V, 0.10)):
    actual = soc_at_loaded_voltage(v, i_hov)
    print(f"  {name:<14}{intended:>13.0%}{actual:>27.0%}")
print()
low_actual = soc_at_loaded_voltage(CURRENT_LOW_V, i_hov)
print(f"  BATT_FS_LOW_ACT = 2 is RTL. Firing at {low_actual:.0%} instead of 20 % aborts the")
print("  search mid-mission and destroys the 2.0x reserve the pack was sized to.")

rule("THE FIX  -  and the two options are ALTERNATIVES, not both")
print("  BATT_LOW_VOLT is compared against whatever BATT_FS_VOLTSRC selects.")
print("  Setting the resistance AND lowering the threshold would apply the")
print("  correction twice and push the failsafe dangerously LATE -- the")
print("  opposite mistake, and a worse one.")
print()
print("  OPTION A  (recommended)  keep VOLTSRC = 1, set the resistance")
print(f"      BATT_RESISTANCE = {pack_resistance(0.50, 25):.3f}")
print(f"      BATT_LOW_VOLT   = {CURRENT_LOW_V:.1f}     unchanged -- correct once")
print(f"      BATT_CRT_VOLT   = {CURRENT_CRT_V:.1f}     compensation actually works")
print("    ArduPilot reconstructs resting voltage, so the 3.40 / 3.20 V-per-cell")
print("    thresholds finally mean what they were chosen to mean. This is the")
print("    right option because the thresholds stay readable as SoC.")
print()
print("  OPTION B  raw voltage, thresholds moved onto the loaded curve")
print("      BATT_FS_VOLTSRC = 0")
for name, soc in (("BATT_LOW_VOLT", 0.20), ("BATT_CRT_VOLT", 0.10)):
    v_loaded = loaded_voltage(soc, i_hov)
    print(f"      {name:<15} = {v_loaded:5.2f}  ({v_loaded / S:.2f} V/cell loaded at hover)")
print("    Simpler, no resistance to get wrong, but the thresholds are now tied")
print("    to ONE current. They read early in a climb and late in a descent.")
print()
print("  THE REAL BACKSTOP is coulomb counting, and it is already correct:")
print("      BATT_LOW_MAH = 2700  (20 %)      BATT_CRT_MAH = 1350  (10 %)")
print("    It is independent of resistance, sag and temperature. ArduPilot acts")
print("    on whichever failsafe fires first, so a correctly-set mAh threshold")
print("    protects the pack even if the voltage estimate is wrong. Do NOT")
print("    weaken it to compensate for a voltage threshold.")
print()
print("  ALSO SET, in either option:")
print("      BATT_LOW_TIMER = 10   explicit, so a delivery manoeuvre transient")
print("                            cannot end the mission by itself")

rule("PEAK DRAW AT END OF MISSION  -  the brownout question")
print("  A delivery manoeuvre near the end of the search is the worst case:")
print("  lowest SoC, highest transient current.")
print()
print(f"  {'SoC':>6}{'temp':>7}{'OCV':>9}{'hover V':>10}{'peak V':>9}{'peak V/cell':>13}")
for soc in (0.50, 0.30, 0.20, 0.10):
    for t in (25.0, 12.0):
        print(f"  {soc:>5.0%}{t:>6.0f}C{pack_ocv(soc):>9.2f}"
              f"{loaded_voltage(soc, i_hov, t):>10.2f}"
              f"{loaded_voltage(soc, i_peak, t):>9.2f}"
              f"{loaded_voltage(soc, i_peak, t) / S:>13.2f}")
print()
v_worst = loaded_voltage(0.20, i_peak, 12.0)
print(f"  Worst case above: {v_worst:.2f} V pack = {v_worst / S:.2f} V/cell.")
print()
print("  MODEL VALIDITY. This is a purely ohmic sag model, so it OVERSTATES the")
print("  droop at the bottom-right of the table -- real cells add polarisation")
print("  but the ESCs also current-limit long before 1.9 V/cell. Read the 10 %")
print("  rows as 'do not go there', not as a prediction. You should never be")
print("  there anyway: with the failsafe fixed, the aircraft lands at 20 %.")
print("  The 5 V avionics rail is fed from this bus. A BEC needs roughly 1-2 V")
print("  of headroom, so the rail is safe on voltage -- but the Jetson, the FC,")
print("  the mesh radio and the camera all sit behind it, and a companion")
print("  brownout loses perception AND the mission-state feed to the GCS.")
print("  Specify the BEC for the WORST case above, not the nominal 21.6 V.")

rule("THERMAL")
rise_sweep = temp_rise_k(i_hov, SWEEP_S)
rise_mission = temp_rise_k(i_hov, MISSION_S)
print(f"  Adiabatic rise, one 93 s sweep      : {rise_sweep:5.1f} K")
print(f"  Adiabatic rise, full 7.7 min mission: {rise_mission:5.1f} K")
print("  Adiabatic = no cooling at all, which is pessimistic for a pack sitting")
print("  in propwash. If this is comfortable the real figure certainly is.")

rule("WHAT IS PREDICTED VERSUS MEASURED")
print("  EVERY number above is a prediction from datasheet-class cell data.")
print("  None of it is measured. Before first flight:")
print()
print("    * Bench-discharge the real pack with a current step and compute")
print("      R = dV / dI. That measurement beats this model outright and takes")
print("      an afternoon.")
print("    * Log a hover and compare measured sag against the table above.")
print("    * Only then trust BATT_LOW_VOLT.")
print()
print("  The values here exist because the alternative currently in the")
print("  firmware is BATT_RESISTANCE = 0, which is not a better estimate.")
print()
print("  If you have a MATLAB licence, a Simscape Electrical pack model adds")
print("  diffusion/relaxation dynamics, per-cell imbalance and a real thermal")
print("  network. Those refine the numbers; they do not change the finding.")
rule()
