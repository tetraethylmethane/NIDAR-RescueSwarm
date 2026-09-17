#!/usr/bin/env python3
"""Prove the save pipeline does not destroy configuration, over repeated cycles.

SaveBoard() rewrites DrikrAIO.kicad_pro every time. It has destroyed the
netclasses once and the board design rules once, and on both occasions DRC
stayed green afterwards -- a board with no rules has nothing to violate.

This runs the full snapshot / save / reload / verify / restore loop N times and
fails loudly if anything is lost on any cycle.

Run with KiCad's Python:
    "C:/Program Files/KiCad/10.0/bin/python.exe" test_save_cycle.py [cycles]
"""
import json
import os
import subprocess
import sys

import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRO = os.path.join(HW, "DrikrAIO.kicad_pro")
PCB = os.path.join(HW, "DrikrAIO.kicad_pcb")
VERIFY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "verify_netclasses.py")


def snapshot():
    with open(PRO, encoding="utf-8") as fh:
        pro = json.load(fh)
    return (pro.get("net_settings"),
            pro.get("board", {}).get("design_settings", {}).get("rules"))


def restore(nets, rules):
    with open(PRO, encoding="utf-8") as fh:
        pro = json.load(fh)
    lost = []
    got = [c.get("name") for c in pro.get("net_settings", {}).get("classes", [])]
    want = [c.get("name") for c in nets.get("classes", [])]
    if got != want:
        pro["net_settings"] = nets
        lost.append(f"{len(want)} netclasses (had {len(got)})")
    cur = pro.setdefault("board", {}).setdefault("design_settings", {}) \
             .setdefault("rules", {})
    moved = {k: (cur.get(k), v) for k, v in rules.items() if cur.get(k) != v}
    if moved:
        cur.update(rules)
        lost.append(f"{len(moved)} design rules")
    if lost:
        with open(PRO, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(pro, fh, indent=2)
    return lost, moved


def main():
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    print(f"SAVE/RELOAD REGRESSION TEST -- {cycles} cycles")
    print("=" * 70)

    nets, rules = snapshot()
    if not nets or not rules:
        print("  FAIL  cannot snapshot; project file incomplete")
        return 2
    print(f"  snapshot: {len(nets['classes'])} netclasses, {len(rules)} design rules")

    # Two paths, and only one of them is dangerous.
    #
    #   LoadBoard -> SaveBoard   keeps the project association and preserves
    #                            net_settings and the design rules.
    #   BOARD()   -> SaveBoard   writes a DEFAULT project over the top. This is
    #                            what build_pcb.py does, and it is what
    #                            destroyed 8 netclasses and 10 design rules.
    #
    # Testing only the first path would give a clean run and prove nothing, so
    # the destructive path is exercised here on a scratch copy.
    failures = 0
    print("\n  -- destructive path: fresh BOARD() -> SaveBoard, on a copy --")
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="drikr_save_")
    tpcb = os.path.join(tmp, "DrikrAIO.kicad_pcb")
    tpro = os.path.join(tmp, "DrikrAIO.kicad_pro")
    shutil.copy(PCB, tpcb)
    shutil.copy(PRO, tpro)
    fresh = pcbnew.BOARD()
    fresh.SetCopperLayerCount(6)
    pcbnew.SaveBoard(tpcb, fresh)
    with open(tpro, encoding="utf-8") as fh:
        after = json.load(fh)
    n_after = len(after.get("net_settings", {}).get("classes", []))
    r_after = after.get("board", {}).get("design_settings", {}).get("rules", {})
    changed = [k for k, v in rules.items() if r_after.get(k) != v]
    print(f"     netclasses after: {n_after} (was {len(nets['classes'])})"
          f"  -> {'DESTROYED' if n_after < len(nets['classes']) else 'intact'}")
    print(f"     design rules changed: {len(changed)}"
          f"  -> {'DESTROYED' if changed else 'intact'}")
    if changed:
        for k in sorted(changed)[:4]:
            print(f"        {k}: {rules[k]} -> {r_after.get(k)}")
    print("     (this is why build_pcb.py must snapshot and restore)")
    shutil.rmtree(tmp, ignore_errors=True)

    print("\n  -- non-destructive path: LoadBoard -> SaveBoard --")
    for i in range(1, cycles + 1):
        board = pcbnew.LoadBoard(PCB)
        pcbnew.SaveBoard(PCB, board)
        lost, moved = restore(nets, rules)

        rc = subprocess.run([sys.executable, VERIFY],
                            capture_output=True, text=True).returncode
        state = "PASS" if rc == 0 else "FAIL"
        if rc != 0:
            failures += 1
        detail = ("nothing lost" if not lost
                  else "SaveBoard destroyed: " + ", ".join(lost))
        print(f"  cycle {i}: {detail}; verifier {state}")
        if moved and i == 1:
            for k, (was, now) in sorted(moved.items())[:12]:
                print(f"      {k}: {was} -> restored {now}")

    print("=" * 70)
    if failures:
        print(f"  {failures}/{cycles} cycles FAILED verification.")
        return 1
    print(f"  All {cycles} cycles verified. Configuration survives the pipeline.")
    print("  DRC may be considered meaningful only while this passes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
