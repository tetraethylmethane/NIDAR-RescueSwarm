# DrikrAIO — Pre-Routing Engineering Review (Rev 2)

## GO / NO-GO: **NO-GO**

Routing is blocked on **one** requirement. Four of the five gate conditions now
pass; the fifth is not mine to close.

| Gate condition | Status |
|---|---|
| BSC014N06NS parameters verified from Rev 2.6 | ✅ §2 |
| Footprint stencil corrected | ✅ §3 — 25/25 checks pass |
| SaveBoard regression verifier passes | ✅ §10 — failure reproduced and guarded |
| Thermal architecture demonstrated feasible | ✅ §4 — **but only with propwash** |
| 115 A peak duration / repetition defined | ❌ **UNRESOLVED** |

**115 A peak-duration requirement unresolved.**

Sources: `tools/power_review.py`, `tools/thermal_model.py`,
`tools/verify_fet_footprint.py`, `tools/verify_netclasses.py`,
`tools/test_save_cycle.py`. Device data is Infineon **BSC014N06NS Final
Datasheet Rev 2.6, 2024-05-11**.

---

## 1. MOSFET selection

**Infineon BSC014N06NS**, 60 V, PG-TDSON-8. Confirmed against three 60 V
candidates: it is the only one that buys transient margin without paying for it
in conduction loss, because at 1.45 mΩ max it is *lower* resistance than the
40 V part being replaced.

The 40 V architecture is rejected: its 80 %-derated loop-inductance budget is
2.25 nH, about 2 mm of loop, which cannot be guaranteed.

**Not committed to the schematic.** `ESC.kicad_sch` still carries SP40N01GHNK.

## 2. Datasheet-verified parameters

Every row **DATASHEET** unless marked. Nothing inferred from another part.

| Parameter | Value | Condition | Status |
|---|---|---|---|
| V_DS | 60 V | Table 1 | DATASHEET |
| V_(BR)DSS | 60 V min | I_D=1 mA, V_GS=0 | DATASHEET |
| R_DS(on) | 1.2 typ / **1.45 max** mΩ | **V_GS=10 V, I_D=50 A** | DATASHEET |
| R_DS(on) | 1.6 typ / 2.2 max mΩ | V_GS=6 V, I_D=12.5 A | DATASHEET |
| R_DS(on) @125 °C | ≈2.25 mΩ | ×1.55 off Diagram 9 max curve | CALCULATED |
| I_D | 257 A / 182 A / **31 A** | T_c=25 °C / T_c=100 °C / **T_a=25 °C at R_thJA=50 K/W** | DATASHEET |
| I_D,pulse | 1028 A | T_c=25 °C | DATASHEET |
| V_GS | ±20 V | — | DATASHEET |
| V_GS(th) | 2.1 / 2.8 / 3.3 V | V_DS=V_GS, I_D=120 µA | DATASHEET |
| R_G | 2 typ / 3 max Ω | by design | DATASHEET |
| C_iss | 6500 / 8125 pF | V_GS=0, V_DS=30 V, 1 MHz | DATASHEET |
| C_oss | 1500 / 1875 pF | as above | DATASHEET |
| C_rss | 59 / 118 pF | as above | DATASHEET |
| Q_g | 89 / **104 max** nC | V_DD=30 V, I_D=50 A, 0→10 V | DATASHEET |
| Q_gs | 28 nC | as above | DATASHEET |
| Q_gd | 16 / 21 max nC | as above | DATASHEET |
| Q_sw | 26 nC | as above | DATASHEET |
| Q_oss | 100 / **125 max** nC | V_DD=30 V, V_GS=0 | DATASHEET |
| V_plateau | 4.3 V | as above | DATASHEET |
| t_d(on) / **t_r** | 23 / **10** ns | V_DD=30 V, V_GS=10 V, I_D=30 A, R_G,ext=2 Ω | DATASHEET |
| t_d(off) / **t_f** | 43 / **11** ns | as above | DATASHEET |
| I_S / I_S,pulse | 156 / 1028 A | T_c=25 °C | DATASHEET |
| V_SD | 0.84 / 1.2 max V | V_GS=0, I_S=50 A | DATASHEET |
| t_rr | 52 / 83 max ns | V_R=30 V, I_F=50 A, di/dt=100 A/µs | DATASHEET |
| **Q_rr** | **139 nC typ** | as above | DATASHEET |
| **R_thJC** | **0.5 typ / 0.8 max K/W** | — | DATASHEET |
| R_thJC (top) | 20 K/W | — | DATASHEET |
| **R_thJA** | **50 K/W** | 6 cm² one-layer 70 µm Cu, 40×40×1.5 FR4, vertical, still air | DATASHEET |
| Z_thJC(t) | 0.010 / 0.030 / 0.10 / 0.30 / 0.50 K/W at 0.1/1/10/100/1000 ms | single pulse, Diagram 4 | **READ FROM GRAPH ±30 %** |
| E_AS | 580 mJ | I_D=50 A, R_GS=25 Ω | DATASHEET |
| P_tot | 188 W / 3.0 W | T_c=25 °C / T_a=25 °C at 50 K/W | DATASHEET |
| T_j max | **175 °C** | — | DATASHEET |
| **Z_thJA(t)** | — | — | **UNKNOWN** — not in Rev 2.6 |
| **R_thJA for our copper** | — | — | **UNKNOWN** — layout property, §4 estimates it |

**The 257 A headline is not a board rating.** It is T_c=25 °C, an ideal
heatsink. The PCB-referenced figure is 31 A.

## 3. Corrected footprint

New canonical footprint: **`lib.pretty/BSC014N06NS_PG-TDSON-8.kicad_mod`**,
derived from the verified OpenESC land. **No electrical geometry changed.**

| Check | Result |
|---|---|
| Lead pads, count / size | 8 × 0.58 × 1.08 mm ✅ |
| Pitch, measured per row | 1.26–1.28 mm vs 1.27 ✅ |
| Lead pad vs package b (0.26–0.54) / L (0.45–0.72) | covers both ✅ |
| Thermal pad copper | 4.40 × 4.10 mm, unchanged ✅ |
| vs exposed pad D1 3.70–4.40 / E1 3.40–3.76 | inside / exceeds ✅ |
| vs recommended drain land 4.41 | within 0.01 mm ✅ |
| Pad numbering & topology | 3 S / 1 G / 4 D + thermal ✅ |
| Mask opening on thermal pad | present ✅ |
| **Paste on thermal pad itself** | **removed** ✅ |
| **Paste windows** | **4 × 1.70 × 1.55 mm** ✅ |
| **Coverage** | **58.4 %** (Infineon's own ≈52 %) ✅ |
| Window spacing / inset | 0.40 / 0.30 mm ✅ |
| Windows inside pad | ✅ |
| Extent vs max body 5.35 × 6.10 | 6.41 × 7.29 mm ✅ |
| **Courtyard** | **added — the donor had none** ✅ |
| Silkscreen | 14 items ✅ |

**25 checks, 25 pass.**

Two defects fixed, both inherited and both present in the 40 V design today:

1. **Single 18.04 mm² solid paste aperture** on the thermal pad. Solid paste
   that size floats and tilts the part and voids the joint — destroying the
   thermal path on a board where §4 shows the thermal path is the constraint.
2. **No courtyard at all.** The donor footprint's only layers were F.Cu, F.Fab,
   F.Mask, F.Paste, F.Silkscreen. Courtyard-overlap DRC therefore had nothing
   to test on these parts — part of why overlapping placement went unnoticed.

Thermal vias are **not** in the footprint: they are a layout property, ≥9 per
drain pad, verified on the board.

## 4. Thermal analysis

The "6 cm² × 24 = 144 cm², therefore impossible" argument is **wrong and has
been discarded**. Thermal resistance does not scale linearly with area. The
model decomposes it:

**R_θ(j-a) = R_θ(j-c) + R_spread + R_conv**

| Term | Value | Note |
|---|--:|---|
| R_θ(j-c) | 0.80 K/W | DATASHEET max |
| R_spread | **1.81 K/W** | radial in a thin plate, pad r=2.40 mm → r=8.14 mm, 280 µm effective copper (all six layers, via-stitched) |
| R_conv (board) | 13.33 / **2.50** K/W | still air h=15 / propwash h=80 W/m²·K |

**Copper spreading is cheap; the board-to-air term dominates and decides
everything.**

| | Per FET | Board total | | Board T | **T_j** | vs 125 °C |
|---|--:|--:|---|--:|--:|---|
| Hover, still air | 1.28 W | 17.96 W | | 279.5 °C | **282.8 °C** | ❌ |
| Hover, propwash | 1.28 W | 17.96 W | | 84.9 °C | **88.3 °C** | ✅ |
| Peak, still air | 2.23 W | 26.37 W | | 391.6 °C | **397.5 °C** | ❌ |
| Peak, propwash | 2.23 W | 26.37 W | | 105.9 °C | **111.8 °C** | ✅ |

Achieved vs required R_θ(j-a):

| | Required (T_j<125 °C) | Achieved, propwash |
|---|--:|--:|
| Hover | 66.2 K/W | **37.6 K/W** ✅ |
| **Peak** | **38.0 K/W** | **32.1 K/W** ✅ |

**The 38.6 K/W requirement is confirmed** (38.0 K/W on the verified device
numbers). It is not a device property — it is what the board must achieve.

### Correction to the previous report

Rev 1 stated the still-air peak case reached ~110 °C. **That was wrong.** It
used h = 75 W/m²·K described as "natural convection", roughly 5× too high for
still air. The correct still-air result is that the board does not thermally
close **at all** — not at peak, and not even at hover.

**Conclusion: the thermal architecture is feasible, and only with propwash.**
Still-air operation at any sustained power is outside the envelope. Bench
testing requires forced airflow — this is a safety instruction, not a
convenience.

**h is the dominant uncertainty** and is a textbook range, not a measurement.
Carry the ordering, not the absolute degrees. R_θ(j-a) must be measured on the
first board.

## 5. Switching transient analysis

Verified independently from Rev 2.6, not carried over.

```
I_phase peak       = 115 A / 4        = 28.75 A
t_f                                    = 11 ns      [DATASHEET T5]
di/dt = 28.75 / 11e-9                  = 2.61 A/ns  [CALCULATED]
headroom to 80% of VDS = 0.8x60 - 25.2 = 22.8 V
L_max = 22.8 / 2.61e9                  = 8.72 nH    [CALCULATED]
```

**8.72 nH confirmed.** The earlier 7.53 nH used the 40 V part's t_f of 9.5 ns
and is superseded — not silently replaced.

| Loop L | Overshoot | V_DS peak | Margin to 60 V |
|--:|--:|--:|--:|
| 2 nH | 5.2 V | 30.4 V | 29.6 V |
| 5 nH | 13.1 V | 38.3 V | 21.7 V |
| **8.72 nH** | **22.8 V** | **48.0 V** | **12.0 V (80 % derating point)** |
| 13.3 nH | 34.8 V | 60.0 V | **0 — at the limit** |
| 20 nH | 52.3 V | 77.5 V | **destroyed** |

The loop to minimise is the **commutation loop**, not "short traces": high-side
drain → low-side source → local ceramic → back. It includes package
inductance, via inductance and the plane return path.

**Recommended topology:** high-side and low-side FETs adjacent on B.Cu with the
switch node between them; ceramics on the **same side**, directly across the
bridge, within 2 mm; In1 solid ground immediately beneath as the return, so the
loop encloses the smallest possible area vertically rather than laterally. No
plane split anywhere under a bridge.

## 6. Main battery bus architecture

```
BAT+ pad (U3 VBAT, 4.5 x 15 mm)
  → 0.1 mΩ shunt (2 × 0.2 mΩ parallel)
  → INA186A3 sense
  → multilayer main bus  ─┬─ ch1 bridge
                          ├─ ch2 bridge
                          ├─ ch3 bridge
                          └─ ch4 bridge
  → avionics tap taken from the BUS, never through a channel
BAT− return: mirror geometry on In1/In4, same width
```

| Construction, 20 mm wide | Area | 115 A adiabatic |
|---|--:|--:|
| 2 oz outer only | 1.39 mm² | 34.0 °C/s → 30 °C in 0.9 s |
| **All six layers** | **5.57 mm²** | **2.13 °C/s → 30 °C in 14.1 s** |

Six-layer bus: **3.09 µΩ/mm**; over 25 mm → 3.2 mV / 0.14 W at 42 A, 8.9 mV /
1.02 W at 115 A.

**Current sharing must not be assumed.** Outer layers are 2 oz and inner 1 oz,
so an ideally-stitched bus splits roughly 25 % per outer layer and 12.5 % per
inner. Sharing is set by the via array, not by the copper: sparse or clustered
vias will crowd current into the outer layers. Requirement: ≥40 vias per
transition, **distributed along the bus**, and current sharing checked against
the final via geometry rather than assumed.

## 7. Phase-current architecture

Two different problems that must not be conflated:

| | DC/RMS current path | HF switching loop |
|---|---|---|
| Governs | copper heating | V_DS overshoot |
| Metric | cross-section, IPC-2221 | enclosed loop area / inductance |
| Requirement | ≥6.6 mm per layer, multilayer pour | ≤8.72 nH, §5 |
| Optimise by | more copper, more layers | tighter geometry, closer ceramics |

Widening copper does **not** fix inductance, and a tight loop does **not** fix
heating. The 6.6 mm netclass figure is a **calculated preliminary floor** for
the DC path — it stops a hand-route necking down. It is not the final geometry,
and it is not a switching-loop specification.

Phase RMS 21 A hover / 28.75 A peak → 6.6 mm and 10.2 mm on 2 oz outer at 20 °C
rise. Final geometry to be set during placement, per channel.

## 8. Capacitor architecture

| Class | Requirement | Placement |
|---|---|---|
| **Switching-loop ceramic** | ≥2 × 4.7 µF 1206 X5R 50 V per half-bridge | **Directly across the bridge, ≤2 mm, same side.** Part of the 8.72 nH budget. |
| Bulk DC-link | 470 µF 50 V electrolytic | Battery entry only. ESL far above the loop budget — **not** part of the switching loop. |
| Regulator input | Per LMR54406 / TLV76733 / LMR51430 datasheets | At each regulator |
| RF supply | Dedicated LDO + filter for the SX1281 | §14 of Rev 1 |

Retain the OpenESC 52 × 4.7 µF bank. **X5R capacitance at 25 V bias is
UNKNOWN** — do not trim the bank on nominal values.

Explicitly: a capacitor "near the battery connector" does nothing for the
commutation loop.

## 9. Connector architecture

| Interface | Rating | Role |
|---|---|---|
| **J1, JST SM08B-SRSS-TB** | **0.7 A/contact**, 50 V, 20 mΩ (40 mΩ aged) | **Signal / monitoring / breakout only** |
| U3 VBAT, BATGND pads | 4.5 × 15 mm, 67.5 mm² each | **Primary battery path**, soldered lead |
| U3 phase pads 1A…4C | 2.2 × 1.2 mm × 2 per phase = 5.28 mm² | Motor phases, soldered wire |

J1 pin 1 currently carries `+BATT` — **60× under** continuous, **164× under**
peak. **Remove `+BATT` from J1** or mark it explicitly as a sense-only tap with
a series limit. No other connector on this board is in a high-current path.

## 10. DRC / save regression protection

**Reproduced deterministically**, not merely guarded. `tools/test_save_cycle.py`
shows the two paths behave differently:

```
-- destructive: fresh BOARD() -> SaveBoard, on a copy --
   netclasses after: 1 (was 8)        -> DESTROYED
   design rules changed: 10           -> DESTROYED
      min_clearance: 0.09 -> 0.0
      min_connection: 0.09 -> 0.0
      min_copper_edge_clearance: 0.2 -> 0.5
      min_hole_clearance: 0.2 -> 0.25

-- non-destructive: LoadBoard -> SaveBoard, 5 cycles --
   cycle 1..5: nothing lost; verifier PASS
```

**The trigger is saving a freshly constructed `BOARD()`** — which is exactly
what `build_pcb.py` does. Re-saving a loaded board is safe. Testing only the
safe path would have produced a clean run and proved nothing.

Pipeline now: snapshot `net_settings` **and** `design_settings.rules` → save →
reload → restore anything that moved → run `verify_netclasses.py` → report.
Last rebuild: `RESTORED after SaveBoard: 8 netclasses, 10 design rules`.

**Rule: a green DRC is invalid unless `verify_netclasses.py` exits 0 for the
same board state.** The verifier checks all eight classes, Phase/VBAT widths,
via dimensions, board minimums and the six custom DRC rules.

## 11. Exact unresolved requirements

| # | Item | Consequence |
|---|---|---|
| **1** | **115 A peak duration AND repetition rate** | **Blocks routing.** See below. |
| 2 | R_θ(j-a) on the real board | Must be measured; model says 32 K/W with propwash, needs ≤38 |
| 3 | Z_thJA(t) for this board | Not in Rev 2.6; needed for pulses beyond ~1 s |
| 4 | PWM frequency | 24 kHz assumed from AM32 default, unverified |
| 5 | X5R capacitance at 25 V bias | Bank cannot be sized on nominal values |
| 6 | BSC014N06NS stock/price at 24 per board | Procurement |
| 7 | Fab capability: 2 oz outer at 0.16 mm | Manufacturing release |
| 8 | Convection coefficient h | Dominant uncertainty in §4 |

### 115 A peak-duration requirement unresolved

Parameterised as far as it can be: **T_j(t) = T_j,hover + ΔP × Z_th(t)**, with
ΔP = 0.95 W per FET and T_j,hover = 88.3 °C (propwash).

| Pulse | Z_thJC | ΔT_j | T_j |
|--:|--:|--:|--:|
| 0.1 ms | 0.010 | 0.01 K | 88.3 °C |
| 1 ms | 0.030 | 0.03 K | 88.3 °C |
| 10 ms | 0.100 | 0.09 K | 88.3 °C |
| 100 ms | 0.300 | 0.28 K | 88.5 °C |
| 1 s | 0.500 | 0.47 K | 88.7 °C |

**Inside the die and package the peak is nearly free.** But Z_thJC stops at the
case: beyond roughly 1 s the PCB and the air dominate, and **Z_thJA(t) for this
board is UNKNOWN**. The datasheet gives only the steady-state reference.

Cannot be closed without duration **and** repetition rate:

- MOSFET transient thermal response beyond ~1 s
- PCB copper temperature (adiabatic bounds short pulses only)
- Connector and pad heating
- Capacitor ripple-current stress and self-heating
- Power-plane temperature
- Repeated-peak accumulation — needs duty cycle, not duration alone

This is a firmware / propulsion / protection-timeout parameter. It has not been
invented here.

## 12. GO / NO-GO

**NO-GO for routing.**

Four gate conditions pass. The fifth — the 115 A peak duration and repetition
rate — is unresolved, and three of the six dependent calculations cannot even
be started without it.

Two further items are **blocking for manufacture** rather than routing: the
corrected footprint must be adopted by every FET instance (§3), and R_θ(j-a)
must be measured on the first board (§4).

The MOSFET is **not committed to the schematic**. No routing has been started.
