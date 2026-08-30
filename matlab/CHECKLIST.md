# RescueSwarm — analysis checklist

Status of every figure, calculation, verification and simulation.
Honest state, not aspiration. **Last run: 2026-08-30.**

Legend: **done** works and is checked · **partial** works, gap noted ·
**todo** not started · **wired** appears in the proposal PDF

---

## 1. Verification

The Python model asserts each derivation against *its own* result — same
expression both sides, so it catches an inconsistent edit but not a wrong
derivation. MATLAB re-derives independently from primitives only.

| # | Check | Tool | Status |
|---|---|---|---|
| V1 | Proposal claims vs models — 48 checks | Python | **done** |
| V2 | Independent re-derivation — 28 checks | MATLAB | **done** |
| V3 | Mass statement closes to MTOW | both | **done** |
| V4 | Generated §V asserts against model | Python | **done** |
| V5 | LaTeX mangling guards (lost backslash, TAB+name) | Python | **done** |
| V6 | Tile count consistent across prose and tiling | Python | **done** |
| V7 | Budget reconciles: BOM → phases → total | Python | **done** |
| V8 | Figure values vs model | — | **todo** — no guard yet; `fig-motor` once carried a 9 Wh error found only by eye |

**V2 covers:** disk area · hover shaft/electrical power · hover and peak
current · thrust totals · coupled mass fixed point · cell count · pack energy
(two routes) · usable energy · reserve requirement · hover endurance · sensor
dimensions · HFOV/VFOV · GSD · swath · looks at 2 Hz · rate for 12 looks ·
mission duration and energy · mass closure.

**Run:** `python matlab/export_model.py && matlab -batch "cd matlab; run_all('verify')"`

---

## 2. Calculations

| # | Quantity | Where | Verified | Status |
|---|---|---|---|---|
| C1 | Momentum-theory hover power | Python + MATLAB | V2 | **done** |
| C2 | Coupled mass–energy fixed point | Python + MATLAB | V2 | **done** |
| C3 | Reserve policy (nominal + re-sweep + loiter) | Python + MATLAB | V2 | **done** |
| C4 | Pack sizing, C-rate, per-cell current | Python + MATLAB | V2 | **done** |
| C5 | Optics: GSD, FOV, swath, hyperfocal | Python + MATLAB | V2 | **done** |
| C6 | Tiling and inference load | Python | V6 | **done** |
| C7 | Temporal sampling / looks per pass | Python + MATLAB | V2 | **done** |
| C8 | Geolocation RSS error budget | Python + MATLAB | V1, S4 | **done** |
| C9 | Payload ballistics with drag | Python | V1 | **done** |
| C10 | Structural bending in the arm | Python | V1 | **done** |
| C11 | Link budget (5.8 GHz, 2.4 GHz) | Python | V1 | **done** |
| C12 | Motor operating point vs datasheet | MATLAB | V2 | **done** |
| C13 | Nickel/copper interconnect sizing | ad hoc | — | **partial** — computed in conversation, not in any model |
| C14 | Thermal rise in cells and interconnects | — | — | **todo** — the I²t argument is asserted, not tested |

---

## 3. Figures

| # | File | Shows | Tool | Status |
|---|---|---|---|---|
| F1 | `fig-detect` | Target area vs altitude/downsample vs COCO | MATLAB | **wired** |
| F2 | `fig-looks` | Looks vs rate; inference cost of 3.06 Hz | MATLAB | **wired** |
| F3 | `fig-motor` | Reserve stack; motor operating point | MATLAB | **wired** |
| F4 | `fig-sag` | Pack voltage over the mission | MATLAB | **wired** |
| F5 | `fig-geotag` | Error by fix quality; fusion saturation | matplotlib | **wired** |
| F6 | `fig-mass` | Mass budget | matplotlib | **wired** |
| F7 | `fig-launch` | Launch separation | matplotlib | **wired** |
| F8 | `fig-pad` | Pad containment | matplotlib | **wired** |
| F9 | `fig-sweep` | Sweep pattern and return | matplotlib | **wired** |
| F10 | `fig-options` | — | matplotlib | **todo** — orphaned, delete or use |
| F11 | `fig-subsystem` | — | matplotlib | **todo** — orphaned (was for the deleted §VIII) |
| F12 | `fig-funding` | — | matplotlib | **todo** — orphaned (funding is out of the paper) |
| F13 | `fig-geobudget` | Variance share; error CDF by receiver class | MATLAB | **wired** |

**Open:** F5–F9 are still matplotlib. Porting them completes the move to one
toolchain; nothing else depends on it.

**Run:** `matlab -batch "cd matlab; run_all('figs')"`

---

## 4. Simulations

| # | Simulation | Question it answers | Toolbox | Status |
|---|---|---|---|---|
| S1 | Pack voltage sag | Where does the failsafe threshold go? | base | **done** |
| S2 | Thermal, cells + nickel | Does 0.2 mm nickel survive 115 A? | PDE | **todo** |
| S3 | Motor–propeller matching | Predict thrust before P2 measures it | Motor Control | **todo** |
| S4 | Geolocation Monte Carlo | What does the receiver class actually buy? | base | **done** |
| S5 | Coverage path timing | Mission time over real region shapes | base | **todo** — Python SITL covers part of this |

### S1 result

```
minimum pack voltage   17.05 V at t = 432 s
failsafe floor         18.00 V
margin                 -0.95 V
SOC at that moment     64 %
sag at the gust        5.82 V   (static model assumes 4.60)
```

The aircraft crosses its own low-voltage floor during a legitimate gust
recovery at two-thirds charge — long before the 80 % DoD limit the reserve
policy is built around. A failsafe on instantaneous pack volts would command
return-to-land mid-search on a healthy pack.

**Caveat:** R0 is calibrated so static sag matches the proposal's 4.6 V
assumption; R1/C1/R2/C2 are typical high-drain 21700 values, not P45B-specific.
The shape is trustworthy; the magnitude inherits that assumption. **P2 replaces
R0 with a measured DC-IR — that is when this becomes evidence.**

### S4 result

```
receiver                 RSS    CEP50   CEP95
RTK fixed               0.88 m  0.73 m  1.53 m
SBAS                    1.07 m  0.89 m  1.85 m
standalone multi-band   1.33 m  1.11 m  2.31 m
```

RTK buys **0.16 m of CEP50** over SBAS, on a budget where unmodelled error and
target centroid carry 95 % of the variance. Every class clears the 5 m delivery
requirement with over 3× margin. §IV-D now presents this as a trade rather than
a requirement — RTK is retained for the *relative* geometry P7–P8 need to
measure against, not because the mission budget fails without it.

**The first run was wrong and said so.** It sampled each quoted term as a
per-axis sigma when the document's convention is a two-axis RSS, inflating
everything by √2 and returning CEP50 = 1.04 m against SYS-12's own 0.75 m. The
disagreement with SYS-12 is what caught it. The script now asserts
CEP50 = 0.8326 × RSS against the analytic Rayleigh result and errors rather than
publishing if they diverge.

---

## 5. What is blocking what

| Blocked item | Waiting on |
|---|---|
| S1 → evidence | P2 thrust-stand DC-IR measurement |
| S3 | Nothing — can be built now |
| C14 / S2 | Nothing — can be built now |
| Detection recall | SeaDronesSee download + GPU |
| Receiver decision | Teravolt quotation, and whether funding supports RTK |
| Phase structure | Seven phases now exceed the ₹30 k cap after the Pi 5 reprice |

---

## 6. Next three, in order

1. **S3, motor–propeller matching.** Turns P2 from "measure a number" into
   "confirm or refute a prediction", which is a far stronger test — and it can
   be built before the motor arrives.
2. **S2/C14, thermal.** The 115 A transient is currently defended by an I²t
   argument that has not been tested.
3. **V8, a guard on figure values.** `fig-motor` once carried a 9 Wh error that
   only an eye caught, and `fig-geobudget` nearly shipped a √2 one. Figures are
   the last part of the pipeline with no assertion behind them.
