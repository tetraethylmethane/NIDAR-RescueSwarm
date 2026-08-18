#!/usr/bin/env python3
"""Render recorded SITL telemetry as the ground station sees it.

Every position, altitude, mode and mAh below comes from MAVLink off a running
ArduPilot instance -- nothing is drawn from the mission plan. Where the plan and
the recording disagree, this renders the RECORDING.

Two corrections carried over from the figure work, because both were live bugs:

  * The pad centre is the BOUNDING-BOX centre of the three slots, not their
    centroid. The three slots sit in an L, so the centroid is pulled 0.436 m
    off -- enough to draw an aircraft outside a 3.66 m pad that is actually
    comfortably inside it.

  * Separation is 3-D and computed pairwise from the recording. The launch
    figure is 64.80 m, which reproduces from this file; an older 92.12 m
    claim did not.

What this recording does NOT contain is stated on the video rather than
implied away: every sample is mode AUTO, and there is not one detection or
payload-release event in the 109 logged. It is a coverage and deconfliction
run, and the panel says so.

Usage:
    python simulations/sitl/render_dashboard.py \
        simulations/recordings/mission-telemetry.json \
        ground-station/mission-flight.mp4
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                          # noqa: E402
from matplotlib.animation import FFMpegWriter            # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402

try:
    import imageio_ffmpeg
    matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:                                       # system ffmpeg then
    pass

# ------------------------------------------------------- Drikr dashboard skin
BG      = "#0A0A0C"
PANEL   = "#131316"
EDGE    = "#26262B"
FG      = "#FFFFFF"
DIM     = "#8A8A93"
FAINT   = "#4A4A52"
RED     = "#FF4D4D"
AMBER   = "#F5C242"
COL     = {1: "#3B9EFF", 2: "#F5C242", 3: "#D14FD1"}

PAD_SIDE   = 3.66      # rule 8.10, 12 ft
FOOTPRINT  = 1.046     # airframe diameter, m
PACK_MAH   = 13_500    # usable, matches the BATT_LOW_MAH trip at 10 800
LOW_MAH    = 10_800
WINDOW_S   = 15 * 60   # competition mission window

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "text.color": FG,
    "axes.labelcolor": DIM,
    "xtick.color": FAINT,
    "ytick.color": FAINT,
})


def physical_time(t, max_gap=5.0):
    """Elapsed time with recorder clock-jumps stitched out.

    Returns (corrected_times, removed_seconds, n_jumps). A gap larger than
    max_gap is replaced by the median sample interval, because the vehicle
    state across such a gap shows no discontinuity -- the clock jumped, the
    aircraft did not. Raw t is left untouched in the recording.
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


def logo(path, invert=True):
    """Black-ink-on-white PNG -> white-on-transparent RGBA, cropped to the ink.

    Returns None if the asset is missing, so the renderer still runs from a
    clean checkout that has not fetched the branding.
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return None
    if not os.path.exists(path):
        return None
    g = np.asarray(Image.open(path).convert("L"), dtype=float) / 255.0
    ink = 1.0 - g if invert else g          # ink -> 1.0, paper -> 0.0
    ys, xs = np.where(ink > 0.5)
    if not len(xs):
        return None
    pad = 2
    ink = ink[max(0, ys.min() - pad):ys.max() + pad + 1,
              max(0, xs.min() - pad):xs.max() + pad + 1]
    rgba = np.ones(ink.shape + (4,), dtype=float)   # white
    rgba[..., 3] = ink                              # keyed to ink density
    return rgba


def place(fig, img, x, y, h):
    """Drop an RGBA logo into figure coords at height h, aspect preserved."""
    if img is None:
        return None
    ph, pw = img.shape[0], img.shape[1]
    fw, fh = fig.get_size_inches()
    w = h * (pw / ph) * (fh / fw)
    ax = fig.add_axes([x, y, w, h], zorder=4)
    ax.imshow(img, interpolation="bilinear")
    ax.axis("off")
    ax.patch.set_alpha(0.0)
    return ax


def load(path):
    d = json.load(open(path))
    d["tracks"] = {int(k): v for k, v in d["tracks"].items()}
    return d


def panel(fig, rect, title=None):
    """A dashboard card: rounded, dark, hairline border."""
    x, y, w, h = rect
    fig.patches.append(FancyBboxPatch(
        (x, y), w, h, transform=fig.transFigure,
        boxstyle="round,pad=0,rounding_size=0.008",
        fc=PANEL, ec=EDGE, lw=1.0, zorder=-2))
    if title:
        fig.text(x + 0.011, y + h - 0.030, title, fontsize=9.5,
                 color=DIM, fontweight="bold", zorder=3)


def style_axes(ax, title):
    # Figure.get_children() yields axes BEFORE figure.patches, so at equal
    # zorder the cards paint over the plots. Lift the axes clear of them.
    ax.set_zorder(1)
    ax.set_facecolor(PANEL)
    for s in ax.spines.values():
        s.set_color(EDGE)
    ax.grid(alpha=0.10, color=FG, lw=0.6)
    ax.tick_params(labelsize=7.5, length=2)
    ax.set_title(title, fontsize=9, loc="left", color=DIM,
                 fontweight="bold", pad=6)


def render(d, out, fps=20):
    tracks = d["tracks"]
    n_s = len(tracks[1])
    T_raw = [tracks[1][k]["t"] for k in range(n_s)]
    T, removed, jumps = physical_time(T_raw)
    pairs = [(1, 2), (1, 3), (2, 3)]

    def sep(a, b, k):
        pa, pb = tracks[a][k], tracks[b][k]
        return ((pa["x"] - pb["x"]) ** 2 + (pa["y"] - pb["y"]) ** 2
                + (pa["alt"] - pb["alt"]) ** 2) ** 0.5

    AIRBORNE = 2.0     # m AGL; below this an aircraft is on the pad

    def airborne_closest(k):
        """Closest approach between two AIRBORNE aircraft, or None.

        Separation measured against parked aircraft is meaningless: the three
        pad slots are 1.22 m apart by design, so including them reports 2.93 m
        against a 5 m minimum and looks like a violation. Airborne-only gives
        5.51 m, which is the figure the deconfliction claim rests on.
        """
        v = [sep(a, b, k) for a, b in pairs
             if tracks[a][k]["alt"] > AIRBORNE and tracks[b][k]["alt"] > AIRBORNE]
        return min(v) if v else None

    closest = [airborne_closest(k) for k in range(n_s)]

    # CORRECTED: bounding-box centre, not the centroid of three L-shaped slots.
    pads = d["pad_xy"]
    cx = (min(p[0] for p in pads) + max(p[0] for p in pads)) / 2
    cy = (min(p[1] for p in pads) + max(p[1] for p in pads)) / 2

    fig = plt.figure(figsize=(19.2, 10.8), facecolor=BG)

    # ----------------------------------------------------------- header strip
    fig.patches.append(Rectangle((0, 0.938), 1, 0.062, transform=fig.transFigure,
                                 fc=BG, ec="none", zorder=1))
    assets = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))),
        "ground-station", "frontend", "public")
    place(fig, logo(os.path.join(assets, "drikr-logo.png")), 0.014, 0.951, 0.030)
    nid = logo(os.path.join(assets, "nidar-logo.png"))
    if nid is not None:
        ph, pw = nid.shape[0], nid.shape[1]
        fw, fh = fig.get_size_inches()
        w = 0.044 * (pw / ph) * (fh / fw)
        place(fig, nid, 0.986 - w, 0.947, 0.044)

    # tab row, as laid out in the mockup: FLIGHT DATA active, two inactive
    fig.patches.append(FancyBboxPatch(
        (0.408, 0.946), 0.086, 0.040, transform=fig.transFigure,
        boxstyle="round,pad=0,rounding_size=0.005", fc="#1B1B20", ec=EDGE,
        lw=1.0, zorder=2))
    fig.text(0.451, 0.960, "FLIGHT DATA", fontsize=10, color=FG, ha="center",
             fontweight="bold", zorder=3)
    fig.text(0.522, 0.960, "DIAGNOSTICS", fontsize=10, color=DIM, zorder=3)
    fig.text(0.600, 0.960, "⚙  SETTINGS", fontsize=10, color=DIM, zorder=3)


    # -------------------------------------------------------------- the cards
    panel(fig, (0.012, 0.586, 0.268, 0.334), "MISSION STATUS")
    panel(fig, (0.012, 0.345, 0.268, 0.228), "AIRCRAFT")
    panel(fig, (0.012, 0.085, 0.268, 0.260), "SAFETY")
    panel(fig, (0.292, 0.360, 0.412, 0.560))          # plan view
    panel(fig, (0.716, 0.360, 0.272, 0.560))          # pad
    panel(fig, (0.292, 0.085, 0.225, 0.260))
    panel(fig, (0.529, 0.085, 0.225, 0.260))
    panel(fig, (0.766, 0.085, 0.222, 0.260))

    ax  = fig.add_axes([0.318, 0.395, 0.360, 0.480])   # plan view
    axp = fig.add_axes([0.746, 0.400, 0.214, 0.460])   # pad close-up
    axa = fig.add_axes([0.322, 0.130, 0.180, 0.170])   # altitude
    axb = fig.add_axes([0.559, 0.130, 0.180, 0.170])   # battery
    axs = fig.add_axes([0.796, 0.130, 0.178, 0.170])   # separation

    # ---- mission-status readouts -------------------------------------------
    # Two rows of two: "MIN AIRBORNE 69.0 m" does not fit four across a
    # 0.268-wide card, and four across left the lower half of it empty.
    stat = {}
    for lab, xl, yl in (("ELAPSED", 0.030, 0.858), ("WINDOW", 0.158, 0.858),
                        ("CLOSEST AIRBORNE", 0.030, 0.756),
                        ("MIN AIRBORNE", 0.158, 0.756)):
        fig.text(xl, yl, lab, fontsize=7.2, color=DIM, zorder=3)
        stat[lab] = fig.text(xl, yl - 0.040, "--", fontsize=16, color=FG,
                             family="monospace", zorder=3)
    # 7 lines when the clock note is present; sized to stay inside the card.
    note = fig.text(0.030, 0.694, "", fontsize=7.0, color=DIM, zorder=3,
                    va="top", linespacing=1.45)
    clock_note = (
        "Coverage and deconfliction run. Every sample is mode AUTO; no\n"
        "detection or payload-release event is present, so no survivor or\n"
        "kit counter is shown.")
    if jumps:
        clock_note += (
            f"\n\nCLOCK CORRECTED: the recorder's timestamp jumps "
            f"{removed:.0f} s\nmid-descent while the aircraft state stays "
            f"continuous.\nElapsed shown is physical time; raw t is unchanged "
            f"in\nthe recording.")

    # ---- per-aircraft rows --------------------------------------------------
    rows = {}
    for i in (1, 2, 3):
        y = 0.512 - (i - 1) * 0.050
        fig.text(0.030, y, "●", fontsize=11, color=COL[i], zorder=3)
        fig.text(0.046, y, f"DRONE 0{i}", fontsize=9.5, color=FG,
                 fontweight="bold", zorder=3)
        rows[i] = {
            "mode": fig.text(0.108, y, "", fontsize=9, color=DIM, zorder=3),
            "alt":  fig.text(0.178, y, "", fontsize=9, color=DIM,
                             family="monospace", zorder=3),
            "batt": fig.text(0.262, y, "", fontsize=9, color=FG, ha="right",
                             family="monospace", zorder=3),
        }
        fig.patches.append(Rectangle((0.030, y - 0.014), 0.232, 0.0008,
                                     transform=fig.transFigure, fc=EDGE,
                                     ec="none", zorder=2))

    # ---- safety card --------------------------------------------------------
    fig.patches.append(FancyBboxPatch(
        (0.030, 0.215), 0.232, 0.088, transform=fig.transFigure,
        boxstyle="round,pad=0,rounding_size=0.006", fc="#17171B", ec=EDGE,
        lw=0.9, zorder=2))
    fig.text(0.042, 0.283, "⚠", fontsize=15, color=AMBER, zorder=3)
    fig.text(0.066, 0.286, "NOT IMPLEMENTED", fontsize=8.5, color=AMBER,
             fontweight="bold", zorder=3)
    fig.text(0.066, 0.226,
             "Abort and recall record operator intent to the\n"
             "mission log and transmit nothing. Recover the\n"
             "aircraft with the safety pilot's RC.",
             fontsize=7.4, color=DIM, zorder=3, linespacing=1.5)
    for lbl, x0, colr in (("ABORT", 0.030, RED), ("RECALL", 0.148, AMBER)):
        fig.patches.append(FancyBboxPatch(
            (x0, 0.150), 0.114, 0.048, transform=fig.transFigure,
            boxstyle="round,pad=0,rounding_size=0.006", fc="none", ec=colr,
            lw=1.2, alpha=0.55, zorder=2))
        fig.text(x0 + 0.057, 0.167, lbl, fontsize=10, color=colr, ha="center",
                 fontweight="bold", alpha=0.55, zorder=3)
    fig.text(0.030, 0.105, "DISABLED — no safety radio configured",
             fontsize=7.4, color=FAINT, zorder=3)

    # ---- plan view ----------------------------------------------------------
    style_axes(ax, "PLAN VIEW — 600 m geofence, three-strip partition")
    bx = [p[0] for p in d["boundary_xy"]] + [d["boundary_xy"][0][0]]
    by = [p[1] for p in d["boundary_xy"]] + [d["boundary_xy"][0][1]]
    ax.plot(bx, by, color=FAINT, lw=1.1, ls="--")
    for i, s in enumerate(d.get("strips", []), start=1):
        sx = [p[0] for p in s] + [s[0][0]]
        sy = [p[1] for p in s] + [s[0][1]]
        ax.fill(sx, sy, color=COL[i], alpha=0.055)
        ax.plot(sx, sy, color=COL[i], lw=0.7, alpha=0.35)
    for i, p in enumerate(pads, start=1):
        ax.plot(p[0], p[1], marker="s", ms=5, color=COL[i], zorder=5)
    ax.set_aspect("equal")
    ax.set_xlabel("east (m)", fontsize=8)
    ax.set_ylabel("north (m)", fontsize=8)

    style_axes(axp, "RECOVERY PAD — 3.66 m, 1.22 m slots")
    axp.add_patch(Rectangle((cx - PAD_SIDE / 2, cy - PAD_SIDE / 2),
                            PAD_SIDE, PAD_SIDE, fill=False, ec=RED, lw=1.5))
    axp.text(cx, cy + PAD_SIDE / 2 + 0.30, "12 ft pad · rule 8.10",
             ha="center", fontsize=7.5, color=RED)
    for i, p in enumerate(pads, start=1):
        axp.plot(p[0], p[1], marker="s", ms=5, color=COL[i], alpha=0.40)
        axp.add_patch(Circle(p, FOOTPRINT / 2, fill=False, ec=COL[i],
                             lw=0.7, ls=":", alpha=0.35))
    axp.set_xlim(cx - 3.1, cx + 3.1)
    axp.set_ylim(cy - 3.1, cy + 3.1)
    axp.set_aspect("equal")

    style_axes(axa, "ALTITUDE (m)")
    axa.set_xlim(0, T[-1]); axa.set_ylim(-2, 48)
    for a in d.get("transit_alt", []):
        axa.axhline(a, color=FAINT, lw=0.5, ls=":")
    axa.axhline(d.get("search_alt", 40), color=DIM, lw=0.6, ls="--")

    style_axes(axb, "BATTERY CONSUMED (mAh)")
    axb.set_xlim(0, T[-1]); axb.set_ylim(0, PACK_MAH)
    axb.axhline(LOW_MAH, color=RED, lw=1.0, ls="--")
    axb.text(4, LOW_MAH + 180, "BATT_LOW_MAH — 20 % reserve", fontsize=6.6,
             color=RED)

    style_axes(axs, "CLOSEST AIRBORNE PAIR (m)")
    # Auto-scale: aircraft in different strips run to a few hundred metres
    # apart, and a fixed 90 m ceiling silently clipped the trace off the top.
    _seen = [c for c in closest if c is not None]
    axs.set_xlim(0, T[-1])
    axs.set_ylim(0, (max(_seen) * 1.12) if _seen else 90)
    axs.axhline(5.0, color=RED, lw=1.0, ls="--")
    axs.text(4, 6.5, "5 m minimum", fontsize=6.6, color=RED)

    # ---- artists ------------------------------------------------------------
    trails = {i: ax.plot([], [], color=COL[i], lw=1.4, alpha=0.9)[0] for i in tracks}
    dots   = {i: ax.plot([], [], marker="o", ms=8, color=COL[i], mec=BG,
                         mew=1.4, zorder=6)[0] for i in tracks}
    pdots  = {i: axp.plot([], [], marker="o", ms=10, color=COL[i], mec=BG,
                          mew=1.4, zorder=6)[0] for i in tracks}
    prings = {i: axp.add_patch(Circle((0, 0), FOOTPRINT / 2, fill=False,
                                      ec=COL[i], lw=1.3, alpha=0.0))
              for i in tracks}
    alines = {i: axa.plot([], [], color=COL[i], lw=1.3)[0] for i in tracks}
    blines = {i: axb.plot([], [], color=COL[i], lw=1.3)[0] for i in tracks}
    sline  = axs.plot([], [], color=FG, lw=1.4)[0]
    sfill  = [None]

    allx = [tracks[i][k]["x"] for i in tracks for k in range(n_s)]
    ally = [tracks[i][k]["y"] for i in tracks for k in range(n_s)]
    m = 45
    ax.set_xlim(min(allx) - m, max(allx) + m)
    ax.set_ylim(min(ally) - m, max(ally) + m)

    xs = {i: [] for i in tracks}
    ys = {i: [] for i in tracks}

    writer = FFMpegWriter(fps=fps, codec="libx264", bitrate=6000,
                          metadata={"title": "RescueSwarm mission replay",
                                    "artist": "Drikr Systems"},
                          extra_args=["-pix_fmt", "yuv420p", "-preset", "medium"])

    with writer.saving(fig, out, dpi=100):
        for k in range(n_s):
            for i in tracks:
                s = tracks[i][k]
                xs[i].append(s["x"]); ys[i].append(s["y"])
                trails[i].set_data(xs[i], ys[i])
                dots[i].set_data([s["x"]], [s["y"]])

                near = abs(s["x"] - cx) < 5 and abs(s["y"] - cy) < 5
                pdots[i].set_data([s["x"]] if near else [],
                                  [s["y"]] if near else [])
                prings[i].set_center((s["x"], s["y"]))
                prings[i].set_alpha(0.8 if near else 0.0)

                alines[i].set_data(T[:k + 1],
                                   [tracks[i][j]["alt"] for j in range(k + 1)])
                blines[i].set_data(T[:k + 1],
                                   [tracks[i][j]["mah"] for j in range(k + 1)])

                pct = max(0.0, 100.0 * (1 - s["mah"] / PACK_MAH))
                rows[i]["mode"].set_text(s["mode"])
                rows[i]["alt"].set_text(f"{s['alt']:5.1f} m")
                rows[i]["batt"].set_text(f"{pct:3.0f}%")
                rows[i]["batt"].set_color(RED if pct < 20 else FG)
                rows[i]["mode"].set_color(DIM if s["armed"] else FAINT)

            tt = [T[j] for j in range(k + 1) if closest[j] is not None]
            vv = [closest[j] for j in range(k + 1) if closest[j] is not None]
            sline.set_data(tt, vv)
            if sfill[0] is not None:
                sfill[0].remove()
                sfill[0] = None
            if tt:
                sfill[0] = axs.fill_between(tt, 0, vv, color=FG, alpha=0.07)

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
            else:
                stat["MIN AIRBORNE"].set_text("--")

            note.set_text(clock_note)
            writer.grab_frame()

    plt.close(fig)
    seen = [c for c in closest if c is not None]
    return {"frames": n_s, "duration_s": n_s / fps, "min_sep": min(seen),
            "pad_centre": (cx, cy), "done_at": T[-1], "raw_at": T_raw[-1],
            "removed": removed, "jumps": jumps}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else \
        "simulations/recordings/mission-telemetry.json"
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
        print(f"  CLOCK JUMP       {r['jumps']} gap(s), {r['removed']:.1f} s "
              f"of recorder time removed")
