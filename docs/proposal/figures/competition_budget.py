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
    ("AI accelerator",         1, 20_000, "KEEP",
     "26 TOPS. The specification floor, not a preference."),
    ("GNSS RTK primary",       1, 18_000, "KEEP",
     "No cheaper RTK-capable part exists. Governs 125 of 200 geotag points."),
    ("Motors",                 4,  4_500, "hobby",
     "Generic 5008-class. NO PUBLISHED THRUST -- verify on the thrust stand."),
    ("Li-ion cells",          18,    700, "KEEP",
     "Capacity- and IR-matched. One weak cell defines the whole pack."),
    ("Structure",              1, 13_000, "KEEP",
     "In-house fabrication; institute machine shop confirmed."),
    ("Camera + lens",          1, 11_100, "KEEP",
     "Arducam IMX477 + 6 mm. Pi-compatible; GSD drives detection."),
    ("Pack, BMS, PDB, BEC",    1,  8_500, "hobby", ""),
    ("RC rx, storage, cooling, mounts", 1, 8_500, "hobby", ""),
    ("ESCs",                   4,  1_800, "hobby", "Generic 60 A. Rating is easy to verify."),
    ("Mesh node + antennas",   1,  6_000, "hobby", "Rule 8.14: three concurrent feeds."),
    ("Payload system",         1,  4_500, "hobby",
     "Metal detents retained -- a brownout must not drop a kit."),
    ("Propellers",             4,  1_000, "hobby", "Generic 18 in CF. Balance every one."),
    ("Wiring, connectors",     1,  2_400, "hobby", ""),
    ("Prop adapters",          4,    350, "hobby", ""),
]
N_AIRCRAFT = 3
PER_AIRCRAFT = sum(q * u for _, q, u, _, _ in AIRCRAFT)

# (label, original INR, this ask, note)
AIR = [
    (f"Air vehicles, {N_AIRCRAFT} x {PER_AIRCRAFT:,}", 790_203,
     PER_AIRCRAFT * N_AIRCRAFT,
     "R4. Hobby-grade propulsion and ancillaries; autopilot, RTK, accelerator, "
     "camera and cells held professional."),
    ("Relief kits (14)", 5_600, 5_600, "Rule C6 fixes the kit at 200 g."),
    ("Ground-truth apparatus", 35_280, 4_860,
     "R5. Mannequins, mats, markers, clothing and dummy kits all fabricated. "
     "Dummy kits and clothing are BETTER made than bought -- exact 200 g mass, "
     "and wider colour variety than matched sets."),
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
    ("Equipment cases", 44_000, 9_000, "One aircraft case, two foam-lined crates."),
    ("Fire extinguisher, sand, charging bags", 11_000, 4_000,
     "KEEP THE CAPABILITY, correct the price. 54 Li-ion cells are cycled across "
     "this programme; thermal runaway is a real failure mode."),
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
    ("Charger PSU", 8_000, 1_500, "Used 12 V server supply."),
    ("Calibrated scale + remaining", 47_700, 12_000,
     "KEEP the calibrated scale -- it decides the rule C2 weigh-in."),
]

SPARES = [
    ("Spare airframe structure set", 25_000, 25_000, "KEEP. What a crash consumes."),
    ("Spare propellers, plate and tube stock", 26_200, 21_400, "KEEP. Consumables."),
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

DUTY, GST, CONTINGENCY = 0.22, 0.18, 0.15
INDIG = 0.45          # falls from 0.61: imported autopilot and generic propulsion
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
                    inst += a
                    tag = "  <-- institutional"
                elif b == 0:
                    tag = "  <-- deferred/removed"
                else:
                    tag = ""
                print(f"   {lbl:<40}{a:>8,} -> {b:>8,}{tag}")
        print(f"   {'subtotal':<40}{o:>8,} -> {n_:>8,}   ({n_-o:>+8,})")

    duty = new_t * (1 - INDIG) * DUTY
    gst = (new_t + duty) * GST
    cont = (new_t + duty + gst) * CONTINGENCY
    total = new_t + duty + gst + cont
    print("\n" + "=" * 78)
    print(f"  {'SUBTOTAL':<40}{old_t:>8,} -> {new_t:>8,}")
    print(f"  {'duty + freight on imported residual':<40}{'':>8}    {duty:>8,.0f}")
    print(f"  {'GST @ 18%':<40}{'':>8}    {gst:>8,.0f}")
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
