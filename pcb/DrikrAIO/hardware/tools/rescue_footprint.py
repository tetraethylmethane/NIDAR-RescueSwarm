"""Recover a footprint that exists only inside a donor board.

OpenESC-30x30 places 14 capacitors on `Capacitor_SMD:C_0402_WIDE`. That
footprint is not in KiCad's stock Capacitor_SMD library and is not a file
anywhere in the OpenDrone sources -- it lived in the author's own modified
copy of the stock library, which was never distributed. Boards embed their
footprints, so the geometry survives inside 4in1.kicad_pcb even though the
library entry is gone.

This lifts it back out into a real .kicad_mod in our project library.
Substituting a stock 0402 instead would be a silent component change: the
whole point of C_0402_WIDE is that its pads are wider than stock, which is a
thermal and assembly decision on a power board.
"""
import io
import os
import re

SRC = (r"c:\Users\swast\OneDrive\Desktop\Drikr-NIDAR\pcb"
       r"\OpenESC-30x30-main\hardware\4in1.kicad_pcb")
DSTDIR = (r"c:\Users\swast\OneDrive\Desktop\Drikr-NIDAR\pcb"
          r"\DrikrAIO\hardware\lib.pretty")
WANT = "Capacitor_SMD:C_0402_WIDE"
NAME = "C_0402_WIDE"


def block_end(s, start):
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unbalanced")


def strip_forms(txt, names):
    """Remove placement/instance forms that must not appear in a library."""
    for nm in names:
        out, pos = [], 0
        while True:
            k = txt.find(f"({nm} ", pos)
            if k < 0:
                out.append(txt[pos:])
                break
            end = block_end(txt, k)
            out.append(txt[pos:k])
            pos = end
        txt = "".join(out)
    return txt


def main():
    src = io.open(SRC, encoding="utf-8", errors="ignore").read()
    k = src.find(f'(footprint "{WANT}"')
    if k < 0:
        raise SystemExit(f"{WANT} not embedded in donor board")
    fp = src[k:block_end(src, k)]

    # A board footprint carries placement and connectivity; a library one must
    # not. Drop position, net assignment, instance path and uuids.
    fp = strip_forms(fp, ["net", "path", "uuid", "tstamp", "fp_text_type"])
    fp = re.sub(r'\(at [-\d.]+ [-\d.]+(?: [-\d.]+)?\)', "(at 0 0)", fp, count=1)
    fp = fp.replace(f'(footprint "{WANT}"', f'(footprint "{NAME}"', 1)

    # The instance we lifted happened to be on the bottom side and carried its
    # placed designator. A library footprint lives on the front and has no
    # designator, or every part built from it arrives pre-flipped and named C34.
    fp = fp.replace('(layer "B.Cu")', '(layer "F.Cu")', 1)
    fp = re.sub(r'\(property "Reference" "[^"]*"', '(property "Reference" "REF**"', fp, count=1)
    fp = re.sub(r'\(property "Value" "[^"]*"', f'(property "Value" "{NAME}"', fp, count=1)
    if "(version" not in fp[:200]:
        fp = fp.replace(f'(footprint "{NAME}"',
                        f'(footprint "{NAME}"\n\t(version 20240108)'
                        f'\n\t(generator "pcbnew")', 1)

    os.makedirs(DSTDIR, exist_ok=True)
    dst = os.path.join(DSTDIR, f"{NAME}.kicad_mod")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(fp + "\n")
    pads = fp.count("(pad ")
    print(f"recovered {NAME}.kicad_mod  ({pads} pads, {len(fp)} bytes)")


if __name__ == "__main__":
    main()
