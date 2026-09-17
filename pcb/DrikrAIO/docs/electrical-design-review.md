# DrikrAIO — Electrical Design Review

> ## ⚠ SUPERSEDED
> This document is retained for its reasoning and its correction record.
> **Current status is [pre-routing-review-2.md](pre-routing-review-2.md); the
> machine-readable baseline is [pre-routing-baseline.json](pre-routing-baseline.json).**
> Numbers here that have since been corrected: the loop-inductance budget is
> **8.72 nH**, not 7.53 nH (the old figure used the 40 V part's t_f), and the
> still-air thermal figures were computed with an over-optimistic convection
> coefficient.

**Gate: routing must not begin until §18 is signed off.**

## Decisions taken (2026-09-04)

| Item | Decision |
|---|---|
| Battery | 6S3P Li-ion, 18–25.2 V |
| Continuous board current | 42 A |
| Peak | 115 A — **duration still undefined** |
| MOSFET | **60 V minimum** |
| Outer copper | 2 oz (current) |
| High-current bus | **All six layers in parallel** |
| Phase copper | Wide multilayer pour, **not** 1 mm traces |
| J1 | **Not a battery-current entry** |
| Main battery entry | U3 high-current pads / high-current connector |
| TVS | **Do not force one** onto a 25.2 V / 40 V architecture |
| Cooling | Propwash-dependent; bench peak testing needs external airflow |
| Routing | **Blocked** until power geometry and FET selection resolve |

**Applied:** `Phase` and `VBAT` netclasses corrected from 1.0 mm to 6.6 mm with
0.8/0.4 vias; the 60 V FET selection is §7a.

Every number here is produced by
[`hardware/tools/power_review.py`](../hardware/tools/power_review.py) and
regenerates from it. Device parameters are quoted from the datasheets committed
in `hardware/KiCad-Library/datasheet/` and cited inline. Anything not sourced is
marked **UNKNOWN** and has not been given a value.

## Operating point

| | |
|---|---|
| Battery | 6S3P Li-ion, 21.6 V nom, **18–25.2 V** |
| Design-against voltage | **25.2 V** for every power component |
| Whole board | **42 A continuous**, **115 A peak** (peak is *not* continuous) |
| Per channel, battery side | 10.5 A cont, 28.8 A peak |
| Per channel, phase RMS | **21 A** hover (50 % duty), **29 A** peak (full duty) |

> The phase figures assume phase RMS ≈ 2× battery current at 50 % duty and ≈ 1×
> at full duty. That is a modelling assumption, not a measurement, and it sets
> every conduction-loss number below.

---

## 1. Battery power path

Path: battery pads (U3 VBAT/BATGND, 4.5 × 15 mm each) → 0.1 mΩ shunt → main DC
bus → four channel bridges, with avionics tapped off the bus **before** any
channel.

| Element | 42 A | 115 A |
|---|--:|--:|
| Shunt (0.1 mΩ) | 0.18 W, 4.2 mV | 1.32 W, 11.5 mV |
| 6-layer bus, 20 mm wide, 25 mm long (3.09 µΩ/mm) | 0.14 W, 3.2 mV | 1.02 W, 8.9 mV |

Bus resistance and drop are negligible **provided the bus is built as specified
in §10**. On outer copper alone it is not.

## 2. 42 A continuous — copper and thermal

IPC-2221, 2 oz outer, 20 °C rise:

| Width | Current @20 °C | @40 °C |
|--:|--:|--:|
| 1.0 mm | 5.3 A | 7.2 A |
| 2.0 mm | 8.8 A | 12.0 A |
| 5.0 mm | 17.2 A | 23.3 A |
| 10.0 mm | 28.4 A | 38.5 A |
| 20.0 mm | 46.9 A | 63.6 A |

**42 A continuous needs 17.2 mm of 2 oz outer copper** at 20 °C rise. That is
achievable as a pour on a 50 mm board, but only as a pour — not a trace.

## 3. 115 A peak — and the parameter nobody has defined

**115 A needs 69.0 mm of 2 oz outer copper. The board is 50 mm.** It cannot be
carried as a steady state on this stackup at any geometry that fits.

So it must be a bounded transient. Adiabatic rise (no heat spreading, worst
case), 20 mm wide bus:

| Construction | Copper area | Rise rate | 30 °C in |
|---|--:|--:|--:|
| 2 oz outer only | 1.39 mm² | 34.0 °C/s | **0.9 s** |
| 2 outer + 4 inner | 5.57 mm² | 2.13 °C/s | **14.1 s** |

> ### UNRESOLVED — blocks thermal sign-off
> **The 115 A peak duration is undefined.** Nothing in the firmware, the sizing
> model, or the ArduPilot parameter set bounds how long T/W = 2 may be held.
> Searched: `docs/sizing/`, `firmware/ardupilot-params/params.py`, `autonomy/`.
>
> Without it, cases 2 and 3 below cannot be separated:
> 1. 42 A continuous — **calculated, passes**
> 2. 115 A short-duration peak — **passes if < ~14 s on a 6-layer bus**
> 3. **Repeated** 115 A peaks — **cannot be assessed**; duty cycle unknown
>
> This is a firmware/flight-dynamics parameter, not a PCB one. It must be
> defined before layout is signed off, not assumed here.

## 4. Four channels — 11 A / 29 A

Per channel, phase copper required (2 oz outer, 20 °C rise):

| | Current | Width needed |
|---|--:|--:|
| Phase, hover | 21 A | **6.6 mm** |
| Phase, peak | 29 A | **10.2 mm** |

The `Phase` netclass **was** 1.0 mm, which carries 5.3 A — short by roughly 4×
at hover and 6× at peak. It was inherited from OpenAIO, a toothpick-class
board, and it would have passed DRC on a board that cannot carry its own
current. **Corrected to 6.6 mm with 0.8/0.4 vias**, alongside `VBAT`.

6.6 mm is the *per-layer* minimum. The rated current is reached by pouring the
same net on all six layers, §10 — the netclass number is a floor that stops a
hand-route quietly necking down, not the whole conductor.

## 5. MOSFET loss — SP40N01GHNK

Datasheet Ver-1.1: V_DSS 40 V, R_DS(on) 1.2 mΩ typ / **1.5 mΩ max** @ V_GS=10 V,
×1.6 at T_J=125 °C → **2.4 mΩ hot**. R_θJC 0.96 °C/W. I_D 80 A @ T_c=100 °C,
I_DM 480 A. Q_g 126 nC, t_r 5 ns, t_f 9.5 ns, C_oss 1950 pF, Q_rr 113 nC.

| Per FET | Hover (21 A) | Peak (29 A) |
|---|--:|--:|
| Conduction | 1.06 W | 1.98 W |
| Switching @ 24 kHz | 0.092 W | 0.126 W |
| C_oss + Q_rr | 0.083 W | 0.083 W |
| **Total** | **1.23 W** | **2.19 W** |
| Per channel (6 FETs) | 3.17 W | 5.22 W |
| **All four channels** | **12.7 W** | **20.9 W** |

Switching loss is small — these are low-voltage parts and conduction dominates.

**PWM frequency 24 kHz is an assumption** (AM32 default) and has not been
verified against our configuration. Switching loss scales linearly with it.

### The number that decides survival

| | Required R_θ(j-a) for T_J < 125 °C at 40 °C ambient |
|---|--:|
| Hover | < 68.9 °C/W |
| Peak | **< 38.8 °C/W** |

R_θJC is 0.96 °C/W, so essentially all of the budget is **case-to-ambient — a
layout property**. It is **UNKNOWN** until the copper under each thermal pad is
drawn. This, not R_DS(on), is what decides whether the parts survive.

**Requirement:** each FET's drain pad shall have ≥ 100 mm² of connected pour
with ≥ 9 thermal vias into the inner planes, and R_θ(j-a) shall be verified by
thermal measurement on the first board.

## 6. MOSFET transient voltage

Do **not** treat 40 V as safe merely because 25.2 V < 40 V.

di/dt at turn-off: 29 A / 9.5 ns = **3.03 A/ns**.

| Derating | Allowed spike | Max loop inductance |
|---|--:|--:|
| To absolute V_DSS | 14.8 V | 4.89 nH |
| **To 80 % of V_DSS** | 6.8 V | **2.25 nH** |

**1 nH is roughly 1 mm of trace.** A 10 nH loop — a few millimetres of casual
routing — puts 30 V on top of the rail, i.e. 55 V across a 40 V part.

Contributors: battery lead inductance (~1 nH/mm, and the leads are external and
outside our control), connector inductance, PCB commutation-loop inductance,
body-diode reverse recovery (Q_rr 113 nC), and regenerative braking during
rapid deceleration.

## 7. TVS — and why one cannot be specified

A TVS here would need V_RWM > 25.2 V (or it conducts in normal flight) and
V_clamp < 32 V (80 % of V_DSS). Real TVS clamping ratios are ~1.5–1.6× V_RWM,
so the lowest standoff that survives the rail — 26 V — clamps near **42 V**,
above the FET rating.

**No standard TVS fits this window.** This is precisely why OpenESC-30x30 rev3
*removed* its input clamp diodes rather than resizing them, recording that "TVS
diodes offer no protection when rail voltage is this close to the MOSFET Vds".
That decision is correct and must not be reversed.

Protection must therefore come from **loop geometry**, §8.

| FET rating | Allowed spike | Max loop L | |
|---|--:|--:|---|
| 40 V (current) | 6.8 V | 2.25 nH | very hard to guarantee |
| **60 V** | 22.8 V | **8.72 nH** | achievable, and re-opens the TVS option |

**Decision taken: 60 V minimum.** See §7a.

## 7a. 60 V MOSFET selection

The assumption that 60 V costs conduction loss turns out to be **false** if the
right part is chosen.

| Part | V_DSS | R_DS(on) max | R hot (×1.6) | P_cond/FET @29 A | 4 ch total | Loop budget | R_θ(j-a) budget |
|---|--:|--:|--:|--:|--:|--:|--:|
| SP40N01GHNK *(fitted, 40 V)* | 40 V | 1.50 mΩ | 2.40 mΩ | 1.98 W | 20.9 W | 2.25 nH | 38.7 °C/W |
| NCEP60T15G | 60 V | 3.10 mΩ | 4.96 mΩ | 4.10 W | 37.8 W | 8.72 nH | 19.7 °C/W |
| BSC028N06NS | 60 V | 2.80 mΩ | 4.48 mΩ | 3.70 W | 34.6 W | 8.72 nH | 21.7 °C/W |
| **BSC014N06NS** | **60 V** | **1.45 mΩ** | **2.32 mΩ** | **1.92 W** | **20.4 W** | **8.72 nH** | **40.0 °C/W** |

**Recommended: Infineon BSC014N06NS**, OptiMOS 5, SuperSO8 5×6, I_D 240 A.

It is 60 V at *lower* R_DS(on) than the fitted 40 V part, so it delivers the
3.3× loop-inductance headroom **and** slightly lower loss **and** a slightly
better thermal budget. The cost is unit price, not watts.

The other two 60 V candidates roughly double conduction loss and cut the
R_θ(j-a) budget to ~20 °C/W, which is not realistically achievable on this PCB.

### Before this part is committed

- **Land pattern must be checked** against `PDFN-8L_L6.0-W5.0-P1.27` by
  arithmetic on the datasheet drawing. The OpenDrone catalogue already lists an
  Infineon SuperSO8 (BSC010N04LS6) as landing on this footprint, which is good
  evidence but is not the check.
- **t_r, t_f, C_oss, Q_rr, R_θJC, E_AS are UNKNOWN** — taken from the Infineon
  product page, not the datasheet. The switching terms above reuse the
  SP40N01GHNK timings. Conduction dominates so the ranking holds, but the
  absolute 60 V numbers are provisional.
- **Stock and price at the required quantity** (24/board) not checked.

### Supply-chain warning carried from the catalogue

`SP40N01GHNK` ships under **one MPN with two datasheet revisions** that disagree
on the parameters this review depends on: R_θJC **1.27 vs 0.96 °C/W** and E_AS
**490 vs 1089 mJ**. This review used Ver-1.1. If Ver-1.0 silicon arrives on a
reorder, the thermal budget is ~32 % worse than calculated. That ambiguity is
itself an argument for moving to a part with a single published spec.

## 8. Bulk and ceramic capacitance

Retain OpenESC-30x30's bank: **52 × 4.7 µF 1206 X5R 50 V** ceramic (≈ 244 µF
nominal, far less at 25 V bias) plus the **470 µF 50 V electrolytic** installed
at the battery lead by the user.

Placement is the requirement, not the value:

- At least **2 × 4.7 µF 1206 within 2 mm** of each half-bridge, on the same
  side, with the loop closed on the adjacent inner ground plane.
- The commutation loop — high-side drain → low-side source → decoupling cap →
  back — shall be **as small as physically drawable**, and its enclosed area
  minimised by placing the return directly beneath the loop on In1.
- Bulk electrolytic at the battery entry, not distributed.
- **Do not** rely on the electrolytic for the switching loop: its ESL is
  orders of magnitude above the 2.25 nH budget.

X5R at 25 V bias loses a large fraction of its rated capacitance. The
derated value is **UNKNOWN** without the specific part's bias curve and should
be checked before the bank is trimmed.

## 9. Via arrays

0.3 mm drill, 25 µm plating: A = 0.0255 mm², **1.08 mΩ per via**.

| Path | Current | A/via | Minimum vias |
|---|--:|--:|--:|
| Bus, continuous | 42 A | 1.5 | **28** |
| Bus, peak | 115 A | 3.0 | **38** |
| Phase, hover | 21 A | 1.5 | **14** |
| Phase, peak | 29 A | 3.0 | **10** |

**Requirement:** ≥ 40 vias at every bus layer transition, ≥ 16 per motor phase,
≥ 9 under each FET thermal pad. Vias shall be distributed across the pour, not
lined up in a row — a single row re-creates the current crowding the array
exists to remove.

## 10. Copper pours

**2 oz outer copper alone is not sufficient. This is calculated, not assumed.**

| Net | Construction required |
|---|---|
| +BATT / GND bus | **All six layers in parallel**, ≥ 20 mm effective width, stitched per §9 |
| Motor phases | ≥ 6.6 mm pour minimum, ≥ 10.2 mm preferred; inner-layer parallel where it fits |
| FET drains | ≥ 100 mm² pour each, thermal vias to inner planes |

If the six-layer bus cannot be routed inside 50 × 50 mm, the escalation order
is: (1) increase inner copper from 1 oz to 2 oz; (2) increase outer to 3 oz;
(3) relax the 50 mm constraint. **Do not** solve it by narrowing the bus.

## 11. Connectors

**J1 (JST SM08B-SRSS-TB) is rated 0.7 A per contact, 50 V, 20 mΩ initial /
40 mΩ after environmental testing** (SR series datasheet, committed).

**J1 pin 1 carries +BATT.** At 0.7 A it is **60× under** the continuous bus
current and **164× under** peak.

**Requirement:** J1 is a **signal and breakout connector only**. It must never
be a battery path. The battery enters exclusively on U3's VBAT/BATGND pads
(4.5 × 15 mm, 67.5 mm² each), which are correctly sized for soldered leads. Add
a silkscreen and documentation note; consider removing +BATT from J1 entirely.

Motor phase pads (U3, 2.2 × 1.2 mm, two per phase = 5.28 mm²) are for soldered
wire, not connectors, and are adequate for 29 A on that basis.

## 12. Stackup

| Layer | Copper | Function |
|---|---|---|
| F.Cu | 2 oz | Control side; FET drains and phase pours where they surface |
| In1.Cu | 1 oz | **Solid ground** — the return for every switching loop |
| In2.Cu | 1 oz | +BATT bus |
| In3.Cu | 1 oz | +BATT bus / phase parallel |
| In4.Cu | 1 oz | **Solid ground** |
| B.Cu | 2 oz | Power side; FETs, battery and motor pads |

1.6 mm nominal, ENIG. **In1 immediately under F.Cu is the load-bearing choice**
— it is what makes a 2.25 nH loop possible at all.

If §10 forces 2 oz inner layers, the stackup and the fab quote both change and
the impedance of the RF section must be re-checked.

## 13. Ground architecture

Single solid ground on In1 and In4. **No split planes.** A split under a
switching loop forces the return current around the gap and adds exactly the
inductance §6 is trying to eliminate.

Separation is by **placement**, not by cuts:

- Power-stage return currents are confined to B.Cu/In4 under the bridges.
- Analog and IMU grounds sit over the In1 region on the control side, physically
  distant from the bridges.
- The shunt is Kelvin-sensed; the INA186 input pair routes as a tight
  differential pair over unbroken ground, and the RC filter (R89/R90 1 k,
  C40/C41 100 n, C42 1 µ — added in OpenESC rev3.2 against high-side
  common-mode feedthrough) stays adjacent to the amplifier.

## 14. RF isolation

The SX1281 2.4 GHz chain shares a board with four switching bridges.

- Receiver in a board corner, its antenna edge facing outward, **on the opposite
  side and diagonally opposite the power stages**.
- Ground via fence around the RF section, stitched to In1 at ≤ λ/20 spacing.
- **No switching node, phase pour or bus copper may pass beneath the RF section
  on any layer.**
- The receiver's TLV75533 LDO is fed from the +3V3 ESC rail today. **Give the RF
  section its own LDO** off a filtered tap, not the rail that also feeds four
  ESC MCUs.
- Controlled impedance: 50 Ω single-ended on the antenna trace. **None of the
  donor boards declared an impedance constraint** — this one must, in the
  stackup and in the fab notes, or the fabricator will not build to it.

## 15. VTX thermal

**There is no VTX on this board.** OpenVTX was never designed (no schematic, no
PCB). What exists is the FC's `10V_ENABLE`-gated rail intended to feed an
external VTX.

That rail is an LMR51430, 3 A. At 10 V it can source 30 W, which covers a
typical analog VTX. The thermal load of the VTX itself is **off-board and out of
scope**; the on-board consideration is the buck's own dissipation, which is
inside the §8 board total.

**If a VTX is later integrated onto this board, this review does not cover it.**
A 1–2 W RF PA is a new thermal zone and a new interferer next to the receiver.

## 16. DRC rules — changes required before routing

| Rule | Was | Now | Why |
|---|---|---|---|
| `Phase` netclass track | 1.0 mm | **6.6 mm** ✅ applied | 1.0 mm carries 5.3 A; phase RMS is 21 A |
| `VBAT` netclass track | 1.0 mm | **6.6 mm/layer, 6 layers** ✅ applied | 42 A continuous |
| Bus via count | none | **≥ 40 per transition** | §9 |
| FET thermal pad | none | **≥ 100 mm² pour, ≥ 9 vias** | §5 |
| RF clearance | 0.30 mm | keep, add **50 Ω impedance class** | §14 |
| Outer track/clearance | 0.16 mm | keep | 2 oz etch taper |

The existing 1.0 mm `Phase`/`VBAT` classes are **actively misleading** — they
will pass DRC on a board that cannot carry its own current.

## 17. Manufacturing constraints

- 6 layers, 1.6 mm, **2 oz outer / 1 oz inner, ENIG** — declared in the stackup,
  not only in the rules. (This is the OpenAIO defect: rules said 2 oz, stackup
  said 1 oz.)
- 0.16 mm minimum track/clearance on outer layers (2 oz etch taper); 0.09 mm
  inner.
- 0.35 mm via on 0.20 mm drill, 0.075 mm annular.
- 2 oz outer with 0.16 mm features is at the tighter end of low-cost fab
  capability. **Confirm with the fabricator before layout**, not after.
- If §10 forces 2 oz inner or 3 oz outer, re-quote: both are specialist and
  change lead time and cost materially.
- `C_0402_WIDE` is a recovered footprint and **must not be substituted**.

---

## 18. Sign-off gate

| # | Item | Status |
|---|---|---|
| 1 | Battery power-path calculation | ✅ §1 |
| 2 | 42 A continuous thermal | ✅ §2 |
| 3 | 115 A peak | ⚠️ §3 — **duration undefined** |
| 4 | Four-channel 11 A / 29 A | ✅ §4 |
| 5 | MOSFET loss | ✅ §5 |
| 6 | MOSFET transient voltage | ⚠️ §6 — 2.25 nH budget is severe |
| 7 | TVS selection | ✅ §7 — none viable; **60 V decided**, §7a |
| 8 | Bulk capacitor sizing/placement | ✅ §8 (X5R bias derating UNKNOWN) |
| 9 | Via arrays | ✅ §9 |
| 10 | Copper pours | ✅ §10 |
| 11 | Connector current | ✅ §11 — J1 is breakout only |
| 12 | Stackup | ✅ §12 |
| 13 | Ground architecture | ✅ §13 |
| 14 | RF isolation | ✅ §14 |
| 15 | VTX thermal | ✅ §15 — out of scope, no VTX exists |
| 16 | DRC rules | ✅ §16 — netclasses corrected |
| 17 | Manufacturing constraints | ⚠️ §17 — fab capability unconfirmed |

**Remaining blockers before routing:**

1. **Define the 115 A peak duration and repetition.** Firmware/flight-dynamics
   parameter. Still blocks thermal sign-off. *(open)*
2. ~~Correct the `Phase` and `VBAT` netclasses.~~ **Done** — 6.6 mm, 0.8/0.4 vias.
3. ~~Decide 40 V vs 60 V.~~ **Done — 60 V minimum.** Now: verify the
   BSC014N06NS land pattern against `PDFN-8L_L6.0-W5.0-P1.27`, read its
   datasheet for the switching and thermal parameters, and check stock at 24
   per board. *(open, but bounded)*

**Two to confirm in parallel:** fabricator capability for 2 oz / 0.16 mm, and
X5R capacitance at 25 V bias.

## Assumptions, stated

| Assumption | Effect if wrong |
|---|---|
| Phase RMS = 2× battery current at 50 % duty | All conduction losses scale as I² |
| PWM 24 kHz (AM32 default, unverified) | Switching loss scales linearly |
| 40 °C ambient | Shifts every junction-temperature margin |
| Convection coefficients 0.0075 / 0.030 W/cm²·K | Textbook ranges, not measured |
| 3 W avionics dissipation | Estimate, not sourced |

**Nothing here is a substitute for measuring the first board.**
