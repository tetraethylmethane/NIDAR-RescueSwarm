# RescueSwarm — Configuration Trade and Sizing-Constraint Review
### NIDAR 2026–27 Track 1 · Companion to `sizing-calculations.md`

**Status: recommendations, not adopted design.** The design point in
[`sizing-calculations.md`](sizing-calculations.md) and the README is unchanged —
quadrotor, 20 in props, 6S2P, T/W 2.0. Nothing here has been folded into the
baseline. Items marked **PROPOSED** need a decision before they become design.

**Reproduce:** `python tools/sizing-model/config_trade.py`
→ committed output in [`config-trade-output.txt`](config-trade-output.txt).

---

## 0. Summary

| Question | Answer |
|---|---|
| Should we go coaxial (X8)? | **No.** ~30 % hover-power penalty for zero footprint benefit. |
| Is there a better rotor configuration? | **Hex 6×18″** beats the quad on physics (−7 % power), but costs setup time. |
| Should we spend mass margin on thrust-to-weight? | **No.** Attitude authority is never the wind limit. |
| What should we actually size against? | **Wind penetration and detection recall** — not mass, coverage time or link margin. |

---

## 1. Configuration trade

Mass scales with **motor** count; induced power scales with **disk** count. This
distinction is the whole coaxial argument, and it is why the trade needs its own
script: `prop_area()` in the main model multiplies disk area by `N_rot`, which
silently assumes every rotor has its own free-stream disk. A coaxial pair does
not — the two rotors share one actuator disk.

Pack held constant at 194 Wh, so endurance moves only through hover power.

| Config | MTOW kg | Fleet kg | P_hov W | Disk load kg/m² | Hover min | Footprint mm | Fits box | ΔP |
|---|---|---|---|---|---|---|---|---|
| **Quad 4×20″** (current) | 5.05 | 15.16 | 601 | 6.23 | 15.5 | 1046 | 3/row | — |
| Hex 6×16″ | 5.00 | 14.99 | 603 | 6.42 | 15.5 | 1279 | 2/row | +0.3 % |
| **Hex 6×18″** | 5.11 | 15.34 | **560** | **5.19** | **16.7** | 1432 | 2/row | **−7.0 %** |
| Octo 8×14″ flat | 4.98 | 14.94 | 595 | 6.27 | 15.7 | 1363 | 2/row | −1.0 % |
| X8 coax 4×2×20″ (κ=0.85) | 5.45 | 16.34 | 775 | 6.72 | 12.0 | 1046 | 3/row | +28.8 % |
| X8 coax 4×2×20″ (κ=0.80) | 5.45 | 16.34 | **819** | 6.72 | **11.4** | 1046 | 3/row | **+36.3 %** |
| X8 coax 4×2×22″ (κ=0.80) | 5.66 | 16.98 | 791 | 5.77 | 11.8 | 1148 | 3/row | +31.5 % |

### 1.1 Why not coaxial

Coaxial costs **+29–36 % hover power and 3.5–4 minutes of endurance** for +8 %
mass. What it is supposed to buy is compactness — and here it buys none:
**stacking rotors does not shorten the arms**, so the X8 has the identical
1046 mm footprint as the quad it replaces. Coaxial earns its penalty only when
the airframe is footprint-constrained and rotors must shrink to fit. Ours is not:
the quad already fits three abreast in the 3.66 m launch box.

The conclusion is insensitive to the interference factor. Even at an
implausibly generous κ = 0.95, coaxial is ~15 % worse for no compensating gain.

Coaxial would become worth revisiting only if the launch box shrank far enough
to force rotor diameter down, or if a transport-case constraint appeared that
the folding-prop quad could not meet.

### 1.2 The hex result is real

Hex 6×18″ is the only configuration that beats the quad on physics: six 18 in
disks give **0.985 m²** of disk area against the quad's **0.811 m²** — 21 % more
— so disk loading falls to 5.19 kg/m² and hover power to 560 W. It also adds
single-motor-out controllability, which the main model already prices at
"affordable" in its STEP 6 trade.

Its cost is not aerodynamic. Two more motors and ESCs mean more preflight
checks, more assembly, and a 1432 mm airframe to unpack — and all of that lands
on **setup time, the only constraint in the system with under 20 % margin**.
That is the trade to argue about, not the power number.

**PROPOSED:** treat hex 6×18″ as the redundancy option of record, and decide it
against measured cold-boot and assembly timings in Phase 5 rather than now.

---

## 2. Sizing-constraint review

The model currently sizes against mass and energy. Both have enormous margin:

| Constraint | Limit | Design | Margin | Binding? |
|---|---|---|---|---|
| Fleet mass | 25 kg | 15.16 kg | 39 % | No |
| Mission time | 30 min | 7.7 min | 74 % | No |
| Coverage | 10 ha | 93 s/drone | ~95 % | No |
| Link margin | — | 13.7 dB @ 600 m | large | No |
| Peak current | 90 A burst | 74 A | 21 % | No |
| **Setup to launch** | **300 s** | **~285 s** | **5 %** | **Yes** |
| **Wind penetration** | **unspecified** | **fails at 8 m/s** | **none** | **Yes, unstated** |
| **Detection recall** | **≥ 0.90** | **unmeasured** | **unknown** | **Yes, long pole** |

Sizing effort is currently going into the top half of that table.

### 2.1 Do not spend mass margin on thrust-to-weight

| T/W | MTOW kg | Fleet kg | Margin kg | P_hov W | Hover min | Hover throttle |
|---|---|---|---|---|---|---|
| **2.0** | 5.05 | 15.16 | 9.84 | 601 | 15.5 | 50 % |
| 2.2 | 5.16 | 15.49 | 9.51 | 620 | 15.1 | 45 % |
| 2.5 | 5.34 | 16.02 | 8.98 | 649 | 14.4 | 40 % |
| 3.0 | 5.66 | 16.99 | 8.01 | 703 | 13.3 | 33 % |

CORRECTION 4 of the main model settles this: tilt reaches only **12.2° at 15 m/s
airspeed**, a thrust factor of 1.023. Attitude authority is never the wind limit.
Raising T/W to 2.5 costs 1.1 min of endurance and buys almost nothing.
**Keep T/W 2.0.**

### 2.2 Wind is the real cliff, and it is not a requirement yet

From CORRECTION 4, sweep time per drone against wind:

| Wind | Sweep time | vs still air |
|---|---|---|
| 0 m/s | 83 s | — |
| 4 m/s | 111 s | +33 % |
| 6 m/s | 191 s | +129 % |
| 8 m/s | **cannot make headway at search speed** | — |

Search groundspeed is 8 m/s, so at 8 m/s of wind the aircraft cannot progress
upwind at all. This is a **total mission failure at an ordinary flood-weather
wind speed**, and no requirement currently forbids it. It is not a power
problem: penetrating at 12 m/s costs 105 W against a 601 W hover draw.

**PROPOSED:** state a maximum sustained wind requirement (suggest **10 m/s**),
and size search *airspeed* to retain headway at it while still flying 8 m/s
*groundspeed* nominally. Add a verification target alongside SYS-21.

### 2.3 Search altitude should be an output, not an input

60 m AGL is currently an input. Recall is called the long pole of the programme,
and coverage time is nearly free — so altitude should fall out of a recall
requirement instead.

| AGL | GSD | Person | Sweep/drone | Mission budget used |
|---|---|---|---|---|
| 60 m | 1.82 cm/px | 93 px | 93 s | 5 % |
| **40 m** | **1.22 cm/px** | **140 px** | **149 s** | **8 %** |
| 30 m | 0.91 cm/px | 186 px | 187 s | 10 % |

Dropping to 40 m gives **50 % more pixels on target** for 56 s out of a 1800 s
budget. It also shrinks the **largest geotag error term**: the 2.76 m
ground-height term scales with the 37 m frame-edge distance, which comes down
with altitude. Two of the three genuinely hard problems improve, paid for in the
one currency held in surplus.

**PROPOSED:** re-baseline search altitude to 40 m pending Phase 7 recall-vs-GSD
measurements, and make altitude an output of the recall requirement.

---

## 3. Assumptions introduced here

| Assumption | Value | Basis | Replace with |
|---|---|---|---|
| Coaxial interference factor κ | 0.80–0.85 | Published multirotor coaxial data; **the only figure imported from outside the model** | Bench thrust-stand test, if coaxial is ever revisited |
| Prop mass scaling | ∝ D^2.5 | Planform × thickness. Main model holds prop mass fixed across diameters, which flatters larger rotors slightly | Vendor mass data at 16/18/20 in |
| Hex/octo arm geometry | Rotor centres on a circle, 30 mm tip clearance | Same convention as main model STEP 11 | CAD once frame layout is fixed |

Every other constant is imported live from `rescueswarm_sizing_model.py`.
