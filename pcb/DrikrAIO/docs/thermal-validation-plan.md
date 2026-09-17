# DrikrAIO — Thermal Validation Plan (Draft)

**Status: DRAFT — `thermal_validation_status: OPEN` in the baseline.**

Purpose: measure R_θ(j-a) and T_j on the first prototype, and determine whether
the 115 A condition is a transient event or a thermally significant operating
condition. Predicted values come from
[thermal-analysis.md](thermal-analysis.md); this plan exists to test them, not
to confirm them.

**Still-air full-power operation is not acceptable and is not a pass condition
anywhere in this plan.**

---

## 1. Temperature measurement locations

| ID | Location | Method | Why |
|---|---|---|---|
| T1–T4 | Case top of one FET per channel (Q_x_high) | fine-gauge thermocouple, thermally bonded | hottest expected devices |
| T5 | Case top of the FET furthest from airflow | thermocouple | worst-case placement |
| T6 | Drain pour, 5 mm from a FET | thermocouple | copper spreading check |
| T7 | Board centre, opposite side | thermocouple | board bulk temperature |
| T8 | Shunt / INA186 region | thermocouple | sense-path drift |
| T9 | Bulk capacitor can | thermocouple | capacitor stress |
| T10 | Board edge, upstream of airflow | thermocouple | inlet reference |
| — | Whole board | IR thermography | finds hot spots the couples miss |

IR emissivity must be calibrated against T7. Thermocouples must be bonded, not
taped, and their leads run along an isotherm before leaving the board.

## 2. Junction-temperature estimation

Two independent methods; they must agree within 10 K or the result is void.

**Method A — case temperature plus computed rise.**
T_j = T_case + P_FET × R_θ(j-c), with R_θ(j-c) = 0.8 K/W max *(DATASHEET)* and
P_FET from measured current and V_DS.

**Method B — R_DS(on) as the temperature-sensitive parameter.**
Measure V_DS at known I_D, compute R_DS(on), invert Diagram 9's R_DS(on)–T_j
curve. Requires a low-side sense point and a calibration at known T_j (board
soaked to a known temperature, no power).

Method B is the primary result. Method A is the cross-check.

## 3. Ambient measurement

Thermocouple in the free stream, ≥100 mm upstream of the board, shielded from
radiation. Ambient recorded continuously; all results reported as **rise above
ambient**, not as absolute temperature.

## 4. Controlled airflow condition

**This is the parameter the whole plan turns on. It must be stated, not
described.**

| Item | Requirement |
|---|---|
| Velocity | Measured at the board face with a calibrated anemometer, ±10 % |
| Test points | **6.23 m/s** (case A, at the disc) and **12.46 m/s** (case B, slipstream) |
| Direction | Normal to the board face, matching the installed orientation |
| Distance | Source ≥150 mm from the board, flow developed |
| Uniformity | Mapped at 5 points across the board; spread ≤20 % |
| Record | Velocity, direction, source geometry, temperature — in the test log |

**"Propwash cooled" is not an acceptable description of a test condition.**

## 5. Hover-current test

- Apply hover load: 42 A board / 21 A phase RMS per channel.
- Run to thermal equilibrium — **≥5τ, i.e. ≥4 minutes** (τ ≈ 31–45 s).
- Record all channels at both airflow points.
- **Predicted:** T_j 103.2 °C at h=60, 128.9 °C at h=42.

## 6. 115 A peak test

**Not to be run until §5 passes and duration is bounded by §7.**

- Step from hover to 115 A board current.
- Instrument continuously at ≥10 Hz; T_j is transient, not a settled value.
- Abort immediately if any case temperature exceeds **150 °C** (T_j margin to
  the 175 °C absolute maximum).
- **Predicted sustained:** T_j 132.7 °C at h=60, 169.9 °C at h=42 — both over
  the 125 °C target, which is why duration must be bounded first.

## 7. Peak-duration sweep

**This is the test that resolves `peak_duration_ms`.**

Step from hover to 115 A, hold for t, return to hover, allow full recovery
(≥5τ) between runs.

| t | Rationale |
|--:|---|
| 1 s | ≪ τ; package-level only |
| 5 s | ≪ τ |
| 15 s | ≈ τ/2 |
| 30 s | ≈ τ |
| 60 s | ≈ 2τ |
| 120 s | approaching steady state |

Plot peak T_j against t. **The duration at which T_j crosses 125 °C is the
answer**, and it becomes the system requirement rather than something anyone
invents.

## 8. Repetition-rate sweep

**This resolves `peak_repetition_rate_Hz` / `peak_duty_cycle`.**

Using the largest duration from §7 that stayed under 125 °C, repeat at duty
cycles 0.05, 0.10, 0.25, 0.50. Run ≥10 cycles or ≥10τ, whichever is longer, and
record the **settled envelope**, not the first cycle.

Predicted at h=60: duty ≤0.5 stays under target. **At h=42 nothing passes** —
if the measured airflow lands near case A, this sweep is expected to fail and
that failure is the result.

## 9. Maximum measured case temperature

Report, for every run: max case temperature, its location, ambient, airflow,
derived T_j by both methods, and derived R_θ(j-a).

**R_θ(j-a) = (T_j − T_ambient) / P_FET** is the headline number the model needs.

## 10. Pass/fail criteria

| # | Criterion | Threshold |
|---|---|---|
| 1 | Hover, developed slipstream, steady state | T_j ≤ **125 °C** |
| 2 | Peak at the agreed duration and duty | T_j ≤ **125 °C** |
| 3 | Any condition | T_j < **175 °C** — a hard abort, not a pass |
| 4 | Method A vs Method B | agree within **10 K** |
| 5 | Measured R_θ(j-a) vs model | within **±25 %**, or the model is wrong and is corrected |
| 6 | No thermal runaway | dT/dt → 0 within 5τ |
| 7 | Capacitor case | within its own rated temperature |
| 8 | Current-sense drift | within its accuracy budget across the range |

**Any T_j between 125 °C and 175 °C is a FAIL against the design target.**
175 °C is the absolute maximum and is never a pass condition.

---

## Test-condition classes — kept distinct

| Class | Condition | Purpose | Full power allowed? |
|---|---|---|---|
| **C1 — bench, forced air** | Controlled anemometer-verified flow, §4 | Primary characterisation, §5–§9 | **Yes**, with §4 airflow verified and §10.3 abort armed |
| **C2 — installed aircraft** | Rotors turning, board in final mounting | Confirms the real boundary condition and P1 vs P2 vs P3 placement | **Yes**, tethered, after C1 passes |
| **C3 — still air** | No forced airflow | Leakage, quiescent, power-up only | **NO. Prohibited above quiescent.** |

**C3 rationale:** predicted still-air junction temperature at peak is **393 °C**.
Sustained full power in still air destroys the parts. Bench testing without
verified airflow is a safety hazard, not a conservative test.

C2 is the only test that measures the **real** boundary condition. C1 predicts
it; C2 decides it. If C2 disagrees with C1 at the same nominal velocity, C2
wins and the placement study (thermal-analysis §5) is re-run against it.

---

## Outputs required before this plan can close

| Output | Feeds |
|---|---|
| Measured R_θ(j-a) at both airflows | baseline `thermal.requires_measurement` |
| T_j vs peak duration curve | `peak_duration_ms` |
| T_j vs duty cycle at the chosen duration | `peak_repetition_rate_Hz`, `peak_duty_cycle` |
| Verified airflow spec (velocity, direction, geometry) | `airflow_boundary_condition` |
| Placement case P1/P2/P3 identified on the real aircraft | thermal-analysis §5 |

Until those exist, `thermal_validation_status` stays **OPEN**.
