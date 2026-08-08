"""Check a SolidWorks part or assembly against the sizing model.

WHAT THIS IS FOR
A human draws the frame; this checks it. The checks are tedious, identical
every time, and exactly what gets skipped the week before a design review --
which is the definition of work worth automating.

Everything it asserts comes from a committed, CI-checked model output. It has
no opinions of its own.

    python tools/cad/cad_check.py                      # the active document
    python tools/cad/cad_check.py path\\to\\frame.SLDASM

Exit code 0 = all checks passed, 1 = at least one FAIL, 2 = could not run.
Warnings do not fail the run: a 6 % mass overshoot at concept stage is
information, not an error.

WHY THE THRESHOLDS ARE WHAT THEY ARE
  mass      MTOW is 6360 g and the fleet has 24 % margin to the 25 kg cap, so
            mass is not tight -- but the ENDURANCE RESERVE is at 2.05x against
            a >=2.0x policy, and that is what growth eats. 5 % warn, 10 % fail.
  CG        cg_budget.py: a 10 mm pack placement error is ~1.2 % permanent
            trim. 10 mm warn, 25 mm fail.
  clearance tip clearance is a design input (30 mm at 20 in), not a preference.
"""
from __future__ import annotations

import math
import os
import sys

try:
    import win32com.client
except ImportError:
    sys.exit("pywin32 not installed:  python -m pip install --user pywin32")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EQ_FILE = os.path.join(REPO, "hardware", "cad", "rescueswarm-frame-equations.txt")
MODEL_OUT = os.path.join(REPO, "docs", "sizing", "model-output.txt")

MTOW_G = 6360.0
STRUCTURE_G = 1495.0
MASS_WARN, MASS_FAIL = 0.05, 0.10
CG_WARN_MM, CG_FAIL_MM = 10.0, 25.0
M_TO_MM = 1000.0

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
results: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str) -> None:
    results.append((status, name, detail))
    mark = {PASS: "  ok  ", WARN: " warn ", FAIL: " FAIL "}[status]
    print(f"[{mark}] {name}")
    if detail:
        for line in detail.splitlines():
            print(f"          {line}")


def member(obj, name, *args):
    """COM members are methods or properties and late binding cannot tell."""
    attr = getattr(obj, name)
    if args:
        return attr(*args)
    return attr() if callable(attr) else attr


def load_expected() -> dict:
    if not os.path.exists(EQ_FILE):
        sys.exit(f"missing {EQ_FILE} -- run tools/sizing-model/cad_equations.py")
    out = {}
    for line in open(EQ_FILE, encoding="utf-8"):
        line = line.strip()
        if line.startswith('"') and "=" in line:
            out[line.split('"')[1]] = float(line.split("=", 1)[1])
    return out


# ----------------------------------------------------------------- checks
def check_variables(model, exp) -> None:
    """The part must still carry the generated variables."""
    try:
        eqm = model.GetEquationMgr
        n = int(member(eqm, "GetCount"))
    except Exception as e:
        record(WARN, "parametric variables", f"could not read equations: {e}")
        return
    if n == 0:
        record(WARN, "parametric variables",
               "none in this document. Dimensions are typed, not driven, so a\n"
               "change to the pack will not propagate. See hardware/cad/README.md.")
        return
    found = {}
    for i in range(n):
        t = eqm.Equation(i)
        if '"' in t:
            found[t.split('"')[1]] = eqm.Value(i)
    drift = [k for k, v in found.items()
             if k in exp and abs(float(v) - exp[k]) > 1e-3]
    missing = [k for k in exp if k not in found]
    if drift:
        record(FAIL, "parametric variables",
               "these differ from the generated file:\n  " + "\n  ".join(
                   f"{k}: model {exp[k]:.3f}, part {found[k]}" for k in drift))
    elif missing:
        record(WARN, "parametric variables",
               f"{len(found)} present, {len(missing)} of the generated set missing")
    else:
        record(PASS, "parametric variables", f"all {len(exp)} match the model")


def mass_properties(model):
    """(mass_g, com_mm) or (None, None).

    IModelDoc2::GetMassProperties is the one that actually resolves under late
    binding here -- Extension.CreateMassProperty and CreateMassProperty2 both
    report 'Member not found'. Verified against a 100 mm aluminium cube, which
    it reports as 2700.0 g with CoM at (0, 50, 0) mm: correct to the gram.

    Returns [CoM x, y, z, volume, surface area, mass] in SI.
    """
    try:
        v = member(model, "GetMassProperties")
    except Exception as e:
        return None, f"could not read: {e}"
    if not v or len(v) < 6:
        return None, "no mass properties returned"
    return (float(v[5]) * 1000.0, [c * M_TO_MM for c in v[:3]]), None


def check_mass(model, is_asm) -> float | None:
    got, err = mass_properties(model)
    if got is None:
        record(WARN, "mass properties", err)
        return None
    mass_g, _com = got

    if mass_g <= 0.001:
        record(WARN, "mass",
               "no solid bodies with material -- nothing to weigh yet.\n"
               "Expected once there are parts: structure 1495 g, MTOW 6360 g.")
        return mass_g

    target = MTOW_G if is_asm else STRUCTURE_G
    label = "MTOW" if is_asm else "structure"
    err = (mass_g - target) / target
    detail = (f"{mass_g:.0f} g against a {label} budget of {target:.0f} g "
              f"({err:+.1%})")
    if abs(err) >= MASS_FAIL:
        record(FAIL, f"mass vs {label} budget", detail +
               "\nthe endurance reserve is 2.05x against a >=2.0x policy; "
               "growth comes off that")
    elif abs(err) >= MASS_WARN:
        record(WARN, f"mass vs {label} budget", detail)
    else:
        record(PASS, f"mass vs {label} budget", detail)
    return mass_g


def check_cg(model, mass_g) -> None:
    if not mass_g or mass_g <= 0.001:
        record(WARN, "centre of gravity", "no mass, so no CG to check")
        return
    got, err = mass_properties(model)
    if got is None:
        record(WARN, "centre of gravity", err)
        return
    _m, (x, y, z) = got
    # The layout sketch is on the Top plane, so the rotor plane is XZ and the
    # lateral offset that trims the aircraft is in X and Z. Y is height.
    lateral = math.hypot(x, z)
    detail = (f"CG at ({x:+.1f}, {y:+.1f}, {z:+.1f}) mm from the origin\n"
              f"lateral offset from the rotor centroid (X-Z): {lateral:.1f} mm\n"
              f"height above the layout plane: {y:+.1f} mm")
    if lateral >= CG_FAIL_MM:
        record(FAIL, "CG on the rotor centroid", detail +
               "\na permanent trim offset costs control margin on every flight")
    elif lateral >= CG_WARN_MM:
        record(WARN, "CG on the rotor centroid", detail +
               "\n10 mm is about 1.2 % permanent trim (cg_budget.py)")
    else:
        record(PASS, "CG on the rotor centroid", detail)


def check_footprint(model, exp) -> None:
    """Bounding box of the whole thing, and three of them in the launch box."""
    # Extension.GetBox does not resolve under late binding; GetPartBox does,
    # and returns [xmin, ymin, zmin, xmax, ymax, zmax] in metres.
    box = None
    for name, arg in (("GetPartBox", True), ("GetPartBox", False)):
        try:
            box = member(model, name, arg)
            if box and len(box) >= 6 and any(box):
                break
        except Exception:
            box = None
    if not box or len(box) < 6 or not any(box):
        record(WARN, "footprint", "no bounding box available (no solid geometry)")
        return
    # Layout is on the Top plane, so the footprint is X by Z.
    dx = abs(box[3] - box[0]) * M_TO_MM
    dz = abs(box[5] - box[2]) * M_TO_MM
    side = max(dx, dz)
    dy = dz
    limit = exp["footprint_square"]
    detail = f"bounding box {dx:.0f} x {dy:.0f} mm, limit {limit:.0f} mm square"
    if side > limit + 1.0:
        record(FAIL, "footprint", detail)
    else:
        record(PASS, "footprint", detail)

    span = 3 * side
    box_mm = exp["launch_box"]
    d2 = f"3 aircraft side by side: {span:.0f} mm against a {box_mm:.0f} mm box"
    record(FAIL if span > box_mm else PASS, "launch box (rule 8.10)", d2)


def check_interference(model, is_asm) -> None:
    if not is_asm:
        record(PASS, "interference", "not an assembly -- nothing to check")
        return
    try:
        idm = model.InterferenceDetectionManager
        idm.TreatCoincidenceAsInterference = False
        idm.TreatSubAssembliesAsComponents = False
        idm.IncludeMultibodyPartInterferences = True
        n = member(idm, "GetInterferenceCount")
        n = int(n) if n is not None else 0
    except Exception as e:
        record(WARN, "interference", f"could not run detection: {e}")
        return
    if n:
        record(FAIL, "interference", f"{n} interference(s) between components")
    else:
        record(PASS, "interference", "no interferences")


def check_prop_clearance(exp) -> None:
    """Geometric, from the model's own numbers -- valid before any CAD exists."""
    gap = exp["motor_spacing_adjacent"] - exp["prop_dia_max"]
    detail = (f"adjacent motors {exp['motor_spacing_adjacent']:.0f} mm apart, "
              f"props {exp['prop_dia_max']:.0f} mm -> {gap:.0f} mm tip gap")
    record(PASS if gap >= 29.9 else FAIL, "prop tip clearance", detail)


def check_parachute_cone(model, is_asm) -> None:
    """The conflict in frame-design-constraints 3a, which cannot be eyeballed."""
    record(WARN, "parachute cone vs antennas",
           "NOT AUTOMATED YET. Needs a cone body in the assembly to run an\n"
           "interference check against. Model the deployment cone as a\n"
           "surface or dummy solid from the mount, then this becomes a real\n"
           "check instead of a reminder. A chute that snags an antenna mast\n"
           "deploys asymmetrically, which is worse than not fitting one.")


# -------------------------------------------------------------------- main
def main() -> int:
    exp = load_expected()
    print("=" * 78)
    print("CAD CHECK  -  the drawn frame against the sizing model")
    print("=" * 78)

    # This one needs no CAD at all.
    check_prop_clearance(exp)

    sw = win32com.client.Dispatch("SldWorks.Application")
    sw.Visible = True

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            print(f"\nno such file: {path}")
            return 2
        errs = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF
                                       | win32com.client.pythoncom.VT_I4, 0)
        warns = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF
                                        | win32com.client.pythoncom.VT_I4, 0)
        kind = 2 if path.lower().endswith(".sldasm") else 1
        model = sw.OpenDoc6(path, kind, 0, "", errs, warns)
    else:
        model = sw.ActiveDoc

    if model is None:
        print("\nNo document. Open a part or assembly, or pass a path.")
        print("Nothing above this line needed CAD; everything below does.")
        return 2

    title = member(model, "GetTitle")
    is_asm = int(member(model, "GetType")) == 2
    print(f"\ndocument: {title}   ({'assembly' if is_asm else 'part'})\n")

    check_variables(model, exp)
    mass = check_mass(model, is_asm)
    check_cg(model, mass)
    check_footprint(model, exp)
    check_interference(model, is_asm)
    check_parachute_cone(model, is_asm)

    print()
    print("=" * 78)
    n_fail = sum(1 for s, _, _ in results if s == FAIL)
    n_warn = sum(1 for s, _, _ in results if s == WARN)
    n_pass = sum(1 for s, _, _ in results if s == PASS)
    print(f"{n_pass} passed, {n_warn} warnings, {n_fail} failed")
    if n_fail:
        print("\nFAILED:")
        for s, name, _ in results:
            if s == FAIL:
                print(f"  - {name}")
    print("=" * 78)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
