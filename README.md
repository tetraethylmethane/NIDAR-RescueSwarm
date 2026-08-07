# NIDAR RescueSwarm

Three autonomous drones that search a flood zone, find survivors, geotag them, and drop medical kits — with no network, no pilot, and one operator who only ever presses start.

<p align="center">
  <b>NIDAR 2026–27 · Track 1 · Mission 1</b><br>
  MeitY · Drone Federation of India · SwaYaan
</p>

<p align="center">
  <img src="https://img.shields.io/badge/fleet-3%20aircraft-informational" alt="fleet">
  <img src="https://img.shields.io/badge/fleet%20mass-15.2%20%2F%2025%20kg-success" alt="mass">
  <img src="https://img.shields.io/badge/mission-7.7%20%2F%2030%20min-success" alt="mission">
  <img src="https://img.shields.io/badge/indigenous-95.5%25%20suppliers-orange" alt="indigenisation">
  <img src="https://img.shields.io/badge/phase-P0%20requirements-blue" alt="phase">
</p>

Everything after "start" is autonomous. The operator loads the mission file, presses start, and can abort or recall. Nothing else — anything more costs 50 points a time.

---

## Where things stand

**Phase 0.** The system is sized end-to-end and the requirements are baselined against the rulebook. No flight code exists yet. Finals are **January 2027**, which is about 22 weeks out, so the schedule is tight and the plan has been re-baselined to match.

**Next four things**, in order of deadline pressure:

1. **Register** — the deadline is the 2nd week of August 2026. Nothing else matters if this slips.
2. **Send the remaining organiser questions** — they have external latency; everything else doesn't.
3. **Start collecting recall data** — it's the long pole and worth 250 points.
4. **Bench the cold-boot timing** — the only constraint under 20 % margin, and it's still modelled rather than measured.

---

## The design point

Not targets. These are outputs of a closed model in [`tools/sizing-model/`](tools/sizing-model/) — if a document disagrees with the model, the document is wrong.

| | |
|---|---|
| Fleet | 3 identical quadrotors, 20 in props, 6S2P 21700 Li-ion |
| MTOW · fleet | 5.05 kg · **15.2 kg** against a 25 kg cap (39 % margin) |
| Battery | 12 cells, 966 g, 194 Wh |
| Hover | 601 W · 15.5 min endurance · disk loading 6.2 kg/m² |
| Design mission | **7.7 min** of a 30 min allowance |
| Search | 60 m AGL at 8 m/s groundspeed → 93 s sweep per drone |
| Geotag | CEP50 ≤ 0.75 m with RTK |
| Delivery | ≥ 60 % within 2 m, ≥ 30 % within 1 m of the survivor |
| Link | ≥ 13 dB margin at 600 m, 2.5 Mbps offered |

Search altitude is under review — 40 m is recommended, pending recall measurements. See [configuration trade](docs/sizing/configuration-trade.md) §5.3.

---

## How it scores, and what that changed

1000 points total: **600 flight**, 200 design review, 200 business strategy. Reading the scoring properly moved the design more than any engineering analysis did.

| Flight criterion | Points |
|---|---|
| Survivor detection + geotagging | **250** (25 each, max 10) |
| Kit delivery accuracy | **200** — ≤1 m: 20/drop · ≤2 m: 14 · ≤3 m: 8 |
| Multi-drone collaboration | 50 |
| Single GCS interface | 50 |
| Finish inside 15 min | 50 |

Penalties: manual input −50 each · crash −50 · geofence −20 · landing outside the box −10. Capped at 150.

Three things fall out of this:

- **Geolocation gates 450 of the 600 points**, not 250. Kits are scored from the survivor, so a drop is never better than the tag it aimed at. Geotag error is 75–83 % of the delivery error budget. RTK alone is worth 82 delivery points.
- **We were designing to the worst zone.** The old ≤3 m delivery target scored 8 points a drop out of 20, and the old requirement — "90 % within 5 m" — sat outside every scoring zone and would have scored nothing.
- **Speed is worth 50 points and we've already won it.** The bonus needs 15 minutes; we fly 7.7. Time is the one resource in surplus, so it should be spent on recall — flying lower, taking more looks — not saved.

Full breakdown in [rulebook compliance](docs/requirements/rulebook-compliance.md).

---

## Decisions made

- **Quadrotor, not coaxial.** Sized properly, an X8 costs +61–84 % hover power and +26–34 % fleet mass and buys no footprint back, because stacking rotors doesn't shorten the arms. It also has the worst attitude bandwidth of anything tested. [Why](docs/sizing/configuration-trade.md)
- **Stay at four arms.** Hex and octo both win on paper, but setup is the only tight constraint and extra arms land straight on it.
- **18 in props, provisionally.** Less rotor inertia and lower gust sensitivity. Design the arms for 16–20 in and settle it on a bench in P5.
- **Thrust-to-weight stays 2.0.** Tilt only reaches 12° at 15 m/s, so attitude authority is never the wind limit.
- **Redundancy from a parachute, not rotors.** Covers more failure modes, adds nothing to unfold.

---

## Known problems

- **Setup has 15 seconds of margin** against a 5-minute rule, and the number is modelled, not measured.
- **VRS on every delivery.** The 2.5 m/s descent sits at 0.48 v_i, right on the vortex-ring onset boundary, and a nulled-groundspeed descent is exactly the condition that triggers it. Fixed in the flight profile, not the airframe.
- **8 m/s of wind stops the mission.** Search groundspeed is 8 m/s, so at that windspeed the aircraft can't make headway at all. No requirement currently forbids it.
- **Business strategy is 200 points** and barely started. Sponsorship evidence can't be produced in the final week.

---

## Open questions for the organisers

1. **What point on the survivor is the delivery datum?** A prone adult is 1.7 m long, so head vs torso differs by up to 0.85 m against a 1 m Zone A. Worth ~18 points and free to fix if we know.
2. May the **RTK base be surveyed and started before** the setup window opens, as ground equipment?
3. Is **pre-booting** the onboard computers allowed before the window?
4. Will survivors be **real people, dummies, or both** — and in what postures and cover?
5. Boundary polygon **format and shape**?
6. Is a **ballistic parachute** permitted, and is motor-out tolerance separately required?
7. Is there a **maximum wind** the mission runs in?

Answered so far: delivery is measured from the survivor · a local RTK base is permitted · scoring weights (above) · every drone needs its own live feed.

---

## Repo

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

```bash
pip install -r tools/sizing-model/requirements.txt

python3 tools/sizing-model/rescueswarm_sizing_model.py   # the design point
python3 tools/sizing-model/config_trade.py               # quad vs hex vs coaxial
python3 tools/sizing-model/delivery_accuracy.py          # sets the geotag/drop targets
python3 tools/sizing-model/mission_profile.py            # altitude, geotag error, downlink
```

Outputs are committed alongside each script in [`docs/sizing/`](docs/sizing/). **Change the model, re-run it, commit the new output in the same commit.**

---

## Where to read more

[System overview](docs/system-overview.md) · [requirements](docs/requirements/requirements-baseline.md) · [rulebook compliance](docs/requirements/rulebook-compliance.md) · [schedule](docs/schedule-baseline.md) · [sizing calculations](docs/sizing/sizing-calculations.md) · [configuration trade](docs/sizing/configuration-trade.md) · [business strategy](docs/business/README.md)

<p align="center">
  <sub>Built for NIDAR 2026–27 · MeitY · Drone Federation of India</sub>
</p>
