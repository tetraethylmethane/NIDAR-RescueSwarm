# BOM Changelog

Both spreadsheets carry ~490 formulas including cross-sheet references to the
TOTAL row of tab 01. **Inserting rows with a script shifts cells but does not
rewrite formulas**, so every change here lists the repairs it made. After any
programmatic edit, run the recalculation check before trusting a number.

---

## 2026-08-11 — the Verified BOM is authoritative, and the aircraft costs ₹26,146 more

**`RescueSwarm_BOM_India_Verified.xlsx` is now tracked.** It had been sitting
untracked in this folder — one `rm` from gone — while being the best artifact in
it. Its own README states the difference: *"The previous BOM named suppliers.
This one names PARTS."* 41 lines, exact model numbers, 28 live product links, a
per-line status flag, and thrust validated against Reflex Drive's published bench
data.

**It disagrees with `RescueSwarm_BOM_India.xlsx` by ₹26,146 per aircraft, and it
is right.**

| Line | India BOM | Verified | Δ | Which is right |
|---|--:|--:|--:|---|
| Flight controller | 26,000 | **42,000** | +16,000 | Verified. The Agam V6X-RT **Full Set** is ₹42,000 incl. 5 % GST and bundles the Digital Power Module, IMU board, carrier, SD and cables — confirmed on the manufacturer's product page |
| Power module | 2,800 | **0** | −2,800 | Verified. It is inside the Full Set; buying it separately double-counts |
| Motor | 7,000 | **9,099** | +2,099 | Verified. ₹9,099 is listed on Reflex Drive's own product page, with measured thrust published. ₹7,000 was never sourced |
| ESC | 3,000 | **3,400** | +400 | Verified. Requirement is 60 A; the India BOM's supplier advertises 30–45 A |
| Propeller | 4,400 | **5,600** | +1,200 | Verified on sourcing — **but see the design conflict below** |
| AI compute | 38,000 | 55,000 | +17,000 | **Neither.** Both are placeholders; a ₹20,000 part meets the spec |
| **Total** | **2,64,400** | **2,90,546** | **+26,146** | |

An independent market search run before this file was opened found the RD MI-5008
at **₹9,099** — the identical figure. The Verified prices are real.

### Unresolved: it is a 17 in aircraft

The Verified BOM uses RD 1760 props (17 × 6.0 in), not 18 in, and its README says
the design point was *"revised to fit real Indian parts."* Bottom-up mass drops
6,236 g → 5,780 g. `docs/sizing/`, `cost_model.py` and `bom_reconcile.py` all
still describe the 18 in aircraft. **Adopting the Verified BOM means re-running
the sizing model, not editing a price.** This is decision D5.

### Cost study rev D — reconciliation plus three costed options

`RescueSwarm_Cost_Study.xlsx` rewritten around the reconciliation:

| Option | ₹/aircraft | Fleet ×3 | What it gives up |
|---|--:|--:|---|
| **A** all-Indian, as verified | 2,90,546 | 8,71,638 | nothing |
| **B** RECOMMENDED | **2,59,001** | **7,77,003** | nothing that scores |
| **C** lowest cost | 2,07,295 | 6,21,885 | ~125 geotag points, the Indian autopilot, the Indian cells |

**Option B saves ₹31,545 per aircraft (10.9 %) with no loss of scored
capability.** Its largest component is the AI compute substitution — Raspberry Pi
5 + AI HAT+ **26 TOPS**, which meets the ≥20 TOPS spec — worth ₹35,000 and
conditional on a benchmark.

**Every option repricing the safety radio upward by ₹11,855.** ₹7,500 does not
buy a compliant 865–867 MHz link in either BOM; the India-legal part is the
RFD 868ux-IND.

₹40,000 remains unreachable: propulsion and power alone are **₹81,896**, more
than twice the target, before any frame, avionics, camera, radio or parachute.

---

## 2026-08-11 — `RescueSwarm_Cost_Study.xlsx`: the BOM is at or below market

Supersedes and deletes `RescueSwarm_BOM_Budget.xlsx` (rev A), which was built on
estimates. **Every alternative now carries a manufacturer part number, a supplier,
a source URL and a dated price**, on tab `04 Market Evidence` — 20 live links.

**Document, rev C.** Seven tabs, ordered so the conclusion comes first:

| Tab | Purpose |
|---|---|
| `00 Summary` | One printable page: question, answer, headline table, five recommendations, how to read the rest, approval block |
| `01 Findings` | Five findings, each as *evidence → what it means → action* |
| `02 Cost Summary` | The roll-up, savings and under-pricing separated |
| `03 Air Vehicle BOM` | All 49 lines with a per-line status: KEEP / SUBSTITUTE / REPRICE / SOURCE |
| `04 Market Evidence` | Every part considered, with source URLs |
| `05 Decisions` | Seven decisions, with columns to record the call and sign |
| `06 What ₹40k Buys` | A real ₹35,400 aircraft and the eight requirements it fails |

Print setup on every sheet (fit-to-width, repeating headers, page numbers), one
colour legend used consistently, and no table wider than eleven columns.
Tab 03 reconciles to **₹2,64,400 and 6,236 g**, matching the build standard exactly.

**Rev A's central claim was wrong.** It reported a ₹76,500 per-aircraft saving.
Pricing the same substitutions against live Indian listings gives ₹29,922 of
verified saving and **₹20,251 of verified *under*-pricing**, for a net movement of
**₹9,671** against a ₹2,64,400 aircraft — 3.7 %.

| Line | BOM ₹ | Market ₹ | Δ ext | |
|---|--:|--:|--:|---|
| 33 AI compute | 38,000 | ~20,000 | **+18,000** | Pi 5 + AI HAT+ **26 TOPS** — meets the ≥20 TOPS spec, unlike the 13 TOPS 8L rev A proposed |
| 35 Camera | 14,000 | 9,600 | +4,400 | Arducam IMX477 |
| 26 Flight controller | 26,000 | 22,600 | +3,400 | Pixhawk 6C Mini — **recommend rejecting** |
| 17 Li-ion cell | 700 | 560 | +2,520 | Molicel P45B |
| 15 Propeller | 2,200 | 1,399 | +1,602 | Tarot TL2848 — **not folding**, no CSIR-NAL |
| 13 Motor | 7,000 | 9,099 | **−8,396** | Nearest listed equivalents are ₹9,099 (Indian RD MI-5008) and ₹9,499 (T-Motor MN5008) |
| 41 Safety radio | 7,500 | ~19,355 | **−11,855** | India-compliant part is the RFD 868ux-IND; RFD868x bundles list at ₹38,709 for an air+ground pair |

**The safety radio is the significant find.** ₹7,500 does not buy a compliant
865–867 MHz link. This is a budget increase that was sitting undiscovered, and it
is larger than any saving on the sheet except the compute module.

**The motor line is the second.** The BOM carries ₹7,000 against a market of
₹9,099–9,499 — so the current BOM is *cheaper than what is actually purchasable*,
not padded. That reframes the whole exercise.

### Two engineering errors in rev A, corrected

- **4-in-1 ESC.** Rev A substituted a 60 A 4-in-1 board. Those are 30×30 mm FPV
  racing stacks — unsuitable for 18 in props on a 6.36 kg airframe, and one board
  failure stops all four motors on a quad with no motor-out capability. Withdrawn.
- **13 TOPS accelerator.** Rev A proposed the Hailo-8L against a ≥20 TOPS spec.
  The 26 TOPS Hailo-8 variant exists at similar cost and meets it. Corrected.

### Four lines in the *current* BOM have no public price at all

The flight controller, motor, cells and camera — **four of the six largest lines
in the aircraft**. They are quote-required, not estimated. Until they are quoted,
₹2,64,400 is itself an estimate, and the motor line is already known to sit below
market. This is decision D6 on tab 04.

### Conclusion recorded on the cover

A cost-reduction pass on this BOM does not produce a cheaper aircraft. It produces
a more accurate estimate of the same one. The ₹40,000 target remains unreachable —
propulsion and power alone are ₹73,050, and both are sized by the mission rather
than by supplier choice.

---

## 2026-08-10 — added `RescueSwarm_BOM_Budget.xlsx`, a cost-reduction study

**A study, not a build standard.** It is not read by `cost_model.py`, not
reproduced in CI, and feeds no published number. The India BOM stays
authoritative. Recorded here so it does not become an orphan workbook.

Target that prompted it: **~₹40,000 per aircraft.** It is not reachable, and the
sheet says so on its front tab rather than burying it.

| | ₹/aircraft |
|---|--:|
| As-costed (India BOM tab 01) | 2,64,400 |
| **Budget variant, every available cut taken** | **1,87,900** |
| Reduction | −76,500, **−28.9 %** |
| Target | 40,000 |
| Budget variant as a multiple of target | **4.7×** |

**Propulsion and power alone are ₹73,050 — 1.8× the whole target** — before any
frame, FC, GNSS, camera, radio, parachute or release mechanism. Both groups are
sized by the mission (4 × 200 g kits, 15 min hover, 600 m, T/W 2.0 at 6.36 kg),
so they do not respond to shopping harder. Reaching ₹40,000 needs a different
aircraft, which tab 02 specifies along with the eight requirements it fails.

**No price in the budget column is a supplier quote.** Each line is marked
`LISTED` (a dated Indian retail listing) or `EST` (my estimate). The as-costed
column has the same weakness in places — Bharath publishes no motor price, GODI
no cell price — so the comparison is directional until quotes land.

### Three lines that do not respond to cost pressure

- **GNSS pair, ₹35,000** — no cheaper RTK-capable equivalent exists. Non-RTK M10
  is ~₹3,000 but drops geotag to ~3.1 m, forfeiting ~125 of 200 points. A
  scoring decision wearing a cost decision's clothes.
- **Parachute, ₹12,000** — SYS-41, supplier still TBD, nearest match already one
  size undersized. Needs solving, not cheapening.
- **Flight controller** — the imported Pixhawk 6C Mini **lists at ₹22,600 in
  India** against the Agam V6X-RT at ₹26,000. **A ₹3,400 saving to forfeit the
  indigenisation story. Recommend not swapping.** An earlier estimate of ~₹9,000
  for this substitution was wrong: Indian-market prices on imported avionics
  carry heavy import margin, and the generic-is-cheaper intuition does not hold.

### The largest cut is also the largest risk

Line 33, AI compute, ₹38,000 → ~₹18,000 (RPi 5 + Hailo-8L). That is **13 TOPS
against a ≥20 TOPS spec**, where §8.2 sized 24 inferences/s at 640×640 on an
Orin Nano at 24–41 FPS. If it misses 2 Hz, detection recall falls and the geotag
points go with it. **Benchmark before committing** — do not buy on the datasheet.

### Tab 02 — what ₹40,000 actually buys, and the useful version of the idea

A ~1.3 kg quad at **₹35,400**, specified in full. It fails eight requirements
including SYS-41, SYS-14, SYS-04 and rule 8.14, and cannot carry 800 g of kits.

It is worthless as a competition entry and genuinely useful as a **development
mule**. The binding constraint is an 8-week flight-test window currently
budgeted entirely on a ₹2.64 L aircraft that does not exist yet and cannot be
risked once it does. Three mules cost about one AI compute module and would
absorb GCS integration, the multi-SYSID radio path, the SYS-21 setup drill that
is still *modelled rather than measured*, failsafe behaviour on real hardware,
and crash-and-rebuild practice — the work that does not need the real airframe.

---

## 2026-08-10 — supplier links on tab 01, and four lines that do not source

**India BOM only.** Tab 01 gains two columns, **P `Source link`** and **Q
`Sourcing note (verified 2026-08-10)`**, covering all 49 priced lines: 23 carry a
product or supplier URL, 26 are marked in-house or local supply because no
catalogue part exists for them.

**No row was inserted and the columns sit beyond the last used column (O), so
nothing shifted.** All **499** formulas survive, `01!I61/K61/L61` still sum to
row 60, and the cross-sheet references from tabs 07/08/09 are unchanged.
`cost_model.py` regenerates `docs/sizing/cost-model-output.txt` **byte for
byte**, so the `reproduce` job is unaffected.

### Four lines whose supplier does not confirm the specification

Looking for the links is what found these. Each was a named supplier in column D
that nobody had opened.

| Line | ₹/aircraft | What the supplier actually offers |
|---|--:|---|
| **39 Mesh node** | 9,000 | FxUAV's mesh module is **928 MHz**; FxLink is 2.4 GHz point-to-point telemetry. This line specifies 802.11s at 2.4/5.8 GHz. **No FxUAV product satisfies it.** |
| **41 Sub-GHz safety radio** | 7,500 | Same supplier, same 928 MHz part. This line specifies **865–867 MHz**, the Indian delicensed SRD band. 928 MHz is outside it. |
| **48 Recovery parachute** | 12,000 | Column D says TBD and it **stays TBD** — no Indian supplier found. Nearest match is imported: Fruity Chutes Harrier, spring-launched (so it clears the no-blast ruling) but **rated to 6.2 kg against a 6.36 kg MTOW**, one size undersized. |
| **28/29 GNSS** | 35,000 | AeroNav-1 confirms NavIC L1+L5 and a BMM350 magnetometer. It **does not claim RTK or moving-baseline** anywhere on the product page. This was already the open action in column O; it is now evidence rather than a worry, and it gates geotag case C. |

That is **₹63,500 per aircraft — 24 % of the air vehicle** — resting on parts
whose suppliers do not advertise them. Three lesser ones are in column Q too:
the ESC catalogue advertises 30–45 A against a 60 A line, the 18 in folding
propeller is not in S R Aerospace's listing, and e-con's 12 MP module is not
confirmed as S-mount — which would void line 36, the ₹2,600 lens bought for it.

**No price is changed by this entry.** These are open procurement actions, not
repricings; deciding them is a human's call and several move the design.

### An arithmetic inconsistency in `cost_model.py`, found by the same pass

Not fixed here, because fixing it moves the published funding ask and that
should be a decision rather than a side effect.

`indig_frac` is computed with tab 01 counted **once**
([`cost_model.py:119-121`](../../tools/sizing-model/cost_model.py#L119-L121)),
but `subtotal` counts tab 01 **three times** (line 107). The same fraction is
then applied to that subtotal to derive the dutiable residual (line 126).

| Weighting | Indigenisation | Dutiable residual | Duty |
|---|--:|--:|--:|
| As published — tab 01 counted once | 67.9 % | ₹6.09 L | ₹1.34 L |
| Programme-weighted — tab 01 × 3 | **65.5 %** | ₹6.55 L | ₹1.44 L |

Both are defensible as *statements* — the published one is literally "across the
priced BOM", which is what it says. The inconsistency is applying a BOM-weighted
fraction to a programme-weighted subtotal. Carried through GST and contingency it
moves the programme total by roughly **₹0.14 L**, so the funding ask is not
materially wrong — but 67.9 % is the headline indigenisation claim and the
programme-weighted number is 65.5 %.

---

## 2026-08-10 — cost pass: subtotal −21 %, indigenisation 61.3 % → 67.9 %

**India BOM only.** The generic BOM is unchanged and now differs from the India
BOM by more than sourcing.

| | Before | After |
|---|---|---|
| Air vehicle, per aircraft | ₹2,81,400 | **₹2,64,400** |
| Subtotal | ₹24.06 L | **₹18.96 L** |
| Programme total | ₹36.97 L | **₹28.74 L** |
| Indigenisation, value-weighted | 61.3 % | **67.9 %** |
| Deployable system, cost basis | ₹16.78 L | **₹14.60 L** |

**No row was inserted or deleted, so no formula moved and none needed repair** —
all 499 survive, verified after saving. Only cell values in the Qty, Unit Price,
description and note columns changed. **Lines that were cut are set to Qty 0 with
their unit price left in the cell**, so the decision stays visible in the sheet
and reinstating one is a single-cell edit.

**Tab 01 bottom-up mass is unchanged at 6,236 g.** MTOW, hover endurance, the
2.0× reserve and the 25 kg margin are all untouched — every cut is on tabs 03–06
or is a reprice, never a mass change. `bom_reconcile.py` reads tab 07's group
masses as constants and reproduces byte-for-byte.

### What was cut, and why it was not a capability

| Tab | Line | Change | ₹ | Basis |
|---|---|---|--:|---|
| 04 | 20 Dev workstation / GPU | Qty 1 → **0** | −1,65,000 | Duplicates tab 06 line 13 (Indian GPU cloud), which is cheaper **and** scores I1 0.9 against this line's I3 0.2. Annotation and SITL run on the two GCS laptops |
| 06 | 13 Training compute | ₹40,000 → **₹75,000** | +35,000 | Absorbs the above. Net −1.30 L, and it moves ₹75,000 of spend from I3 0.2 to I1 0.9 |
| 05 | 10 Complete spare aircraft → **spare airframe structure set** | ₹1,65,000 → **₹25,000** | −1,40,000 | Lines 1–9 already held motors, ESCs, props, arms, FC, GNSS, compute, camera and three packs — ₹2.1 L, everything a fourth airframe needs *except the structure*. The old line bought most of it twice |
| 01 | 33 AI compute module | ₹55,000 → **₹38,000** | −51,000 (×3) | Priced for an integrated e-con Darsi-class box. Sizing §8.2 sizes tiled inference at 2 Hz on an **Orin Nano**, and §14's thermal case is 18 W. Buy the module the model assumes, on an Indian carrier |
| 05 | 7 Spare compute module | ₹55,000 → **₹38,000** | −17,000 | Tracks tab 01 |
| 03 | 1–2 GCS + backup laptop | ₹1,05,000 → ₹85,000; ₹85,000 → ₹55,000 | −50,000 | The load is 3 × 720p H.264 WebRTC decode plus a Python GCS. With training on cloud, neither needs a discrete GPU. The backup must run the same software, not match the same benchmark |
| 03 | 11 Portable power station | 2 kWh → **1.2 kWh** | −25,000 | 3 × 292 Wh at ~85 % charge efficiency is 1.03 kWh, plus GCS. The rest was reserve nothing asked for |
| 03 | 16 Equipment cases | ₹16,000 → **₹11,000** ea | −20,000 | Foam layout is what the 5-minute setup depends on, not the shell |
| 03 | 12 Solar panel | Qty 1 → **0** | −15,000 | The BOM's own note called it optional. 200 W folding PV needs ~7 h of ideal sun to refill 1.2 kWh |
| 04 | 3 Battery charger | ₹26,000 → **₹14,000** ea | −24,000 | 292 Wh at 1C is ~300 W. The 1000 W class bought headroom above 1C the cells should not see |
| 04 | 6 Spot welder | Qty 1 → **0** | −15,000 | Tab 01 line 18 already buys pack assembly as a service from an Indian pack house, which spot-welds |
| 04 | 4 Charger PSU | Qty 2 → **1** | −8,000 | Two 600 W chargers at 1C draw ~600 W combined; one 960 W supply carries both |
| 03 | 3 Sun hood + monitor | ₹20,000 → **₹12,000** | −8,000 | Locally fabricated hood, commodity portable panel |
| 04 | 2, 9 Power analyser, calipers | Qty 2 → **1** each | −7,200 | Bench measurements, not two parallel stations |

Total **−₹5,10,200** on the subtotal.

**Not cut, and deliberately so.** Tab 08's DO-NOT-CUT list is intact: safety
equipment, the calibrated scales that decide the rule C2 weigh-in, and the
flight spares that protect the 8-week window. The **GNSS secondary** (₹17,000 ×3)
stays — moving-baseline yaw is load-bearing for the 450 geotag points, since a
magnetometer sitting near a 98 A bus is not a heading source. The **recovery
parachute** (₹13,500 ×3) stays — the changelog entry below bought it on a points
argument, not a cost one, and reversing that is a design decision rather than a
cost cut. The **flight controller** (₹26,000) stays: a cheaper Indian FC may
exist, but no quote does, and repricing it would be inventing a number.

### Prices repriced on requirement, not on quotation

The AI compute, laptop, power-station, charger and case lines were repriced
against what the sizing model or the rule actually asks for. They are still
**indicative budgetary estimates, like every price in this workbook** — tab 08
row 2 has always said so. Lines carrying the largest uncertainty are marked
`QUOTE REQUIRED` in the note column. Send RFQs before any of this is quoted to a
panel.

### The accepted risk, stated plainly

Rebuilding a crashed airframe now consumes the spares set, so **a second failure
in the same week is uncovered**. Rule C1 needs only 2 aircraft flying and the
design flies 3. If funding arrives, the first ₹1,65,000 to spend is reinstating
the complete fourth aircraft (tab 05 line 10).

### Prose corrections in the same pass

Three cells stated a number as text beside a formula that computed it, so none
of them updated when the mix changed. All are prose — nothing computed from them
was wrong, which is why they survived:

| Where | Was | Now |
|---|---|---|
| `cost_model.py` | label literal `programme as costed (61.3% Indian)` | formatted from `indig_frac` |
| `00!C7` | "about 60% of PROGRAMME VALUE ... about 57% of flight-hardware value" | 68 % / 59 %, plus an instruction to re-read tab 09 |
| `09!B31` | *"84% of system value is Indian"* — a figure tab 09 has never computed | 68 %, plus a note to read it off row 11 |

`08!B25` records the pass where a procurement reader will meet it.

---

## 2026-08-08 — recovery parachute, RTK confirmed, simplified autonomy

### Added: recovery parachute (SYS-41)

Absent from both BOMs. The organisers confirmed an aircraft recovery chute is
permitted, **ballistic and CO₂ deployment included**, provided the aircraft lands
on the pad — a condition a canopy cannot meet (it drifts ~36 m from 60 m in a
3 m/s breeze against a 3.66 m pad). Fitted anyway: a crash costs **−50** and
landing outside the zone costs **−10**, so deploying is worth ~40 points even
accepting the penalty, before counting the airframe.

| Tab | Row | Item | Mass | Price |
|---|---|---|---|---|
| 01 India | 48 | Recovery parachute, <20 m deployment | 240 g | ₹12,000 *(estimate)* |
| 01 India | 49 | Parachute mount + Kevlar bridle | 60 g | ₹1,500 *(estimate)* |
| 01 generic | 56–57 | as above | 300 g | — |

**Prices are estimates and the supplier is TBD.** Replace both before the cost
sheet is submitted (rule 7.5).

### ⚠ Consequence: the endurance reserve is now spent

300 g per aircraft takes hover endurance to **≈2.0×** the mission against a
self-imposed **≥2.0×** reserve policy:

| Source | MTOW | Fleet | Endurance | × mission |
|---|---|---|---|---|
| BOM bottom-up | 6.23 kg | 18.70 kg | 15.8 min | **2.05×** |
| Sizing model | 6.36 kg | 19.08 kg | 15.3 min | **1.99×** |

The 2 % spread is the model's structural growth factor (23.5 % of MTOW) running
slightly ahead of the bottom-up line count. Both still clear the 25 kg rule with
~24 % margin.

**The design now sits on its own reserve line.** The next 200 g of growth breaks
it, and the reserve exists so a full re-sweep plus four minutes of loiter remain
available after the nominal mission. Three options if mass grows again: trim
elsewhere, go to 6S4P and accept the battery spiral, or consciously relax the
policy — but relaxing it to fit the hardware is moving the goalposts.

### Changed: RTK base station header (tab 03)

Was *"pending organiser confirmation (Dev Plan clarification Q1)"*. The
organisers have confirmed a team-owned RTK base is **permitted**, and separately
that it may **not** be positioned or started before the 5-minute setup window
(SYS-42). Header updated to say both.

### Changed: coverage planner and task allocation (tab 06)

- *DARP reference implementation* → static equal-area partition + boustrophedon,
  generated on the GCS.
- *CBBA reference implementation* → greedy claim-and-lock with a deterministic
  tie-break.

Both per [`implementation-plan.md`](../../docs/implementation-plan.md) §1.3–1.4.
DARP and CBBA are still presented as design in the Design Review; they are not
implemented, and the rubric (4D-3) names neither.

### Added: MediaMTX video gateway (tab 06)

Rule 8.14 requires a live camera feed from **each** drone. Three MJPEG streams
would cost 4.5–6 Mbps against a 2.5 Mbps link budget; MediaMTX serves three
H.264 WebRTC streams for ~2.7 Mbps.

### Formula repairs made

Row insertion moved the tab 01 TOTAL row, so these were rewritten by hand:

**India** — TOTAL 58 → 61

| Cell | Was | Now |
|---|---|---|
| `01!I61 / K61 / L61` | `SUM(…:57)` | `SUM(…:60)` |
| `01!F61` | `=L58/K58` | `=L61/K61` |
| `07!D15` | `'01'!I58` | `'01'!I61` |
| `08!D5` | `'01'!K58` | `'01'!K61` |
| `08!F5` | `C5*'01'!L58` | `C5*'01'!L61` |
| `09!C5 / D5` | `'01'!K58*3`, `'01'!L58*3` | `…K61*3`, `…L61*3` |
| `09!C15–C18` | `COUNTIF('01'!E4:E57,…)` | `E4:E60` |
| `07!D14` | `SUM(D5:D12)` | `SUM(D5:D13)` — new group 9 |

**Generic** — TOTAL 66 → 69: `01!F69/H69/I69` ranges extended to row 68;
`07!D15 → '01'!F69`; `08!D5 → '01'!H69`.

### How this was verified

openpyxl writes formulas but cannot evaluate them, so a broken SUM range looks
correct on disk and only surfaces when someone opens the file. Both workbooks
were **recalculated with the `formulas` package** and checked:

```
INDIA    tab 01 TOTAL 6236 g · group total 6233 g · agree to 3 g
         fleet 18699 g · 25.2 % margin under the 25 kg cap
GENERIC  tab 01 TOTAL 6101 g · tab 07 tracks tab 01
RESULT   PASS
```

> **Cached values are stale.** openpyxl discards the values Excel cached for each
> formula. Anything reading the file with `data_only=True` will see `None` until
> the workbook is opened in Excel or LibreOffice once and saved. The formulas
> themselves are correct — verified above — this only affects the cache.

Backups were taken before editing and removed after verification; git history is
the restore path if a change needs reverting.
