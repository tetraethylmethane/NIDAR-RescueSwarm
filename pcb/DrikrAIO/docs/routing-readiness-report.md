# DrikrAIO — Routing Readiness Report

# ROUTING STATUS: BLOCKED

**Reasons:**

1. **115 A peak duration unresolved**
2. **115 A repetition rate unresolved**
3. **Airflow boundary condition unresolved**
4. **Thermal validation plan unresolved**
5. **BSC014N06NS schematic commitment intentionally deferred**

Date 2026-09-05 · Baseline rev 3, **FROZEN**:
[`pre-routing-baseline.json`](pre-routing-baseline.json) ·
[`freeze-manifest.json`](freeze-manifest.json)

**The baseline is frozen.** 16 artefacts recorded by SHA-256 with the state
assertions that held at freeze time. `hardware/tools/freeze.py` verifies it and
exits non-zero on any drift — tested by injecting a Phase-width regression,
which it caught by both hash and assertion.

Unfreezing is a deliberate, reviewed act requiring the peak duration, duty
cycle, airflow specification and executed validation plan. **Do not unfreeze to
make progress.**

No routing performed. No Gerbers, drill files or fabrication outputs generated.
No peak duration, repetition rate or airflow condition invented.

---

## PASS

| # | Item | Evidence |
|---|---|---|
| 1 | BSC014N06NS Rev 2.6 transient architecture | 60 V; di/dt 2.61 A/ns from datasheet t_f = 11 ns |
| 2 | **8.72 nH** switching-loop budget | 80 % derating of 60 V against 25.2 V rail |
| 3 | Corrected footprint | `BSC014N06NS_PG-TDSON-8.kicad_mod`, **25/25** |
| 4 | Phase/VBAT netclasses = 6.6 mm | applied, vias 0.8/0.4 |
| 5 | All 8 netclasses verified after SaveBoard | `verify_netclasses.py` |
| 6 | SaveBoard regression detection is a **hard build gate** | `build_pcb.py` exits non-zero |
| 7 | All 10 design-rule minimums compared for **exact equality, both directions** | `verify_netclasses.py` |
| 8 | Fault injection fails correctly on `min_clearance` 0.09 → 0.0 | tested, exit 1 |
| 9 | 7.53 nH **SUPERSEDED** | purged from live use; older docs bannered |
| 10 | h = 80 W/m²·K **SUPERSEDED** | absent from the live thermal model |

## NOT PASS — thermal is MARGINAL

The thermal architecture is **not** PASS. It is **MARGINAL**.

| Case | h | T_j hover | T_j peak sustained |
|---|--:|--:|--:|
| A — at the disc, 6.23 m/s | 42 | **128.9 °C** ❌ | **169.9 °C** ❌ |
| B — slipstream, 12.46 m/s | 60 | **103.2 °C** ✅ | **132.7 °C** ❌ |
| still air *(safety fact)* | 15 | 282.8 °C | 393 °C |

- 125 °C is the design target; **175 °C is the absolute maximum, not a target**.
- Peak fails the 125 °C target at **both** airflows.
- At case A, peak leaves **5.1 °C** to the absolute maximum.
- **Only one steady-state case passes: hover in developed slipstream.**
- Rotor-disc / slipstream placement is a **thermal design parameter**.
- The design is **not** "propwash cooled" — see the placement study.

### Primary remaining variables: airflow and duty cycle

**More copper is not the primary solution.**

### The result that redirects the work

R_θ(j-c) + R_spread contribute only **5.7 K** of the total rise. Everything else
is board-to-air.

**More thermal vias, more copper pour, or a lower-R_DS(on) part cannot fix the
peak case.** The bottleneck is getting heat off the board, not out of the die.
The only two levers that work are **airflow exposure** and **duty cycle**.

Remediation, solved from the steady-state peak case:

| Lever | Required | Available |
|---|--:|--:|
| Airflow | h = 65.8 (≈15.1 m/s) | 42 / 60 (6.23 / 12.46 m/s) |
| Board area at h=60 | 55 cm² (≈52 × 52 mm) | 50 cm² — violates the mechanical constraint |

### And the result that may make it moot

Board thermal time constant **τ ≈ 31–45 s** *(estimate)*.

A peak much shorter than that barely moves the board. **The duration threshold
that matters is tens of seconds, not milliseconds.** At h = 60, duty cycles up
to **0.5** stay under the 125 °C target.

So the peak case may never apply — but **duty cycle is OPEN**, so no row of that
table can be selected as the operating condition.

> **Peak thermal acceptability cannot be determined from peak current alone.
> Peak duration and repetition rate determine whether the 115 A condition is a
> transient event or a thermally significant operating condition.**

## OPEN

| # | Item | Baseline field | Status |
|---|---|---|---|
| 1 | 115 A peak duration | `peak_duration_ms: null` | **OPEN** |
| 2 | 115 A repetition rate / duty cycle | `peak_repetition_rate_Hz: null`, `peak_duty_cycle: null` | **OPEN** |
| 3 | Airflow boundary condition | `airflow_boundary_condition: null` | **OPEN** |
| 4 | Thermal validation plan | `thermal_validation_plan: null` | **OPEN** — drafted, not executed |
| 5 | Placement case P3 (partially obstructed) | — | **REQUIRES MECHANICAL INPUT** |

None of these has been turned into a PASS by assumption.

## Deliverables

| Document | State |
|---|---|
| [`pre-routing-baseline.json`](pre-routing-baseline.json) | rev 2 — OPEN statuses and engineering statement recorded |
| [`thermal-analysis.md`](thermal-analysis.md) | parameterised; steady-state / single-pulse / repeated-pulse separated; placement study |
| [`thermal-validation-plan.md`](thermal-validation-plan.md) | draft; C1 bench forced-air, C2 installed aircraft, C3 still air prohibited above quiescent |
| [`routing-readiness-report.md`](routing-readiness-report.md) | this document |
| [`pre-routing-review-2.md`](pre-routing-review-2.md) | prior review, still valid for §1–§13 |
| `electrical-design-review.md`, `pre-routing-report.md` | **SUPERSEDED**, bannered |

## Build gate — enforced

```
CREATE FRESH BOARD → APPLY NETCLASSES → APPLY DESIGN RULES → SAVE → RELOAD
  → VERIFY 8 NETCLASSES → VERIFY 10 DESIGN RULES → VERIFY WIDTHS/VIAS/CLEARANCES
  → [only then] DRC → [only then] MANUFACTURING OUTPUT
```

On failure: exit non-zero, no DRC, no Gerbers, no drill files, no fabrication
outputs. Verified by fault injection, and by a fresh-board vs loaded-board
save-cycle test that reproduces the regression on demand.

## Prohibited, restated

No routing. No auto-routing. No Gerbers, drill files or fabrication package. No
committing BSC014N06NS to the schematic. No inventing peak duration, repetition
rate or airflow. **7.53 nH** and **h = 80 W/m²·K** must not reappear. 175 °C is
not an operating target. Do not describe the design as "propwash cooled". Design
below 8.72 nH with margin, not up against it.

---

# ROUTING STATUS: BLOCKED

Stopping here. No further speculative engineering changes.
