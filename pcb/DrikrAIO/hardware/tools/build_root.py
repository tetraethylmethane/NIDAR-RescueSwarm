"""Build the DrikrAIO root schematic from the proven donor sheets.

Two jobs the KiCad GUI would normally do for us, done here explicitly:

  1. RE-INSTANCE. Every symbol in a copied sheet carries an (instances ...)
     block naming the donor project and the donor's sheet-UUID path. In a new
     project those paths are meaningless, so each one is rewritten to this
     project and this root's sheet UUIDs. ESC.kicad_sch is instantiated four
     times, so its symbols get four paths, one per channel.

  2. RE-ANNOTATE. OpenFC's R49 and OpenESC's R49 are different resistors that
     would collide. Each sheet gets a reference band (rp2350a 1xx, power 2xx,
     ... ESC channels 11xx-14xx) so references stay unique and you can tell
     which block a part belongs to by its number.

The root itself wires the sheets with global labels on short stubs rather than
drawn wires: it is generated, and a label farm is reviewable where a generated
rat's nest of wire segments is not. Open it in KiCad and read the labels.
"""
import io
import os
import re
import sys
import uuid as U

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HW = r"c:\Users\swast\OneDrive\Desktop\Drikr-NIDAR\pcb\DrikrAIO\hardware"
PROJECT = "DrikrAIO"

# sheet name -> (file, reference band, page)
SHEETS = [
    ("rp2350a",  "rp2350a.kicad_sch",            100, 2),
    ("power",    "power.kicad_sch",              200, 3),
    ("imu",      "imu.kicad_sch",                300, 4),
    ("osd",      "osd.kicad_sch",                400, 5),
    ("blackbox", "blackbox.kicad_sch",           500, 6),
    ("pads",     "pads.kicad_sch",               600, 7),
    ("rx",       "rx_esp32c3_sx1281.kicad_sch",  700, 8),
    ("esc1",     "ESC.kicad_sch",               1100, 9),
    ("esc2",     "ESC.kicad_sch",               1200, 10),
    ("esc3",     "ESC.kicad_sch",               1300, 11),
    ("esc4",     "ESC.kicad_sch",               1400, 12),
]

# sheet pin -> root net.  Where two sheets use different names for the same
# node the mapping is what joins them; those are commented.
NETS = {
    "rp2350a": {
        "SPI1{SCK,MOSI,MISO}": "SPI1{SCK,MOSI,MISO}",
        "SPI0{SCK,MOSI,MISO}": "SPI0{SCK,MOSI,MISO}",
        "I2C0{SCL,SDA}": "I2C0{SCL,SDA}",
        "GYRO_CS": "GYRO_CS",          # -> imu CS
        "GYRO_INT": "GYRO_INT",
        "FLASH_CS": "FLASH_CS",
        "OSD_EN": "OSD_EN", "OSD_SYNC": "OSD_SYNC", "OSD_W": "OSD_W",
        "10V_ENABLE": "10V_ENABLE",
        "BUZZER-": "BUZZER-", "LED_STRIP": "LED_STRIP",
        "UART0_RX": "UART0_RX", "UART0_TX": "UART0_TX",
        "UART1_RX": "UART1_RX", "UART1_TX": "UART1_TX",   # -> rx ELRS
        "PIOUART0_RX": "PIOUART0_RX", "PIOUART0_TX": "PIOUART0_TX",
        "ESC_CURRENT": "ESC_CURRENT",  # from the onboard INA186, not the pads
        "MOTOR1": "MOTOR1", "MOTOR2": "MOTOR2",
        "MOTOR3": "MOTOR3", "MOTOR4": "MOTOR4",
    },
    "power":    {"10V_ENABLE": "10V_ENABLE"},
    "imu":      {"SPI1{SCK,MOSI,MISO}": "SPI1{SCK,MOSI,MISO}",
                 "CS": "GYRO_CS", "GYRO_INT": "GYRO_INT",
                 "CLKIN": "IMU_CLKIN_NC"},   # documented dead end, see README
    "osd":      {"OSD_EN": "OSD_EN", "OSD_SYNC": "OSD_SYNC", "OSD_W": "OSD_W",
                 "VIDEO_IN": "VIDEO_IN", "VIDEO_OUT": "VIDEO_OUT"},
    "blackbox": {"SPI0{SCK,MOSI,MISO}": "SPI0{SCK,MOSI,MISO}",
                 "FLASH_CS": "FLASH_CS"},
    "pads": {
        "I2C0{SCL,SDA}": "I2C0{SCL,SDA}",
        "BUZZER-": "BUZZER-", "LED_STRIP": "LED_STRIP",
        "UART0_RX": "UART0_RX", "UART0_TX": "UART0_TX",
        "UART1_RX": "UART1_RX", "UART1_TX": "UART1_TX",
        "PIOUART0_RX": "PIOUART0_RX", "PIOUART0_TX": "PIOUART0_TX",
        "PIOUART1_RX": "PIOUART1_RX_NC",   # RP2354A QFN-60 exposes one PIO UART
        "PIOUART1_TX": "PIOUART1_TX_NC",
        "CAMERA": "VIDEO_IN", "VTX": "VIDEO_OUT",
        "CURRENT": "PADS_CURRENT_NC",      # onboard INA186 drives ESC_CURRENT
        "M1": "MOTOR1", "M2": "MOTOR2", "M3": "MOTOR3", "M4": "MOTOR4",
    },
    "rx":   {"ELRS_TX": "UART1_RX", "ELRS_RX": "UART1_TX"},  # crossed, TX->RX
    "esc1": {"dshot": "MOTOR1", "A": "M1_A", "B": "M1_B", "C": "M1_C"},
    "esc2": {"dshot": "MOTOR2", "A": "M2_A", "B": "M2_B", "C": "M2_C"},
    "esc3": {"dshot": "MOTOR3", "A": "M3_A", "B": "M3_B", "C": "M3_C"},
    "esc4": {"dshot": "MOTOR4", "A": "M4_A", "B": "M4_B", "C": "M4_C"},
}

HIER = re.compile(
    r'\(hierarchical_label\s+"([^"]+)"\s*\(shape\s+(\w+)\)', re.S)


def uid():
    return str(U.uuid4())


def sheet_pins(path):
    txt = io.open(path, encoding="utf-8", errors="ignore").read()
    seen, out = set(), []
    for name, shape in HIER.findall(txt):
        if name not in seen:
            seen.add(name)
            out.append((name, shape))
    return out


def reinstance(src, dst, project, root_uuid, entries, band_map):
    """Rewrite a donor sheet's symbol instances for this project.

    `entries` is [(sheet_uuid, band)] -- more than one for a sheet used
    several times, which is how the four ESC channels share one file.
    """
    txt = io.open(src, encoding="utf-8", errors="ignore").read()

    # Build one map per band: original reference -> new reference.
    #
    # Sequential, NOT modulo. Taking `band + num % 100` collapses #PWR0129 and
    # #PWR0229 onto the same #PWR129, and KiCad then refuses to export a
    # netlist with "schematic has annotation errors" -- which is how this was
    # caught. Numbering each prefix from the band upwards is collision-free by
    # construction.
    originals = sorted({r for r in re.findall(r'\(reference "([^"]+)"', txt)})
    maps = {}
    for _, band in entries:
        seq, m = {}, {}
        for ref in originals:
            g = re.match(r"^([^\d]+)(\d+)(.*)$", ref)
            if not g:
                m[ref] = ref
                continue
            pre = g.group(1)
            seq[pre] = seq.get(pre, 0) + 1
            m[ref] = f"{pre}{band + seq[pre]}"
        maps[band] = m

    def renumber(ref, band):
        return maps[band].get(ref, ref)

    # Replace each (instances ...) block wholesale.
    #
    # Found by balanced-paren scan, not by regex: these blocks sit at different
    # nesting depths in different donor sheets, so a pattern anchored on the
    # closing indentation silently matches some files and not others. It did
    # exactly that on the first attempt -- imu, pads and rx were rewritten
    # while rp2350a, power, osd, blackbox and ESC were quietly left bound to
    # their donor projects.
    def block_end(s, start):
        depth = 0
        for i in range(start, len(s)):
            if s[i] == "(":
                depth += 1
            elif s[i] == ")":
                depth -= 1
                if depth == 0:
                    return i + 1
        raise ValueError("unbalanced (instances block")

    out, pos = [], 0
    while True:
        k = txt.find("(instances", pos)
        if k < 0:
            out.append(txt[pos:])
            break
        end = block_end(txt, k)
        block = txt[k:end]
        refs = re.findall(r'\(reference "([^"]+)"', block)
        units = re.findall(r"\(unit (\d+)\)", block)
        out.append(txt[pos:k])
        if refs:
            ref, unit = refs[0], units[0] if units else "1"
            paths = "".join(
                f'\n\t\t\t\t(path "/{root_uuid}/{su}"'
                f'\n\t\t\t\t\t(reference "{renumber(ref, band)}")'
                f"\n\t\t\t\t\t(unit {unit})\n\t\t\t\t)"
                for su, band in entries)
            out.append(f'(instances\n\t\t\t(project "{project}"'
                       f"{paths}\n\t\t\t)\n\t\t)")
        else:
            out.append(block)
        pos = end
    txt = "".join(out)

    # Keep the cached Reference property in step with the first instance.
    band = entries[0][1]

    def prop(m):
        return f'(property "Reference" "{renumber(m.group(1), band)}"'

    txt = re.sub(r'\(property "Reference" "([^"]+)"', prop, txt)
    io.open(dst, "w", encoding="utf-8", newline="\n").write(txt)
    return txt


def main():
    root_uuid = uid()
    # one sheet-instance uuid per placed sheet
    placed = [(name, f, band, page, uid()) for name, f, band, page in SHEETS]

    # group by donor file so a shared file gets all its instance paths
    by_file = {}
    for name, f, band, page, su in placed:
        by_file.setdefault(f, []).append((su, band))
    for f, entries in by_file.items():
        p = os.path.join(HW, f)
        reinstance(p, p, PROJECT, root_uuid, entries, None)

    # Sheets first, then wires, then labels. Emitting them interleaved means
    # opening and re-closing the (sheet ...) form around every pin, which is
    # how the first attempt produced a file KiCad refused to load.
    sheets, wires, labels = [], [], []
    x, y = 25.4, 25.4
    for name, f, band, page, su in placed:
        pins = sheet_pins(os.path.join(HW, f))
        w = 45.72           # 36 x 1.27 mm, so the pins land on grid
        h = max(12.7, 2.54 * (len(pins) + 1))
        if y + h > 380:
            x += 104.14     # 82 x 1.27 mm
            y = 25.4
        body = [
            f'\t(sheet\n\t\t(at {x} {y})\n\t\t(size {w} {h})\n'
            f'\t\t(fields_autoplaced yes)\n'
            f'\t\t(stroke (width 0.1524) (type solid))\n'
            f'\t\t(fill (color 0 0 0 0.0000))\n\t\t(uuid "{su}")\n'
            f'\t\t(property "Sheetname" "{name}" (at {x} {y - 0.7112} 0)'
            f' (effects (font (size 1.27 1.27)) (justify left bottom)))\n'
            f'\t\t(property "Sheetfile" "{f}" (at {x} {y + h + 1.27} 0)'
            f' (effects (font (size 1.27 1.27)) (justify left top)))']
        for i, (pname, shape) in enumerate(pins):
            py = round(y + 2.54 * (i + 1), 4)
            px = round(x + w, 4)
            ex = round(px + 7.62, 4)
            body.append(
                f'\t\t(pin "{pname}" {shape} (at {px} {py} 0)'
                f' (uuid "{uid()}")'
                f' (effects (font (size 1.27 1.27)) (justify right)))')
            net = NETS.get(name, {}).get(pname, pname)
            # A name carrying {A,B,C} is a bus vector. Joining a bus pin with a
            # plain wire is a bus_to_net_conflict -- an ERC *error*, not a
            # warning. SPI0, SPI1 and I2C0 all arrive as buses.
            kind = "bus" if "{" in pname else "wire"
            wires.append(
                f"\t({kind} (pts (xy {px} {py}) (xy {ex} {py}))"
                f' (stroke (width 0) (type default)) (uuid "{uid()}"))')
            labels.append(
                f'\t(global_label "{net}" (shape {shape})'
                f" (at {ex} {py} 0) (fields_autoplaced yes)"
                f" (effects (font (size 1.27 1.27)) (justify left))"
                f' (uuid "{uid()}"))')
        body.append(
            f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n'
            f'\t\t\t\t(path "/{root_uuid}" (page "{page}"))\n'
            f"\t\t\t)\n\t\t)\n\t)")
        sheets.append("\n".join(body))
        y += h + 7.62

    txt = "\n".join(sheets + wires + labels)

    pages = "\n".join(f'\t\t(path "/{su}" (page "{page}"))'
                      for _, _, _, page, su in placed)
    out = (
        "(kicad_sch\n\t(version 20260306)\n\t(generator \"eeschema\")\n"
        "\t(generator_version \"10.0\")\n"
        f'\t(uuid "{root_uuid}")\n\t(paper "A2")\n'
        "\t(title_block\n\t\t(title \"DrikrAIO -- Stage 1 integration\")\n"
        "\t\t(rev \"A\")\n\t)\n"
        "\t(lib_symbols)\n"
        + txt +
        "\n\t(sheet_instances\n\t\t(path \"/\" (page \"1\"))\n" + pages +
        "\n\t)\n\t(embedded_fonts no)\n)\n")
    io.open(os.path.join(HW, "DrikrAIO.kicad_sch"), "w",
            encoding="utf-8", newline="\n").write(out)
    print(f"root written: {len(placed)} sheets, root uuid {root_uuid}")


if __name__ == "__main__":
    main()
