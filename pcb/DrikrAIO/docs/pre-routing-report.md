# DrikrAIO — Pre-Routing Engineering Report

> ## ⚠ SUPERSEDED
> This document is retained for its reasoning and its correction record.
> **Current status is [pre-routing-review-2.md](pre-routing-review-2.md); the
> machine-readable baseline is [pre-routing-baseline.json](pre-routing-baseline.json).**
> Numbers here that have since been corrected: the loop-inductance budget is
> **8.72 nH**, not 7.53 nH (the old figure used the 40 V part's t_f), and the
> still-air thermal figures were computed with an over-optimistic convection
> coefficient.

**ROUTING REMAINS BLOCKED.** One requirement is unresolved (§14) and one
assembly defect must be fixed (§2).

Numbers regenerate from [`hardware/tools/power_review.py`](../hardware/tools/power_review.py).
Device data is quoted from **Infineon BSC014N06NS Final Datasheet, Revision 2.6,
2024-05-11**, table and diagram cited. Nothing is taken from a product page.

---

## 1. BSC014N06NS datasheet verification

**Package: PG-TDSON-8** (outline PG-TDSON-8-U04). Not "SuperSO8" — that is a
marketing family name; the drawing is what matters.

| Parameter | Value | Source |
|---|---|---|
| V_DS | 60 V | Table 1 |
| V_(BR)DSS | 60 V min @ I_D=1 mA | Table 4 |
| R_DS(on) | **1.2 typ / 1.45 max mΩ** @ V_GS=10 V, I_D=50 A | Table 4 |
| R_DS(on) @ V_GS=6 V | 1.6 typ / 2.2 max mΩ @ I_D=12.5 A | Table 4 |
| **R_DS(on) @ 125 °C** | **≈2.25 mΩ (×1.55)** | Diagram 9, max curve |
| V_GS(th) | 2.1 / 2.8 / 3.3 V | Table 4 |
| R_G | 2 typ / 3 max Ω | Table 4 |
| I_D @ T_c=25 °C | 257 A | Table 2 |
| I_D @ T_c=100 °C | 182 A | Table 2 |
| **I_D @ T_a=25 °C, R_thJA=50 K/W** | **31 A** | Table 2 |
| I_D,pulse | 1028 A @ T_c=25 °C | Table 2 |
| E_AS | 580 mJ (I_D=50 A, R_GS=25 Ω) | Table 2 |
| V_GS max | ±20 V | Table 2 |
| P_tot | 188 W @ T_c=25 °C / **3.0 W @ T_a=25 °C** | Table 2 |
| T_j max | **175 °C** | Table 2 |
| **R_thJC** | **0.5 typ / 0.8 max K/W** | Table 3 |
| R_thJC (top) | 20 K/W | Table 3 |
| **R_thJA** | **50 K/W**, 6 cm² one-layer 70 µm Cu, 40×40×1.5 FR4, vertical, still air | Table 3 |
| C_iss | 6500 typ / 8125 max pF @ V_DS=30 V | Table 5 |
| C_oss | 1500 typ / 1875 max pF | Table 5 |
| C_rss | 59 typ / 118 max pF | Table 5 |
| t_d(on) / t_r / t_d(off) / t_f | 23 / **10** / 43 / **11** ns @ R_G,ext=2 Ω | Table 5 |
| Q_g | 89 typ / **104 max** nC | Table 6 |
| Q_gs / Q_gd / Q_sw | 28 / **16 typ, 21 max** / 26 nC | Table 6 |
| Q_oss | 100 typ / **125 max** nC @ V_DD=30 V | Table 6 |
| V_plateau | 4.3 V | Table 6 |
| I_S / V_SD | 156 A max / 0.84 typ, 1.2 max V | Table 7 |
| t_rr / Q_rr | 52 typ, **83 max** ns / **139 typ** nC | Table 7 |

### The headline current is not board capability

**257 A is at T_c = 25 °C** — an ideal heatsink holding the case at room
temperature. The figure that describes a real board is **31 A**, and even that
assumes **6 cm² of copper per device** in still air.

| | |
|---|--:|
| Our phase RMS at peak | **29 A** = **93 %** of the 31 A figure |
| Copper the datasheet assumes, 24 FETs | 144 cm² |
| Copper available, both sides of 50 × 50 | 50 cm² |
| **Per FET, achievable** | **≈2.1 cm²** — **2.9× short** |

The 240 A in the decision table was wrong on two counts: the number is 257 A,
and it does not apply to a PCB.

## 2. Footprint verification — PASSES on copper, FAILS on paste

Measured from `4in1ESC-30x30:PDFN-8L_L6.0-W5.0-P1.27`, compared against
PG-TDSON-8-U04 (Figure 1) and Infineon's recommended land (Figure 2).

| Item | Infineon | Our footprint | Verdict |
|---|---|---|---|
| Lead pitch | 1.27 mm | 1.27 mm (measured 1.26–1.28) | ✅ |
| Lead width b | 0.26–0.54 mm | pad 0.58 mm | ✅ covers max lead |
| Lead length L | 0.45–0.72 mm | pad 1.08 mm | ✅ generous fillet |
| Recommended lead pad | 1.10 mm tall | 1.08 mm | ✅ within 0.02 |
| Recommended lead widths | 0.50 / 0.77 / 0.77 / 0.50 | 0.58 uniform | ⚠️ inner pads 0.19 mm narrower |
| Body D | 4.80–5.35 mm | footprint W5.0 | ✅ |
| Body E | 5.70–6.10 mm | footprint L6.0 | ✅ |
| Exposed pad D1×E1 | 3.70–4.40 × 3.40–3.76 | land 4.40 × 4.10 | ✅ land ≥ exposed pad |
| Recommended drain land | 4.41 × 4.55 mm | 4.40 wide; drain copper spans 4.73 mm with its leads | ✅ within 0.2 mm |
| Pin mapping | 1–3 S, 4 G, 5–8 D | pad "1"×3 S, "2" G, "3"×4 + thermal D | ✅ same topology |
| Courtyard | body 6.10 max | 6.18 × 6.74 mm | ✅ clears |
| **Solder paste, thermal pad** | **windowpane, 4 apertures** | **one 4.40 × 4.10 aperture, 18.0 mm²** | ❌ **FAIL** |

### The paste defect

The thermal pad has a **single solid 18.0 mm² paste aperture**. Infineon
specifies a windowpane. A solid aperture on a pad this size deposits far too
much solder, and the part floats, tilts and voids — which destroys the very
thermal path the pad exists to provide, on a board where §10 shows the thermal
path is the binding constraint.

**This defect is in the OpenESC-30x30 footprint as it stands**, so it affects the
current 40 V design too. **Fix before any assembly:** split into four apertures
per Figure 2 (≈1.50 × 2.52 and 1.50 × 0.95 with 0.20/0.28 gaps), target 50–70 %
paste coverage.

**Conclusion: the land pattern is compatible and may be reused. The stencil is
not, and must be corrected before the footprint is committed.**

## 3. Switching loss

At V=25.2 V, f=24 kHz (**AM32 default — assumed, not verified against our
configuration**):

| Term | Hover (21 A) | Peak (29 A) |
|---|--:|--:|
| Turn-on + turn-off, ½·V·I·(t_r+t_f)·f | 0.133 W | 0.183 W |
| Q_oss·V·f | 0.076 W | 0.076 W |
| Q_rr·V·f | 0.084 W | 0.084 W |
| **Per FET** | **0.29 W** | **0.34 W** |

Slower than the 40 V part (t_r 10 vs 5 ns) so switching loss is higher, but it
remains a minority term — and the slower edge is what buys the transient margin
in §5.

## 4. Conduction loss

R_DS(on) 1.45 mΩ max → **2.25 mΩ at 125 °C** (Diagram 9). Two devices conduct in
series at any instant.

| | Hover (21 A) | Peak (29 A) |
|---|--:|--:|
| Per FET | 0.99 W | **1.86 W** |
| Per FET, total incl. switching | 1.28 W | **2.20 W** |
| Per channel (2 conducting + 6 switching) | 3.74 W | **5.77 W** |
| **All four channels** | **15.0 W** | **23.1 W** |

Against the 40 V SP40N01GHNK this is 15.0/23.1 W versus 12.7/20.9 W — about
10 % more, from the slower edges and higher Q_rr, not from R_DS(on).

## 5. Loop-inductance verification

The 7.53 nH figure was computed with the **40 V part's** t_f of 9.5 ns. With
BSC014N06NS's verified t_f = 11 ns the edge is slower and the budget is larger:

| | Value |
|---|--:|
| di/dt = 29 A / 11 ns | **2.61 A/ns** |
| Allowed spike to 100 % V_DS (60 − 25.2) | 34.8 V → **13.31 nH** |
| **Allowed spike to 80 % V_DS (48 − 25.2)** | **22.8 V → 8.72 nH** |

**Corrected budget: 8.72 nH at 80 % derating**, not 7.53 nH. Against the 40 V
part's 2.25 nH this is **3.9× more headroom** — the reason for the change.

8.72 nH is a routable target: roughly 8 mm of loop. 2.25 nH was not.

## 6. Local capacitor requirements

- **≥ 2 × 4.7 µF 1206 X5R 50 V within 2 mm** of each half-bridge, same side,
  loop closed on the adjacent inner ground plane.
- Commutation loop (high-side drain → low-side source → cap → back) **≤ 8 mm
  total path**, budgeted against §5's 8.72 nH.
- Return directly beneath the loop on In1. **No plane split under any bridge.**
- Bulk 470 µF 50 V electrolytic at the battery entry only. Its ESL is orders of
  magnitude above the budget — it is not part of the switching loop.
- Retain OpenESC's 52 × 4.7 µF bank.

**X5R capacitance at 25 V bias is UNKNOWN** without the specific part's bias
curve. Do not trim the bank on nominal values.

## 7. 115 A multilayer bus architecture

**A single 6.6 mm outer trace is not the bus.** 6.6 mm is a netclass floor that
stops a hand-route necking down; the conductor is a pour on all six layers.

| Construction | Copper area | 115 A adiabatic rise |
|---|--:|--:|
| 2 oz outer only, 20 mm wide | 1.39 mm² | 34.0 °C/s → 30 °C in **0.9 s** |
| **2 outer + 4 inner, 20 mm wide** | **5.57 mm²** | **2.13 °C/s → 30 °C in 14.1 s** |

Required: ≥ 20 mm effective width on **all six layers**, stitched with ≥ 40 vias
per transition (§11). Resistance 3.09 µΩ/mm → 8.9 mV and 1.02 W over 25 mm at
115 A.

## 8. 42 A continuous thermal

IPC-2221, 2 oz outer, 20 °C rise: **42 A needs 17.2 mm** of outer copper as a
pour. On the six-layer bus the drop is 3.2 mV and the loss 0.14 W over 25 mm —
negligible. Continuous operation is not the problem.

## 9. Peak thermal

| Case | Board total | Still air | Propwash ~5 m/s |
|---|--:|--:|--:|
| Hover | 16.0 W | +42.6 °C → 82.6 °C | +10.7 °C → 50.7 °C |
| Peak | 26.2 W | **+70.0 °C → 110.0 °C** | +17.5 °C → 57.5 °C |

*(Board totals computed with the 40 V part; with BSC014N06NS add ~2 W.)*

**The board is cooled by the propellers.** Bench testing at peak in still air
will exceed the envelope. Convection coefficients are textbook ranges, not
measured — the conclusion survives the uncertainty, the exact numbers do not.

## 10. FET junction temperature — the binding constraint

| Case | P per FET | R_θ(j-a) for T_j<125 °C | for T_j<175 °C |
|---|--:|--:|--:|
| Hover | 1.28 W | 66.2 K/W | 105.1 K/W |
| **Peak** | **2.20 W** | **38.6 K/W** | 61.4 K/W |

R_θJC is 0.5–0.8 K/W, so **essentially the entire budget is case-to-ambient**,
which is a layout property.

The datasheet's 50 K/W assumes 6 cm² per device. **We can give ≈2.1 cm².** With
less copper, R_θ(j-a) will be worse than 50 K/W in still air — and 38.6 K/W is
needed at peak for a 125 °C junction. **The still-air peak case does not close.**

T_j max is 175 °C (versus 150 °C for the 40 V part), which is real margin: at
175 °C the budget relaxes to 61.4 K/W. Designing to 125 °C is the conservative
choice and should be held unless measurement says otherwise.

**Requirement:** ≥ 100 mm² of connected pour per drain pad, ≥ 9 thermal vias,
and **R_θ(j-a) measured on the first board**. This is the number that decides
whether the design works, and it cannot be settled on paper.

## 11. Via current

0.3 mm drill, 25 µm plating: 0.0255 mm², **1.08 mΩ per via**.

| Path | Current | Minimum vias |
|---|--:|--:|
| Bus continuous | 42 A @ 1.5 A/via | **28** |
| Bus peak | 115 A @ 3.0 A/via | **38** |
| Phase hover | 21 A @ 1.5 A/via | **14** |
| Phase peak | 29 A @ 3.0 A/via | **10** |

≥ 40 per bus transition, ≥ 16 per phase, ≥ 9 per FET thermal pad, distributed
across the pour rather than in a row.

## 12. Connector analysis

**J1, JST SM08B-SRSS-TB: 0.7 A per contact, 50 V, 20 mΩ initial / 40 mΩ after
environmental testing.**

J1 pin 1 carries `+BATT` — **60× under** continuous bus current, **164× under**
peak. **J1 is a signal and breakout connector only.** Decision recorded: it is
not a battery-current entry.

Battery enters on U3's pads: **VBAT and BATGND, 4.5 × 15 mm, 67.5 mm² each**,
sized for soldered leads. Motor phases on U3: 2.2 × 1.2 mm × 2 per phase =
5.28 mm², adequate for soldered wire at 29 A.

## 13. Netclass and DRC verification

`tools/verify_netclasses.py` is an **independent** check. DRC status alone is
not evidence: a board that has lost its rules passes DRC because there is
nothing left to violate.

```
classes found: 8 -> Analog Default Gate Phase Power RF USB VBAT
ok  Phase.track_width 6.6   via 0.8/0.4
ok  VBAT.track_width  6.6   via 0.8/0.4
custom rules: 7
All expected netclasses, widths, via rules and DRC rules present.
```

### Two regressions found and fixed

`pcbnew.SaveBoard()` rewrites `DrikrAIO.kicad_pro` on **every** save:

1. It replaced all eight netclasses with a bare `Default` (found by inspection).
2. It relaxed **ten** board-level minimums — including `min_clearance` to
   **0.0**, `min_track_width` 0.09 → 0.2, `min_via_diameter` 0.35 → 0.5
   (found by the verifier, after the first fix guarded only `net_settings`).

`build_pcb.py` now snapshots both blocks, saves, reloads, restores anything that
moved, and runs the verifier. On the last rebuild it reported:
`RESTORED after SaveBoard: 8 netclasses, 10 design rules`.

**Rule: no DRC result is valid unless `verify_netclasses.py` exits 0 for the
same board state.**

## 14. Remaining unresolved requirements

| # | Item | Blocks |
|---|---|---|
| 1 | **115 A peak duration and repetition rate.** Undefined in firmware, sizing model and ArduPilot parameters. Do not invent one. | Transient thermal, repeated-peak, copper, junction and connector temperature calculations — all five |
| 2 | **Thermal-pad paste apertures** — single 18 mm² aperture must become a windowpane | Assembly of any board |
| 3 | **R_θ(j-a) at ≈2.1 cm²/FET.** Datasheet gives 50 K/W at 6 cm². Peak needs 38.6 K/W. Still-air peak does not close on paper. | Peak thermal sign-off |
| 4 | PWM frequency — 24 kHz assumed from AM32 default, unverified | Switching-loss accuracy |
| 5 | X5R capacitance at 25 V bias | Capacitor bank sizing |
| 6 | BSC014N06NS stock and price at 24/board | Procurement |
| 7 | Fabricator capability: 2 oz outer at 0.16 mm features | Manufacturing release |

### Gate status

| | |
|---|---|
| Sections 1–13 | ✅ complete |
| §14 item 1 | ❌ **blocks routing** |
| §14 item 2 | ❌ must be fixed before assembly |
| §14 item 3 | ⚠️ measurement required on first board |

**Routing remains blocked on item 1.** Once the peak duration is defined, the
five dependent calculations can be completed and this report re-issued.

The part is **not committed to the schematic** — `ESC.kicad_sch` still carries
SP40N01GHNK, as instructed.
