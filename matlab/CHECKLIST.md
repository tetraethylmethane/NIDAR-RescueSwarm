# RescueSwarm — analysis checklist

Status of every figure, calculation, verification and simulation.
Honest state, not aspiration. **Last run: 2026-08-27.**

Legend: **done** works and is checked · **partial** works, gap noted ·
**todo** not started · **wired** appears in the proposal PDF

---

## 1. Verification

The Python model asserts each derivation against *its own* result — same
expression both sides, so it catches an inconsistent edit but not a wrong
derivation. MATLAB re-derives independently from primitives only.

| # | Check | Tool | Status |
|---|---|---|---|
| V1 | Proposal claims vs models — 46 checks | Python | **done** |
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
| C8 | Geolocation RSS error budget | Python | V1 | **done** |
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
| F1 | `fig-detect` | Target area vs altitude/downsample vs COCO | MATLAB | **done** — not wired |
| F2 | `fig-looks` | Looks vs rate; inference cost of 3.06 Hz | MATLAB | **done** — not wired |
| F3 | `fig-motor` | Reserve stack; motor operating point | MATLAB | **done** — not wired |
| F4 | `fig-sag` | Pack voltage over the mission | MATLAB | **wired** |
| F5 | `fig-geotag` | Error by fix quality; fusion saturation | matplotlib | **wired** |
| F6 | `fig-mass` | Mass budget | matplotlib | **wired** |
| F7 | `fig-launch` | Launch separation | matplotlib | **wired** |
| F8 | `fig-pad` | Pad containment | matplotlib | **wired** |
| F9 | `fig-sweep` | Sweep pattern and return | matplotlib | **wired** |
| F10 | `fig-options` | — | matplotlib | **todo** — orphaned, delete or use |
| F11 | `fig-subsystem` | — | matplotlib | **todo** — orphaned (was for the deleted §VIII) |
| F12 | `fig-funding` | — | matplotlib | **todo** — orphaned (funding is out of the paper) |

**Open:** F1–F4 exist but no `\begin{figure}` block references them. F5–F9 are
still matplotlib; porting them completes the move to one toolchain.

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

---

## 5. What is blocking what

| Blocked item | Waiting on |
|---|---|
| S1 → evidence | P2 thrust-stand DC-IR measurement |
| S3 | Nothing — can be built now |
| C14 / S2 | Nothing — can be built now |
| Detection recall | SeaDronesSee download + GPU |
| F1–F4 in the paper | One editing pass, ~4 figure blocks |
| BOM totals | Teravolt quotation received; four phases now exceed the ₹30 k cap |

---

## 6. Next three, in order

1. **Wire F1–F4 into the proposal.** They exist and are verified; the paper's
   central claim still has no figure in it.
2. **S3, motor–propeller matching.** Turns P2 from "measure a number" into
   "confirm or refute a prediction", which is a far stronger test.
3. **S2/C14, thermal.** The 115 A transient is currently defended by an I²t
   argument that has not been tested.
