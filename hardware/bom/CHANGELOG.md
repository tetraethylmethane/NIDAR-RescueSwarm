# BOM Changelog

Both spreadsheets carry ~490 formulas including cross-sheet references to the
TOTAL row of tab 01. **Inserting rows with a script shifts cells but does not
rewrite formulas**, so every change here lists the repairs it made. After any
programmatic edit, run the recalculation check before trusting a number.

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
