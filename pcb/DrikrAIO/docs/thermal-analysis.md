# DrikrAIO — Parameterised Thermal Analysis

**Status: MARGINAL — not PASS.** No fake PASS is constructed here.

Regenerates from [`hardware/tools/thermal_param.py`](../hardware/tools/thermal_param.py).
Device data: Infineon BSC014N06NS Rev 2.6. **h = 80 W/m²·K is superseded and is
not present in the live model.**

T_j ≤ **125 °C** is the design target. T_j = **175 °C** is the absolute maximum
and **is not an operating target**.

---

## Model

T_j is evaluated as a function of peak current, peak duration, repetition rate,
ambient, airflow coefficient, MOSFET count, R_DS(on), copper spreading and
board-to-air resistance.

| Term | Value | Source |
|---|--:|---|
| R_DS(on) @125 °C | 2.25 mΩ | DATASHEET × Diagram 9 |
| R_θ(j-c) max | 0.80 K/W | DATASHEET |
| R_spread | 1.81 K/W | CALCULATED, radial thin-plate, 280 µm effective Cu |
| Board area | 50 cm² (both sides) | 50 × 50 mm |
| MOSFETs | 24 → 2.08 cm² each | — |
| Board heat capacity | 9.3 J/K | **ESTIMATE** — 1.6 mm FR4 + ~50 % Cu |
| Ambient | 40 °C | ASSUMED |
| f_PWM | 24 kHz | ASSUMED (AM32 default), unverified |

**Airflow — the two conditions this aircraft actually produces.** Derived from
momentum theory on disc loading 9.69 kg/m², then flat-plate correlation
Nu = 0.664 Re^0.5 Pr^(1/3) at L = 50 mm:

| Case | Velocity | h |
|---|--:|--:|
| **A** — at the disc | 6.23 m/s | **42 W/m²·K** |
| **B** — developed slipstream | 12.46 m/s | **60 W/m²·K** |
| *(still air, safety reference only)* | — | 15 W/m²·K |

---

## 1. Steady state — the trustworthy regime

| Case | Condition | P/FET | P/board | T_board | **T_j** | Verdict |
|---|---|--:|--:|--:|--:|---|
| A | hover | 1.28 W | 17.96 W | 125.5 °C | **128.9 °C** | OVER TARGET |
| A | peak sustained | 2.20 W | 26.08 W | 164.2 °C | **169.9 °C** | OVER TARGET |
| B | hover | 1.28 W | 17.96 W | 99.9 °C | **103.2 °C** | **PASS** |
| B | peak sustained | 2.20 W | 26.08 W | 126.9 °C | **132.7 °C** | OVER TARGET |

Still air at peak: **393 °C** — reported as a safety fact, never a design case.

**Only one steady-state case passes: hover in developed slipstream.**

## 2. Single pulse — package level only

T_j(t) = T_j,steady(hover) + ΔP × Z_th(J-C)(t), ΔP = 0.92 W/FET.

| Pulse | Z_th(J-C) | ΔT_j | T_j (case A) | T_j (case B) |
|--:|--:|--:|--:|--:|
| 0.1 ms | 0.010 | 0.01 K | 128.9 °C | 103.2 °C |
| 1 ms | 0.030 | 0.03 K | 128.9 °C | 103.2 °C |
| 10 ms | 0.100 | 0.09 K | 129.0 °C | 103.3 °C |
| 100 ms | 0.300 | 0.28 K | 129.2 °C | 103.5 °C |
| 1 s | 0.500 | 0.46 K | 129.3 °C | 103.7 °C |

**Z_th(J-C) stops at the case.** It bounds the die, not the board, and is not
extrapolated to junction-to-ambient — Rev 2.6 contains no Z_th(J-A) and none is
invented. Package-level excursion is negligible at every duration the datasheet
covers, and **that does not close the peak case.**

## 3. Repeated pulse — board level, driven by average power

The board responds to **average** power, not pulse shape. That *is* computable
as a function of duty cycle.

**Board thermal time constant τ = C × R_conv** *(ESTIMATE)*:

| Case | R_conv | **τ** |
|---|--:|--:|
| A (h=42) | 4.76 K/W | **44.5 s** |
| B (h=60) | 3.33 K/W | **31.2 s** |

**This is the number that decides whether the 115 A peak matters at all.** A
peak much shorter than ~30–45 s barely moves the board; one comparable to it
drives the board toward its average-power steady state. **The threshold is tens
of seconds, not milliseconds.**

| Duty | Case A P_avg | T_j | | Case B P_avg | T_j |
|--:|--:|--:|---|--:|--:|
| 0.00 | 17.96 W | 128.9 °C ❌ | | 17.96 W | **103.2 °C** ✅ |
| 0.05 | 18.37 W | 130.9 °C ❌ | | 18.37 W | **104.7 °C** ✅ |
| 0.10 | 18.77 W | 133.0 °C ❌ | | 18.77 W | **106.2 °C** ✅ |
| 0.25 | 19.99 W | 139.1 °C ❌ | | 19.99 W | **110.6 °C** ✅ |
| 0.50 | 22.02 W | 149.4 °C ❌ | | 22.02 W | **117.9 °C** ✅ |
| 1.00 | 26.08 W | 169.9 °C ❌ | | 26.08 W | 132.7 °C ❌ |

**In slipstream, duty cycles up to 0.5 stay under the 125 °C target.** At the
disc, nothing passes — not even hover.

**Duty cycle is UNRESOLVED, so no row above can be selected as the operating
case.** The table is the shape of the answer, not the answer.

## 4. What would make T_j ≤ 125 °C at sustained peak

Solving the steady-state peak case for each lever, others held:

| Lever | Required | Available | Verdict |
|---|--:|--:|---|
| Airflow | **h = 65.8** (≈15.1 m/s) | 42 / 60 (6.23 / 12.46 m/s) | just out of reach |
| Board area at h=60 | **55 cm²** (≈52 × 52 mm) | 50 cm² (50 × 50 mm) | violates the mechanical constraint |
| Lower R_DS(on) | — | — | **cannot fix it** |
| More thermal vias / copper | — | — | **cannot fix it** |

**R_θ(j-c) + R_spread contribute only 5.7 K of the total rise.** Everything else
is board-to-air. That is the single most useful result here: **effort spent on
thermal vias, copper pours or a lower-R_DS(on) part buys almost nothing at
sustained peak.** The bottleneck is getting heat off the board, not out of the
die.

The two levers that do work are **airflow exposure** and **duty cycle**.

## 5. Placement sensitivity study

Because airflow dominates, placement relative to the rotor disc is a thermal
design parameter worth ~26 K at hover and ~37 K at peak.

| Case | Airflow | h | T_j hover | T_j peak sustained | Status |
|---|---|--:|--:|--:|---|
| **P1** — directly in developed slipstream | 12.46 m/s | 60 | **103.2 °C** ✅ | 132.7 °C ❌ | Best available |
| **P2** — near disc-flow region | 6.23 m/s | 42 | 128.9 °C ❌ | 169.9 °C ❌ | Fails even at hover |
| **P3** — partially obstructed by structure | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** | **REQUIRES MECHANICAL INPUT** |
| **P4** — enclosed / still air | ~0 | 15 | 282.8 °C ❌ | 393 °C ❌ | Not survivable |

**P3 cannot be evaluated without mechanical geometry.** Blockage ratio, standoff
height, frame members and any canopy over the stack all reduce the effective
velocity below case A, and no geometry has been supplied. **This case is marked
as requiring mechanical input and is not estimated.**

Placement requirements that follow:

1. The power stage must sit in **developed slipstream (P1)**, not in the
   near-disc region.
2. Mounting height and orientation relative to the rotor plane must be treated
   as **thermal design parameters** and stated in the mechanical interface.
3. Any structure between the rotors and the board moves the design toward P3,
   which is **unquantified**. Obstruction must be identified before layout is
   frozen.
4. **No enclosure over the power stage.**

## 6. Conclusion

Sustained 115 A is **not thermally acceptable at either airflow**. Whether that
matters depends entirely on duration and repetition rate, which are **OPEN**.

- If the peak is **short relative to τ ≈ 31–45 s and infrequent**, the
  steady-state peak row never applies and case B closes comfortably.
- If the peak is **sustained**, no amount of copper, vias or lower R_DS(on)
  fixes it inside 50 × 50 mm.

**Peak thermal acceptability cannot be determined from peak current alone. Peak
duration and repetition rate determine whether the 115 A condition is a
transient event or a thermally significant operating condition.**

### Assumptions that move these numbers

| Assumption | Effect |
|---|---|
| h from flat-plate correlation, not measured | dominant uncertainty in every result |
| Board heat capacity 9.3 J/K (ESTIMATE) | sets τ, hence the duration threshold |
| Ambient 40 °C | shifts all T_j one-for-one |
| f_PWM 24 kHz (assumed) | switching loss scales linearly |
| P_avionics 3 W (estimate) | small, but unsourced |
| Phase RMS = 2× battery current at 50 % duty | conduction loss scales as I² |

**R_θ(j-a) must be measured on the first board.** See
[thermal-validation-plan.md](thermal-validation-plan.md).
