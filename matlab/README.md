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
minimum pack voltage   17.05 V at t = 432 s
failsafe floor         18.00 V
margin                 -0.95 V
SOC at that moment     64 %
sag at the gust        5.82 V   (static model assumes 4.60)
```

The aircraft crosses its own low-voltage floor during a legitimate gust
recovery, at two-thirds charge, long before the 80 % DoD limit the reserve
policy is built around. Dynamic sag exceeds the static figure by 1.2 V because
the diffusion terms add to the instantaneous ohmic drop.

A failsafe set on instantaneous pack volts would command return-to-land
mid-search on a healthy pack.

**Caveat.** R0 is calibrated so the static sag matches the 4.6 V the proposal
assumes; R1/C1/R2/C2 are typical high-drain 21700 values, not P45B-specific. So
the shape is trustworthy and the magnitude inherits that assumption. P2 replaces
R0 with a measured DC-IR, and that is when this becomes evidence rather than
analysis.
