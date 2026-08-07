# RescueSwarm — Schedule Baseline
### Re-baselined against the NIDAR 2026–27 competition calendar

**Why this document exists.** [`development-plan.md`](development-plan.md) runs a
30-week programme in abstract week numbers. The competition calendar
(rulebook §5.2) puts the finals in **January 2027**, roughly **22 weeks** from
the August 2026 registration deadline. **The plan is about 8 weeks longer than
the competition allows**, and it does not acknowledge the two mandatory interim
reviews. This document re-baselines against real dates. Where it disagrees with
`development-plan.md`, this document governs.

---

## 1. Fixed external dates

| Date | Event | Consequence of missing it |
|---|---|---|
| **2nd week Aug 2026** | **Registration deadline** — INR 5,000, institution approval letter, team details with Govt + College ID, payment proof | **Disqualification (5.1)** |
| 3rd week Aug 2026 | Verification | — |
| 3rd week Sept 2026 | Online presentation & shortlisting — M1 teams auto-shortlisted (4.12) | Not a filter for us |
| **2nd week Oct 2026** | **Progress Review 1** — attendance mandatory (4.14) | Non-eliminating (4.16), but attendance is required |
| **2nd week Dec 2026** | **Progress Review 2** — attendance mandatory | As above |
| **January 2027** | **Finals: 4A Design Review · 4B Business Strategy · 4C Pre-Flight Inspection · 4D Final Mission** | — |

Assume the **first week of January 2027** for finals planning. That is the
conservative reading and costs nothing if the event lands later.

---

## 2. Re-baselined phases

Weeks are counted from **10 August 2026**. Finals at week ~21 (early Jan 2027).

| Phase | Milestone | Gate criterion | Week | Calendar |
|---|---|---|---|---|
| **P0** | Registration + requirements baselined | Fee paid, docs submitted; every rule clause maps to a testable requirement | **0–1** | **Aug 2026 — now** |
| P1 | Architecture frozen | ICDs agreed, **long-lead items ordered** | 2–4 | Aug–Sep 2026 |
| P2 | Design complete | Software and electronics pass internal review | 5–7 | Sep 2026 |
| **P3** | **Progress Review 1** | Architecture + sizing presented; bench hardware powered | **8–9** | **Oct 2026** |
| P4 | Simulation validated | ≥95 % completion over 200 Monte Carlo runs | 9–11 | Oct 2026 |
| P5 | Bench prototype | **Cold-boot < 240 s measured**, RF and payload validated | 11–12 | Oct–Nov 2026 |
| P6 | First autonomous flight | Stable auto waypoint flight, failsafes demonstrated | 13–15 | Nov 2026 |
| **P7** | **Perception validated** | Recall ≥ 0.90, geotag CEP50 ≤ 0.75 m | **12–17** *(parallel)* | Nov–Dec 2026 |
| **P8** | **Progress Review 2** + single-drone mission | 5 consecutive autonomous end-to-end missions | **17–18** | **Dec 2026** |
| P9 | Swarm operational | 3 consecutive 3-drone 10 ha missions | 18–20 | Dec 2026 |
| P10 | Competition ready | 13/15 repeatability, setup ≤ 240 s, **mock Pre-Flight Inspection passed**, config frozen | 20–21 | Dec 2026 – Jan 2027 |

**Buffer is one week, not three.** That is the honest consequence of a 22-week
calendar. Buffer must be protected by cutting scope, not by compressing P7.

---

## 3. What the compression costs

The 30-week plan is not compressible uniformly. Three things must give:

**(a) Perception starts immediately, not at week 6.** P7 is the long pole and is
worth 250 points. Field data collection must begin in **P1**, in parallel with
architecture, using any camera at the right altitude — mannequins in a field
do not require a finished aircraft. This is the single highest-value schedule
change.

**(b) Long-lead procurement moves into P1.** A 22-week programme cannot absorb a
6-week import lead time discovered in week 12. The Indian-supplier strategy
helps here and should be treated as a schedule decision as much as an
indigenisation one.

**(c) Monte Carlo and fault injection shrink.** 200 runs at ~2 h is fine; the
campaign should run unattended overnight from P4 onward rather than being a
discrete phase.

---

## 4. Milestones that did not exist in the old plan

| Milestone | Why it is new |
|---|---|
| **Registration (P0)** | Not in the plan at all. Hard disqualification if missed. |
| **Progress Review 1 (P3)** | Mandatory attendance, October. Needs a presentable architecture and some running hardware. |
| **Progress Review 2 (P8)** | Mandatory attendance, December. Needs demonstrable autonomy. |
| **Mock Pre-Flight Inspection (P10)** | 4C is Pass/Fail with **one retry**; failing forfeits all 600 flight points. The model checklist is to be released separately (4.31) — track it. |
| **Business Strategy work (parallel)** | 200 points, equal to Design Review. Sponsorship and funds-raised evidence cannot be produced in the final week. See [`business/README.md`](business/README.md). |

---

## 5. Immediate actions

Ordered by deadline pressure, not by importance:

1. **Register.** Deadline is this month. Confirm team meets 3.6–3.8: 4–10
   students, interdisciplinary, one faculty member.
2. **Send the organiser questions.** Seven remain open
   ([`rulebook-compliance.md`](requirements/rulebook-compliance.md) §5); two of
   them — the delivery measurement datum and whether RTK is permitted — between
   them govern 450 of the 600 flight points. These have external latency and
   nothing else on this list does.
3. **Start the recall dataset.** It has irreducible calendar cost and the plan
   previously deferred it to week 6 of 30, which no longer exists.
4. **Bench the cold-boot timing.** Needs a companion computer, a flight
   controller, a GNSS module and a stopwatch — no airframe. It is the only
   constraint with under 20 % margin, and the number is currently modelled
   rather than measured.
   **Extend it to time unpack-to-armed for a 4-arm against a 6-arm frame.**
   The rotor-count decision currently rests on an unmeasured assumption that
   extra arms consume setup margin; this measurement settles it, and octo 8×14″
   beats the quad on physics if the assumption turns out to be wrong. See
   [`sizing/configuration-trade.md`](sizing/configuration-trade.md) §2.3.
5. **Order long-lead items** once P1 freezes the architecture.
