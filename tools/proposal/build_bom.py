#!/usr/bin/env python3
r"""Generate the bill of materials: phase, item, model, INR, link, per line.

WHY THIS EXISTS. Prices lived in competition_budget.py, phase assignment lived
in the brief's tables, models lived in a third place, and no file carried a
purchase link at all. Anyone actually buying the parts had to join three
documents by hand. This emits one table that carries all five columns and
reconciles to the programme total, so the join is done once and asserted.

WHAT IS AND IS NOT VERIFIED. Prices come from the budget model, which is the
authority. Links are a per-part table below and each carries a status:

    verified   the page was opened and the listing confirmed
    product    a product page for this exact part exists and is linked, but
               Robu.in returns 403 to automated fetches, so the price on the
               page has not been read back -- treat the INR column as the
               budget figure, not as a quoted price
    supplier   the supplier is known and named, the exact page is not
    fabricate  made in-house or by a local shop; there is nothing to link
    quote      priced by supplier quotation, not a public listing

A link is never invented to fill the column. An item with no confirmed page
says so, because a plausible-looking wrong link is worse than a blank.

Run:  python tools/proposal/build_bom.py
Emits: docs/proposal/BOM.md
       hardware/bom/RescueSwarm_BOM.csv
"""
from __future__ import annotations

import csv
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "docs", "proposal", "figures"))
import competition_budget as cb                                   # noqa: E402

# ---------------------------------------------------------------------------
# Phase assignment. Mirrors the 32-phase partition: one aircraft is built in
# eight steps, repeated three times, with instruments first and ground segment
# last. Per-aircraft rows list all three phases.
# ---------------------------------------------------------------------------
AC_PHASE = {
    "Flight controller":               "3, 13, 21",
    "Companion computer":              "4, 14, 22",
    "AI accelerator":                  "4, 14, 22",
    "GNSS RTK primary":                "5, 15, 23",
    "Camera + lens":                   "6, 16, 24",
    "RC rx, storage, cooling, mounts": "6, 16, 24",
    "Video and coordination radios":            "6, 16, 24",
    "Structure":                       "7, 17, 25",
    "Li-ion cells":                    "8, 18, 26",
    "Pack, BMS, PDB, BEC":             "8, 18, 26",
    "ESCs":                            "9, 19, 27",
    "Payload system":                  "9, 19, 27",
    "Propellers":                      "9, 19, 27",
    "Wiring, connectors":              "9, 19, 27",
    "Prop adapters":                   "9, 19, 27",
    "VEGA co-processor":               "9, 19, 27",
    "Motors":                          "2, 10, 20, 28",
}
LINE_PHASE = {
    "Thrust stand":                          "1",
    "Calibrated scale + remaining":          "1",
    "Battery chargers":                      "11",
    "Safety-pilot transmitter":              "11",
    "Fasteners, tape, connectors, filament": "12",
    "Sun hood + observer monitor":           "12",
    "RTK base receiver":                     "29",
    "Survey tripod + tribrach":              "30",
    "Remaining ground items":                "31",
    "DGCA registration":                     "32",
}

# ---------------------------------------------------------------------------
# Model and link, per part.  (model, link, status)
# ---------------------------------------------------------------------------
V, P, S, F, Q = "verified", "product", "supplier", "fabricate", "quote"
PARTS = {
 "Flight controller": (
   "Holybro Pixhawk 6C Mini",
   "https://robu.in/product/holybro-pixhawk-6c-mini-flight-controller/", P),
 "Companion computer": (
   "Raspberry Pi 5, 8 GB", "Robu.in / Silverline / Element14 India", S),
 "AI accelerator": (
   "Raspberry Pi AI HAT+, 26 TOPS (Hailo-8)",
   "Robu.in / Silverline; multiple Indian retailers", S),
 "GNSS RTK primary": (
   "Teravolt AeroNav-Pro RTK (or AeroNav-X5)",
   "https://teravolt.gitbook.io/teravolt/gps/aeronav-pro-rtk", Q),
 "Camera + lens": (
   "Arducam 12.3 MP IMX477, 1/2.3 in, 6 mm CS mount, fixed focus",
   "https://robu.in/product/arducam-hq-camera-for-jetson-nano-and-xavier-nx"
   "-12-3mp-1-2-3-inch-imx477-with-6mm-cs-mount-lens/", P),
 "Motors": ("Tarot TL96020, 5008, 340 KV", "Robokits India / IndiaMART", S),
 "ESCs": ("50-60 A continuous, 6S", "Robokits India / Robu.in", S),
 "Propellers": ("Tarot 1855 carbon, 18 in, CW/CCW", "Robokits India", S),
 "Prop adapters": ("4 mm bore self-tightening hubs (Tarot TL96020 shaft is 4 mm)",
                   "Robokits India / Robu.in", S),
 "Li-ion cells": (
   "Molicel P45B 21700, 4500 mAh, 45 A", "Robokits India (imported listing)", S),
 "Pack, BMS, PDB, BEC": ("6S 60 A BMS, distribution board, regulator",
                         "Robu.in / IndiaMART", S),
 "Structure": ("25 x 23 mm carbon tube, machined clamps", "in-house / local machine shop", F),
 "Payload system": ("Four metal-gear servos, mechanical detents",
                    "Robu.in / Robokits India", S),
 "Wiring, connectors": ("10 AWG silicone, XT90-S, JST-GH", "Robu.in / IndiaMART", S),
 "Video and coordination radios": ("3x analog 5.8 GHz VTX, 3x GCS receiver + patch, 4x SX1262 865 MHz", "supplier quotation", Q),
 "RC rx, storage, cooling, mounts": (
   "ExpressLRS 2.4 GHz receiver, storage, cooling, mounts", "Robu.in / IndiaMART", S),
 "VEGA co-processor": ("VEGA RISC-V development kit (no cost line)",
                       "C-DAC VEGA processor programme", S),
 "Thrust stand": ("20 kg load cell, HX711, power meter, in-house frame",
                  "load cell and HX711 from Robu.in; frame fabricated", F),
 "Calibrated scale + remaining": ("Bench scale, 30 kg, 1 g, certified",
                                  "IndiaMART (calibration certificate required)", S),
 "Battery chargers": ("ToolkitRC M6D, 500 W, 25 A, dual",
                      "Indian Hobby Center / Robu.in", S),
 "Safety-pilot transmitter": ("RadioMaster Boxer, ExpressLRS",
                              "IndiaMART / Robu.in", S),
 "Fasteners, tape, connectors, filament": ("Consumables", "local / Robu.in", S),
 "Sun hood + observer monitor": ("Fabricated hood, second-hand monitor",
                                 "fabricated; monitor sourced locally", F),
 "RTK base receiver": ("Second Teravolt AeroNav unit, base station",
                       "https://teravolt.gitbook.io/teravolt/gps/aeronav-x5", Q),
 "Survey tripod + tribrach": ("Photographic tripod and adapter",
                              "IndiaMART / local survey supplier", S),
 "Remaining ground items": ("Cables, mounts, spares, transport protection",
                            "local / Robu.in", S),
 "DGCA registration": ("Statutory fee, three aircraft",
                       "https://digitalsky.dgca.gov.in/", V),
}


def main() -> None:
    rows, total = [], 0

    ac = {n: (q, u) for n, q, u, _t, _x in cb.AIRCRAFT}
    for name, (qty, unit) in ac.items():
        if name not in PARTS:
            raise SystemExit(f"no PARTS entry for aircraft line {name!r}")
        model, link, status = PARTS[name]
        # Every aircraft line is bought three times. Motors are still 12: the
        # one measured in phase 2 is the FIRST of the twelve, not a thirteenth,
        # which is why phase 10 buys three for aircraft 1 and phases 20 and 28
        # buy four each.
        n = 3 * qty
        rows.append((AC_PHASE[name], name, model, unit, n, unit * n, link, status))
        total += unit * n

    for _g, group in cb.GROUPS:
        for lbl, _old, new, _note in group:
            if lbl.startswith("Air vehicles") or new == 0:
                continue
            if lbl not in PARTS:
                raise SystemExit(f"no PARTS entry for line {lbl!r}")
            model, link, status = PARTS[lbl]
            rows.append((LINE_PHASE[lbl], lbl, model, new, 1, new, link, status))
            total += new

    # Reconcile against the model's own parts subtotal.
    split = cb.tax_split()
    parts_total = sum(split.values())
    if abs(total - parts_total) > 1:
        raise SystemExit(f"BOM sums to {total:,} against model {parts_total:,}")

    hdr = ["Phase", "Item", "Model", "Unit INR", "Qty", "Line INR", "Link", "Link status"]

    csv_path = os.path.join(ROOT, "hardware", "bom", "RescueSwarm_BOM.csv")
    with io.open(csv_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        w.writerows(rows)
        w.writerow(["", "PARTS TOTAL", "", "", "", total, "", ""])

    md = [
        "# RescueSwarm — Bill of Materials",
        "",
        "Generated by `tools/proposal/build_bom.py` from the budget model. Do not",
        "hand-edit: prices come from `docs/proposal/figures/competition_budget.py`",
        "and the parts total is asserted against it.",
        "",
        "**Link status.** `verified` — page opened and confirmed. `product` — a",
        "page for this exact part is linked, but Robu.in returns 403 to automated",
        "fetches, so the price was not read back from it; treat the INR column as",
        "the budget figure, not a quoted price.",
        "`supplier` — supplier known and named, exact page not confirmed.",
        "`quote` — priced by quotation, no public listing. `fabricate` — made",
        "in-house or locally. Links are never invented to fill the column.",
        "",
        "| " + " | ".join(hdr) + " |",
        "|" + "|".join(["---"] * len(hdr)) + "|",
    ]
    for ph, item, model, unit, qty, line, link, status in rows:
        shown = f"[{link.split('/')[2]}]({link})" if link.startswith("http") else link
        md.append(f"| {ph} | {item} | {model} | {unit:,} | {qty} | {line:,} "
                  f"| {shown} | {status} |")
    # Landed total: duty falls only on the imported share of the ex-GST lines,
    # GST on those lines plus their duty, contingency on everything.
    duty = split["excl"] * (1 - cb.INDIG) * cb.DUTY
    gst = (split["excl"] + duty) * cb.GST
    landed = parts_total + duty + gst
    landed += landed * cb.CONTINGENCY

    md += ["", f"**Parts total: INR {total:,}**", "",
           f"Landed programme total, after {cb.DUTY:.0%} duty on the imported "
           f"share, {cb.GST:.0%} GST and {cb.CONTINGENCY:.0%} contingency: "
           f"**INR {landed:,.0f}**", ""]

    md_path = os.path.join(ROOT, "docs", "proposal", "BOM.md")
    io.open(md_path, "w", encoding="utf-8", newline="\n").write("\n".join(md))

    print(f"  {len(rows)} lines, parts total INR {total:,} -- reconciles")
    print(f"  links: {sum(1 for r in rows if r[7] == V)} verified, "
          f"{sum(1 for r in rows if r[7] == P)} product page, "
          f"{sum(1 for r in rows if r[7] == S)} supplier-named, "
          f"{sum(1 for r in rows if r[7] == Q)} on quotation, "
          f"{sum(1 for r in rows if r[7] == F)} fabricated")
    print(f"  wrote {os.path.relpath(md_path, ROOT)}")
    print(f"  wrote {os.path.relpath(csv_path, ROOT)}")


if __name__ == "__main__":
    main()
