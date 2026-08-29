#!/usr/bin/env python3
"""Convert a potrace-style SVG logo to vector PDF for inclusion in LaTeX.

WHY THIS EXISTS. pdflatex cannot include SVG, and this machine has no
inkscape, rsvg-convert or ImageMagick -- the `convert` on PATH is Windows'
disk-conversion tool, which fails confusingly. matplotlib is already a
dependency of the figure pipeline, so the logo is parsed and re-emitted as a
vector PDF rather than rasterised.

SCOPE. Handles exactly the subset potrace emits: absolute M, relative m/l/c,
and z, inside a single group transform of the form
    translate(tx,ty) scale(sx,sy)
Anything else raises rather than silently drawing the wrong shape.

Run:  python tools/proposal/svg_logo_to_pdf.py <in.svg> <out.pdf>
"""
from __future__ import annotations

import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib.path import Path                      # noqa: E402
from matplotlib.patches import PathPatch              # noqa: E402

NUM = re.compile(r"-?\d*\.?\d+(?:[eE][-+]?\d+)?")


def parse_transform(svg: str):
    m = re.search(r'transform="translate\(([-\d.]+),([-\d.]+)\)\s*'
                  r'scale\(([-\d.]+),([-\d.]+)\)"', svg)
    if not m:
        raise SystemExit("unsupported or missing group transform")
    tx, ty, sx, sy = (float(g) for g in m.groups())
    return lambda x, y: (tx + sx * x, ty + sy * y)


def parse_path(d: str):
    """Return (vertices, codes) for one path's data."""
    verts, codes = [], []
    cx = cy = 0.0
    sx = sy = 0.0                                     # subpath start
    i, n = 0, len(d)
    cmd = None
    while i < n:
        ch = d[i]
        if ch.isalpha():
            cmd = ch
            i += 1
            continue
        if ch in " ,\n\t\r":
            i += 1
            continue
        m = NUM.match(d, i)
        if not m:
            raise SystemExit(f"cannot parse path at offset {i}: {d[i:i+20]!r}")

        def take(k):
            """Read k numbers starting at the current position."""
            nonlocal i
            out = []
            while len(out) < k:
                while i < n and d[i] in " ,\n\t\r":
                    i += 1
                mm = NUM.match(d, i)
                if not mm:
                    raise SystemExit("ran out of numbers in path")
                out.append(float(mm.group()))
                i = mm.end()
            return out

        if cmd == "M":
            x, y = take(2)
            cx, cy = x, y
            sx, sy = cx, cy
            verts.append((cx, cy)); codes.append(Path.MOVETO)
            cmd = "L"                                  # subsequent pairs are lineto
        elif cmd == "m":
            dx, dy = take(2)
            cx, cy = cx + dx, cy + dy
            sx, sy = cx, cy
            verts.append((cx, cy)); codes.append(Path.MOVETO)
            cmd = "l"
        elif cmd == "l":
            dx, dy = take(2)
            cx, cy = cx + dx, cy + dy
            verts.append((cx, cy)); codes.append(Path.LINETO)
        elif cmd == "L":
            x, y = take(2)
            cx, cy = x, y
            verts.append((cx, cy)); codes.append(Path.LINETO)
        elif cmd == "c":
            a, b, c_, dd, e, f = take(6)
            p1 = (cx + a, cy + b)
            p2 = (cx + c_, cy + dd)
            cx, cy = cx + e, cy + f
            verts += [p1, p2, (cx, cy)]
            codes += [Path.CURVE4] * 3
        elif cmd == "C":
            a, b, c_, dd, e, f = take(6)
            verts += [(a, b), (c_, dd), (e, f)]
            codes += [Path.CURVE4] * 3
            cx, cy = e, f
        else:
            raise SystemExit(f"unsupported path command {cmd!r}")

        # 'z' closes; handled by the alpha branch, but potrace writes it inline
        while i < n and d[i] in " \n\t\r,":
            i += 1
        if i < n and d[i] in "zZ":
            verts.append((sx, sy)); codes.append(Path.CLOSEPOLY)
            cx, cy = sx, sy
            i += 1
    return verts, codes


def convert(src: str, dst: str) -> None:
    svg = open(src, encoding="utf-8").read()
    tf = parse_transform(svg)
    vb = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', svg)
    if not vb:
        raise SystemExit("no viewBox")
    _, _, vw, vh = (float(g) for g in vb.groups())

    fig = plt.figure(figsize=(vw / 100.0, vh / 100.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, vw); ax.set_ylim(0, vh)
    ax.invert_yaxis()                    # SVG y grows downward
    ax.axis("off")

    n_paths = 0
    for d in re.findall(r'd="([^"]*)"', svg):
        verts, codes = parse_path(d)
        if not verts:
            continue
        verts = [tf(x, y) for x, y in verts]
        ax.add_patch(PathPatch(Path(verts, codes), facecolor="black",
                               edgecolor="none", lw=0))
        n_paths += 1

    fig.savefig(dst, format="pdf", transparent=True,
                bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    print(f"  {n_paths} paths -> {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    convert(sys.argv[1], sys.argv[2])
