#!/usr/bin/env python3
"""Publication figures for the RescueSwarm funding proposal.

WHY THIS EXISTS
The proposal's rule is the repository's rule: every published number regenerates
from its source. These figures are therefore generated, not drawn by hand, and
every series carries a comment naming the file it came from. Re-run this script
after any model change and the proposal picks the new figures up on next build.

Output is vector PDF at exact IEEE column widths, so nothing is scaled, cropped
or resampled in the document.

Run:  python docs/proposal/figures/make_figures.py
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

OUT = os.path.dirname(os.path.abspath(__file__))

# IEEEtran geometry. Figures are produced at final size so \includegraphics
# never rescales them -- rescaling is how axis labels end up unreadable.
COL = 3.5      # single-column width, inches
FULL = 7.16    # two-column (\textwidth), inches

# Colour-blind-safe (Okabe--Ito). Used consistently across every figure.
BLUE, ORANGE, GREEN = "#0072B2", "#E69F00", "#009E73"
RED, PURPLE, GREY = "#D55E00", "#CC79A7", "#7F7F7F"
LIGHT = "#D9D9D9"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8.5,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.5,
    "figure.dpi": 200,
    "savefig.bbox": "tight",     # never clip a label
    "savefig.pad_inches": 0.02,
})


def inr(x, _=None):
    """Indian numbering: lakh = 1e5."""
    return f"{x/1e5:.2f}L"


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path)
    plt.close(fig)
    print(f"  wrote {name}")



def save_exact(fig, name):
    """Save at exactly figsize, so \includegraphics does not rescale.

    bbox_inches="tight" crops to the axes, which for an aspect-locked plot is
    narrower than the figure; LaTeX then scales the result up and every label
    with it. These figures are laid out by hand instead.
    """
    path = os.path.join(OUT, name)
    # bbox_inches=None falls back to rcParams["savefig.bbox"], which is
    # "tight" here -- so the crop has to be disabled in a context instead.
    with plt.rc_context({"savefig.bbox": None}):
        fig.savefig(path)
    plt.close(fig)
    print(f"  wrote {name}  (exact size)")

# ===========================================================================
# 1. Geolocation error budget.  Source: docs/sizing/geotag-accuracy-output.txt
# ===========================================================================
def fig_geotag():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(FULL, 2.5))

    # -- (a) single-frame error by GNSS fix quality, typical attitude -------
    fixes = ["RTK\nfixed", "RTK\nfloat", "3-D\nonly", "No\nfix"]
    cep = [0.80, 0.92, 3.08, 9.48]
    rss = [0.95, 1.10, 3.67, 11.30]
    x = np.arange(len(fixes))
    w = 0.38
    ax1.bar(x - w/2, cep, w, label="CEP50", color=BLUE)
    ax1.bar(x + w/2, rss, w, label="RSS", color=ORANGE)
    ax1.axhline(5.0, color=RED, ls="--", lw=1)
    ax1.text(-0.42, 5.9, "5 m delivery requirement", color=RED, fontsize=6.5,
             ha="left", va="bottom")
    ax1.set_yscale("log")
    ax1.set_xticks(x); ax1.set_xticklabels(fixes)
    ax1.set_ylabel("Horizontal error (m)")
    ax1.set_title("(a) Single-frame error by fix quality")
    ax1.legend(frameon=False, loc="upper left")
    for xi, v in zip(x, rss):
        ax1.text(xi + w/2, v * 1.10, f"{v:.2f}", ha="center", fontsize=6.3)
    ax1.set_ylim(0.4, 40)

    # -- (b) multi-frame fusion, RTK fixed, typical attitude ---------------
    n = np.array([1, 3, 5, 10, 20])
    cep_n = np.array([0.80, 0.59, 0.55, 0.50, 0.49])
    ax2.plot(n, cep_n, "o-", color=GREEN, lw=1.4, ms=4, label="Monte Carlo CEP50")
    ideal = cep_n[0] / np.sqrt(n)
    ax2.plot(n, ideal, "s--", color=GREY, lw=1.1, ms=3.4,
             label=r"ideal $1/\sqrt{n}$")
    # Frames available per pass, derived from the survey geometry rather than
    # written in. This marker previously read 14, which matched neither the
    # 40 m design point nor the 60 m altitude the caption cited.
    PX_H, PITCH_UM, F_MM = 3040, 1.55, 6.0        # Arducam IMX477, 6 mm lens
    H_SEARCH, V_GND = 40.0, 8.0                   # m AGL, m/s ground speed
    vfov = 2 * np.arctan((PX_H * PITCH_UM / 1000.0) / (2 * F_MM))
    dwell = 2 * H_SEARCH * np.tan(vfov / 2) / V_GND      # s a target is in view
    n_2hz, n_3hz = 2 * dwell, 3 * dwell                  # 7.9 and 11.8
    ax2.axvspan(n_2hz, n_3hz, color=BLUE, alpha=0.13, lw=0)
    ax2.axvline(n_2hz, color=BLUE, ls=":", lw=1)
    ax2.text(n_3hz + 0.5, 0.74,
             f"{n_2hz:.0f}--{n_3hz:.0f} frames per pass\n(2--3 Hz at 40 m)",
             fontsize=6.3, color=BLUE, va="top")
    ax2.set_xlabel("Frames fused per target")
    ax2.set_ylabel("CEP50 (m)")
    ax2.set_title("(b) Multi-frame fusion saturates")
    ax2.legend(frameon=False)
    ax2.set_xlim(0, 21); ax2.set_ylim(0.1, 0.95)

    fig.suptitle("")
    fig.tight_layout()
    save(fig, "fig-geotag.pdf")


# ===========================================================================
# 2. Mass budget.  Source: docs/sizing/model-output.txt
# ===========================================================================
def fig_mass():
    fig, ax = plt.subplots(figsize=(COL, 2.35))
    # The model's own mass statement lists 6,061 g against a 6,360 g MTOW.
    # The 299 g residual is shown rather than left for a reader to find by
    # adding the bars up.
    # Single-line tick labels. The two-line ones made the row pitch uneven and
    # crowded the axis; the qualifiers moved into the caption instead.
    items = ["Structure", "Battery pack", "Avionics", "Survivor kits",
             "Motors", "Unallocated", "Propellers", "Magazine", "ESCs"]
    g = [1495, 1449, 925, 800, 640, 299, 288, 240, 224]
    colours = [GREY, BLUE, PURPLE, GREEN, ORANGE, RED, ORANGE, GREEN, ORANGE]
    y = np.arange(len(items))[::-1]
    ax.barh(y, g, color=colours, height=0.68)
    for yi, v in zip(y, g):
        ax.text(v + 40, yi, f"{v} g  ({v/6360*100:.1f}%)", va="center", fontsize=6.6)
    ax.set_yticks(y); ax.set_yticklabels(items)
    ax.set_xlabel("Mass (g)")
    ax.set_xlim(0, 2050)
    ax.set_title(f"Mass budget, MTOW 6 360 g per aircraft")
    ax.grid(axis="y", alpha=0)
    fig.tight_layout()
    save(fig, "fig-mass.pdf")


# ===========================================================================
# 3. Cost options A--E.  Source: hardware/bom/RescueSwarm_Cost_Study.xlsx
# ===========================================================================
def fig_options():
    fig, ax = plt.subplots(figsize=(COL, 2.6))
    # Revised after review. Options are now ordered by WHAT THEY TRADE, and
    # three savings claimed in the first pass were withdrawn as unsound:
    # a motor price below the lowest listing, a non-compliant ESC, and a
    # sub-GHz radio outside the Indian band. See docs/proposal/README.md.
    opts = ["A\nverified", "B\nefficiency", "C\n+indig.\ntrade",
            "D\n+capability\ntrade", "E\ndifferent\naircraft"]
    cost = [290546, 263401, 237081, 157800, 37309]
    colours = [GREY, GREEN, BLUE, ORANGE, RED]
    x = np.arange(len(opts))
    bars = ax.bar(x, cost, color=colours, width=0.62)
    bars[3].set_edgecolor("black"); bars[3].set_linewidth(1.1)

    # Notes sit BELOW the axis, not inside the bars: at column width a bar is
    # narrower than the text, and text inside it gets clipped.
    notes = ["baseline", "nothing lost", "$-$Indian", "$-$margin", "cannot fly"]
    for xi, v, nt in zip(x, cost, notes):
        ax.text(xi, v + 9000, f"{v/1e5:.2f}L", ha="center", fontsize=7, weight="bold")
        ax.annotate(nt, xy=(xi, 0), xytext=(0, -30), textcoords="offset points",
                    ha="center", va="top", fontsize=6.3, color=GREY)
    ax.set_xticks(x); ax.set_xticklabels(opts)
    ax.yaxis.set_major_formatter(FuncFormatter(inr))
    ax.set_ylabel("Cost per aircraft (INR)")
    ax.set_ylim(0, 340000)
    ax.set_title("Costed configurations of the same mission")
    ax.grid(axis="x", alpha=0)
    fig.tight_layout()
    save(fig, "fig-options.pdf")


# ===========================================================================
# 4. Cost by subsystem, A vs B.  Source: the verified BOM, tab 01.
# ===========================================================================
def fig_subsystem():
    fig, ax = plt.subplots(figsize=(COL, 2.5))
    subs = ["Avionics", "Compute &\nperception", "Propulsion", "Power",
            "Structure", "Comms", "Payload"]
    # A (fully specified) against D (adopted), from competition_budget.py.
    a = [85400, 79500, 57396, 24500, 20550, 17800, 5400]
    b = [49100, 31100, 30600, 23500, 13000,  6000, 4500]
    y = np.arange(len(subs))[::-1]
    h = 0.36
    ax.barh(y + h/2, a, h, label="A (as verified)", color=LIGHT, edgecolor=GREY, lw=0.5)
    ax.barh(y - h/2, b, h, label="D (adopted)", color=GREEN)
    for yi, va, vb in zip(y, a, b):
        d = vb - va
        if d:
            ax.text(max(va, vb) + 2500, yi - h/2,
                    f"{'+' if d > 0 else '−'}{abs(d)/1000:.1f}k",
                    va="center", fontsize=6.3,
                    color=RED if d > 0 else GREEN)
    ax.set_yticks(y); ax.set_yticklabels(subs)
    ax.set_xlabel("Cost per aircraft (INR)")
    ax.xaxis.set_major_formatter(FuncFormatter(inr))
    ax.set_xlim(0, 108000)
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("Where the saving comes from")
    ax.grid(axis="y", alpha=0)
    fig.tight_layout()
    save(fig, "fig-subsystem.pdf")


# ===========================================================================
# 5. Phased funding.  Source: Section on phased disbursement.
# ===========================================================================
def fig_funding():
    fig, ax = plt.subplots(figsize=(FULL, 2.6))
    tranches = ["T1\nmonths 1–2", "T2\nmonths 3–4",
                "T3\nmonths 5–6", "T4\nmonths 7–8"]
    # Competition build, not the development programme.
    # Source: figures/competition_budget.py
    amounts = np.array([2.90, 2.45, 1.75, 1.14])       # INR lakh
    phases = ["P1–P4\nanalysis, ground segment,\nautonomy, long-lead order",
              "P5\nairframe build,\nground segment",
              "P6–P8\nfirst flight, perception\nand delivery trials",
              "P9–P10\nfull rehearsal,\nsetup drills, contingency"]
    x = np.arange(len(tranches))
    cols = [BLUE, ORANGE, GREEN, PURPLE]
    # Black on the light orange, white on the three dark fills -- white on
    # #E69F00 does not carry in print.
    txtc = ["white", "black", "white", "white"]
    ax.bar(x, amounts, color=cols, width=0.6)
    for xi, v, p, tc in zip(x, amounts, phases, txtc):
        ax.text(xi, v + 0.25, f"{v:.2f} L", ha="center", fontsize=7.5, weight="bold")
        ax.text(xi, 0.35, p, ha="center", va="bottom", fontsize=6.0, color=tc)
    ax.set_xticks(x); ax.set_xticklabels(tranches)
    ax.set_ylabel("Tranche (INR lakh)")
    ax.set_ylim(0, 4.0)
    ax.grid(axis="x", alpha=0)

    ax2 = ax.twinx()
    cum = np.cumsum(amounts)
    ax2.plot(x, cum, "o-", color=RED, lw=1.6, ms=5, label="cumulative")
    # Offset in points, above-left of each marker, so labels clear both the
    # line and the bar tops.
    for xi, c in zip(x, cum):
        ax2.annotate(f"{c:.2f} L", xy=(xi, c), xytext=(-4, 9),
                     textcoords="offset points", fontsize=6.8, color=RED,
                     ha="right", weight="bold")
    ax2.set_ylabel("Cumulative disbursement (INR lakh)", color=RED)
    ax2.tick_params(axis="y", colors=RED)
    ax2.set_ylim(0, 10)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(RED)

    ax.set_title("Phased disbursement: no tranche released before its "
                 "predecessor's exit criterion is met")
    fig.tight_layout()
    save(fig, "fig-funding.pdf")


# ===========================================================================
# 6. Indigenisation by subsystem.  Source: verified BOM declared fractions.
# ===========================================================================
def fig_indig():
    fig, ax = plt.subplots(figsize=(COL, 2.4))
    # ADOPTED configuration. Propulsion falls 89% -> 21% and avionics
    # 60% -> 32%: the generic motors and imported autopilot are exactly
    # what make this configuration affordable.
    subs = ["Payload", "Structure", "Power", "Avionics",
            "Comms", "Propulsion", "Compute &\nperception"]
    frac = [90.0, 85.0, 60.0, 32.0, 30.0, 21.0, 10.0]
    val = [4500, 13000, 23500, 49100, 6000, 30600, 31100]
    y = np.arange(len(subs))[::-1]
    cols = [GREEN if f >= 70 else (ORANGE if f >= 50 else RED) for f in frac]
    ax.barh(y, frac, color=cols, height=0.66)
    # Cost per subsystem was annotated inside each bar. It is dropped because
    # the master proposal no longer carries funding content -- that lives in the
    # track work packages now. `val` is retained: it still orders the bars by
    # value weight, which is what makes the mean a weighted one.
    for yi, f in zip(y, frac):
        ax.text(f + 1.5, yi, f"{f:.0f}%", va="center", fontsize=6.8)
    ax.axvline(35.5, color="black", ls="--", lw=1)
    # Above the plot area, not rotated across the bars -- a vertical label here
    # sits on top of the Power and Comms rows and becomes unreadable.
    ax.annotate("adopted mean 36%", xy=(35.5, len(subs) - 0.45),
                xytext=(4, 0), textcoords="offset points",
                fontsize=6.3, ha="left", va="center")
    ax.set_yticks(y); ax.set_yticklabels(subs)
    ax.set_xlabel("Indian content, value-weighted (%)")
    ax.set_xlim(0, 108)
    ax.set_ylim(-0.7, len(subs) - 0.05)
    ax.set_title("Indigenous content by subsystem, as adopted")
    ax.grid(axis="y", alpha=0)
    fig.tight_layout()
    save(fig, "fig-indig.pdf")


# ===========================================================================
# 7-8. SITL evidence, re-rendered for publication.
#      Source: simulations/recordings/*.json -- the same telemetry the
#      committed proof figures use. Prose lives in the LaTeX caption, not in
#      the image.
# ===========================================================================
import bisect
import json
import math

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(OUT))),
                   "simulations", "recordings")
AIRFRAME = 1.046          # m, tip-to-tip; the separation floor that matters
PAD = 3.66                # m, 12 ft launch/recovery box


def _load(name):
    with open(os.path.join(REC, name), encoding="utf-8") as f:
        return json.load(f)


def _at(track, t):
    ts = [q["t"] for q in track]
    i = bisect.bisect_left(ts, t)
    return track[min(max(i, 0), len(track) - 1)]


def _min_sep(d, t, airborne_only=True):
    """Closest pair at time t, in three dimensions."""
    ids = sorted(d["tracks"])
    best = None
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            p1 = _at(d["tracks"][ids[a]], t)
            p2 = _at(d["tracks"][ids[b]], t)
            if airborne_only and (p1["alt"] < 2.0 or p2["alt"] < 2.0):
                continue
            sep = math.dist((p1["x"], p1["y"], p1["alt"]),
                            (p2["x"], p2["y"], p2["alt"]))
            best = sep if best is None else min(best, sep)
    return best


def fig_launch():
    before = _load("mission-telemetry-before-fixes.json")
    after = _load("mission-telemetry.json")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(FULL, 2.45))

    # -- (a) closest airborne pair, both runs ------------------------------
    grid = [i * 0.25 for i in range(0, 241)]          # first 60 s
    for d, col, lab in ((before, RED, "simultaneous launch"),
                        (after, GREEN, "staggered launch")):
        xs, ys = [], []
        for t in grid:
            v = _min_sep(d, t)
            if v is not None:
                xs.append(t); ys.append(v)
        ax1.plot(xs, ys, color=col, lw=1.5, label=lab)
        lo = min(range(len(ys)), key=lambda i: ys[i])
        ax1.plot(xs[lo], ys[lo], "o", color=col, ms=5)
        ax1.annotate(f"{ys[lo]:.2f} m", xy=(xs[lo], ys[lo]),
                     xytext=(10, 14 if col == GREEN else 10),
                     textcoords="offset points", fontsize=7.5,
                     color=col, weight="bold")
    ax1.axhline(AIRFRAME, color=GREY, ls="--", lw=1)
    ax1.text(2, AIRFRAME * 0.62, "one airframe width, 1.046 m",
             fontsize=6.3, color=GREY, ha="left")
    ax1.set_yscale("log")
    ax1.set_xlabel("Time since mission start (s)")
    ax1.set_ylabel("Closest pair, 3-D (m)")
    ax1.set_title("(a) Separation during launch")
    ax1.legend(frameon=False, loc="upper center", ncol=1)
    ax1.set_xlim(0, 60)
    ax1.set_ylim(0.45, 900)

    # -- (b) the mechanism: altitude stagger -------------------------------
    # OBSERVED lift-off, not commanded. The mission file sets NAV_DELAY to
    # 0/15/30 s; the telemetry shows the aircraft leaving the pad at
    # 0.00/3.50/10.01 s. Plotting the commanded values would assert something
    # this recording does not support -- see docs/proposal/README.md.
    for i, k in enumerate(sorted(after["tracks"])):
        tr = after["tracks"][k]
        t = [q["t"] for q in tr if q["t"] <= 60]
        a = [q["alt"] for q in tr if q["t"] <= 60]
        col = [BLUE, ORANGE, PURPLE][i]
        ax2.plot(t, a, color=col, lw=1.3, label=f"aircraft {k}")
        lift = next((q["t"] for q in tr if q["alt"] > 2.0), None)
        if lift is not None:
            ax2.axvline(lift, color=col, ls=":", lw=0.9)
            ax2.annotate(f"{lift:.1f} s", xy=(lift, 46.5 - 3.4 * i),
                         fontsize=6.5, color=col, ha="left", va="center",
                         xytext=(3, 0), textcoords="offset points")
    ax2.set_xlabel("Time since mission start (s)")
    ax2.set_ylabel("Altitude AGL (m)")
    ax2.set_title("(b) Observed lift-off, staggered by mission file")
    ax2.legend(frameon=False, loc="lower right")
    ax2.set_xlim(0, 60)
    ax2.set_ylim(0, 50)

    fig.tight_layout()
    save(fig, "fig-launch.pdf")


def fig_pad():
    before = _load("mission-telemetry-before-fixes.json")
    after = _load("mission-telemetry.json")
    fig, ax = plt.subplots(figsize=(COL, 3.60))
    fig.subplots_adjust(left=0.175, right=0.985, top=0.925, bottom=0.20)

    # Pad centre from the BOUNDING BOX of the slots, not their centroid: for
    # three of four corners the centroid sits 0.436 m off. Cross-checked below
    # against the row run, whose slots all lie on the pad centre line.
    xs = [q[0] for q in after["pad_xy"]]
    ys = [q[1] for q in after["pad_xy"]]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    assert abs(cy - before["pad_xy"][0][1]) < 1e-6, "pad centre disagrees with the row run"

    h = PAD / 2
    r = AIRFRAME / 2
    ax.add_patch(plt.Rectangle((cx - h, cy - h), PAD, PAD, fill=False,
                               ec=RED, lw=1.5, zorder=4))
    ax.text(cx + h, cy + h + 0.10, "3.66 m × 3.66 m pad", color=RED,
            fontsize=7, ha="right", va="bottom")

    # The square slot centres must stay inside if no airframe is to overhang.
    ax.add_patch(plt.Rectangle((cx - h + r, cy - h + r), PAD - 2 * r,
                               PAD - 2 * r, fill=False, ec=GREY, ls=":",
                               lw=1, zorder=4))
    ax.text(cx - h + r + 0.06, cy - h + r + 0.06,
            "slot centres must stay inside", fontsize=6.1, color=GREY)

    for pts, col, mk, lab in ((before["pad_xy"], GREY, "s", "row of three"),
                              (after["pad_xy"], GREEN, "o", "corner slots")):
        ax.plot([q[0] for q in pts], [q[1] for q in pts], mk, color=col, ms=6,
                ls="none", label=lab, mfc="none" if col == GREY else col,
                mew=1.4, zorder=5)
        if col == GREEN:
            for x, y in pts:
                ax.add_patch(plt.Circle((x, y), r, color=col, alpha=0.18, lw=0))

    def closest(pts):
        return min(math.dist(pts[i], pts[j])
                   for i in range(len(pts)) for j in range(i + 1, len(pts)))

    cb, ca = closest(before["pad_xy"]), closest(after["pad_xy"])
    a0, a1 = after["pad_xy"][1], after["pad_xy"][2]
    ax.annotate("", xy=a0, xytext=a1,
                arrowprops=dict(arrowstyle="<->", color=GREEN, lw=1.3))
    ax.text((a0[0] + a1[0]) / 2 + 0.10, (a0[1] + a1[1]) / 2, f"{ca:.2f} m",
            color=GREEN, fontsize=8, weight="bold", ha="left", va="center")

    b0, b1 = before["pad_xy"][0], before["pad_xy"][1]
    ax.annotate("", xy=b0, xytext=b1,
                arrowprops=dict(arrowstyle="<->", color=GREY, lw=1.1))
    ax.text((b0[0] + b1[0]) / 2, b1[1] + 0.13, f"{cb:.2f} m", color=GREY,
            fontsize=7.5, ha="center", va="bottom")

    # Answer the question the figure exists to answer, numerically.
    margin = min(min(h - abs(x - cx), h - abs(y - cy)) for x, y in after["pad_xy"])
    ax.text(0.5, -0.285,
            f"worst edge clearance {margin:.3f} m = exactly one airframe radius:\n"
            f"no overhang at the nominal slot, and no margin beyond it",
            transform=ax.transAxes, ha="center", fontsize=6.6)

    ax.set_xlabel("East (m)")
    ax.set_ylabel("North (m)")
    ax.set_title("Recovery slot geometry, same pad")
    ax.set_aspect("equal")
    ax.set_xlim(cx - h - 0.75, cx + h + 0.75)
    ax.set_ylim(cy - h - 0.75, cy + h + 0.85)
    ax.legend(frameon=False, loc="lower left", fontsize=6.8,
              handletextpad=0.4, borderaxespad=0.2)
    save_exact(fig, "fig-pad.pdf")


# ===========================================================================
# 9. Coverage decomposition and return geometry.
#    Source: simulations/recordings/mission-telemetry.json
# ===========================================================================
def fig_sweep():
    d = _load("mission-telemetry.json")
    fig, ax = plt.subplots(figsize=(COL, 5.05))
    fig.subplots_adjust(left=0.20, right=0.98, top=0.945, bottom=0.135)

    pad = d["pad_xy"]
    cx = sum(q[0] for q in pad) / 3
    cy = sum(q[1] for q in pad) / 3

    bx = [q[0] for q in d["boundary_xy"]] + [d["boundary_xy"][0][0]]
    by = [q[1] for q in d["boundary_xy"]] + [d["boundary_xy"][0][1]]
    ax.plot(bx, by, color=GREY, ls="--", lw=1, label="search area")

    cols = [BLUE, ORANGE, PURPLE]
    for i, strip in enumerate(d["strips"]):
        xs = [q[0] for q in strip] + [strip[0][0]]
        ys = [q[1] for q in strip] + [strip[0][1]]
        ax.fill(xs, ys, color=cols[i], alpha=0.07, lw=0)

    for i, k in enumerate(sorted(d["tracks"])):
        tr = [q for q in d["tracks"][k] if q["alt"] > 5]
        ax.plot([q["x"] for q in tr], [q["y"] for q in tr],
                color=cols[i], lw=0.9, label=f"aircraft {k}")

    ax.plot(cx, cy, "s", color="black", ms=6, zorder=5)
    ax.annotate("pad", xy=(cx, cy), xytext=(11, -3),
                textcoords="offset points", fontsize=7, weight="bold",
                va="center")

    # The argument this figure exists to make: the sweep direction is chosen so
    # every aircraft finishes NEAR HOME, on the lowest state of charge of the
    # flight. Measure that at the end of the SWEEP -- the last sample inside the
    # search boundary -- not at the end of the track, which is back at the pad.
    ymin = min(q[1] for q in d["boundary_xy"])
    ymax = max(q[1] for q in d["boundary_xy"])
    ends = []
    for k in sorted(d["tracks"]):
        inside = [q for q in d["tracks"][k]
                  if q["alt"] > 20 and ymin <= q["y"] <= ymax]
        if inside:
            last = inside[-1]
            r = math.hypot(last["x"] - cx, last["y"] - cy)
            ends.append(r)
            ax.plot(last["x"], last["y"], "*", color="black", ms=8, zorder=6)
    ax.text(0.5, -0.30,
            f"sweeps finish {min(ends):.0f}–{max(ends):.0f} m from the pad "
            f"(stars)",
            transform=ax.transAxes, ha="center", fontsize=7, weight="bold")

    ax.set_xlabel("East (m)")
    ax.set_ylabel("North (m)")
    ax.set_title("Coverage decomposition and return")
    ax.set_aspect("equal")
    ax.set_xlim(-190, 190)
    ax.set_ylim(-340, 220)
    ax.legend(frameon=False, fontsize=6.4, loc="upper center", ncol=2,
              handletextpad=0.4, borderaxespad=0.1,
              bbox_to_anchor=(0.5, 1.0))
    save_exact(fig, "fig-sweep.pdf")


if __name__ == "__main__":
    print("Generating proposal figures...")
    fig_geotag()
    fig_mass()
    fig_options()
    fig_subsystem()
    fig_funding()
    fig_indig()
    fig_launch()
    fig_pad()
    fig_sweep()
    print("Done.")
