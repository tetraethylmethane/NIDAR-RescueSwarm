# DrikrAIO — Via and Copper Design

**VIA/COPPER DESIGN: OPEN ITEMS**

Regenerates from [`hardware/tools/via_copper.py`](../hardware/tools/via_copper.py).
No routing. No footprint change. No frozen requirement altered.

> ## Two results that change earlier conclusions
>
> **1. The 0.8 mm / 0.4 mm via rule is the worst of the options considered.**
> Current capacity per unit *board area* — not per via — is what matters, and
> larger vias need proportionally larger pitch. 0.40/0.80 delivers the least
> copper per mm² of the four geometries evaluated.
>
> **2. R_spread was optimistic: 1.82 → 4.22 K/W.** The earlier thermal model
> treated all six layers as one 280 µm plate. Heat only reaches the inner
> layers *through the via field*, which is in **series** with them. With that
> corrected, **sustained peak at the disc reaches 176.8 °C and exceeds the
> 175 °C absolute maximum** — it previously sat 3.6 °C below it.

---

## 1. Main VBAT copper

**6.6 mm is the netclass minimum, not the answer.** A single 2 oz outer layer
would need **17.2 mm** for 42 A and **69.0 mm** for 115 A — the latter wider
than the board.

| Layer | Cu | Width | Area | R (25 mm) | Share |
|---|--:|--:|--:|--:|--:|
| L1 F.Cu | 2 oz | 18.0 mm | 1.25 mm² | 0.343 mΩ | 32.1 % |
| L3 In2 | 1 oz | 20.0 mm | 0.70 mm² | 0.618 mΩ | 17.9 % |
| L4 In3 | 1 oz | 20.0 mm | 0.70 mm² | 0.618 mΩ | 17.9 % |
| L6 B.Cu | 2 oz | 18.0 mm | 1.25 mm² | 0.343 mΩ | 32.1 % |
| **Total** | | | **3.90 mm²** | **110 µΩ** | |

| Condition | Drop | Loss | Adiabatic rate | 20 °C in |
|---|--:|--:|--:|--:|
| 42 A continuous | 4.63 mV | 0.19 W | 0.58 °C/s | 34.5 s |
| 115 A peak | 12.69 mV | 1.46 W | 4.34 °C/s | **4.6 s** |

**Sharing is 32/18/18/32 %, and it is set by the via array, not the copper.**
Sparse or clustered stitching crowds current into L1/L6. Peak duration is OPEN,
so the adiabatic column is a rate, not a verdict.

## 2. Motor phase copper

| Condition | I | 2 oz width needed | At 6.6 mm | Drop | Loss |
|---|--:|--:|--:|--:|--:|
| Hover | 21.0 A | **6.6 mm** | 0.374 mΩ | 7.9 mV | 0.17 W |
| Peak | 28.8 A | **10.2 mm** | 0.374 mΩ | 10.8 mV | 0.31 W |

**6.6 mm covers hover but not peak on a single outer layer.** Phases run
**L6 + L4 in parallel**, or widen to 10.2 mm where the quadrant allows. Both
conditions were checked separately, as required.

## 3. Via geometry trade

| Hole | Pad | Pitch | A_cu | R_via | Aspect | **Cu per mm² board** |
|--:|--:|--:|--:|--:|--:|--:|
| 0.20 mm | 0.45 mm | 0.65 mm | 0.0177 mm² | 1.557 mΩ | 8.0:1 | 0.0418 |
| **0.25 mm** | 0.50 mm | 0.70 mm | 0.0216 mm² | 1.274 mΩ | 6.4:1 | **0.0441** |
| **0.30 mm** ★ | 0.60 mm | 0.80 mm | 0.0255 mm² | 1.078 mΩ | **5.3:1** | 0.0399 |
| 0.40 mm | 0.80 mm | 1.00 mm | 0.0334 mm² | 0.824 mΩ | 4.0:1 | **0.0334** ← worst |

**Recommendation: 0.30 mm hole / 0.60 mm pad.** It carries 19 % more copper per
board area than the current 0.40/0.80 rule while staying at a routine 5.3:1
aspect ratio.

0.25 mm is denser still but every figure above assumes **25 µm plating reaches
the middle of the barrel**, which is not guaranteed at higher aspect ratios.
**OPEN — fab must confirm plating thickness at the chosen aspect ratio.**

The existing 0.8/0.4 netclass rule is a *minimum via size*, and nothing above
violates it being present; adopting 0.30/0.60 for arrays would require changing
that rule, which is **frozen** and therefore raised rather than done.

## 4. Via arrays — sized so the transition never limits the copper

**Rule applied:** an array must carry at least what the copper on either side
carries. Two sizing methods are computed and **the larger is used**.

| Transition | I | Match plane | n by area | n by 1.5 A | **Use** | R_array | Field |
|---|--:|--:|--:|--:|--:|--:|--:|
| Battery entry → bus | 115 A | 3.90 mm² | 153 | 77 | **153** | 7.05 µΩ | 13×13 |
| VBAT bus L6↔L1 | 115 A | 3.90 mm² | 153 | 77 | **153** | 7.05 µΩ | 13×13 |
| VBAT → channel branch | 28.8 A | — | — | 20 | **20** | 53.9 µΩ | 5×5 |
| Phase L6↔L4 | 28.8 A | — | — | 20 | **20** | 53.9 µΩ | 5×5 |
| Bulk capacitor return | 115 A | — | — | 77 | **77** | 14.0 µΩ | 9×9 |

**The conventional 1.5 A/via rule under-specifies the main bus by 2×** — 77
vias against the 153 needed to match the plane copper. A transition that merely
passes the current rule can still be a resistive step relative to the pour
either side of it. That is the bottleneck this section exists to prevent.

## 5. Via placement

| Location | Array | Note |
|---|---|---|
| U3 battery pads → bus | 13×13 | at the pad, both polarities |
| Centre-strip bus transitions | 13×13 | distributed along the strip |
| Bus → each channel branch | 5×5 | ×4 |
| Phase L6↔L4 | 5×5 | ×12 |
| Bulk capacitor return | 9×9 | paired with its forward path |
| FET thermal pads | 5×5 | ×24, §6 |

**Forward and return arrays must be paired and adjacent.** A return path that
takes a different route from its forward path encloses loop area, which is the
thing §7 exists to minimise.

## 6. MOSFET thermal vias — and the R_spread correction

**The verified footprint is not modified.** Electrical land geometry, pads,
mask and the windowpane paste are unchanged. Thermal vias are a **layout**
feature placed into the pad region at layout time.

| Option | Field | R_th |
|---|---|--:|
| 0.30 mm at 0.80 mm pitch | 5×5 = **25 vias** | 6.51 K/W |
| 0.25 mm at 0.70 mm pitch | 6×5 = 30 vias | 6.41 K/W |

### The spreading network, done properly

| Path | R_th |
|---|--:|
| B.Cu alone (2 oz) | 7.27 K/W |
| Inner layers alone (4 × 1 oz) | 3.63 K/W |
| Through 25 thermal vias | 6.51 K/W |
| **Via path** = vias + inner (series) | 10.15 K/W |
| **B.Cu ∥ via path** | **4.23 K/W** ← real |
| Earlier ideal-plate model | 1.82 K/W ← optimistic |

Extra junction rise: **+3.1 K** hover, **+5.4 K** peak.

### Consequence

| Case | Was | **Now** | vs 175 °C |
|---|--:|--:|---|
| Hover, slipstream | 103.2 °C | **106.3 °C** | OK — still meets 125 °C |
| Hover, at disc | 128.9 °C | **132.0 °C** | over target |
| Peak, slipstream | 133.7 °C | **139.1 °C** | over target |
| **Peak, at disc** | 171.4 °C | **176.8 °C** | **EXCEEDS ABSOLUTE MAXIMUM** |

Sustained peak at the disc previously sat 3.6 °C below the limit. It now sits
**1.8 °C above it**. Board-to-air still dominates, so **more copper and more
vias do not fix this** — but the model was flattering and is corrected.

### Via-in-pad manufacturing

Vias in the thermal pad **will wick solder** unless filled and capped.

| Approach | Requires | Status |
|---|---|---|
| Filled and capped (VIPPO) | fab supports resin fill + cap plating | **OPEN — assumed, not confirmed** |
| Tented on the opposite side | mask over the far end | cheaper; partial protection |
| Vias outside the pad | more spreading distance | worse thermally |

**No via-in-pad assumption is adopted here.** The 4.23 K/W figure assumes vias
that conduct; if the fab cannot fill and cap, the thermal case gets worse again.

## 7. Switching-loop copper

Budget **8.72 nH** at 80 % of 60 V. *(7.53 nH is superseded and unused.)*

| Element | Geometry requirement |
|---|---|
| High-side path | VBAT pour on L6, minimal length to the drain |
| Switching node | L6 only, smallest area that carries 28.8 A |
| Low-side return | **L5 solid ground, 0.10 mm below L6** |
| DC-link ceramic | ≥2 × 4.7 µF within 2 mm, same side, across the bridge |
| Gate-drive return | same L5 region as the FET source, never a separate route |

The loop closes **vertically** through the 0.10 mm L6→L5 prepreg, not laterally.
No via is permitted inside the commutation loop: a via adds height, and height
is loop area.

## 8. Current bottleneck audit

| Segment | I | A_cu | Layers | Vias | R | Drop | Loss | Limiting element |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| U3 battery pads | 115 A | 135 mm² | 1 | — | ~0 | 0.11 mV | 0.01 W | pad area, ample |
| **Shunt 2 × 0.2 mΩ** | 115 A | — | 1 | — | 0.100 mΩ | 11.50 mV | **1.32 W** | **by design** |
| Battery → bus vias | 115 A | — | — | 133 | 0.008 mΩ | 0.93 mV | 0.11 W | via array |
| VBAT bus, 4 layers | 115 A | 3.90 mm² | 4 | — | 0.110 mΩ | 12.69 mV | **1.46 W** | copper, ample |
| Branch to channel | 28.8 A | 0.69 mm² | 2 | 20 | 0.300 mΩ | 8.61 mV | 0.25 W | copper |
| **MOSFET R_DS(on) ×2** | 28.8 A | — | — | — | 4.500 mΩ | 129.4 mV | **3.72 W** | **semiconductor** |
| Phase copper | 28.8 A | 0.46 mm² | 1 | — | 0.374 mΩ | 10.76 mV | 0.31 W | copper |
| Phase pads (U3) | 28.8 A | 5.28 mm² | 1 | — | ~0 | 0.03 mV | 0.00 W | soldered wire |

**Smallest-capacity element: none of the copper.** The largest losses are the
MOSFET channel (3.72 W) and the shunt (1.32 W), both deliberate design choices
rather than bottlenecks to remove. **J1 is excluded from this chain entirely**
at 0.7 A per contact.

## 9. Manufacturability

| Item | Value | Status |
|---|---|---|
| 2 oz outer vs 0.4 mm pitch QFN | pads exactly 0.200 mm | **OPEN — zero margin, see stackup §6.1** |
| Minimum trace/space, 2 oz | 0.16 mm assumed | **OPEN** |
| Via aspect ratio | 5.3:1 at 0.30 mm | routine; **plating thickness OPEN** |
| Annular ring | 0.15 mm at 0.30/0.60 | **OPEN** |
| Via pitch | 0.80 mm | acceptable |
| Thermal relief | none — solid connection preferred on power pads | **OPEN — assembly impact** |
| Solder-mask clearance | mask slivers between 0.4 mm pitch pads on 2 oz | **OPEN — may be unachievable** |
| 0402 / 0201 compatibility | 0201 present, 0.18 mm gaps | **OPEN at 2 oz** |
| RF clearance | 0.30 mm rule present | impedance widths **OPEN** |
| Via-in-pad fill and cap | assumed for thermal vias | **OPEN — not confirmed** |
| Three degenerate footprints | 5–10 µm pads | **BLOCKING — unbuildable** |

## 10. Thermal

**THERMAL STATUS: MARGINAL.** More copper does not solve it. R_θ(j-c) plus
spreading is now 5.02 K/W against a board-to-air term of 3.33–13.33 K/W;
board-to-air still dominates. Airflow exposure and duty cycle remain the primary
unresolved variables. h = 80 W/m²·K is not used.

The correction in §6 makes the peak case **worse**, not better — which is the
point of correcting it.

---

## Open items

1. Plating thickness at the chosen via aspect ratio
2. Via-in-pad fill and cap capability
3. 2 oz minimum trace/space
4. Annular ring at 0.30/0.60
5. Solder-mask slivers on 0.4 mm pitch at 2 oz
6. 0201 at 2 oz
7. Thermal relief vs solid connection on power pads
8. Impedance trace widths (fab calculates)
9. Adopting 0.30/0.60 arrays would change the frozen 0.8/0.4 via rule
10. **Peak at the disc now exceeds 175 °C** — see §6
11. 115 A peak duration and duty cycle *(frozen OPEN)*
12. Airflow boundary condition *(frozen OPEN)*
13. Three degenerate footprints, unbuildable at any copper weight

**VIA/COPPER DESIGN: OPEN ITEMS**
**ROUTING STATUS: BLOCKED**
