#!/usr/bin/env python3
"""Independently verify that the netclass and power rules still exist.

A board that has lost its netclasses passes DRC, because a board with no rules
has nothing to violate. That happened here once: pcbnew.SaveBoard() rewrote
DrikrAIO.kicad_pro and replaced all eight classes with a bare Default, DRC
stayed green, and nothing complained.

So DRC status is NOT evidence on its own. This is the independent check that
has to pass alongside it.

Exit code 0 = all expectations met. Non-zero = a rule disappeared; do not trust
any DRC result taken since.

Run:  python hardware/tools/verify_netclasses.py
"""
import json
import os
import re
import sys

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRO = os.path.join(HW, "DrikrAIO.kicad_pro")
DRU = os.path.join(HW, "DrikrAIO.kicad_dru")

# What must exist. Widths from tools/power_review.py: 1.0 mm of 2 oz outer
# carries 5.3 A at a 20 C rise, against a 21 A phase RMS and a 42 A bus.
EXPECTED_CLASSES = {
    "Default":  {},
    "Analog":   {},
    "Gate":     {},
    "Power":    {},
    "RF":       {},
    "USB":      {},
    "Phase":    {"track_width": 6.6, "via_diameter": 0.8, "via_drill": 0.4},
    "VBAT":     {"track_width": 6.6, "via_diameter": 0.8, "via_drill": 0.4},
}

EXPECTED_RULES = [
    "2 oz outer copper, clearance",
    "2 oz outer copper, track width",
    "motor phase minimum width",
    "battery rail minimum width",
    "power via size",
    "RF clearance to other copper",
]

# Board-level minimums. EXACT equality is required, in both directions.
#
# An earlier version of this file only failed when a value went UP, on the
# reasoning that a larger minimum is a tighter rule. That is wrong for a
# minimum: min_clearance going 0.09 -> 0.0 means there is no clearance rule at
# all, and the check waved it through as "tighter". It was caught by
# deliberately injecting the exact regression this file exists to detect.
#
# Any deviation is now a failure. A rule that changed for a good reason should
# be changed HERE, in the baseline, as a reviewed edit.
EXPECTED_DS = {
    "min_clearance": 0.09,
    "min_connection": 0.09,
    "min_track_width": 0.09,
    "min_via_diameter": 0.35,
    "min_through_hole_diameter": 0.2,
    "min_via_annular_width": 0.075,
    "min_hole_clearance": 0.2,
    "min_hole_to_hole": 0.2,
    "min_copper_edge_clearance": 0.2,
    "solder_mask_to_copper_clearance": 0.005,
}


def fail(msg, problems):
    problems.append(msg)
    print(f"  FAIL  {msg}")


def main():
    problems = []
    print("NETCLASS AND RULE VERIFICATION")
    print("=" * 66)

    if not os.path.exists(PRO):
        print(f"  FAIL  {PRO} missing")
        return 2
    pro = json.load(open(PRO, encoding="utf-8"))

    classes = {c["name"]: c for c in
               pro.get("net_settings", {}).get("classes", [])}
    print(f"  classes found: {len(classes)} -> {sorted(classes)}")

    # 5. every expected class exists
    for name in EXPECTED_CLASSES:
        if name not in classes:
            fail(f"netclass '{name}' has disappeared", problems)

    # 9. count matches
    if len(classes) < len(EXPECTED_CLASSES):
        fail(f"expected >= {len(EXPECTED_CLASSES)} classes, found {len(classes)}",
             problems)

    # 6, 7. Phase and VBAT widths and via rules
    for name, want in EXPECTED_CLASSES.items():
        got = classes.get(name)
        if not got:
            continue
        for key, val in want.items():
            actual = got.get(key)
            if actual is None:
                fail(f"{name}.{key} is unset", problems)
            elif abs(float(actual) - val) > 1e-6:
                fail(f"{name}.{key} is {actual}, expected {val}", problems)
            else:
                print(f"  ok    {name}.{key} = {actual}")

    # 8. board-level minimums -- exact match, either direction
    ds = pro.get("board", {}).get("design_settings", {}).get("rules", {})
    print(f"  design rules checked: {len(EXPECTED_DS)}")
    for key, val in EXPECTED_DS.items():
        actual = ds.get(key)
        if actual is None:
            fail(f"design_settings.{key} is MISSING", problems)
        elif abs(float(actual) - val) > 1e-9:
            direction = "weakened" if float(actual) < val else "changed"
            fail(f"design_settings.{key} {direction}: {actual}, expected {val}",
                 problems)

    # custom DRC rules
    if not os.path.exists(DRU):
        fail("DrikrAIO.kicad_dru is missing", problems)
    else:
        dru = open(DRU, encoding="utf-8").read()
        names = re.findall(r'\(rule\s+"([^"]+)"', dru)
        print(f"  custom rules: {len(names)}")
        for r in EXPECTED_RULES:
            if r not in names:
                fail(f"DRC rule '{r}' has disappeared", problems)
        m = re.search(r'"motor phase minimum width"\s*\(constraint track_width '
                      r'\(min ([\d.]+)mm\)\)', dru)
        if m and abs(float(m.group(1)) - 6.6) > 1e-6:
            fail(f"phase minimum width rule is {m.group(1)} mm, expected 6.6",
                 problems)

    print("=" * 66)
    if problems:
        print(f"  {len(problems)} PROBLEM(S). Any DRC result taken since the")
        print("  last good state must be treated as meaningless.")
        return 1
    print("  All expected netclasses, widths, via rules and DRC rules present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
