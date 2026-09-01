#!/usr/bin/env python3
"""Split the competition ask across the four delivery tracks.

WHY THIS EXISTS. competition_budget.py is the single source of truth for what
the programme costs. It says nothing about WHO SPENDS IT, and the development
plan 1.3 assigns the work to four tracks plus a shared pool. Without a split,
every track competes for one undifferentiated pot and no track lead can be held
to a number.

THE INVARIANT. This file must not restate a single rupee. Every figure is
derived from competition_budget, and the sum of the four track asks plus the
shared pool must equal the master COMPETITION ASK exactly. main() asserts it.
If that assertion ever fails, this file is wrong and the master is right.

The tax formulas are all LINEAR in the per-track pools -- duty on the ex-GST
residual, GST on that plus duty, contingency on the whole -- which is what makes
an exact partition possible rather than an approximate allocation.

Run:  python docs/proposal/figures/track_budget.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import competition_budget as cb  # noqa: E402

TRACKS = {
    "A": "Air vehicle -- frame, propulsion, power, payload mechanism, assembly",
    "B": "Avionics & comms -- FC, companion computer, GNSS/RTK, mesh, safety link",
    "C": "Autonomy & GCS -- coverage planner, allocation, state machine, SITL",
    "D": "Perception -- detector, tiling, geotagging, calibration, dataset",
    "S": "Shared -- safety, statutory, field kit, consumables no single track owns",
}

# --- per-aircraft lines. These multiply by N_AIRCRAFT. ----------------------
# The companion computer sits in B rather than C: C's software runs ON it, but
# it is avionics hardware that B specifies, powers, cools and integrates.
AIRCRAFT_TRACK = {
    "Flight controller": "B",
    "Companion computer": "B",
    "AI accelerator": "D",
    "GNSS RTK primary": "B",
    "Motors": "A",
    "Li-ion cells": "A",
    "Structure": "A",
    "Camera + lens": "D",
    "Pack, BMS, PDB, BEC": "A",
    "RC rx, storage, cooling, mounts": "B",
    "ESCs": "A",
    "Video and coordination radios": "B",
    "Payload system": "A",
    "Propellers": "A",
    "Wiring, connectors": "A",
    "Prop adapters": "A",
    "VEGA co-processor": "B",
}

# --- programme lines --------------------------------------------------------
LINE_TRACK = {
    # air vehicle and payload
    "Relief kits (14)": "A",
    "Ground-truth apparatus": "D",
    "Recovery parachutes, 3": "A",
    # ground segment
    "GCS laptop": "C",
    "Backup GCS laptop": "C",
    "Portable power station": "S",
    "RTK base receiver": "B",
    "Survey tripod + tribrach": "B",
    "Equipment cases": "S",
    "Fire extinguisher, sand, charging bags": "S",
    "Safety-pilot transmitter": "B",
    "Sun hood + observer monitor": "C",
    "Remaining ground items": "S",
    # test equipment
    "3D printer": "A",
    "Thrust stand": "A",
    "Battery chargers": "A",
    "Cell tester": "A",
    "Soldering station": "S",
    "Rotary tool + CF extraction": "A",
    "Bench power supply": "S",
    "Multimeters": "S",
    "Charger PSU": "A",
    "Calibrated scale + remaining": "A",
    # spares and consumables
    "Spare airframe structure set": "A",
    "Spare propellers, plate and tube stock": "A",
    "Fasteners, tape, connectors, filament": "S",
    "Spare battery packs": "A",
    "Spare motors": "A",
    "Spare compute module": "B",
    "Spare flight controller": "B",
    "Spare GNSS": "B",
    "Spare camera + lens": "D",
    # software, data, regulatory
    "Training compute": "D",
    "Indian SAR field dataset": "D",
    "Insurance": "S",
    "WPC / ETA licensing": "B",
    "DGCA registration": "S",
}


def per_aircraft_by_track():
    """The per-aircraft figure, partitioned. Read from cb.PER_AIRCRAFT."""
    out = {t: 0 for t in TRACKS}
    for name, q, u, _tier, _note in cb.AIRCRAFT:
        out[AIRCRAFT_TRACK[name]] += q * u
    return out


def collect():
    """Subtotal and tax pools per track, mirroring cb.tax_split() exactly."""
    sub = {t: 0 for t in TRACKS}
    pools = {t: {"incl": 0, "excl": 0, "exempt": 0} for t in TRACKS}
    lines = {t: [] for t in TRACKS}

    # the aircraft aggregate, decomposed the same way the master decomposes it
    for name, q, u, tier, note in cb.AIRCRAFT:
        t = AIRCRAFT_TRACK[name]
        amt = q * u * cb.N_AIRCRAFT
        status = cb.TAX_STATUS.get(name, ("incl", ""))[0]
        sub[t] += amt
        pools[t][status] += amt
        lines[t].append((f"{name} ({q} x {u:,} x {cb.N_AIRCRAFT} ac)", amt, tier, note))

    for _group, rows in cb.GROUPS:
        for lbl, _old, new, note in rows:
            if lbl.startswith("Air vehicles"):
                continue                      # handled above
            t = LINE_TRACK[lbl]
            sub[t] += new
            lines[t].append((lbl, new, "", note))
            if new == 0:
                continue                      # deferred: no tax on nothing
            key = lbl.split(",")[0].strip()
            status = cb.TAX_STATUS.get(lbl, cb.TAX_STATUS.get(key, ("incl", "")))[0]
            pools[t][status] += new
    return sub, pools, lines


def ask_for(subtotal, pool):
    """The same linear chain the master applies, on one track's pools."""
    duty = pool["excl"] * (1 - cb.INDIG) * cb.DUTY
    gst = (pool["excl"] + duty) * cb.GST
    cont = (subtotal + duty + gst) * cb.CONTINGENCY
    return {"subtotal": subtotal, "duty": duty, "gst": gst,
            "contingency": cont, "total": subtotal + duty + gst + cont}


def main():
    sub, pools, lines = collect()
    asks = {t: ask_for(sub[t], pools[t]) for t in TRACKS}

    print("=" * 78)
    print("PER-AIRCRAFT SPEND BY TRACK")
    print("=" * 78)
    pa = per_aircraft_by_track()
    for t in "ABCDS":
        if pa[t]:
            print(f"  {t}  {pa[t]:>8,}   ({pa[t]/cb.PER_AIRCRAFT:>5.1%} of {cb.PER_AIRCRAFT:,})")
    assert sum(pa.values()) == cb.PER_AIRCRAFT, "per-aircraft split lost money"
    print(f"     {sum(pa.values()):>8,}   reconciles to PER_AIRCRAFT")

    print("\n" + "=" * 78)
    print("TRACK ASKS")
    print("=" * 78)
    print(f"  {'':3}{'subtotal':>10}{'duty':>9}{'GST':>9}{'cont.':>9}{'ASK':>11}")
    for t in "ABCDS":
        a = asks[t]
        print(f"  {t}  {a['subtotal']:>10,}{a['duty']:>9,.0f}{a['gst']:>9,.0f}"
              f"{a['contingency']:>9,.0f}{a['total']:>11,.0f}")
    tot = sum(a["total"] for a in asks.values())
    print(f"  {'':3}{'':10}{'':9}{'':9}{'TOTAL':>9}{tot:>11,.0f}")

    print("\n" + "=" * 78)
    print("RECONCILIATION AGAINST THE MASTER BUDGET")
    print("=" * 78)
    master_sub = sum(sum(r[2] for r in rows) for _g, rows in cb.GROUPS)
    msplit = cb.tax_split()
    master = ask_for(master_sub, msplit)["total"]
    print(f"  sum of track asks   {tot:>12,.2f}")
    print(f"  master ask          {master:>12,.2f}")
    print(f"  difference          {tot-master:>12,.2f}")
    assert abs(tot - master) < 0.01, "TRACK SPLIT DOES NOT RECONCILE"
    assert sum(sub.values()) == master_sub, "subtotals do not partition"
    print("  RECONCILES EXACTLY")

    print("\n" + "=" * 78)
    print("WHAT EACH TRACK IS FUNDED FOR")
    print("=" * 78)
    for t in "ABCDS":
        print(f"\n  TRACK {t} -- {TRACKS[t]}")
        print(f"  {'-'*74}")
        for lbl, amt, tier, _note in sorted(lines[t], key=lambda r: -r[1]):
            if amt == 0:
                continue
            mark = "KEEP " if tier == "KEEP" else "     "
            print(f"   {mark}{lbl:<52}{amt:>10,}")
        deferred = [l for l, a, _t, _n in lines[t] if a == 0]
        if deferred:
            print(f"   {'':5}deferred/held: {', '.join(sorted(deferred))}")
        print(f"   {'':5}{'TRACK ASK (incl. tax and contingency)':<52}"
              f"{asks[t]['total']:>10,.0f}")
    return asks


if __name__ == "__main__":
    main()
