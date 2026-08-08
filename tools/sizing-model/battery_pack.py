"""Pack electrical model -- internal resistance, sag, and the failsafe thresholds.

WHY THIS EXISTS
---------------
`rescueswarm_sizing_model.py` treats the pack as a flat energy bucket:
`E = m_batt * e_spec * DOD`, with a fixed motor+ESC efficiency. That is the
right level of detail for sizing, and it is blind to the thing that actually
decides whether the aircraft completes a mission: **voltage under load**.

It matters here specifically because the firmware sets

    BATT_FS_VOLTSRC = 1        # sag-compensated voltage
    BATT_LOW_VOLT   = 20.4     # 6 x 3.40 V, chosen as "~20 % SoC RESTING"

Sag compensation computes `resting = measured + current * BATT_RESISTANCE`.
**BATT_RESISTANCE was not set**, so it defaults to 0 and the compensation does
nothing until ArduPilot learns it in flight. The failsafe therefore compares a
*loaded* voltage against a threshold chosen from a *resting* curve, and fires
early -- at roughly half pack rather than at 20 %.

`BATT_FS_LOW_ACT = 2` is RTL. Firing at half pack aborts the search, destroys
the 2.0x reserve the whole battery sizing rests on, and is a scored failure.

This module produces the missing numbers:

    * BATT_RESISTANCE          the pack internal resistance, ohms
    * BATT_LOW_VOLT            corrected for the loaded comparison
    * BATT_CRT_VOLT            same
    * peak-draw sag at 80 % DoD, and whether the 5 V rail survives it

WHAT THIS IS AND IS NOT
-----------------------
This is the physics a Simscape Electrical pack model would give you, written in
the language the rest of the model already uses so it stays inside the
single-source-of-truth rule and inside CI. It captures OCV-vs-SoC, ohmic IR,
IR rise at low SoC and cold, and a lumped thermal rise.

It does **not** capture diffusion/relaxation dynamics, per-cell imbalance, or
ageing. If you have a MATLAB licence and someone who knows Simscape, a proper
pack model adds those; the note at the bottom says what to model.

**Every number here is a prediction from a datasheet-class cell, not a
measurement.** BATT_RESISTANCE must be measured on the real pack before first
flight -- a bench discharge with a current step gives it in an afternoon and
beats any model. Until then these values are better than the 0 that is there
now, which is not a high bar.
"""
from __future__ import annotations

# ----------------------------------------------------------------- cell data
# Molicel P45B class, matching rescueswarm_sizing_model.py's
# '21700 Li-ion, 4500 mAh 45 A class'. DC internal resistance for this class of
# high-drain 21700 is 12-16 mOhm at 25 C and 50 % SoC; 15 mOhm is the
# conservative end of the datasheet band.
CELL_IR_25C_50SOC = 0.015      # ohm
CELL_AH = 4.5
CELL_IMAX = 45.0               # A continuous

S, P = 6, 3                    # 6S3P
N_CELLS = S * P

# Interconnect: nickel strip / solder joints, XT90, 10 AWG leads, BMS shunt,
# and the ESC power distribution. Measured values for a build this size land
# around 8-12 mOhm; 10 mOhm is a fair estimate and is NOT negligible next to
# the 30 mOhm of cells.
WIRING_R = 0.010               # ohm

# OCV vs state of charge, 21700 NMC, per cell, at rest and 25 C.
# From the flat-ish middle to the knee. Linear interpolation between points is
# good to a few tens of mV, which is enough to place a failsafe threshold.
OCV_CURVE = [
    (1.00, 4.15), (0.90, 4.03), (0.80, 3.92), (0.70, 3.83), (0.60, 3.74),
    (0.50, 3.66), (0.40, 3.58), (0.30, 3.50), (0.20, 3.40), (0.15, 3.34),
    (0.10, 3.24), (0.05, 3.08), (0.00, 2.80),
]

# Internal resistance multiplier vs SoC. Cells stiffen as they empty; the rise
# below 20 % is the part that matters, because that is where the failsafe lives.
IR_VS_SOC = [
    (1.00, 1.05), (0.80, 1.00), (0.50, 1.00), (0.30, 1.08),
    (0.20, 1.18), (0.10, 1.45), (0.05, 1.85), (0.00, 2.40),
]

# Temperature multiplier. India in January: dawn ground temperature of 12-15 C
# is plausible, and a cold pack is a stiff pack.
IR_VS_TEMP = [(0.0, 2.20), (10.0, 1.45), (20.0, 1.12), (25.0, 1.00),
              (35.0, 0.92), (45.0, 0.90)]

CELL_MASS_KG = 0.070
CELL_CP = 1000.0               # J/kg/K, typical Li-ion lumped specific heat


def _interp(table, x):
    """Linear interpolation over a table sorted either way, clamped at ends."""
    pts = sorted(table, key=lambda t: t[0])
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def cell_ocv(soc: float) -> float:
    return _interp(OCV_CURVE, soc)


def cell_ir(soc: float, temp_c: float = 25.0) -> float:
    return CELL_IR_25C_50SOC * _interp(IR_VS_SOC, soc) * _interp(IR_VS_TEMP, temp_c)


def pack_resistance(soc: float = 0.5, temp_c: float = 25.0,
                    include_wiring: bool = True) -> float:
    """Pack internal resistance.

    S cells in series multiply resistance; P in parallel divide it.
    This is the number ArduPilot wants in BATT_RESISTANCE -- and ArduPilot's
    sag compensation uses the resistance seen at the monitor, so the wiring and
    connectors between the monitor and the cells count.
    """
    r = S * cell_ir(soc, temp_c) / P
    return r + WIRING_R if include_wiring else r


def pack_ocv(soc: float) -> float:
    return S * cell_ocv(soc)


def loaded_voltage(soc: float, current_a: float, temp_c: float = 25.0) -> float:
    return pack_ocv(soc) - current_a * pack_resistance(soc, temp_c)


def soc_at_loaded_voltage(v_target: float, current_a: float,
                          temp_c: float = 25.0) -> float:
    """The SoC at which a given LOADED voltage is reached.

    This is the question the failsafe actually asks, and the one the current
    thresholds got wrong: BATT_LOW_VOLT was picked off a resting curve.
    """
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if loaded_voltage(mid, current_a, temp_c) < v_target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def i2r_loss_w(current_a: float, soc: float = 0.5, temp_c: float = 25.0) -> float:
    return current_a ** 2 * pack_resistance(soc, temp_c, include_wiring=False)


def temp_rise_k(current_a: float, seconds: float, soc: float = 0.5,
                temp_c: float = 25.0) -> float:
    """Adiabatic lumped temperature rise -- no cooling.

    Deliberately pessimistic: a hovering multirotor has propwash over the pack,
    so the real rise is lower. If the adiabatic number is comfortable, the real
    one certainly is; that is the only claim being made.
    """
    q = i2r_loss_w(current_a, soc, temp_c) * seconds
    return q / (N_CELLS * CELL_MASS_KG * CELL_CP)
