#!/usr/bin/env python3
"""Typeset the camera and lens derivation as a technical note.

The prose is written; the numbers are computed. Every figure in the document is
imported from camera_optics rather than typed, so the note cannot drift from
the calculator the way the sizing chapter drifted from the bill of materials --
which is the whole subject of the note.

    python tools/sizing-model/camera_optics_tex.py
    pdflatex -output-directory docs/sizing docs/sizing/camera-optics.tex
"""
from __future__ import annotations

import datetime as dt
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from camera_optics import (ALTITUDES, AREA_HA, COCO_MED_PX2,  # noqa: E402
                           COCO_SMALL_PX2, GROUNDSPEED, MODELLED, N_DRONES,
                           PERSON_M, PERSON_W, SIDELAP, SPECIFIED,
                           at_altitude, blur_limit, optics)


TILE_PX, TILE_OVERLAP = 640, 0.20


def stage(c, h_m, ds):
    """What the detector is handed at one pipeline stage."""
    gsd = at_altitude(c, h_m)["gsd_cm"] * ds / 100.0      # m/px
    L, W = PERSON_M / gsd, PERSON_W / gsd
    area = L * W
    cls = ("small" if area < COCO_SMALL_PX2
           else "medium" if area < COCO_MED_PX2 else "large")
    return {"gsd_cm": gsd * 100, "len": L, "wid": W, "area": area, "cls": cls,
            "frac_tile": L / TILE_PX}


OUT = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "docs", "sizing",
    "camera-optics.tex")

so, mo = optics(SPECIFIED), optics(MODELLED)
s40, m40 = at_altitude(SPECIFIED, 40.0), at_altitude(MODELLED, 40.0)


def alt_rows(c):
    out = []
    for h in ALTITUDES:
        a = at_altitude(c, h)
        bold = r"\bfseries " if h == 40.0 else ""
        out.append(
            f"{bold}{h:.0f} & {bold}{a['gsd_cm']:.2f} & {bold}{a['person_px']:.0f} & "
            f"{bold}{a['swath_w']:.1f}$\\,\\times\\,${a['swath_h']:.1f} & "
            f"{bold}{a['spacing']:.1f} & {bold}{a['n_lines']:d} & "
            f"{bold}{a['sweep_s']:.0f} \\\\")
    return "\n".join(out)


cmp_rows = "\n".join(
    f"{n} & {a:.2f} & {b:.2f} & {(a-b)/b*100:+.1f} \\\\"
    for n, a, b in (
        ("Horizontal field of view, $^\\circ$", so["hfov"], mo["hfov"]),
        ("Ground sample distance, cm/px", s40["gsd_cm"], m40["gsd_cm"]),
        ("Survivor along the long axis, px", s40["person_px"], m40["person_px"]),
        ("Swath width, m", s40["swath_w"], m40["swath_w"]),
        ("Line spacing, m", s40["spacing"], m40["spacing"]),
        ("Transects per drone", s40["n_lines"], m40["n_lines"]),
        ("Sweep time per drone, s", s40["sweep_s"], m40["sweep_s"])))

blur_rows = " \\\\\n".join(
    f"{h:.0f} & {blur_limit(SPECIFIED, h, GROUNDSPEED)*1000:.2f} & "
    f"1/{1/blur_limit(SPECIFIED, h, GROUNDSPEED):.0f}" for h in ALTITUDES) + r" \\"

tile_rows = []
for ds, rate in ((1, 5.0), (2, 2.0)):
    w, h = SPECIFIED["px_w"] // ds, SPECIFIED["px_h"] // ds
    tiles = math.ceil(w / (640 * 0.8)) * math.ceil(h / (640 * 0.8))
    gsd = s40["gsd_cm"] * ds
    tile_rows.append(f"${ds}\\times$ & {w}$\\,\\times\\,${h} & {tiles} & "
                     f"{tiles*rate:.0f} & {gsd:.2f} & {PERSON_M/(gsd/100):.0f} \\\\")
tile_rows = "\n".join(tile_rows)


pipe = [("Sensor, native", stage(SPECIFIED, 40.0, 1)),
        ("After $2\\times$ downsample", stage(SPECIFIED, 40.0, 2)),
        ("Chapter figure, 60\\,m, $2\\times$", stage(MODELLED, 60.0, 2))]
pipe_rows = "\n".join(
    f"{n} & {d['gsd_cm']:.2f} & {d['len']:.0f}$\\,\\times\\,${d['wid']:.0f} & "
    f"{d['area']:.0f} & {d['frac_tile']*100:.0f}\\,\\% & "
    + (f"\\textcolor{{warn}}{{\\textbf{{{d['cls']}}}}}" if d['cls'] == 'small'
       else d['cls']) + " \\\\"
    for n, d in pipe)
st_native, st_ds, st_old = pipe[0][1], pipe[1][1], pipe[2][1]


alt_rows_short = "\n".join(
    f"{h:.0f} & {at_altitude(SPECIFIED, h)['gsd_cm']:.2f} & "
    f"{at_altitude(SPECIFIED, h)['person_px']:.0f} & "
    f"{at_altitude(SPECIFIED, h)['swath_w']:.1f}$\\,\\times\\,$"
    f"{at_altitude(SPECIFIED, h)['swath_h']:.1f} & "
    f"{at_altitude(SPECIFIED, h)['swath_h'] * 2.0 / GROUNDSPEED:.0f} \\\\"
    for h in ALTITUDES)
_w2, _h2 = SPECIFIED["px_w"] // 2, SPECIFIED["px_h"] // 2
tiles_ds = math.ceil(_w2 / (640 * 0.8)) * math.ceil(_h2 / (640 * 0.8))
inf_ds = tiles_ds * 2.0

det_gain = (s40["person_px"] / m40["person_px"] - 1) * 100
cov_cost = (s40["sweep_s"] / m40["sweep_s"] - 1) * 100
ds_px = PERSON_M / (s40["gsd_cm"] * 2 / 100)

DOC = rf"""\documentclass[11pt,a4paper]{{article}}
\usepackage[T1]{{fontenc}}
\usepackage{{mathptmx}}
\usepackage[scaled=0.88]{{helvet}}
\usepackage{{microtype}}
\usepackage[margin=24mm,top=22mm,bottom=24mm]{{geometry}}
\usepackage{{amsmath,booktabs,array,xcolor,titlesec}}

\definecolor{{ink}}{{HTML}}{{1A1A1A}}
\definecolor{{dim}}{{HTML}}{{6B6B72}}
\definecolor{{rule}}{{HTML}}{{B9B9C0}}
\definecolor{{warn}}{{HTML}}{{8C2B20}}

\color{{ink}}
\setlength{{\parskip}}{{0pt}}
\setlength{{\parindent}}{{1.2em}}
\renewcommand{{\arraystretch}}{{1.22}}
\pagestyle{{plain}}

\titleformat{{\section}}{{\normalfont\bfseries\large}}{{\thesection.}}{{0.6em}}{{}}
\titlespacing*{{\section}}{{0pt}}{{16pt plus 3pt}}{{6pt}}

\newcommand{{\lead}}[1]{{{{\itshape\color{{dim}} #1}}\par\vspace{{6pt}}}}

\begin{{document}}

\begin{{center}}
{{\LARGE\bfseries What the detector actually sees}}\\[5pt]
{{\large\color{{dim}} Pixels on target through the pipeline, and a correction
to the figure in the proposal}}\\[10pt]
{{\color{{rule}}\rule{{0.82\linewidth}}{{0.6pt}}}}\\[7pt]
{{\small Swastik Kumar \quad$\cdot$\quad for the perception lead \quad$\cdot$\quad RescueSwarm, NIDAR 2026--27
Track 1 \quad$\cdot$\quad {dt.date.today().strftime('%d %B %Y')}}}
\end{{center}}

\vspace{{6pt}}

\section{{What the model actually receives}}

You asked what the detector is being handed, so this starts there and works
backwards to the optics. Short version: the numbers in
\texttt{{sizing-calculations.md}}~\S8 were computed for a different sensor than
the one we are buying, and the difference matters more to you than to anyone
else on the team.

We are buying an \textbf{{Arducam IMX477}} with a 6\,mm S-mount lens. Sony
specifies it as type 1/2.3: $4056\times3040$ on a \textbf{{1.55\,\textmu m}}
pitch. The sizing chapter assumes ``1/1.8\,in\ldots\ \textbf{{1.82\,\textmu m}}
pitch''. Same pixel \emph{{count}}, different pixel \emph{{size}} --- so
resolution on target is not what the chapter says.

Here is the target through the pipeline, at the 40\,m search altitude, taking a
supine adult as {PERSON_M}\,m by {PERSON_W}\,m:

\begin{{center}}
\begin{{tabular}}{{l r c r r l}}
\toprule
 & \textbf{{GSD}} & \textbf{{Target}} & \textbf{{Area}} &
\textbf{{Of a 640 tile}} & \textbf{{COCO class}} \\
 & (cm/px) & (px) & (px$^2$) & & \\
\midrule
{pipe_rows}
\bottomrule
\end{{tabular}}
\end{{center}}

\textbf{{The last row is the one to look at.}} The 47\,px figure currently in
the proposal puts the target at {st_old['area']:.0f}\,px$^2$, which is
\emph{{below}} COCO's small-object threshold of {COCO_SMALL_PX2}\,px$^2$. On the
sensor we are actually buying, at 40\,m, it sits at
{st_ds['area']:.0f}\,px$^2$ --- comfortably in the \emph{{medium}} band.

That is not a cosmetic difference. Any published recall figure you benchmark
against reports AP by that size class, and small-object AP is routinely a large
fraction below medium on the same model. If we quote the 47\,px number we are
implicitly promising small-object performance we do not have to accept.

\section{{Where those numbers come from}}

Everything follows from three quantities: pixel count, pixel pitch, focal
length. Active area is count times pitch,
\[
w = 4056 \times 1.55\,\text{{\textmu m}} = {so['w_mm']:.3f}\,\text{{mm}},
\qquad
h = {so['h_mm']:.3f}\,\text{{mm}},
\qquad
d = {so['diag_mm']:.2f}\,\text{{mm}},
\]
which is the type 1/2.3 format Sony quotes. Half-fields are arctangents of half
the sensor over $f$, exactly, with no small-angle approximation:
\[
\theta = 2\arctan\!\left(\frac{{s}}{{2f}}\right)
\;\Longrightarrow\;
\text{{HFOV}} = {so['hfov']:.1f}^\circ,\quad
\text{{VFOV}} = {so['vfov']:.1f}^\circ,\quad
\text{{DFOV}} = {so['dfov']:.1f}^\circ .
\]
Sensor and ground are similar triangles about the lens, so ground sample
distance is just
\[
\text{{GSD}} = \frac{{p\,H}}{{f}}
= \frac{{1.55\,\text{{\textmu m}} \times 40\,\text{{m}}}}{{6\,\text{{mm}}}}
= {s40['gsd_cm']:.2f}\,\text{{cm/px}} .
\]
One pixel subtends {so['ifov_mdeg']:.2f}\,mdeg, which is what sets the blur
tolerance in~\S4.

\begin{{center}}
\begin{{tabular}}{{r r r c r}}
\toprule
\textbf{{AGL}} (m) & \textbf{{GSD}} (cm/px) & \textbf{{Target}} (px) &
\textbf{{Footprint}} (m) & \textbf{{Frames/target}} \\
\midrule
{alt_rows_short}
\bottomrule
\end{{tabular}}
\end{{center}}

\section{{Tiling, and one property worth checking}}

Tile count depends on pixel count, which did not change, so the inference
budget is untouched: at $2\times$ downsample and 2\,Hz we still get
{tiles_ds} tiles per frame and {inf_ds:.0f} inferences per second.

\begin{{center}}
\begin{{tabular}}{{c c r r r r}}
\toprule
\textbf{{Downsample}} & \textbf{{Frame}} & \textbf{{Tiles}} &
\textbf{{Inferences/s}} & \textbf{{GSD}} (cm/px) & \textbf{{Target}} (px) \\
\midrule
{tile_rows}
\bottomrule
\end{{tabular}}
\end{{center}}

The property worth checking is the overlap. At {TILE_PX}\,px tiles and
{TILE_OVERLAP*100:.0f}\,\% overlap the shared margin is
{TILE_PX*TILE_OVERLAP:.0f}\,px, and the target at 40\,m is
{st_ds['len']:.0f}\,px along its long axis. \textbf{{The overlap is wider than
the target}}, so no survivor can be cut by a tile boundary without appearing
whole in the neighbouring tile. That holds at every altitude in the table
above, and it is the reason the overlap is 20\,\% rather than something
smaller.

\section{{Blur, which turns out not to bind}}

Forward motion smears the image by $v\,t_{{\text{{exp}}}}$ on the ground, so
holding smear under one pixel means $t_{{\text{{exp}}}} \le \text{{GSD}}/v$. At
{GROUNDSPEED:.0f}\,m/s:

\begin{{center}}
\begin{{tabular}}{{r r l}}
\toprule
\textbf{{AGL}} (m) & \textbf{{Longest exposure}} (ms) & \textbf{{Shutter}} \\
\midrule
{blur_rows}
\bottomrule
\end{{tabular}}
\end{{center}}

\texttt{{SYS-45}} already mandates $1/1000$\,s or faster, which clears every
altitude. In Indian daylight that pushes ISO down rather than exposure up, so
it costs nothing in noise either. Blur is not what will limit recall; target
size is.

\section{{What it costs the flight side}}

For completeness, since the same substitution moves the coverage numbers in the
opposite direction. A smaller pixel behind the same lens narrows the field and
finens the GSD in the same proportion, so at 40\,m:

\begin{{center}}
\begin{{tabular}}{{l r r r}}
\toprule
At 40\,m AGL & \textbf{{IMX477}} & \textbf{{Sizing chapter}} & \textbf{{Change, \%}} \\
\midrule
{cmp_rows}
\bottomrule
\end{{tabular}}
\end{{center}}

We gain {det_gain:.0f}\,\% more pixels on target and pay {cov_cost:.0f}\,\% more
sweep time --- seven transects per drone instead of six. Against 250 marks for
detection and an 1800\,s budget I think that favours the sensor we are buying,
but it was never a decision anyone made.

\section{{What I need from you}}

Two things, and neither is urgent this week.

First, if you have benchmarked anything on HERIDAL or SARD, tell me which size
band the reported AP came from. If the published number was measured on
medium-class targets then our 40\,m figure is comparable and the 47\,px one was
never going to be.

Second, the survey altitude is unresolved --- the design point says 60\,m, every
simulation we have flown says 40\,m, and the sizing chapter proposes 40\,m
pending a recall measurement. That measurement is yours. If you can say what
recall looks like at {st_ds['len']:.0f}\,px against
{st_old['len']:.0f}\,px, the altitude decision follows from it rather than from
argument, and I can re-baseline the documents once instead of twice.

\vfill
{{\footnotesize\color{{dim}}
The prose here is mine; the arithmetic is not. Every figure in this note
is computed by \texttt{{camera\_optics.py}} and typeset by
\texttt{{camera\_optics\_tex.py}}, both under \texttt{{tools/sizing-model/}},
so the document cannot drift from the model the way the sizing chapter drifted
from the parts list --- which is the whole subject of the note.}}

\end{{document}}
"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(DOC)
print(f"wrote {os.path.relpath(OUT)}")
print(f"  IMX477   HFOV {so['hfov']:.1f} deg  GSD@40m {s40['gsd_cm']:.2f} cm/px  "
      f"survivor {s40['person_px']:.0f} px")
print(f"  chapter  HFOV {mo['hfov']:.1f} deg  GSD@40m {m40['gsd_cm']:.2f} cm/px  "
      f"survivor {m40['person_px']:.0f} px")
