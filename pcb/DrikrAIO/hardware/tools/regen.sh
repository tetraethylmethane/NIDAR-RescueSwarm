#!/usr/bin/env bash
# Rebuild the DrikrAIO schematic from the upstream donor sheets.
#
# Every sheet in this project is a copy of a proven OpenDrone sheet, re-instanced
# and re-annotated for this project. That rewrite is not idempotent -- running it
# twice over an already-rewritten sheet renumbers it again -- so the donors are
# re-copied first and the whole set is rebuilt from scratch every time.
#
# Run from anywhere. Requires KiCad 10 for the checks at the end.
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HW="$(dirname "$HERE")"
PCB="$(dirname "$(dirname "$HW")")"
TOOLS="$HERE"

FC="$PCB/OpenFC-Lite-Mini-main/hardware"
ESC="$PCB/OpenESC-30x30-main/hardware"
AIO="$PCB/OpenAIO-main/hardware"

echo "== restoring donor sheets =="
for f in rp2350a power imu osd blackbox pads; do
  cp "$FC/$f.kicad_sch" "$HW/"
done
cp "$ESC/ESC.kicad_sch"                "$HW/"
cp "$AIO/rx_esp32c3_sx1281.kicad_sch"  "$HW/"

echo "== extracting the ESC power + current-sense block =="
python "$TOOLS/make_esc_power.py"

echo "== building the root =="
python "$TOOLS/build_root.py"

CLI="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
if [ -x "$CLI" ]; then
  echo "== ERC =="
  "$CLI" sch erc --format report -o "$HW/erc.rpt" "$HW/DrikrAIO.kicad_sch" || true
  echo "errors:   $(grep -B1 '; error'   "$HW/erc.rpt" | grep -cE '^\[' || true)"
  echo "warnings: $(grep -B1 '; warning' "$HW/erc.rpt" | grep -cE '^\[' || true)"
fi
