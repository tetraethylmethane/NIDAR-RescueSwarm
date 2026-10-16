# CAD brief — RescueSwarm airframe

3 identical custom quadrotors. No frame kits (rule 8.2).
If this disagrees with [`docs/sizing/`](../../docs/sizing/) or [`sourced_bom.py`](../bom/sourced_bom.py), they win.

## Numbers

| | |
|:--|:--|
| Structure mass (frame, arms, gear, hardware) | **≤ 1495 g** |
| MTOW | 6.8–7.1 kg |
| Wheelbase | **761 mm** diagonal (props up to 20 in, 18 in fitted, 30 mm tip clearance) |
| Footprint | **≤ 1046 mm** square, unfolded |
| Payload | 4 kits, each 200 × 100 × 50 mm, 200 g |
| Battery | GenX 6S 16 Ah LiPo, about 2 kg. Size unknown, so keep the bay parametric (placeholder 200 × 75 × 65 mm). |
| Parachute | 300 g, top-centre |

Don't use the `bay_*` variables. They are for the old pack.

## Parts to fit

CF tube OD25 × ID23 · CF sheet 300 × 200 × 2 mm · Tarot TL9602 motor mounts · Tarot 5008 motors, 18 in props · T-bolt clamps 23–25 mm · F450 skid · Kakute H7 + 4-in-1 ESC (30.5 mm stack, soft-mounted) · Pi 5 + AI HAT+ + cooler · Arducam HQ camera (nadir) · GenX F9P Air GNSS · TFmini-S (down) · BL-M8812EU2 + fan · ELRS RX, E22 radio · 4 × MG90S release servos · PETG-CF printed parts.

## Must

1. Payload release locks mechanically and holds without servo power.
2. Battery tray loads from the side, with a hard stop and a latch. Pack CG sits in the rotor plane, not hung low.
3. Camera, FC and GNSS sit on **one rigid core**. Folds, if any, go outboard of it and take ≤ 22 s per aircraft to deploy, lock and verify.
4. Camera mount moves **≤ 0.21 mm over 80 mm** for life. Use dowels or bonding, not bolt friction. No aluminium bracket.
5. The camera bracket shares no structure with the compute bay.
6. Add a measurable datum between the GNSS and the camera face.
7. GNSS needs a clear sky view, stays outside the parachute cone, and sits away from power wiring and the ESC.
8. Parachute cone is clear of the props and antennas. Check it with a dummy cone solid in CAD.
9. Fan runs from power-on.
10. Captive fasteners, keyed connectors, nothing that can be assembled wrong.

## Analysis

The figures below are hand estimates. Your analysis replaces them. **Material values are conservative placeholders; get supplier datasheets.**

### Design loads (limit loads; ultimate = limit × FoS)

| Load | Value | Basis |
|:--|:--|:--|
| Weight | 70 N (7.1 kg) | Worst-case MTOW |
| Max thrust per motor | **35 N** | T/W 2.0 at 7.1 kg |
| Motor reaction torque | 1.0 N·m | About 500 W shaft at about 6000 rpm |
| Gyroscopic moment per prop | 1.5 N·m | 18 in prop, 120 °/s body rate |
| Wind | 15 m/s gust, about 11 N horizontal on the body | SYS-37 (10 m/s sustained) + margin |
| Normal landing | 0.5 m/s | ArduPilot LAND_SPEED |
| Hard landing | **2 m/s**, one skid first (60 % on one side) | |
| Parachute landing | about 5 m/s (confirm from chute spec) | Gear may break; battery, sensor core and pack must survive |
| Parachute opening shock | 5 × weight = 350 N at the mount | |
| Handling | Lift by one arm, 2 × weight | |

### Load cases for FEA

| LC | Case |
|:--|:--|
| 1 | Hover, 1 g |
| 2 | All motors at max thrust + reaction torque |
| 3 | One motor at max, the opposite one at idle (asymmetric manoeuvre) + gyroscopic moment |
| 4 | LC2 + 15 m/s gust |
| 5 | Hard landing, level and skid-first |
| 6 | Parachute opening shock |
| 7 | Handling |

### Materials (placeholders)

| Material | E | Allowable | Note |
|:--|:--|:--|:--|
| 3K CF tube | 60 GPa | 300 MPa | Shear modulus G about 4.5 GPa |
| 3K CF plate, 2 mm | 45 GPa | 250 MPa | Woven, in-plane |
| Al 6061-T6 (Tarot mounts) | 69 GPa | 276 MPa yield | Fatigue about 95 MPa |
| PETG-CF, printed | 3.5 GPa | 35 MPa in-plane, **15 MPa across layers** | Softens near 80 °C. Check a 60 °C sun soak. |
| SS304 A2-70 fasteners | — | 450 MPa yield | |

Composite failure: max-stress or Tsai-Wu, with a 0.8 knockdown for impact damage. **No printed part in a primary load path** (arm–plate, motor mount, gear root, parachute mount).

### Required factors of safety

| | FoS |
|:--|:--|
| Carbon fibre | **2.0** on ultimate |
| Metals | 1.5 on yield |
| Printed parts | **3.0** |
| Fasteners and joints | 2.0 |
| Buckling | 3.0 |

### Analyses and pass criteria

| Analysis | What to do | Pass |
|:--|:--|:--|
| **Mass** | Mass every part with real densities, and add fasteners, wiring and adhesive | Structure **≤ 1495 g**, MTOW ≤ 7.1 kg, fleet ≤ 24 kg |
| **CG** | Report CG fully loaded, after each kit drop, and empty | Lateral ≤ 10 mm from the rotor centroid (`cad_check` fails at 25 mm). Shift across the 4 drops ≤ 4 mm. Pack CG in the rotor plane. |
| **Static FEA** | LC1–7, with a mesh convergence study (< 5 % change in peak stress) | All FoS met |
| **Stress / strain** | Von Mises for metals, ply stresses for CF, layer direction for printed parts | Below allowable ÷ FoS |
| **Deformation** | LC2 | Arm tip ≤ 3 mm, motor tilt **≤ 0.5°** (estimate: 1.5 mm, 0.37°) |
| **Arm bending** | Cantilever, 35 N at 345 mm, giving 12 N·m at the root | σ ≈ 28 MPa, FoS ≈ 10 (estimate). Bending is not the driver. |
| **Arm torsion** | Reaction torque + gyroscopic moment = 2.5 N·m | Twist ≤ 1° (estimate: about 1.0°, marginal) |
| **Buckling** | Gear legs (LC5), arm wall under the clamp, thin plate regions | Linear buckling FoS ≥ 3 |
| **Material failure** | Composite criterion above, sun-soaked PETG-CF | Failure index ≤ 1/FoS |
| **Joints / fasteners** | Arm clamps: slip torque and pull-out. Bolts: shear, bearing in 2 mm CF, edge distance. | Clamp holds 5 N·m without slip and has an **anti-rotation key or pin**. Tube has an insert under each clamp so it isn't crushed. CF edge distance ≥ 3d. Washers, Loctite 243 or nyloc. |
| **Modal** | First 6 modes of the full aircraft with lumped motor, battery and payload masses | Every mode ≥ 15 % away from the hover 1P and 2P rotor frequencies. Estimates: arm bending about 48 Hz; 1P 60–75 Hz, 2P 120–150 Hz. **Get rpm from the thrust stand.** |
| **Vibration / resonance** | Harmonic response at 1P and 2P. Check FC soft-mount isolation. | Flight log: IMU vibration < 30 m/s², zero clipping (ArduPilot) |
| **Fatigue** | 10⁷ cycles (about 65 Hz × 50 flight hours) + 500 landings | Alternating stress: CF ≤ 30 % of UTS, Al ≤ 95 MPa, no cyclic load on printed parts |
| **Wind** | LC4 for structure. For control: tilt angle at 10 m/s. | FoS met. Tilt leaves thrust headroom (about 4° estimated). |
| **Thrust / torque** | LC2 and LC3 at the motor mount, arm and clamp | Covered by the rows above |
| **Landing impact** | LC5. Load factor n = v²/(2·g·stroke) + 1, so 2 m/s on 20 mm of stroke is about 11 g and needs about 50 mm of stroke to stay near 5 g. Parachute case: protect the core. | No damage at 2 m/s. Battery and sensor core intact at 5 m/s. |

⚠ **The F450 skid is built for an aircraft of about 2 kg.** Run LC5 on it first. It will probably need replacing.

### Tests that confirm the analysis

- **Static arm test:** hang 35 N on the arm. Measure tip deflection, and check it against the FEA within 20 %.
- **Tap test:** measure the arm's natural frequency and compare it with the modal result.
- **Thrust stand:** measure rpm and record the 1P and 2P bands.
- **Drop test:** 2 m/s equals a drop from 0.2 m, with the aircraft at full mass.
- **First flights:** check the IMU vibration log.

Deliver one short report per analysis, covering model, boundary conditions, loads, result, FoS and pass/fail.

## Tools

```
python tools/cad/sw_build_skeleton.py      # driven variables, then Save As your own file
python tools/cad/cad_check.py your.SLDASM  # checks mass, CG, footprint, clearance
```
