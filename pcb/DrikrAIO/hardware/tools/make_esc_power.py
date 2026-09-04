"""Extract the ESC power + current-sense block from OpenESC-30x30's root sheet.

OpenESC-30x30 keeps the battery entry, the two 0.2 mOhm shunts, the INA186
current-sense amplifier, the LMR54406 buck that makes +10 V for the gate
drivers and the TLV76733 LDO that makes +3V3 on its ROOT sheet, alongside the
four channel sheets. Copying ESC.kicad_sch alone therefore brought the power
stages across without anything to power them -- which is what the 25 ERC errors
were.

This lifts that root and drops only the four channel sheets, which we
instantiate ourselves. The result becomes esc_power.kicad_sch, one more proven
sheet.

U3 stays. An earlier pass removed it as "OpenESC's board outline" -- it is not.
It is the ESC's entire pad set: VBAT, BATGND, CUR, M1-M4 and the twelve motor
phase pads 1A..4C. Deleting it removed the battery entry and every motor output
at once, which is the sort of thing a name talks you into.

Surgery is done on the raw text with a balanced-paren scan rather than by
parsing and re-serialising: the parser cannot tell a bare token from a quoted
string, so a round trip would quietly corrupt the file.
"""
import io
import os
import re
import uuid as U

SRC = (r"c:\Users\swast\OneDrive\Desktop\Drikr-NIDAR\pcb"
       r"\OpenESC-30x30-main\hardware\4in1.kicad_sch")
DST = (r"c:\Users\swast\OneDrive\Desktop\Drikr-NIDAR\pcb"
       r"\DrikrAIO\hardware\esc_power.kicad_sch")

# Labels that must cross to the root, and the direction they cross in.
PROMOTE = {
    "CURR": "output",          # INA186 drives it -> ESC_CURRENT
    "M1": "bidirectional",     # J1 / U3 breakout, joins the FC's DShot nets
    "M2": "bidirectional",
    "M3": "bidirectional",
    "M4": "bidirectional",
}

# The four channel sheets are deleted here because we instantiate ESC.kicad_sch
# at our own root. Their pins were real connection points, so every wire that
# ran to one is left dangling. Rather than delete that routing, a hierarchical
# label is dropped on each vacated pin coordinate, which carries the same node
# up to our root instead of across to the sheet that used to be there.
#
# U3 -- which an earlier pass mistook for a board outline and removed -- is the
# ESC's whole pad set: VBAT, BATGND, CUR, M1-M4 and the twelve phase pads
# 1A..4C. It is the battery entry and the motor outputs, and it stays.
VACATED = {
    (321.31, 102.87): ("M1_A", "input"),
    (321.31, 106.68): ("M1_B", "input"),
    (321.31, 110.49): ("M1_C", "input"),
    (351.79, 106.68): ("MOTOR1", "bidirectional"),
    (321.31, 90.17):  ("M2_A", "input"),
    (321.31, 93.98):  ("M2_B", "input"),
    (321.31, 86.36):  ("M2_C", "input"),
    (351.79, 87.63):  ("MOTOR2", "bidirectional"),
    (273.05, 106.68): ("M3_A", "input"),
    (273.05, 110.49): ("M3_B", "input"),
    (273.05, 102.87): ("M3_C", "input"),
    (242.57, 104.14): ("MOTOR3", "bidirectional"),
    (273.05, 86.36):  ("M4_A", "input"),
    (273.05, 90.17):  ("M4_B", "input"),
    (273.05, 93.98):  ("M4_C", "input"),
    (242.57, 87.63):  ("MOTOR4", "bidirectional"),
}


def block_end(s, start):
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unbalanced form")


def drop_forms(txt, opener, keep=lambda body: False):
    out, pos = [], 0
    dropped = 0
    while True:
        k = txt.find(opener, pos)
        if k < 0:
            out.append(txt[pos:])
            break
        end = block_end(txt, k)
        body = txt[k:end]
        out.append(txt[pos:k])
        if keep(body):
            out.append(body)
        else:
            dropped += 1
        pos = end
    return "".join(out), dropped


def main():
    txt = io.open(SRC, encoding="utf-8", errors="ignore").read()

    # 1. drop the four channel sheets (we instantiate ESC.kicad_sch ourselves)
    txt, n_sheets = drop_forms(txt, "(sheet (at ")
    # 2. put a hierarchical label on every pin those sheets vacated, so the
    #    routing that ran to them now carries up to our root instead
    stubs = []
    for (x, y), (net, shape) in VACATED.items():
        stubs.append(
            f'(hierarchical_label "{net}" (shape {shape}) (at {x} {y} 0) '
            f'(effects (font (size 1.27 1.27)) (justify left)) '
            f'(uuid "{U.uuid4()}"))')
    n_stub = len(stubs)
    # 3. promote the crossing labels to hierarchical labels
    n_lbl = 0
    for name, shape in PROMOTE.items():
        pat = f'(label "{name}" (at '
        k = txt.find(pat)
        while k >= 0:
            end = block_end(txt, k)
            body = txt[k:end]
            new = body.replace(f'(label "{name}" (at ',
                               f'(hierarchical_label "{name}" (shape {shape}) (at ', 1)
            txt = txt[:k] + new + txt[end:]
            n_lbl += 1
            k = txt.find(pat, k + len(new))

    # 4. the sheet_instances block is a root-only form; a sub-sheet keeps none
    txt, _ = drop_forms(txt, "(sheet_instances ")

    # 5. splice the stubs in just before the closing paren of the file
    close = txt.rstrip()
    assert close.endswith(")")
    txt = close[:-1] + "\n" + "\n".join(stubs) + "\n)\n"

    io.open(DST, "w", encoding="utf-8", newline="\n").write(txt)
    print("esc_power.kicad_sch written")
    print(f"   dropped {n_sheets} channel sheets (U3 pad set kept)")
    print(f"   added {n_stub} hierarchical labels on vacated sheet pins")
    print(f"   promoted {n_lbl} labels to hierarchical")
    print(f"   size {os.path.getsize(DST)} bytes")


if __name__ == "__main__":
    main()
