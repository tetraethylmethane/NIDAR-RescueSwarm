# CAD brief — RescueSwarm airframe

For the mechanical team. Binding list:
[`frame-design-constraints.md`](../../docs/frame-design-constraints.md). Numbers:
[`docs/sizing/`](../../docs/sizing/) and [`sourced_bom.py`](../bom/sourced_bom.py).
**If this brief disagrees with them, they win.**

---

## 1. The job

Three identical quadrotors. Each one autonomously searches part of a flood
plain, geotags survivors and drops up to four 200 g medical kits. The team has
five minutes to go from boxes to airborne.

**Custom frame, no kit.** Rule 8.2 bans ready-to-fly airframes, and Design
Review item 3 scores our own design (indigenisation). Bought components are fine.

## 2. Fixed numbers

| | Value | Note |
|:--|:--|:--|
| Structure budget | **1495 g** | Frame, arms, landing gear and hardware. Everything structural. |
| MTOW | **6.8–7.1 kg** | With the 16 Ah LiPo. The model's 6.36 kg is the old Li-ion point. |
| Fleet limit | **25 kg**, all 3 weighed together | About 21 kg expected |
| Wheelbase | **761 mm** diagonal | Arms take **16–20 in** props (18 in now) with 30 mm tip clearance |
| Footprint | **≤ 1046 mm** square, unfolded | Launch box is 12 ft (3.66 m). No part may leave it. |
| Payload | **4 kits**, each 200 × 100 × 50 mm, 200 g | Fixed by rule |
| Battery | **GenX 6S 16 Ah HV LiPo**, 1880–2211 g, AS150 | **Dimensions unpublished. Measure on arrival.** |
| Arm root moment | 10.7 N·m at T/W 2 | Bending isn't the driver. Clamps and vibration fatigue are. |

> ⚠ **Battery bay:** the `bay_*` variables in
> [`rescueswarm-frame-equations.txt`](rescueswarm-frame-equations.txt) still
> describe the old 6S3P Li-ion pack. **Don't use them.** Use a placeholder of
> about 200 × 75 × 65 mm (typical 6S 16 Ah) as a named variable until the real
> pack is measured.

## 3. Bought parts the frame must take

| Part | Interface |
|:--|:--|
| Arms | 3K CF tube **OD25 × ID23**, cut from 1000 mm |
| Centre plates | 3K CF sheet **300 × 200 × 2 mm**, one sheet per aircraft (top + bottom) |
| Motor mounts | **Tarot TL9602**, 25 mm tube clamp |
| Motors / props | Tarot 5008 340 KV / 1855 CF |
| Arm clamps | SS304 T-bolt clamps, 23–25 mm |
| Landing gear | F450/F550 skid + 5 mm torsion springs |
| FC + ESC | Kakute H7 + Hobbywing 4-in-1, **30.5 mm stack**, soft-mounted |
| Compute | Raspberry Pi 5 + AI HAT+ + active cooler |
| Camera | Arducam 12.3 MP HQ + 6 mm CS lens, **nadir** |
| GNSS | **GenX F9P Air**: one module with an integrated compass |
| Rangefinder | TFmini-S, facing down, clear view |
| Video link | BL-M8812EU2 + **heatsink and fan**, 2 × 5 GHz dipoles |
| Radios | ELRS RX24T, E22-900 |
| Release | 4 × MG90S servos |
| Printed parts | PETG-CF |

Use vendor drawings for hole patterns.

## 4. Decided. Don't reopen these.

1. **Quadrotor, 4 arms.**
2. **Folding is optional.** If you fold, deploy + lock + verify must take **≤ 22 s per aircraft**. Use quick-release clamps and a lock indicator visible from 1 m, not bolts. **Folds go only outboard of the sensor core.**
3. **Battery tray:** side-loading, captive latch, hard stop. The position must be repeatable, not adjustable, because 10 mm of error means about 1.2 % permanent trim.
4. **Pack CG in the rotor plane.** Don't sling it low. If the pack needs more room, grow the tray wider or longer, not deeper.
5. **Magazine:** 4 kits centred on the CG, laid out for packaging and a clear drop path. Don't optimise it for CG.
6. **Payload release:** a positive mechanical lock that holds without servo power. A brownout must not drop a kit.
7. **Parachute:** top-centre with a clear deployment cone, 300 g budget. It has to be designed in. A retrofit fouls the props.
8. **Cooling fan** on the main bus, running from power-on, not gated on arming.
9. **Setup-proof:** captive fasteners, keyed connectors, and folds that can't be assembled wrong.

## 5. Accuracy rules. These earn the points.

Geotag accuracy gates 450 of the 600 flight points, and three of its error terms are mechanical.

- **One rigid sensor core.** Camera, FC/IMU and the GNSS module go on a single stiff part. No fold or soft joint between them.
- **Camera mount: ≤ 0.21 mm differential movement over 80 mm, for the airframe's life.** An M3 clearance hole alone has 0.2–0.4 mm of slop, so use **dowel pins or a bonded joint**, not bolt friction. Use a CF bracket, not aluminium, which bends like a bimetallic strip with temperature.
- **Don't share structure** between the camera bracket and the compute bay. Compute heat rotates the camera.
- **Lever-arm datum:** a feature callipers can reach between the GNSS module and the camera face. It's one dimension on the drawing.
- **GNSS placement:** clear sky view, outside the parachute cone, and away from carbon plates, power leads and the ESC because of the onboard compass.

## 6. Order of work

1. Payload magazine and release (fixed by rule, needs nothing else).
2. Rigid sensor core.
3. Arms and motor mounts, driven by `wheelbase_diag`. Decide fold or fixed.
4. Battery tray, parametric until the pack is measured.
5. Compute bay and airflow, thermally separate from the sensor core.
6. Parachute mount, with its cone checked as a swept volume against the GNSS and props.
7. Landing gear, clear of the magazine and the drop path.

## 7. Tools

```
python tools/cad/sw_build_skeleton.py      # skeleton part with 25 driven variables
python tools/cad/cad_check.py your.SLDASM  # asserts the model; exit 1 on failure
```

- **Save As your own filename immediately.** The generated skeleton is overwritten on every run.
- Drive dimensions by expression (`= "wheelbase_diag" / 2`). Never type 761.
- `cad_check` checks variables, mass (±10 %), CG offset (fails at > 25 mm), footprint, launch box, interference and tip clearance. It doesn't yet check the parachute cone, so model the cone as a dummy solid and the interference check will catch it.
- `cad_check` still asserts the old Li-ion MTOW and bay. Expect those two to be off until the model is updated.

## 8. Open. These don't block CAD.

| Question | Meanwhile |
|:--|:--|
| GenX pack real mass and size | Keep the bay parametric. Weigh and measure on arrival. |
| Motor-out tolerance required? | Build the quad. A hex would reuse everything except frame and propulsion. |
| Fold or fixed arms? | Depends on transport to the venue. The launch box doesn't need folding. |
| Search altitude | Affects the camera choice, not the mount. |
