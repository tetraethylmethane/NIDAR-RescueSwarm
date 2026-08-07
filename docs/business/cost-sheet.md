# RescueSwarm — Cost Sheet

**Required deliverable (rulebook 7.5):** "A detailed bill of materials and cost
sheet specifying all costs and expenses incurred by the team in designing,
developing, integrating and testing its solution." Submitted with the Phase 4B
Business Strategy presentation, and scored under parameter 5, *Expenditure
Breakdown & Resource Planning* (20 points).

**Status: skeleton — figures to be filled as procurement happens.** Keep this
current from P1 onward. Reconstructing spend from memory in January is both
harder and less accurate, and the jury can ask about any line.

**Scope note.** This is *all costs incurred*, not just flight hardware. The
commonly forgotten categories are development tooling, test consumables, crash
replacements and travel — and a cost sheet showing only the BOM total tends to
read as incomplete.

---

## A. Flight hardware — per aircraft × 3

Line-item detail lives in [`../../hardware/bom/`](../../hardware/bom/); this is
the roll-up.

| Subsystem | Per aircraft (INR) | × 3 | Notes |
|---|---|---|---|
| Frame, arms, landing gear, hardware | | | Custom — 8.2 forbids a ready-to-fly airframe |
| Motors (4) | | | |
| ESCs (4) | | | |
| Propellers (4) + spares | | | Spares are not optional |
| Battery pack (12 × 21700) + BMS | | | |
| Flight controller + GNSS (dual, RTK-capable) | | | |
| Companion computer + carrier | | | |
| Camera + lens | | | |
| Radios — 5.8 GHz mesh node, 868 MHz safety link | | | |
| Payload magazine + release mechanism | | | |
| Wiring, connectors, PDB | | | |
| **Flight hardware subtotal** | | | |

## B. Ground segment

| Item | Cost (INR) | Notes |
|---|---|---|
| GCS computer | | |
| GCS mesh node + sector antenna + mast | | |
| 868 MHz ground radio | | |
| **RTK base station + survey tripod** | | **Confirmed permitted — required item.** Worth 82 delivery points; see compliance §4.4 |
| Cases, transport, field kit | | |
| **Ground segment subtotal** | | |

## C. Payload and mission consumables

| Item | Cost (INR) | Notes |
|---|---|---|
| Survivor kits (200 g each, 20×10×5 cm) | | ≥12 plus spares |
| Ground-truth targets / mannequins | | Also serves the P7 dataset |
| Surveyed marker set | | For geotag verification |
| **Subtotal** | | |

## D. Development and test

| Item | Cost (INR) | Notes |
|---|---|---|
| Development boards, sensors for bench work | | Includes C-DAC VEGA if not free-issued |
| Test bench, thrust stand, power supply | | Thrust stand also settles the rotor-inertia proxy |
| **Crash and damage replacement allowance** | | Budget it; do not discover it |
| 3D printing / machining | | |
| Software, simulation, cloud (non-mission) | | |
| **Subtotal** | | |

## E. Programme costs

| Item | Cost (INR) | Notes |
|---|---|---|
| **Registration fee** | **5,000** | Rule 4.6, non-refundable |
| Travel and accommodation for finals | | |
| Field-test logistics | | Site access, transport |
| Documentation, printing | | |
| **Subtotal** | | |

---

## Roll-up

| Category | Cost (INR) | % of total |
|---|---|---|
| A. Flight hardware (×3) | | |
| B. Ground segment | | |
| C. Payload and consumables | | |
| D. Development and test | | |
| E. Programme | | |
| **TOTAL** | | 100 % |

## Funding against spend

| Source | Amount (INR) | Status | Evidence |
|---|---|---|---|
| Institutional grant | | | |
| Departmental support | | | |
| Component sponsorship (in kind) | | | Value at market price and say so |
| Incubator / external sponsor | | | |
| Team contribution | | | |
| **TOTAL FUNDED** | | | |
| **Gap** | | | |

> Sponsorship and funds raised are separately scored (parameter 6, 20 points) and
> have **lead time**. Record evidence — letters, emails, invoices — as it arrives.
> In-kind component sponsorship counts and should be valued explicitly.

---

## Cost per system

Worth stating explicitly, because the Business Strategy pitch needs a unit
economic story and the jury will ask for one:

| Metric | Value |
|---|---|
| Cost per aircraft (recurring hardware only) | |
| Cost per 3-aircraft system | |
| Non-recurring development cost | |
| Projected unit cost at 10 systems | |
| Projected unit cost at 100 systems | |

The gap between the prototype cost and the volume cost is the heart of
parameter 4 (Business Model & Revenue Approach). Show the learning curve
assumption rather than asserting a number.
