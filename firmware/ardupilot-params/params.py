"""ArduPilot parameters — four of the five failsafes, as configuration not code.

SYS-11 requires failsafes for low battery, C2 loss, geofence breach, mission
abort and RTH. Four of those five are ArduPilot parameters. Writing a custom
battery monitor on the companion would be slower, less tested, and would fail
exactly when the companion fails — which is one of the cases the failsafe exists
for.

Only **abort and recall** need building, and even those are configured here in
part: an RC channel mapped to RTL means the safety radio can recover the
aircraft **without the companion being alive**, which is constraint 3 of the
abort design (implementation-plan.md §4).

Generates one `.parm` per aircraft, because three values must differ:

    SYSID_THISMAV   1 / 2 / 3, so mavlink-router can tell them apart and the
                    GCS Fleet can key on the source system
    RTL_ALT         staggered, so three aircraft returning at once are not
                    coplanar
    FENCE_*         identical, but stated per aircraft so a file is complete

Run:  python firmware/ardupilot-params/params.py --out .
"""
from __future__ import annotations

import argparse

# 6S 21700 Li-ion, 13.5 Ah. Voltage thresholds are per-cell x 6.
CELLS = 6
PACK_MAH = 13500
LOW_V_PER_CELL = 3.40          # ~20 % SoC resting for 21700 NMC
CRT_V_PER_CELL = 3.20          # ~10 %; below this the cells are being damaged

# Pack internal resistance, ohms. BATT_FS_VOLTSRC = 1 below asks ArduPilot to
# reconstruct RESTING voltage as `measured + current * BATT_RESISTANCE`, which
# is the only way the per-cell thresholds above mean what they say -- they were
# read off a resting discharge curve.
#
# THIS WAS UNSET, AND UNSET MEANS ZERO. The sag compensation therefore did
# nothing, and the failsafe compared a LOADED voltage against a RESTING
# threshold. tools/sizing-model/battery_failsafe.py puts the consequence at
#
#     BATT_LOW_VOLT (RTL)             fired at ~53 % SoC, not 20 %
#     BATT_CRT_VOLT (land immediately) fired at ~30 % SoC, not 10 %
#
# An RTL at 53 % aborts the search mid-mission and destroys the 2.0x endurance
# reserve the entire pack sizing rests on.
#
# 0.040 ohm = 6 x (15 mOhm cell / 3 parallel) + 10 mOhm wiring, connectors and
# BMS shunt, at 50 % SoC and 25 C.
#
# ⚠ PREDICTED, NOT MEASURED. Bench-discharge the real pack with a current step
# and compute R = dV/dI before first flight; that measurement beats the model
# outright and takes an afternoon. This value exists because the alternative
# sitting in the firmware was 0, which is not a better estimate.
BATT_RESISTANCE = 0.040

# Base parameters, identical on every aircraft.
BASE: dict[str, float] = {
    # --- battery failsafe (SYS-11) -------------------------------------
    # Capacity-based is primary: a Li-ion discharge curve is flat, so voltage
    # alone is a poor state-of-charge estimate under varying load. Voltage is
    # kept as the backstop.
    "BATT_MONITOR": 4,                       # voltage and current
    "BATT_CAPACITY": PACK_MAH,
    "BATT_LOW_MAH": PACK_MAH * 0.20,         # land with 20 % — the DoD policy
    "BATT_CRT_MAH": PACK_MAH * 0.10,
    "BATT_LOW_VOLT": CELLS * LOW_V_PER_CELL,
    "BATT_CRT_VOLT": CELLS * CRT_V_PER_CELL,
    "BATT_FS_LOW_ACT": 2,                    # RTL
    "BATT_FS_CRT_ACT": 1,                    # Land immediately
    "BATT_FS_VOLTSRC": 1,                    # sag-compensated voltage
    "BATT_RESISTANCE": BATT_RESISTANCE,      # without this, VOLTSRC=1 is inert
    # Explicit rather than relying on the 10 s default: a delivery manoeuvre
    # pulls ~115 A for a second or two, and a transient must not be able to end
    # the mission on its own.
    "BATT_LOW_TIMER": 10,

    # --- geofence (SYS-09, rule 8.18, -20 per breach) -------------------
    "FENCE_ENABLE": 1,
    "FENCE_TYPE": 7,                         # max alt + circle + polygon
    "FENCE_ACTION": 1,                       # RTL
    "FENCE_ALT_MAX": 100,
    "FENCE_RADIUS": 600,                     # matches the 600 m link budget
    "FENCE_MARGIN": 10,                      # turn back BEFORE the line

    # --- GCS / C2 link loss (SYS-28, rule 8.19) -------------------------
    # 60 s, matching the architecture: continue the assigned bundle for 10 s of
    # mesh loss, return home at 60 s. Nothing requires the link to make
    # progress, so a short timeout would abort a mission that is fine.
    "FS_GCS_ENABLE": 1,
    "FS_GCS_TIMEOUT": 60,
    "FS_OPTIONS": 0,

    # --- RC failsafe: the safety pilot, not the mission ------------------
    "FS_THR_ENABLE": 1,
    "FS_THR_VALUE": 975,

    # --- RTH (SYS-11) ---------------------------------------------------
    "RTL_SPEED": 800,                        # cm/s
    "RTL_ALT_FINAL": 0,                      # land, do not hover
    "RTL_LOIT_TIME": 0,

    # --- ABORT AND RECALL, constraint 3: survive a dead companion --------
    # The 868 MHz safety receiver drives these channels directly into the
    # flight controller. If the companion has hung -- one of the reasons to
    # abort -- this path still works, because no software of ours is in it.
    "RC7_OPTION": 4,                         # RTL          <- recall
    "RC8_OPTION": 18,                        # Land         <- abort to ground
    "RC9_OPTION": 31,                        # Motor E-stop <- last resort

    # --- GNSS / RTK (SYS-12, SYS-42) ------------------------------------
    "GPS_TYPE": 1,
    "GPS_TYPE2": 1,
    "GPS_AUTO_SWITCH": 1,
    "GPS_INJECT_TO": 127,                    # RTCM to all GPS units
    "EK3_SRC1_POSXY": 3,                     # GPS
    "EK3_SRC1_VELXY": 3,

    # --- arming ----------------------------------------------------------
    "ARMING_CHECK": 1,                       # all checks; never ship with 0

    # --- mission behaviour ------------------------------------------------
    "WPNAV_SPEED": 800,                      # cm/s, the 8 m/s design sweep
    "WPNAV_RADIUS": 200,                     # cm
    "WP_YAW_BEHAVIOR": 0,                    # hold heading: the camera is fixed
}

REQUIRED_FAILSAFES = (
    "BATT_FS_LOW_ACT", "BATT_FS_CRT_ACT",
    "FENCE_ENABLE", "FENCE_ACTION",
    "FS_GCS_ENABLE",
    "RTL_ALT",
)


def for_drone(drone_id: int, rtl_alt_m: float = 25.0,
              rtl_stagger_m: float = 5.0) -> dict[str, float]:
    """Full parameter set for one aircraft."""
    if not 1 <= drone_id <= 250:
        raise ValueError("drone_id must be a valid MAVLink system id")
    p = dict(BASE)
    p["SYSID_THISMAV"] = drone_id
    # RTL_ALT is in CENTIMETRES. Setting 25 here means 25 cm, not 25 m, and the
    # aircraft would return home at ankle height.
    p["RTL_ALT"] = (rtl_alt_m + (drone_id - 1) * rtl_stagger_m) * 100
    return p


def to_parm(params: dict[str, float]) -> str:
    """ArduPilot .parm format: NAME,VALUE — one per line, sorted."""
    return "".join(f"{k},{v:g}\n" for k, v in sorted(params.items()))


def validate(params: dict[str, float]) -> list[str]:
    """Check the failsafes are present AND set to something safe."""
    problems = []
    for key in REQUIRED_FAILSAFES:
        if key not in params:
            problems.append(f"{key} missing — SYS-11 requires it")

    if params.get("ARMING_CHECK", 1) == 0:
        problems.append("ARMING_CHECK=0 disables every pre-arm check")
    if params.get("FENCE_ENABLE", 0) != 1:
        problems.append("FENCE_ENABLE must be 1 (rule 8.18, -20 per breach)")
    if params.get("FENCE_ACTION", 0) == 0:
        problems.append("FENCE_ACTION=0 reports the breach and does nothing")
    if params.get("BATT_FS_LOW_ACT", 0) == 0:
        problems.append("BATT_FS_LOW_ACT=0 means no action on low battery")
    if params.get("FS_GCS_ENABLE", 0) != 1:
        problems.append("FS_GCS_ENABLE must be 1 (rule 8.19 C2 loss)")

    rtl = params.get("RTL_ALT", 0)
    if rtl and rtl < 500:
        problems.append(
            f"RTL_ALT={rtl:g} — this parameter is in CENTIMETRES, so that is "
            f"{rtl/100:.1f} m. The aircraft would return home below head height."
        )
    if not any(params.get(f"RC{n}_OPTION") == 4 for n in range(5, 17)):
        problems.append(
            "no RC channel mapped to RTL (option 4) — the abort path would "
            "depend on the companion being alive"
        )
    fence_alt = params.get("FENCE_ALT_MAX", 0)
    if fence_alt and fence_alt <= 60:
        problems.append(
            f"FENCE_ALT_MAX={fence_alt:g} m is at or below the search altitude"
        )

    # Sag compensation without a resistance is not sag compensation.
    #
    # BATT_FS_VOLTSRC=1 asks ArduPilot to reconstruct resting voltage from
    # `measured + current * BATT_RESISTANCE`. With the resistance at its 0
    # default the reconstruction is a no-op, and BATT_LOW_VOLT -- picked off a
    # RESTING discharge curve -- gets compared against a LOADED voltage. It
    # fired at ~53 % SoC instead of 20 %, which is an RTL in the middle of the
    # search. This shipped, and only turned up when someone read the params
    # against the pack model.
    if params.get("BATT_FS_VOLTSRC", 0) == 1 and not params.get("BATT_RESISTANCE", 0):
        problems.append(
            "BATT_FS_VOLTSRC=1 (sag-compensated) with BATT_RESISTANCE unset or "
            "zero — the compensation does nothing, so BATT_LOW_VOLT is compared "
            "against loaded voltage and fires roughly 30 points of SoC early. "
            "Set BATT_RESISTANCE, or set BATT_FS_VOLTSRC=0 and move the "
            "thresholds onto the loaded curve. See "
            "tools/sizing-model/battery_failsafe.py."
        )

    # The two corrections are alternatives; applying both pushes the failsafe
    # dangerously late, which is the worse mistake.
    if params.get("BATT_RESISTANCE", 0) and params.get("BATT_FS_VOLTSRC", 0) == 1:
        low_v = params.get("BATT_LOW_VOLT", 0)
        if low_v and low_v < 3.30 * CELLS:
            problems.append(
                f"BATT_LOW_VOLT={low_v:g} is on the LOADED curve while "
                f"BATT_RESISTANCE is set and VOLTSRC=1, which already corrects "
                f"for sag. The correction is applied twice and the failsafe "
                f"fires far too late."
            )

    # Coulomb counting is the one failsafe that is independent of resistance,
    # temperature and load. It must not be weakened to paper over a voltage
    # threshold.
    cap = params.get("BATT_CAPACITY", 0)
    low_mah = params.get("BATT_LOW_MAH", 0)
    if cap and low_mah and low_mah < 0.15 * cap:
        problems.append(
            f"BATT_LOW_MAH={low_mah:g} is below 15 % of {cap:g} mAh — the "
            f"capacity failsafe is the backstop for a wrong voltage estimate "
            f"and the DoD policy is 20 %"
        )
    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drones", type=int, default=3)
    ap.add_argument("--out", default=".")
    args = ap.parse_args()
    import os

    for i in range(1, args.drones + 1):
        p = for_drone(i)
        bad = validate(p)
        if bad:
            raise SystemExit("refusing to write invalid parameters:\n  " +
                             "\n  ".join(bad))
        path = os.path.join(args.out, f"rescueswarm-drone{i}.parm")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(to_parm(p))
        print(f"wrote {path}  (SYSID {i}, RTL_ALT {p['RTL_ALT']/100:.0f} m)")


if __name__ == "__main__":
    main()
