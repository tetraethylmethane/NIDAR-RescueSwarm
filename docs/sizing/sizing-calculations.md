# RescueSwarm — Sizing & Engineering Calculations
### NIDAR 2026–27 Track 1 · Companion volume to the Development Plan

**Purpose:** convert the Mission Brief constraints into a closed, self-consistent design point, with every number traceable to a stated method and assumption. This is a *preliminary sizing* — the accuracy of a first-order model with empirical scaling laws, roughly ±10–15 % on mass and ±20 % on power. Every assumption is listed in §16 with the phase in which it must be replaced by measured data.

---

## 0. The design point, in one card

| Parameter | Value |
|---|---|
| Fleet | **3 aircraft**, identical |
| Configuration | Quadrotor, 18 in CF folding props, 6S3P 21700 Li-ion |
| MTOW per aircraft (4 kits loaded) | **5.88 kg** |
| **Fleet all-up weight** | **17.65 kg** vs 25.0 kg limit → **29 % margin** |
| Empty mass (no battery, no kits) | 3.63 kg |
| Battery | 18 × 21700, 1449 g, **292 Wh**, 13.5 Ah, 21.6 V nom |
| Disk loading | 9.0 kg/m² |
| Hover power (electrical) | **818 W** · power loading 7.2 g/W |
| Hover endurance @ 80 % DoD | **17.1 min** (2.22× the mission) |
| Design mission duration | **7.7 min** (26 % of the 30 min allowance) |
| Design mission energy | 95 Wh = **41 % of usable** → lands at ~68 % SoC |
| Thrust-to-weight (static, SL) | 2.0 → 2.94 kgf per motor |
| Hover throttle point | 50 % of max motor thrust |
| Search altitude / speed | 60 m AGL / 8 m/s **groundspeed** |
| GSD at 60 m | 1.82 cm/px → person ≈ 93 px long |
| Sweep time (10 ha, 3 drones) | ~93 s per drone including turns |
| Geotag accuracy (design target) | **CEP50 ≤ 0.75 m** with RTK — scoring-derived, see `../requirements/rulebook-compliance.md` |
| Delivery accuracy (design target) | **≥ 60 % within 2 m, ≥ 30 % within 1 m** of the survivor, from a 6 m hover-and-drop |
| Peak current | 102 A (7.6 C) — pack burst capability 135 A, 32 % margin |

**The headline result: nothing about this mission is tight except the 5-minute setup window.** Mass has 29 % margin, energy has 59 % margin, coverage uses a quarter of the allowed time, and the link budget has >13 dB of fade margin. Setup has **15 seconds** of margin. Allocate engineering effort accordingly.

---

> ### ⚠ Read §0 as current; read §2–§4 as history
>
> The design point card above is **current** — 18 in props, 6S3P, reconciled with the
> Indian BOM to within 1 %.
>
> The derivation sections that follow (**§2 fleet sizing, §3 rotor sizing, §4 battery
> sizing**) still work through the **earlier 20 in / 6S2P** design, because that is the
> path the model originally took. Their *method* is sound and worth reading; their
> *numbers* — 5.05 kg MTOW, 39 % margin, "20 in selected", the 6S2P pack — are
> superseded.
>
> Why the design point moved: with generic component masses the 6S2P pack met the
> 2× endurance reserve at 2.01×. With the BOM's real Indian masses it does not, at
> 1.78×. See [`bom_reconcile.py`](../../tools/sizing-model/bom_reconcile.py) and
> [`bom-reconcile-output.txt`](bom-reconcile-output.txt).
>
> **Rewriting §2–§4 against the new design point is a P1 task.**

---

## 1. Method and governing equations

### 1.1 Hover power — momentum theory with a figure of merit

Induced velocity through an actuator disk, and the resulting rotor shaft power:

```
v_i  = sqrt( T / (2 ρ A) )
P_ideal = T · v_i = (m g)^(3/2) / sqrt(2 ρ A_total)
P_shaft = P_ideal / FM
P_elec  = P_shaft / (η_motor · η_ESC) + P_avionics
```

where `A_total = N_rotors · π (D/2)²`.

**Figure of merit FM = 0.60.** The literature range for small multirotor propellers is 0.5–0.7; 0.6 is the standard value used in multicopter range/endurance work (e.g. *Range, Endurance and Optimal Speed Estimates for Multicopters*, arXiv:2109.04741, which uses 0.6 explicitly). Using 0.5 instead raises hover power by 20 %; using 0.7 lowers it by 14 %. **This is the single largest uncertainty in the power model — measure it on a thrust stand in Phase 5.**

### 1.2 Air density

`ρ = 1.150 kg/m³` — approximately 30 °C at ~300 m elevation, i.e. a realistic Indian summer field, not ISA sea level. Using ρ = 1.225 would understate hover power by ~3 % and overstate available thrust by ~6 %. Motor sizing uses sea-level static thrust figures (as manufacturers publish them), which is the conservative direction.

### 1.3 Mass convergence

MTOW is solved by fixed-point iteration, because propulsion and structure mass both scale with MTOW:

```
m_motors    = N · (T/W · m g / N) / k_T        k_T = 195 N per kg of motor mass
m_ESC       = 0.35 · m_motors
m_structure = 0.235 · MTOW
MTOW        = (m_avionics + m_payload_sys + m_battery + m_motors + m_ESC + m_props) / (1 − 0.235)
```

- `k_T = 195 N/kg` is calibrated against T-Motor MN-class hardware (e.g. an MN5008-class motor at ~175 g producing ~3.5 kgf on an 18 in prop ≈ 196 N/kg).
- `k_struct = 0.235` sits inside the 0.20–0.30 empirical band for multirotor structural fraction (Budinger et al.'s scaling laws, validated 1.6–8.5 kg).

### 1.4 Battery specific energy — pack level, not cell level

| Chemistry | Cell | Pack level used |
|---|---|---|
| 6S high-C LiPo | ~180 Wh/kg | **165 Wh/kg** |
| 21700 Li-ion (Molicel P45B class) | ~231 Wh/kg | **200 Wh/kg** |

The pack figure includes holders, BMS, balance leads, main leads and wrap (~15 % penalty). Usable depth of discharge **80 %** — land at 20 % SoC, which is both a battery-health and a safety-reserve decision.

---

## 2. Fleet sizing against the 25 kg cap

C2 caps the **combined** all-up weight of all deployed drones at 25 kg. Working target: **24.0 kg**, leaving 4 % against scale calibration and last-minute additions.

| Fleet | MTOW allowed each | Verdict |
|---|---|---|
| 2 drones | 12.0 kg | Wasteful — a 12 kg airframe for a 200 g payload; and one failure ends the attempt |
| **3 drones** | **8.0 kg** | **Selected.** Design comes in at 5.05 kg, so 39 % margin. One aircraft can fail and the fleet is still rule-compliant (≥ 2) |
| 4 drones | 6.0 kg | Achievable, but adds a fourth boot into a 300 s window and a fourth recovery into a 3.66 m box for ~15 s of sweep time |

Because the design lands so far under the cap, **the 25 kg rule is not the binding constraint** — which is worth knowing, because it means you should not compromise reliability to save grams.

---

## 3. Rotor sizing — disk loading sweep

At a 6.5 kg reference mass, quad configuration:

| Prop | A_total | Disk loading | Hover P_elec | Power loading |
|---|---|---|---|---|
| 15 in | 0.456 m² | 14.3 kg/m² | 1118 W | 5.7 g/W |
| 16 in | 0.519 m² | 12.5 kg/m² | 1052 W | 6.2 g/W |
| 17 in | 0.586 m² | 11.1 kg/m² | 993 W | 6.5 g/W |
| 18 in | 0.657 m² | 9.9 kg/m² | 941 W | 6.9 g/W |
| **20 in** | **0.811 m²** | **8.0 kg/m²** | **852 W** | **7.6 g/W** |
| 22 in | 0.981 m² | 6.6 kg/m² | 780 W | 8.3 g/W |

Hover power scales as `1/D`, so bigger is always more efficient. The counter-pressures are frame mass and size, prop inertia (slower control response), cost, and transport. **20 in selected**: 9 % less hover power than 18 in for a modest size increase, and it keeps the footprint (~1.05 m square) such that all three aircraft still fit inside the 3.66 m launch box.

At the final MTOW of 5.05 kg, disk loading is **6.2 kg/m²** and power loading **8.4 g/W** — a comfortable, efficient design point for this class.

---

## 4. Battery sizing — the reserve policy, not the mission, sets the pack

Sizing to the nominal mission would give an absurdly small pack. Sizing to maximum endurance would give an 11 kg aircraft (the unconstrained optimum sits at ~4.8 kg of battery, well past the fleet cap). Neither is the right answer.

**Policy adopted:** the pack must deliver **[nominal mission + one complete re-sweep + 4 minutes of loiter]** within an 80 % DoD, and hover endurance must be ≥ 2× mission duration.

This is a defensible engineering rule: it covers the realistic contingency (the first sweep misses survivors and the swarm re-searches) plus a genuine hold reserve, rather than an arbitrary percentage.

Solving the coupled problem (pack mass ↔ MTOW ↔ mission energy):

| Chemistry | Pack | MTOW | Fleet | Hover endurance | Mission |
|---|---|---|---|---|---|
| LiPo | 928 g (153 Wh) | 4.99 kg | 15.0 kg | 12.4 min | 7.7 min |
| **Li-ion** | 688 g (138 Wh) | 4.61 kg | 13.8 kg | 12.4 min | 7.7 min |

Rounded **up** to a buildable configuration — **6S2P of 21700 4500 mAh 45 A cells** (12 cells, 966 g, 194 Wh, 9.0 Ah) — because 12 cells is the natural pack and the extra 280 g buys endurance ratio 2.0× instead of 1.6×.

**Li-ion over LiPo** for this mission because: 21 % better pack-level specific energy; the C-rate demand is modest (8.2 C peak, and 21700 high-drain cells cover it); far better cycle life across a long test campaign; and safer storage in a student lab. The counter-argument — LiPo's superior burst and voltage sag behaviour — matters for aggressive flight, which this mission is not.

---

## 5. Mass statement (per aircraft)

| Item | Mass | % MTOW |
|---|---|---|
| Structure: frame, arms, landing gear, hardware | 1187 g | 23.5 % |
| Motors ×4 | 508 g | 10.1 % |
| ESCs ×4 | 178 g | 3.5 % |
| Propellers ×4 | 248 g | 4.9 % |
| Battery pack | 966 g | 19.1 % |
| Avionics + wiring harness | 925 g | 18.3 % |
| Payload magazine + release mechanism | 240 g | 4.8 % |
| Survivor kits, 4 × 200 g | 800 g | 15.8 % |
| **MTOW** | **5052 g** | 100 % |
| **Fleet of 3 (weigh-in figure)** | **15.16 kg** | |

**Avionics breakdown (925 g):** FC 45 g · GNSS primary RTK 35 g · GNSS secondary heading 35 g · Jetson Orin Nano + carrier 185 g · camera/lens/damped mount 130 g · 5.8 GHz mesh radio + 2 antennas 110 g · 868 MHz radio 30 g · RC safety receiver 20 g · power modules/BEC/PDB 85 g · wiring harness 190 g · buzzer/LEDs/switches/mounts 60 g.

**Growth allowance:** 8.84 kg to the 24.0 kg fleet target = **58 % build overweight tolerated**. Student builds routinely come in 10–20 % over CAD estimate; this design absorbs that without approaching the rule.

**Payload capacity:** 4 kits per aircraft × 3 = 12 kit capacity for a 10-survivor mission — 20 % spare, which covers a jammed release or a wasted drop on a false positive.

---

## 6. Propulsion and electrical

| Quantity | Value |
|---|---|
| Static thrust required at T/W = 2.0 | 99 N (10.1 kgf) total → **2.53 kgf per motor** |
| Motor class | ~5008/5010, 300–400 KV, 6S, 20 in prop |
| Hover thrust per motor | 1.26 kgf = **50 % of max** |
| Hover current | 27.8 A (3.1 C) |
| Peak current at T/W = 2 | **74 A** (8.2 C), 1601 W |
| Pack burst capability (2P × 45 A) | 90 A → **21 % margin** |
| ESC | 19 A peak per motor → specify **50–60 A** ESC (≥ 2.5× margin) |
| Main power leads | 74 A peak → **10 AWG**; motor leads 14 AWG |

The **50 % hover throttle point** is the number to check on any propulsion trade. Below ~40 % the motors are oversized (dead mass); above ~60 % you lose control authority and thermal margin. 50 % is the centre of the good band.

Note that `P ∝ T^1.5`, so full-thrust power (1601 W) is 2.7× hover power, not 2×. That factor drives ESC and wiring sizing, not battery energy.

---

## 7. Quadrotor vs hexacopter — redundancy trade

| Config | MTOW | Fleet | Hover P | Endurance | Disk loading | Fleet margin |
|---|---|---|---|---|---|---|
| **Quad 4 × 20 in** | 5.05 kg | 15.16 kg | 601 W | 15.4 min | 6.2 kg/m² | 9.84 kg |
| Hex 6 × 16 in | 5.25 kg* | 15.75 kg | 646 W | 14.4 min | 6.7 kg/m² | 9.25 kg |
| Hex 6 × 15 in | 5.25 kg* | 15.75 kg | 685 W | 13.5 min | 7.7 kg/m² | 9.25 kg |

*plus ~120 g for two additional arms and hardware, not captured by the scaling model.

A quadrotor **has no motor-out tolerance** — losing one rotor means losing yaw and roll authority and the aircraft comes down. A hexacopter degrades gracefully.

**Recommendation: build the quad, but treat this as an open decision reviewed at the P1 gate.** The mass budget can afford the hex (still >35 % fleet margin), and the reliability argument is real. The counter-argument is that fleet-level redundancy already exists — three aircraft, and the rules only require two — so a single aircraft loss is survivable at the *mission* level. If the rulebook penalises an in-flight loss heavily, or if the venue has crowds nearby, switch to hex. The cost is ~1 minute of endurance you do not need and ~600 g of fleet mass you have.

---

## 8. Camera and optics

**Baseline sensor:** 1/1.8 in, 4056 × 3040 (12.3 MP), 7.4 × 5.6 mm, 1.82 µm pitch, **f = 6.0 mm** → HFOV 63.3°, VFOV 50.0°.

| AGL | Swath | Along-track | GSD | Person (1.7 m) | Transects | Total track | Sweep/drone |
|---|---|---|---|---|---|---|---|
| 30 m | 37.0 m | 28.0 m | 0.91 cm | 186 px | 10 | 4000 m | 187 s |
| 40 m | 49.3 m | 37.3 m | 1.22 cm | 140 px | 8 | 3200 m | 149 s |
| 50 m | 61.7 m | 46.7 m | 1.52 cm | 112 px | 6 | 2400 m | 112 s |
| **60 m** | **74.0 m** | **56.0 m** | **1.82 cm** | **93 px** | **5** | **2000 m** | **93 s** |
| 70 m | 86.3 m | 65.3 m | 2.13 cm | 80 px | 5 | 2000 m | 93 s |
| 80 m | 98.7 m | 74.7 m | 2.43 cm | 70 px | 4 | 1600 m | 75 s |

*(10 ha as 400 × 250 m, 30 % sidelap, 3 drones, 8 m/s, ~6 s per 180° turn.)*

Aerial SAR targets in HERIDAL/SARD occupy roughly **0.1 % of frame area**, and CNN detectors need on the order of 20–30 px on target for reliable small-object recall. Every row above clears that by more than 2×.

**60 m selected.** Going from 60 m to 80 m saves 18 seconds of a 30-minute allowance and costs 25 % of the pixels on target. That is a bad trade. **Altitude is chosen for detection margin, because coverage is not the binding constraint.**

### 8.1 Motion blur and exposure

Translational smear = `v · t_exp / GSD`:

| Groundspeed | 1/500 s | 1/1000 s |
|---|---|---|
| 8 m/s | 0.88 px | 0.44 px |
| 12 m/s | 1.32 px ⚠ | 0.66 px |

Angular smear = `ω · t_exp / (HFOV/px_w)`, with an angular pixel scale of **15.6 mdeg/px**:

| Body rate | 1/500 s | 1/1000 s | 1/2000 s |
|---|---|---|---|
| 5 °/s | 0.64 px | 0.32 px | 0.16 px |
| 10 °/s | 1.28 px ⚠ | 0.64 px | 0.32 px |
| 20 °/s | 2.56 px ⚠ | 1.28 px ⚠ | 0.64 px |
| 45 °/s | 5.76 px ⚠ | 2.88 px ⚠ | 1.44 px ⚠ |

**Two rules follow:** shutter ≤ 1/1000 s (which in Indian daylight is trivially achievable — it drives ISO down, not up), and **gate detections on |body rate| < 15 °/s**. Suppress inference during turn arcs; the aircraft is banking, the ground plane assumption is worst there, and the imagery is smeared anyway. You lose nothing, because the turns are outside the search sub-region.

### 8.2 Capture and inference rate

Along-track footprint at 60 m is 56.0 m. For 80 % forward overlap at 8 m/s you need **0.71 Hz**. Running detection at **5 Hz** gives ~35 frames on every target per pass.

**This is the key perception insight: multi-frame fusion is free.** You get 35 independent looks at each survivor. Use them — for temporal confirmation (suppressing false positives) and for geolocation averaging.

**Tiling budget (SAHI-style, 640 px tiles, 20 % overlap):**

| Strategy | Tiles/frame | Inferences/s @5 Hz | Verdict |
|---|---|---|---|
| Full 4056 × 3040 | 48 | 240 | Far beyond an Orin Nano |
| 2× downsample (2028 × 1520, GSD 3.65 cm, person 47 px) | 12 | 60 | Still beyond at 5 Hz |
| 2× downsample @ 2 Hz | 12 | 24 | **Fits** (Orin Nano TensorRT FP16 YOLO ≈ 24–40 FPS) |
| 3 × 3 tile grid on a centre crop @ 5 Hz | 9 | 45 | Marginal — benchmark it |

**Recommendation: 2× downsample + full tiling at 2 Hz.** Even at 2 Hz you get ~14 frames per target per pass — still plenty for fusion. Benchmark the actual throughput on hardware in Phase 5 before freezing; published Orin Nano numbers vary from 24 FPS (P2-head models) to 41 FPS (YOLOv5n) at 640 × 640, and that spread changes the answer.

---

## 9. Coverage, timeline and wind

### 9.1 Mission energy budget (per aircraft)

| Segment | Time | Power | Energy |
|---|---|---|---|
| Arm, spin-up, sequenced launch queue | 45 s | 210 W | 2.6 Wh |
| Climb to 60 m @ 3 m/s | 20 s | 792 W | 4.4 Wh |
| Transit to sub-region (~120 m) | 10 s | 563 W | 1.6 Wh |
| Area sweep (667 m + turns) | 93 s | 563 W | 14.6 Wh |
| Delivery phase (3.3 drops) | 185 s | 552 W | 28.3 Wh |
| RTH transit (~250 m) | 21 s | 563 W | 3.3 Wh |
| Recovery hold, sequenced descent, land | 90 s | 601 W | 15.0 Wh |
| **TOTAL** | **464 s = 7.7 min** | | **69.8 Wh** |

Usable pack energy 155 Wh → mission consumes **45 %**, landing at ~64 % SoC.

**Where the time actually goes:** the delivery phase (185 s) and the recovery sequence (90 s) together are 59 % of the mission. The sweep everyone worries about is 20 %. Optimise deliveries and recovery, not the search.

Forward-flight power is modelled as 0.93 × hover — multirotor power has a shallow bucket around 8–12 m/s. This is an assumption to verify with logged flight data in Phase 6.

### 9.2 Wind

Airframe drag with a 0.075 m² frontal area, Cd 1.1:

| Airspeed | Drag | Tilt | Extra power |
|---|---|---|---|
| 8 m/s | 3.0 N | 3.5° | 31 W |
| 12 m/s | 6.8 N | 7.8° | 105 W |
| 15 m/s | 10.7 N | 12.2° | 206 W |
| 20 m/s | 19.0 N | 21.0° | 487 W |

Attitude authority is never the wind limit — tilt stays small and thrust demand rises only 2 % at 15 m/s.

**The right policy is constant *groundspeed*, letting airspeed vary.** If you instead hold airspeed, a 6 m/s wind more than doubles sweep time (191 s vs 83 s) because upwind transects crawl. Holding groundspeed:

| Wind | Upwind airspeed | Sweep time | Sweep energy |
|---|---|---|---|
| 0 m/s | 8 m/s | 83 s | 14.7 Wh |
| 4 m/s | 12 m/s | 83 s | 15.2 Wh |
| 6 m/s | 14 m/s | 83 s | 15.9 Wh |
| 8 m/s | 16 m/s | 83 s | 16.8 Wh |
| 10 m/s | 18 m/s | 83 s | 18.0 Wh |

Sweep time becomes wind-independent, and the cost is 22 % more sweep energy at 10 m/s wind — trivial against a 55 % energy reserve. **Constant groundspeed also keeps motion blur constant**, which matters for detection.

Where the sub-region shape allows, orient transects **perpendicular to the wind** (Coombes et al. show cross-wind sweeps beat along-wind for survey time in fixed-wing surveys; the same asymmetry applies here through turn handling).

---

## 10. Payload drop ballistics

**Kit:** 200 g, 200 × 100 × 50 mm. Tumbling reference area (mean of the three face areas) = 117 cm², Cd ≈ 1.05.

Terminal velocity `v_t = sqrt(2mg / (ρ Cd A))` = **16.2 m/s**; ballistic coefficient `m/(Cd·A)` = 16.3 kg/m².

Numerically integrated 2-D trajectory with quadratic drag:

| Release height | Fall time | Impact speed | Drift @ 0 wind | @ 3 m/s | @ 6 m/s |
|---|---|---|---|---|---|
| 4 m | 0.90 s | 8.2 m/s | 0 | 0.20 m | 0.60 m |
| **6 m** | **1.11 s** | **9.7 m/s** | **0** | **0.34 m** | **0.95 m** |
| 8 m | 1.28 s | 10.9 m/s | 0 | 0.49 m | 1.32 m |
| 10 m | 1.43 s | 11.7 m/s | 0 | 0.66 m | 1.72 m |
| 15 m | 1.75 s | 13.3 m/s | 0 | 1.14 m | 2.80 m |

**Sensitivity to release-state errors (6 m release, still air):**

| Error source | Magnitude | Miss contribution |
|---|---|---|
| Residual groundspeed 0.25 m/s | | 0.27 m |
| Residual groundspeed 0.50 m/s | | 0.53 m |
| Residual groundspeed 1.00 m/s | | 1.06 m |
| Residual groundspeed 2.00 m/s | | 2.10 m |
| Altitude error +1 m | | +3.9 cm |
| Altitude error +2 m | | +7.4 cm |

**Release velocity dominates, by an order of magnitude over altitude error.** This is exactly the conclusion of the fixed-wing airdrop literature (Mathisen et al., *Autonomous Robots* 2020, report ~3.4 m of miss per 1 m/s of release-velocity error at 50 m and 18 m/s, and ~0.4 m per metre of altitude error). A fixed-wing cannot null its groundspeed; **a multirotor can**, which removes the dominant error term outright.

**Design conclusions:**
- **Release altitude 6 m.** Low enough that wind drift is under 1 m even at 6 m/s, high enough for safe clearance above a person and above debris.
- **Groundspeed gate: release only below 0.3 m/s** → ≤ 0.32 m of ballistic miss.
- Total delivery error is `RSS(geotag error, position-hold error, ballistic dispersion)`. With RTK geotagging at ~1.3 m, position hold at ~0.5 m and ballistics at ~0.4 m, the RSS is **~1.5 m** — well inside a 5 m requirement. Without RTK, geotag error at ~3 m dominates and the RSS is **~3.1 m**.
- Impact speed 9.7 m/s: the kit must survive it, or be padded. Test this.
- **Do not release below 4 m** — rotor downwash at that height starts to influence a light box, which the ballistic model does not capture.

---

## 11. Geotag error budget

Ray–ground intersection at 60 m AGL, detection at the frame edge (worst case, 37 m off nadir), 20-frame fusion. Random terms scale as `1/√N`; **systematic terms do not**.

| Term | B: standard GNSS, calibrated | C: RTK + dual-antenna | C-strict: + surveyed ground plane |
|---|---|---|---|
| GNSS horizontal | 0.56 m | 0.01 m | 0.01 m |
| Attitude | 0.23 m | 0.07 m | 0.07 m |
| Pixel centroid | 0.02 m | 0.02 m | 0.02 m |
| Time sync | 0.04 m | 0.04 m | 0.04 m |
| EKF lag | 0.07 m | 0.07 m | 0.07 m |
| **Boresight residual** (systematic) | 0.31 m | 0.21 m | 0.16 m |
| **Ground-height assumption** (systematic) | **2.76 m** | **0.62 m** | 0.19 m |
| **Target extent / centroid** (systematic) | 0.50 m | 0.50 m | 0.50 m |
| **GNSS–camera lever arm** (systematic) | 0.10 m | 0.10 m | 0.10 m |
| **Unmodelled** (systematic) | 1.00 m | 1.00 m | 0.70 m |
| **RSS (1σ)** | **3.06 m** | **1.30 m** | **0.91 m** |
| CEP50 | 2.54 m | 1.08 m | 0.75 m |
| R95 | 5.29 m | 2.25 m | 1.57 m |

**Three findings:**

1. **The ground-height assumption is the dominant term without RTK** — 2.76 m, larger than the GNSS error itself, because a height error scales the projection ray by `(Δh/h)·r`, and `r` is 37 m at the frame edge. Fixing the ground plane (surveying the field elevation during setup, or applying a DEM) is cheaper than any other improvement.
2. **Systematic error does not average out.** Twenty frames reduce GNSS noise by 4.5×, but boresight misalignment, target-extent bias and terrain assumption survive untouched. **Calibrate first, then fuse** — the reverse order wastes the fusion.
3. **RTK converts a 3 m problem into a 1.3 m problem.** This is the strongest single argument for the local base station — and it is why clarification question 1 in the development plan matters. Note the base is ground equipment on a team-owned local link, not an external network, but get it confirmed.

**Design targets to state in the requirements:** geotag CEP50 ≤ 2.0 m with RTK, ≤ 3.5 m without. Published monocular UAV geolocation results sit at a few metres, dominated by GNSS and attitude, consistent with case B. **Do not promise sub-metre performance until you have measured it against surveyed markers.**

---

## 12. RF link budget

Free-space path loss `FSPL(dB) = 20log₁₀(d_km) + 20log₁₀(f_MHz) + 32.44`, plus 4 dB implementation/polarisation loss.

Worst-case slant range: field diagonal 472 m + GCS offset → **design to 600 m**.

**Configuration** (within India's delicensed 5.825–5.875 GHz drone allocation, 1 W / 30 dBm Tx, 4 W / 36 dBm EIRP): air node 24 dBm + 3 dBi dipole (27 dBm EIRP); GCS node 24 dBm + 9 dBi sector on a 2 m mast (33 dBm EIRP). Both legal.

| Range | FSPL | P_rx | Margin @ MCS3 (−85) | @ MCS5 (−80) | @ MCS7 (−74) |
|---|---|---|---|---|---|
| 200 m | 93.8 dB | −61.8 dBm | 23.2 dB | 18.2 dB | 12.2 dB |
| 400 m | 99.8 dB | −67.8 dBm | 17.2 dB | 12.2 dB | 6.2 dB |
| **600 m** | **103.3 dB** | **−71.3 dBm** | **13.7 dB** | 8.7 dB | 2.7 dB |
| 800 m | 105.8 dB | −73.8 dBm | 11.2 dB | 6.2 dB | 0.2 dB |

**868 MHz safety link** at 600 m: FSPL 86.8 dB, margin at LoRa SF7 (−120 dBm sensitivity) = **53 dB**. Effectively unbreakable inside the field. This is why abort and recall live on this link.

**Air-to-air** (two drones at 60 m AGL, 400 m apart): FSPL 99.8 dB with clean LOS and no ground clutter — the best link in the system. **Route through it when the ground link degrades.** That is the point of building a mesh rather than a star.

### 12.1 Data rate budget

| Stream (per drone) | Rate |
|---|---|
| MAVLink telemetry @ 10 Hz | 60 kbps |
| Swarm state / task consensus @ 5 Hz | 25 kbps |
| Detection metadata + thumbnails | 150 kbps |
| **Non-video subtotal** | **235 kbps** × 3 = 0.70 Mbps |
| One switched 720p30 H.265 video feed | 1800 kbps |
| **Total offered load** | **2.50 Mbps** |

**Design conclusion:** offered load is 2.5 Mbps against a link that delivers ≥26 Mbps at MCS3. **Trade rate for margin deliberately** — lock the mesh to a low MCS and a 10 MHz channel rather than letting it chase high rates. A slow link that never drops beats a fast one that renegotiates mid-mission. Do not stream three simultaneous video feeds: three 720p streams (5.4 Mbps) would still fit at MCS3 but destroy the margin you are buying.

---

## 13. Geometry, structure and CG

**Footprint.** 20 in prop with 30 mm tip clearance → 761 mm motor-to-motor diagonal, ~1.05 m overall square footprint. Three aircraft fit inside the 3.66 m launch box simultaneously (3 per row).

**But sequence the launches anyway.** At under one rotor diameter of separation, downwash interaction is a real upset risk during the transition to climb. The rules require you to launch from the box; they do not require you to launch simultaneously.

**Arm loading.** At T/W = 2, thrust per motor is 24.8 N at a 380 mm arm → root bending moment **9.4 N·m**. A 25 × 23 mm carbon tube (I ≈ 5438 mm⁴) sees ~22 MPa against ~600 MPa for UD carbon — a safety factor of ~28. **Bending is not the design driver.** Joint and clamp design, and vibration fatigue at the arm root, are. Design the clamps and run a vibration survey; do not spend effort on tube wall thickness.

**CG shift on release.** Dropping one 200 g kit from a magazine 50 mm off the centreline moves the CG by 1.98 mm and leaves a residual moment of 0.098 N·m — countered by ~26 g of differential thrust. Trivial in magnitude, **but it is a step change** that excites the attitude loop at exactly the moment you care about position accuracy.

Mitigations: mount the magazine on the CG axis; release from the centre of the stack outward rather than sequentially from one side; and hold position for 2 s after release before commanding the next waypoint. If the flight stack supports it, feed a mass-change event to the controller.

---

## 14. Avionics power and thermal

| Load | Power |
|---|---|
| Jetson Orin Nano, sustained inference | 18.0 W |
| Flight controller + 2 × GNSS | 4.5 W |
| Camera + ISP | 3.0 W |
| 5.8 GHz mesh radio (Tx duty) | 9.0 W |
| 868 MHz radio | 0.7 W |
| RC receiver | 0.5 W |
| Servos, idle/actuation average | 2.0 W |
| BEC / regulator losses (12 %) | 4.5 W |
| **Total** | **42.2 W** |

The energy model assumed 55 W — a 30 % margin over this bottom-up figure, which is the right direction.

**The worst thermal case is not flight — it is setup.** In flight, the compute bay sits in a several-m/s downwash column. During the 5-minute setup window the props are stopped, the Jetson is booting and loading a model at full load, and ambient may be 35 °C+ in direct sun. **Fit a small blower on the compute bay, active from power-on**, and verify the thermal case on the bench in Phase 5 with the props stopped.

---

## 15. Setup time budget — the binding constraint

C7 gives **300 seconds** from the mission file arriving to launch.

| Step | Duration | Serial cumulative |
|---|---|---|
| Aircraft out of case, battery in, power on (×3) | 60 s | 60 |
| FC boot + IMU/EKF init | 25 s | 85 |
| Companion boot (Linux + ROS 2 + model load) | 75 s | 160 |
| Mesh association, 3 nodes + GCS | 20 s | 180 |
| GNSS cold → 3D fix (cached almanac) | 45 s | 225 |
| RTK float → fix (base already surveyed and running) | 60 s | 285 |
| Payload magazines loaded and locked (×3) | 45 s | 330 |
| Mission file parsed, partitioned, rendered on GCS | 30 s | 360 |
| Pre-arm checks, operator confirm, arm | 20 s | 380 |

**Fully serial: 380 s — exceeds the window by 27 %.**

With two people and aggressive overlapping (boots, GNSS/RTK convergence and magazine loading in parallel): **~285 s, leaving 15 seconds of margin.**

**This is the tightest constraint in the entire system, by a wide margin.** Everything else has 25–55 % reserve; this has 5 %.

**Mitigations, in order of leverage:**
1. **Survey and start the RTK base before the window opens.** It is ground equipment, not an aircraft.
2. **Pre-build and cache the TensorRT engine.** Never JIT-compile at boot — that alone can cost 60+ s.
3. **Cache the GNSS almanac** for a hot start; saves 30–40 s over a true cold start.
4. **Ask the organisers whether power-on may precede the window** (clarification question 6). If yes, the whole problem evaporates.
5. **Rehearse it 20+ times.** The plan's P10 target of ≤ 3:30 is achievable but only through drilled choreography.
6. **Measure all of these numbers on real hardware in Phase 5.** They are engineering estimates, not data.

---

## 16. Assumption register — what must be replaced by measurement

| # | Assumption | Value | Sensitivity | Measure in |
|---|---|---|---|---|
| A1 | Rotor figure of merit | 0.60 | ±0.1 → ∓17 % hover power | P5/P6 thrust stand |
| A2 | Motor specific thrust | 195 N/kg | ±20 % → ±3 % MTOW | P1 (datasheets), P5 (test) |
| A3 | Structural mass fraction | 0.235 | ±0.05 → ±8 % MTOW | P6 (weigh the built frame) |
| A4 | Pack specific energy | 200 Wh/kg | ±15 % → ±15 % endurance | P5 (discharge test) |
| A5 | Motor + ESC efficiency | 0.78 combined | ±0.05 → ∓6 % endurance | P5 (power meter) |
| A6 | Cruise/hover power ratio | 0.93 | ±0.1 → ±7 % mission energy | P6 (flight logs) |
| A7 | Airframe drag area Cd·A | 0.083 m² | ±30 % → wind margin | P6 (log airspeed vs power) |
| A8 | Payload Cd, tumbling area | 1.05, 117 cm² | ±25 % → ±12 % drift | P5 (drop test from a rig) |
| A9 | Attitude accuracy | 0.3–1.0° | dominant in geotag case C | P7 (surveyed markers) |
| A10 | Orin Nano inference throughput | 24–40 FPS | changes tiling strategy | P5 (benchmark) |
| A11 | Cold-boot times | 25/75/45/60 s | dominant in setup budget | **P5 — highest priority** |
| A12 | Mesh sensitivity and real-world path loss | −85 dBm, FSPL + 4 dB | ±10 dB → range | P5 (field RF survey) |
| A13 | Detection recall at 60 m on real targets | ≥ 0.90 assumed | mission-critical | P7 (field campaign) |

**A11 is the highest-priority measurement in the programme**, because it is the only assumption with less than 10 % margin behind it.

---

## 17. Numbers to write into the requirement register

> **⚠ This section used to define its own SYS-xx numbers, which collided with the
> requirement register in
> [`../requirements/requirements-baseline.md`](../requirements/requirements-baseline.md)
> — the same IDs meant different things in the two documents. That register is now
> the single authority.** The IDs below are the canonical ones. Four requirements
> that once lived here have been overturned by the scoring structure and are
> listed in §8.1 of the baseline.

| ID | Requirement | Derived in |
|---|---|---|
| SYS-01 | Fleet AUW fully loaded ≤ 25.0 kg by rule; **≤ 24.0 kg internal target** (design 15.2 kg) | §2, §5 |
| SYS-04 | Thrust-to-weight ≥ 2.0 static at MTOW; hover throttle 45–55 % | §6 |
| SYS-06 | Peak current capability ≥ 90 A; ESC ≥ 50 A each; 10 AWG mains | §6 |
| SYS-14 | Hover endurance ≥ 15 min at MTOW; land with ≥ 25 % SoC | §4, §9.1 |
| SYS-44 | Search altitude held to ±5 m; GSD ≤ 2.0 cm/px ⚠ *altitude under review* | §8 |
| SYS-45 | Shutter ≤ 1/1000 s; inference gated at body rate < 15 °/s | §8.1 |
| SYS-46 | Detection at ≥ 2 Hz with ≥ 12 frames per target per pass | §8.2 |
| SYS-47 | Constant groundspeed 8 m/s during sweep, wind-compensated | §9.2 |
| SYS-48 | Boresight and lever-arm calibration before any accuracy claim | §11 |
| SYS-49 | Payload released at 6 m AGL | §10 |
| SYS-50 | Kit survives 9.7 m/s impact | §10 |
| SYS-51 | Link margin ≥ 13 dB at 600 m; offered load ≤ 3 Mbps | §12 |
| SYS-52 | Sequenced launch and recovery, one aircraft at a time through the box | §13 |
| SYS-53 | Compute bay forced-air cooling active from power-on | §14 |
| SYS-21 | Boot-to-launch ≤ 240 s (modelled 285 s — **requires optimisation**) | §15 |

**Superseded by scoring — do not build to these:** geotag CEP50 ≤ 2.0 m (now
0.75 m), delivery CEP ≤ 3 m (now ≥ 60 % within 2 m / ≥ 30 % within 1 m), one video
feed (now one per drone), mission ≤ 12 min (now ≤ 15 min for the bonus). See
baseline §8.1.

---

## 18. Sensitivity — what would change these answers

> **Three of these branches are now resolved.** This table was written before the
> rulebook was read; the outcomes are marked below. It called the delivery case
> correctly.

| If… | Then… | Outcome |
|---|---|---|
| Rulebook weights mission time heavily | Raise search altitude to 70–80 m, increase groundspeed to 12 m/s (shutter to 1/2000 s), consider drop-on-the-fly. Saves ~2 min; costs detection margin and drop accuracy. | ❌ **Did not happen.** Time is worth 50 points and is already won at 7.7 min against a 15 min threshold. Go the *other* way — lower and slower. |
| Rulebook weights delivery proximity heavily | Keep 6 m hover-and-drop, add RTK, and consider a winch or guided pod. Current design already targets ~1.5 m. | ✅ **Happened.** 200 points on tight zones (1/2/3 m). RTK is now committed and worth 82 delivery points. This row called it right. |
| RTK base is disallowed | Geotag degrades to ~3 m CEP. Compensate with a surveyed ground plane during setup (drops the dominant height term), longer dwell over each target, and a wider delivery tolerance assumption. | ✅ **Permitted** — but it may not be started before the setup window, which cost 175 s until mitigated. See `../requirements/rulebook-compliance.md` §6.7. |
| Survivors are under partial cover | Detection recall dominates everything. Lower altitude to 40–50 m, accept 149 s of sweep (still trivial), and consider a second oblique pass over low-confidence candidates. Budget allows both. | ⚠ **Targets are human-looking dummies**, posture and cover unspecified. The 40–50 m recommendation here is exactly what the scoring analysis independently reached. |
| Boundary polygon is long and thin (e.g. 800 × 125 m) | Transect count halves but each is longer; sweep time similar. Partitioning must handle high-aspect-ratio regions — this is exactly the adversarial-polygon unit test in P2. |
| Build comes in 20 % overweight | Fleet 18.2 kg, still 27 % under the cap. Endurance drops to ~13 min, still 1.7× the mission. **No redesign needed** — this is what the margin is for. |
| You switch to hexacopter | +0.2 kg per aircraft, −1 min endurance, +45 W hover power. All within margin. Buys motor-out tolerance. |

---

*Calculations performed with a first-order momentum-theory sizing model, numerical trajectory integration for ballistics, and RSS error propagation for geolocation. Methods and empirical coefficients sourced as cited. Preliminary design accuracy: ±10–15 % mass, ±20 % power. All figures to be re-baselined against measured data at the Phase 5 and Phase 6 gates.*
