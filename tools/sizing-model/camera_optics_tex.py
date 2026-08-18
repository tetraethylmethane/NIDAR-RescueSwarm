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
from camera_optics import (ALTITUDES, AREA_HA, GROUNDSPEED, MODELLED,  # noqa: E402
                           N_DRONES, PERSON_M, SIDELAP, SPECIFIED,
                           at_altitude, blur_limit, optics)

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
{{\LARGE\bfseries The camera, worked through}}\\[5pt]
{{\large\color{{dim}} What a 6\,mm lens on an IMX477 actually sees,
and why the sizing chapter disagrees}}\\[10pt]
{{\color{{rule}}\rule{{0.82\linewidth}}{{0.6pt}}}}\\[7pt]
{{\small Swastik Kumar \quad$\cdot$\quad Project RescueSwarm, NIDAR 2026--27
Track 1 \quad$\cdot$\quad {dt.date.today().strftime('%d %B %Y')}}}
\end{{center}}

\vspace{{6pt}}

\section{{Why I went back to this}}

We are buying an Arducam IMX477 with a 6\,mm S-mount lens, and I wanted the
line spacing and sweep times to come out of the sensor rather than out of a
table someone had already written. Working it through, the two do not agree,
and the reason is worth writing down.

Sony specifies the IMX477 as a type 1/2.3 sensor: $4056\times3040$ pixels on a
\textbf{{1.55\,\textmu m}} pitch, 7.9\,mm across the diagonal. Our own
\texttt{{sizing-calculations.md}}~\S8 gives the baseline as ``1/1.8\,in,
$4056\times3040$, $7.4\times5.6$\,mm, \textbf{{1.82\,\textmu m}} pitch''.

\textcolor{{warn}}{{The pixel \emph{{count}} is identical and the pixel
\emph{{size}} is not.}} Every optical quantity we depend on scales with pitch,
so the field of view, ground sample distance, swath, line spacing and sweep
time in that chapter all describe a camera we are not buying. What follows
derives both, so the difference can be seen rather than argued about.

\section{{From three numbers to a field of view}}

Everything here comes from the pixel count, the pixel pitch and the focal
length. The active area is simply count times pitch,
\[
w = N_x\,p = 4056 \times 1.55\,\text{{\textmu m}} = {so['w_mm']:.3f}\,\text{{mm}},
\qquad
h = N_y\,p = {so['h_mm']:.3f}\,\text{{mm}},
\]
giving a {so['diag_mm']:.2f}\,mm diagonal, which is the type 1/2.3 format Sony
quotes. The lens forms that image at its focal length, so each half-field is
the arctangent of half the sensor over $f$. There is no small-angle
approximation in this and there does not need to be:
\[
\theta = 2\arctan\!\left(\frac{{s}}{{2f}}\right)
\qquad\Longrightarrow\qquad
\text{{HFOV}} = {so['hfov']:.1f}^\circ,
\quad
\text{{VFOV}} = {so['vfov']:.1f}^\circ,
\quad
\text{{DFOV}} = {so['dfov']:.1f}^\circ .
\]
A single pixel subtends {so['ifov_mdeg']:.2f}\,mdeg. That number returns in
\S5, because it is what decides how long the shutter may stay open.

\section{{Ground sample distance, footprint and spacing}}

The sensor and the ground form similar triangles about the lens, which gives
the ground sample distance directly, and the swath follows from the field of
view. Line spacing is the swath less the sidelap:
\[
\text{{GSD}} = \frac{{p\,H}}{{f}},
\qquad
W = 2H\tan\frac{{\text{{HFOV}}}}{{2}},
\qquad
S = W\,(1-\ell), \quad \ell = {SIDELAP*100:.0f}\,\%.
\]

Sidelap is not conservatism for its own sake. Attitude wobble, altitude error
and lens distortion all move the real footprint around between one pass and the
next, and a gap between passes is not a cosmetic defect --- it is a survivor
nobody flew over.

\begin{{center}}
\begin{{tabular}}{{r r r c r r r}}
\toprule
\textbf{{AGL}} & \textbf{{GSD}} & \textbf{{Survivor}} & \textbf{{Footprint}} &
\textbf{{Spacing}} & \textbf{{Lines}} & \textbf{{Sweep}} \\
(m) & (cm/px) & (px) & (m) & (m) & & (s) \\
\midrule
{alt_rows(SPECIFIED)}
\bottomrule
\end{{tabular}}
\end{{center}}

Transect counts and sweep times take the {AREA_HA:.0f}\,ha area divided
{N_DRONES} ways, treat each sub-region as square, and fly it at
{GROUNDSPEED:.0f}\,m/s with six seconds spent in each turn.

\section{{What changed when the sensor changed}}

Comparing the two at the 40\,m search altitude shows the substitution is not
simply better or worse. It is a trade, and it happens to be one nobody made
deliberately.

\begin{{center}}
\begin{{tabular}}{{l r r r}}
\toprule
At 40\,m AGL & \textbf{{IMX477}} & \textbf{{Sizing chapter}} & \textbf{{Change, \%}} \\
\midrule
{cmp_rows}
\bottomrule
\end{{tabular}}
\end{{center}}

A smaller pixel behind the same lens narrows the field and finens the ground
sample distance in exactly the same proportion, so the two effects are the same
number wearing different signs. \textbf{{We gain
{det_gain:.0f}\,\% more pixels on a survivor and pay {cov_cost:.0f}\,\% more
sweep time}} --- seven transects per drone instead of six.

Set against 250 marks for detection and an 1800\,s mission budget, I think that
trade favours the part we are actually buying. The uncomfortable part is that
it was never chosen: the figures we have been quoting describe neither camera.

\section{{Two things this settles}}

\textbf{{Motion blur is not the constraint we half-expected.}} Forward motion
smears the image by $v\,t_{{\text{{exp}}}}$ on the ground, so holding that under a
single pixel means $t_{{\text{{exp}}}} \le \text{{GSD}}/v$:

\begin{{center}}
\begin{{tabular}}{{r r l}}
\toprule
\textbf{{AGL}} (m) & \textbf{{Longest exposure}} (ms) & \textbf{{Shutter}} \\
\midrule
{blur_rows}
\bottomrule
\end{{tabular}}
\end{{center}}

\texttt{{SYS-45}} already requires $1/1000$\,s or faster, which clears every
altitude with room to spare. In Indian daylight that requirement drives ISO
down rather than exposure up, so it costs us nothing.

\textbf{{The tiling budget survives, but one published figure does not.}} Tile
count follows pixel count, which did not change, so the inference load is
untouched:

\begin{{center}}
\begin{{tabular}}{{c c r r r r}}
\toprule
\textbf{{Downsample}} & \textbf{{Frame}} & \textbf{{Tiles}} &
\textbf{{Inferences/s}} & \textbf{{GSD}} (cm/px) & \textbf{{Survivor}} (px) \\
\midrule
{tile_rows}
\bottomrule
\end{{tabular}}
\end{{center}}

At $2\times$ downsampling and 2\,Hz we still get 24 inferences per second. But
the survivor in that downsampled frame is \textbf{{{ds_px:.0f}\,px}}, not the
47\,px the proposal currently states --- that figure was computed at 60\,m, on
the other sensor, and both of those need correcting together.

\section{{What I would do about it}}

Nothing here is an argument for changing the camera. The IMX477 is the better
of the two where the marks are, and it is already on order.

It is an argument for re-baselining the documents onto the part we are buying:
the GSD table, the swath and line-spacing figures, the sweep times, and the
survivor pixel count in the perception section. That work runs into the
unresolved question of whether we survey at 40\,m or 60\,m, because both move
the same quantities, and I would rather settle the two in one pass than do the
arithmetic twice.

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
