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
    ax2.axvline(14, color=BLUE, ls=":", lw=1)
    ax2.text(14.4, 0.74, "~14 frames\navailable per pass", fontsize=6.3,
             color=BLUE, va="top")
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
    items = ["Structure", "Battery pack", "Avionics\n+ harness",
             "Survivor kits", "Motors", "Propellers", "Magazine\n+ release", "ESCs"]
    g = [1495, 1449, 925, 800, 640, 288, 240, 224]
    colours = [GREY, BLUE, PURPLE, GREEN, ORANGE, ORANGE, GREEN, ORANGE]
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
    opts = ["A\nas verified", "B\nrecommended", "C\nlow cost",
            "D\nfloor", "E\nreduced"]
    cost = [290546, 259001, 207295, 129632, 37309]
    colours = [GREY, GREEN, BLUE, ORANGE, RED]
    x = np.arange(len(opts))
    bars = ax.bar(x, cost, color=colours, width=0.62)
    bars[1].set_edgecolor("black"); bars[1].set_linewidth(1.1)

    # Notes sit BELOW the axis, not inside the bars: at column width a bar is
    # narrower than the text, and text inside it gets clipped.
    notes = ["baseline", "no loss", "$-$125 pts", "$-$RTK", "cannot fly"]
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
    a = [85400, 79500, 57396, 24500, 20550, 17800, 5400]
    b = [83000, 38500, 57396, 24500, 20550, 29655, 5400]
    y = np.arange(len(subs))[::-1]
    h = 0.36
    ax.barh(y + h/2, a, h, label="A (as verified)", color=LIGHT, edgecolor=GREY, lw=0.5)
    ax.barh(y - h/2, b, h, label="B (recommended)", color=GREEN)
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
    ax.set_title("Where the recommended saving comes from")
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
    amounts = np.array([8.50, 9.50, 6.50, 4.24])       # INR lakh
    phases = ["P1–P4\nanalysis, ground segment,\nautonomy, long-lead order",
              "P5\nairframe build,\ntest equipment",
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
    ax.set_ylim(0, 12.2)
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
    ax2.set_ylim(0, 34)
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
    subs = ["Propulsion", "Structure", "Payload", "Avionics",
            "Power", "Comms", "Compute &\nperception"]
    frac = [88.6, 79.2, 61.1, 59.8, 58.2, 41.5, 33.3]
    val = [57396, 20550, 5400, 85400, 24500, 17800, 79500]
    y = np.arange(len(subs))[::-1]
    cols = [GREEN if f >= 70 else (ORANGE if f >= 50 else RED) for f in frac]
    ax.barh(y, frac, color=cols, height=0.66)
    for yi, f, v in zip(y, frac, val):
        ax.text(f + 1.5, yi, f"{f:.0f}%", va="center", fontsize=6.8)
        ax.text(2, yi, f"{v/1000:.0f}k", va="center", fontsize=6.0, color="white")
    ax.axvline(58.4, color="black", ls="--", lw=1)
    # Above the plot area, not rotated across the bars -- a vertical label here
    # sits on top of the Power and Comms rows and becomes unreadable.
    ax.annotate("air-vehicle mean 58%", xy=(58.4, len(subs) - 0.45),
                xytext=(4, 0), textcoords="offset points",
                fontsize=6.3, ha="left", va="center")
    ax.set_yticks(y); ax.set_yticklabels(subs)
    ax.set_xlabel("Indian content, value-weighted (%)")
    ax.set_xlim(0, 108)
    ax.set_ylim(-0.7, len(subs) - 0.05)
    ax.set_title("Indigenous content by subsystem")
    ax.grid(axis="y", alpha=0)
    fig.tight_layout()
    save(fig, "fig-indig.pdf")


if __name__ == "__main__":
    print("Generating proposal figures...")
    fig_geotag()
    fig_mass()
    fig_options()
    fig_subsystem()
    fig_funding()
    fig_indig()
    print("Done.")
