"""Boresight and lever arm -- turning an error budget into a mount tolerance.

SYS-48 says boresight and lever-arm calibration must be complete before any
accuracy claim. That is a process requirement. This is the mechanical one that
follows from it, and it is the number CAD actually needs: **how much movement
in the camera mount is too much**.

The geotag stack (sizing-calculations.md section 11) budgets:

    boresight residual (systematic)   0.31 m  ->  0.21 m  ->  0.16 m   A/B/C
    GNSS-camera lever arm (systematic)                       0.10 m
    attitude                          0.23 m  ->  0.07 m  ->  0.07 m

Systematic terms are the ones multi-frame fusion CANNOT reduce. Twenty frames
divide the GNSS noise by 4.5; they divide a misaligned camera by one.

Run:  python tools/sizing-model/boresight_budget.py
"""
from __future__ import annotations

import math

W = 78
ALT_SEARCH_M = 60.0        # selected; 40 m under review
ALT_ALT_M = 40.0
BORESIGHT_BUDGET_M = 0.16  # case C allocation
GEOTAG_C_TERMS = {         # case C, sizing-calculations.md section 11
    "unmodelled": 0.70,
    "target extent / centroid": 0.50,
    "boresight residual": 0.16,
    "GNSS-camera lever arm": 0.10,
    "attitude": 0.07,
    "pixel centroid": 0.02,
}


def rule(t=""):
    print("=" * W)
    if t:
        print(t)
        print("=" * W)


def ground_error_m(angle_deg: float, alt_m: float) -> float:
    return alt_m * math.tan(math.radians(angle_deg))


def angle_for_error_deg(err_m: float, alt_m: float) -> float:
    return math.degrees(math.atan(err_m / alt_m))


def rss(vals) -> float:
    return math.sqrt(sum(v * v for v in vals))


rule("HOW MUCH BORESIGHT ERROR IS THE BUDGET BUYING?")
tol60 = angle_for_error_deg(BORESIGHT_BUDGET_M, ALT_SEARCH_M)
tol40 = angle_for_error_deg(BORESIGHT_BUDGET_M, ALT_ALT_M)
print(f"  The 0.16 m case-C allocation corresponds to:")
print(f"     {tol60:.3f} deg at {ALT_SEARCH_M:.0f} m AGL   ({tol60 * 17.45:.2f} mrad)")
print(f"     {tol40:.3f} deg at {ALT_ALT_M:.0f} m AGL   ({tol40 * 17.45:.2f} mrad)")
print()
print(f"  {'angle':>9}{'@40 m':>10}{'@60 m':>10}   note")
for a in (0.05, 0.10, 0.15, 0.25, 0.50, 1.00, 2.00):
    note = ""
    if abs(a - 0.15) < 1e-9:
        note = "the budgeted allocation at 60 m"
    if abs(a - 1.00) < 1e-9:
        note = "a mount that shifted, or a skipped calibration"
    print(f"  {a:>8.2f}d{ground_error_m(a, 40):>9.2f}m{ground_error_m(a, 60):>9.2f}m   {note}")

rule("BUT CHECK ITS LEVERAGE BEFORE SPENDING MONEY ON IT")
base = rss(GEOTAG_C_TERMS.values())
print(f"  Case C geotag RSS with every term at budget: {base:.3f} m")
print()
print(f"  {'term':>26}{'value':>8}{'share of variance':>20}")
for k, v in sorted(GEOTAG_C_TERMS.items(), key=lambda kv: -kv[1]):
    print(f"  {k:>26}{v:>7.2f}m{v * v / base ** 2:>19.1%}")
print()
print("  Boresight at budget is a SMALL term -- a few percent of variance. The")
print("  0.70 m unmodelled allowance and the 0.50 m target-extent term dominate")
print("  case C between them.")
print()
for mult, label in ((2.0, "boresight doubles to 0.32 m"),
                    (4.0, "boresight quadruples to 0.64 m"),
                    (6.6, "boresight becomes 1.05 m = 1 deg at 60 m")):
    t = dict(GEOTAG_C_TERMS)
    t["boresight residual"] = BORESIGHT_BUDGET_M * mult
    print(f"  {label:<42} geotag {rss(t.values()):.2f} m  "
          f"(+{rss(t.values()) - base:.2f} m)")
print()
print("  THE POINT IS NOT OPTIMISATION, IT IS FAILURE MODE.")
print("  Tightening boresight below its 0.16 m allocation buys almost nothing.")
print("  Letting it go to a degree -- one shifted mount, one skipped")
print("  calibration -- makes it the largest single term in the stack and")
print("  costs about 0.5 m of geotag, silently, with nothing on the screen to")
print("  say so. Design the mount to HOLD calibration, not to be precise.")

rule("WHAT THAT MEANS IN MILLIMETRES")
print("  A mount rotates when one side moves relative to the other. Over a")
print("  fastener spacing L, an angular error a needs a differential of")
print("  L * tan(a):")
print()
print(f"  {'spacing':>9}{'0.15 deg':>12}{'0.50 deg':>12}{'1.0 deg':>11}")
for L in (40.0, 60.0, 80.0, 120.0):
    print(f"  {L:>7.0f}mm"
          f"{L * math.tan(math.radians(0.15)):>11.3f}mm"
          f"{L * math.tan(math.radians(0.50)):>11.3f}mm"
          f"{L * math.tan(math.radians(1.00)):>10.3f}mm")
print()
print("  Read the 0.15 deg column. On an 80 mm fastener spacing the budget is")
print("  0.21 mm of differential movement -- TOTAL, for the life of the")
print("  airframe, through transport, vibration and every landing.")
print()
print("  A clearance-hole bolted joint does not hold 0.2 mm. Standard M3")
print("  clearance is 0.2-0.4 mm of radial slop on its own, and it only takes")
print("  one hard landing to take it up. That is the argument for dowel pins")
print("  or a bonded joint, and it is a number rather than a preference.")

rule("THERMAL -- the one nobody checks")
print("  Carbon fibre is ~1 ppm/K. Aluminium is ~23 ppm/K. An aluminium camera")
print("  bracket bolted flat to a CF plate is a bimetallic strip.")
print()
print(f"  {'bracket':>9}{'dT':>6}{'differential':>14}{'as angle over 80 mm':>22}")
for L in (60.0, 100.0):
    for dT in (15.0, 30.0):
        diff = L * (23e-6 - 1e-6) * dT
        ang = math.degrees(math.atan(diff / 80.0))
        print(f"  {L:>7.0f}mm{dT:>5.0f}K{diff:>13.3f}mm{ang:>21.3f}d")
print()
print("  A 100 mm aluminium bracket over a 30 K day-night swing moves 0.066 mm,")
print("  which is a third of the whole 0.15 deg allowance if it turns into")
print("  rotation. It will not all become rotation in a well-designed joint --")
print("  but it will in an over-constrained one.")
print()
print("  Calibrate at the temperature you fly at, or make the bracket CF, or")
print("  constrain it kinematically so growth translates instead of rotating.")

rule("LEVER ARM -- cheap, so just do it properly")
print("  The GNSS-camera lever arm is budgeted at 0.10 m and is systematic.")
t = dict(GEOTAG_C_TERMS)
t["GNSS-camera lever arm"] = 0.01
print(f"  Measured to 1 cm instead: geotag {rss(t.values()):.3f} m against "
      f"{base:.3f} m")
print()
print("  Worth 0.005 m. Almost nothing -- and that is the useful finding,")
print("  because it means the lever arm does NOT justify design compromises.")
print("  What it does justify is a MEASURABLE DATUM: a defined feature you can")
print("  put callipers on between the antenna phase centre and the camera")
print("  mounting face. The cost of that is one dimension on a drawing, and")
print("  without it the 0.10 m is a guess rather than a budget line.")

rule("WHAT CAD HAS TO DELIVER")
print("  1. Camera, IMU and both GNSS antenna mounts on ONE rigid core. No")
print("     folding joint anywhere in that load path -- a fold re-datums the")
print("     lever arm on every unpack and invalidates SYS-48.")
print("  2. Camera located by DOWELS or bonded, not by bolt friction. Budget")
print("     is 0.21 mm of differential over an 80 mm spacing, for life.")
print("  3. A measurable datum between antenna phase centre and camera face.")
print("  4. Kinematic or CF bracket so thermal growth translates, not rotates.")
print("  5. A calibration target arrangement that can be re-flown in the field,")
print("     because the honest assumption is that boresight WILL move and the")
print("     question is whether anyone finds out.")
rule()
