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
| 6 | **Camera mount rigidity** | **0.21 mm of differential movement over an 80 mm fastener spacing — total, for the life of the airframe.** Dowelled or bonded; **not** bolt friction. Kinematic or CF bracket so thermal growth translates rather than rotates. |
| 7 | **GNSS–camera lever arm** | A **measurable datum** — a defined feature callipers can reach, between antenna phase centre and camera mounting face. One dimension on a drawing. |

**Where #6 comes from, and what it is *not* for** ([`boresight_budget.py`](../tools/sizing-model/boresight_budget.py)):

The 0.16 m case-C boresight allocation is **0.153° at 60 m AGL**. Over an 80 mm
fastener spacing that is 0.21 mm of differential movement. An M3 clearance hole
has 0.2–0.4 mm of radial slop on its own, and one hard landing takes it up —
which is why this is a dowel-or-bond requirement rather than a preference.

But check the leverage before over-engineering it. At budget, boresight is
**3.3 % of geotag variance**; the 0.70 m unmodelled allowance (62.7 %) and the
0.50 m target-extent term (32.0 %) dominate. Tightening boresight *below* 0.16 m
buys essentially nothing:

| boresight | geotag RSS | delta |
|:--|--:|--:|
| 0.16 m (budget) | 0.884 m | — |
| 0.32 m | 0.93 m | +0.04 m |
| 0.64 m | 1.08 m | +0.20 m |
| 1.05 m (= 1° at 60 m) | 1.37 m | **+0.48 m** |

**So this is a failure-mode requirement, not an optimisation.** Design the mount
to *hold* whatever calibration you achieve. A shifted mount or a skipped
calibration costs ~0.5 m of geotag **silently** — nothing on the operator's
screen says the camera moved.

The lever arm is the same story inverted: measuring it to 1 cm instead of 10 cm
is worth **0.005 m**. It does not justify any design compromise — it justifies a
datum, so the 0.10 m is a budget line rather than a guess.

> **Thermal.** A 100 mm aluminium bracket on a CF plate moves 0.066 mm over a
> 30 K day–night swing — a third of the whole allowance if it becomes rotation.
> Calibrate at flight temperature, use CF, or constrain it kinematically.
| 8 | **Dual GNSS antenna baseline** | As long as the frame allows, symmetric about the CG, clear of carbon and power wiring. Heading accuracy scales with baseline length. |

## 3. Constraints from the mission

| # | Constraint | Requirement |
|---|---|---|
| 9 | **Footprint** | ≤ 1046 mm square at 20 in props. Three aircraft must sit inside a 3.66 m box with **no part outside during launch or landing** (rule 8.10, MB §7) |
| 10 | **Payload release** | Positive mechanical lock independent of servo power. A brownout must not drop a kit |
| 11 | **Compute bay airflow** | Fan on the **main bus, running at power-on** (SYS-53) — not gated on arming or flight mode. Inlet and outlet clear on the ground **and folded**. **Do not bolt the camera bracket to the compute bay.** Battery airflow separate |
| 12 | **Setup handling** | Unpack-to-armed is the binding constraint. Every fastener, connector and folding joint on the outside of this airframe is spending the 15 s of margin. Prefer captive fasteners, keyed connectors and folds that cannot be assembled wrongly |

**Why #11 says "at power-on"** ([`thermal_budget.py`](../tools/sizing-model/thermal_budget.py)):

The instinct is to let propwash cool everything and save the fan. It fails in
the one window that matters. During the 5-minute setup the avionics are powered,
the companion is booting and working, and **the props are stopped**.

A sealed 150 × 100 × 60 mm bay carrying 18 W reaches a **42.9 K** steady rise in
still air. Its time constant is 429 s, so across a 285 s setup it gets ~49 % of
the way there — about **56 °C of bay air on a 35 °C day, before the mission
starts**. That is air; silicon sits above it. A companion that throttles during
the search is a detection-rate problem that arrives late, under load, with
nothing on the operator's screen to explain it.

With a modest fan the rise is **10 K**. The flow needed is **3.3 CFM** — a 40 mm
fan on a fraction of a watt. **The cooling is not hard; remembering to power it
from the main bus at power-on is the whole requirement.**

Two couplings worth knowing:

- **Compute heat reaches the camera.** A sealed bay adds 0.068° of bracket
  rotation — 0.07 m at 60 m. Honestly, that is *nearly nothing* against the
  0.884 m geotag (it makes 0.887 m) and does not justify contorting the layout.
  It earns its line because it is **systematic** and tracks **compute load**, so
  it moves once the detector starts working. Calibrate cold, fly hot, and you
  get an unexplained bias in P7. The ask is free: don't share structure.
- **The battery is the opposite problem.** Pack I²R is **54 W in hover** — three
  times the companion — and ~0 W on the ground. So compute is hot when
  stationary, the battery when flying. A single "propwash cools everything"
  layout satisfies the pack and fails the bay.

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
