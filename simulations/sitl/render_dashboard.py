#!/usr/bin/env python3
"""Render recorded SITL telemetry as the ground station sees it.

Laid out to match ground-station/gcs-dashboard.png: mission status and safety
down the left, a map filling the main area, and one camera pane per aircraft
across the bottom.

Every position, altitude, mode and mAh comes from MAVLink off a running
ArduPilot instance. Where the plan and the recording disagree, this renders the
RECORDING.

Three things are corrected or stated rather than smoothed over:

  * The pad centre is the BOUNDING-BOX centre of the three slots, not their
    centroid. The slots sit in an L, so the centroid is pulled 0.436 m off --
    enough to draw an aircraft outside a 3.66 m pad it is comfortably inside.

  * Separation is measured only between AIRBORNE aircraft. The pad slots are
    1.22 m apart by design, so including parked aircraft reports a spurious
    violation against the 5 m minimum.

  * THE CAMERA PANES ARE COMPUTED, NOT IMAGERY. SITL carries no camera. Each
    pane draws the ground footprint the lens would actually cover at that
    instant, sized from the repo's own GSD table, and says so on its face. It
    is a coverage instrument, not a picture.

Usage:
    python simulations/sitl/render_dashboard.py \
        simulations/recordings/mission-telemetry-speedup1.json \
        ground-station/mission-flight.mp4
"""
from __future__ import annotations

import json
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                          # noqa: E402
import numpy as np                                       # noqa: E402
from matplotlib.animation import FFMpegWriter            # noqa: E402
from matplotlib.patches import (Circle, FancyBboxPatch,  # noqa: E402
                                Rectangle)

try:
    import imageio_ffmpeg
    matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    pass

# ------------------------------------------------------- Drikr dashboard skin
BG, PANEL, EDGE = "#0A0A0C", "#131316", "#26262B"
FG, DIM, FAINT = "#FFFFFF", "#8A8A93", "#4A4A52"
RED, AMBER = "#FF4D4D", "#F5C242"
MAP_BG, MAP_GRID = "#0E1216", "#28323A"
COL = {1: "#3B9EFF", 2: "#F5C242", 3: "#D14FD1"}

PAD_SIDE, FOOTPRINT = 3.66, 1.046
PACK_MAH = 13_500
WINDOW_S = 15 * 60
AIRBORNE = 2.0

# Camera. GSD is linear in altitude; docs/sizing/configuration-trade.md gives
# 1.22 cm/px at 40 m for the Arducam IMX477 + 6 mm lens, and the sensor is
# 4056 x 3040. Every footprint number below follows from those three.
GSD_AT_40M, SENSOR_W, SENSOR_H = 0.0122, 4056, 3040
PERSON_M = 1.7

# The pad's true position, from fly_and_record.py, so the map carries real
# coordinates rather than bare local metres.
PAD_LAT, PAD_LON = 12.99700, 80.00000
M_PER_DEG_LAT = 111_320.0

plt.rcParams.update({
    "font.family": "DejaVu Sans", "text.color": FG,
    "axes.labelcolor": DIM, "xtick.color": FAINT, "ytick.color": FAINT,
})


def logo(path):
    """Black-ink-on-white PNG -> white-on-transparent RGBA, cropped to ink."""
    try:
        from PIL import Image
    except ImportError:
        return None
    if not os.path.exists(path):
        return None
    g = np.asarray(Image.open(path).convert("L"), dtype=float) / 255.0
    ink = 1.0 - g
    ys, xs = np.where(ink > 0.5)
    if not len(xs):
        return None
    ink = ink[max(0, ys.min() - 2):ys.max() + 3, max(0, xs.min() - 2):xs.max() + 3]
    rgba = np.ones(ink.shape + (4,), dtype=float)
    rgba[..., 3] = ink
    return rgba


def place(fig, img, x, y, h):
    if img is None:
        return
    ph, pw = img.shape[0], img.shape[1]
    fw, fh = fig.get_size_inches()
    ax = fig.add_axes([x, y, h * (pw / ph) * (fh / fw), h], zorder=4)
    ax.imshow(img, interpolation="bilinear")
    ax.axis("off")
    ax.patch.set_alpha(0.0)


def physical_time(t, max_gap=5.0):
    """Elapsed time with recorder clock-jumps stitched out.

    A gap larger than max_gap is replaced by the median sample interval,
    because vehicle state across such a gap shows no discontinuity: the clock
    jumped, the aircraft did not. Raw t is left untouched in the recording.
    """
    d = [t[i + 1] - t[i] for i in range(len(t) - 1)]
    med = sorted(d)[len(d) // 2] if d else 0.0
    out, removed, jumps = [0.0], 0.0, 0
    for g in d:
        if g > max_gap:
            removed += g - med
            jumps += 1
            g = med
        out.append(out[-1] + g)
    return out, removed, jumps


def load(path):
    d = json.load(open(path))
    d["tracks"] = {int(k): v for k, v in d["tracks"].items()}
    return d


def card(fig, rect, title=None):
    x, y, w, h = rect
    fig.patches.append(FancyBboxPatch(
        (x, y), w, h, transform=fig.transFigure,
        boxstyle="round,pad=0,rounding_size=0.007",
        fc=PANEL, ec=EDGE, lw=1.0, zorder=-2))
    if title:
        fig.text(x + 0.010, y + h - 0.028, title, fontsize=9,
                 color=DIM, fontweight="bold", zorder=3)


def style(ax, face=PANEL, grid=0.0):
    # Figure.get_children() yields axes BEFORE figure.patches, so at equal
    # zorder the cards paint over the plots. Lift the axes clear of them.
    ax.set_zorder(1)
    ax.set_facecolor(face)
    for s in ax.spines.values():
        s.set_color(EDGE)
    if grid:
        ax.grid(alpha=grid, color=MAP_GRID, lw=0.6)
    ax.tick_params(labelsize=6.5, length=2)


def render(d, out, fps=20):
    tracks = d["tracks"]
    n_s = len(tracks[1])
    T_raw = [tracks[1][k]["t"] for k in range(n_s)]
    T, removed, jumps = physical_time(T_raw)
    pairs = [(1, 2), (1, 3), (2, 3)]

    def sep(a, b, k):
        p, q = tracks[a][k], tracks[b][k]
        return ((p["x"] - q["x"]) ** 2 + (p["y"] - q["y"]) ** 2
                + (p["alt"] - q["alt"]) ** 2) ** 0.5

    def closest_air(k):
        v = [sep(a, b, k) for a, b in pairs
             if tracks[a][k]["alt"] > AIRBORNE and tracks[b][k]["alt"] > AIRBORNE]
        return min(v) if v else None

    closest = [closest_air(k) for k in range(n_s)]

    pads = d["pad_xy"]
    cx = (min(p[0] for p in pads) + max(p[0] for p in pads)) / 2
    cy = (min(p[1] for p in pads) + max(p[1] for p in pads)) / 2

    # Local metres -> degrees, anchored on the known pad position.
    lat0 = PAD_LAT - cy / M_PER_DEG_LAT
    m_per_deg_lon = M_PER_DEG_LAT * math.cos(math.radians(PAD_LAT))
    to_lat = lambda y: lat0 + y / M_PER_DEG_LAT          # noqa: E731
    to_lon = lambda x: PAD_LON + x / m_per_deg_lon       # noqa: E731

    fig = plt.figure(figsize=(19.2, 10.8), facecolor=BG)

    # ------------------------------------------------------------- header
    assets = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "ground-station", "frontend", "public")
    place(fig, logo(os.path.join(assets, "drikr-logo.png")), 0.014, 0.951, 0.030)
    nid = logo(os.path.join(assets, "nidar-logo.png"))
    if nid is not None:
        fw, fh = fig.get_size_inches()
        w = 0.044 * (nid.shape[1] / nid.shape[0]) * (fh / fw)
        place(fig, nid, 0.986 - w, 0.947, 0.044)
    fig.patches.append(FancyBboxPatch(
        (0.408, 0.946), 0.086, 0.040, transform=fig.transFigure,
        boxstyle="round,pad=0,rounding_size=0.005", fc="#1B1B20", ec=EDGE,
        lw=1.0, zorder=2))
    fig.text(0.451, 0.960, "FLIGHT DATA", fontsize=10, color=FG, ha="center",
             fontweight="bold", zorder=3)
    fig.text(0.522, 0.960, "DIAGNOSTICS", fontsize=10, color=DIM, zorder=3)
    fig.text(0.600, 0.960, "⚙  SETTINGS", fontsize=10, color=DIM, zorder=3)

    # ------------------------------------------------------------- cards
    card(fig, (0.012, 0.560, 0.268, 0.362), "MISSION STATUS")
    card(fig, (0.012, 0.318, 0.268, 0.228), "SAFETY")
    card(fig, (0.292, 0.318, 0.696, 0.604))                  # map
    for x in (0.012, 0.343, 0.674):
        card(fig, (x, 0.030, 0.314, 0.272))                  # camera panes

    axm = fig.add_axes([0.312, 0.336, 0.660, 0.548], zorder=1)

    # ---- mission-status readouts ---------------------------------------
    stat = {}
    for lab, xl, yl in (("ELAPSED", 0.030, 0.876), ("WINDOW", 0.158, 0.876),
                        ("CLOSEST AIRBORNE", 0.030, 0.798),
                        ("MIN AIRBORNE", 0.158, 0.798)):
        fig.text(xl, yl, lab, fontsize=7, color=DIM, zorder=3)
        stat[lab] = fig.text(xl, yl - 0.034, "--", fontsize=15, color=FG,
                             family="monospace", zorder=3)

    rows = {}
    for i in (1, 2, 3):
        y = 0.712 - (i - 1) * 0.040
        fig.text(0.030, y, "●", fontsize=10, color=COL[i], zorder=3)
        fig.text(0.045, y, f"DRONE 0{i}", fontsize=9, color=FG,
                 fontweight="bold", zorder=3)
        rows[i] = {
            "mode": fig.text(0.103, y, "", fontsize=8.5, color=DIM, zorder=3),
            "alt": fig.text(0.160, y, "", fontsize=8.5, color=DIM,
                            family="monospace", zorder=3),
            "batt": fig.text(0.262, y, "", fontsize=8.5, color=FG, ha="right",
                             family="monospace", zorder=3),
        }
        fig.patches.append(Rectangle((0.030, y - 0.011), 0.232, 0.0007,
                                     transform=fig.transFigure, fc=EDGE,
                                     ec="none", zorder=2))
    note = fig.text(0.030, 0.608, "", fontsize=6.5, color=DIM, zorder=3,
                    va="top", linespacing=1.45)

    # ---- safety card ----------------------------------------------------
    fig.patches.append(FancyBboxPatch(
        (0.028, 0.418), 0.236, 0.072, transform=fig.transFigure,
        boxstyle="round,pad=0,rounding_size=0.005", fc="#17171B", ec=EDGE,
        lw=0.9, zorder=2))
    fig.text(0.040, 0.470, "⚠", fontsize=13, color=AMBER, zorder=3)
    fig.text(0.062, 0.472, "NOT IMPLEMENTED", fontsize=8, color=AMBER,
             fontweight="bold", zorder=3)
    fig.text(0.062, 0.424,
             "Abort and recall record operator intent to the mission\n"
             "log and transmit nothing. Recover the aircraft with the\n"
             "safety pilot's RC.", fontsize=6.8, color=DIM, zorder=3,
             linespacing=1.5)
    for lbl, x0, c in (("ABORT", 0.028, RED), ("RECALL", 0.146, AMBER)):
        fig.patches.append(FancyBboxPatch(
            (x0, 0.352), 0.118, 0.042, transform=fig.transFigure,
            boxstyle="round,pad=0,rounding_size=0.005", fc="none", ec=c,
            lw=1.2, alpha=0.5, zorder=2))
        fig.text(x0 + 0.059, 0.367, lbl, fontsize=9.5, color=c, ha="center",
                 fontweight="bold", alpha=0.5, zorder=3)
    fig.text(0.028, 0.330, "DISABLED — no safety radio configured",
             fontsize=6.8, color=FAINT, zorder=3)

    # ---- map ------------------------------------------------------------
    style(axm, face=MAP_BG, grid=0.14)
    bx = [p[0] for p in d["boundary_xy"]] + [d["boundary_xy"][0][0]]
    by = [p[1] for p in d["boundary_xy"]] + [d["boundary_xy"][0][1]]
    strips = d.get("strips", [])
    for i, s in enumerate(strips, start=1):
        sx = [p[0] for p in s] + [s[0][0]]
        sy = [p[1] for p in s] + [s[0][1]]
        axm.fill(sx, sy, color=COL[i], alpha=0.05, zorder=1)
        axm.plot(sx, sy, color=COL[i], lw=0.7, alpha=0.30, zorder=2)
    axm.plot(bx, by, color="#6E7A85", lw=1.2, ls="--", zorder=3)
    axm.plot([cx], [cy], marker="s", ms=7, mfc="none", mec=FG, mew=1.4, zorder=6)
    axm.annotate("PAD", (cx, cy), textcoords="offset points", xytext=(9, -3),
                 fontsize=7.5, color=FG, zorder=6)

    allx = [tracks[i][k]["x"] for i in tracks for k in range(n_s)]
    ally = [tracks[i][k]["y"] for i in tracks for k in range(n_s)]
    m = 40
    x0, x1 = min(allx) - m, max(allx) + m
    y0, y1 = min(ally) - m, max(ally) + m
    # Equal aspect in a wide card would leave the tall search area as a
    # narrow column. Fit vertically and widen the view instead: a map showing
    # extra east-west context is still a correct map.
    fw_in, fh_in = fig.get_size_inches()
    ax_ratio = (0.660 * fw_in) / (0.548 * fh_in)
    want_x = (y1 - y0) * ax_ratio
    xc = (min(bx) + max(bx)) / 2
    if want_x > (x1 - x0):
        x0, x1 = xc - want_x / 2, xc + want_x / 2
    axm.set_xlim(x0, x1)
    axm.set_ylim(y0, y1)
    axm.set_aspect("equal")
    axm.xaxis.set_major_locator(plt.MaxNLocator(6))
    axm.yaxis.set_major_locator(plt.MaxNLocator(7))
    xt = [t for t in axm.get_xticks() if x0 <= t <= x1]
    yt = [t for t in axm.get_yticks() if y0 <= t <= y1]
    axm.set_xticks(xt); axm.set_yticks(yt)
    axm.set_xticklabels([f"{to_lon(t):.5f}°E" for t in xt])
    axm.set_yticklabels([f"{to_lat(t):.5f}°N" for t in yt])
    fig.text(0.303, 0.898, "MAP  ·  600 m geofence, three-strip partition",
             fontsize=9, color=DIM, fontweight="bold", zorder=3)

    sb, sx0, sy0 = 100.0, x0 + (x1 - x0) * 0.04, y0 + (y1 - y0) * 0.05
    axm.plot([sx0, sx0 + sb], [sy0, sy0], color=FG, lw=2.2, zorder=7)
    axm.text(sx0 + sb / 2, sy0 + (y1 - y0) * 0.013, "100 m", ha="center",
             fontsize=7, color=FG, zorder=7)
    axm.annotate("", (x0 + (x1 - x0) * 0.045, y1 - (y1 - y0) * 0.040),
                 xytext=(x0 + (x1 - x0) * 0.045, y1 - (y1 - y0) * 0.115),
                 arrowprops=dict(arrowstyle="-|>", color=FG, lw=1.3),
                 ha="center", fontsize=8, color=FG, zorder=7)
    axm.text(x0 + (x1 - x0) * 0.045, y1 - (y1 - y0) * 0.145, "N",
             ha="center", fontsize=8.5, color=FG, fontweight="bold", zorder=7)

    trails = {i: axm.plot([], [], color=COL[i], lw=1.4, alpha=0.9, zorder=4)[0]
              for i in tracks}
    dots = {i: axm.plot([], [], marker="o", ms=9, color=COL[i], mec=BG,
                        mew=1.5, zorder=8)[0] for i in tracks}
    halos = {i: axm.add_patch(Circle((0, 0), 0, fill=False, ec=COL[i],
                                     lw=1.0, alpha=0.0, zorder=7))
             for i in tracks}

    # ---- camera panes ---------------------------------------------------
    cams, cam_hdr, cam_foot = {}, {}, {}
    for idx, i in enumerate((1, 2, 3)):
        x = (0.012, 0.343, 0.674)[idx]
        fig.text(x + 0.010, 0.282, f"DRONE {i}", fontsize=8.5, color=FG,
                 fontweight="bold", zorder=3)
        fig.text(x + 0.050, 0.282, "● NADIR", fontsize=8, color=COL[i],
                 zorder=3)
        cam_hdr[i] = fig.text(x + 0.304, 0.282, "", fontsize=7.5, color=DIM,
                              ha="right", family="monospace", zorder=3)
        ax = fig.add_axes([x + 0.010, 0.052, 0.294, 0.220], zorder=1)
        style(ax, face="#0C1013")
        ax.set_xticks([]); ax.set_yticks([])
        cams[i] = ax
        cam_foot[i] = fig.text(x + 0.010, 0.037, "", fontsize=6.2,
                               color=FAINT, zorder=3)

    writer = FFMpegWriter(fps=fps, codec="libx264", bitrate=7000,
                          metadata={"title": "RescueSwarm mission replay",
                                    "artist": "Drikr Systems"},
                          extra_args=["-pix_fmt", "yuv420p", "-preset", "medium"])

    xs = {i: [] for i in tracks}
    ys = {i: [] for i in tracks}

    with writer.saving(fig, out, dpi=100):
        for k in range(n_s):
            for i in tracks:
                s = tracks[i][k]
                xs[i].append(s["x"]); ys[i].append(s["y"])
                trails[i].set_data(xs[i], ys[i])
                dots[i].set_data([s["x"]], [s["y"]])

                gsd = GSD_AT_40M * (s["alt"] / 40.0) if s["alt"] > 0 else 0.0
                fw_m, fh_m = SENSOR_W * gsd, SENSOR_H * gsd
                flying = s["alt"] > AIRBORNE
                halos[i].set_center((s["x"], s["y"]))
                halos[i].set_radius(max(fw_m, fh_m) / 2 if flying else 0.0)
                halos[i].set_alpha(0.35 if flying else 0.0)

                pct = max(0.0, 100.0 * (1 - s["mah"] / PACK_MAH))
                rows[i]["mode"].set_text(s["mode"])
                rows[i]["alt"].set_text(f"{s['alt']:6.1f} m")
                rows[i]["batt"].set_text(f"{pct:3.0f}%")
                rows[i]["batt"].set_color(RED if pct < 20 else FG)

                # --- camera pane: the ground the lens actually covers -----
                ax = cams[i]
                ax.clear()
                style(ax, face="#0C1013")
                ax.set_xticks([]); ax.set_yticks([])
                if not flying or fw_m <= 0:
                    ax.text(0.5, 0.5, "ON PAD", transform=ax.transAxes,
                            ha="center", va="center", fontsize=13,
                            color=FAINT, fontweight="bold")
                    cam_hdr[i].set_text("")
                    cam_foot[i].set_text("")
                    continue

                px, py = s["x"], s["y"]
                ax.set_xlim(px - fw_m / 2, px + fw_m / 2)
                ax.set_ylim(py - fh_m / 2, py + fh_m / 2)
                ax.set_aspect("equal")
                for gx in np.arange(10 * np.floor((px - fw_m / 2) / 10),
                                    px + fw_m / 2 + 10, 10):
                    ax.axvline(gx, color=FG, alpha=0.07, lw=0.6, zorder=0)
                for gy in np.arange(10 * np.floor((py - fh_m / 2) / 10),
                                    py + fh_m / 2 + 10, 10):
                    ax.axhline(gy, color=FG, alpha=0.07, lw=0.6, zorder=0)
                for j, st in enumerate(strips, start=1):
                    sx = [p[0] for p in st] + [st[0][0]]
                    sy = [p[1] for p in st] + [st[0][1]]
                    ax.fill(sx, sy, color=COL[j], alpha=0.10, zorder=1)
                    ax.plot(sx, sy, color=COL[j], lw=1.0, alpha=0.5, zorder=2)
                ax.plot(bx, by, color="#6E7A85", lw=1.2, ls="--", zorder=3)
                ax.plot([cx], [cy], marker="s", ms=8, mfc="none", mec=FG,
                        mew=1.2, zorder=4)
                ax.plot([px], [py], marker="+", ms=11, color=COL[i], mew=1.4,
                        zorder=6)
                cam_hdr[i].set_text(f"{s['alt']:5.1f} m AGL")
                cam_foot[i].set_text(
                    f"COMPUTED FOOTPRINT {fw_m:.0f}×{fh_m:.0f} m · "
                    f"GSD {gsd*100:.2f} cm/px · 1.7 m person ≈ "
                    f"{PERSON_M/gsd:.0f} px · SITL has no camera")

            el = T[k]
            stat["ELAPSED"].set_text(f"{int(el)//60:02d}:{int(el)%60:02d}")
            stat["WINDOW"].set_text(f"{WINDOW_S//60:02d}:00")
            stat["CLOSEST AIRBORNE"].set_text(
                f"{closest[k]:.1f} m" if closest[k] is not None else "on pad")
            seen = [c for c in closest[:k + 1] if c is not None]
            if seen:
                mn = min(seen)
                stat["MIN AIRBORNE"].set_text(f"{mn:.1f} m")
                stat["MIN AIRBORNE"].set_color(RED if mn < 5 else FG)

            txt = ("Coverage and deconfliction run · all samples mode AUTO\n"
                   "No detection or payload-release event, so no survivor\n"
                   "or kit counter is shown\n"
                   "Camera panes are COMPUTED coverage, not imagery")
            if jumps:
                txt += (f"\nClock corrected: {removed:.0f} s of recorder "
                        f"time removed")
            note.set_text(txt)
            writer.grab_frame()

    plt.close(fig)
    seen = [c for c in closest if c is not None]
    return {"frames": n_s, "duration_s": n_s / fps, "min_sep": min(seen),
            "pad_centre": (cx, cy), "done_at": T[-1], "raw_at": T_raw[-1],
            "removed": removed, "jumps": jumps}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else \
        "simulations/recordings/mission-telemetry-speedup1.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "ground-station/mission-flight.mp4"
    r = render(load(src), out)
    print(f"wrote {out}")
    print(f"  {r['frames']} frames · {r['duration_s']:.1f} s · "
          f"{os.path.getsize(out)/1e6:.2f} MB")
    print(f"  min sep airborne {r['min_sep']:.2f} m  (5 m minimum)")
    print(f"  pad centre       {r['pad_centre'][0]:.3f}, {r['pad_centre'][1]:.3f}")
    print(f"  physical duration {r['done_at']:.1f} s "
          f"(raw t claims {r['raw_at']:.1f} s)")
    if r["jumps"]:
        print(f"  CLOCK JUMP       {r['jumps']} gap(s), {r['removed']:.1f} s removed")
