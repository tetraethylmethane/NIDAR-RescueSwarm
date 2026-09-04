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
| `esc_power` | OpenESC-30x30 rev3.3 root sheet | Shipping |
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
| 8xx | esc_power | | 14xx | ESC channel 4 |

## State

```
components 347      nets 332      sheets 12
ERC        30 errors, 546 warnings
```

**The 30 errors are inherited, not introduced.** The donor boards report the
same classes: OpenFC-Lite-Mini, which has flown, reports 8 `power_pin_not_driven`,
and OpenESC-30x30, in production, reports 24 `pin_not_driven` and 3
`power_pin_not_driven`. Summed across what we instantiate, the donor baseline is
about 37; this design sits below it. `PWR_FLAG`s were tried on +BATT and GND and
removed again -- they cleared none of the old errors and added two new
`label_dangling`, and a new error type is a regression where an existing one is
not. Resolve these in KiCad against the real symbols.

Most of the warnings are the same story: `pin_to_pin` inherited from the donor
sheets, plus unresolved `ESCLibrary` / `PCM_*` symbol libraries, which are KiCad
PCM add-ons. Symbols are embedded in the schematics, so the design opens and
netlists without them; install them only to re-place those parts.

## Open work

1. **PCB layout.** Not started; no `.kicad_pcb` exists. This is the bulk of the
   remaining work and it is not a job for a generator: four switching power
   stages, a 2.4 GHz chain and a 115 A-capable battery entry share one board.
2. **Review the generated root in KiCad.** `DrikrAIO.kicad_sch` was produced by
   a script, not drawn. It wires sheets with global labels on stubs, which is
   electrically correct and reviewable, but it is not a drawn schematic.
3. **Resolve the 30 inherited ERC errors** against the real symbols, or record
   them as accepted the way the donor projects do.
4. **`+3.3V` and `+3V3` are different nets** -- the FC rail and the ESC rail,
   deliberately separate per the power-tree decision above. The names differ by
   one character and mean different things, which is a trap. Consider renaming
   the FC rail to `+3V3_FC` before layout.

### Done

Board power entry, ESC current sense and the motor pads all arrived with
`esc_power`. `U3` in that sheet is not a board outline -- an earlier pass
mistook it for one and deleted it -- it is the ESC's whole pad set: VBAT,
BATGND, CUR, M1-M4 and the twelve phase pads 1A..4C. Verified in the netlist:
`ESC_CURRENT` reaches the FC ADC, `+10V` reaches all four gate-driver rails,
`M1_A` runs from the channel-1 MOSFETs to its pad, and `MOTOR1` runs from the
FC MCU to the channel-1 DShot input.

## Build

Every sheet here is a rewritten copy of a donor. That rewrite is not
idempotent, so rebuild the whole set rather than editing in place:

```sh
bash hardware/tools/regen.sh
```

```sh
kicad-cli sch erc hardware/DrikrAIO.kicad_sch
kicad-cli sch export netlist --format kicadsexpr -o /tmp/DrikrAIO.net hardware/DrikrAIO.kicad_sch
```

Requires KiCad 10. The files are KiCad 10 format and KiCad 8 cannot open them.
