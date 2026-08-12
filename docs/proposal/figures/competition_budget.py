#!/usr/bin/env python3
"""Competition-build budget: ask only for what the NIDAR entry actually needs.

The earlier figure (INR 28.74 L) costed a development PROGRAMME -- it bought
laboratory equipment, a full spares set and a field data campaign that a
competition entry does not require, and that the host institution largely
already owns. This recosts the ask as a competition build and moves the
programme framing to future work.

Three rules applied:
  R1  If the department already owns it, it is not in the ask. It is listed as
      an institutional contribution instead, because that is what it is.
  R2  If it can be built rather than bought, it is costed as built.
  R3  Spares cover what CRASHES (props, motors, arms, packs), not what fails
      rarely and costs a fortune (compute, autopilot, GNSS, camera). The
      accepted risk is stated rather than hidden.

Run:  python docs/proposal/figures/competition_budget.py
"""
from __future__ import annotations

# (label, old INR, new INR, note)
AIR = [
    ("Air vehicles, 3 x Option B", 790_203, 774_303,
     "Option B substitutions, less in-house fabrication of the CNC-cut plates, "
     "machined arm clamps and motor mounts. CONFIRMED: institute machine shop."),
    ("Recovery parachutes, 3", 0, 0,
     "DEFERRED. PERMITTED, not required -- rulebook-compliance 6.2. Accepted risk: "
     "a crash costs -50 against -10 for landing outside the zone, so this is a "
     "~40-point bet, not a compliance item. First reinstatement."),
    ("Payload and relief kits", 40_880, 40_880, "Unchanged."),
]

GROUND = [
    ("GCS laptop", 85_000, 0,
     "R1: team-supplied. Load is three H.264 decodes and a Python GCS."),
    ("Backup GCS laptop", 55_000, 0,
     "R1: team-supplied. A GCS failure on the day scores zero, so a standby is "
     "still required -- it just does not have to be bought."),
    ("Portable power station", 55_000, 0,
     "R1: institute field power confirmed. 3 x 292 Wh at ~85% is 1.03 kWh."),
    ("Equipment cases", 44_000, 24_000, "Foam layout is what setup time depends on, not the shell."),
    ("RTK base receiver", 38_000, 38_000, "KEEP. Governs the whole geolocation budget."),
    ("Safety-pilot transmitter", 16_000, 8_000, "A basic ELRS transmitter is sufficient."),
    ("Sun hood + observer monitor", 12_000, 6_000, "Hood fabricated in-house."),
    ("Fire extinguisher, sand", 11_000, 11_000, "KEEP. Safety equipment, do not cut."),
    ("Survey tripod + tribrach", 9_500, 9_500, "KEEP. The RTK base needs it."),
    ("Remaining ground items", 62_800, 25_000,
     "Trimmed. This was a bulk placeholder with no itemisation behind it."),
]

TEST = [
    ("3D printer", 50_000, 0, "R1: department facility."),
    ("Thrust stand", 45_000, 8_000,
     "R2: load cell + HX711 + printed fixture. Building and calibrating it is a "
     "better answer to the motor-thrust risk than buying it."),
    ("Battery chargers", 28_000, 14_000, "One charger, not two."),
    ("Cell tester", 13_000, 13_000, "KEEP. Capacity and IR matching is a real failure mode."),
    ("Soldering station", 9_000, 0, "R1: department facility."),
    ("Rotary tool + CF extraction", 8_500, 0, "R1: department facility."),
    ("Bench power supply", 8_500, 0, "R1: department facility."),
    ("Multimeters", 8_000, 0, "R1: department facility."),
    ("Charger PSU", 8_000, 8_000, "Needed to drive the charger at 1C."),
    ("Calibrated scale + remaining", 47_700, 20_000,
     "KEEP the calibrated scale: it decides the rule C2 weigh-in."),
]

SPARES = [
    ("Spare battery packs", 57_000, 0, "DEFERRED. Reinstate if a pack is damaged."),
    ("Spare motors, 4", 28_000, 0, "DEFERRED. 2-3 week domestic lead time is the mitigation."),
    ("Spare airframe structure set", 25_000, 25_000, "KEEP. This is what a crash consumes."),
    ("Spare propeller pairs", 13_200, 8_400, "Consumable. Repriced to the RD 1760."),
    ("Carbon plate and tube stock", 13_000, 13_000, "KEEP. Arm and plate rebuilds."),
    ("Spare compute module", 38_000, 0, "DEFERRED. Accepted risk."),
    ("Spare flight controller", 26_000, 0, "ACCEPTED RISK. Low failure rate, high cost."),
    ("Spare GNSS", 18_000, 0, "ACCEPTED RISK."),
    ("Spare camera + lens", 16_600, 0, "ACCEPTED RISK."),
    ("Remaining consumables", 37_800, 13_000, "KEEP. Fasteners, tape, connectors, filament."),
]

SOFT = [
    ("Training compute", 75_000, 0,
     "R1: institute GPUs confirmed available for model training."),
    ("Indian SAR field dataset", 60_000, 0,
     "DEFERRED. Public aerial-person datasets carry the model until funded; "
     "detection recall stays MODELLED rather than measured."),
    ("Insurance", 25_000, 0,
     "DEFERRED AT TEAM DIRECTION. MUST BE CONFIRMED against the rulebook and "
     "DGCA rules before any flight -- third-party cover is commonly mandatory."),
    ("WPC / ETA licensing", 10_000, 0,
     "REMOVED. All links are delicensed: 2.4/5.8 GHz ISM and 865-867 MHz SRD. "
     "No spectrum licence is needed; ETA is the supplier obligation, so buy "
     "ETA-approved radios from Indian vendors."),
    ("DGCA airspace and operations", 5_000, 5_000, "KEEP. Regulatory."),
]

MULE = [
    ("Training airframe (1)", 0, 0,
     "DEFERRED. Would fly from week 1 and protect the competition aircraft. "
     "Second reinstatement priority."),
]

GROUPS = [("Air vehicle and payload", AIR), ("Ground segment", GROUND),
          ("Test equipment", TEST), ("Spares and consumables", SPARES),
          ("Software, data and regulatory", SOFT), ("Training airframe", MULE)]

DUTY, GST, CONTINGENCY = 0.22, 0.18, 0.15
INDIG = 0.61          # Option B, value-weighted

def main():
    print("=" * 74)
    print("COMPETITION BUILD  -  ask only for what the entry needs")
    print("=" * 74)
    old_t = new_t = 0
    inst = 0
    for name, rows in GROUPS:
        o = sum(r[1] for r in rows)
        n = sum(r[2] for r in rows)
        old_t += o
        new_t += n
        print(f"\n{name}")
        for lbl, a, b, note in rows:
            if a != b:
                mark = "  <-- institutional" if b == 0 and "R1" in note else ""
                if b == 0 and "R1" in note:
                    inst += a
                print(f"   {lbl:<34}{a:>9,} -> {b:>9,}  {b-a:>+9,}{mark}")
        print(f"   {'subtotal':<34}{o:>9,} -> {n:>9,}  {n-o:>+9,}")

    print("\n" + "=" * 74)
    print(f"  {'SUBTOTAL':<34}{old_t:>9,} -> {new_t:>9,}  {new_t-old_t:>+9,}")
    imported = new_t * (1 - INDIG)
    duty = imported * DUTY
    gst = (new_t + duty) * GST
    cont = (new_t + duty + gst) * CONTINGENCY
    total = new_t + duty + gst + cont
    print(f"  {'duty + freight on imported residual':<34}{'':>9} {duty:>12,.0f}")
    print(f"  {'GST @ 18%':<34}{'':>9} {gst:>12,.0f}")
    print(f"  {'contingency @ 15%':<34}{'':>9} {cont:>12,.0f}")
    print(f"  {'COMPETITION ASK':<34}{'':>9} {total:>12,.0f}   ({total/1e5:.2f} L)")
    print(f"  {'previous programme ask':<34}{'':>9} {2_873_880:>12,}   (28.74 L)")
    print(f"  {'reduction':<34}{'':>9} {total-2_873_880:>+12,.0f}"
          f"   ({(total-2_873_880)/2_873_880:+.0%})")
    print("=" * 74)
    print(f"  Institutional contribution (equipment already held): {inst:,}")
    print("=" * 74)
    return total

if __name__ == "__main__":
    main()
