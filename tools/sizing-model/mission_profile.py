"""Mission profile: search altitude, geotag error structure, and downlink budget.

Three questions the scoring structure forces open:

1. What search altitude? Speed is worth 50 points and is already won at 7.7 min
   against a 15 min bonus threshold, while detection is worth 250. Altitude
   should therefore be set by recall, spending the surplus time.

2. Does lowering altitude actually improve geotagging? Section 2 shows the
   answer is PARTLY, and corrects an error in an earlier revision of
   configuration-trade.md. The dominant ground-height term does NOT fall with
   altitude -- see below.

3. Rule 8.14 requires a live camera feed from EACH drone, not one switched
   feed. Section 3 re-runs the downlink budget for three concurrent streams.

NOTE ON CAMERA GEOMETRY. The main model is internally inconsistent: the sweep
planner uses a hardcoded HFOV of 70 deg while the camera section derives 63.3
deg from the sensor and lens. This script uses the sensor-derived value
throughout. At 60 m the two happen to give the same line count, so the
committed numbers are unaffected -- but the inconsistency is a latent bug if
altitude changes.

Run:  python tools/sizing-model/mission_profile.py
"""
import contextlib
import io
import os

import numpy as np

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'rescueswarm_sizing_model.py')
G = {'__name__': '__profile__'}
with open(MODEL, encoding='utf-8') as f:
    src = f.read()
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src, MODEL, 'exec'), G)

# --- camera, derived from the sensor (NOT the hardcoded 70 deg) -------------
SENSOR_W, PX_W, F_MM = 7.4, 4056, 6.0
HFOV = 2 * np.arctan(SENSOR_W / (2 * F_MM))
PERSON_M = 1.70

# --- mission constants ------------------------------------------------------
SIDELAP = 0.30
AREA_W, AREA_L = 250.0, 400.0        # 10 ha
N_DRONES = 3
V_SEARCH, V_TRANSIT = 8.0, 12.0
V_CLIMB, V_DESC = 3.0, 2.5
H_DROP, H_TRANSIT = 6.0, 40.0
N_DEL = 10 / 3
BONUS_S = 15 * 60                     # fast-completion threshold
LIMIT_S = 30 * 60


def sweep(h):
    W = 2 * h * np.tan(HFOV / 2)
    S = W * (1 - SIDELAP)
    n_lines = np.ceil(AREA_W / S)
    L_per = n_lines * AREA_L / N_DRONES
    t = L_per / V_SEARCH + (n_lines / N_DRONES) * 6.0
    gsd = W / PX_W
    return dict(W=W, n_lines=n_lines, t=t, gsd=gsd, px=PERSON_M / gsd)


def mission_time(h, v_desc=V_DESC):
    s = sweep(h)
    per_del = (150 / V_TRANSIT + (h - H_DROP) / v_desc + 8 + 2
               + (H_TRANSIT - H_DROP) / V_CLIMB)
    return (45 + h / V_CLIMB + 120 / V_TRANSIT + s['t']
            + N_DEL * per_del + 250 / V_TRANSIT + 90), s


def main():
    print("=" * 92)
    print("SECTION 1  SEARCH ALTITUDE  -  spending surplus time on recall")
    print("=" * 92)
    print(f"  Sensor-derived HFOV {np.degrees(HFOV):.1f} deg "
          f"(the sweep planner in the main model hardcodes 70 deg -- see docstring)")
    print(f"  Fast-completion bonus needs <= {BONUS_S/60:.0f} min; hard limit "
          f"{LIMIT_S/60:.0f} min\n")
    print(f"{'AGL':>5}{'swath':>8}{'GSD':>9}{'person':>8}{'lines':>7}"
          f"{'sweep':>8}{'mission':>9}{'of bonus':>10}{'verdict':>10}")
    print(f"{'m':>5}{'m':>8}{'cm/px':>9}{'px':>8}{'':>7}{'s':>8}{'min':>9}{'':>10}{'':>10}")
    print('-' * 92)
    for h in [25, 30, 35, 40, 45, 50, 60, 70]:
        T, s = mission_time(h)
        frac = T / BONUS_S
        verdict = 'BONUS OK' if T <= BONUS_S else 'NO BONUS'
        print(f"{h:5.0f}{s['W']:8.1f}{s['gsd']*100:9.2f}{s['px']:8.0f}"
              f"{s['n_lines']:7.0f}{s['t']:8.0f}{T/60:9.1f}{frac:10.0%}{verdict:>10}")
    print()
    print("  Detection is 250 points; the speed bonus is 50 and needs only 15 min.")
    print("  Every altitude down to 25 m keeps the bonus with room to spare, so")
    print("  altitude should be chosen by recall, not by time.")
    print()
    print("  RECOMMENDED: 40 m. 140 px on a person against 93 px at 60 m, for")
    print("  ~2.5 min of a 15 min allowance. Going below 40 m keeps adding pixels")
    print("  but the marginal recall gain must be measured (P7) before paying for")
    print("  it in line count and turn overhead.")

    print("\n" + "=" * 92)
    print("SECTION 2  GEOTAG ERROR vs ALTITUDE  -  correcting an earlier claim")
    print("=" * 92)
    print("  An earlier revision of configuration-trade.md section 5.3 claimed the")
    print("  2.76 m ground-height term 'scales with the 37 m frame-edge distance,")
    print("  which comes down with altitude'. That is WRONG. For a ground-height")
    print("  error dh and an off-nadir angle theta:")
    print()
    print("      ground position error = dh * tan(theta)")
    print()
    print("  because the frame-edge distance r = h*tan(theta) and the projection")
    print("  error is (dh/h)*r. The h cancels. The term depends on the ground-height")
    print("  uncertainty and the off-nadir angle ONLY -- flying lower does not help.")
    print()
    print(f"{'dh (m)':>8}" + ''.join(f"{f'edge {a:.0f}deg':>12}"
                                     for a in [10, 20, 31.6]))
    print('-' * 92)
    for dh in [0.5, 1.0, 2.0, 3.0, 4.5]:
        row = ''.join(f"{dh*np.tan(np.radians(a)):12.2f}" for a in [10, 20, 31.6])
        print(f"{dh:8.1f}{row}")
    print()
    print(f"  Frame half-angle is {np.degrees(HFOV/2):.1f} deg, so a detection at the")
    print("  frame edge suffers tan = %.2f times the height error." % np.tan(HFOV / 2))
    print()
    print("  WHAT ACTUALLY REDUCES IT:")
    print("    1. Reduce dh -- survey the field elevation during setup, or carry a")
    print("       downward laser rangefinder. This is the cheapest large win.")
    print("    2. Reduce theta -- only geotag detections in the central portion of")
    print("       the frame. At 20 deg instead of 31.6 deg the term drops 41%.")
    print("       Costs nothing: the frame surplus is ~14 looks per target, so")
    print("       edge detections can be discarded and re-acquired near nadir.")
    print("    3. Multi-frame fusion does NOT help -- it is systematic, not noise.")
    print()
    print("  Altitude reduction DOES shrink the attitude/boresight term, which")
    print("  scales as h*epsilon, and improves centroid accuracy through GSD.")
    print("  It simply does not touch the dominant term.")

    print("\n" + "=" * 92)
    print("SECTION 3  DOWNLINK BUDGET  -  rule 8.14 requires a feed from EACH drone")
    print("=" * 92)
    print("  Detection runs onboard. The downlink carries video for the judges'")
    print("  display only, so resolution is a compliance question, not a")
    print("  perception one. 8.14 requires a live camera feed from each drone.\n")
    non_video = 3 * 0.235                      # Mbps, from sizing doc 12.1
    options = [
        ('1 x 720p30 H.265  (old, non-compliant)', 1, 1.80),
        ('3 x 720p30 H.265', 3, 1.80),
        ('3 x 720p15 H.265', 3, 1.00),
        ('3 x 480p15 H.265  (recommended)', 3, 0.60),
        ('3 x 360p15 H.265', 3, 0.35),
    ]
    # 802.11n 20 MHz 1SS PHY rates; usable throughput ~55% of PHY
    phy = {'MCS3': 26.0, 'MCS5': 52.0}
    print(f"{'option':<40}{'video':>8}{'total':>8}"
          + ''.join(f"{f'util {k}':>12}" for k in phy))
    print(f"{'':<40}{'Mbps':>8}{'Mbps':>8}" + ''.join(f"{'':>12}" for k in phy))
    print('-' * 92)
    for lbl, n, rate in options:
        v = n * rate
        tot = v + non_video
        utils = ''.join(f"{tot/(0.55*phy[k]):11.0%} " for k in phy)
        print(f"{lbl:<40}{v:8.2f}{tot:8.2f}{utils}")
    print()
    print(f"  Non-video load {non_video:.2f} Mbps (telemetry + swarm state + detections).")
    print("  Usable throughput taken as 55% of PHY rate, which is optimistic for a")
    print("  multi-hop mesh -- treat these utilisations as a floor.")
    print()
    print("  READING: three 480p15 feeds cost 1.80 Mbps, exactly what ONE 720p30")
    print("  feed cost before. Compliance with 8.14 is therefore free: the total")
    print("  offered load stays at the 2.5 Mbps the link was designed around, and")
    print("  the deliberate low-MCS margin strategy survives intact.")
    print("  Three 720p30 feeds would push utilisation past 40% at MCS3, which is")
    print("  where latency and jitter on a shared mesh start to bite.")


if __name__ == '__main__':
    main()
