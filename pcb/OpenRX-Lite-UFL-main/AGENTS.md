# OpenRX Lite-UFL

Open-source 2.4 GHz ExpressLRS receiver. An ESP32-C3 controls an SX1281 radio;
the ELRS link terminates in a U.FL connector, while a separate ceramic antenna
serves the ESP32-C3 Wi-Fi interface.

## Repo

| | |
|---|---|
| Maintainer | @bastian2001 |
| Status | See the `status-*` topic on the repo. Never written here. |
| Designed in | KiCad 10 |
| KiCad project | `hardware/OpenRX-Lite-UFL.kicad_pro` |
| Root schematic | `hardware/OpenRX-Lite-UFL.kicad_sch`; radio/core sheet `hardware/esp32c3_sx1281_lite.kicad_sch` |
| Board | `hardware/OpenRX-Lite-UFL.kicad_pcb`, 6 layers, 1.0 mm |
| Local library | `hardware/lib.pretty/` and `hardware/lib.3dshapes/`, nickname `OpenRX-Shared` retained by the design; `shared/libs/OpenRX-Shared.3dshapes` is a compatibility link for embedded legacy model paths |
| Shared library | `hardware/KiCad-Library/`, submodule of [OpenDrone-hw/KiCad-Library](https://github.com/OpenDrone-hw/KiCad-Library), nickname `OpenDrone`; exact component datasheets resolve through the project text variable `OPENDRONE_LIB` |
| Design rules | `hardware/OpenRX-Lite-UFL.kicad_dru` |
| Fab config | `hardware/fabrication-toolkit-options.json` |
| Firmware target | `firmware/OpenRX Lite-UFL 2400.json` and `firmware/targets_entries.json` |
| Board setup | Standard: 6 layers, 0.09 mm clearance and track, via 0.35 on 0.20 drill |
| License | CERN-OHL-S-2.0 |

## Parts and datasheets

- **Per-repository part index:** `hardware/OpenRX-Lite-UFL.kicad_sch` and its
  listed sub-sheet are authoritative for what this board fits. Export the
  netlist with the command below when a script-readable board index is needed;
  do not maintain a second hand-written BOM.
- **Proven shared parts:**
  `hardware/KiCad-Library/PARTS-USED.md` is the catalogue index. Its `Boards`
  column identifies every repository using each LCSC part; filter it for
  `OpenRX-Lite-UFL` to get this repository's proven shared-part view.
- **Exact datasheets:**
  `hardware/KiCad-Library/datasheet/manifest.json` maps shared symbols to the
  committed PDFs and their SHA-256 hashes. The PDFs live in
  `hardware/KiCad-Library/datasheet/`, and symbol links resolve there through
  `OPENDRONE_LIB`.
- **Local-only parts:** inspect `hardware/lib.pretty/` and
  `hardware/lib.3dshapes/`, then verify supplier fields in the board
  schematic. Do not duplicate a shared part or datasheet.

## Rules

Identical in every OpenDrone board repo. Do not edit here; edit the template.

- **Never text-edit** `.kicad_sch`, `.kicad_pcb` or `.kicad_dru`. Use KiCad, or
  kicad-skip / the pcbnew API for scripted changes. `.kicad_pro` is JSON and may
  be edited directly for metadata.
- **Metadata yes, connections no.** An agent may write BOM and documentation
  fields (MPN, Manufacturer, LCSC, Cost, Datasheet, text variables). An agent
  may not change nets, wiring, routing, placement, footprint assignment, or any
  value that changes the circuit.
- **Close KiCad before any write to a KiCad file.** KiCad caches library tables
  at process start and overwrites files on save.
- **Reuse before you draw.** Check the `OpenDrone` library and its
  `PARTS-USED.md` first. If the part is there we have already sourced,
  footprinted and shipped it, and its symbol links to the exact committed
  datasheet: place it from `OpenDrone`. Draw a new part into `lib` only when
  the catalogue has nothing that fits, imported with `easyeda2kicad` from its
  LCSC number. Pulling a newer catalogue is a deliberate, reviewed commit:
  `git submodule update --remote hardware/KiCad-Library`, then DRC.
- **One person holds a board layout at a time.** KiCad files do not merge. Say
  on Discord that you are taking it. See [CONTRIBUTING.md](CONTRIBUTING.md).
- **Run ERC and DRC before every pull request.** Existing approved findings
  may remain; a new type or increased count must be reviewed before merge.
  Commands below.

## Environment

```sh
kicad-cli sch erc hardware/OpenRX-Lite-UFL.kicad_sch
kicad-cli pcb drc --schematic-parity --refill-zones hardware/OpenRX-Lite-UFL.kicad_pcb
kicad-cli sch export netlist --format kicadsexpr -o /tmp/OpenRX-Lite-UFL.net hardware/OpenRX-Lite-UFL.kicad_sch
```

On macOS `kicad-cli` is at
`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, and `pcbnew` imports
only under KiCad's bundled Python. Reusable scripts for renders, STEP export,
and packaging art come from Incutec hardware tooling. The OpenDrone release
standard lives in `OpenDrone-hw/.github/RELEASES.md`; board-specific scripts
live in `hardware/tools/`.

## Architecture

The ESP32-C3 (U1) runs ExpressLRS, communicates with the flight controller over
UART0/CRSF, and drives the WS2812B status LED (D1). The SX1281 (U3) uses SPI and
a 52 MHz TCXO. Its 2.4 GHz RFIO passes through the 2450FM07D0034T filter (FL1)
to U.FL connector J1; there is no PA, LNA or RF switch. The
2450AT18A100E antenna (AE1, net `WIFI`) belongs only to the ESP32-C3 Wi-Fi
interface used for flashing and configuration.

## Key parts

| Function | Ref | Part | LCSC | Note |
|---|---|---|---|---|
| MCU | U1 | ESP32-C3 | | QFN-32 |
| 3.3 V LDO | U2 | TLV75533PDQNR | C2861882 | 500 mA |
| 2.4 GHz radio | U3 | SX1281IMLTRT | C2151551 | |
| 2.4 GHz filter | FL1 | 2450FM07D0034T | C2651081 | |
| ELRS connector | J1 | U.FL-R-SMT-1(80) | C88374 | 50 ohm |
| Wi-Fi antenna | AE1 | 2450AT18A100E | C89334 | ESP32-C3 only |
| Radio TCXO | OSC1 | OW7EL89CENUNFAYLC-52M | C22434896 | 52 MHz |
| MCU crystal | X1 | CJ17-400001010B20 | C2875272 | 40 MHz |
| Status LED | D1 | XL-1010RGBC-WS2812B | C5349953 | |

## Power

```text
5V pad (TP3)
└── TLV75533PDQNR (U2), 3.3 V
    ├── ESP32-C3 (U1) and status LED (D1)
    └── SX1281 (U3) and 52 MHz TCXO (OSC1)
```

## Connectors and I/O

| Pad | Net | ESP32-C3 | Function |
|---|---|---|---|
| RX (TP1) | U0RXD | GPIO20 | CRSF serial input |
| TX (TP2) | U0TXD | GPIO21 | CRSF telemetry output |
| 5V (TP3) | +5V | - | Supply input |
| GND (TP4) | GND | - | Ground |
| BOOT (TP5) | BOOT | GPIO9 | UART download mode when held low at power-up |

Radio SPI is SCK/MOSI/MISO on GPIO6/4/5; NSS/RST/BUSY/DIO1 are GPIO7/2/3/1.
The RGB status LED is GPIO8 in GRB order.

## Firmware

ExpressLRS target `Unified_ESP32C3_2400_RX`, platform `esp32-c3`, minimum
version 3.5.0. Upload methods are UART, Wi-Fi and Betaflight passthrough. The
authoritative GPIO and power values are in
`firmware/OpenRX Lite-UFL 2400.json`.

## Layout rules

Preserve the short 50-ohm SX1281-to-filter-to-U.FL path, its ground-via fence,
and the Wi-Fi antenna keepout. Keep the external ELRS antenna away from the
on-board Wi-Fi antenna in the product installation.

## Revisions

| Rev | Date | Change |
|---|---|---|
| rev2 | 2026-08-14 | Fab set re-exported and verified; U.FL LCSC field corrected. |
| rev1 | 2026-03-23 | First released OpenRX Lite-UFL design. |
