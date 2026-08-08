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
| 2a | **Folding arms are ALLOWED, with a hard budget** | Deploy + lock + **verify** in **≤ 22 s per aircraft**. Folds strictly **outboard** of the camera/IMU/GNSS core | Measured, not assumed — [`setup_budget.py`](../tools/sizing-model/setup_budget.py). Deployment is *free* up to 22 s because it hides in the 75 s companion-boot shadow; the crew are not the critical path. It goes over the window at 30 s, and 28 s only "passes" by 1 s, which is a coin toss rather than margin. **22 s needs quick-release clamps and a lock indicator visible from a metre away — it is not achievable with bolts.** The launch box does not force this either way: three aircraft unfolded at 1046 mm sit in 3138 mm, inside the 3.66 m box. Folding buys transport volume only, ~944 mm → ~450 mm. |
| 3 | **Battery bay** | **6S3P, 18 × 21700, 1449 g.** Bare cell block ≈ **126 × 70 × 63 mm** (6 across × 3 deep, cells lying down); allow **≈ 140 × 80 × 78 mm** with holders, wrap, BMS and leads, plus ~15 % growth on the 63 mm axis | ⚠ **This entry previously said 6S2P, 12 cells, 966 g.** That was the pre-BOM design point. With real Indian component masses (+471 g/aircraft) the 6S2P pack **fails the ≥2.0× endurance reserve at 1.78×**; 6S3P makes it at 2.05×. The change is **+6 cells and +483 g** — a whole extra row. The old "~20 % volume growth" allowance covered 14.4 cells, so a bay built to the old entry **could not take the real pack even with its stated margin**. Authoritative source: [`sizing/model-output.txt`](sizing/model-output.txt). |
| 4 | **Payload magazine** | 4 kits, each 200 × 100 × 50 mm, 200 g. **Lay it out for packaging and drop-path clearance, not for CG** — centre the group on the CG and stop there | Fixed by rule — MB §2. Can be designed and built today, independent of everything else. CG was checked rather than assumed ([`cg_budget.py`](../tools/sizing-model/cg_budget.py)): across a 2×2 and two row layouts, peak CG excursion during release is **3.7–4.0 mm at best order and 7.4 mm at worst — under 4 % of hover thrust either way.** Layout is worth 0.3 mm; *release order* is worth twice as much, and that is autonomy's decision, not CAD's. |
| 4a | **Battery tray** | **Side-loading, captive latch, hard stop.** Repeatable position, not adjustable | The pack is the heaviest item at 22.8 % of MTOW, so its seating repeatability *is* the trim repeatability — a 10 mm placement error is 2.3 mm of CG and ~1.2 % permanent trim. Side loading also keeps a pack swap clear of the parachute mount above and the magazine below, and off the setup critical path. |
| 4b | **Vertical CG** | Pack CG **in the rotor plane**, not slung beneath it | Hanging the heaviest item low for "stability" is a fixed-wing instinct that misfires on a multirotor: the rotors are the control effectors, and a CG well below them makes a pendulum the controller fights, coupling attitude into translation during exactly the slow precise hover a delivery needs. The extra 21 mm the 6S3P block needs over 6S2P should be taken by making the tray **wider or longer, not deeper**. |
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

## 3a. Two constraints that fight each other

These are not independent, and CAD has to resolve them together rather than
satisfying each in turn.

**Parachute cone vs GNSS antennas — both want the top centre.** #5 needs a clear
deployment cone straight up from top-centre with nothing in the path. #8 wants
two GNSS antennas symmetric about the CG, raised, clear of carbon. Antennas on
masts either side of centre are directly in the canopy's way, and a chute that
snags on an antenna mast is worse than no chute — it deploys asymmetrically and
takes the aircraft down inverted. **Resolve by putting the antennas on the arms
or on booms outboard of the cone**, keeping them symmetric about the CG, and
proving the cone clear with a swept-volume check in CAD rather than by eye.

**Folding joints vs boresight vs setup time.** Folds help transport and cost
setup seconds (#12). More importantly they must not sit between the camera and
the GNSS antennas: every folding joint in that load path is a lever-arm term
that changes each time the aircraft is unpacked, which breaks #6 and #7 and
invalidates SYS-48. **The camera, the IMU and the GNSS antenna mounts must all
be on one rigid core structure**, with folds only outboard of them.

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
