"""Create the DrikrAIO board scaffold: stack-up, outline, and zoned placement.

This is a STARTING POINT, not a layout. It puts every footprint on the right
side of the board in the right functional zone with its nets assigned, so a
human opens KiCad to a board that is ready to be laid out rather than to 347
parts in a heap at the origin. Nothing is routed and no placement here is
final.

Run with KiCad's bundled Python:
    "C:/Program Files/KiCad/10.0/bin/python.exe" build_pcb.py
"""
import json
import os
import re
import sys

import pcbnew

HW = r"c:\Users\swast\OneDrive\Desktop\Drikr-NIDAR\pcb\DrikrAIO\hardware"
NET = os.path.join(HW, "DrikrAIO.net")
OUT = os.path.join(HW, "DrikrAIO.kicad_pcb")
KI = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"

MM = pcbnew.FromMM
GAP = 0.35          # mm of air between placed parts
STAGE_X = 62.0      # staging area, off the board, for zone overflow
STAGE_W = 26.0      # one column per band

# 50 x 50 mm on the 30.5 mm FPV mounting pattern. Sized from measurement, not
# taste: U3's pad set alone spans 44.0 x 45.8 mm, so 45 mm did not even contain
# it, and the remaining 346 parts come to 2409 mm2 of footprint area. At 50 mm
# that is 48% of a two-sided board, which leaves room to route; at 45 mm it was
# 59% with the power stages crowded onto one side.
BW, BH = 50.0, 50.0
MOUNT = 30.5          # mounting pattern, 4.0 mm holes per OpenESC-30x30
HOLE_D = 4.0

# Reference band -> (side, zone box in mm as x0,y0,x1,y1).
# Power stages go bottom, control goes top: the classic AIO split, and it keeps
# the switching nodes off the same side as the IMU and the 2.4 GHz chain.
# Zones must be a PARTITION -- non-overlapping boxes. The first version put
# the IMU box inside the MCU box and ran the power-block strip across all four
# ESC quadrants, which planted 37 overlapping footprints before a human had
# touched anything.
ZONES = {
    # bottom: four power stages in quadrants, shared power across the middle
    11: ("bottom", (2.0, 2.0, 23.0, 22.0)),      # ESC ch1
    12: ("bottom", (27.0, 2.0, 48.0, 22.0)),     # ESC ch2
    13: ("bottom", (2.0, 28.0, 23.0, 48.0)),     # ESC ch3
    14: ("bottom", (27.0, 28.0, 48.0, 48.0)),    # ESC ch4
    8:  ("bottom", (2.0, 23.0, 48.0, 27.0)),     # shunts, INA186, buck, LDO
    # top: control side
    2:  ("top",    (2.0, 2.0, 18.0, 16.0)),      # FC power tree
    4:  ("top",    (32.0, 2.0, 48.0, 16.0)),     # OSD
    6:  ("top",    (2.0, 18.0, 9.0, 34.0)),      # solder pads, left edge
    1:  ("top",    (10.0, 18.0, 40.0, 34.0)),    # RP2354A and its support
    3:  ("top",    (41.0, 18.0, 48.0, 34.0)),    # IMU
    5:  ("top",    (2.0, 36.0, 20.0, 48.0)),     # blackbox / microSD
    7:  ("top",    (33.0, 36.0, 48.0, 48.0)),    # receiver, corner for antenna
}

BOARD_SPANNING = {"U805"}


def place(fp, cx_mm, cy_mm):
    """Put the footprint's BOUNDING BOX centre at (cx, cy), not its origin.

    SetPosition moves the origin, and for parts with an offset thermal pad the
    origin is nowhere near the middle of the body -- so packing by bounding box
    while positioning by origin leaves parts sitting outside their slot and
    overlapping the next one.
    """
    fp.SetPosition(pcbnew.VECTOR2I(MM(cx_mm), MM(cy_mm)))
    bb = fp.GetBoundingBox(False, False)
    dx = MM(cx_mm) - (bb.GetLeft() + bb.GetRight()) // 2
    dy = MM(cy_mm) - (bb.GetTop() + bb.GetBottom()) // 2
    fp.Move(pcbnew.VECTOR2I(dx, dy))


def band(ref):
    m = re.match(r"^[^\d]+(\d+)", ref)
    if not m:
        return None
    n = int(m.group(1))
    return n // 100 if n >= 1000 else n // 100


def lib_paths():
    """nickname -> .pretty directory, from the project fp-lib-table + stock."""
    out = {}
    tbl = open(os.path.join(HW, "fp-lib-table"), encoding="utf-8").read()
    for name, uri in re.findall(r'\(name "([^"]+)"\).*?\(uri "([^"]+)"\)', tbl):
        out[name] = uri.replace("${KIPRJMOD}", HW).replace("/", os.sep)
    for d in os.listdir(KI):
        if d.endswith(".pretty"):
            out.setdefault(d[:-7], os.path.join(KI, d))
    return out


def parse_netlist(path):
    """(components, nets) from a kicadsexpr netlist.

    Parsed, not pattern-matched: the exporter writes indented multi-line forms,
    so regexes keyed on `(comp (ref "X")` appearing together match nothing and
    fail silently -- which they did, producing a board with zero footprints.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sexp import parse, findall

    tree = parse(open(path, encoding="utf-8", errors="ignore").read())

    def first(node, key, default=None):
        for c in node:
            if isinstance(c, list) and c and c[0] == key:
                return c[1] if len(c) > 1 else default
        return default

    comps = {}
    for block in findall(tree, "components"):
        for comp in findall(block, "comp"):
            ref = first(comp, "ref")
            if ref:
                comps[ref] = (first(comp, "footprint"), first(comp, "value", ""))

    nets = {}
    for block in findall(tree, "nets"):
        for net in findall(block, "net"):
            name = first(net, "name")
            nodes = [(first(n, "ref"), first(n, "pin"))
                     for n in findall(net, "node")]
            nodes = [(r, p) for r, p in nodes if r and p]
            if name and nodes:
                nets[name] = nodes
    return comps, nets


ESC_PCB = (r"c:\Users\swast\OneDrive\Desktop\Drikr-NIDAR\pcb"
           r"\OpenESC-30x30-main\hardware\4in1.kicad_pcb")


def block(txt, opener, start=0):
    """The balanced-paren span of the first `opener` at or after `start`."""
    k = txt.find(opener, start)
    if k < 0:
        return None, -1, -1
    depth = 0
    for i in range(k, len(txt)):
        if txt[i] == "(":
            depth += 1
        elif txt[i] == ")":
            depth -= 1
            if depth == 0:
                return txt[k:i + 1], k, i + 1
    return None, -1, -1


def inject_stackup(path):
    """Give the board a real 2 oz / 1 oz ENIG stack-up.

    Taken verbatim from OpenESC-30x30, which is in production on exactly this
    construction. Declaring it matters: OpenAIO enforces 0.16 mm outer track
    rules for 2 oz copper while its stack-up still says 1 oz, so its power
    traces are sized for copper the fabricator was never asked to supply. The
    rules and the stack-up have to agree, and this is the half that reaches the
    fab.
    """
    donor = open(ESC_PCB, encoding="utf-8", errors="ignore").read()
    stk, _, _ = block(donor, "(stackup")
    if not stk:
        print("   WARNING: no stackup found in donor board")
        return
    txt = open(path, encoding="utf-8", errors="ignore").read()
    setup, s0, s1 = block(txt, "(setup")
    if not setup:
        print("   WARNING: no (setup block in generated board")
        return
    new_setup = setup[:setup.index("\n", 0) + 1] + "\t\t" + stk + "\n" + setup[setup.index("\n", 0) + 1:]
    open(path, "w", encoding="utf-8", newline="\n").write(
        txt[:s0] + new_setup + txt[s1:])
    ox = stk.count('(thickness 0.07)')
    print(f"   stack-up injected: 6 layers, {ox} outer copper at 0.07 mm (2 oz), ENIG")


def main():
    board = pcbnew.BOARD()

    # 6 copper layers. The stack-up itself is injected after saving -- see
    # inject_stackup(); KiCad 10's SWIG bindings return the stackup descriptor
    # as an opaque object with no usable methods.
    board.SetCopperLayerCount(6)

    # ---- board outline and mounting holes ---------------------------------
    for x0, y0, x1, y1 in [(0, 0, BW, 0), (BW, 0, BW, BH),
                           (BW, BH, 0, BH), (0, BH, 0, 0)]:
        seg = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0)))
        seg.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(MM(0.1))
        board.Add(seg)

    libs = lib_paths()
    hole_lib = libs.get("MountingHole")
    for dx in (-1, 1):
        for dy in (-1, 1):
            cx, cy = BW / 2 + dx * MOUNT / 2, BH / 2 + dy * MOUNT / 2
            circ = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
            circ.SetCenter(pcbnew.VECTOR2I(MM(cx), MM(cy)))
            circ.SetEnd(pcbnew.VECTOR2I(MM(cx + HOLE_D / 2), MM(cy)))
            circ.SetLayer(pcbnew.Edge_Cuts)
            circ.SetWidth(MM(0.1))
            board.Add(circ)

    # ---- footprints, placed by zone ---------------------------------------
    comps, nets = parse_netlist(NET)
    cursor = {}
    stage = {}
    overflow = set()
    placed, missing = 0, []
    for ref, (fpid, val) in sorted(comps.items()):
        if not fpid or ":" not in fpid:
            missing.append((ref, fpid))
            continue
        nick, name = fpid.split(":", 1)
        fp = None
        # The nickname first, then our own lib.pretty. C_0402_WIDE is referenced
        # as Capacitor_SMD:C_0402_WIDE but is not in KiCad's stock library and
        # never shipped as a file -- it survives only inside the donor board and
        # is recovered into lib.pretty by tools/rescue_footprint.py.
        for path in (libs.get(nick), os.path.join(HW, "lib.pretty")):
            if fp is not None or not path or not os.path.isdir(path):
                continue
            try:
                fp = pcbnew.FootprintLoad(path, name)
            except Exception:
                fp = None
        if fp is None:
            missing.append((ref, fpid))
            continue

        fp.SetReference(ref)
        fp.SetValue(val)

        # Shelf-pack each zone off the footprint's real extents. A fixed grid
        # overlaps anything larger than its pitch, and 347 overlapping parts
        # generate so many courtyard and clearance violations that DRC stops
        # being able to finish.
        if ref in BOARD_SPANNING:
            # Centred, and on the bottom: it carries the battery and motor
            # pads, which belong on the same side as the power stages.
            fp.SetPosition(pcbnew.VECTOR2I(MM(BW / 2), MM(BH / 2)))
            board.Add(fp)
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
            placed += 1
            continue

        b = band(ref)
        side, box = ZONES.get(b, ("top", (2.0, 2.0, BW - 2, BH - 2)))
        x0, y0, x1, y1 = box
        bb = fp.GetBoundingBox(False, False)
        w = bb.GetWidth() / 1e6 + GAP
        h = bb.GetHeight() / 1e6 + GAP
        cx, cy, rowh = cursor.get(b, (x0, y0, 0.0))
        if cx + w > x1:                      # next shelf
            cx, cy, rowh = x0, cy + rowh, 0.0
        if cy + h > y1:
            # Zone is full. Stage the remainder OFF the board rather than
            # letting rows run on into the neighbouring zone: overlapping
            # footprints make DRC meaningless and are worse than honestly
            # unplaced ones. This is what KiCad does with new parts -- they
            # arrive outside the outline for the designer to drag in, grouped
            # by function so that is a short job.
            overflow.add(b)
            sx, sy, srow = stage.get(b, (STAGE_X + STAGE_W * len(stage), 2.0, 0.0))
            if sx + w > STAGE_X + STAGE_W * (len(stage) + 1):
                sx, sy, srow = stage[b][0], sy + srow, 0.0
            place(fp, sx + w / 2, sy + h / 2)
            stage.setdefault(b, (STAGE_X + STAGE_W * len(stage), 2.0, 0.0))
            stage[b] = (sx + w, sy, max(srow, h))
        else:
            place(fp, cx + w / 2, cy + h / 2)
            cursor[b] = (cx + w, cy, max(rowh, h))
        board.Add(fp)
        if side == "bottom":
            # Add first, then flip. Flipping a footprint that has no parent
            # board segfaults the interpreter. And KiCad 9+ takes a
            # FLIP_DIRECTION enum here, not a bool -- passing False segfaults
            # too, which is two ways for the same line to take the process out
            # without raising anything a try/except could catch.
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        placed += 1

    # ---- nets --------------------------------------------------------------
    for name in nets:
        board.Add(pcbnew.NETINFO_ITEM(board, name))
    assigned = 0
    for name, nodes in nets.items():
        ni = board.FindNet(name)
        if ni is None:
            continue
        for ref, pin in nodes:
            fp = board.FindFootprintByReference(ref)
            if fp is None:
                continue
            for pad in fp.Pads():
                if pad.GetNumber() == pin:
                    pad.SetNet(ni)
                    assigned += 1

    board.BuildListOfNets()

    # SaveBoard REWRITES the .kicad_pro and replaces net_settings with a bare
    # Default class. That silently destroyed the whole netclass set once
    # already -- Phase, VBAT, RF, Gate, Analog and USB all vanished, and the
    # board still opened and still passed DRC, because a board with no
    # netclasses has nothing to violate. Preserve it around the save.
    pro_path = os.path.join(HW, "DrikrAIO.kicad_pro")
    keep = None
    if os.path.exists(pro_path):
        with open(pro_path, encoding="utf-8") as fh:
            keep = json.load(fh).get("net_settings")

    pcbnew.SaveBoard(OUT, board)

    if keep is not None:
        with open(pro_path, encoding="utf-8") as fh:
            pro = json.load(fh)
        if [c.get("name") for c in pro.get("net_settings", {}).get("classes", [])] \
                != [c.get("name") for c in keep.get("classes", [])]:
            pro["net_settings"] = keep
            with open(pro_path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(pro, fh, indent=2)
            print(f"   net_settings restored after SaveBoard "
                  f"({len(keep.get('classes', []))} classes)")

    inject_stackup(OUT)

    print(f"board written: {OUT}")
    print(f"   {BW} x {BH} mm, 6 layers, {MOUNT} mm mount")
    print(f"   footprints placed : {placed}")
    print(f"   pads netted       : {assigned}")
    print(f"   nets              : {len(nets)}")
    if overflow:
        print(f"   staged off-board (zone full, grouped by band): "
              f"{sorted(overflow)}")
    if missing:
        print(f"   FOOTPRINT NOT FOUND: {len(missing)}")
        for ref, fpid in missing[:12]:
            print(f"      {ref:<10} {fpid}")


if __name__ == "__main__":
    main()
