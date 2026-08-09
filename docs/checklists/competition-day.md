# Competition day — ground station

How the GCS is actually operated on the day, in order.

**Status: DRAFT, never rehearsed.** Every individual step below has been run;
the sequence has not been run end to end by a person against a clock. The P1
bench test is what turns this from a plan into a procedure. Two items in §0 are
open blockers, not paperwork.

**Crew: 2.** One on the aircraft, one on the GCS. The setup budget assumes
exactly this and queues manual work on two pairs of hands.

---

## 0. Blockers — resolve before this checklist is usable

| Blocker | Why it stops you |
|---|---|
| ~~No mission-mode launcher~~ | **Fixed.** `scripts/run-mission.sh` in NIDAR-GSC starts the mission build and refuses to hand over unless `mission_mode` is true and `/uav/commands/insert` answers 403. Do **not** use `run-gs.sh` — it is the dev launcher and registers 31 command routes, each a −50 under rule 8.16. |
| **No 868 MHz safety radio** | `/api/safety/status` reports `NO_RADIO` and abort returns 503. Rule 8.19 needs abort and recall to work. The RC-channel path (`RC7/RC8/RC9`) is independent of the GCS and does work, but it is the safety pilot's, not the operator's. |
| **`mission_backend` has drifted** between this repo and NIDAR-GSC — the flying copy is not the tested copy. See [HANDOFF](../../HANDOFF.md) §4.2b. |

---

## 1. The night before

- [ ] **Pre-cache map tiles for the venue.** With no network the map is blank —
      no boundary, no survivors, no aircraft, and the 250-point geotag evidence
      path is a white rectangle.
      ```sh
      python server/utils/slippy_map_getter.py --center LAT,LON --radius-km 10 --zoom 10-18
      python server/utils/slippy_map_getter.py --verify        # must pass, not "look fine"
      ```
- [ ] **Charge and log every pack.** 18 cells per aircraft, 54 for the fleet.
- [ ] **Flash and verify the parameter files**, then read them back off each
      aircraft rather than trusting the upload:
      ```sh
      cd firmware/ardupilot-params && python params.py --drones 3 --out .
      ```
      Confirm on the vehicle: `BATT_FS_LOW_ACT=2`, `BATT_LOW_MAH=2700`,
      `FENCE_ENABLE=1`, `RTL_ALT` 2500/3000/3500 cm, `RTL_LOIT_TIME`
      0/20000/40000 ms, `SYSID_THISMAV` 1/2/3.
- [ ] **Confirm the GCS laptop boots the mission build**, offline, from cold.

---

## 2. Before the window opens

- [ ] Laptop **off the network entirely** — Wi-Fi hardware-off, no tethering.
      Rule 8.4. `scripts/check-no-network.sh` is the guard; run it.
- [ ] Start `mavlink-router` on the committed config. Aircraft connect **to**
      it on 14541/14542/14543; it fans them onto **one** port, 14550, which is
      what rule 8.13 wants.
      ```sh
      mavlink-routerd -c scripts/mavlink-router.conf
      ```
- [ ] Start the GCS **in mission mode**:
      ```sh
      ./scripts/run-mission.sh          # NOT run-gs.sh, which is the dev build
      ```
      It refuses to start if the machine can reach the internet, if the tile
      cache is empty, or if the build that comes up is not mission mode.
- [ ] `run-mission.sh` has already asserted `mission_mode: true` and
      `/uav/commands/insert -> 403`. Confirm by eye what it cannot: the map
      renders with the network down, and three aircraft appear once powered.
- [ ] Load the organisers' KML boundary and generate the missions. Under 30 s
      (SYS-38); it is pure geometry with no I/O.

---

## 3. Inside the 5-minute window

Budget case **D** — RTK converges in flight. Calibrated estimate **285 s against
300 s**, so about 15 s of real margin. Nothing in the rules requires an RTK fix
at launch.

| t | Who | Action |
|--:|:--|:--|
| 0 s | both | Aircraft out, arms deployed. Up to ~20 s per aircraft is free — it hides behind the boot |
| — | — | **Place each aircraft on its own pad CORNER**, drone 1/2/3 to slot 1/2/3 |
| ~30 s | A | Power aircraft; boots, GNSS and RTK run automatically from here |
| ~60 s | B | RTK base down and running; corrections flowing |
| ~90 s | B | Upload one mission per aircraft; confirm 3/3 accepted |
| ~150 s | B | Confirm on the GCS: 3 heartbeats, 3 distinct SYSIDs, batteries, GNSS fix |
| ~185 s | B | **Arm and start.** From here the operator touches nothing but abort or recall |

**Arm each aircraft on its own slot.** ArduPilot takes HOME from the arming
position and RTL returns there regardless of what mission item 0 says. Arm one
on the wrong corner and it will come home to the wrong corner.

---

## 4. What to expect, so nothing looks like a fault

- **Launches are staggered 0 / 15 / 30 s.** Drone 3 sitting still for half a
  minute is `NAV_DELAY` working, not a hung aircraft.
- **Each drone climbs to its own transit altitude** — 20 / 25 / 30 m — flies to
  its strip, then climbs to the 40 m search deck.
- **Each strip is swept twice**, the second pass on the reverse heading.
- **Recovery is sequenced**: they hold at 25 / 30 / 35 m and descend one at a
  time, `RTL_LOIT_TIME` 0 / 20 / 40 s. The last aircraft waiting 40 s over the
  pad is correct behaviour and costs ~3.5 % of the pack.
- **Low battery returns them home by itself** at 20 % remaining. Verified in
  SITL at 10 809 mAh of a 10 800 mAh trip.

---

## 5. The only three things the operator may do

| Action | Cost |
|---|---|
| Press start | 0 |
| Abort | 0 — permitted by 8.16, required by 8.19 |
| Recall | 0 |
| **Anything else** | **−50 each**, and the mission build has no route for it by construction |

If something looks wrong, the choice is abort or let it run. There is no
mid-mission fix, and reaching for one costs more than the failure usually does.

---

## 6. After the flight

- [ ] Pull the `.bin` logs from `mavlink-router`'s log directory — rule 8.6
      lets the jury inspect them.
- [ ] Export the survivor list and geotags; that display **is** the evidence for
      the 250 detection points.
- [ ] Photograph the pad before moving anything, if a landing is contested.

---

## Open questions that change this procedure

Answers pending from the organisers — see
[organiser-questions.md](../requirements/organiser-questions.md):

1. **How "correctly geotagged" is verified.** If it is against surveyed truth,
   the base needs a real survey-in and §3 shifts from case D to case E.
2. **Whether the pad can be surveyed beforehand**, which is worth ~0.4 m of
   geotag budget.
