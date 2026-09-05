# DrikrAIO — Power Architecture

**POWER ARCHITECTURE: OPEN ITEMS** — 12 open, 2 of them structural.

Regenerates from [`hardware/tools/power_arch.py`](../hardware/tools/power_arch.py).
Device ratings quoted from committed datasheets; anything not read is marked
**OPEN**, never assumed to pass.

No routing. No placement change. No schematic change. No outputs.

---

## 1. Battery input path

```
Battery leads (external)
  └─> U3 solder pads  VBAT / BATGND, 4.5 x 15 mm, 67.5 mm2 each   [L6]
        └─> Rsense801 || Rsense802   2 x 0.2 mOhm = 0.1 mOhm      [L6]
              └─> INA186A3 high-side sense  -> CURR -> FC ADC
                    └─> MAIN VBAT BUS  L1 / L3 / L4 / L6
                          ├─> bulk: 470 uF 50 V electrolytic (USER-INSTALLED, off-board)
                          ├─> ch1..ch4 bridge branches -> local ceramics -> FETs -> phases
                          ├─> LMR54406 -> +10V ESC  -> TLV76733 -> +3V3 ESC
                          └─> LMR51430 x2 -> +10V FC (gated) and +5V FC
                                              -> DSK24 OR -> +4V5
                                                   ├─> LP5912-3.3 -> +3.3V FC
                                                   └─> LP5912-1.8 -> +1.8V IMU
```

**J1 is NOT in this path.** JST SM08B-SRSS-TB is **0.7 A per contact, 50 V**
(JST SR datasheet) — 60× under continuous and 164× under peak. It is a signal
and breakout connector. The battery enters only on U3's pads.

### Device verification at 25.2 V

| Part | Role | V abs max | V rec max | Margin @25.2 V | Status |
|---|---|--:|--:|--:|---|
| BSC014N06NS | bridge FET ×24 | 60 V | 60 V | 34.8 V | OK |
| LMR54406 | ESC +10 V gate rail | 45 V | 36 V | 19.8 V | OK |
| **LMR51430** | **FC +10 V / +5 V bucks** | **38 V** | 36 V | **12.8 V** | **OK, but lowest** |
| SM08B-SRSS-TB | J1 signal only | 50 V | — | 24.8 V | OK (0.7 A) |
| INA186A3 | battery current sense | ? | ? | ? | **OPEN** |
| TLV76733 | ESC 3V3 LDO | ? | ? | ? | **OPEN** |
| LP5912 | FC 3V3 / 1V8 LDOs | ? | ? | ? | **OPEN** |
| DSK24 | 5 V diode-OR ×2 | ? | ? | ? | **OPEN** |

Sources: Infineon Rev 2.6 T2; TI SLUSEF4A §7.1/7.3; TI SLUSEG8E §6.1/6.3
(45 V DC, 50 V for ≤1 s at ≤0.01 % duty); JST SR series.

> ### The FET is not the lowest-rated device on this bus
>
> | Device | V abs | Spike to abs | Spike to 80 % | L for 80 % |
> |---|--:|--:|--:|--:|
> | BSC014N06NS | 60 V | 34.8 V | 22.8 V | **8.72 nH** |
> | LMR54406 | 45 V | 19.8 V | 10.8 V | 4.13 nH |
> | **LMR51430** | **38 V** | **12.8 V** | 5.2 V | **1.99 nH** |
>
> Taken naively, the FC bucks would demand a **1.99 nH** bus — tighter than the
> 2.25 nH that got the 40 V FET architecture rejected.
>
> That comparison is **not** apples to apples: 8.72 nH governs V_DS inside the
> local commutation loop, while the regulators sit on the bulk-decoupled bus
> and see an attenuated transient. But *attenuated* is not a number, and the
> attenuation depends on final geometry and bulk ESL, neither of which exists
> yet. **OPEN: VBAT bus transient at the LMR51430 inputs.** It is not claimed
> to pass.

## 2. Main VBAT bus — multilayer, not a trace

| Layer | Role | Copper | Share (ideal) |
|---|---|--:|--:|
| L1 F.Cu | VBAT pour | 2 oz | 33.3 % |
| L3 In2 | VBAT plane | 1 oz | 16.7 % |
| L4 In3 | VBAT / phase | 1 oz | 16.7 % |
| L6 B.Cu | VBAT pour, power side | 2 oz | 33.3 % |

20 mm effective width, 25 mm length: **4.18 mm²**, **103 µΩ**.

| Path | I | R | V drop | P loss |
|---|--:|--:|--:|--:|
| VBAT bus continuous | 42 A | 103 µΩ | 4.3 mV | 0.18 W |
| VBAT bus peak | 115 A | 103 µΩ | 11.8 mV | 1.36 W |
| Shunt continuous | 42 A | 0.1 mΩ | 4.2 mV | 0.18 W |
| Shunt peak | 115 A | 0.1 mΩ | 11.5 mV | 1.32 W |

**Copper resistance is not the problem.** The shunt dissipates as much as the
entire bus. What matters is that the bus is built on four layers — on a single
2 oz outer layer the same bus is 1.40 mm² and heats at 34 °C/s at 115 A.

**Sharing is 33/17/17/33 %, not equal**, because outer layers are 2 oz and
inner 1 oz. That split is only achieved with sufficient, distributed stitching;
sparse or clustered vias crowd current into the outer layers. **Sharing must be
verified against the final via geometry, not assumed.**

**115 A is not a continuous rating.** Duration and repetition remain OPEN.

## 3. Motor power, per channel ×4

```
VBAT bus  ->  branch (L6 + L4, >=6.6 mm)  ->  local ceramics  ->  half-bridge  ->  phase pad
```

| Path | I | R | V drop | P loss |
|---|--:|--:|--:|--:|
| Channel branch continuous | 10.5 A | 0.30 mΩ | 3.2 mV | 0.03 W |
| Channel branch peak | 28.8 A | 0.30 mΩ | 8.6 mV | 0.25 W |
| Motor phase hover | 21 A | 0.37 mΩ | 7.9 mV | 0.17 W |
| Motor phase peak | 28.8 A | 0.37 mΩ | 10.8 mV | 0.31 W |

The **6.6 mm Phase/VBAT netclass is a minimum constraint, not proof of
adequacy** for 115 A. It exists to stop a hand-route necking down where copper
leaves a pad. Final geometry is the four-layer pour above.

## 4. Switching loop, per half-bridge

| Element | Location |
|---|---|
| High-side path | VBAT pour L6 → high-side drain |
| Switching node | between high and low FET, L6, minimal area |
| Low-side return | source → **L5 solid ground, 0.10 mm below** |
| DC-link ceramic | ≥2 × 4.7 µF 1206 50 V, **same side, ≤2 mm**, across the bridge |
| Gate-drive return | to driver GND, referenced to the same L5 region as the source |

**Budget: 8.72 nH** at 80 % of 60 V. **7.53 nH is superseded and not used.**

Route the loop **vertically** — L6 out, L5 back, 0.10 mm apart — not laterally.
Design below the budget with margin; do not route up against it.

## 5. Capacitors

| Class | Part | Rating | Verification |
|---|---|---|---|
| DC-link ceramic | 52 × 4.7 µF 1206 X5R | **50 V** vs 25.2 V | OK on voltage; **capacitance at 25.2 V bias OPEN** |
| Battery bulk | 470 µF 50 V electrolytic | 50 V | **User-installed, off-board.** Not on this PCB |
| ESC buck in/out | 22 µF, 4.7 µF, 100 nF | mixed | **OPEN — ratings not individually verified** |
| FC buck in/out | 22 µF, 4.7 µF 50 V | 50 V on C201/C202 | partly verified |

**Capacitance alone does not solve switching transients.** The ceramics work
only if they are inside the commutation loop; a capacitor at the battery
connector contributes nothing to a 2.61 A/ns edge 20 mm away. Placement is the
specification, value is secondary.

**Ripple current is unquantified** — it depends on duty cycle and PWM
frequency, both OPEN.

## 6. Avionics power hierarchy

```
VBAT 18-25.2 V
 ├─ LMR54406 (0.6 A)  -> +10V ESC (ungated)  -> TLV76733 -> +3V3 ESC
 │                                                          -> 4x AT32F421, INA186, RX
 └─ LMR51430 (3 A)    -> +10V FC (10V_ENABLE gated) -> external VTX
    LMR51430 (3 A)    -> +5V FC  -> DSK24 ─┐
                        +5V_USB  -> DSK24 ─┴─> +4V5 -> LP5912-3.3 -> +3.3V FC
                                                    -> LP5912-1.8 -> +1.8V IMU
```

**The two 10 V rails are deliberately separate.** The FC's is gated by
`10V_ENABLE`, a firmware PINIO for switching a VTX. A rail firmware can cut is
not a rail that may feed gate drivers, so the ESC keeps its own LMR54406.

**`+3.3V` (FC) and `+3V3` (ESC) are different nets** separated by one
character. Rename before routing.

**+1.8V feeds only the IMU analog supply** and is deliberately not merged with
3V3 — inherited from OpenFC-Lite-Mini and preserved.

## 7. RF and sensor power

| Load | Rail | Concern |
|---|---|---|
| SX1281 RF | +3V3 **ESC rail**, via TLV75533 | Shares a rail with four ESC MCUs. **Give RF its own LDO off a filtered tap.** |
| IMU (BMI270) | +1.8V analog, +3.3V IO | Already separated. Keep. |
| Magnetometer / GPS | — | **Not present on this board.** |

Switching inductors L201/L202 (FC bucks) are in the top-left zone, diagonally
opposite the RF block in the top-right — the maximum in-plane separation the
board allows.

## 8. Ground architecture

**Two solid planes, L2 and L5, neither split.** Separation is by placement and
by which plane a return rides.

| Return | Plane | Rationale |
|---|---|---|
| MOSFET commutation | L5 under L6 | shortest loop, 0.10 mm |
| Battery / bulk | L5 + L6 pour | high current stays on the power side |
| Avionics, MCU, OSD | L2 under L1 | continuous reference |
| RF | L2 only, unbroken | no L3/L4 copper beneath the feedline |
| Shunt Kelvin sense | L2, unbroken | no discontinuity under the pair |

**No isolated ground islands.** Motor return current is kept out of the
avionics region by keeping the battery entry, shunt and bridges on L6/L5 in the
bottom-side quadrants and centre strip — not by cutting copper.

## 9. Protection — mostly absent

| Protection | Present? | Note |
|---|---|---|
| Current sensing | **Yes** | 0.1 mΩ + INA186A3 → FC ADC |
| Reverse polarity | **NO** | Absent. Inherited from OpenFC-Lite-Mini, which documents having none. |
| Input fuse / limiting | **NO** | Nothing limits a 115 A-capable bus into a fault |
| Input transient / TVS | **NO** | Deliberate — no TVS fits a 25.2 V rail under a 60 V part |
| UV / OV | Partial | Regulator UVLO only; no board-level OV |
| Regulator protection | Yes | LMR51430 and LMR54406 have internal current limit, hiccup and thermal shutdown |

**Two structural gaps:** no reverse-polarity protection and no fusing on a bus
that can deliver 115 A. Both are inherited, both are recorded rather than
patched, and both are **decisions for you**, not defects to fix unilaterally.

## 10. Thermal

**THERMAL STATUS: MARGINAL.** Unchanged. Copper does not solve it —
R_θ(j-c) plus spreading are only 5.7 K of the rise. Primary variables remain
airflow exposure, peak duration and duty cycle. h = 80 W/m²·K not used.

## 11. Power budget

| Rail | V | I cont | I peak | Source | Load | Protection |
|---|---|---|---|---|---|---|
| VBAT | 18–25.2 | 42 A | 115 A | battery, U3 pads | 4 bridges + both bucks | shunt + INA186; **no fuse, no reverse** |
| +10V ESC | 10 | ~0.1 A | ~0.2 A | LMR54406 0.6 A | 4× NSG2065Q | buck limit |
| +3V3 ESC | 3.3 | ~0.1 A | ~0.15 A | TLV76733 | 4× AT32F421, INA186, RX | LDO limit **(rating OPEN)** |
| +10V FC | 10 | ≤3 A | ≤3 A | LMR51430 | external VTX | MCU-gated |
| +5V FC | 5 | ≤3 A | ≤3 A | LMR51430 | 5 V pads → OR | always-on |
| +4V5 | 4.5 | <0.5 A | <0.5 A | DSK24 OR | 3V3, 1V8 LDOs | none |
| +3.3V FC | 3.3 | <0.5 A | <0.5 A | LP5912-3.3 | MCU IO, IMU IO, SD, OSD | LDO limit |
| +1.8V | 1.8 | <0.05 A | <0.05 A | LP5912-1.8 | IMU analog | LDO limit |

## 12. PCB implementation constraints (no routing)

| # | Requirement |
|---|---|
| 1 | VBAT pour on **L1, L3, L4, L6**, ≥20 mm effective width |
| 2 | GND solid on **L2 and L5**, unbroken |
| 3 | **≥39 vias** per VBAT layer transition, distributed, never in a row |
| 4 | **≥16 vias** per motor phase transition |
| 5 | **≥9 thermal vias** per FET drain pad into L5 |
| 6 | ≥2 × 4.7 µF within **2 mm** of each half-bridge, same side |
| 7 | Commutation loop closes on L5, **≤8 mm** path, below 8.72 nH |
| 8 | Battery entry, shunt and INA186 in the **centre strip**, L6 |
| 9 | Kelvin sense pair over unbroken L2, RC filter adjacent to INA186 |
| 10 | No switching node or power pour beneath the RF block on any layer |
| 11 | Regulator zones: FC power top-left, ESC power centre strip |
| 12 | J1 carries **no battery current** |

## 13. Validation

| Check | Result |
|---|---|
| 25.2 V rating, all verified devices | **PASS** (4 devices OPEN) |
| 42 A continuous | **PASS** — 4.3 mV, 0.18 W on the four-layer bus |
| 115 A peak | **PASS as a transient only**; duration OPEN |
| Current bottlenecks | Shunt dissipates as much as the whole bus; acceptable |
| Connector ratings | **PASS** — J1 excluded from the power path |
| Via bottlenecks | **PASS with requirement** — ≥39 per transition |
| Capacitor ratings | **PARTIAL** — 50 V ceramics OK, bias derating OPEN |
| Regulator ratings | **PASS on the two read**; 4 devices OPEN |
| Thermal | **MARGINAL** |
| Layer transitions | **PASS with requirement** — sharing must be verified |

### Open items — not assumed to pass

1. INA186A3 rating not verified
2. TLV76733 rating not verified
3. LP5912 rating not verified
4. DSK24 rating not verified
5. **VBAT bus transient at LMR51430 inputs (38 V abs max)**
6. 115 A peak duration and repetition rate *(frozen OPEN)*
7. Airflow boundary condition *(frozen OPEN)*
8. **Reverse-polarity protection: none present**
9. **Input fuse / current limiting: none present**
10. UV/OV protection beyond regulator UVLO: none
11. Bulk 470 µF is user-installed and off-board
12. X5R capacitance at 25.2 V bias

---

**POWER ARCHITECTURE: OPEN ITEMS (12)**
**ROUTING STATUS: BLOCKED**
