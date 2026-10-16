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

## Tools

```
python tools/cad/sw_build_skeleton.py      # driven variables, then Save As your own file
python tools/cad/cad_check.py your.SLDASM  # checks mass, CG, footprint, clearance
```
