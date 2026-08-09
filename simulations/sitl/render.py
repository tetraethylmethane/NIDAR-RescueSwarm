#!/usr/bin/env python3
"""Turn recorded SITL telemetry into a GIF you can watch and check.

Nothing here is drawn from the plan -- every position, altitude, mode and mAh
comes from MAVLink off a running aircraft. The pad inset is the part worth
watching: three aircraft, 1.22 m apart, arriving on one 3.66 m pad.
"""
from __future__ import annotations

import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib.animation import PillowWriter        # noqa: E402
from matplotlib.patches import Circle, Rectangle     # noqa: E402

COL = {1: "#e6194b", 2: "#3cb44b", 3: "#4363d8"}
PAD_SIDE = 3.66
FOOTPRINT = 1.046


def load(path):
    d = json.load(open(path))
    d["tracks"] = {int(k): v for k, v in d["tracks"].items()}
    return d


def render(d, out, title, subtitle, fps=20, max_frames=420):
    tracks = d["tracks"]
    n = len(tracks)
    step = max(1, len(tracks[1]) // max_frames)
    frames = list(range(0, len(tracks[1]), step))

    fig = plt.figure(figsize=(13, 7.3), facecolor="white")
    gs = fig.add_gridspec(3, 3, width_ratios=[1.45, 1, 1],
                          height_ratios=[1, 1, 1], hspace=0.55, wspace=0.32,
                          left=0.055, right=0.985, top=0.86, bottom=0.08)
    ax = fig.add_subplot(gs[:, 0])          # plan view
    axp = fig.add_subplot(gs[0, 1])         # pad close-up
    axa = fig.add_subplot(gs[1, 1])         # altitude
    axb = fig.add_subplot(gs[2, 1])         # battery
    axs = fig.add_subplot(gs[:, 2])         # separation + log

    fig.suptitle(title, fontsize=15, fontweight="bold", x=0.055, ha="left",
                 y=0.965)
    fig.text(0.055, 0.905, subtitle, fontsize=9.5, color="#444", ha="left")

    bx = [p[0] for p in d["boundary_xy"]] + [d["boundary_xy"][0][0]]
    by = [p[1] for p in d["boundary_xy"]] + [d["boundary_xy"][0][1]]
    ax.plot(bx, by, color="#999", lw=1.2, ls="--", label="search area")
    for i, s in enumerate(d.get("strips", []), start=1):
        sx = [p[0] for p in s] + [s[0][0]]
        sy = [p[1] for p in s] + [s[0][1]]
        ax.fill(sx, sy, color=COL[i], alpha=0.06)
        ax.plot(sx, sy, color=COL[i], lw=0.7, alpha=0.5)
    pads = d["pad_xy"]
    for i, p in enumerate(pads, start=1):
        ax.plot(p[0], p[1], marker="s", ms=5, color=COL[i], zorder=5)
    ax.set_aspect("equal")
    ax.set_xlabel("east (m)"); ax.set_ylabel("north (m)")
    ax.set_title("plan view", fontsize=10, loc="left")
    ax.grid(alpha=0.18)

    cx = sum(p[0] for p in pads) / len(pads)
    cy = sum(p[1] for p in pads) / len(pads)
    axp.add_patch(Rectangle((cx - PAD_SIDE / 2, cy - PAD_SIDE / 2),
                            PAD_SIDE, PAD_SIDE, fill=False, ec="#c00",
                            lw=1.6, ls="-"))
    axp.text(cx, cy + PAD_SIDE / 2 + 0.35, "12 ft pad (rule 8.10)",
             ha="center", fontsize=7.5, color="#c00")
    for i, p in enumerate(pads, start=1):
        axp.plot(p[0], p[1], marker="s", ms=4, color=COL[i], alpha=0.45)
    axp.set_xlim(cx - 4.2, cx + 4.2); axp.set_ylim(cy - 3.4, cy + 3.4)
    axp.set_aspect("equal")
    axp.set_title("the pad — 1.22 m slots, 1.046 m airframes", fontsize=9,
                  loc="left")
    axp.tick_params(labelsize=7)

    T = [tracks[1][k]["t"] for k in range(len(tracks[1]))]
    axa.set_xlim(0, T[-1]); axa.set_ylim(-2, 48)
    axa.set_ylabel("alt (m)", fontsize=8); axa.grid(alpha=0.18)
    axa.tick_params(labelsize=7)
    axa.set_title("altitude", fontsize=9, loc="left")
    for a in d.get("rtl_alt", []):
        axa.axhline(a, color="#bbb", lw=0.6, ls=":")

    axb.set_xlim(0, T[-1]); axb.grid(alpha=0.18)
    axb.set_ylabel("consumed (mAh)", fontsize=8); axb.tick_params(labelsize=7)
    axb.set_xlabel("wall-clock s", fontsize=8)
    axb.set_title("battery", fontsize=9, loc="left")
    axb.axhline(10800, color="#c00", lw=1.0, ls="--")
    axb.text(0.5, 10800, " BATT_LOW_MAH trip (20 % left)", fontsize=7,
             color="#c00", va="bottom")
    axb.set_ylim(0, 13500)

    axs.set_xlim(0, T[-1]); axs.set_ylim(0, 60)
    axs.set_ylabel("pairwise separation (m)", fontsize=8)
    axs.set_xlabel("wall-clock s", fontsize=8)
    axs.grid(alpha=0.18); axs.tick_params(labelsize=7)
    axs.set_title("3-D separation between aircraft", fontsize=9, loc="left")
    axs.axhline(5.0, color="#c00", lw=1.0, ls="--")
    axs.text(0.5, 5.2, " 5 m minimum", fontsize=7, color="#c00")

    trails = {i: ax.plot([], [], color=COL[i], lw=1.3, alpha=0.85)[0]
              for i in tracks}
    dots = {i: ax.plot([], [], marker="o", ms=7, color=COL[i],
                       mec="white", mew=1.1, zorder=6)[0] for i in tracks}
    pdots = {i: axp.plot([], [], marker="o", ms=9, color=COL[i], mec="white",
                         mew=1.1, zorder=6)[0] for i in tracks}
    prings = {i: axp.add_patch(Circle((0, 0), FOOTPRINT / 2, fill=False,
                                      ec=COL[i], lw=1.0, alpha=0.0))
              for i in tracks}
    alines = {i: axa.plot([], [], color=COL[i], lw=1.2)[0] for i in tracks}
    blines = {i: axb.plot([], [], color=COL[i], lw=1.2)[0] for i in tracks}
    pairs = [(1, 2), (1, 3), (2, 3)]
    slines = {p: axs.plot([], [], lw=1.1,
                          color=["#888", "#555", "#222"][k],
                          label=f"{p[0]}–{p[1]}")[0]
              for k, p in enumerate(pairs)}
    axs.legend(fontsize=7, loc="upper right")

    for i in tracks:
        ax.plot([], [], color=COL[i], lw=2, label=f"drone {i}")
    ax.legend(fontsize=8, loc="upper left")

    hud = ax.text(0.015, 0.985, "", transform=ax.transAxes, va="top",
                  fontsize=8.5, family="monospace",
                  bbox=dict(fc="white", ec="#ccc", alpha=0.9, pad=4))
    banner = fig.text(0.5, 0.015, "", ha="center", fontsize=11,
                      fontweight="bold", color="#c00")

    xs = {i: [] for i in tracks}
    ys = {i: [] for i in tracks}

    def sep(a, b, k):
        pa, pb = tracks[a][k], tracks[b][k]
        return ((pa["x"] - pb["x"]) ** 2 + (pa["y"] - pb["y"]) ** 2
                + (pa["alt"] - pb["alt"]) ** 2) ** 0.5

    seps = {p: [sep(p[0], p[1], k) for k in range(len(T))] for p in pairs}
    allx = [tracks[i][k]["x"] for i in tracks for k in range(len(T))]
    ally = [tracks[i][k]["y"] for i in tracks for k in range(len(T))]
    m = 40
    ax.set_xlim(min(allx) - m, max(allx) + m)
    ax.set_ylim(min(ally) - m, max(ally) + m)

    first_rtl = {}
    for i in tracks:
        for k in range(len(T)):
            if tracks[i][k]["mode"] in ("RTL", "LAND") and i not in first_rtl:
                first_rtl[i] = T[k]

    writer = PillowWriter(fps=fps)
    with writer.saving(fig, out, dpi=100):
        for fi, k in enumerate(frames):
            for i in tracks:
                s = tracks[i][k]
                xs[i].append(s["x"]); ys[i].append(s["y"])
                trails[i].set_data(xs[i], ys[i])
                dots[i].set_data([s["x"]], [s["y"]])
                near = abs(s["x"] - cx) < 6 and abs(s["y"] - cy) < 6
                pdots[i].set_data([s["x"]] if near else [],
                                  [s["y"]] if near else [])
                prings[i].set_center((s["x"], s["y"]))
                prings[i].set_alpha(0.75 if near else 0.0)
                kk = slice(0, k + 1)
                alines[i].set_data(T[kk], [tracks[i][j]["alt"]
                                           for j in range(k + 1)])
                blines[i].set_data(T[kk], [tracks[i][j]["mah"]
                                           for j in range(k + 1)])
            for p in pairs:
                slines[p].set_data(T[:k + 1], seps[p][:k + 1])

            rows = [f"t+{T[k]:6.1f}s   sim x{d['speedup']}"]
            for i in tracks:
                s = tracks[i][k]
                rows.append(f"d{i} {s['mode']:<7} {s['alt']:5.1f}m "
                            f"{s['mah']:6.0f}mAh")
            live = min(seps[p][k] for p in pairs)
            rows.append(f"closest pair  {live:5.1f} m")
            hud.set_text("\n".join(rows))

            msg = ""
            for i in tracks:
                if i in first_rtl and T[k] >= first_rtl[i]:
                    msg = "BATTERY FAILSAFE → RETURN TO PAD"
            if all(not tracks[i][k].get("armed", True) for i in tracks):
                msg = "ALL THREE DOWN — sequenced, no conflict"
            banner.set_text(msg)
            writer.grab_frame()
    plt.close(fig)
    print(f"wrote {out}  ({len(frames)} frames)")
    return seps, first_rtl


if __name__ == "__main__":
    src = sys.argv[1]
    out = sys.argv[2]
    title = sys.argv[3]
    sub = sys.argv[4]
    d = load(src)
    seps, rtl = render(d, out, title, sub)
    print("worst separation per pair:",
          {f"{a}-{b}": round(min(v), 2) for (a, b), v in seps.items()})
    print("first RTL/LAND per drone:", {k: round(v, 1) for k, v in rtl.items()})
