#!/usr/bin/env python3
"""Tiling geometry for the cascade experiment, and the scale-matching that
makes a maritime dataset stand in for our aircraft.

WHY THIS EXISTS. We want to know whether a cheap gate can reject most tiles
without dropping survivors. That question is only answerable if the targets in
the test data are the SIZE our targets will be, in pixels. SeaDronesSee was
flown between 5 and 260 m on a different camera; feeding it in raw would
measure a detector on the wrong problem.

So this module does two things and nothing else:

  1. Rescales a source frame so its targets land at OUR pixel size. This is the
     step that makes borrowed data mean something. Pixels on target -- not
     altitude, not metres -- is what a detector responds to.

  2. Tiles the frame the way SAHI does, and works out which tiles contain a
     usable view of each target.

THE THING TO BE CAREFUL ABOUT. A target clipped by a tile boundary is not a
positive example -- it is a sliver, and asking a gate to fire on it measures
nothing useful. So a tile is positive only if it contains ENOUGH of the target
(`MIN_VISIBLE`). With 20 % overlap on 640 px tiles the shared margin is 128 px
and our target is ~39 px, so every target appears whole in at least one tile;
if that stops being true the tiling is wrong, and `tiles_for_box` will say so.

Pure geometry. No I/O, no model, no dataset. Runs and is tested without torch.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# A tile counts as containing a target only if this much of the target's area
# falls inside it. Below this the crop holds a fragment, and a gate trained on
# fragments learns to fire on edges.
MIN_VISIBLE = 0.80


@dataclass(frozen=True)
class Tile:
    """Pixel bounds of one tile, half-open: [x0, x1) x [y0, y1)."""
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def w(self) -> int:
        return self.x1 - self.x0

    @property
    def h(self) -> int:
        return self.y1 - self.y0

    def intersect_area(self, box) -> float:
        bx0, by0, bx1, by1 = box
        dx = min(self.x1, bx1) - max(self.x0, bx0)
        dy = min(self.y1, by1) - max(self.y0, by0)
        return dx * dy if dx > 0 and dy > 0 else 0.0


def gsd_m(altitude_m: float, pitch_um: float, f_mm: float) -> float:
    """Ground sample distance in metres per pixel. Similar triangles."""
    return (pitch_um / 1e6) * altitude_m / (f_mm / 1000.0)


def target_px(size_m: float, altitude_m: float, pitch_um: float,
              f_mm: float) -> float:
    """How many pixels a target of `size_m` subtends."""
    return size_m / gsd_m(altitude_m, pitch_um, f_mm)


def scale_to_match(source_target_px: float, wanted_target_px: float) -> float:
    """Resize factor that makes a source frame's targets our size.

    Greater than 1 upsamples. Upsampling does NOT create detail -- it makes the
    target occupy our pixel count while carrying the source's real resolution,
    which is the honest way to borrow data: it can only make the measured recall
    PESSIMISTIC relative to our own optics, never optimistic.
    """
    if source_target_px <= 0:
        raise ValueError("source target size must be positive")
    return wanted_target_px / source_target_px


def tile_grid(width: int, height: int, tile: int = 640,
              overlap: float = 0.20) -> list[Tile]:
    """SAHI-style overlapping tiles covering the frame.

    The last row and column are pulled back flush with the frame edge rather
    than padded, so every tile is full size and the detector never sees a
    partially black crop it was not trained on.
    """
    if not 0.0 <= overlap < 1.0:
        raise ValueError("overlap must be in [0, 1)")
    if tile > width or tile > height:
        raise ValueError(f"tile {tile} does not fit in {width}x{height}")
    stride = int(round(tile * (1.0 - overlap)))
    xs = list(range(0, max(width - tile, 0) + 1, stride))
    ys = list(range(0, max(height - tile, 0) + 1, stride))
    if xs[-1] != width - tile:
        xs.append(width - tile)
    if ys[-1] != height - tile:
        ys.append(height - tile)
    return [Tile(x, y, x + tile, y + tile) for y in ys for x in xs]


def tiles_for_box(tiles: list[Tile], box, min_visible: float = MIN_VISIBLE
                  ) -> list[int]:
    """Indices of tiles holding at least `min_visible` of the box's area.

    An empty result means the target is cut by every tile it touches -- the
    overlap is too narrow for the target size. That is a geometry failure, not
    a detection failure, and the caller should treat it as one.
    """
    bx0, by0, bx1, by1 = box
    area = (bx1 - bx0) * (by1 - by0)
    if area <= 0:
        return []
    return [i for i, t in enumerate(tiles)
            if t.intersect_area(box) / area >= min_visible]


def overlap_covers_target(tile: int, overlap: float, target_px_: float) -> bool:
    """Is the shared margin wider than the target?

    If it is, a target can never be sliced without appearing whole in the
    neighbouring tile. This is the property the whole tiling scheme rests on,
    and it is cheap to assert rather than assume.
    """
    return tile * overlap > target_px_


def summarise(width: int, height: int, tile: int, overlap: float,
              target_px_: float) -> dict:
    """Everything the experiment needs to know about one tiling choice."""
    tiles = tile_grid(width, height, tile, overlap)
    return {
        "n_tiles": len(tiles),
        "stride": int(round(tile * (1.0 - overlap))),
        "shared_margin_px": tile * overlap,
        "target_px": target_px_,
        "overlap_covers_target": overlap_covers_target(tile, overlap, target_px_),
        "redundancy": len(tiles) * tile * tile / float(width * height),
    }
