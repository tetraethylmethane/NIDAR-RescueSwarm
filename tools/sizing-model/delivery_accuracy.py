"""Delivery accuracy budget against the NIDAR scoring zones.

The rulebook scores each kit drop by its distance from the survivor:

    Zone A  <= 1 m   20 points
    Zone B  <= 2 m   14 points
    Zone C  <= 3 m    8 points
    beyond            0 points

Ten drops are therefore worth 200 points, and the difference between hitting
Zone A and Zone C is 120 points -- more than twice the fast-completion bonus.

The kit is scored from the SURVIVOR, not from the tag, so a drop can be no more
accurate than the tag it was aimed at. The geotag error and the release
dispersion compound. This script builds the combined budget and converts it
into expected points, so the requirement can be set from the scoring rather
than from a round number.

STATISTICS. The sizing document quotes geotag error as an RSS 1-sigma over two
axes. For a circular Gaussian with that convention, sigma per axis is RSS/sqrt2
and the radial miss is Rayleigh distributed, giving the clean form

    P(r <= R) = 1 - exp(-(R/E)^2)          E = total 2-axis RSS

which reproduces the document's CEP50 = 0.8326 * RSS. Verified in main().

Run:  python tools/sizing-model/delivery_accuracy.py
"""
import contextlib
import io
import os

import numpy as np

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'rescueswarm_sizing_model.py')
G = {'__name__': '__delivery__'}
with open(MODEL, encoding='utf-8') as f:
    src = f.read()
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src, MODEL, 'exec'), G)

drop = G['drop']            # ballistic integrator, reused as-is
h_drop = G['h_drop']        # 6 m release altitude

ZONES = [(1.0, 20), (2.0, 14), (3.0, 8)]
N_DROPS = 10

# Geotag RSS (2-axis, 1 sigma) from sizing-calculations.md section 11.
GEOTAG = {
    'A  no RTK, single frame':      3.06,
    'B  RTK, single frame':         1.30,
    'C  RTK + fusion + calibrated': 0.91,
}


def p_within(R, E):
    """Rayleigh CDF for a 2-axis RSS of E."""
    return 1.0 - np.exp(-(R / E) ** 2)


def expected_points(E):
    """Expected score for one drop at total 2-axis RSS error E."""
    pts, prev = 0.0, 0.0
    for R, v in ZONES:
        p = p_within(R, E)
        pts += v * (p - prev)
        prev = p
    return pts


def budget(geotag, v_res, wind, wind_comp, nav=0.20, kit=0.15):
    """Total delivery RSS from its contributors.

    geotag     tag-to-survivor error (2-axis RSS)
    v_res      residual groundspeed at release, m/s
    wind       steady wind, m/s
    wind_comp  fraction of wind drift removed by aiming upwind (0..1)
    nav        aircraft position error at release, m
    kit        kit aero variability / tumble scatter, m
    """
    release, _ = drop(h_drop, v_res, 0.0)          # miss from residual velocity
    drift, _ = drop(h_drop, 0.0, wind)             # miss from wind on the kit
    drift_resid = drift * (1.0 - wind_comp)
    terms = dict(geotag=geotag, nav=nav, release=release,
                 wind=drift_resid, kit=kit)
    total = np.sqrt(sum(v ** 2 for v in terms.values()))
    return total, terms


def main():
    # --- sanity: reproduce the sizing document's CEP50 convention ----------
    e = 3.06
    cep = e * np.sqrt(np.log(2))
    print("=" * 88)
    print("DELIVERY ACCURACY vs THE NIDAR SCORING ZONES")
    print("=" * 88)
    print(f"  Convention check: RSS {e:.2f} m -> CEP50 {cep:.2f} m "
          f"(sizing doc section 11 says 2.54 m)\n")

    print("  Zone A <=1 m = 20 pts | Zone B <=2 m = 14 | Zone C <=3 m = 8 | "
          f"{N_DROPS} drops = 200 max\n")

    # --- what total error buys what score ---------------------------------
    print("-" * 88)
    print("SECTION 1  Expected points vs total delivery error")
    print("-" * 88)
    print(f"{'total RSS':>10}{'CEP50':>8}{'P(<=1m)':>9}{'P(<=2m)':>9}"
          f"{'P(<=3m)':>9}{'pts/drop':>10}{'10 drops':>10}")
    print('-' * 88)
    for E in [0.5, 0.7, 0.9, 1.1, 1.3, 1.6, 2.0, 2.5, 3.0, 3.5]:
        print(f"{E:10.2f}{E*np.sqrt(np.log(2)):8.2f}"
              f"{p_within(1, E):9.2f}{p_within(2, E):9.2f}{p_within(3, E):9.2f}"
              f"{expected_points(E):10.1f}{N_DROPS*expected_points(E):10.0f}")
    print()
    print("  Diminishing returns set in below ~0.7 m; the steep part of the")
    print("  curve is between 2.5 m and 1.0 m. That is where the points are.")

    # --- the actual budget, by geotag case and wind -----------------------
    print("\n" + "-" * 88)
    print("SECTION 2  Combined budget: geotag + nav + release + wind + kit")
    print("-" * 88)
    print("  Release gate 0.30 m/s residual groundspeed, 6 m release, "
          "nav 0.20 m, kit 0.15 m\n")
    print(f"{'geotag case':<32}{'wind':>7}{'comp':>7}{'total':>8}"
          f"{'pts/drop':>10}{'10 drops':>10}")
    print('-' * 88)
    for name, gt in GEOTAG.items():
        for wind, comp in [(0, 0.0), (3, 0.0), (6, 0.0), (3, 0.7), (6, 0.7)]:
            tot, _ = budget(gt, 0.30, wind, comp)
            print(f"{name:<32}{wind:6.0f}m{comp:7.0%}{tot:8.2f}"
                  f"{expected_points(tot):10.1f}{N_DROPS*expected_points(tot):10.0f}")
        print()

    # --- where the error comes from ---------------------------------------
    print("-" * 88)
    print("SECTION 3  Contribution breakdown (RTK + fusion, 3 m/s wind)")
    print("-" * 88)
    for comp in (0.0, 0.7):
        tot, terms = budget(GEOTAG['C  RTK + fusion + calibrated'], 0.30, 3, comp)
        print(f"\n  Wind compensation {comp:.0%}  ->  total {tot:.2f} m")
        for k, v in sorted(terms.items(), key=lambda kv: -kv[1]):
            print(f"    {k:<10}{v:6.2f} m   {100*v**2/tot**2:5.1f}% of variance")

    # --- sensitivity to the release gate ----------------------------------
    print("\n" + "-" * 88)
    print("SECTION 4  Release-gate sensitivity (RTK + fusion, 3 m/s, 70% comp)")
    print("-" * 88)
    print(f"{'v_residual':>11}{'release miss':>14}{'total':>8}{'pts/drop':>10}")
    print('-' * 88)
    gt = GEOTAG['C  RTK + fusion + calibrated']
    for v in [0.10, 0.20, 0.30, 0.50, 0.75, 1.00]:
        tot, terms = budget(gt, v, 3, 0.7)
        print(f"{v:10.2f}m{terms['release']:13.2f}m{tot:8.2f}"
              f"{expected_points(tot):10.1f}")
    print()
    print("  Tightening the gate below ~0.3 m/s buys little once geotag")
    print("  dominates. Fix geolocation first, then the release gate.")

    # --- survivor datum ambiguity -----------------------------------------
    print("\n" + "-" * 88)
    print("SECTION 5  SURVIVOR-DATUM OFFSET  (delivery is measured from the survivor)")
    print("-" * 88)
    print("  Confirmed: drops are scored from the SURVIVOR, so geotag error and")
    print("  release dispersion compound -- as budgeted above. But a prone adult is")
    print("  ~1.7 m long, so 'the survivor's position' is ambiguous by up to 0.85 m")
    print("  depending on whether the datum is a marked point, the torso centre or")
    print("  the nearest body part. That is comparable to the whole Zone A radius.")
    print()
    print("  A datum offset is a BIAS, not noise: it shifts the whole distribution")
    print("  and multi-frame fusion cannot remove it.\n")
    gt = GEOTAG['C  RTK + fusion + calibrated']
    base, _ = budget(gt, 0.30, 3, 0.7)
    print(f"{'datum bias':>11}{'P(<=1m)':>10}{'P(<=2m)':>10}{'pts/drop':>10}"
          f"{'10 drops':>10}{'vs zero':>9}")
    print('-' * 88)
    ref = None
    for bias in [0.0, 0.25, 0.50, 0.85]:
        # offset Rice distribution, evaluated by quadrature over the 2-D Gaussian
        s = base / np.sqrt(2)
        n = 400
        xs = np.linspace(-5 * s + bias, 5 * s + bias, n)
        ys = np.linspace(-5 * s, 5 * s, n)
        X, Y = np.meshgrid(xs, ys)
        w = np.exp(-((X - bias) ** 2 + Y ** 2) / (2 * s ** 2))
        w /= w.sum()
        r = np.hypot(X, Y)
        p1, p2, p3 = (w[r <= R].sum() for R in (1.0, 2.0, 3.0))
        pts = 20 * p1 + 14 * (p2 - p1) + 8 * (p3 - p2)
        if ref is None:
            ref = pts
        print(f"{bias:10.2f}m{p1:10.2f}{p2:10.2f}{pts:10.1f}"
              f"{N_DROPS*pts:10.0f}{N_DROPS*(pts-ref):+9.0f}")
    print()
    print("  A worst-case 0.85 m datum bias costs ~18 points -- less than RTK (82)")
    print("  but comparable to fusion plus ground-plane calibration (20), and it is")
    print("  free to remove. Ask which point is scored, then bias the detector")
    print("  centroid toward it.")

    # --- requirement derivation -------------------------------------------
    print("\n" + "=" * 88)
    print("SECTION 6  REQUIREMENT DERIVATION")
    print("=" * 88)
    tgt = 0.90
    lo, hi = 0.05, 5.0
    for _ in range(200):                      # bisect for the geotag budget
        mid = 0.5 * (lo + hi)
        t, _ = budget(mid, 0.30, 3, 0.7)
        if expected_points(t) < 14.0:         # >= Zone B value in expectation
            hi = mid
        else:
            lo = mid
    print(f"  For an expected 14 pts/drop (Zone B value) in 3 m/s wind with 70%")
    print(f"  wind compensation, the geotag budget must be <= {lo:.2f} m RSS.")
    tot_c, _ = budget(GEOTAG['C  RTK + fusion + calibrated'], 0.30, 3, 0.7)
    print(f"  Case C (RTK + fusion + calibrated ground plane) gives {tot_c:.2f} m")
    print(f"  total -> {expected_points(tot_c):.1f} pts/drop, "
          f"{N_DROPS*expected_points(tot_c):.0f} of 200.")
    tot_b, _ = budget(GEOTAG['B  RTK, single frame'], 0.30, 3, 0.7)
    tot_a, _ = budget(GEOTAG['A  no RTK, single frame'], 0.30, 3, 0.7)
    print(f"  Case B (RTK, no fusion)  {tot_b:.2f} m -> "
          f"{N_DROPS*expected_points(tot_b):.0f} of 200.")
    print(f"  Case A (no RTK)          {tot_a:.2f} m -> "
          f"{N_DROPS*expected_points(tot_a):.0f} of 200.")
    print()
    print(f"  RTK is worth {N_DROPS*(expected_points(tot_b)-expected_points(tot_a)):.0f} "
          f"points on delivery alone, before its effect on the 250-point")
    print("  detection-and-geotag score. Multi-frame fusion and ground-plane")
    print(f"  calibration add a further "
          f"{N_DROPS*(expected_points(tot_c)-expected_points(tot_b)):.0f} points.")
    print()
    print("  PROPOSED REQUIREMENTS")
    print("    SYS-12  Geotag CEP50 <= 0.75 m with RTK (0.91 m RSS), verified")
    print("            against surveyed ground truth.")
    print("    SYS-15  >= 60% of drops within 2.0 m and >= 30% within 1.0 m of")
    print("            the survivor, over >= 30 drops in <= 3 m/s wind.")
    print("    SYS-31  Release gated at <= 0.30 m/s residual groundspeed.")
    print("    SYS-32  Wind-compensated release aim point, >= 70% of estimated")
    print("            drift removed.")


if __name__ == '__main__':
    main()
