# DrikrAIO — Stage 1

Single-board integration of a flight controller, four ESC channels and an
ExpressLRS receiver, assembled from proven OpenDrone designs.

**Status: schematic netlists; board is a placed scaffold, unrouted.** See *Open work*.

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

## Board

`DrikrAIO.kicad_pcb` exists as a **scaffold, not a layout**. 50 x 50 mm on the
30.5 mm mounting pattern, 6 layers, 2 oz outer / 1 oz inner, ENIG. Nothing is
routed.

```
50 x 50 mm      6 layers      347 footprints      1283 pads netted
292 placed on board            55 staged off-board, grouped by block
0 overlaps                     0 parts crossing the edge
```

Placement is by function: power stages in four quadrants on the bottom with
the shared power block across the middle, control on top, receiver in a corner
for the antenna. Where a zone filled up the remainder is staged **outside** the
outline in per-block columns, which is what KiCad does with new parts -- better
an honestly unplaced part than one silently overlapping its neighbour.

**Board size was measured, not chosen.** U3's pad set alone spans 44.0 x 45.8 mm
so 45 mm could not contain it, and the other 346 parts come to 2409 mm2 of
footprint area -- 48 % of a two-sided 50 mm board, which leaves room to route.

Rebuild it with:

```sh
"C:/Program Files/KiCad/10.0/bin/python.exe" hardware/tools/build_pcb.py
```

## Reviews

# ROUTING STATUS: BLOCKED — BASELINE FROZEN

**[docs/routing-readiness-report.md](docs/routing-readiness-report.md) is current.**
Baseline rev 3, frozen: [docs/pre-routing-baseline.json](docs/pre-routing-baseline.json),
[docs/freeze-manifest.json](docs/freeze-manifest.json).

Verify the freeze at any time:

```sh
python hardware/tools/freeze.py     # exit 0 = intact
```

Primary remaining thermal variables are **airflow exposure and duty cycle**.
More copper is **not** the primary solution.

Blocked on: 115 A peak duration, peak repetition rate, airflow boundary
condition, thermal validation plan, and the deferred MOSFET schematic commit.

**Thermal is MARGINAL, not PASS.** Only one steady-state case passes — hover in
developed slipstream (103.2 C). Peak fails the 125 C target at both airflows
(132.7 C slipstream, 169.9 C at the disc). Still air reaches 393 C and is
prohibited above quiescent.

The result that redirects the work: Rth(j-c) + R_spread contribute only **5.7 K**
of the rise. **More vias and more copper cannot fix the peak case** — the
bottleneck is board-to-air. The only levers are airflow exposure and duty cycle.

The result that may make it moot: board time constant is **31-45 s**, so a peak
much shorter than that barely moves the board. At h=60, duty up to 0.5 stays
under target. But duty cycle is OPEN, so no row can be selected.

Analysis: [docs/thermal-analysis.md](docs/thermal-analysis.md) ·
Validation: [docs/thermal-validation-plan.md](docs/thermal-validation-plan.md)

## Electrical design review

**[docs/electrical-design-review.md](docs/electrical-design-review.md) gates
routing.** Numbers regenerate from `hardware/tools/power_review.py`.

**Resolved:** `Phase` and `VBAT` netclasses corrected 1.0 mm → 6.6 mm with
0.8/0.4 vias (1.0 mm carries 5.3 A against a 21 A phase RMS), and the MOSFET
decision is **60 V minimum**.

**Preferred part: Infineon BSC014N06NS**, verified against the manufacturer
datasheet (Rev 2.6) in [docs/pre-routing-report.md](docs/pre-routing-report.md).
Package is **PG-TDSON-8**. Land pattern **passes** the arithmetic against
`PDFN-8L_L6.0-W5.0-P1.27`; the **stencil does not** — the thermal pad has one
18 mm² paste aperture where Infineon specifies a windowpane, a defect the
current OpenESC footprint already carries. Loop budget corrected to **8.72 nH**
on the real t_f of 11 ns, 3.9× the 40 V part. Not committed to the schematic.

**The headline current is not board capability:** 257 A is at T_c=25 °C. On a
PCB in still air the datasheet says **31 A**, assuming 6 cm² of copper per
device — and 24 FETs on a 50 × 50 board get about 2.1 cm² each.

**Still open: the 115 A peak duration** is undefined anywhere in the repo, so
repeated peaks cannot be assessed. Firmware parameter, not a PCB one.

Also established: 115 A needs 69 mm of 2 oz outer copper on a 50 mm board, so
the bus must use **all six layers**; J1 is 0.7 A per contact and is a breakout
only, never a battery path; and the board is cooled by propwash — at peak in
still air it reaches ~110 °C.

## Open work

1. **Routing, and real placement.** The scaffold groups parts correctly; it does
   not lay them out. Four switching power stages, a 2.4 GHz chain and a 115 A
   battery entry share this board, and that is judgement work, not a generator's.
   Start by pulling the 55 staged parts in and putting the IMU near the board
   centre -- the scaffold parks it at the right edge for want of a free zone.
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
