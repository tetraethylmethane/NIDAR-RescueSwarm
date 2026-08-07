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

## Notes on questions we are *not* asking

Recorded so the team does not re-raise them:

- **Whether we may pre-boot anything airborne.** Answered: no. We are not asking
  again, and Q4 explicitly concerns ground equipment only.
- **Whether the kit may be parachuted.** We do not intend to. A canopy would drift
  4 m or more in light wind, against a free-fall drift of 0.34 m from 6 m. The
  organisers' warning on this matches our own analysis.
- **A maximum wind figure.** Answered: none. We are designing for 10 m/s
  penetration rather than asking for a limit.
