# DrikrAIO — Stage 1

Single-board integration of a flight controller, four ESC channels and an
ExpressLRS receiver, assembled from proven OpenDrone designs.

**Status: schematic assembles, netlists, and is not finished.** See *Open work*.

This is Stage 1 of two. It deliberately targets FPV-class hardware on the parts
that already fly, to prove the integration once. Stage 2 re-platforms to
ArduPilot on a Pixhawk Autopilot Bus carrier and reuses the power tree, ESC
block and layout zoning proven here.

## Licence and attribution

**CERN-OHL-S-2.0, strongly reciprocal**, inherited from the upstream sources.
Every sheet in `hardware/` is copied from an [OpenDrone-hw](https://github.com/OpenDrone-hw)
project by @Just4Stan / incutec. This board is a derivative work; its complete
sources are published under the same licence, as that licence requires.

| Sheet | Copied from | Upstream status |
|---|---|---|
| `rp2350a`, `power`, `imu`, `osd`, `blackbox`, `pads` | OpenFC-Lite-Mini rev3.3 | Shipping. Rev2 flown. |
| `ESC` (×4) | OpenESC-30x30 rev3.3 | Shipping. Rev1 validated build. |
| `rx_esp32c3_sx1281` | OpenAIO (itself from OpenRX-Lite) | Routed, never manufactured |
| `KiCad-Library/` | OpenDrone-hw/KiCad-Library | Shared parts catalogue |

## Design decisions

**40 V MOSFETs, not 30 V.** OpenAIO uses the DOY180N03T, 30 V, which on a 6S
pack at 25.2 V leaves 1.19× margin — below what half-bridge ringing reaches.
The `ESC` sheet is taken from OpenESC-30x30 instead, which uses the 40 V
SP40N01GHNK at 1.59× and is rated to 8S. This is why the ESC sheet comes from
the 30×30 rather than from OpenAIO.

**30.5 × 30.5 mm mount.** Four PDFN-8L 5×6 power stages do not fit on OpenAIO's
25.5 mm — that is precisely why upstream used the smaller 30 V part. The larger
mount also removes the crowding that left OpenAIO with 74 unrouted pads.

**Two power trees, kept separate.** The FC sheet makes +10 V, +5 V, +3V3 and
+1V8; the ESC needs its own +10 V gate rail and +3V3. They are **not** merged.
The FC's +10 V is gated by `10V_ENABLE` (a firmware PINIO, there to switch a
VTX), and a firmware toggle that cuts gate drive in flight is not a rail an ESC
may share. The ESC keeps the LMR54406 buck and TLV76733 LDO from OpenESC-30x30.

**SX1281, 2.4 GHz.** Not the dual-band LR1121. The 865–867 MHz safety link
([`communication/safety_link/`](../../communication/safety_link/)) must be a
physically separate radio: the reason to abort is usually that the primary link
has failed, so an abort path sharing that radio is not an abort path.

## Reference bands

Each sheet numbers into its own band, so a reference says which block it is in
and nothing collides. The four ESC channels share one file and are distinguished
by band.

| Band | Sheet | | Band | Sheet |
|---|---|---|---|---|
| 1xx | rp2350a | | 6xx | pads |
| 2xx | power | | 7xx | rx |
| 3xx | imu | | 11xx | ESC channel 1 |
| 4xx | osd | | 12xx | ESC channel 2 |
| 5xx | blackbox | | 13xx | ESC channel 3 |
| | | | 14xx | ESC channel 4 |

## State

```
components 318      nets 563      sheets 11
ERC        25 errors, 467 warnings
```

All 25 errors are the same missing block (below). Of the warnings, 381 are
`pin_to_pin` inherited from the donor sheets — the same findings those boards
ship with — and 61 are unresolved `ESCLibrary` / `PCM_*` symbol libraries, which
are KiCad PCM add-ons. Symbols are embedded in the schematics, so the design
opens and netlists without them; install them only to re-place those parts.

## Open work

1. **Board power entry and ESC current sense — the 25 ERC errors.** The donor
   projects kept this on their own root sheets, so it did not come across with
   the sub-sheets. Needs: battery connector, `PWR_FLAG` on +BATT/GND, the two
   0.2 mΩ shunts in parallel, INA186A3 current-sense amp driving `ESC_CURRENT`,
   and the ESC's LMR54406 → +10 V and TLV76733 → +3V3 rails.
2. **Motor phase outputs.** `M1_A`…`M4_C` are twelve nets that currently
   terminate at global labels and need pads.
3. **Review the generated root in KiCad.** `DrikrAIO.kicad_sch` was produced by
   a script, not drawn. It wires sheets with global labels on stubs, which is
   electrically correct and reviewable, but it is not a drawn schematic.
4. **PCB layout.** Not started. No `.kicad_pcb` exists yet.

## Build

```sh
kicad-cli sch erc hardware/DrikrAIO.kicad_sch
kicad-cli sch export netlist --format kicadsexpr -o /tmp/DrikrAIO.net hardware/DrikrAIO.kicad_sch
```

Requires KiCad 10. The files are KiCad 10 format and KiCad 8 cannot open them.
