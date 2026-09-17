# DrikrAIO — 6-Layer Stackup Proposal

**NOMINAL PROPOSAL. NOT MANUFACTURER-APPROVED.**

Every dielectric thickness below is a nominal value for a standard 6-layer
process. **The fabricator must substitute their own laminate stack and
recalculate impedance from it.** Nothing here is a supplier-confirmed
construction.

No routing performed. No placement changed. Board remains 50 × 50 mm.

---

## 1. Proposed 6-layer stackup

Finished thickness target **1.60 mm ± 10 %**. Surface finish **ENIG**.

| # | Layer | Purpose | Copper | Dielectric below | Nominal | Role |
|---|---|---|--:|---|--:|---|
| L1 | F.Cu | Control side — MCU, IMU, RF, OSD, connectors | **2 oz (70 µm)** ⚠ | prepreg | **0.10 mm** ⚠ | RF microstrip reference gap |
| L2 | In1.Cu | **Solid GND** — reference for L1 | 1 oz (35 µm) | core | **0.51 mm** ⚠ | |
| L3 | In2.Cu | **VBAT / power distribution** | 1 oz (35 µm) | prepreg | **0.20 mm** ⚠ | |
| L4 | In3.Cu | **VBAT / phase distribution** | 1 oz (35 µm) | core | **0.51 mm** ⚠ | |
| L5 | In4.Cu | **Solid GND** — reference for L6 switching | 1 oz (35 µm) | prepreg | **0.10 mm** ⚠ | tight commutation return |
| L6 | B.Cu | Power side — MOSFETs, battery entry, phases | **2 oz (70 µm)** | — | — | |

⚠ = requires fabricator confirmation.

Copper total 280 µm. Dielectric total 1.42 mm. Nominal sum **1.70 mm** — above
the 1.60 mm target, so **the fabricator must redistribute dielectrics to hit
1.60 mm**, most likely by thinning the L2–L3 and L4–L5 cores. (The board file
currently carries 1.67 mm on 0.545 mm cores; both that and this proposal need
the same reconciliation.) The two 0.10 mm
prepregs at L1–L2 and L5–L6 are the values that must be **preserved**; they are
what the RF reference and the commutation loop depend on.

### Why the layer order is this way

- **L2 solid ground directly under L1** gives every top-side signal a
  continuous reference 0.10 mm away, and makes 50 Ω microstrip achievable.
- **L5 solid ground directly under L6** puts an unbroken return plane 0.10 mm
  beneath the MOSFET switching loops. This is the single most important
  stackup choice for the 8.72 nH budget — loop area is minimised vertically,
  not laterally.
- **L3 and L4 carry VBAT between the two ground planes**, so the power
  distribution is shielded on both sides and the planes stay whole.

## 2. Power / ground layer strategy

**Two solid ground planes, L2 and L5. Neither is split.**

Separation between noisy motor return and quiet avionics return is by
**placement and by which plane the return rides**, not by cutting the copper. A
split under a switching loop forces return current around the gap and adds
exactly the inductance the design is trying to remove.

| Return | Rides on | Because |
|---|---|---|
| MOSFET commutation | L5, directly under L6 | shortest possible loop |
| Battery / bulk | L5 and L6 pour | high current, power side |
| MCU, OSD, blackbox | L2, directly under L1 | continuous reference |
| RF | L2 only | §3 |
| Shunt Kelvin sense | L2, over unbroken copper | no plane discontinuity under the differential pair |

L3 and L4 carry VBAT and phase copper. Where they are not power, they are
**GND fill stitched to L2/L5**, never left floating.

## 3. RF and reference-plane strategy

The SX1281 chain sits on L1 in the top-right corner. Its reference is **L2, at
0.10 mm nominal**.

**Impedance targets the fabricator must calculate from their own laminate:**

| Net class | Target | Geometry |
|---|--:|---|
| RF antenna feed | **50 Ω single-ended** | L1 microstrip over L2 |
| USB D+/D− | **90 Ω differential** | L1 over L2 |

**No trace width is stated here.** Width depends on the fabricator's actual
dielectric thickness, resin content and copper weight, none of which are known.
Supplying a width would be inventing an impedance. The fabricator returns the
widths; the design adopts them.

Requirements that are ours to hold, not theirs:

1. **L2 must be unbroken beneath the entire RF section.** No via antipads, no
   plane cuts, no L3/L4 power copper crossing under the feedline.
2. **No switching node on any layer beneath the RF block** — this includes L6
   directly opposite.
3. Antenna keepout preserved on all six layers.
4. Ground via fence around the RF section stitched L1→L2.

> **Note:** εr 4.5 in the current board file is a placeholder. Real FR4 is
> typically 4.2–4.6 and varies with resin content and frequency. It must not be
> used to compute a final trace width.

## 4. High-current multilayer strategy

**A trace width alone does not make the 115 A path safe, and no width is
claimed to.**

VBAT and GND distribute across **four layers** — L1, L3, L4, L6:

| Contribution | Copper |
|---|--:|
| L1 + L6 at 2 oz, 20 mm effective | 2.80 mm² |
| L3 + L4 at 1 oz, 20 mm effective | 1.40 mm² |
| **Total** | **4.20 mm²** |

Single-layer 2 oz outer alone would be 1.40 mm² and heats at 34 °C/s at 115 A.
Across four layers the same bus is 4.20 mm² and the adiabatic rate falls by the
square of the area ratio.

**Via transitions are the bottleneck, not the copper.** From the earlier
analysis: 0.3 mm drill at 25 µm plating is 1.08 mΩ per via, ≈1.5 A continuous.

| Path | Minimum vias | Requirement |
|---|--:|---|
| VBAT L6↔L3↔L4↔L1 | **≥40 per transition** | distributed along the bus, never in a row |
| Motor phase | **≥16 per phase** | |
| FET thermal pad | **≥9 per pad** | into L5, then spread |

**Current sharing must not be assumed equal.** L1/L6 are 2 oz and L3/L4 are
1 oz, so an ideally stitched bus splits roughly 33 % per outer layer and 17 %
per inner. Sparse or clustered vias crowd current into the outer layers
instead. Sharing must be checked against the final via geometry.

**No post-fabrication bus bars, soldered copper reinforcement or hand-added
wire.** The stackup carries the current or the design changes.

## 5. Manufacturing assumptions requiring fab confirmation

| # | Item | Nominal | Must confirm |
|---|---|---|---|
| 1 | All dielectric thicknesses | as tabled | actual laminate stack |
| 2 | Finished thickness | 1.60 mm | achievable with 2 oz outer |
| 3 | εr | 4.5 placeholder | actual, at frequency |
| 4 | 50 Ω / 90 Ω widths | **not stated** | fab calculates and returns |
| 5 | **2 oz outer minimum feature** | 0.20 mm assumed | **see §6 — parts sit exactly on this** |
| 6 | Via 0.35 mm / 0.20 mm drill, 25 µm plating | | plating thickness guaranteed? |
| 7 | ENIG over 2 oz | | |
| 8 | Solder mask sliver between 0.4 mm pitch pads on 2 oz | | may be unachievable |
| 9 | Asymmetric copper warpage | if §6 option B adopted | 50 × 50 mm, low risk but confirm |
| 10 | Thermal relief vs solid connection on power pads | solid preferred | assembly implications |

## 6. Stackup conflicts

### 6.1 — BLOCKING: 2 oz outer copper vs 0.4 mm pitch QFN

The requirement is 2 oz on **both** outer layers. The board carries fine-pitch
parts on **both** outer layers:

| Side | Part | Package | Smallest pad |
|---|---|---|--:|
| **B.Cu (2 oz, power)** | AT32F421G8U7 ×4 | QFN-28, 0.4 mm pitch | **0.200 mm** |
| F.Cu | RP2354A | QFN-60, 0.4 mm pitch | **0.200 mm** |
| F.Cu | ESP32-C3 | QFN-32, 0.5 mm pitch | 0.250 mm |
| both | 0201 passives | — | 0.180 mm gap |

**These land at exactly 0.200 mm — precisely on the assumed 2 oz limit, with
zero margin.** `verify_stackup.py` passes them on a strict `<` test and that
pass is not reassurance: a feature equal to the stated capability has no
tolerance budget left for etch variation. 2 oz etches with a wide taper, and
typical low-cost capability is 0.15–0.20 mm at 1 oz against 0.20–0.25 mm at
2 oz. Solder-mask slivers between 0.4 mm pitch pads on 2 oz are a further
problem, and the mask is usually what fails first.

This is why item 5 in §5 asks the fabricator to confirm the number rather than
assume 0.20 mm is available.

**Asymmetric copper does not fix this**, because the four ESC channel MCUs are
on the 2 oz power side, beside the MOSFETs they drive — where they must stay
for gate-drive integrity.

Three ways out, and this is a decision, not a fix:

| Option | Construction | Effect |
|---|---|---|
| **A** | Keep 2 oz outer, require fab to hold 0.20 mm | Cost and yield risk; may be refused |
| **B** ★ | **1 oz outer / 2 oz inner** | Copper total rises 280→350 µm. Fine pitch fine on both sides. Inner spreading improves. **Changes a frozen requirement.** |
| **C** | Move ESC MCUs to F.Cu | Breaks gate-drive proximity. Not recommended. |

**Option B is recommended on the numbers** — more total copper, better inner
spreading, and it removes the fine-pitch conflict entirely. It **contradicts the
frozen `outer_copper_oz: 2`**, so it is raised here rather than adopted.

### 6.2 — BLOCKING: three unmanufacturable footprints

| Ref | Part | Smallest copper pad |
|---|---|--:|
| U403 | TLV7031DPWR (OSD comparator) | **0.005 mm** |
| U402 | SN74LVC1G3157DTBR (OSD pixel switch) | **0.010 mm** |
| U703 | TLV75533PDQNR (RF LDO) | **0.010 mm** |

5–10 µm pads are unbuildable at **any** copper weight. These are footprint
defects inherited from the donor libraries, independent of the stackup, and
they block fabrication regardless of which option in §6.1 is chosen.

### 6.3 — Thickness arithmetic

Nominal dielectrics sum to 1.70 mm against a 1.60 mm target. Fab must
redistribute while **preserving the two 0.10 mm prepregs** at L1–L2 and L5–L6.

### 6.4 — Impedance not declared in the board file

`dielectric_constraints` is currently `no`. It must be set, with the two
impedance classes of §3 declared, or the fabricator will not build to
impedance.

## 7. Thermal note

The stackup **does not solve the airflow problem** and is not claimed to.

Thermal status remains **MARGINAL**. R_θ(j-c) plus copper spreading account for
only 5.7 K of the junction rise; the rest is board-to-air. Adding copper layers
improves spreading marginally and changes nothing about convection. h = 80
W/m²·K is not used anywhere.

What the stackup does contribute: L5 solid ground under the FETs gives the
thermal vias somewhere to spread into, and option B would improve that further.

## 8. Routing prerequisites

Before any copper is routed:

1. Fabricator confirms the stackup and returns **actual** dielectric thicknesses
2. Fabricator returns **calculated** 50 Ω and 90 Ω trace widths
3. §6.1 decided — A, B or C
4. §6.2 fixed — three footprints rebuilt
5. `dielectric_constraints` set and impedance classes declared
6. Finished-thickness arithmetic reconciled to 1.60 mm
7. All five frozen OPEN system requirements still stand

ROUTING STATUS: BLOCKED
