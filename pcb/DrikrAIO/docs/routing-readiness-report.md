# DrikrAIO — Routing Readiness Report

**ROUTING = NO-GO.**

Date 2026-09-05. Baseline: [`pre-routing-baseline.json`](pre-routing-baseline.json).
No routing performed. BSC014N06NS not committed to the schematic. No peak
duration invented.

---

## PASS

| # | Item | Evidence |
|---|---|---|
| 1 | **MOSFET transient architecture** | BSC014N06NS, 60 V. di/dt = 28.75 A / 11 ns = 2.61 A/ns; 80 %-derated budget **8.72 nH**. 3.9× the 40 V part's 2.25 nH. Verified from Rev 2.6, not carried over. |
| 2 | **Corrected footprint** | `lib.pretty/BSC014N06NS_PG-TDSON-8.kicad_mod`, **25/25 checks pass**. Electrical land preserved; paste windowpane 4 × 1.70 × 1.55 mm at 58.4 %; courtyard added. |
| 3 | **Netclass corrections** | `Phase`/`VBAT` 1.0 → 6.6 mm, vias 0.8/0.4. All 8 classes present. |
| 4 | **SaveBoard regression detection** | Reproduced deterministically and now a **hard build gate**. |

### On (4) — the gate is now real

`build_pcb.py` exits non-zero and refuses to continue if verification fails. No
DRC, no manufacturing outputs, on a board whose rules were lost.

Deliberate fault injection found a bug **in the verifier itself**: it only
flagged design rules that moved *up*, so `min_clearance` 0.09 → **0.0** — the
exact regression it exists to catch — was waved through as "tighter". A minimum
going down is a weakened rule. All ten board minimums are now checked for
**exact equality in both directions**. Re-tested: injected fault → exit 1;
restored → exit 0.

---

## FAIL / OPEN

| # | Item | Owner | Blocks |
|---|---|---|---|
| 1 | **115 A peak duration** | system / firmware | Routing, and 6 dependent calculations |
| 2 | **115 A repetition rate / duty cycle** | system / firmware | Repeated-peak accumulation |
| 3 | **Reproducible airflow specification** | mechanical / test | Thermal validation, bench safety |
| 4 | **Final thermal validation plan** | hardware / test | Thermal sign-off |

**115 A peak duration and repetition rate are unresolved system requirements.**

---

## Thermal — the previous PASS does not survive

You asked me to define the airflow rather than write "propwash cooled". Doing
that **withdraws the earlier verdict.**

The 32.1 K/W / 111.8 °C result used **h = 80 W/m²·K**. Derived from momentum
theory on the actual design point (disc loading 9.69 kg/m², from
`docs/sizing/model-output.txt`):

| | Velocity | h |
|---|--:|--:|
| Induced, at the disc | 6.23 m/s | 42 W/m²·K |
| Fully developed slipstream | 12.46 m/s | 60 W/m²·K |
| **h = 80 requires** | **22.4 m/s** | — |

**h = 80 needs almost double this aircraft's own slipstream.** Against airflow
it actually produces:

| Condition | T_j at the disc (h=42) | T_j in slipstream (h=60) |
|---|--:|--:|
| Hover | 128.9 °C ❌ | 103.2 °C ✅ |
| **Peak** | **171.4 °C** ❌ | **133.7 °C** ❌ |

Still air remains catastrophic: 282.8 °C hover, 397.5 °C peak.

**Nothing exceeds the 175 °C absolute maximum**, so the design is not
disqualified — but the **conservative 125 °C target is not met at peak under any
airflow this aircraft produces**, and 171.4 °C at the disc sits 3.6 °C from the
hard limit.

Consequences:

- Thermal status moves from **PASS WITH CONDITION** to **MARGINAL — does not
  meet the 125 °C target at peak**.
- **Mounting position relative to the rotor disc is now a thermal design
  parameter**, not a mechanical convenience. Slipstream is worth ~38 °C.
- This sharpens open item 1: if the 115 A peak is short and rare it is
  irrelevant; if it is sustained, the peak case governs. **The duration decides
  whether this matters at all.**
- h is calculated, not measured. R_θ(j-a) must be measured on the first board.

---

## Bench-test safety requirement

**Full-power bench testing requires controlled forced airflow.**

Do not run sustained 115 A on a stationary board without it: still air gives
~398 °C junction, which destroys the parts.

The airflow used for any thermal measurement must be **stated and reproducible**
— velocity, direction and distance — not described as "propwash". The reference
conditions for this design are 6.23 m/s (at the disc) and 12.46 m/s (developed
slipstream), and a bench setup should bracket both.

---

## Prohibited, restated

No routing. No auto-routing. No Gerbers, drill files or fabrication package. No
committing BSC014N06NS to the schematic. **7.53 nH** and **h = 80 W/m²·K** are
superseded and must not reappear — earlier documents now carry SUPERSEDED
banners and their live values have been corrected.

Design to **below** 8.72 nH; do not route up against the calculated limit.

---

## Verdict

**ROUTING = NO-GO.**

Four gate items pass. Two fail outright (peak duration, repetition rate), one is
undefined (airflow specification), one is not yet written (validation plan), and
the thermal verdict has weakened from PASS to MARGINAL on closer analysis.

Stopping here as instructed. No further speculative PCB changes.
