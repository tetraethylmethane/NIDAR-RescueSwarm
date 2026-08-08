"""Compute-bay thermal -- why the worst case is on the ground, props stopped.

SYS-53 requires forced-air cooling active from power-on. That is an unusual
requirement and it is worth showing why, because the instinct is to cool a
multirotor with propwash and save the fan.

The instinct fails in exactly the window that matters. During the 5-minute
setup the avionics are powered, the companion is booting and running, and the
props are STOPPED. There is no propwash, the aircraft is sitting on hot ground,
and nothing is moving air through the bay.

There is also a coupling the thermal analysis usually misses: the compute bay
heats the structure the camera is bolted to, and boresight drifts with
temperature. See boresight_budget.py -- 0.066 mm of bracket growth is a third
of the whole boresight allowance.

Run:  python tools/sizing-model/thermal_budget.py
"""
from __future__ import annotations

import math

W = 78

# Avionics load, from rescueswarm_sizing_model.py's P_avio breakdown.
LOADS_W = {
    "companion (Jetson class)": 15.0,
    "mesh radio": 8.0,
    "FC + GNSS": 5.0,
    "camera": 3.0,
}
COMPUTE_BAY_W = 15.0 + 3.0        # what actually sits in the sealed bay

# A plausible bay: 150 x 100 x 60 mm.
BAY = (0.150, 0.100, 0.060)
AMBIENT_C = 35.0                  # India, midday, on a hot apron
SETUP_S = 285.0                   # calibrated setup-to-launch, setup_budget.py

H_NATURAL = 7.0                   # W/m2K, still air, vertical-ish surfaces
H_FORCED = 30.0                   # W/m2K, modest fan-driven flow
CP_AIR = 1005.0                   # J/kg/K
RHO_AIR = 1.16                    # kg/m3 at 35 C

# Lumped thermal mass: board + heatsink + bay structure.
THERMAL_MASS_J_K = 180.0


def rule(t=""):
    print("=" * W)
    if t:
        print(t)
        print("=" * W)


def area_m2(b) -> float:
    x, y, z = b
    return 2 * (x * y + x * z + y * z)


A = area_m2(BAY)

rule("THE SEALED BAY -- what happens if you trust propwash")
print(f"  Bay {BAY[0]*1000:.0f} x {BAY[1]*1000:.0f} x {BAY[2]*1000:.0f} mm, "
      f"surface {A:.3f} m2, load {COMPUTE_BAY_W:.0f} W (companion + camera)")
print()
print(f"  {'condition':>26}{'h':>8}{'steady dT':>12}{'bay air':>10}")
for label, h in (("sealed, still air", H_NATURAL),
                 ("forced air, modest fan", H_FORCED)):
    dt = COMPUTE_BAY_W / (h * A)
    print(f"  {label:>26}{h:>7.0f} {dt:>10.1f} K{AMBIENT_C + dt:>9.1f} C")
print()
tau = THERMAL_MASS_J_K / (H_NATURAL * A)
dt_steady = COMPUTE_BAY_W / (H_NATURAL * A)
frac = 1 - math.exp(-SETUP_S / tau)
print(f"  Time constant, sealed: {tau:.0f} s. Over a {SETUP_S:.0f} s setup the bay")
print(f"  reaches {frac:.0%} of that steady rise = {frac * dt_steady:.0f} K, so about "
      f"{AMBIENT_C + frac * dt_steady:.0f} C of bay air")
print("  by launch -- BEFORE the mission starts, and before any propwash.")
print()
print("  That is bay AIR. Silicon junction sits above it. A companion that")
print("  throttles during the search is a detection-rate problem, and throttling")
print("  is exactly what this produces: it arrives late, under load, with no")
print("  obvious cause on the ground station.")

rule("THE FAN IS TRIVIALLY SMALL -- there is no reason not to fit it")
print("  Flow needed to carry the heat away at a given air temperature rise:")
print()
print(f"  {'air dT':>9}{'mass flow':>13}{'volume':>12}{'CFM':>8}")
for dt_air in (5.0, 10.0, 20.0):
    mdot = COMPUTE_BAY_W / (CP_AIR * dt_air)
    q = mdot / RHO_AIR
    print(f"  {dt_air:>7.0f} K{mdot * 1000:>11.2f} g/s{q * 1000:>10.2f} L/s"
          f"{q * 2118.9:>7.1f}")
print()
print("  A 40 mm fan moves several CFM on a fraction of a watt. The cooling")
print("  requirement is not hard; REMEMBERING TO POWER IT FROM THE MAIN BUS AT")
print("  POWER-ON is the requirement. A fan gated on arming, or on flight mode,")
print("  is off for the entire window this analysis is about.")

rule("THE COUPLING NOBODY MODELS -- compute heat moves the camera")
print("  boresight_budget.py budgets 0.153 deg (0.21 mm over an 80 mm spacing)")
print("  for boresight, and shows a 100 mm aluminium bracket growing 0.066 mm")
print("  over a 30 K swing -- a third of the allowance.")
print()
print("  That analysis assumed AMBIENT swing, dawn to midday. If the camera")
print("  bracket is bolted to, or shares structure with, the compute bay, it")
print("  also sees the bay's rise:")
print()
for label, h in (("sealed bay", H_NATURAL), ("fan-cooled bay", H_FORCED)):
    dt = COMPUTE_BAY_W / (h * A)
    growth_mm = 100.0 * (23e-6 - 1e-6) * dt
    ang = math.degrees(math.atan(growth_mm / 80.0))
    print(f"  {label:>16}: +{dt:4.1f} K at the bracket -> {growth_mm:.3f} mm -> "
          f"{ang:.3f} deg -> {60.0 * math.tan(math.radians(ang)):.2f} m at 60 m")
print()
print("  BE HONEST ABOUT THE SIZE OF THIS. 0.07 m added in quadrature to the")
print("  0.884 m case-C geotag gives 0.887 m. It is nearly nothing on its own,")
print("  and it does not justify contorting the layout.")
print()
print("  Two reasons it is still worth a line on the drawing. It is SYSTEMATIC,")
print("  so it stacks with the boresight residual rather than averaging out")
print("  across frames. And unlike the ambient swing it tracks COMPUTE LOAD, so")
print("  it moves when the detector starts working -- during the search, while")
print("  geotagging. Calibrating on a cold aircraft and flying a hot one is the")
print("  kind of error that shows up as an unexplained bias in P7 and costs")
print("  days to find.")
print()
print("  CAD consequence, and it is free at design time: do not bolt the camera")
print("  bracket to the compute bay. That is the whole ask -- not a heat pipe,")
print("  not an isolator, just do not share the structure.")

rule("THE BATTERY IS THE OPPOSITE PROBLEM")
print("  battery_failsafe.py puts pack I2R at 54 W in hover -- three times the")
print("  companion -- and an adiabatic 19.7 K over the 7.7 min mission.")
print()
print("  But on the ground at 55 W avionics draw the pack contributes almost")
print("  nothing, and in flight it has full propwash over it.")
print()
print("  So the two heat sources need opposite things:")
print("     compute  hot on the GROUND, needs a fan, props stopped")
print("     battery  hot in FLIGHT, has propwash, needs a path through it")
print()
print("  A single 'propwash cools everything' layout satisfies the battery and")
print("  fails the compute bay in the one window where the aircraft is powered")
print("  and stationary.")

rule("WHAT CAD HAS TO DELIVER")
print("  1. Fan powered from the main bus AT POWER-ON. Not on arming, not on")
print("     mode. SYS-53, and the reason is the setup window.")
print("  2. Inlet and outlet that stay clear when the aircraft is on the ground")
print("     and -- if arms fold -- when it is folded. A blocked duct fails in")
print("     the configuration it spends the setup window in.")
print("  3. Camera bracket thermally isolated from the compute bay.")
print("  4. Battery airflow path through propwash, separate from the compute")
print("     bay so a hot pack does not preheat the companion.")
print("  5. Filtration is a real trade in a flood zone: a filter that halves")
print("     the flow doubles the rise. Decide it deliberately rather than")
print("     discovering it -- and note that ingress protection is a real")
print("     requirement in standing water, not an optional nicety.")
rule()
