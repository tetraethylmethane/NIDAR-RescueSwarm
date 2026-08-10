# BOM Changelog

Both spreadsheets carry ~490 formulas including cross-sheet references to the
TOTAL row of tab 01. **Inserting rows with a script shifts cells but does not
rewrite formulas**, so every change here lists the repairs it made. After any
programmatic edit, run the recalculation check before trusting a number.

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
