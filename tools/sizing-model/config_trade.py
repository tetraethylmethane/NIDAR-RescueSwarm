"""Configuration decision for RescueSwarm: quad vs hex vs octo vs coaxial X8.

Reuses the constants and physics of rescueswarm_sizing_model.py rather than
restating them, so this script cannot drift away from the design point.

Two things the main model cannot express, and this script adds:

1. COAXIAL. prop_area() multiplies disk area by N_rot, which assumes every
   rotor has its own free-stream disk. A coaxial pair does not -- the two
   rotors share one actuator disk. Here mass scales with MOTOR count while
   induced power scales with DISK count, with an interference penalty (kappa)
   on figure of merit.

2. FLIGHT DYNAMICS. The main model is steady-state momentum theory, so it
   cannot see vortex ring state, gust sensitivity or attitude bandwidth --
   which is where the hard part of this mission lives (precision
   hover-and-drop in wind). Sections 2-4 cover those.

Every config is sized to SATISFY THE RESERVE POLICY (endurance >= 2x mission
time, and nominal + re-sweep + 4 min loiter inside 80% DoD). Comparing configs
at a fixed pack size is misleading: it lets a thirsty config post a low
endurance instead of paying for the battery it would actually need. Because
the 2x endurance rule binds for every config, pack size ends up directly
proportional to hover power, so a power penalty compounds into fleet mass.

Run:  python tools/sizing-model/config_trade.py
"""
import contextlib
import io
import os

import numpy as np

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'rescueswarm_sizing_model.py')

G = {'__name__': '__trade__'}
with open(MODEL, encoding='utf-8') as f:
    src = f.read()
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src, MODEL, 'exec'), G)

g, rho, FM = G['g'], G['rho'], G['FM']
eta_chain, P_avio = G['eta_prop_chain'], G['P_avio']
m_avio, m_pay = G['m_avio'], G['m_payload_sys']
k_struct, k_esc = G['k_struct'], G['k_esc']
spec_thrust, T_W = G['spec_thrust_motor'], G['T_W']
m_prop_18, DOD, e_liion = G['m_prop_ea'], G['DOD'], G['e_liion']

D18 = 18 * 0.0254            # anchor: m_prop_ea is the 18 in mass
BOX = 3.6576                 # 12 ft launch/landing box, m
C_T = 0.012                  # thrust coeff on disk area + tip speed, typical
                             # multirotor prop. Used only for advance ratio.

# --- mission geometry (config-independent, replicated from the main model) --
v_climb, v_desc = 3.0, 2.5
h_search, h_transit, h_drop = 60.0, 40.0, 6.0
v_search, v_transit = 8.0, 12.0
k_cruise = 0.93
HFOV = np.deg2rad(70)
W_sw = 2 * h_search * np.tan(HFOV / 2)
S = W_sw * (1 - 0.30)
n_lines = np.ceil(250 / S)
L_per = n_lines * 400 / 3
t_turns = (n_lines / 3) * 6.0
t_sweep = L_per / v_search + t_turns
n_del = 10 / 3
per_del_t = (150 / v_transit + (h_search - h_drop) / v_desc + 8 + 2
             + (h_transit - h_drop) / v_climb)


def prop_mass(D):
    """Prop mass ~D^2.5 (planform x thickness), anchored at the 18 in BOM part.

    The main model holds prop mass fixed across diameters, which is fine when
    diameter is not the variable. Here it is, so it has to scale.
    """
    return m_prop_18 * (D / D18) ** 2.5


def converge_mass(n_motors, D, m_batt):
    m = 6.0
    for _ in range(500):
        m_mot = n_motors * (T_W * m * g / n_motors) / spec_thrust
        m_new = (m_avio + m_pay + m_batt + m_mot + k_esc * m_mot
                 + n_motors * prop_mass(D)) / (1 - k_struct)
        if abs(m_new - m) < 1e-12:
            break
        m = m_new
    return m


def hover_power(m, n_disks, D, kappa):
    A = n_disks * np.pi * (D / 2) ** 2
    P_shaft = (m * g) ** 1.5 / (FM * kappa * np.sqrt(2 * rho * A))
    return P_shaft / eta_chain + P_avio, A


def mission_TE(m, Ph):
    P_cr = (Ph - P_avio) * k_cruise + P_avio
    segs = [(45, Ph * 0.35),
            (h_search / v_climb, Ph + m * g * v_climb / eta_chain),
            (120 / v_transit, P_cr), (t_sweep, P_cr),
            (n_del * per_del_t, P_cr * 0.98), (250 / v_transit, P_cr),
            (90, Ph)]
    return (sum(s[0] for s in segs),
            sum(s[0] * s[1] / 3600 for s in segs), P_cr)


def size_to_policy(n_motors, n_disks, D, kappa=1.0, T_W_=None):
    """Grow the pack until BOTH reserve conditions hold."""
    global T_W
    T_W_saved = T_W
    if T_W_ is not None:
        T_W = T_W_
    mb = 0.5
    for _ in range(800):
        m = converge_mass(n_motors, D, mb)
        Ph, A = hover_power(m, n_disks, D, kappa)
        T, E, P_cr = mission_TE(m, Ph)
        E_need = E + t_sweep * P_cr / 3600 + 4 * 60 * Ph / 3600
        mb_new = max(E_need / DOD,
                     2 * (T / 60) * Ph / (60 * DOD)) / e_liion
        if abs(mb_new - mb) < 1e-10:
            break
        mb = 0.5 * mb + 0.5 * mb_new
    m = converge_mass(n_motors, D, mb)
    Ph, A = hover_power(m, n_disks, D, kappa)
    T, E, P_cr = mission_TE(m, Ph)
    T_W = T_W_saved
    v_i = np.sqrt((m * g / A) / (2 * rho))
    v_tip = np.sqrt((m * g / n_motors) / (C_T * rho * np.pi * (D / 2) ** 2))
    return dict(m=m, A=A, DL=m / A, P=Ph, E=mb * e_liion, T=T, v_i=v_i,
                t_hov=60 * mb * e_liion * DOD / Ph, v_tip=v_tip,
                J=n_motors * prop_mass(D) * (D / 2) ** 2)


def footprint(n_arms, D, clr=0.03):
    if n_arms == 4:
        return 2 * D + clr
    R = (D + clr) / (2 * np.sin(np.pi / n_arms))
    return 2 * R + D


CONFIGS = [
    ('Quad  4x18"  (current)', 4, 4, 18, 4, 1.00),
    ('Quad  4x20"',            4, 4, 20, 4, 1.00),
    ('Quad  4x16"',            4, 4, 16, 4, 1.00),
    ('Hex   6x18"',            6, 6, 18, 6, 1.00),
    ('Hex   6x16"',            6, 6, 16, 6, 1.00),
    ('Octo  8x14"  (flat)',    8, 8, 14, 8, 1.00),
    ('X8 coax 4x2x20" k=.85',  8, 4, 20, 4, 0.85),
    ('X8 coax 4x2x20" k=.80',  8, 4, 20, 4, 0.80),
    ('X8 coax 4x2x18" k=.80',  8, 4, 18, 4, 0.80),
    ('X8 coax 4x2x22" k=.80',  8, 4, 22, 4, 0.80),
]


def main():
    res = {}
    print("=" * 96)
    print("SECTION 1  CONFIGS SIZED TO THE RESERVE POLICY (battery spiral included)")
    print("=" * 96)
    print(f"{'config':<26}{'pack':>7}{'MTOW':>7}{'fleet':>8}{'cap':>6}"
          f"{'P_hov':>8}{'DL':>7}{'foot':>7}{'/box':>6}{'dP':>8}{'dmass':>8}")
    print(f"{'':<26}{'Wh':>7}{'kg':>7}{'kg':>8}{'25kg':>6}"
          f"{'W':>8}{'kg/m2':>7}{'mm':>7}{'':>6}{'vs quad':>8}{'vs quad':>8}")
    print('-' * 96)
    base = None
    for lbl, nm, nd, D_in, arms, kap in CONFIGS:
        r = size_to_policy(nm, nd, D_in * 0.0254, kap)
        r['foot'] = footprint(arms, D_in * 0.0254)
        res[lbl] = r
        if base is None:
            base = r
        fleet = 3 * r['m']
        print(f"{lbl:<26}{r['E']:7.0f}{r['m']:7.2f}{fleet:8.2f}"
              f"{'OK' if fleet <= 25 else 'FAIL':>6}{r['P']:8.0f}{r['DL']:7.2f}"
              f"{r['foot']*1000:7.0f}{int(np.floor(BOX/r['foot'])):6d}"
              f"{100*(r['P']/base['P']-1):+7.1f}%{100*(r['m']/base['m']-1):+7.1f}%")

    print()
    print("  Every config lands at exactly 15.5 min hover / 2.00x mission, because the")
    print("  2x-endurance rule -- not the energy rule -- is what binds. Pack size is")
    print("  therefore proportional to hover power, and a power penalty compounds:")
    print("  more battery -> more mass -> more power. That is the coaxial story.")
    print()
    cx = [res[k] for k in res if 'coax' in k]
    print(f"  COAXIAL VERDICT: +{min(100*(c['P']/base['P']-1) for c in cx):.0f} to "
          f"+{max(100*(c['P']/base['P']-1) for c in cx):.0f}% hover power and "
          f"+{min(100*(c['m']/base['m']-1) for c in cx):.0f} to "
          f"+{max(100*(c['m']/base['m']-1) for c in cx):.0f}% fleet mass,")
    print(f"  cutting the {100*(1-3*base['m']/25):.0f}% mass margin to "
          f"{100*(1-3*max(c['m'] for c in cx)/25):.0f}%. It buys NO footprint back --")
    print("  stacking rotors does not shorten the arms, so the X8 footprint equals")
    print("  the quad it replaces. Coaxial pays only when rotors must shrink to fit")
    print("  a box; the quad already fits 3 per row. Rejected at every kappa.")

    print("\n" + "=" * 96)
    print("SECTION 2  FLIGHT DYNAMICS  -  what steady-state momentum theory misses")
    print("=" * 96)
    print(f"{'config':<26}{'v_i':>7}{'VRS window':>15}{'desc@2.5':>10}"
          f"{'gust dT/W':>11}{'J_rotor':>9}")
    print(f"{'':<26}{'m/s':>7}{'m/s':>15}{'x v_i':>10}{'per m/s':>11}{'rel':>9}")
    print('-' * 96)
    J0 = res['Quad  4x18"  (current)']['J']
    for lbl, *_ in CONFIGS:
        r = res[lbl]
        vi = r['v_i']
        flag = '  <-- IN VRS' if 2.5 >= 0.5 * vi else ''
        print(f"{lbl:<26}{vi:7.2f}{f'{0.5*vi:.1f} - {1.5*vi:.1f}':>15}"
              f"{2.5/vi:10.2f}{1/vi:11.3f}{r['J']/J0:9.2f}{flag}")
    print()
    print("  v_i        hover induced velocity, sqrt(DL*g/2rho)")
    print("  VRS        vertical descent band where vortex ring state develops.")
    print("             Onset is conventionally taken at 0.25-0.5 v_i, worst near 0.7-1.0.")
    print("  desc@2.5   the model's 2.5 m/s descent rate as a fraction of v_i")
    print("  gust dT/W  vertical gust sensitivity = 1/v_i exactly (from T = 2 rho A v_i^2,")
    print("             dT/dV at V=0 is 2 rho A v_i, normalised by W). A 1 m/s vertical")
    print("             gust perturbs thrust by this fraction of weight, open loop.")
    print("             LOW disk loading = MORE gust sensitive. Not a virtue here.")
    print("  J_rotor    total rotor inertia proxy, sum(m_prop * R^2), vs current quad.")
    print("             Higher = slower thrust response = lower attitude bandwidth.")
    print("             PROXY ONLY. Response time scales steeply with diameter")
    print("             (tau ~ D^3.5 at fixed aircraft power); needs bench measurement.")

    print("\n" + "=" * 96)
    print("SECTION 3  BLADE STALL / ADVANCE RATIO")
    print("=" * 96)
    print(f"  Tip speed from T = C_T rho A (omega R)^2 with C_T = {C_T} (assumed).")
    print(f"  Retreating-blade effects appear above advance ratio mu ~ 0.30.\n")
    print(f"{'config':<26}{'v_tip':>8}{'mu @8':>8}{'mu @12':>8}{'mu @16':>8}{'mu @20':>8}")
    print('-' * 96)
    for lbl in ['Quad  4x18"  (current)', 'Quad  4x20"', 'Quad  4x16"']:
        r = res[lbl]
        vt = r['v_tip']
        print(f"{lbl:<26}{vt:8.1f}" + ''.join(f"{v/vt:8.2f}" for v in (8, 12, 16, 20)))
    print()
    print("  READING: blade stall is NOT a limit at search (8 m/s) or transit (12 m/s)")
    print("  speed -- mu stays near 0.2. But mu approaches 0.30 around 20 m/s, so if")
    print("  search airspeed is raised for wind penetration, validate it rather than")
    print("  assuming the drag-only model of CORRECTION 4 still holds.")

    print("\n" + "=" * 96)
    print("SECTION 4  VRS-SAFE DESCENT PROFILE  (current quad, v_i = "
          f"{res['Quad  4x18\"  (current)']['v_i']:.2f} m/s)")
    print("=" * 96)
    vi = res['Quad  4x18"  (current)']['v_i']
    print(f"{'descent rate':>14}{'x v_i':>8}{'verdict':>26}{'54 m takes':>13}"
          f"{'vs 2.5 m/s':>12}")
    print('-' * 96)
    for vd in [1.0, 1.25, 1.5, 2.0, 2.5, 3.0]:
        t = 54 / vd
        verdict = 'safe' if vd < 0.25 * vi else ('marginal' if vd < 0.5 * vi
                                                 else 'VRS RISK')
        print(f"{vd:11.2f} m/s{vd/vi:8.2f}{verdict:>26}{t:11.1f} s"
              f"{t-54/2.5:+11.1f} s")
    print()
    print(f"  Nulled-groundspeed descent is near-vertical, which is exactly the")
    print(f"  condition VRS needs. Two fixes, both nearly free against a 74% time margin:")
    print(f"    (a) descend at <= 1.25 m/s (0.25 v_i) -- costs +21.6 s per drop, or")
    print(f"        ~+72 s per aircraft over 3.3 drops, on a 7.7 of 30 min mission;")
    print(f"    (b) keep horizontal speed >= v_i ({vi:.1f} m/s) through the descent and")
    print(f"        decelerate to hover at the 6 m drop altitude -- costs nothing.")
    print(f"  (b) is preferred: it also cuts exposure time in the gust-sensitive regime.")

    print("\n" + "=" * 96)
    print("SECTION 5  THRUST-TO-WEIGHT SWEEP  -  what the mass margin would buy")
    print("=" * 96)
    print(f"{'T/W':>6}{'MTOW':>8}{'fleet':>8}{'margin':>9}{'P_hov':>8}"
          f"{'pack':>8}{'hov thr':>9}")
    print('-' * 56)
    for tw in [2.0, 2.2, 2.5, 2.8, 3.0]:
        r = size_to_policy(4, 4, D18, 1.0, T_W_=tw)
        print(f"{tw:6.1f}{r['m']:8.2f}{3*r['m']:8.2f}{25.0-3*r['m']:9.2f}"
              f"{r['P']:8.0f}{r['E']:7.0f}W{100/tw:8.0f}%")
    print()
    print("  READING: do not spend margin here. CORRECTION 4 of the main model shows")
    print("  tilt reaches only 12.2 deg at 15 m/s airspeed (thrust factor 1.023), so")
    print("  attitude authority is never the wind limit. Keep T/W 2.0.")


if __name__ == '__main__':
    main()
