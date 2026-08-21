#!/usr/bin/env python3
"""Competition-build budget: ask only for what the NIDAR entry actually needs.

The original figure (INR 28.74 L) costed a development PROGRAMME. It bought
laboratory equipment and computing the institution already owns, a full spares
set, a purchased field-data campaign and bought ground-truth apparatus. None of
that is what a competition entry needs. This recosts the ask as a competition
build; the programme and commercialisation framing moves to future work.

Rules applied, in the order they were applied:
  R1  If the institution already owns it, it is not in the ask. It is recorded
      as an institutional contribution, because that is what it is.
  R2  If it can be built rather than bought, it is costed as built.
  R3  Spares cover what CRASHES, not what fails rarely and costs a fortune.
      Accepted risks are stated, not hidden.
  R4  Hobby-grade where the failure mode is visible and the spec is easy to
      verify; professional where it is not. The autopilot, the RTK receiver,
      the accelerator, the camera and the cells stay professional.
  R5  Ground-truth apparatus is fabricated. A clothed form reads the same to a
      detector at 60 m as a bought mannequin.

Run:  python docs/proposal/figures/competition_budget.py
"""
from __future__ import annotations

# ---------------------------------------------------------------- air vehicle
# Per aircraft. "KEEP" marks a line held at professional grade on purpose.
AIRCRAFT = [
    ("Flight controller",      1, 22_600, "KEEP",
     "Holybro Pixhawk 6C Mini. Dual IMU, Pixhawk standard, ArduPilot native."),
    ("Companion computer",     1,  8_000, "KEEP",
     "Raspberry Pi 5 8 GB. THE HOST THE AUTONOMY RUNS ON -- Linux, ROS 2, the "
     "coverage planner, MAVLink routing, the mesh link and the delivery logic. "
     "It was missing: the accelerator below is a Pi AI HAT+, which communicates "
     "over the Pi 5's PCIe and is an M.2 card with nothing to plug into "
     "without it, and the camera is a CSI module with nothing to connect to. "
     "The verified BOM carried a 55,000 module WITH an integrated host; the "
     "cost pass swapped in a 20,000 accelerator and did not put the host back."),
    ("AI accelerator",         1, 11_000, "KEEP",
     "Pi AI HAT+ (Hailo-8, 26 TOPS) -- an NPU, not a computer; needs the host "
     "above, and PCIe, which only the Pi 5 exposes. PRICE CORRECTED from "
     "20,000: the part lists at 9,950-11,309 in India. THE '26 TOPS IS THE "
     "SPECIFICATION FLOOR' CLAIM WAS WRONG and is withdrawn -- the requirement "
     "is 37 inferences/s at 640 (12 tiles at the 3.06 Hz SYS-46 needs), and "
     "the 13 TOPS Hailo-8L does 60-80 FPS on that workload, clearing it 1.6x. "
     "26 TOPS is retained as MARGIN on the one budget that already fails, not "
     "as a floor; 13 TOPS is a legitimate saving if the look count is settled "
     "at <=3 Hz first."),
    ("GNSS RTK primary",       1, 18_000, "KEEP",
     "Governs 125 of 200 geotag points -- the step from 3.88 m to 0.75 m is "
     "RTK and nothing else in the budget moves the number comparably. "
     "WARNING: the part currently carried against this line is specified by "
     "its supplier as SBAS-corrected at <1.5 m CEP, which is assisted GNSS, "
     "NOT RTK. If that is the part bought, the system sits in the 3.88 m row "
     "and 125 points go with it. Resolve at P1: confirm the part, substitute "
     "a true RTK receiver, or restate the geotagging expectation."),
    ("Motors",                 4,  4_500, "hobby",
     "5008-class, 340 KV, 6S, 18 in. Requirement is 3.18 kgf per motor at "
     "T/W 2.0 with hover at 1.59 kgf (50% of max). NO PUBLISHED THRUST -- "
     "this is why the thrust stand is funded as an instrument rather than a "
     "convenience. Named parts that meet it: Tarot TL96020 at ~3,378 "
     "(marginal, 'over 3 kg' is a marketing figure not a curve) and T-Motor "
     "MN5008 at ~10,836 (4.215 kgf published, 135 g). Buy ONE and measure "
     "before committing the fleet."),
    ("Li-ion cells",          18,    700, "KEEP",
     "4500 mAh / 45 A continuous, DC-IR <=15 mOhm. Peak draw is 38.3 A/cell, "
      "so a 40 A cell leaves 4.5% margin and a Samsung 40T is a 35 A cell "
      "once the 80C cut-off is excluded. Capacity- and IR-matched: one weak "
      "cell defines the whole pack."),
    ("Structure",              1, 13_000, "KEEP",
     "In-house fabrication; institute machine shop confirmed."),
    ("Camera + lens",          1, 11_100, "KEEP",
     "Arducam IMX477 + 6 mm CS, FIXED FOCUS -- buy the bundled B0240-class "
     "part, not a motorised-focus module and not a separate lens on top of "
     "one. Hyperfocal distance is 4.15 m and the aircraft never flies below "
     "30 m, so focus set once is correct at every altitude; a focus motor "
     "buys nothing, adds a moving part on a vibrating airframe, and fails in "
     "a way that cannot be seen from the air. Sensor is 1.55 um, type 1/2.3 "
     "-- NOT the 1.82 um part the sizing chapter once assumed."),
    ("Pack, BMS, PDB, BEC",    1,  8_500, "hobby", ""),
    ("RC rx, storage, cooling, mounts", 1, 8_500, "hobby",
     "ExpressLRS receiver MUST run 3.5+ in NATIVE MAVLink mode. That mode "
     "carries RC control and MAVLink on ONE link and one autopilot UART, which "
     "is what allows the sub-GHz safety radio to be deferred. The older AirPort "
     "mode is a transparent serial bridge that CONSUMES the link -- configured "
     "that way the aircraft has telemetry and no control, and needs the second "
     "radio back. Not a preference; the deferral depends on it."),
    ("ESCs",                   4,  1_800, "hobby", "Generic 60 A. Rating is easy to verify."),
    ("Mesh node + antennas",   1,  6_000, "hobby", "Rule 8.14: three concurrent feeds."),
    ("Payload system",         1,  4_500, "hobby",
     "Metal detents retained -- a brownout must not drop a kit."),
    ("Propellers",             4,  1_000, "hobby", "Generic 18 in CF. Balance every one."),
    ("Wiring, connectors",     1,  2_400, "hobby", ""),
    ("Prop adapters",          4,    350, "hobby", ""),
    ("VEGA co-processor",       1,      0, "KEEP",
     "C-DAC ARIES v3.0. Free to top-100 teams, so it costs nothing to carry. "
     "A monitor and logger, NOT an accelerator -- RV32IM at 100 MHz with "
     "256 KB SRAM. Retained because it is the only Indian silicon on the "
     "aircraft and the indigenisation claim in Section VIII depends on it."),
]
N_AIRCRAFT = 3
PER_AIRCRAFT = sum(q * u for _, q, u, _, _ in AIRCRAFT)

# (label, original INR, this ask, note)
AIR = [
    (f"Air vehicles, {N_AIRCRAFT} x {PER_AIRCRAFT:,}", 790_203,
     PER_AIRCRAFT * N_AIRCRAFT,
     "R4. Hobby-grade propulsion and ancillaries; autopilot, RTK, accelerator, "
     "camera and cells held professional."),
    ("Relief kits (14)", 5_600, 0,
     "DEFERRED AT TEAM DIRECTION 2026-08-18. Rule C6 fixes the kit at 200 g. "
     "THIS IS THE DELIVERED PAYLOAD -- see the note in the deferred register."),
    ("Ground-truth apparatus", 35_280, 0,
     "DEFERRED AT TEAM DIRECTION 2026-08-18. Was R5, fabricated. Removing it "
     "means detection has no target to be measured against, so recall stays "
     "modelled -- the field-data campaign is deferred too."),
    ("Recovery parachutes, 3", 0, 0,
     "DEFERRED. PERMITTED, not required (rulebook-compliance 6.2). A crash is "
     "-50 against -10 for landing outside the zone: a ~40-point bet."),
]

GROUND = [
    ("GCS laptop", 85_000, 0, "R1: team-supplied."),
    ("Backup GCS laptop", 55_000, 0, "R1: team-supplied."),
    ("Portable power station", 55_000, 0, "R1: institute field power."),
    ("RTK base receiver", 38_000, 18_000,
     "A second AeroNav-1. A base needs a good antenna and a stable mount, not a "
     "different class of receiver."),
    ("Survey tripod + tribrach", 9_500, 4_000, "Photographic tripod and adapter."),
    ("Equipment cases", 44_000, 0,
     "R1: CONFIRMED HELD by the institute, 2026-08-18. Department stores."),
    ("Fire extinguisher, sand, charging bags", 11_000, 0,
     "R1: CONFIRMED HELD by the institute, 2026-08-18. Safety office. The "
     "capability is still required -- 54 Li-ion cells are cycled across this "
     "programme and thermal runaway is a real failure mode -- it is simply "
     "no longer being bought."),
    ("Safety-pilot transmitter", 16_000, 8_000, "ELRS set."),
    ("Sun hood + observer monitor", 12_000, 1_500, "R2: hood fabricated."),
    ("Remaining ground items", 62_800, 25_000,
     "Cables, mounts, field consumables. RTCM corrections ride the existing "
     "telemetry link, so no separate base-to-rover radio is carried."),
]

TEST = [
    ("3D printer", 50_000, 0, "R1: department facility."),
    ("Thrust stand", 45_000, 8_000,
     "R2, and now LOAD-BEARING: with generic motors this is the instrument that "
     "says whether the aircraft hovers."),
    ("Battery chargers", 28_000, 14_000, "One charger."),
    ("Cell tester", 13_000, 0,
     "Most 1C chargers measure per-cell IR. CONFIRM before deleting."),
    ("Soldering station", 9_000, 0, "R1: department facility."),
    ("Rotary tool + CF extraction", 8_500, 0, "R1: department facility."),
    ("Bench power supply", 8_500, 0, "R1: department facility."),
    ("Multimeters", 8_000, 0, "R1: department facility."),
    ("Charger PSU", 8_000, 0,
     "R1: CONFIRMED HELD by the institute, 2026-08-18."),
    ("Calibrated scale + remaining", 47_700, 12_000,
     "KEEP the calibrated scale -- it decides the rule C2 weigh-in."),
]

SPARES = [
    ("Spare airframe structure set", 25_000, 0,
     "DEFERRED AT TEAM DIRECTION 2026-08-18. This was the crash cover."),
    ("Spare propellers, plate and tube stock", 26_200, 0,
     "DEFERRED AT TEAM DIRECTION 2026-08-18. Propellers are the most "
     "frequently consumed item in a flight-test campaign."),
    ("Fasteners, tape, connectors, filament", 37_800, 13_000, "KEEP."),
    ("Spare battery packs", 57_000, 0, "DEFERRED."),
    ("Spare motors", 28_000, 0, "DEFERRED. 2-3 week domestic lead time is the mitigation."),
    ("Spare compute module", 38_000, 0, "DEFERRED. Accepted risk."),
    ("Spare flight controller", 26_000, 0, "DEFERRED. Accepted risk."),
    ("Spare GNSS", 18_000, 0, "DEFERRED. Accepted risk."),
    ("Spare camera + lens", 16_600, 0, "DEFERRED. Accepted risk."),
]

SOFT = [
    ("Training compute", 75_000, 0, "R1: institute GPUs."),
    ("Indian SAR field dataset", 60_000, 0, "DEFERRED. Detection recall stays MODELLED."),
    ("Insurance", 25_000, 0,
     "DEFERRED AT TEAM DIRECTION. MUST BE CONFIRMED against the rulebook and "
     "DGCA rules before any flight."),
    ("WPC / ETA licensing", 10_000, 0,
     "REMOVED. Every link is delicensed: 2.4/5.8 GHz ISM and 865-867 MHz SRD. "
     "Type approval is a supplier obligation."),
    ("DGCA registration", 5_000, 5_000,
     "KEEP. At 6.36 kg these are Small category (2-25 kg) under the Drone Rules "
     "2021 -- only Nano is broadly exempt. UIN registration is required."),
]

GROUPS = [("Air vehicle and payload", AIR), ("Ground segment", GROUND),
          ("Test equipment", TEST), ("Spares and consumables", SPARES),
          ("Software, data and regulatory", SOFT)]

# ---------------------------------------------------------------- tax status
# Line label -> ("incl" | "excl" | "exempt", why).
#   incl   dated Indian retail listing; duty and GST already paid at the till
#   excl   supplier quote or fabrication service, normally quoted ex-GST
#   exempt statutory fee
# Anything not listed defaults to "incl", because after the market-verification
# pass the great majority of this bill is retail.
TAX_STATUS = {
    # -- air vehicle: the quoted and fabricated lines --------------------
    "GNSS RTK primary":  ("excl", "Teravolt quote; RFQ, not a listing"),
    "Li-ion cells":      ("excl", "GODI quote. A public benchmark DOES now "
                              "exist: Molicel P45B -- the cell the pack is "
                              "sized on -- lists at Rs 405 at Robokits India. "
                              "Hold the GODI quote against that number."),
    "Structure":         ("excl", "in-house fabrication; machine-shop service"),
    "Payload system":    ("excl", "in-house fabrication"),
    # -- ground segment --------------------------------------------------
    "RTK base receiver": ("excl", "same Teravolt quote as the rover"),
    "Sun hood + observer monitor": ("excl", "fabricated in-house"),
    # -- test ------------------------------------------------------------
    "Thrust stand":      ("excl", "built, not bought"),
    # -- payload ----------------------------------------------------------
    "Ground-truth apparatus": ("excl", "fabricated in-house"),
    "Relief kits (14)":  ("excl", "assembled in-house"),
    # -- statutory ---------------------------------------------------------
    "DGCA registration": ("exempt", "statutory fee, no GST"),
}


def tax_split():
    """Subtotal split by tax status.

    The air-vehicle row is an aggregate of AIRCRAFT, so it is decomposed
    line by line -- otherwise the ex-GST quotes inside it (GNSS, cells,
    structure, payload fabrication) are silently treated as tax-paid retail
    and the ask is understated.
    """
    out = {"incl": 0, "excl": 0, "exempt": 0}

    for name, q, u, _tier, _note in AIRCRAFT:
        status = TAX_STATUS.get(name, ("incl", ""))[0]
        out[status] += q * u * N_AIRCRAFT

    for _, rows in GROUPS:
        for lbl, _old, new, _note in rows:
            if new == 0 or lbl.startswith("Air vehicles"):
                continue          # aircraft handled above
            key = lbl.split(",")[0].strip()
            status = TAX_STATUS.get(lbl, TAX_STATUS.get(key, ("incl", "")))[0]
            out[status] += new
    return out

# Confirmed held by the institute on 2026-08-18, with the amount the request
# had ACTUALLY BUDGETED for each. The institutional contribution is credited at
# this figure rather than at the original-programme price: we would have spent
# 14,500 on these, not 63,000, and claiming the larger number would overstate
# the institute's share of a document the institute itself will audit.
CONFIRMED_HELD = {
    "Equipment cases": 9_000,
    "Fire extinguisher, sand, charging bags": 4_000,
    "Charger PSU": 1_500,
}

DUTY, GST, CONTINGENCY = 0.22, 0.18, 0.15
INDIG = 0.355         # COMPUTED, not estimated, from the per-line Indian
                      # fractions of the adopted configuration. Falls from 0.58
                      # in the fully specified aircraft: the imported autopilot
                      # and generic propulsion are what make it affordable.
ORIGINAL = 2_873_880


def main():
    print("=" * 78)
    print(f"AIR VEHICLE  -  {PER_AIRCRAFT:,} per aircraft")
    print("=" * 78)
    for n, q, u, tier, note in AIRCRAFT:
        mark = "KEEP " if tier == "KEEP" else "     "
        print(f" {mark}{n:<34}{q:>3} x {u:>6,} = {q*u:>7,}")
    print(f" {'':5}{'TOTAL':<34}{'':>12}{PER_AIRCRAFT:>8,}")

    print("\n" + "=" * 78)
    print("PROGRAMME")
    print("=" * 78)
    old_t = new_t = inst = 0
    for name, rows in GROUPS:
        o = sum(r[1] for r in rows)
        n_ = sum(r[2] for r in rows)
        old_t += o
        new_t += n_
        print(f"\n{name}")
        for lbl, a, b, note in rows:
            if a != b:
                if b == 0 and note.startswith("R1"):
                    # Credit newly confirmed items at what we would have SPENT,
                    # not at the original-programme price, so this agrees with
                    # the university workbook instead of quietly diverging.
                    inst += CONFIRMED_HELD.get(lbl, a)
                    tag = "  <-- institutional"
                elif b == 0:
                    tag = "  <-- deferred/removed"
                else:
                    tag = ""
                print(f"   {lbl:<40}{a:>8,} -> {b:>8,}{tag}")
        print(f"   {'subtotal':<40}{o:>8,} -> {n_:>8,}   ({n_-o:>+8,})")

    # Tax only what is genuinely untaxed. See TAX_STATUS.
    split = tax_split()
    duty = split["excl"] * (1 - INDIG) * DUTY
    gst = (split["excl"] + duty) * GST
    cont = (new_t + duty + gst) * CONTINGENCY
    total = new_t + duty + gst + cont
    print("\n" + "=" * 78)
    print(f"  {'SUBTOTAL':<40}{old_t:>8,} -> {new_t:>8,}")
    print()
    print(f"  {'tax-inclusive retail (no tax added)':<40}{split['incl']:>8,}")
    print(f"  {'ex-GST quotes and services (taxed)':<40}{split['excl']:>8,}")
    print(f"  {'statutory, exempt':<40}{split['exempt']:>8,}")
    print(f"  {'duty + freight on the ex-tax residual':<40}{'':>8}    {duty:>8,.0f}")
    print(f"  {'GST @ 18% on the ex-tax lines only':<40}{'':>8}    {gst:>8,.0f}")
    print(f"  {'contingency @ 15%':<40}{'':>8}    {cont:>8,.0f}")
    print(f"  {'COMPETITION ASK':<40}{'':>8}    {total:>8,.0f}   ({total/1e5:.2f} L)")
    print(f"  {'original programme ask':<40}{'':>8}    {ORIGINAL:>8,}   ({ORIGINAL/1e5:.2f} L)")
    print(f"  {'reduction':<40}{'':>8}    {total-ORIGINAL:>8,.0f}"
          f"   ({(total-ORIGINAL)/ORIGINAL:+.0%})")
    print("=" * 78)
    print(f"  Institutional contribution (already held): {inst:,}")
    print("=" * 78)
    return total


if __name__ == "__main__":
    main()
