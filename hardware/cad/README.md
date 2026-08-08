# hardware/cad

## The frame is driven by the model, not by transcription

[`rescueswarm-frame-equations.txt`](rescueswarm-frame-equations.txt) is
**generated** by [`tools/sizing-model/cad_equations.py`](../../tools/sizing-model/cad_equations.py).
Do not edit it by hand.

### Why it exists

The battery bay in [`frame-design-constraints.md`](../../docs/frame-design-constraints.md)
specified a **12-cell 6S2P pack when the design point is 18 cells and 6S3P**. It
got there by being transcribed from the model into a document, after which the
model moved and the document didn't. A markdown table is cheap to correct; a
frame is not, and CAD is the next place that error lands.

So the driving dimensions come from a file the model writes.

### Getting the variables into a part

**Use the script.** From the repo root, with SolidWorks installed:

```
python tools/cad/sw_build_skeleton.py
```

It launches SolidWorks, creates a part in MMGS, pushes all 25 variables in, and
draws the layout sketch. **Then immediately `Save As` under your own filename**
and model from there — the generated `rescueswarm-skeleton.SLDPRT` is
gitignored and will be overwritten the next time anyone runs the script.

> **The external-file link does not work through the API, and this was tested.**
> `IEquationMgr.FilePath` and `.LinkToFile` can both be set and SolidWorks reads
> them back correctly, but the equations are never imported: **count stays 0**
> across every ordering, every encoding (utf-8, utf-8-sig, utf-16, ansi) and a
> forced rebuild. `Add2` works and accepts exactly the syntax this file uses, so
> the script pushes the variables in directly.
>
> Linking the file **through the UI** (Tools → Equations → Link to external
> file) is the documented workflow and probably does work — but **I have not
> verified it**, so treat it as untested. If it does work for you it is the
> better option, because the variables then update on rebuild instead of
> needing the script re-run.

Once the variables exist, drive sketch dimensions by expression instead of
typing numbers:

   | dimension | expression |
   |:--|:--|
   | motor mount circle, from centre | `= "wheelbase_diag" / 2` |
   | battery pocket length | `= "bay_length"` |
   | magazine cut-out | `= "magazine_length"` |
   | camera mount hole spacing | `= "cam_fastener_spacing"` |

Change the pack → re-run `cad_equations.py` → re-run `sw_build_skeleton.py` (or
rebuild, if you got the UI link working). The frame follows. Nobody retypes 761.

### What the skeleton contains

Reference geometry only — no solids. It is the layout other parts mate to:

- four motor axes at `"wheelbase_diag"/2` on the diagonals
- prop-tip circles at `"prop_dia_max"/2`, so tip clearance is **visible** rather
  than trusted (30 mm at 20 in)
- battery bay footprint, 140 × 84 mm
- magazine footprint, 400 × 200 mm
- overall footprint, 1046 mm square

Verified by closing the part, reopening it from disk and reading it back:
**25 of 25 variables match the generated file exactly**, and `Sketch1` plus the
`Equations` folder are present.

### File format

Plain text, one variable per line, `'` for comments:

```
' PROPULSION GEOMETRY
"wheelbase_diag"= 760.847
"arm_length"= 380.423
```

Values are in **document units** — set the part to **MMGS** before linking, or
every dimension will be out by 25.4.

### What CI enforces

The reproduce job runs the generator and fails if either:

- the CAD parameters no longer agree with `docs/sizing/model-output.txt` — the
  generator parses the pack topology and cell count out of the committed model
  output and refuses to emit a file for the wrong aircraft; or
- the committed equations file differs from what the generator produces, i.e.
  someone edited it by hand or changed the model without regenerating.

Verified to fail: reverting the model output to 6S2P/12 cells produces

```
CAD EQUATIONS DO NOT MATCH THE MODEL:
   pack topology: model 6S2P, this script 6S3P
   cell count: model 12, this script 18
```

### Two numbers worth reading before you start modelling

- **`cam_max_differential` = 0.214 mm.** That is the *total* differential
  movement allowed across the camera mount's 80 mm fastener spacing, for the
  life of the airframe. An M3 clearance hole carries 0.2–0.4 mm of slop on its
  own — which is why constraint #6 is dowels or a bond, not bolt friction.
- **`bay_depth` = 72 mm** against 48 mm for the superseded 6S2P. Take those
  24 mm by making the tray **wider or longer, not deeper** — the pack CG belongs
  in the rotor plane ([`cg_budget.py`](../../tools/sizing-model/cg_budget.py)).
