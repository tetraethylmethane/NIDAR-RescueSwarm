# Frame Design Constraints
### What CAD needs before the first part is cut

Everything here is expensive or impossible to retrofit. Decide these before the
frame is designed, not after.

---

## 1. Decided

| # | Constraint | Value | Why |
|---|---|---|---|
| 1 | **Configuration** | **Quadrotor, 4 arms** | Physics marginally favours hex/octo, but a hex is 50 % more propulsion integration across three aircraft and an octo is double, on a 21-week calendar with no flight code written. See [configuration-trade](sizing/configuration-trade.md) §2.4. **Revisit only if organiser Q3 says motor-out tolerance is required.** |
| 2 | **Arms accept 16–20 in props** | Wheelbase sized for 20 in with 30 mm tip clearance → **761 mm diagonal** | Prop diameter is provisionally 18 in but settles on a bench in P5. Late-binding costs nothing now and everything later. |
| 3 | **Battery bay** | 6S2P, 12 × 21700, 966 g, with ~20 % volume growth | The reserve policy sizes the pack from hover power. If the pack grows, the bay must not be the thing that stops it. |
| 4 | **Payload magazine** | 4 kits, each 200 × 100 × 50 mm, 200 g | Fixed by rule — MB §2. Can be designed and built today, independent of everything else. |
| 5 | **Parachute mount** | Top-centre, clear deployment cone, no prop or antenna in the path | Permitted and worth fitting (SYS-41). **Must be designed in** — a retrofitted mount fouls props or deploys into an arm. |

## 2. Constraints that come from the accuracy budget

Geotagging is 75–83 % of the delivery error budget and gates 450 of the 600 flight
points. Three of its terms are decided by *mechanical design*, not software:

| # | Constraint | Requirement |
|---|---|---|
| 6 | **Camera mount rigidity** | Boresight must hold calibration through transport, launch vibration and landing. A flexible or re-clampable mount invalidates SYS-48 and silently degrades every geotag. Prefer a bonded or doweled mount over one that relies on bolt friction. |
| 7 | **GNSS–camera lever arm** | Must be **fixed, known and measurable** to ~1 cm. It is a 0.10 m term in the error budget only because it is assumed rigid. Design a measurable datum between the GNSS antenna phase centre and the camera. |
| 8 | **Dual GNSS antenna baseline** | As long as the frame allows, symmetric about the CG, clear of carbon and power wiring. Heading accuracy scales with baseline length. |

## 3. Constraints from the mission

| # | Constraint | Requirement |
|---|---|---|
| 9 | **Footprint** | ≤ 1046 mm square at 20 in props. Three aircraft must sit inside a 3.66 m box with **no part outside during launch or landing** (rule 8.10, MB §7) |
| 10 | **Payload release** | Positive mechanical lock independent of servo power. A brownout must not drop a kit |
| 11 | **Compute bay airflow** | Forced-air cooling active from power-on (SYS-53). The worst thermal case is the 3-minute ground idle during setup, props stopped, not flight |
| 12 | **Setup handling** | Unpack-to-armed is the binding constraint. Every fastener, connector and folding joint on the outside of this airframe is spending the 15 s of margin. Prefer captive fasteners, keyed connectors and folds that cannot be assembled wrongly |

---

## 4. Still open — do not let these block the build

| Question | Blocks | Workaround while waiting |
|---|---|---|
| Q3 — is motor-out tolerance required? | Configuration (#1) | Build the quad. If the answer forces hex, the payload, avionics and ground segment all carry over; only the frame and propulsion are lost. |
| Q1 — how is "correctly geotagged" verified? | How much to spend on absolute RTK accuracy | Nothing mechanical. Affects procedure, not structure. |

**Nothing else in this document is waiting on an answer.**

---

## 5. Build now, in parallel with the frame

None of this depends on the airframe existing:

- Payload magazine and release mechanism (#4, #10) — dimensions are fixed by rule
- Ground station, including the read-only architecture
- Autonomy stack and multi-instance SITL
- Perception pipeline and the KML parser
- The full avionics stack on a bench, which is also the setup-timing test rig
