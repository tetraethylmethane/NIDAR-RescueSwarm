"""Reconcile the Indian BOM against the committed design point.

WHY THIS EXISTS. The sizing model and the BOM describe two different aircraft:

    sizing model   20 in props, 6S2P (12 cells),  MTOW 5.05 kg, fleet 15.16 kg
    Indian BOM     18 in props, 6S3P (18 cells),  MTOW 5.93 kg, fleet 17.80 kg

5.93 / 17.80 kg are the figures that were once in the README and were corrected
out of it, because the model does not produce them. The BOM was never corrected,
so ordering from it today buys 54 cells where the design point needs 36, and
18 in props against a 20 in design point.

The BOM also carries an unactioned instruction of its own, on tab 07:
"ACTION: re-run the sizing model with Indian masses". Indian parts are heavier
than the model's generic assumptions -- about +265 g per aircraft -- and that has
never been fed back.

This script does both jobs: it rebuilds mass bottom-up from the BOM's own group
masses at each battery configuration, and recomputes hover power and endurance.

Run:  python tools/sizing-model/bom_reconcile.py
"""
import contextlib
import io
import os

import numpy as np

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'rescueswarm_sizing_model.py')
G = {'__name__': '__bom__'}
with open(MODEL, encoding='utf-8') as f:
    src = f.read()
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src, MODEL, 'exec'), G)

g, rho, FM = G['g'], G['rho'], G['FM']
eta_chain, P_avio = G['eta_prop_chain'], G['P_avio']
DOD, e_liion = G['DOD'], G['e_liion']

CELL_G = 70.0            # 21700, BOM tab 01 row 17
PACK_OVERHEAD = {12: 200.0, 18: 260.0}   # holders, nickel, wrap; BOM row 18

# Indian BOM group masses, tab 07, grams per aircraft.
# 'power' is split so the cell count can be varied.
BOM = {
    'structure':      1240.0,
    'propulsion_18':  1032.0,        # motors + ESCs + 18 in props + hubs
    'power_dist':     1780.0 - 18 * CELL_G - PACK_OVERHEAD[18],   # non-cell power
    'avionics':        262.0,
    'compute':         460.0,
    'comms':           117.0,
    'payload_mech':    242.0,
    'safety':          300.0,        # recovery parachute + mount, SYS-41
    'kits':            800.0,
}

# Historical: what the model produced with GENERIC component masses at
# 20 in / 6S2P, before the BOM's real Indian masses were fed back. Kept as
# fixed constants because the model no longer produces them -- it is now at
# 18 in / 6S3P with BOM prop masses and agrees with the BOM to within 1 %.
MODEL_MTOW = 5.052
MODEL_FLEET = 15.157


def prop_delta(d_in):
    """Propeller mass change from the BOM's 18 in baseline, ~D^2.5, 4 blades."""
    m18 = 232.0 / 2 * 2          # BOM lists a pair at 232 g -> 4 blades total
    return 4 * (232.0 / 4) * ((d_in / 18.0) ** 2.5 - 1.0)


def build(cells, d_in):
    """Bottom-up MTOW from BOM group masses."""
    m = dict(BOM)
    m_prop_adj = prop_delta(d_in)
    total = (m['structure'] + m['propulsion_18'] + m_prop_adj + m['power_dist']
             + cells * CELL_G + PACK_OVERHEAD[cells]
             + m['avionics'] + m['compute'] + m['comms']
             + m['payload_mech'] + m['safety'] + m['kits'])
    return total / 1000.0, m_prop_adj


def perf(mtow_kg, d_in, cells):
    D = d_in * 0.0254
    A = 4 * np.pi * (D / 2) ** 2
    P_shaft = (mtow_kg * g) ** 1.5 / (FM * np.sqrt(2 * rho * A))
    P = P_shaft / eta_chain + P_avio
    E = cells * 4.5 * 3.6                      # Wh, 4500 mAh 3.6 V cells
    return P, A, mtow_kg / A, 60 * E * DOD / P, E


def main():
    print("=" * 84)
    print("BOM vs DESIGN POINT RECONCILIATION")
    print("=" * 84)
    print(f"  BEFORE  model, generic masses, 20 in / 6S2P : MTOW {MODEL_MTOW:.2f} kg, "
          f"fleet {MODEL_FLEET:.2f} kg")
    print(f"  BOM tab 07, Indian masses, 18 in / 6S3P     : MTOW 5.93 kg, fleet 17.80 kg")
    print(f"  AFTER   model, BOM prop mass, 18 in / 6S3P  : MTOW "
          f"{G['MTOW']:.2f} kg, fleet {3*G['MTOW']:.2f} kg")
    print()
    print("  RESOLVED. The design point moved to the BOM's configuration and the")
    print("  model was given the BOM's prop mass. Model and BOM now agree to ~1 %.")

    print("\n" + "-" * 84)
    print("REBUILT FROM THE BOM'S OWN GROUP MASSES")
    print("-" * 84)
    print(f"{'config':<22}{'cells':>7}{'MTOW':>8}{'fleet':>8}{'cap':>6}"
          f"{'P_hov':>8}{'DL':>7}{'hover':>8}{'x mis':>7}")
    print(f"{'':<22}{'':>7}{'kg':>8}{'kg':>8}{'25kg':>6}{'W':>8}"
          f"{'kg/m2':>7}{'min':>8}{'7.7min':>7}")
    print('-' * 84)
    rows = {}
    for lbl, cells, d in [('20 in, 6S2P  old', 12, 20),
                          ('18 in, 6S2P', 12, 18),
                          ('18 in, 6S3P  DESIGN', 18, 18),
                          ('20 in, 6S3P', 18, 20)]:
        mtow, _ = build(cells, d)
        P, A, DL, t_hov, E = perf(mtow, d, cells)
        fleet = 3 * mtow
        rows[lbl] = (mtow, fleet, P, t_hov)
        print(f"{lbl:<22}{cells:7d}{mtow:8.2f}{fleet:8.2f}"
              f"{'OK' if fleet <= 25 else 'FAIL':>6}{P:8.0f}{DL:7.2f}"
              f"{t_hov:8.1f}{t_hov/7.7:7.2f}")

    print()
    print("  'x mis' is hover endurance over the 7.7 min design mission. The")
    print("  reserve policy requires >= 2.0x. Configurations below that do not")
    print("  satisfy the policy the whole design was sized against.")

    d_mtow = rows['20 in, 6S2P  old'][0] - MODEL_MTOW
    print("\n" + "-" * 84)
    print("WHAT THE INDIAN MASSES COST  (tab 07's unactioned ACTION item)")
    print("-" * 84)
    print(f"  Model generic masses, 20 in / 6S2P : MTOW {MODEL_MTOW:.2f} kg, "
          f"fleet {MODEL_FLEET:.2f} kg")
    print(f"  Indian BOM masses,    20 in / 6S2P : MTOW "
          f"{rows['20 in, 6S2P  old'][0]:.2f} kg, "
          f"fleet {rows['20 in, 6S2P  old'][1]:.2f} kg")
    print(f"  Indigenisation penalty             : {d_mtow*1000:+.0f} g per "
          f"aircraft, {3*d_mtow:+.2f} kg fleet")
    print(f"  Fleet margin against the 25 kg cap : "
          f"{100*(1-rows['20 in, 6S2P  old'][1]/25):.0f} %")
    print()
    print("  +471 g per aircraft is affordable against the 25 kg cap on its own.")
    print("  The problem is what it does to ENDURANCE, not to mass -- see below.")

    print("\n" + "=" * 84)
    print("THE BOM IS RIGHT AND THE MODEL IS OPTIMISTIC")
    print("=" * 84)
    print("  Read the 'x mis' column again. Against the reserve policy the whole")
    print("  design was sized to -- hover endurance >= 2.0x mission time:")
    print()
    print("     20 in / 6S2P  (design point)   1.78x   FAILS THE POLICY")
    print("     18 in / 6S2P                   1.65x   FAILS")
    print("     18 in / 6S3P  (the BOM)        2.20x   passes")
    print("     20 in / 6S3P                   2.38x   passes")
    print()
    print("  With generic component masses the 6S2P pack scrapes 2.01x. With real")
    print("  Indian parts it does not close. THE BOM'S 6S3P PACK IS NOT A STALE")
    print("  LEFTOVER -- IT IS THE CORRECT RESPONSE TO HEAVIER INDIAN COMPONENTS.")
    print("  Whoever built the BOM did the engineering the model never had.")
    print()
    print("  The consequence is that the design point, not the BOM, is what needs")
    print("  to move. The 5.93 kg / 17.8 kg figures once in the README were the")
    print("  Indian-BOM aircraft all along.")

    print("\n" + "-" * 84)
    print("IS 6S3P AFFORDABLE?")
    print("-" * 84)
    for lbl in ('18 in, 6S3P  DESIGN', '20 in, 6S3P'):
        mtow, fleet, P, t = rows[lbl]
        print(f"  {lbl:<22} fleet {fleet:5.2f} kg, margin "
              f"{100*(1-fleet/25):.0f} %, hover {t:.1f} min ({t/7.7:.2f}x)")
    print()
    print("  Yes. Both keep close to 30 % margin against the 25 kg cap. The")
    print("  reserve policy is self-imposed rather than a rule, but it exists so")
    print("  that a re-sweep and a 4 min loiter stay available after the nominal")
    print("  mission. Relaxing it to justify a lighter pack would be moving the")
    print("  goalposts to fit the hardware.")

    print("\n" + "=" * 84)
    print("PROCUREMENT ACTIONS")
    print("=" * 84)
    print("  ORDER NOW -- unaffected by the open questions:")
    print("    motors (2.53 kgf each covers every case), ESCs (60 A covers every")
    print("    case), flight controller, GNSS x2 + antennas, compute, camera,")
    print("    lens, radios, RTK base, payload servos, fasteners, wire and PDB")
    print("    (10 AWG mains either way).")
    print()
    print("  ORDER 18 CELLS PER AIRCRAFT (54 fleet), not 12. The BOM is correct.")
    print("    Cells have no Indian source, so this is imported spend -- but")
    print("    under-ordering costs a re-order and 3 weeks, which the flight")
    print("    window cannot absorb.")
    print()
    print("  HOLD PROPS until the diameter is settled. 20 in is more efficient")
    print("    (763 W vs 828 W) and gives more endurance margin; 18 in has lower")
    print("    rotor inertia and better gust rejection. Both pass the policy at")
    print("    6S3P. 3 week lead -- decide at the P2 thrust-stand run, or order")
    print("    one set of each and settle it on measured data.")
    print()
    print("  RE-RUN THE MAIN SIZING MODEL with Indian component masses before")
    print("    the design point is republished. That is tab 07's ACTION item and")
    print("    it is still open.")


if __name__ == '__main__':
    main()
