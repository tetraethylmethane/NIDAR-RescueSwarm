# MATLAB analysis, verification and simulation

MATLAB is the primary tool for figures, verification and simulation. It is not
the source of truth for the design.

## The split, and why

| | |
|---|---|
| **Python** (`tools/sizing-model/`) | owns the **primitives** — the constants the design chooses |
| **MATLAB** (here) | **re-derives** from those primitives, **asserts** against Python's results, and does everything dynamic |

Nothing here retypes a design constant. Two copies of a constant is the defect
this repository keeps finding in itself: three different tile counts in one
document, a mass line naming a computer that was never bought, a fusion figure
computed at an altitude the design had abandoned. Two authorities always
diverge, and the divergence is silent.

## Pipeline

```
python matlab/export_model.py             # Python -> data/model.json
matlab -batch "cd matlab; run_all"          # verify + figures + simulations
matlab -batch "cd matlab; run_all('verify')"   # or one stage at a time
```

## What each part does

See CHECKLIST.md for the status of every figure, calculation, verification and
simulation.

## Layout

```
matlab/
  run_all.m          verify + figures + simulations, one entry point
  export_model.py    Python -> data/model.json
  lib/               rs_model, rs_style, rs_axes, rs_save
  calc/              (reserved)
  verify/            verify_model.m -- 28 independent cross-checks
  figures/           fig_detect, fig_looks, fig_energy
  sim/               sim_pack_sag
  data/              model.json and results
```

**`export_model.py`** writes `data/model.json`: 38 primitives, 34 derived values, the
mass statement and the mission profile.

**`verify_model.m`** is the cross-validation. The Python model asserts each
derivation against its own result, which catches an inconsistent edit but *not*
a mistake in the derivation itself — the same expression sits on both sides.
This re-derives all of it independently, in another language, from primitives
only. **28 checks, currently all passing** -- most to machine precision.

Two of those are deliberately redundant: pack energy is computed both from the
cell arithmetic (exact identity) and from mass times specific energy (agrees to
0.6 %). The loose tolerance on the second is the point — it says the specific
energy assumption is consistent with the cell count rather than tuned to it.

**`pack_sag.m`** is the dynamic simulation, and the one thing here that
produces information the static model cannot. Second-order Thevenin cell model
driven by the real mission profile.

## The result that matters

```
pack                    6S 16 Ah LiHV at 7.12 kg (heavy end of its bracket)
peak current            144 A
minimum raw voltage     20.37 V at t = 432 s (sag 3.51 V)
minimum compensated     22.97 V  (low 21.6 V, critical 21.0 V)
longest dip below low   0.0 s  (timer 10 s)
SOC at landing          66.5 %  (capacity failsafe at 20 %)
```

Raw pack volts dip below BATT_LOW_VOLT during each two-second gust recovery,
but the failsafe compares sag-compensated volts (BATT_FS_VOLTSRC = 1) and waits
BATT_LOW_TIMER = 10 s, so it does not fire. The 144 A peak sits close to the
150 A fuse and AS150 rating, which is now the tightest electrical margin.

Until 2026-10-30 this simulated the 6S3P Li-ion pack, which crossed its 18.0 V
floor at 17.05 V mid-mission. That pack is no longer in the design.

**Caveat:** R0/R1/C1/R2/C2 are typical values for a 16 Ah 25 C LiHV pack with
leads, not measured, and the compensation uses R0 alone (conservative).
**P2 replaces them with a loaded discharge test on the real pack.**
