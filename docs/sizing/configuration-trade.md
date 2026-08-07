# RescueSwarm — Configuration Decision and Sizing-Constraint Review
### NIDAR 2026–27 Track 1 · Companion to `sizing-calculations.md`

**Status.** Coaxial is **decided — rejected**. The rotor-count decision (stay quad)
is **decided**. Prop diameter is **provisionally 18 in, to be confirmed on a bench
in Phase 5**. Everything marked **PROPOSED** is a recommendation awaiting a call.
The baseline design point in [`sizing-calculations.md`](sizing-calculations.md) and
the README is **unchanged** until those are adopted.

**Reproduce:** `python tools/sizing-model/config_trade.py`
→ committed output in [`config-trade-output.txt`](config-trade-output.txt).

---

## 0. Decisions

| Decision | Outcome | Confidence |
|---|---|---|
| Coaxial (X8)? | **No.** +61–84 % power, +26–34 % fleet mass, worst attitude bandwidth of any option. | High — robust at every κ |
| Rotor count? | **Stay quad — provisionally.** Hex 6×18″ is rejected on flight dynamics. Hex 6×16″ and octo 8×14″ are *not*; they are held off on assembly and preflight cost, which is **asserted, not measured**. | **Low — see §2.3** |
| Prop diameter? | **18 in provisionally**, arms designed to accept 16–20 in. Confirm in P5. | Medium — rests on an inertia proxy |
| Thrust-to-weight? | **Keep 2.0.** Attitude authority is never the wind limit. | High |
| Motor-out redundancy? | **Fit a recovery chute; rotor redundancy still open.** They cover different failures — only rotors preserve *score*. | Medium — §5.4 |
| VRS on descent? | **Fix the flight profile, not the airframe.** | High |

---

## 1. Method note: why a fixed pack size misleads

An earlier revision of this study compared configurations at a **fixed 194 Wh
pack**. That is the wrong comparison. It lets a thirsty configuration post a low
endurance number instead of paying for the battery it would actually need — and
X8 in particular silently **violated the reserve policy** (11.4 min hover against
a 7.7 min mission is 1.48×, where the policy demands ≥ 2×).

Every configuration here is sized to **satisfy** the policy: endurance ≥ 2×
mission time, and nominal + re-sweep + 4 min loiter inside 80 % DoD.

The consequence is worth stating on its own, because it governs the whole trade:

> **The 2×-endurance rule binds for every configuration — the energy rule never
> does.** So pack size is directly proportional to hover power, and any power
> penalty compounds: more battery → more mass → more power. Every config lands at
> exactly 15.5 min hover / 2.00× mission, and pays for it in fleet mass.

---

## 2. Configuration trade, reserve-policy sized

Mass scales with **motor** count; induced power scales with **disk** count. That
distinction is the whole coaxial argument, and it is why this needs its own
script: `prop_area()` in the main model multiplies disk area by `N_rot`, which
assumes every rotor has its own free-stream disk. A coaxial pair does not.

| Config | Pack Wh | MTOW kg | Fleet kg | P_hov W | Disk load | Footprint mm | Fits box | ΔP | Δmass |
|---|---|---|---|---|---|---|---|---|---|
| **Quad 4×20″** (current) | 194 | 5.06 | 15.18 | 603 | 6.24 | 1046 | 3/row | — | — |
| **Quad 4×18″** | 221 | 5.18 | 15.54 | 685 | 7.89 | 944 | 3/row | +13.7 % | +2.4 % |
| Quad 4×16″ | 264 | 5.45 | 16.34 | 820 | 10.50 | 843 | 4/row | +36.0 % | +7.6 % |
| Hex 6×18″ | 173 | 4.95 | 14.84 | 535 | 5.02 | 1432 | 2/row | −11.2 % | −2.2 % |
| Hex 6×16″ | 195 | 5.01 | 15.04 | 606 | 6.44 | 1279 | 2/row | +0.6 % | −0.9 % |
| Octo 8×14″ flat | 191 | 4.96 | 14.89 | 592 | 6.25 | 1363 | 2/row | −1.7 % | −1.9 % |
| X8 coax 4×2×20″ κ=0.85 | 313 | 6.40 | **19.19** | 971 | 7.89 | 1046 | 3/row | **+61.1 %** | **+26.4 %** |
| X8 coax 4×2×20″ κ=0.80 | 358 | 6.76 | **20.27** | 1111 | 8.33 | 1046 | 3/row | **+84.4 %** | **+33.5 %** |
| X8 coax 4×2×18″ κ=0.80 | 427 | 7.12 | **21.36** | 1325 | 10.84 | 944 | 3/row | +119.8 % | +40.7 % |
| X8 coax 4×2×22″ κ=0.80 | 322 | 6.68 | 20.05 | 999 | 6.81 | 1148 | 3/row | +65.8 % | +32.1 % |

### 2.1 Coaxial: rejected

Sized honestly, coaxial costs **+61 to +84 % hover power and +26 to +34 % fleet
mass**, eating the 39 % mass margin down to roughly 19 %. What it is supposed to
buy is compactness, and here it buys none: **stacking rotors does not shorten the
arms**, so the X8 footprint is *identical* to the quad it replaces (1046 mm).

It is also the **worst option on attitude bandwidth** — rotor inertia 2.0–3.1×
the current quad (§3) — which is the property that most directly governs a
precision hover-and-drop. Coaxial loses on power, on mass, and on the dynamics
that matter, simultaneously.

The conclusion does not depend on the interference factor. At an implausibly
generous κ = 0.95 it is still ~15 % worse for no compensating gain.

**Coaxial would only merit revisiting if the launch box shrank enough to force
rotor diameter down, or a transport-case constraint appeared that a folding-prop
quad could not meet.** Neither is in prospect.

### 2.2 Hex 6×18″: recommendation withdrawn

An earlier revision of this document recommended hex 6×18″ on the strength of its
−11 % hover power. **That recommendation is withdrawn.** It optimised the one
resource in surplus, and §3 shows it is the *worst* configuration on the two that
are not: it has the lowest disk loading of any option, making it the most
gust-sensitive, and its 2.3–6.9 m/s VRS window puts the current 2.5 m/s descent
rate **inside** the vortex-ring band.

**This rejection is on flight dynamics, not on setup time.** An earlier summary
of this document gave setup as the reason, which was wrong and is corrected in
§2.3.

### 2.3 Hex 6×16″ and octo 8×14″: the genuinely open case

Rejecting hex 6×18″ does **not** dispose of the other two, and an earlier
revision wrongly implied it did by treating "hex and octo" as one option.

| | Power | Mass | VRS @2.5 m/s | Gust | Rotor inertia | Motor-out |
|---|---|---|---|---|---|---|
| Quad 4×20″ | — | — | 0.48 v_i | 0.194 | 1.00 | ✗ |
| Hex 6×16″ | +0.6 % | −0.9 % | 0.48 v_i | 0.191 | **0.55** | ✓ |
| Octo 8×14″ | −1.7 % | −1.9 % | 0.48 v_i | 0.194 | **0.40** | ✓ |

Neither is a paper win on power — hex 6×16″ is a wash and octo is −1.7 %. But
neither carries the hex 6×18″ dynamics penalty either: **both match the quad
exactly on disk loading, VRS margin and gust sensitivity**, while offering
**2–2.5× better rotor bandwidth** and motor-out survivability.

On physics, **octo 8×14″ is arguably the better aircraft than the quad we have
chosen.**

The case for staying quad therefore rests almost entirely on **assembly and
preflight cost — which this study has not measured.** The setup budget
(main model, CORRECTION 6) carries a single 60 s line, "aircraft out of case,
battery in, power on (×3, serialised)", with no per-arm or per-rotor breakdown.
The claim that two or four extra arms meaningfully consume the 15 s of setup
margin is **plausible and unquantified**.

**PROPOSED:** treat "stay quad" as provisional and low-confidence. The P1
cold-boot bench test (see [`../schedule-baseline.md`](../schedule-baseline.md) §5)
already exists and is the highest-priority measurement in the programme —
**extend it to time unpack-to-armed for a 4-arm and a 6-arm frame**. That single
measurement converts this from an assertion into a decision. Until then, avoid
frame design choices that would preclude a 6-arm variant.

### 2.4 The third axis: build and debug effort

The trade above weighs physics and setup time. There is a third axis that a
22-week programme with no flight code written cannot ignore, and it is **not** a
physics question:

| | Quad | Hex | Octo |
|---|---|---|---|
| Motors, ESCs, props to mount and wire, across 3 aircraft | **36** | 54 | 72 |
| Motor/ESC channels to calibrate and tune | **12** | 18 | 24 |
| Independent propulsion failure points during integration | **12** | 18 | 24 |

A hex is **50 % more propulsion integration** than a quad; an octo is double. That
is soldering, calibration, tuning, and — more importantly — debugging time during
the phase where the schedule is tightest and the team is also writing autonomy,
perception and a ground station from nothing.

**This is a judgement about programme risk, not a measurement**, and it is stated
as such. But it points the same way for a student team on a compressed calendar:
the physics case for hex or octo is real and modest, while the schedule case for
the quad is substantial. Complexity is what most often kills projects of this
shape, and 21 weeks is not long.

**RECOMMENDED: build the quad**, on schedule-risk grounds rather than the
unmeasured setup claim that §2.3 corrects. Revisit only if the organisers answer
that motor-out tolerance is *required* (Q3), in which case the decision is made
for us and the extra integration has to be absorbed.

---

## 3. Flight dynamics — what steady-state momentum theory misses

The main model is steady-state. The hard part of this mission is not steady: it
is holding position precisely, in wind, while descending to 6 m and releasing.

| Config | v_i m/s | VRS window m/s | Descent @2.5 m/s | Gust ΔT/W per m/s | Rotor inertia |
|---|---|---|---|---|---|
| **Quad 4×20″** (current) | 5.16 | 2.6 – 7.7 | **0.48 v_i** | **0.194** | 1.00 |
| **Quad 4×18″** | 5.80 | 2.9 – 8.7 | 0.43 v_i | 0.172 | **0.62** |
| Quad 4×16″ | 6.69 | 3.3 – 10.0 | 0.37 v_i | 0.149 | **0.37** |
| Hex 6×18″ | 4.63 | 2.3 – 6.9 | **0.54 v_i ⚠** | 0.216 | 0.93 |
| Hex 6×16″ | 5.24 | 2.6 – 7.9 | 0.48 v_i | 0.191 | 0.55 |
| Octo 8×14″ flat | 5.16 | 2.6 – 7.7 | 0.48 v_i | 0.194 | 0.40 |
| X8 coax 4×2×20″ κ=0.80 | 5.96 | 3.0 – 8.9 | 0.42 v_i | 0.168 | **2.00** |
| X8 coax 4×2×22″ κ=0.80 | 5.39 | 2.7 – 8.1 | 0.46 v_i | 0.186 | **3.07** |

### 3.1 Gust sensitivity is exactly 1/v_i

From momentum theory, `T = 2ρA v_i²`, so `∂T/∂V` at `V = 0` is `2ρA v_i`.
Normalised by weight this is exactly **1/v_i**. A 1 m/s vertical gust therefore
perturbs thrust by **19.4 % of weight** on the current design, open loop.

**Low disk loading is a liability for this mission, not a virtue.** The 20 in
rotors are optimised for endurance that sits in 74 % surplus, and they pay for it
in disturbance rejection. Every step down in diameter improves it: 18 in gives
0.172, 16 in gives 0.149.

### 3.2 Attitude bandwidth

`J_rotor` is a proxy — `Σ m_prop·R²`, relative to the current quad. Lower means
faster thrust response and therefore higher attitude bandwidth, which is what
rejects a gust once it has hit. Response time scales steeply with diameter
(τ ~ D^3.5 at fixed aircraft power), so the 38 % inertia reduction from 20 → 18 in
is meaningful.

**This is a proxy and the magnitude needs bench measurement.** The *direction* —
smaller rotors respond faster — is robust; the size of the gain is not, and it is
the main reason prop diameter is provisional rather than decided.

Note that the two effects compound in the same direction: low disk loading means
**larger** disturbances, and large rotors mean **slower** correction. The current
design is worst-in-class among the quads on both.

---

## 4. Stall

**Blade stall is not a limiting factor.** Advance ratio `μ = V/v_tip`, with tip
speed from `T = C_T ρ A (ΩR)²` at `C_T = 0.012`:

| Config | v_tip m/s | μ @8 | μ @12 | μ @16 | μ @20 |
|---|---|---|---|---|---|
| Quad 4×20″ | 66.6 | 0.12 | 0.18 | 0.24 | **0.30** |
| Quad 4×18″ | 74.9 | 0.11 | 0.16 | 0.21 | 0.27 |
| Quad 4×16″ | 86.4 | 0.09 | 0.14 | 0.19 | 0.23 |

Retreating-blade effects appear above μ ≈ 0.30. At search (8 m/s) and transit
(12 m/s) speeds μ sits near 0.2 with ample margin. **But the current 20 in rotor
reaches μ = 0.30 at 20 m/s** — so if search airspeed is raised for wind
penetration (§5.2), the drag-only model of CORRECTION 4 stops being sufficient and
the high-speed end needs validating. Smaller rotors have more headroom here too.

**Vortex ring state is the stall-type phenomenon that actually threatens this
aircraft**, and it is addressed in §5.1.

Motor/ESC desync under rapid throttle transients is a bench item for P5, not a
sizing question.

---

## 5. Sizing-constraint review

The model sizes against margins it already has:

| Constraint | Limit | Design | Margin | Binding? |
|---|---|---|---|---|
| Fleet mass | 25 kg | 15.18 kg | 39 % | No |
| Mission time | 30 min | 7.7 min | 74 % | No |
| Coverage | 10 ha | 93 s/drone | ~95 % | No |
| Link margin | — | 13.7 dB @ 600 m | large | No |
| **Setup to launch** | **300 s** | **~285 s** | **5 %** | **Yes** |
| **Descent / VRS** | **—** | **0.48 v_i, at onset** | **none** | **Yes, unstated** |
| **Wind penetration** | **unspecified** | **fails at 8 m/s** | **none** | **Yes, unstated** |
| **Detection recall** | **≥ 0.90** | **unmeasured** | **unknown** | **Yes, long pole** |

### 5.1 VRS — fix the profile, not the airframe

A nulled-groundspeed descent is near-vertical, which is precisely the condition
vortex ring state requires. At 2.5 m/s the current design sits at **0.48 v_i**,
on the conventional 0.25–0.5 v_i onset boundary, with no margin — **on every
delivery**.

| Descent rate | × v_i | Verdict | 54 m takes | vs 2.5 m/s |
|---|---|---|---|---|
| 1.00 m/s | 0.19 | safe | 54.0 s | +32.4 s |
| 1.25 m/s | 0.24 | safe | 43.2 s | +21.6 s |
| 1.50 m/s | 0.29 | marginal | 36.0 s | +14.4 s |
| 2.50 m/s | 0.48 | marginal | 21.6 s | — |
| 3.00 m/s | 0.58 | **VRS risk** | 18.0 s | −3.6 s |

**PROPOSED (a):** descend at ≤ 1.25 m/s — costs ~72 s per aircraft across 3.3
drops, against a 74 % time margin.
**PROPOSED (b), preferred:** hold horizontal speed ≥ v_i (5.2 m/s) through the
descent and decelerate to hover at the 6 m drop altitude. **Costs nothing**, and
cuts time spent in the gust-sensitive regime.

This is a waypoint-parameter fix. **Do not buy hardware for it.**

### 5.2 Wind is the unstated cliff

From CORRECTION 4: sweep time per drone goes 83 s → 111 s (4 m/s wind) → 191 s
(6 m/s), and at **8 m/s the aircraft cannot make headway at all**, because search
groundspeed *is* 8 m/s. That is total mission failure at ordinary flood weather,
and no requirement currently forbids it. It is not a power problem — penetrating
at 12 m/s costs 105 W against a 603 W hover draw.

> **Confirmed by the organisers: wind is natural and uncapped.** There is no
> maximum condition and no artificial wind — the mission runs in whatever weather
> occurs, and nothing in the rules protects us from the 8 m/s cliff.

**REQUIRED, not proposed** — now **SYS-37**: retain positive headway at **10 m/s**
sustained wind, sizing search *airspeed* for it while flying 8 m/s *groundspeed*
nominally, and validate the high-speed end against §4. The finals fall in January,
when much of India is comparatively calm — but that is luck, not design margin.

### 5.3 Search altitude should be an output, not an input

Recall is the long pole; coverage time is nearly free. Altitude should fall out of
a recall requirement rather than being fixed at 60 m.

| AGL | GSD | Person | Sweep/drone | Mission budget |
|---|---|---|---|---|
| 60 m | 1.82 cm/px | 93 px | 93 s | 5 % |
| **40 m** | **1.22 cm/px** | **140 px** | **149 s** | **8 %** |
| 30 m | 0.91 cm/px | 186 px | 187 s | 10 % |

40 m gives **50 % more pixels on target** for 56 s of a 1800 s budget.

> **Correction.** An earlier revision of this section also claimed that lowering
> altitude shrinks the dominant 2.76 m ground-height geotag term, "because it
> scales with the 37 m frame-edge distance, which falls with altitude". **That is
> wrong.** The frame-edge distance is `r = h·tan θ` and the projection error is
> `(Δh/h)·r = Δh·tan θ` — the `h` cancels. The term depends only on the
> ground-height uncertainty and the off-nadir angle, so **flying lower does not
> touch it**. What does: surveying the field elevation (or a laser rangefinder) to
> shrink `Δh`, and geotagging only near-nadir detections to shrink `tan θ`. See
> [`mission-profile-output.txt`](mission-profile-output.txt) §2. Altitude *does*
> shrink the attitude/boresight term, which scales as `h·ε`, and improves centroid
> accuracy through GSD — but the case for going lower rests on **recall**, not
> geotagging.

**PROPOSED:** re-baseline to 40 m pending P7 recall-vs-GSD measurement. The
scoring structure strengthens this considerably — see
[`../requirements/rulebook-compliance.md`](../requirements/rulebook-compliance.md)
§1.2, where detection is 250 points and speed is 50 that are already won.

### 5.4 Redundancy: fit both, because they cover different failures

**Organiser position (final):** a recovery parachute for the aircraft **is
permitted, including pyrotechnic and CO₂ deployment** — the earlier "no blast"
answer referred to parachuting the *kit*, not the airframe. The condition attached
is that the aircraft **must land on the landing pad**.

#### The landing-pad condition cannot be met under canopy

Drift under canopy is `wind × h / v_descent`. At a typical 5 m/s descent for a
5 kg airframe, against a 3.66 m pad:

| Release altitude | 2 m/s wind | 3 m/s wind | 6 m/s wind |
|---|---|---|---|
| 60 m (search) | 24 m | **36 m** | 72 m |
| 40 m | 16 m | 24 m | 48 m |
| 20 m | 8 m | 12 m | 24 m |
| 6 m (drop hover) | 2.4 m | 3.6 m | 7.2 m |

To stay inside the pad you would have to deploy below **4.6 m** in a 2 m/s breeze,
**3.0 m** at 3 m/s, **1.5 m** at 6 m/s — all below the altitude at which a canopy
can inflate at all (typically 15–20 m minimum for this class). **A recovery chute
and the landing-pad condition are physically incompatible in flight.**

#### The penalties make it worth deploying anyway

| Outcome | Penalty | Airframe |
|---|---|---|
| Motor-out, no chute | **−50** (crash) + likely −10 (landed outside) | Destroyed |
| Motor-out, chute deployed, lands off-pad | **−10** (landed outside) | Usually survives |

Deploying is worth **~40 points** even accepting the off-pad penalty, before
counting the airframe and the safety case. Penalty 1 also exempts an
"organiser-approved emergency landing", which a canopy descent plausibly is.

**NEW QUESTION FOR THE ORGANISERS:** is a recovery-canopy descent scored as an
*emergency landing* (−10, or exempt) or as a *crash* (−50)? The rules define a
crash as "uncontrolled ground impact, collision resulting in loss of flight, or
crash landing", and a canopy descent is arguably none of those. The answer is
worth 40 points per incident.

#### Chute and rotor redundancy are not substitutes

They fail differently and the mission outcomes differ completely:

| | Rotor redundancy (hex / octo) | Recovery chute |
|---|---|---|
| Covers | Single motor or ESC failure | Total power loss, structural failure, FC failure, multi-motor loss |
| Mission outcome | **Continues — no points lost** | Aircraft is down; its share of coverage and deliveries is lost |
| Score impact | 0 | −10 at best, −50 if scored as a crash |
| Works during the 6 m delivery hover? | **Yes** | **No** — too low to inflate |
| Mass cost | +2 or +4 motors, ESCs, arms | ~300 g |
| Setup cost | more arms to unfold — **unmeasured** (§2.3) | negligible |

The chute covers the search phase, which is most of the flight time, and does
nothing during the delivery hover. Rotor redundancy covers the one failure mode
that is both most likely and most recoverable, and is the only one of the two that
**preserves score** rather than merely preserving hardware.

**RECOMMENDED: fit both.** Three chutes cost ~0.9 kg of a 9.8 kg fleet margin,
which is cheap for eliminating the −50 crash case and the safety hazard of a 5 kg
airframe falling on a field. Rotor redundancy remains the open question at §2.3,
and is now decided on *scoring* grounds rather than safety ones — a hex or octo
keeps flying and keeps earning, where a chute ends that aircraft's mission.

Still worth asking the organisers whether motor-out tolerance is separately
required, and whether a **non-pyrotechnic** canopy would be accepted.

### 5.5 Open risk: quad yaw authority

Quad yaw comes only from motor-torque differential and is the weakest of any
configuration considered. Heading hold in crosswind feeds camera pointing and
therefore geotag accuracy. This is the one genuine argument for more rotors that
this study does not dismiss — it is a **P4 SITL / P5 bench check**, not a reason to
change configuration now.

---

## 6. Assumptions introduced here

| Assumption | Value | Basis | Replace with |
|---|---|---|---|
| Coaxial interference κ | 0.80–0.85 | Published multirotor coaxial data. **The only figure in this repo not derived from the project's own model.** | Thrust-stand test, only if coaxial is revisited |
| Rotor inertia proxy | Σ m_prop·R² | Direction is robust, magnitude is not | Bench step-response measurement, P5 |
| VRS onset band | 0.25–0.5 v_i | Conventional rotorcraft practice | Flight test in P6, instrumented descent |
| Prop mass scaling | ∝ D^2.5 | Planform × thickness. Main model holds prop mass fixed across diameters | Vendor mass data at 16/18/20 in |
| Thrust coefficient | C_T = 0.012 | Typical multirotor prop; used only for advance ratio | Vendor or bench data |
| Hex/octo arm geometry | Centres on a circle, 30 mm tip clearance | Same convention as main model STEP 11 | CAD once frame layout is fixed |

Every other constant is imported live from `rescueswarm_sizing_model.py`.
