#!/usr/bin/env python3
"""Placement optimisation for DrikrAIO. PLACEMENT ONLY -- never routes.

Repositions footprints on the existing board. Does not touch nets, does not
create tracks, does not modify the schematic.

DESIGN INTENT
-------------
Bottom = power, top = control, which keeps switching nodes off the same side as
the IMU and the 2.4 GHz chain.

The four ESC channels sit in symmetric quadrants. Symmetry is deliberate:
airflow DIRECTION is an open requirement (P3), so a layout that depends on
knowing it would be a layout built on an assumption. Four identical quadrants
behave the same whichever way the air moves.

Within each quadrant, parts are ordered MOSFETs -> gate driver and channel MCU
-> ceramics -> resistors, and packed FROM THE OUTER CORNER INWARD. That does
two things at once:

  * the six MOSFETs land at the board edge, which is where the most airflow is
    under any direction assumption; and
  * the gate driver and the local ceramics land immediately beside them, which
    is what keeps the commutation loop small.

The IMU goes to the BOARD CENTRE on the top side. Every top-side position on a
board this dense sits above something, so the question is what. The centre sits
above the shunt / regulator strip, which is a DC path, not a switching node --
and it is the point furthest from all four MOSFET clusters at once.

RF and the FC switching regulators go to opposite corners, so the receiver is
as far as the board allows from the only other switching source on its own side.

Run with KiCad's Python:
    "C:/Program Files/KiCad/10.0/bin/python.exe" place_optimize.py
"""
import collections
import os
import re
import sys

import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HW, "DrikrAIO.kicad_pcb")
MM = pcbnew.FromMM
GAP = 0.35
BW = BH = 50.0

# band -> (side, box, corner)
# corner names which corner of the box packing starts from, so that the parts
# ordered first end up there.
ZONES = {
    # ---- bottom: power ----------------------------------------------------
    # Quadrants, packed from the OUTER corner so the FETs reach the board edge.
    11: ("bottom", (2.0, 2.0, 23.0, 21.5), "tl"),
    12: ("bottom", (27.0, 2.0, 48.0, 21.5), "tr"),
    13: ("bottom", (2.0, 28.5, 23.0, 48.0), "bl"),
    14: ("bottom", (27.0, 28.5, 48.0, 48.0), "br"),
    # Battery entry, shunt, current sense, +10 V buck, +3V3 LDO.
    # Centre strip: shortest broad VBAT path to all four quadrants at once.
    # Stops at x=33: the right end of the strip is reserved for J801, which is
    # pinned there for cable access. Without the reservation the packer filled
    # that space and the connector landed on top of four capacitors.
    8:  ("bottom", (2.0, 22.0, 33.0, 28.0), "tl"),

    # ---- top: control -----------------------------------------------------
    2:  ("top", (2.0, 2.0, 18.0, 16.0), "tl"),    # FC power, switching inductors
    7:  ("top", (32.0, 2.0, 48.0, 18.0), "tr"),   # RX 2.4 GHz, antenna to edge
    1:  ("top", (2.0, 18.0, 20.0, 34.0), "tl"),   # RP2354A and support
    3:  ("top", (21.0, 21.0, 29.0, 29.0), "tl"),  # IMU, board centre
    4:  ("top", (32.0, 20.0, 48.0, 34.0), "tl"),  # OSD
    5:  ("top", (2.0, 36.0, 18.0, 48.0), "tl"),   # blackbox / microSD
    6:  ("top", (20.0, 36.0, 48.0, 48.0), "tl"),  # solder pads, board edge
}

BOARD_SPANNING = {"U805"}

# Connectors are PINNED to board-edge positions, not left to the packer.
# Accessibility is a mechanical requirement, and a connector that the packer
# happens to place inland is useless however tidy the result looks. Three of
# them -- USB101, J801 and U601 -- staged off-board entirely before this.
#
# (ref, x, y, rotation_deg, side)
PINNED = [
    ("USB101", 25.0, 5.2, 0, "top"),      # USB-C, top edge, cable access
    ("U601", 41.0, 45.5, 0, "top"),       # VTX/telemetry JST, bottom edge
    ("P601", 12.0, 45.5, 0, "top"),       # ESC signal JST, bottom edge
    ("J801", 41.0, 25.0, 0, "bottom"),    # FC signal JST, reserved right end
]

# Order within an ESC quadrant. First in this list lands at the outer corner,
# i.e. at the board edge where the airflow is.
ESC_ORDER = {"Q": 0, "U": 1, "C": 2, "R": 3, "TP": 4}

# Order everywhere else. Critical actives first so that if a zone overflows it
# is passives that stage off-board, never the IC.
#
# The first version sorted these alphabetically, which put U after C and R --
# and duly staged U701, the 2.4 GHz transceiver, off the board while keeping
# its decoupling capacitors on it.
GENERAL_ORDER = {
    # High-current and mechanically-constrained parts outrank everything.
    # Rsense -- the two 0.2 mOhm shunts carrying the whole battery current --
    # was not in this table at all and defaulted to last, so it staged off
    # the board while its filter capacitors stayed on it.
    "Rsense": 0,
    "USB": 0, "J": 0, "P": 0, "JP": 0, "Card": 0,   # connectors need board access
    "U": 0,      # ICs
    "Q": 1,      # transistors
    "AE": 2, "RF": 2,                    # antenna and RF connector
    "FL": 3, "L": 3, "OSC": 3, "X": 3,   # filters, inductors, crystals
    "D": 4, "SW": 4,
    "C": 5,
    "R": 6,
    "TP": 7,
}


def band_of(ref):
    m = re.match(r"^[^\d]+(\d+)", ref)
    return int(m.group(1)) // 100 if m else None


def prefix(ref):
    return "".join(c for c in ref if not c.isdigit())


def sort_key(band, ref):
    """Within ESC quadrants, order by role. Elsewhere, keep it stable."""
    if band in (11, 12, 13, 14):
        return (ESC_ORDER.get(prefix(ref), 9), ref)
    return (GENERAL_ORDER.get(prefix(ref), 8), ref)


def place(fp, cx, cy):
    """Put the footprint's bounding-box centre at (cx, cy)."""
    fp.SetPosition(pcbnew.VECTOR2I(MM(cx), MM(cy)))
    bb = fp.GetBoundingBox(False, False)
    fp.Move(pcbnew.VECTOR2I(MM(cx) - (bb.GetLeft() + bb.GetRight()) // 2,
                            MM(cy) - (bb.GetTop() + bb.GetBottom()) // 2))


def main():
    board = pcbnew.LoadBoard(PCB)

    if len(list(board.GetTracks())):
        print("  REFUSING: board already has tracks. This tool is placement "
              "only and must not run on a routed board.")
        return 2

    pinned = {}
    for ref, x, y, rot, side in PINNED:
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            continue
        want = pcbnew.B_Cu if side == "bottom" else pcbnew.F_Cu
        if fp.GetLayer() != want:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        if rot:
            fp.SetOrientationDegrees(rot)
        place(fp, x, y)
        pinned[ref] = (x, y)

    by_band = collections.defaultdict(list)
    for fp in board.Footprints():
        ref = fp.GetReference()
        if ref in pinned:
            continue
        if ref in BOARD_SPANNING:
            place(fp, BW / 2, BH / 2)
            if fp.GetLayer() != pcbnew.B_Cu:
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
            continue
        b = band_of(ref)
        if b is not None:
            by_band[b].append(fp)

    stage_x, staged = 62.0, 0
    moved = 0
    summary = []

    for band, fps in sorted(by_band.items()):
        if band not in ZONES:
            continue
        side, (x0, y0, x1, y1), corner = ZONES[band]
        fps.sort(key=lambda f: sort_key(band, f.GetReference()))

        # put every part on the right side first, so bounding boxes are correct
        for fp in fps:
            want = pcbnew.B_Cu if side == "bottom" else pcbnew.F_Cu
            if fp.GetLayer() != want:
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)

        rtl = corner in ("tr", "br")     # pack right-to-left
        btt = corner in ("bl", "br")     # pack bottom-to-top

        cx = x1 if rtl else x0
        cy = y1 if btt else y0
        rowh = 0.0
        placed_here = 0
        for fp in fps:
            bb = fp.GetBoundingBox(False, False)
            w = bb.GetWidth() / 1e6 + GAP
            h = bb.GetHeight() / 1e6 + GAP

            # new shelf?
            if (rtl and cx - w < x0) or (not rtl and cx + w > x1):
                cx = x1 if rtl else x0
                cy = cy - rowh if btt else cy + rowh
                rowh = 0.0

            overflow = (cy - h < y0) if btt else (cy + h > y1)
            if overflow:
                # stage off-board, grouped by band, rather than overlap a
                # neighbouring zone
                place(fp, stage_x + (staged % 12) * 2.2,
                      2.0 + (staged // 12) * 2.2)
                staged += 1
                continue

            px = (cx - w / 2) if rtl else (cx + w / 2)
            py = (cy - h / 2) if btt else (cy + h / 2)
            place(fp, px, py)
            cx = (cx - w) if rtl else (cx + w)
            rowh = max(rowh, h)
            moved += 1
            placed_here += 1

        summary.append((band, side, placed_here, len(fps) - placed_here))

    pcbnew.SaveBoard(PCB, board)

    print("PLACEMENT OPTIMISED  (no routing performed)")
    print("=" * 70)
    print(f"  {'band':>5} {'side':<7} {'on board':>9} {'staged':>7}")
    names = {1: "MCU", 2: "FC power", 3: "IMU", 4: "OSD", 5: "blackbox",
             6: "pads", 7: "RX 2.4GHz", 8: "batt/sense",
             11: "ESC ch1", 12: "ESC ch2", 13: "ESC ch3", 14: "ESC ch4"}
    for band, side, on, off in summary:
        print(f"  {band:>4}x {side:<7} {on:>9} {off:>7}   {names.get(band,'')}")
    print(f"\n  repositioned {moved}, staged off-board {staged}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
