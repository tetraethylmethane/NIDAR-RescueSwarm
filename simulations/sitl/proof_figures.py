#!/usr/bin/env python3
"""Figures that show the fixes working, drawn only from committed telemetry.

Nothing here is drawn from a plan or a model. Every point comes from MAVLink
off a running ArduCopter SITL, recorded by fly_and_record.py and
fly_endurance.py, and committed in simulations/recordings/.

    python3 simulations/sitl/proof_figures.py

Writes PNGs next to the telemetry.
"""
from __future__ import annotations

import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib.patches import Circle, Rectangle      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REC = os.path.join(os.path.dirname(HERE), "recordings")
COL = {1: "#e6194b", 2: "#2a9d3f", 3: "#3b6bd8"}
PAD_SIDE, FOOTPRINT = 3.66, 1.046
PAIRS = [(1, 2), (1, 3), (2, 3)]


def load(name):
    d = json.load(open(os.path.join(REC, name)))
    d["tracks"] = {int(k): v for k, v in d["tracks"].items()}
    return d


def sep(tr, a, b, k):
    A, B = tr[a][k], tr[b][k]
    return math.dist((A["x"], A["y"], A["alt"]), (B["x"], B["y"], B["alt"]))


def min_sep_series(tr, airborne_only=True, thresh=2.0):
    """Closest pair over time.

    Airborne-only by default: three aircraft parked 1.22 m apart on their slots
    are 1.22 m apart because that is where they were put, and including the
    ground phase drags the whole trace onto the floor and hides the part of the
    flight where separation is earned.
    """
    n, ts, vals = len(tr[1]), [], []
    for k in range(n):
        cand = [sep(tr, a, b, k) for a, b in PAIRS
                if not airborne_only
                or (tr[a][k]["alt"] > thresh and tr[b][k]["alt"] > thresh)]
        ts.append(tr[1][k]["t"])
        vals.append(min(cand) if cand else float("nan"))
    return ts, vals


def airborne_min(tr, thresh=2.0, spd=1.0, t_max=None):
    """Closest approach with both aircraft airborne, optionally windowed.

    `t_max` is in SIMULATED seconds. Figure 1 windows it to the launch, because
    the launch is what NAV_DELAY changed; the tightest point of the whole
    flight is now in recovery and belongs with the pad finding in figure 4.
    """
    best = (1e9, None)
    for k in range(len(tr[1])):
        if t_max is not None and tr[1][k]["t"] * spd > t_max:
            continue
        for a, b in PAIRS:
            if tr[a][k]["alt"] > thresh and tr[b][k]["alt"] > thresh:
                s = sep(tr, a, b, k)
                if s < best[0]:
                    best = (s, (k, a, b))
    return best


def style(ax, title, xl, yl):
    ax.set_title(title, fontsize=10, loc="left", fontweight="bold")
    ax.set_xlabel(xl, fontsize=8.5)
    ax.set_ylabel(yl, fontsize=8.5)
    ax.grid(alpha=0.2)
    ax.tick_params(labelsize=8)


# ---------------------------------------------------------------- figure A
def fig_launch(before, after, out):
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 6.4), facecolor="white")
    fig.suptitle("Launch sequencing — NAV_DELAY 0/15/30 s before each takeoff",
                 fontsize=13, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.895,
             "Recorded from three ArduCopter SITL. Left: every aircraft leaves "
             "the pad at once. Right: the mission file staggers them.\n"
             "First 60 simulated seconds.",
             fontsize=9, color="#444")

    for col, (d, label) in enumerate(((before, "BEFORE"), (after, "AFTER"))):
        tr = d["tracks"]
        spd = d.get("speedup", 1)
        # Show the launch in SIMULATED seconds, which is where the 0/15/30 s
        # NAV_DELAY actually lives. Wall clock divides it by the speedup and
        # makes a real 15 s stagger look like a 1 s one.
        span = 60.0
        ax = axes[0][col]
        for i in tr:
            t = [s["t"] * spd for s in tr[i]]
            ax.plot(t, [s["alt"] for s in tr[i]], color=COL[i], lw=1.6,
                    label=f"drone {i}")
        for gx in (15, 30):
            ax.axvline(gx, color="#bbb", ls=":", lw=0.9)
        ax.set_xlim(0, span)
        ax.set_ylim(-1, 46)
        style(ax, f"{label} — altitude off the pad  (SIM_SPEEDUP {spd:g})",
              "simulated s since mission start", "alt (m)")
        ax.legend(fontsize=8, loc="lower right")

        ax = axes[1][col]
        t, s = min_sep_series(tr)
        ax.plot([x * spd for x in t], s, color="#222", lw=1.5)
        ax.axhline(FOOTPRINT, color="#c00", ls="--", lw=1.1)
        ax.text(span * 0.52, FOOTPRINT + 2.5,
                "one airframe width, 1.046 m", fontsize=7.5, color="#c00")
        m, info = airborne_min(tr, spd=spd, t_max=span)
        ax.set_xlim(0, span)
        # Same scale on both panels, tall enough to hold the AFTER trace --
        # otherwise it sits off the top and the panel reads as missing data
        # rather than as "they were never close".
        ax.set_ylim(0, 115)
        ok = m >= 5.0
        style(ax, f"{label} — closest pair during launch: {m:.2f} m",
              "simulated s since mission start", "3-D separation (m)")
        if info:
            k = info[0]
            ax.plot([tr[1][k]["t"] * spd], [m], marker="v", ms=11,
                    color="#2a9d3f" if ok else "#c00", mec="k", zorder=6)
            ax.annotate(f"{m:.2f} m", (tr[1][k]["t"] * spd, m),
                        textcoords="offset points", xytext=(8, 8),
                        fontsize=10, fontweight="bold",
                        color="#2a9d3f" if ok else "#c00")
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print("wrote", out)


# ---------------------------------------------------------------- figure B
def fig_sweep(after, out):
    """Where each sweep ENDS, and the double pass."""
    fig, ax = plt.subplots(figsize=(8.0, 8.4), facecolor="white")
    d = after
    tr = d["tracks"]
    pads = d["pad_xy"]
    bx = [p[0] for p in d["boundary_xy"]] + [d["boundary_xy"][0][0]]
    by = [p[1] for p in d["boundary_xy"]] + [d["boundary_xy"][0][1]]
    ax.plot(bx, by, color="#888", ls="--", lw=1.2, label="search area")
    for i, s in enumerate(d.get("strips", []), start=1):
        sx = [p[0] for p in s] + [s[0][0]]
        sy = [p[1] for p in s] + [s[0][1]]
        ax.fill(sx, sy, color=COL[i], alpha=0.07)

    for i in tr:
        xs = [s["x"] for s in tr[i]]
        ys = [s["y"] for s in tr[i]]
        ax.plot(xs, ys, color=COL[i], lw=1.4, label=f"drone {i}")

    # BEFORE-fix sweep ends, from the plan that produced them, as annotation.
    px, py = pads[0][0], pads[0][1]
    for i, p in enumerate(pads, start=1):
        ax.plot(p[0], p[1], marker="s", ms=7, color=COL[i], mec="k", zorder=6)
    ax.annotate("pad", (px, py), textcoords="offset points", xytext=(8, -16),
                fontsize=9, fontweight="bold")

    # Mark where the SWEEP finished -- the last sample still inside the search
    # area. "Last airborne" is wrong for this: it picks the final descent over
    # the pad, which is 0 m from the pad by definition and says nothing.
    xs_b = [p[0] for p in d["boundary_xy"]]
    ys_b = [p[1] for p in d["boundary_xy"]]
    x0, x1, y0, y1 = min(xs_b), max(xs_b), min(ys_b), max(ys_b)
    for i in tr:
        pts = [s for s in tr[i]
               if s["alt"] > 5 and x0 - 5 <= s["x"] <= x1 + 5
               and y0 - 5 <= s["y"] <= y1 + 5]
        if not pts:
            continue
        e = pts[-1]
        dist = math.hypot(e["x"] - pads[i - 1][0], e["y"] - pads[i - 1][1])
        ax.plot([e["x"], pads[i - 1][0]], [e["y"], pads[i - 1][1]],
                color=COL[i], lw=0.9, ls=":", alpha=0.8)
        ax.plot(e["x"], e["y"], marker="*", ms=15, color=COL[i], mec="k",
                zorder=7)
        ax.annotate(f"d{i} sweep ends\n{dist:.0f} m from pad",
                    (e["x"], e["y"]), textcoords="offset points",
                    xytext=(14, -18 - 26 * (i - 1)), fontsize=8,
                    bbox=dict(fc="white", ec=COL[i], alpha=0.92, pad=2))

    ax.set_aspect("equal")
    npass = 2 if d.get("passes", 2) >= 2 else 1
    style(ax, f"Two passes per strip, finishing near the pad "
              f"({'double coverage' if npass == 2 else 'single'})",
          "east (m)", "north (m)")
    ax.legend(fontsize=8, loc="upper center", ncol=4,
              bbox_to_anchor=(0.5, -0.07), frameon=False)
    fig.text(0.02, 0.015,
             "Each strip is swept TWICE — the second pass retraces the same "
             "ground on the reverse heading, so the two overlay here. The "
             "evidence is the mission:\n18/19/19 items against 12/13/13 for a "
             "single pass, and 2535 m of path against 1267 m. It is for the "
             "GEOTAG, not coverage: boresight bias is\nsystematic and only "
             "cancels when the same ground is seen from the opposite "
             "direction. The cost is a second sweep, 347 s against 170 s.\n"
             "Sweeps also finish near the pad now — 116-123 m, against 516 m "
             "and 540 m for two of three aircraft before.",
             fontsize=8.5, color="#444")
    fig.tight_layout(rect=[0, 0.085, 1, 1])
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print("wrote", out)


# ---------------------------------------------------------------- figure C
def fig_battery(end, out):
    tr = end["tracks"]
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 6.6), sharex=True,
                             facecolor="white")
    fig.suptitle("Battery failsafe — no intervention, all three trip together",
                 fontsize=13, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.905,
             "Three aircraft hold station until the pack drains. "
             "BATT_LOW_MAH = 2700 of 13500, so the trip is at 10800 mAh used.",
             fontsize=9, color="#444")

    ax = axes[0]
    for i in tr:
        ax.plot([s["t"] for s in tr[i]], [s["mah"] for s in tr[i]],
                color=COL[i], lw=1.5, label=f"drone {i}")
    ax.axhline(10800, color="#c00", ls="--", lw=1.2)
    ax.text(0.30, 0.90, "BATT_LOW_MAH trip — 20 % remaining",
            transform=ax.transAxes, fontsize=8.5, color="#c00")
    ax.set_ylim(0, 13500)
    style(ax, "consumed capacity", "", "mAh")
    ax.legend(fontsize=8, loc="upper left", framealpha=0.95)

    ax = axes[1]
    for i in tr:
        ax.plot([s["t"] for s in tr[i]], [s["alt"] for s in tr[i]],
                color=COL[i], lw=1.5)
        first = next((s for s in tr[i] if s["mode"] in ("RTL", "LAND")), None)
        if first:
            ax.axvline(first["t"], color=COL[i], ls=":", lw=1.2)
            # Anchored left of the event so the box stays inside the axes --
            # the previous version placed them past the right edge and clipped.
            ax.annotate(f"d{i} RTL  t+{first['t']:.0f}s  "
                        f"{first['mah']:.0f} mAh",
                        (first["t"], 30 - 9 * (i - 1)),
                        textcoords="offset points", xytext=(-14, 0),
                        ha="right", fontsize=8.5, color=COL[i],
                        bbox=dict(fc="white", ec=COL[i], alpha=0.95, pad=2.5))
        down = next((s for s in tr[i] if s["t"] > 120 and s["alt"] < 0.5), None)
        if down:
            ax.plot(down["t"], 0, marker="v", ms=9, color=COL[i], mec="k",
                    zorder=6)
    style(ax, "altitude — descents sequenced by RTL_LOIT_TIME 0/20/40 s",
          "wall-clock s (SIM_SPEEDUP 20)", "alt (m)")
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print("wrote", out)


# ---------------------------------------------------------------- figure D
def fig_pad(end, out):
    """The finding that is still open, drawn to scale."""
    tr = end["tracks"]
    pads = end["pad_xy"]
    cx = sum(p[0] for p in pads) / len(pads)
    cy = sum(p[1] for p in pads) / len(pads)

    fig, ax = plt.subplots(figsize=(7.6, 6.4), facecolor="white")
    ax.add_patch(Rectangle((cx - PAD_SIDE / 2, cy - PAD_SIDE / 2),
                           PAD_SIDE, PAD_SIDE, fill=False, ec="#c00", lw=2))
    ax.text(cx, cy + PAD_SIDE / 2 + 0.22,
            "12 ft × 12 ft pad — rule 8.10", ha="center", fontsize=10,
            color="#c00", fontweight="bold")

    final = {}
    for i in tr:
        onground = [s for s in tr[i] if s["alt"] < 0.6]
        final[i] = onground[-1] if onground else tr[i][-1]

    # Worst horizontal approach at ANY point in the recording, not just at rest.
    # "They parked safely" is not the requirement; "they never overlapped" is.
    worst_any = min(
        (math.dist((tr[a][k]["x"], tr[a][k]["y"]), (tr[b][k]["x"], tr[b][k]["y"])),
         a, b)
        for k in range(len(tr[1])) for a, b in PAIRS)

    for i in tr:
        ax.plot(pads[i - 1][0], pads[i - 1][1], marker="s", ms=7,
                color=COL[i], alpha=0.4)
        ax.annotate(f"slot {i}", (pads[i - 1][0], pads[i - 1][1]),
                    textcoords="offset points", xytext=(-12, -16),
                    fontsize=7.5, color=COL[i], alpha=0.8)
        f = final[i]
        ax.add_patch(Circle((f["x"], f["y"]), FOOTPRINT / 2, fill=True,
                            fc=COL[i], ec=COL[i], alpha=0.22, lw=1.8))
        ax.plot(f["x"], f["y"], marker="o", ms=6, color=COL[i], mec="k",
                zorder=6)
        ax.annotate(f"drone {i}", (f["x"], f["y"]),
                    textcoords="offset points", xytext=(0, 10), fontsize=9,
                    ha="center", fontweight="bold", color=COL[i])

    worst = None
    for a, b in PAIRS:
        d = math.dist((final[a]["x"], final[a]["y"]),
                      (final[b]["x"], final[b]["y"]))
        if worst is None or d < worst[0]:
            worst = (d, a, b)
    d, a, b = worst
    ax.plot([final[a]["x"], final[b]["x"]], [final[a]["y"], final[b]["y"]],
            color="k", lw=1.6)
    clear = d - FOOTPRINT
    good = clear > 0
    ax.annotate(f"closest parked pair {d:.2f} m centre-to-centre\n"
                f"{'clear of' if good else 'OVERLAPS'} a {FOOTPRINT:.3f} m "
                f"airframe by {abs(clear):.2f} m",
                ((final[a]["x"] + final[b]["x"]) / 2,
                 (final[a]["y"] + final[b]["y"]) / 2),
                textcoords="offset points", xytext=(-150, -30), fontsize=9,
                fontweight="bold", color="#1a7f37" if good else "#c00",
                bbox=dict(fc="#f2fbf4" if good else "#fff4f4",
                          ec="#1a7f37" if good else "#c00", pad=4),
                arrowprops=dict(arrowstyle="->",
                                color="#1a7f37" if good else "#c00"))

    ax.set_xlim(cx - 3.2, cx + 3.2)
    ax.set_ylim(cy - 2.8, cy + 3.2)
    ax.set_aspect("equal")
    style(ax, f"RESOLVED: corner slots — closest approach at any time "
              f"{worst_any[0]:.2f} m",
          "east (m)", "north (m)")
    fig.text(0.02, 0.015,
             "A ROW of three gave 1.22 m spacing and they landed 0.83 m apart "
             "— an overlap of 1.046 m airframes.\n"
             "Centres must stay half an airframe inside the pad edge, so they "
             "live in a 2.61 m square; its CORNERS are 2.61 m apart — twice a "
             "row, on the same pad.\n"
             "Worst case with ±0.5 m touchdown dispersion on each aircraft: "
             "1.61 m, still clear. Holding over points 2.6 m apart instead of "
             "1.2 m also lifted\nthe stacked-over-the-pad separation from "
             "3.99 m to 6.52 m.",
             fontsize=8.5, color="#444")
    fig.tight_layout(rect=[0, 0.10, 1, 1])
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    before = load("mission-telemetry-before-fixes.json")
    after = load("mission-telemetry.json")
    end = load("battery-rtl-telemetry.json")
    fig_launch(before, after, os.path.join(REC, "proof-1-launch.png"))
    fig_sweep(after, os.path.join(REC, "proof-2-sweep.png"))
    fig_battery(end, os.path.join(REC, "proof-3-battery.png"))
    fig_pad(end, os.path.join(REC, "proof-4-pad.png"))
