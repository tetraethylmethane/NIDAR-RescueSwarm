#!/usr/bin/env python3
"""Freeze / verify the pre-routing baseline.

A freeze that is only a label in a document is not a freeze. This records a
SHA-256 for every frozen artefact plus the state assertions that were true at
freeze time, so any later drift is detectable rather than assumed absent.

    python hardware/tools/freeze.py --write    # take the freeze
    python hardware/tools/freeze.py            # verify against it

Verify exits non-zero if any frozen file changed or any assertion no longer
holds.
"""
import hashlib
import json
import os
import subprocess
import sys

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HW)
MANIFEST = os.path.join(ROOT, "docs", "freeze-manifest.json")

FROZEN = [
    "DrikrAIO.kicad_pcb",
    "DrikrAIO.kicad_pro",
    "DrikrAIO.kicad_dru",
    "DrikrAIO.kicad_sch",
    "ESC.kicad_sch",
    "esc_power.kicad_sch",
    "rp2350a.kicad_sch",
    "power.kicad_sch",
    "imu.kicad_sch",
    "osd.kicad_sch",
    "blackbox.kicad_sch",
    "pads.kicad_sch",
    "rx_esp32c3_sx1281.kicad_sch",
    "lib.pretty/BSC014N06NS_PG-TDSON-8.kicad_mod",
    "fp-lib-table",
    "sym-lib-table",
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def assertions():
    """State that must remain true while the baseline is frozen."""
    out, ok = {}, True

    pro = json.load(open(os.path.join(HW, "DrikrAIO.kicad_pro"), encoding="utf-8"))
    cls = {c["name"]: c for c in pro["net_settings"]["classes"]}
    rules = pro["board"]["design_settings"]["rules"]
    out["netclass_count"] = len(cls)
    out["phase_track_mm"] = cls.get("Phase", {}).get("track_width")
    out["vbat_track_mm"] = cls.get("VBAT", {}).get("track_width")
    out["min_clearance_mm"] = rules.get("min_clearance")

    # no routing
    pcb = open(os.path.join(HW, "DrikrAIO.kicad_pcb"),
               encoding="utf-8", errors="ignore").read()
    out["track_segments"] = pcb.count("\n\t(segment")
    out["vias"] = pcb.count("\n\t(via")

    # MOSFET must not be committed
    committed = 0
    for f in os.listdir(HW):
        if f.endswith(".kicad_sch"):
            if "BSC014N06NS" in open(os.path.join(HW, f), encoding="utf-8",
                                     errors="ignore").read():
                committed += 1
    out["schematic_files_with_bsc014n06ns"] = committed

    # no manufacturing outputs anywhere in the project
    mfg = []
    for dirpath, _, files in os.walk(ROOT):
        if "KiCad-Library" in dirpath:
            continue
        for f in files:
            if f.lower().endswith((".gbr", ".drl", ".gbrjob", ".gko")):
                mfg.append(os.path.join(dirpath, f))
    out["manufacturing_outputs"] = len(mfg)

    return out


EXPECTED = {
    "netclass_count": 8,
    "phase_track_mm": 6.6,
    "vbat_track_mm": 6.6,
    "min_clearance_mm": 0.09,
    "track_segments": 0,
    "vias": 0,
    "schematic_files_with_bsc014n06ns": 0,
    "manufacturing_outputs": 0,
}


def main():
    write = "--write" in sys.argv
    files = {}
    missing = []
    for rel in FROZEN:
        p = os.path.join(HW, rel.replace("/", os.sep))
        if os.path.exists(p):
            files[rel] = sha(p)
        else:
            missing.append(rel)

    state = assertions()

    if write:
        man = {
            "schema": "drikraio.freeze/1",
            "frozen_at": "2026-09-05",
            "frozen_state": "PRE-ROUTING BASELINE",
            "routing_status": "BLOCKED",
            "thermal_status": "MARGINAL",
            "note": "Frozen. Do not route, do not commit BSC014N06NS to the "
                    "schematic, do not generate manufacturing outputs. "
                    "Unfreezing is a deliberate, reviewed act.",
            "assertions": state,
            "sha256": files,
        }
        json.dump(man, open(MANIFEST, "w", encoding="utf-8"), indent=2)
        print(f"FROZEN. {len(files)} artefacts recorded in "
              f"{os.path.relpath(MANIFEST, ROOT)}")
        for k, v in state.items():
            print(f"   {k}: {v}")
        if missing:
            print(f"   WARNING, not found: {missing}")
        return 0

    # ---- verify ----
    if not os.path.exists(MANIFEST):
        print("  FAIL  no freeze manifest; run with --write first")
        return 2
    man = json.load(open(MANIFEST, encoding="utf-8"))
    problems = []

    print("FREEZE VERIFICATION")
    print("=" * 66)
    print(f"  frozen at {man['frozen_at']} -- {man['frozen_state']}")

    for rel, want in man["sha256"].items():
        got = files.get(rel)
        if got is None:
            problems.append(f"{rel} is MISSING")
            print(f"  FAIL  {rel} missing")
        elif got != want:
            problems.append(f"{rel} CHANGED")
            print(f"  FAIL  {rel} changed since freeze")
    for rel in files:
        if rel not in man["sha256"]:
            print(f"  note  {rel} is new since the freeze")

    for k, want in man["assertions"].items():
        got = state.get(k)
        if got != want:
            problems.append(f"{k}: {got}, frozen at {want}")
            print(f"  FAIL  {k} is {got}, frozen at {want}")

    for k, want in EXPECTED.items():
        if state.get(k) != want:
            msg = f"{k} violates the freeze contract: {state.get(k)} != {want}"
            if msg not in problems:
                problems.append(msg)
                print(f"  FAIL  {msg}")

    print("=" * 66)
    if problems:
        print(f"  FREEZE BROKEN -- {len(problems)} problem(s)")
        return 1
    print(f"  INTACT. {len(files)} artefacts unchanged; all assertions hold.")
    print("  0 tracks, 0 vias, 8 netclasses, Phase/VBAT 6.6 mm,")
    print("  min_clearance 0.09, MOSFET uncommitted, no manufacturing output.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
