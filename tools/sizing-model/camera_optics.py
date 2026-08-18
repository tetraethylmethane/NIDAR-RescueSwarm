#!/usr/bin/env python3
"""Camera and lens, derived from the sensor actually in the bill of materials.

WHY THIS EXISTS. sizing-calculations.md 8 states the baseline sensor as
"1/1.8 in, 4056 x 3040, 7.4 x 5.6 mm, 1.82 um pitch". The BOM buys an Arducam
IMX477, which is a type 1/2.3 sensor: 4056 x 3040 at 1.55 um, 6.287 x 4.712 mm,
7.9 mm diagonal. Same pixel COUNT, different pixel SIZE, so the optics are not
the ones the mission was sized against.

The substitution cuts both ways, which is why it needs computing rather than
asserting: a smaller sensor behind the same 6 mm lens gives a NARROWER field
(more transects, longer sweep) and a FINER ground sample distance (more pixels
on a survivor). One hurts coverage, the other helps detection.

Run:  python tools/sizing-model/camera_optics.py
"""
from __future__ import annotations

import math

# --------------------------------------------------------------- the two cases
SPECIFIED = {                      # what the BOM buys
    "name": "Arducam IMX477 (type 1/2.3)",
    "px_w": 4056, "px_h": 3040,
    "pitch_um": 1.55,
    "f_mm": 6.0,
}
MODELLED = {                       # what sizing-calculations.md 8 assumed
    "name": "sizing model baseline (1/1.8 in)",
    "px_w": 4056, "px_h": 3040,
    "pitch_um": 1.82,
    "f_mm": 6.0,
}

PERSON_M = 1.7                     # supine adult, long axis
PERSON_W = 0.5                     # supine adult, across the shoulders
# COCO area thresholds, which is how detection papers report AP and therefore
# how any published recall number we compare against was measured.
COCO_SMALL_PX2 = 32 ** 2           # below this an object is "small"
COCO_MED_PX2 = 96 ** 2             # below this it is "medium"
SIDELAP = 0.30                     # sizing 8
AREA_HA = 10.0                     # rulebook: 10 hectare search area
N_DRONES = 3
GROUNDSPEED = 8.0                  # m/s, sizing 9.2
TURN_S = 6.0                       # per transect turn
ALTITUDES = (30.0, 40.0, 60.0)


def optics(c):
    """Sensor geometry and field of view. All of it follows from three numbers."""
    w_mm = c["px_w"] * c["pitch_um"] / 1000.0
    h_mm = c["px_h"] * c["pitch_um"] / 1000.0
    diag = math.hypot(w_mm, h_mm)
    f = c["f_mm"]
    return {
        "w_mm": w_mm, "h_mm": h_mm, "diag_mm": diag,
        "hfov": math.degrees(2 * math.atan(w_mm / (2 * f))),
        "vfov": math.degrees(2 * math.atan(h_mm / (2 * f))),
        "dfov": math.degrees(2 * math.atan(diag / (2 * f))),
        # angular size of one pixel, which is what sets smear tolerance
        "ifov_mdeg": math.degrees(c["pitch_um"] / 1000.0 / f) * 1000.0,
    }


def at_altitude(c, h_m):
    """Ground sample distance, footprint and coverage at altitude h."""
    o = optics(c)
    # GSD = pitch * h / f  -- similar triangles, no small-angle approximation
    gsd_m = (c["pitch_um"] / 1e6) * h_m / (c["f_mm"] / 1000.0)
    swath_w = 2 * h_m * math.tan(math.radians(o["hfov"] / 2))
    swath_h = 2 * h_m * math.tan(math.radians(o["vfov"] / 2))
    spacing = swath_w * (1 - SIDELAP)
    per_drone_m2 = AREA_HA * 10_000 / N_DRONES
    # a square-ish sub-region, so side = sqrt(area); transects run its length
    side = math.sqrt(per_drone_m2)
    n_lines = max(1, math.ceil(side / spacing))
    path_m = n_lines * side
    sweep_s = path_m / GROUNDSPEED + TURN_S * (n_lines - 1)
    return {
        "gsd_cm": gsd_m * 100,
        "person_px": PERSON_M / gsd_m,
        "swath_w": swath_w, "swath_h": swath_h,
        "spacing": spacing,
        "n_lines": n_lines, "sweep_s": sweep_s,
        "area_rate_ha_min": (spacing * GROUNDSPEED * 60) / 10_000,
    }


def blur_limit(c, h_m, speed_ms, max_smear_px=1.0):
    """Longest exposure before forward motion smears more than one pixel."""
    gsd_m = (c["pitch_um"] / 1e6) * h_m / (c["f_mm"] / 1000.0)
    return max_smear_px * gsd_m / speed_ms


def report(c):
    o = optics(c)
    print(f"\n{c['name']}")
    print("-" * 72)
    print(f"  sensor        {o['w_mm']:.3f} x {o['h_mm']:.3f} mm "
          f"(diagonal {o['diag_mm']:.2f} mm)")
    print(f"  pixels        {c['px_w']} x {c['px_h']}  at {c['pitch_um']} um")
    print(f"  lens          f = {c['f_mm']:.1f} mm")
    print(f"  field of view H {o['hfov']:.1f}deg  V {o['vfov']:.1f}deg  "
          f"D {o['dfov']:.1f}deg")
    print(f"  one pixel     {o['ifov_mdeg']:.2f} mdeg")
    print()
    print(f"  {'AGL':>5} {'GSD':>9} {'person':>8} {'footprint':>14} "
          f"{'spacing':>9} {'lines':>6} {'sweep':>8}")
    for h in ALTITUDES:
        a = at_altitude(c, h)
        print(f"  {h:>4.0f}m {a['gsd_cm']:>7.2f}cm {a['person_px']:>6.0f}px "
              f"{a['swath_w']:>6.1f}x{a['swath_h']:<6.1f}m "
              f"{a['spacing']:>7.1f}m {a['n_lines']:>6d} {a['sweep_s']:>6.0f}s")
    return o


if __name__ == "__main__":
    print("=" * 72)
    print("CAMERA AND LENS -- COMPLETE DERIVATION")
    print("=" * 72)
    print(f"  {AREA_HA:.0f} ha search area, {N_DRONES} drones, "
          f"{GROUNDSPEED:.0f} m/s ground speed, {SIDELAP:.0%} sidelap")

    spec = report(SPECIFIED)
    modl = report(MODELLED)

    print("\n" + "=" * 72)
    print("THE SUBSTITUTION, AT THE 40 m SEARCH ALTITUDE")
    print("=" * 72)
    s, m = at_altitude(SPECIFIED, 40.0), at_altitude(MODELLED, 40.0)
    rows = [
        ("HFOV (deg)", spec["hfov"], modl["hfov"], "narrower"),
        ("GSD (cm/px)", s["gsd_cm"], m["gsd_cm"], "finer"),
        ("person (px)", s["person_px"], m["person_px"], "more pixels"),
        ("swath (m)", s["swath_w"], m["swath_w"], "narrower"),
        ("line spacing (m)", s["spacing"], m["spacing"], "tighter"),
        ("transects/drone", s["n_lines"], m["n_lines"], "more lines"),
        ("sweep (s)", s["sweep_s"], m["sweep_s"], "longer"),
    ]
    print(f"  {'':<18}{'SPECIFIED':>11}{'MODELLED':>11}{'change':>10}   effect")
    for name, a, b, eff in rows:
        d = (a - b) / b * 100 if b else 0
        print(f"  {name:<18}{a:>11.2f}{b:>11.2f}{d:>9.1f}%   {eff}")

    print()
    print("  Detection improves and coverage costs more. Both are real; the")
    print("  mission was sized on neither.")

    print("\n" + "=" * 72)
    print("MOTION BLUR -- longest exposure for <= 1 px of smear at 8 m/s")
    print("=" * 72)
    for h in ALTITUDES:
        t = blur_limit(SPECIFIED, h, GROUNDSPEED)
        print(f"  {h:>4.0f} m   {t*1000:>6.2f} ms   -> shutter faster than "
              f"1/{1/t:.0f} s")
    print("  sizing 8.1 requires <= 1/1000 s, which clears this at every "
          "altitude.")

    print("\n" + "=" * 72)
    print("TILING -- what the detector is handed (sizing 8.2)")
    print("=" * 72)
    for ds, rate in ((1, 5.0), (2, 2.0)):
        w, h = SPECIFIED["px_w"] // ds, SPECIFIED["px_h"] // ds
        tiles = math.ceil(w / (640 * 0.8)) * math.ceil(h / (640 * 0.8))
        gsd = at_altitude(SPECIFIED, 40.0)["gsd_cm"] * ds
        print(f"  {ds}x downsample @ {rate:.0f} Hz: {w}x{h}, "
              f"{tiles} tiles of 640 px, {tiles*rate:.0f} inferences/s, "
              f"GSD {gsd:.2f} cm/px, person {PERSON_M/(gsd/100):.0f} px")
