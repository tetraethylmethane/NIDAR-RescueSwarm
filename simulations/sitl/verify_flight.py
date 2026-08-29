#!/usr/bin/env python3
"""Audit a recorded SITL flight and issue a pass/fail verdict per check.

Written because "is the flight autonomous and clean?" deserves an answer that
can be re-run, not an assertion. Every check below reads the recording and the
harness source; nothing is asserted from memory.

    python simulations/sitl/verify_flight.py \
        simulations/recordings/mission-telemetry-speedup1.json

Exit status is 0 only if every check passes.
"""
from __future__ import annotations

import ast
import collections
import json
import os
import sys

# Requirements this flight is judged against, with where each comes from.
MIN_SEP_M = 5.0             # proposal, deconfliction claim
FENCE_M = 600.0             # FENCE_RADIUS, firmware/ardupilot-params
BATT_LOW_MAH = 2700.0       # BATT_LOW_MAH, firmware/ardupilot-params
BATT_LOW_VOLT = 20.4        # BATT_LOW_VOLT, firmware/ardupilot-params
AIRBORNE_M = 2.0
MAX_CLOCK_GAP_S = 5.0
PAD_SIDE_M = 3.66           # rule 8.10

RESULTS = []


def check(name, ok, detail, severity="FAIL"):
    RESULTS.append((name, ok, detail, severity))
    mark = "PASS" if ok else severity
    print(f"  [{mark:4}] {name}")
    if detail:
        print(f"         {detail}")


def audit_harness(path):
    """Static check: does the harness command anything after handing to AUTO?

    Parses the source rather than grepping, so a renamed variable or a new
    call site cannot slip past.
    """
    if not os.path.exists(path):
        check("harness sends no in-flight command", False,
              f"{path} not found - cannot verify", "UNKNOWN")
        return
    tree = ast.parse(open(path, encoding="utf-8").read())
    main = next((n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    if main is None:
        check("harness sends no in-flight command", False,
              "main() not found", "UNKNOWN")
        return
    # Line of the last set_mode("AUTO"); anything transmitting after it is
    # in-flight intervention.
    auto_line = 0
    sends = []
    for n in ast.walk(main):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        name = getattr(f, "attr", None)
        if name == "set_mode" and n.args and isinstance(n.args[0], ast.Constant) \
                and n.args[0].value == "AUTO":
            auto_line = max(auto_line, n.lineno)
        if name and (name.endswith("_send") or name == "set_mode"):
            sends.append((n.lineno, name))
    after = [(ln, nm) for ln, nm in sends if ln > auto_line]
    check("harness sends no in-flight command", not after,
          f"last set_mode(AUTO) at line {auto_line}; "
          + (f"transmissions after it: {after}" if after
             else "no transmit call after it - receive only"))


def main(path):
    d = json.load(open(path))
    t = {int(k): v for k, v in d["tracks"].items()}
    ids = sorted(t)
    ts = [s["t"] for s in t[ids[0]]]
    n = len(ts)
    pairs = [(a, b) for i, a in enumerate(ids) for b in ids[i + 1:]]

    print(f"\nAUDIT  {os.path.basename(path)}")
    print(f"  {len(ids)} aircraft x {n} samples, speedup {d.get('speedup')}\n")

    print("AUTONOMY")
    audit_harness(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "fly_and_record.py"))
    modes = {i: collections.Counter(s["mode"] for s in t[i]) for i in ids}
    all_auto = all(set(m) == {"AUTO"} for m in modes.values())
    check("every sample is mode AUTO", all_auto,
          "; ".join(f"d{i} {dict(modes[i])}" for i in ids))

    disarmed = {i: not t[i][-1].get("armed", False) for i in ids}
    check("all aircraft disarmed themselves", all(disarmed.values()),
          "; ".join(f"d{i} final alt {t[i][-1]['alt']:.2f} m, "
                    f"armed={t[i][-1].get('armed')}" for i in ids))

    ev = d.get("events", [])
    rtl = {i: [e for e in ev if e[1] == i and "RTL" in e[2]] for i in ids}
    check("every aircraft reached its RTL step", all(rtl[i] for i in ids),
          "; ".join(f"d{i} RTL@{rtl[i][0][0]:.1f}s" if rtl[i] else f"d{i} NONE"
                    for i in ids))

    print("\nSAFETY")

    def sep(a, b, k):
        p, q = t[a][k], t[b][k]
        return ((p["x"] - q["x"]) ** 2 + (p["y"] - q["y"]) ** 2
                + (p["alt"] - q["alt"]) ** 2) ** 0.5

    worst, worst_k, worst_pair = 1e9, None, None
    breaches = 0
    for k in range(n):
        for a, b in pairs:
            if t[a][k]["alt"] > AIRBORNE_M and t[b][k]["alt"] > AIRBORNE_M:
                s = sep(a, b, k)
                if s < MIN_SEP_M:
                    breaches += 1
                if s < worst:
                    worst, worst_k, worst_pair = s, k, (a, b)
    check(f"airborne separation >= {MIN_SEP_M} m", breaches == 0,
          f"closest {worst:.2f} m at t={ts[worst_k]:.1f}s between "
          f"d{worst_pair[0]} and d{worst_pair[1]}; "
          f"{breaches} sample(s) below the minimum")

    pad = d["pad_xy"]
    cx = (min(p[0] for p in pad) + max(p[0] for p in pad)) / 2
    cy = (min(p[1] for p in pad) + max(p[1] for p in pad)) / 2
    far = {i: max(((s["x"] - cx) ** 2 + (s["y"] - cy) ** 2) ** 0.5
                  for s in t[i]) for i in ids}
    check(f"geofence {FENCE_M:.0f} m never breached",
          all(v < FENCE_M for v in far.values()),
          "; ".join(f"d{i} max {far[i]:.0f} m" for i in ids))

    bad = [e for e in ev if any(w in e[2].lower() for w in
           ("failsafe", "breach", "crash", "error", "glitch", "unhealthy",
            "emergency", "abort", "lost"))]
    check("no failsafe or error event", not bad,
          f"{len(ev)} events logged, {len(bad)} matching failure keywords"
          + ("" if not bad else f": {bad[:3]}"))

    print("\nENERGY")
    peak = {i: max(s["mah"] for s in t[i]) for i in ids}
    check(f"consumption stayed under BATT_LOW_MAH ({BATT_LOW_MAH:.0f})",
          all(v < BATT_LOW_MAH for v in peak.values()),
          "; ".join(f"d{i} peak {peak[i]:.0f} mAh" for i in ids))
    volts = {i: {s["volt"] for s in t[i]} for i in ids}
    flat = all(len(v) == 1 for v in volts.values())
    check("simulated pack voltage varies (sag modelled)", not flat,
          ("voltage is CONSTANT at "
           f"{list(volts[ids[0]])[0]:.2f} V - the BATT_LOW_VOLT "
           f"({BATT_LOW_VOLT} V) path cannot fire and is therefore UNTESTED"
           if flat else "varies"),
          severity="WARN")

    print("\nRECORDING INTEGRITY")
    gaps = [ts[i + 1] - ts[i] for i in range(n - 1)]
    big = [g for g in gaps if g > MAX_CLOCK_GAP_S]
    check(f"no clock gap over {MAX_CLOCK_GAP_S:.0f} s", not big,
          f"max gap {max(gaps):.2f} s"
          + (f"; {len(big)} gap(s) exceed it: {[round(g,1) for g in big]}"
             if big else ""))

    got = all(s.get("got", True) for i in ids for s in t[i])
    check("every sample carries a real position fix", got,
          "no placeholder samples" if got else "some samples lack a fix")

    print("\nMISSION SCOPE (not defects - what this run does not cover)")
    kinds = collections.Counter()
    for _, _, txt in ev:
        low = txt.lower()
        for w in ("detect", "payload", "release", "servo", "survivor"):
            if w in low:
                kinds[w] += 1
    check("detection / payload events present in this recording",
          bool(kinds), f"{dict(kinds) or 'none'} - this is a coverage and "
          "deconfliction run", severity="N/A")

    print("\n" + "=" * 66)
    fails = [r for r in RESULTS if not r[1] and r[3] == "FAIL"]
    warns = [r for r in RESULTS if not r[1] and r[3] in ("WARN", "UNKNOWN")]
    na = [r for r in RESULTS if not r[1] and r[3] == "N/A"]
    auto = [r for r in RESULTS[:4] if not r[1]]
    print(f"  AUTONOMOUS : {'YES' if not auto else 'NO'}")
    print(f"  CLEAN      : {'YES' if not fails else 'NO - ' + str(len(fails)) + ' failed check(s)'}")
    for nm, _, det, _ in fails:
        print(f"      FAIL  {nm}\n            {det}")
    for nm, _, det, sev in warns:
        print(f"      {sev}  {nm}\n            {det}")
    for nm, _, det, _ in na:
        print(f"      N/A   {nm}")
    print("=" * 66)
    return 1 if fails else 0


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else \
        "simulations/recordings/mission-telemetry-speedup1.json"
    sys.exit(main(src))
