"""Build the RescueSwarm layout skeleton in SolidWorks.

WHY NOT THE EXTERNAL-FILE LINK
IEquationMgr.FilePath and .LinkToFile can both be set, and SolidWorks reads
them back correctly, but the equations are never imported: count stays 0 across
every ordering, every encoding (utf-8, utf-8-sig, utf-16, ansi) and a forced
rebuild. Whatever populates a linked equation set is not reachable from the API
in SW2026, at least by late binding.

Add2 DOES work, and it accepts exactly the syntax the generator emits -- that
was verified before writing this. So the variables are pushed in directly and
the generated file remains the single source; re-run this after regenerating.

WHAT IT BUILDS
A layout skeleton, not parts. Reference geometry other components mate to:

  * four motor axes at wheelbase/2 on the diagonals, with prop-tip circles so
    clearance is visible rather than trusted
  * the battery bay footprint
  * the magazine footprint
  * the launch-box check: three footprints side by side against 3660 mm

Everything is construction geometry on one sketch, which is what a top-down
assembly wants to reference.
"""
import math
import os
import sys

import win32com.client

REPO = r"c:\Users\swast\OneDrive\Desktop\Drikr-NIDAR"
EQ_FILE = os.path.join(REPO, "hardware", "cad", "rescueswarm-frame-equations.txt")
OUT = os.path.join(REPO, "hardware", "cad", "rescueswarm-skeleton.SLDPRT")
MM = 0.001          # SolidWorks API is metres regardless of document units


def member(obj, name, *args):
    attr = getattr(obj, name)
    if args:
        return attr(*args)
    return attr() if callable(attr) else attr


def read_equations(path):
    """Parse the generated file into (name, value) pairs."""
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("'"):
            continue
        if "=" in line and line.startswith('"'):
            name = line.split('"')[1]
            val = float(line.split("=", 1)[1].strip())
            out.append((name, val))
    return out


def main() -> int:
    if not os.path.exists(EQ_FILE):
        print(f"missing {EQ_FILE} -- run tools/sizing-model/cad_equations.py")
        return 2
    eqs = read_equations(EQ_FILE)
    V = dict(eqs)
    print(f"read {len(eqs)} variables from the generated file")

    sw = win32com.client.Dispatch("SldWorks.Application")
    sw.Visible = True

    # A document already open on the target path makes SaveAs fail with a
    # generic error 1 and nothing else to go on. Close everything first --
    # this is a scratch skeleton, there is nothing to lose.
    closed = 0
    for _ in range(10):
        d = sw.ActiveDoc
        if d is None:
            break
        sw.CloseDoc(member(d, "GetTitle"))
        closed += 1
    if closed:
        print(f"closed {closed} open document(s)")

    tmpl = sw.GetUserPreferenceStringValue(8)
    model = sw.NewDocument(tmpl, 0, 0.0, 0.0)
    if model is None:
        print("could not create a part (licence?)")
        return 3
    ext = model.Extension
    ext.SetUserPreferenceInteger(49, 0, 0)          # linear units -> mm
    print("part created, units mm")

    # --- variables ---------------------------------------------------------
    eqm = model.GetEquationMgr
    try:
        eqm.LinkToFile = False
    except Exception:
        pass
    added = 0
    for name, val in eqs:
        try:
            if eqm.Add2(-1, f'"{name}"= {val:.4f}', True) >= 0:
                added += 1
        except Exception as e:
            print(f"  {name}: {e}")
    print(f"pushed {added}/{len(eqs)} variables into the model")

    # --- layout sketch -----------------------------------------------------
    # SelectByID2's 8th argument is a Callout object. Late binding will not
    # take a bare None for it -- 'Type mismatch' on arg 8 -- so it has to be an
    # explicitly typed empty VARIANT.
    nothing = win32com.client.VARIANT(win32com.client.pythoncom.VT_DISPATCH, None)
    sk = model.SketchManager
    picked = model.Extension.SelectByID2(
        "Top Plane", "PLANE", 0.0, 0.0, 0.0, False, 0, nothing, 0)
    if not picked:
        # Non-English installs name the planes differently; fall back to the
        # feature tree rather than failing on a localisation detail.
        for alt in ("Top", "Dessus", "Oben", "Planta"):
            picked = model.Extension.SelectByID2(
                alt, "PLANE", 0.0, 0.0, 0.0, False, 0, nothing, 0)
            if picked:
                print(f"  (plane selected as {alt!r})")
                break
    if not picked:
        print("could not select a sketch plane")
        return 4
    sk.InsertSketch(True)
    sk.AddToDB = True

    half = V["wheelbase_diag"] / 2.0 * MM
    d = half / math.sqrt(2.0)                 # X and Y of each motor on a quad X
    prop_r = V["prop_dia_max"] / 2.0 * MM

    made = 0
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        x, y = sx * d, sy * d
        if sk.CreatePoint(x, y, 0.0):
            made += 1
        c = sk.CreateCircle(x, y, 0.0, x + prop_r, y, 0.0)
        if c:
            made += 1
            try:
                c.ConstructionGeometry = True
            except Exception:
                pass
    print(f"  4 motor axes + prop-tip circles ({made} entities)")

    def rect(w_mm, h_mm, construction=True):
        w, h = w_mm / 2.0 * MM, h_mm / 2.0 * MM
        lines = sk.CreateCornerRectangle(-w, -h, 0.0, w, h, 0.0)
        if construction and lines:
            for ln in lines:
                try:
                    ln.ConstructionGeometry = True
                except Exception:
                    pass
        return lines

    rect(V["bay_length"], V["bay_width"])
    print(f"  battery bay {V['bay_length']:.0f} x {V['bay_width']:.0f} mm")
    rect(V["magazine_length"], V["magazine_width"])
    print(f"  magazine {V['magazine_length']:.0f} x {V['magazine_width']:.0f} mm")
    rect(V["footprint_square"], V["footprint_square"])
    print(f"  footprint {V['footprint_square']:.0f} mm square")

    sk.AddToDB = False
    sk.InsertSketch(True)
    model.ClearSelection2(True)
    model.ViewZoomtofit2()

    # --- checks ------------------------------------------------------------
    span = 3 * V["footprint_square"]
    print()
    print(f"  3 aircraft side by side : {span:.0f} mm vs {V['launch_box']:.0f} mm "
          f"[{'OK' if span <= V['launch_box'] else 'OVER'}]")
    print(f"  prop tip gap, adjacent  : "
          f"{V['motor_spacing_adjacent'] - V['prop_dia_max']:.0f} mm")

    # Confirm the variables are really in the model before saving. Add2
    # returning an index is not the same as the equation manager holding it,
    # and the first version of this script reported "pushed 25/25" over a part
    # that saved with none.
    in_model = int(member(eqm, "GetCount"))
    print(f"\nequation manager holds {in_model} of {len(eqs)}")
    if in_model != len(eqs):
        print("  variables did not stick -- not saving a misleading file")
        return 5

    # ModelDocExtension::SaveAs(Name, Version, Options, ExportData, Errors,
    # Warnings). ExportData must be a typed empty VARIANT, same as Callout.
    nothing2 = win32com.client.VARIANT(win32com.client.pythoncom.VT_DISPATCH, None)
    errs = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF
                                   | win32com.client.pythoncom.VT_I4, 0)
    warns = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF
                                    | win32com.client.pythoncom.VT_I4, 0)
    before = os.path.getmtime(OUT) if os.path.exists(OUT) else 0
    ok = ext.SaveAs(OUT, 0, 1, nothing2, errs, warns)
    after = os.path.getmtime(OUT) if os.path.exists(OUT) else 0
    # SaveAs returns TRUE on success; errs is 0 when clean. A 0 return is a
    # FAILURE, which the previous version of this script treated as success.
    print(f"SaveAs -> {ok}   errors={errs.value} warnings={warns.value}")
    print(f"file {'rewritten' if after > before else 'NOT rewritten'} -> {OUT}")
    if not ok or after <= before:
        print("SAVE FAILED")
        return 6
    print("SKELETON_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
