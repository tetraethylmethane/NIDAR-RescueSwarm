<h1 align="center">NIDAR RescueSwarm</h1>

<p align="center">
  Three autonomous drones that search a flood zone, find survivors, geotag them,<br>
  and drop medical kits — with no network, no pilot, and one operator who only presses start.
</p>

<p align="center">
  <b>NIDAR 2026–27 · Track 1 · Mission 1</b><br>
  <sub>MeitY · Drone Federation of India · SwaYaan</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/phase-P0%20requirements-blue" alt="phase">
  <img src="https://img.shields.io/badge/fleet-3%20aircraft-informational" alt="fleet">
  <img src="https://img.shields.io/badge/mass-15.2%20%2F%2025%20kg-success" alt="mass">
  <img src="https://img.shields.io/badge/mission-7.7%20%2F%2030%20min-success" alt="mission">
  <img src="https://img.shields.io/badge/finals-Jan%202027-critical" alt="finals">
</p>

<p align="center">
  <a href="#1-status">Status</a> ·
  <a href="#2-design-point">Design point</a> ·
  <a href="#3-scoring">Scoring</a> ·
  <a href="#4-decisions">Decisions</a> ·
  <a href="#5-open-risks">Risks</a> ·
  <a href="#6-open-questions">Questions</a> ·
  <a href="#7-repository">Repo</a>
</p>

---

## 1. Status

**Phase 0 — requirements.** The system is sized end to end and the requirements are baselined against the rulebook. No flight code exists yet.

Everything after "start" is autonomous. The operator loads the mission file, presses start, and can abort or recall. Nothing else — anything more costs 50 points a time.

### 1.1 Immediate actions

| # | Action | Deadline | Why it's first |
|:--|:--|:--|:--|
| 1 | **Register the team** | 2nd week Aug 2026 | Hard disqualification. Nothing else matters if this slips. |
| 2 | Send the remaining organiser questions | This week | They have external latency; nothing else on this list does. |
| 3 | Start collecting recall data | P1 | The long pole, worth 250 points, with irreducible calendar cost. |
| 4 | Bench the cold-boot timing | P1 | The only constraint under 20 % margin — and still modelled, not measured. |

### 1.2 Calendar

| Milestone | When | Notes |
|:--|:--|:--|
| Registration deadline | 2nd week Aug 2026 | INR 5,000 · approval letter · ID proofs |
| Progress Review 1 | 2nd week Oct 2026 | Attendance mandatory |
| Progress Review 2 | 2nd week Dec 2026 | Attendance mandatory |
| **Finals** | **January 2027** | Design review · business strategy · pre-flight · mission |

About 22 weeks from registration. The original 30-week plan overran it by eight, so the schedule has been re-baselined — see [schedule baseline](docs/schedule-baseline.md).

---

## 2. Design point

Not targets. These are outputs of a closed model in [`tools/sizing-model/`](tools/sizing-model/). **If a document disagrees with the model, the document is wrong.**

### 2.1 Aircraft

| Parameter | Value |
|:--|:--|
| Configuration | 3 identical quadrotors · 20 in props · 6S2P 21700 Li-ion |
| MTOW | 5.05 kg per aircraft |
| Fleet all-up weight | **15.2 kg** against a 25 kg cap — 39 % margin |
| Battery | 12 cells · 966 g · 194 Wh |
| Hover power | 601 W · disk loading 6.2 kg/m² |
| Hover endurance | 15.5 min at 80 % DoD |
| Thrust-to-weight | 2.0 static · hover at 50 % of max thrust |

### 2.2 Mission

| Parameter | Value |
|:--|:--|
| Design mission | **7.7 min** of a 30 min allowance |
| Search altitude / speed | 60 m AGL at 8 m/s groundspeed |
| Sweep time | 93 s per drone, 10 ha across 3 drones |
| Ground sample distance | 1.82 cm/px — a person is ~93 px long |
| Link margin | ≥ 13 dB at 600 m · 2.5 Mbps offered load |

> **Under review.** 40 m is recommended over 60 m — 140 px on a person instead of 93, for 2.5 min of a 15 min allowance. Pending recall measurement in P7. See [configuration trade](docs/sizing/configuration-trade.md) §5.3.

### 2.3 Accuracy

| Parameter | Target | Derived from |
|:--|:--|:--|
| Geotag | CEP50 ≤ 0.75 m with RTK | Scoring — see §3 |
| Delivery | ≥ 60 % within 2 m, ≥ 30 % within 1 m of the survivor | Scoring — see §3 |

---

## 3. Scoring

**1000 points total:** 600 flight · 200 design review · 200 business strategy. Reading the scoring properly moved the design more than any engineering analysis did.

### 3.1 Flight — 600 points

| Criterion | Points | Detail |
|:--|--:|:--|
| Survivor detection + geotagging | **250** | 25 each, max 10 survivors |
| Kit delivery accuracy | **200** | ≤1 m: 20/drop · ≤2 m: 14 · ≤3 m: 8 |
| Multi-drone collaboration | 50 | Binary |
| Single GCS interface | 50 | Binary |
| Finish inside 15 min | 50 | Binary |

| Penalty | Cost |
|:--|--:|
| Manual input or reset | −50 each |
| Crash | −50 each |
| Geofence breach | −20 each |
| Landing outside the box | −10 per drone |

<sub>Penalties capped at 150, except safety-critical violations.</sub>

### 3.2 What that changed

| Finding | Consequence |
|:--|:--|
| **Geolocation gates 450 of 600 points**, not 250 | Kits are scored from the survivor, so a drop is never better than the tag it aimed at. Geotag error is 75–83 % of the delivery budget. RTK alone is worth 82 delivery points. |
| **We were designing to the worst zone** | The old ≤3 m target scored 8 of 20 per drop. The old requirement — "90 % within 5 m" — sat outside every zone and would have scored nothing. |
| **Speed is worth 50 points and is already won** | The bonus needs 15 min; we fly 7.7. Time is the one surplus resource, so spend it on recall — fly lower, take more looks — rather than saving it. |

Full breakdown in [rulebook compliance](docs/requirements/rulebook-compliance.md).

---

## 4. Decisions

| Decision | Outcome | Reasoning |
|:--|:--|:--|
| Coaxial X8? | **Rejected** | Sized properly it costs +61–84 % hover power and +26–34 % fleet mass, buys no footprint back (stacking rotors doesn't shorten arms), and has the worst attitude bandwidth of anything tested. |
| Rotor count | **Stay quad** | Hex and octo both win on paper, but setup is the only tight constraint and extra arms land straight on it. |
| Prop diameter | **18 in, provisional** | Less rotor inertia, lower gust sensitivity. Design arms for 16–20 in and settle it on a bench in P5. |
| Thrust-to-weight | **Keep 2.0** | Tilt only reaches 12° at 15 m/s — attitude authority is never the wind limit. |
| Motor-out redundancy | **Parachute, not rotors** | Covers more failure modes and adds nothing to unfold. |

Reasoning and numbers in [configuration trade](docs/sizing/configuration-trade.md).

---

## 5. Open risks

| Risk | Detail | Status |
|:--|:--|:--|
| **Setup margin** | 15 seconds against a 5-minute rule — and modelled, not measured | Bench test in P1 |
| **VRS on every delivery** | The 2.5 m/s descent sits at 0.48 v_i, on the vortex-ring onset boundary, and a nulled-groundspeed descent is exactly what triggers it | Fix in the flight profile, not the airframe |
| **Wind cliff at 8 m/s** | Search groundspeed is 8 m/s, so at that windspeed the aircraft can't make headway at all | No requirement forbids it yet |
| **Business strategy** | 200 points, barely started — sponsorship evidence can't be produced in the final week | Start now |

---

## 6. Open questions

For the organisers, in priority order:

| # | Question | Why it matters |
|:--|:--|:--|
| 1 | What point on the survivor is the delivery datum? | A prone adult is 1.7 m long, so head vs torso differs by up to 0.85 m against a 1 m Zone A. Worth ~18 points, free to fix if known. |
| 2 | May the RTK base be surveyed and started before the setup window? | It's ground equipment, and setup has 15 s of margin. |
| 3 | Is pre-booting the onboard computers allowed? | Same 15 s of margin. |
| 4 | Real people, dummies, or both — in what postures and cover? | Drives the training dataset. |
| 5 | Boundary polygon format and shape? | Drives the mission-file parser. |
| 6 | Is a ballistic parachute permitted? Is motor-out tolerance separately required? | Decides the redundancy mechanism. |
| 7 | Is there a maximum wind the mission runs in? | Decides whether the 8 m/s cliff matters. |

**Already answered:** delivery is measured from the survivor · a local RTK base is permitted · scoring weights (§3) · every drone needs its own live feed.

---

## 7. Repository

### 7.1 Layout

```text
docs/
  system-overview.md        how the system actually works
  schedule-baseline.md      re-baselined against the real calendar
  requirements/             requirements baseline + rulebook compliance
  business/                 phase 4B strategy + cost sheet
  sizing/                   calculations, trades, committed model outputs
tools/sizing-model/         the model everything traces back to
hardware/bom/               Indian BOM + indigenisation scorecard
```

Everything else in the tree — `firmware/`, `autonomy/`, `perception/`, `communication/`, `ground-station/`, `simulations/` — is planned, not written.

### 7.2 Running the model

```bash
pip install -r tools/sizing-model/requirements.txt

python3 tools/sizing-model/rescueswarm_sizing_model.py   # the design point
python3 tools/sizing-model/config_trade.py               # quad vs hex vs coaxial
python3 tools/sizing-model/delivery_accuracy.py          # sets geotag + drop targets
python3 tools/sizing-model/mission_profile.py            # altitude, geotag error, downlink
```

Outputs are committed beside each script in [`docs/sizing/`](docs/sizing/).

> **Change the model, re-run it, and commit the new output in the same commit.** Every number in this README traces back to those files.

### 7.3 Further reading

| Document | What's in it |
|:--|:--|
| [System overview](docs/system-overview.md) | Mission flow, architecture, methods, perception, indigenisation, failsafes |
| [Requirements baseline](docs/requirements/requirements-baseline.md) | Every SYS-xx requirement, traced to a rule and a verification method |
| [Rulebook compliance](docs/requirements/rulebook-compliance.md) | Rule-by-rule matrix, scoring structure, conflicts |
| [Schedule baseline](docs/schedule-baseline.md) | Phases against the real calendar |
| [Sizing calculations](docs/sizing/sizing-calculations.md) | The full engineering derivation |
| [Configuration trade](docs/sizing/configuration-trade.md) | Quad vs hex vs coaxial, flight dynamics, constraint review |
| [Business strategy](docs/business/README.md) | Phase 4B structure and cost sheet |

---

<p align="center">
  <sub>Built for NIDAR 2026–27 · MeitY · Drone Federation of India</sub>
</p>
