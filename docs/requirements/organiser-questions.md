# Questions for the NIDAR Organising Team
### Team RescueSwarm · Track 1 · Mission 1

Ready to send. Four questions remain open; the answered ones are recorded at the
end so the thread stays self-contained. Each question states why it matters, so
the organisers can see it is a design question rather than a request for an
advantage.

---

## Q1 — How is "correctly geotagged" verified?

Scoring criterion 1 awards 25 marks for each survivor "correctly detected **and**
correctly geotagged on the GCS / mission map".

**Question:** is this verified by comparing the coordinates our GCS displays
against a surveyed truth position for each survivor, and if so, what horizontal
tolerance counts as correct? Or is it assessed by the marker appearing at the
right survivor on the map?

**Why it matters:** our RTK base station derives its own position from its first
GNSS fix, which carries roughly 1–2 m of absolute error. That error is *common
mode* — it shifts every aircraft equally — so it cancels completely for kit
delivery, where the kit lands on the true survivor regardless. It would **not**
cancel against a surveyed truth coordinate. The answer decides whether we need to
invest in an accurate absolute base position, which affects 250 points.

---

## Q2 — Is a recovery-parachute descent scored as an emergency landing or a crash?

We intend to fit each aircraft with a recovery parachute, as permitted.

**Question:** if a parachute deploys in flight and the aircraft descends under
canopy to a controlled landing outside the launch pad, is that scored as a
**landing outside the designated zone** (−10, or exempt as an organiser-approved
emergency landing), or as a **crash** (−50)?

**Why it matters:** the penalty table defines a crash as "uncontrolled ground
impact, collision resulting in loss of flight, or crash landing". A canopy descent
is arguably none of those. We would also note that a parachute physically cannot
land on the pad: at a typical 5 m/s descent rate, a canopy deployed at 60 m drifts
about 36 m in a 3 m/s breeze, against a 3.66 m pad. Staying inside the pad would
require deploying below about 3 m, which is below the altitude at which a canopy
can inflate. We are content to accept the landing-outside penalty; we would like to
know whether that is the correct reading.

---

## Q3 — Is motor-out tolerance separately required?

**Question:** is any specific tolerance to a single motor or ESC failure required,
beyond the failsafe list in rule 8.19? Would a configuration that cannot maintain
controlled flight after losing one motor fail the Pre-Flight Inspection?

**Why it matters:** it decides between a quadrotor and a hexacopter or octocopter
airframe. That is a frame-level decision we would rather make once, early, than
revisit after the frame is built.

---

## Q4 — Is prior site access available to survey the launch area?

**Question:** will teams have access to the competition site before the Final
Mission — for example on a practice or setup day — sufficient to survey the
position of the launch/landing area with our own equipment?

**Why it matters:** this is only relevant if the answer to **Q1** is that geotag
accuracy is judged against surveyed truth. In that case, knowing the pad's precise
coordinates in advance would let our RTK base start from an accurate absolute
position without consuming any of the 5-minute setup window. If Q1 is judged on
the map instead, Q4 does not matter and can be disregarded.

---

## Answers already received — recorded for the thread

| Question | Answer |
|---|---|
| Scoring weights across detection, delivery, autonomy, time | Rulebook §9 |
| One switched video feed, or all feeds simultaneously? | A live feed from **each** drone (rule 8.14) |
| Is delivery measured from the tagged position or the survivor? | **From the survivor**; ideally the kit lands on the survivor |
| Is a team-owned local RTK base station permitted? | **Yes** |
| May the RTK base be positioned and started before the setup window? | **No** — it must be set up inside the 5 minutes |
| Is pre-booting of onboard computers permitted? | **No** |
| Is there a maximum wind condition? | **No** — wind is natural, not induced |
| Is an aircraft recovery parachute permitted? | **Yes**, including pyrotechnic and CO₂ deployment, provided the aircraft lands on the pad |
| Boundary polygon format? | **KML file**, provided during the setup window |
| Will survivors be real people or dummies? | **Human-looking dummies** |

---

## If every answer comes back badly

A no-regrets analysis: assume the **worst** answer to each question, and take the
cheapest action now that makes the answer stop mattering. Three actions cover all
four questions, and none of them is wasted if the answers come back well.

### Q1 worst case — geotag judged against surveyed truth, tight tolerance

Our base takes its position from its first 3D fix: **~1.5 m absolute**. Total
absolute error is that compounded with the geotag budget itself (0.91 m):

| Base position from | Base abs | Total abs | Cost |
|---|---|---|---|
| First 3D fix *(current plan)* | ~1.5 m | **1.75 m** | free |
| 90 s survey-in | ~1.0 m | **1.35 m** | **free — see below** |
| 90 s survey-in + **GAGAN/SBAS** | ~0.7 m | **1.15 m** | free |
| Surveyed pad *(needs Q4)* | ~0.05 m | 0.91 m | needs site access |

**The floor is 0.91 m — the geotag error itself.** Survey-in plus GAGAN gets
within 27 % of that floor **without site access and without a network.**

**Action 1 — put a 90 s survey-in in the setup procedure.** Modelled in
[`setup-budget-output.txt`](../sizing/setup-budget-output.txt) case E: it costs
**zero launch time** (launch stays at 285 s calibrated) because launch is gated on
a 3D fix, not an RTK fix. It only pushes the RTK fix from 290 s to 375 s, so more
of the sweep is float-quality. That barely matters: float is 0.3–0.5 m relative
against a budget where the 0.70 m unmodelled and 0.50 m target-extent terms
dominate, and **tags can be re-fused once RTK fixes, before deliveries begin.**

**Action 2 — configure the base to use GAGAN.** ISRO's satellite augmentation is a
**broadcast signal received passively, exactly like GNSS itself** — not GSM, LTE,
Wi-Fi, internet or cloud, none of which rule 8.4 permits. It is also Indian, so it
helps the indigenisation score. *Worth confirming with the organisers that SBAS is
not read as an external network — but the same argument already applies to GNSS.*

### Q2 worst case — a canopy descent is scored as a crash (−50)

**Fit the parachute anyway.** The arithmetic is unchanged: crashing without a
canopy also costs −50, and you additionally lose the airframe and create a safety
event. Worst case, the chute is score-neutral and airframe-positive.

What the worst case *does* change is the trigger logic:

- Deploy **only** on unrecoverable conditions — attitude beyond 60° held for
  >0.5 s, or total thrust loss. Never on a recoverable fault.
- **Never** deploy for low battery, link loss or geofence breach. Those have
  powered responses, and a powered landing outside the pad costs −10 where a
  canopy might cost −50.
- Keep the below-20 m inhibit (SYS-41): below that it cannot inflate anyway.

A spurious deployment on a healthy aircraft is the only way this loses points that
would not otherwise be lost. Tune the trigger conservatively.

### Q3 worst case — motor-out tolerance is required, forcing a hex

This is the expensive one: 3–4 weeks of frame and propulsion rework against an
8-week flight window.

**Action 3 — cut the centre plate with both 4-arm and 6-arm bolt patterns.** It is
the same part with more holes: no extra material, no extra process step, perhaps
30–50 g. It converts "redesign the aircraft" into "bolt on two more arms". Do this
even though the quad is the decision.

**And order 18 motors and ESCs rather than 12.** Either they build three
hexacopters, or they are six spares for a quad fleet — and motors and ESCs are the
highest-failure-rate items in a flight-test programme. **They are not wasted in
either outcome**, and they carry a 3–4 week lead time that the flight window
cannot absorb twice.

### Q4 worst case — no site access at all

Fully covered by Action 1 and Action 2. Q4 only ever mattered as a route to a
better absolute position, and survey-in plus GAGAN gets most of the way there
independently. **If Q4 comes back "no", nothing changes.**

### Summary: three actions, no regrets

| # | Action | Cost if the answers are good |
|---|---|---|
| 1 | 90 s base survey-in in the setup procedure | None — zero launch time either way |
| 2 | Configure the base for GAGAN/SBAS | None — better absolute position regardless |
| 3 | Dual-pattern centre plate + order 18 motors/ESCs | ~40 g and six spare motors that get used anyway |

Taking all three now means **no answer can cost more than about a week**, and the
combined worst case — tight tolerance, no site access, hex required, canopy scored
as a crash — degrades geotag absolute accuracy from 0.91 m to 1.15 m and adds
roughly a week of assembly. That is a survivable outcome from the worst branch of
every question.

---

## Notes on questions we are *not* asking

Recorded so the team does not re-raise them:

- **Whether we may pre-boot anything airborne.** Answered: no. We are not asking
  again, and Q4 explicitly concerns ground equipment only.
- **Whether the kit may be parachuted.** We do not intend to. A canopy would drift
  4 m or more in light wind, against a free-fall drift of 0.34 m from 6 m. The
  organisers' warning on this matches our own analysis.
- **A maximum wind figure.** Answered: none. We are designing for 10 m/s
  penetration rather than asking for a limit.
