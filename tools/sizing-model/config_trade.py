"""Configuration trade for RescueSwarm: quad vs hex vs octo vs coaxial X8.

Reuses the constants and physics of rescueswarm_sizing_model.py rather than
restating them, so this script cannot drift away from the design point.

The one thing the main model cannot express is coaxial. Its prop_area()
multiplies disk area by N_rot, which is wrong for stacked rotors: a coaxial
pair shares a single actuator disk, so doubling the motor count does not
double the disk area. Here mass scales with MOTOR count while induced power
scales with DISK count, with an interference penalty on figure of merit.

Run:  python tools/sizing-model/config_trade.py
"""
import contextlib
import io
import os

import numpy as np

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'rescueswarm_sizing_model.py')

# The model prints its full report at import; swallow it and keep the globals.
G = {'__name__': '__trade__'}
with open(MODEL, encoding='utf-8') as f:
    src = f.read()
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src, MODEL, 'exec'), G)

g, rho, FM = G['g'], G['rho'], G['FM']
eta_chain, P_avio = G['eta_prop_chain'], G['P_avio']
m_avio, m_pay = G['m_avio'], G['m_payload_sys']
k_struct, k_esc = G['k_struct'], G['k_esc']
spec_thrust = G['spec_thrust_motor']
T_W_base = G['T_W']
m_prop_20 = G['m_prop_ea']          # kg at 20 in
DOD = G['DOD']
E_pack = G['E_pack']                # Wh, from the committed design point
m_batt = G['m_pack']                # kg, held constant across configs

D20 = 20 * 0.0254
BOX = 3.6576                        # 12 ft launch/landing box, m


def prop_mass(D):
    """Prop mass scales ~D^2.5 (planform x thickness), anchored at 20 in.

    The main model holds prop mass fixed across diameters, which is fine when
    diameter is not the variable. Here it is, so it has to scale.
    """
    return m_prop_20 * (D / D20) ** 2.5


def size(n_motors, n_disks, D, T_W=T_W_base, coax_kappa=1.0):
    """Fixed point on MTOW, then hover power on the TRUE disk area."""
    m = 6.0
    for _ in range(400):
        T_motor = T_W * m * g / n_motors
        m_mot = n_motors * T_motor / spec_thrust
        m_esc = k_esc * m_mot
        m_prop = n_motors * prop_mass(D)
        m_new = (m_avio + m_pay + m_batt + m_mot + m_esc + m_prop) / (1 - k_struct)
        if abs(m_new - m) < 1e-12:
            break
        m = m_new
    A = n_disks * np.pi * (D / 2) ** 2
    P_shaft = (m * g) ** 1.5 / (FM * coax_kappa * np.sqrt(2 * rho * A))
    return dict(m=m, A=A, DL=m / A, P=P_shaft / eta_chain + P_avio)


def footprint(n_arms, D, clr=0.03):
    """Overall square footprint, same convention as the main model."""
    if n_arms == 4:
        return 2 * D + clr
    R = (D + clr) / (2 * np.sin(np.pi / n_arms))   # rotor centres on a circle
    return 2 * R + D


CONFIGS = [
    # label,                     motors, disks, D_in, arms, kappa
    ('Quad  4x20"  (current)',        4, 4, 20, 4, 1.00),
    ('Hex   6x16"',                   6, 6, 16, 6, 1.00),
    ('Hex   6x18"',                   6, 6, 18, 6, 1.00),
    ('Octo  8x14"  (flat)',           8, 8, 14, 8, 1.00),
    ('X8 coax 4x2x20"  k=0.85',       8, 4, 20, 4, 0.85),
    ('X8 coax 4x2x20"  k=0.80',       8, 4, 20, 4, 0.80),
    ('X8 coax 4x2x22"  k=0.80',       8, 4, 22, 4, 0.80),
]


def main():
    print("=" * 84)
    print("CONFIGURATION TRADE  -  quad vs hex vs octo vs coaxial X8")
    print("=" * 84)
    print(f"  Pack held constant at {E_pack:.0f} Wh ({m_batt*1000:.0f} g) for every config,")
    print("  so endurance differs only through hover power.\n")

    print(f"{'config':<28}{'MTOW':>7}{'fleet':>8}{'P_hov':>8}{'DL':>8}"
          f"{'hover':>8}{'foot':>8}{'/box':>6}{'dP':>8}")
    print(f"{'':<28}{'kg':>7}{'kg':>8}{'W':>8}{'kg/m2':>8}{'min':>8}{'mm':>8}"
          f"{'':>6}{'vs quad':>8}")
    print("-" * 84)

    base = None
    for lbl, nm, nd, D_in, arms, kap in CONFIGS:
        D = D_in * 0.0254
        r = size(nm, nd, D, coax_kappa=kap)
        t_hov = 60 * E_pack * DOD / r['P']
        fp = footprint(arms, D)
        if base is None:
            base = r
        dP = 100 * (r['P'] / base['P'] - 1)
        print(f"{lbl:<28}{r['m']:7.2f}{3*r['m']:8.2f}{r['P']:8.0f}{r['DL']:8.2f}"
              f"{t_hov:8.1f}{fp*1000:8.0f}{int(np.floor(BOX/fp)):6d}{dP:+7.1f}%")

    print()
    print("  k = coaxial interference factor on figure of merit. Published multirotor")
    print("  coaxial pairs sit around 0.80-0.87; 0.80/0.85 brackets the plausible range.")
    print("  /box = airframes that fit per row in the 12 ft (3.66 m) launch box.")
    print()
    print("  READING: coaxial costs ~30% hover power and buys NO footprint back,")
    print("  because stacking rotors does not shorten the arms. The X8 footprint is")
    print("  identical to the quad it replaces. Coaxial pays only when you are forced")
    print("  to shrink rotors to fit a box -- and the quad already fits 3 per row.")
    print()
    print("  Hex 6x18\" is the one config that beats the quad on physics: 6 disks of")
    print("  18 in give 0.985 m2 against the quad's 0.811 m2, so power and disk loading")
    print("  both improve. Its cost is footprint, assembly and preflight time -- which")
    print("  land on setup, the only constraint with less than 20% margin.")

    print("\n" + "=" * 84)
    print("THRUST-TO-WEIGHT SWEEP  -  what the fleet mass margin would buy")
    print("=" * 84)
    print(f"{'T/W':>6}{'MTOW':>8}{'fleet':>8}{'margin':>9}{'P_hov':>8}"
          f"{'hover':>8}{'hov thr':>9}")
    print("-" * 56)
    for tw in [2.0, 2.2, 2.5, 2.8, 3.0, 3.5]:
        r = size(4, 4, D20, T_W=tw)
        t_hov = 60 * E_pack * DOD / r['P']
        print(f"{tw:6.1f}{r['m']:8.2f}{3*r['m']:8.2f}{25.0-3*r['m']:9.2f}"
              f"{r['P']:8.0f}{t_hov:8.1f}{100/tw:8.0f}%")
    print()
    print("  READING: do not spend margin here. CORRECTION 4 of the main model shows")
    print("  tilt reaches only 12.2 deg at 15 m/s airspeed (thrust factor 1.023), so")
    print("  attitude authority is never the wind limit. Raising T/W to 2.5 costs")
    print("  1.1 min of endurance and buys almost nothing.")


if __name__ == '__main__':
    main()
