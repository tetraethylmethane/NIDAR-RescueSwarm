#!/usr/bin/env python3
"""The BOM as actually sourced, line by line, with the listing each price came from.

WHY THIS REPLACES THE ESTIMATES. Until now the budget was a cost MODEL: a few
firm retail listings and a majority of quotations and comparable-part
estimates. The mentor brief said so in as many words -- "every other line in
this section is a quotation or an estimate ... and those are where the total is
most likely to move." Every line below is now a real listing from a named
supplier with a URL, so the ask stops being a projection and becomes a basket.

CONVENTION FROM THE SOURCE SHEET. A blank phase cell means "same group as the
row above"; that rule is applied here rather than re-deriving the grouping.
`ac_qty` is the quantity fitted to ONE aircraft, and is zero for a line bought
once for the whole programme. `qty` is always the programme quantity, so
per-aircraft lines already carry their factor of three.

TWO ARITHMETIC NOTES ON THE SOURCE SHEET, both preserved rather than silently
corrected elsewhere:
  1. Its stated total of 592,572.09 is 2,660 short of the sum of its own rows.
     The gap is exactly the three landing-gear lines -- skid, springs and
     filament -- which sit above the first phase-numbered row and fall outside
     the SUM range. Adding the spring row did not move the stated total, which
     is what confirms the range and not the arithmetic is at fault.
  2. Its cost-per-drone column multiplies the 4-in-1 speed controller by four.
     One 4-in-1 ESC drives all four motors, so the correct figure is one.

Run:  python hardware/bom/sourced_bom.py
"""
from __future__ import annotations

# group, item, model, unit INR, programme qty, per-aircraft qty, link
BOM = [
 # ---- measurement instruments, phases 1-2 -------------------------------
 ("instruments", "Load-cell amplifier", "7Semi HX711 24-bit ADC", 104, 1, 0,
  "https://robu.in/product/7semi-hx711-load-cell-amplifier-24bit-adc-for-weigh-scales/"),
 ("instruments", "Load cell", "REES52 20 kg load cell + HX711 breakout", 854, 1, 0,
  "https://www.amazon.in/REES52-20kg-HX711-Electronic-Compatible/dp/B0D3HXLPS"),
 ("instruments", "Thrust-stand mast", "SURYAKUSH metal 2.1 m tripod", 373, 1, 0,
  "https://www.flipkart.com/hi/suryakush-metal-2-1m-tripod-light-stand-max-200cm-photo-studio/p/itm6eeec3987af1c"),
 ("instruments", "Fasteners", "Hex socket-head assortment M3/M4/M5, SS304", 1140, 1, 0,
  "https://onlyscrews.in/products/hexallen-socket-head-assorted-screw-pack-ss304"),
 ("instruments", "Threadlocker", "Loctite 243, 50 ml", 664, 1, 0,
  "https://www.amazon.in/Loctite-243-Threadlocker-Pack-Size/dp/B014MMG3AM"),

 # ---- per aircraft, avionics and sensing, phases 3-6 --------------------
 ("avionics", "Flight controller", "Holybro Pixhawk 6C Mini", 22049, 3, 1,
  "https://robu.in/product/holybro-pixhawk-6c-mini-flight-controller/"),
 ("avionics", "FC vibration mount", "Glass-fibre anti-vibration shock absorber", 161, 3, 1,
  "https://robu.in/product/glass-fiber-flight-controller-anti-vibration-set-shock-absorber-apmkkmwc/"),
 ("avionics", "Companion computer", "Raspberry Pi 5, 8 GB", 19999, 3, 1,
  "https://robu.in/product/raspberry-pi-5-model-8gb/"),
 ("avionics", "AI accelerator", "Raspberry Pi AI HAT+, 26 TOPS", 11749, 3, 1,
  "https://robu.in/product/raspberry-pi-ai-hat-26-tops/"),
 ("avionics", "Compute cooling", "Official Raspberry Pi 5 active cooler", 519, 3, 1,
  "https://robu.in/product/official-raspberry-pi-5-active-cooler/"),
 ("avionics", "Storage", "SanDisk High Endurance 128 GB microSD", 3989, 3, 1,
  "https://www.flipkart.com/sandisk-high-endurance-128-gb-microsd-card-class-10-100-mb-s-memory/p/itmb71522dd1ecd0"),
 ("avionics", "GNSS RTK receiver", "Teravolt AeroNav-Pro RTK, 3 rover + 1 base", 25000, 4, 0,
  "https://teravolt.gitbook.io/teravolt/gps/aeronav-pro-rtk"),
 ("avionics", "Camera + lens", "Arducam 12.3 MP 1/2.3 in HQ module, 6 mm CS lens", 6799, 3, 1,
  "https://robu.in/product/arducam-high-quality-camera-for-raspberry-pi-12-3mp-1-2-3-inch-hq-camera-module-with-6mm-cs-lens-for-pi-4b-3b-2b-3a-pi-zero-and-more/"),
 ("avionics", "Video transmitter", "SunRobotics TS832, 5.8 GHz, 600 mW", 4239, 3, 1,
  "https://www.indiamart.com/proddetail/sunrobotics-fpv-5-8g-600mw-48-channels-wireless-av-tx-rx-ts832-rc832-24438006630.html"),
 ("avionics", "Command receiver", "ExpressLRS RX24T, 2.4 GHz", 1439, 3, 1,
  "https://robu.in/product/expresslrs-rx24t-2-4g-receiver/"),
 ("avionics", "Coordination radio", "EByte E22-900T22D-V2, SX1262, 22 dBm", 989, 3, 1,
  "https://robu.in/product/lora-868mhz-wireless-module-uart/"),
 ("avionics", "Power module", "Holybro PM07", 5249, 3, 1,
  "https://robu.in/product/holybro-pm07-power-module-14s/"),
 ("avionics", "BEC, primary", "8 A UBEC, 5/6 V out, 2-6S in", 3939, 3, 1,
  "https://www.amazon.in/FEICHAO-Output-7V-25-5V-Switch-Helicopters/dp/B07DD9L6P6"),
 ("avionics", "BEC, secondary", "ReadytoSky 2-6S 5V/3A + 12V/3A switchable UBEC", 279, 3, 1,
  "https://robu.in/product/readytosky-2-6s-5v-3a-and-12v-3a-switchable-ubec/"),

 # ---- per aircraft, airframe and drive, phases 7-10 ---------------------
 ("airframe", "Motors", "Tarot TL96020, 5008, 340 KV", 4703, 12, 4,
  "https://robokits.co.in/multirotor-spare-parts/brushless-motor-propeller-esc/brushless-motor/tarot-tl96020-5008-340kv-high-power-brushless-motor"),
 ("airframe", "Propellers", "1855 counter-rotating carbon fibre, CW+CCW pair", 1641, 16, 4,
  "https://robokits.co.in/multirotor-spare-parts/brushless-motor-propeller-esc/propellers/11-to-20-inch/counter-rotating-carbon-fiber-propeller-1855-cw-ccw"),
 ("airframe", "Speed controllers", "Darkmatter VISHNU 50 MK-III, 4-in-1, 50 A", 5189, 3, 1,
  "https://robu.in/product/darkmatter-vishnu-50-mk-iii-4-in-1-50a-8bit-blheli_s-esc-made-in-india/"),
 ("airframe", "Arm tube", "3K carbon fibre, OD25 x ID23 x 1000 mm", 2259, 6, 2,
  "https://robu.in/product/3k-carbon-fiber-tube-hollow-od25-x-id23-x-l1000-mm/"),
 ("airframe", "Motor mounts", "Tarot 25 mm motor mount, TL9602", 1119, 12, 4,
  "https://robu.in/product/tarot-25mm-motor-mount-multicopter-orange-tl9602/"),
 ("airframe", "Arm clamps", "T-bolt hose clamps 23-25 mm, SS304, 4 pcs", 3012.11, 3, 1,
  "https://www.amazon.in/T-Bolt-Clamps-Adjust-23-25mm-Stainless/dp/B0BHW1SCDL"),
 ("airframe", "Landing gear", "F450/F550 landing skid", 549, 3, 1,
  "http://robu.in/product/f450-f550-frame-landing-gear-landing-skid/"),
 # 30 fitted, 2 spare. Bought as a bulk lot, so the programme quantity is not
 # a multiple of three.
 ("airframe", "Suspension springs", "5 mm stainless double torsion spring", 2, 32, 10,
  "https://www.indiamart.com/proddetail/5mm-ss-double-torsion-spring-18969709097.html"),
 ("airframe", "Printed parts", "Pro-Range PETG-CF filament, 1.75 mm, 1 kg", 949, 1, 0,
  "https://robu.in/product/pro-range-petg-cf-filament-1-75mm-1-kg-spool-black/"),
 ("airframe", "Release servos", "MG90S mini servo, 180 deg", 149, 12, 4,
  "https://robocraze.com/products/mg90s-servo-motor"),
 ("airframe", "Cells", "Molicel INR21700-P45B, 6S3P", 509, 54, 18,
  "https://robu.in/product/molicel-inr21700-p45b-4500mah-lithium-ion-battery/"),
 ("airframe", "Cell holders", "3x1 21700 holder, 21.75 mm bore", 12, 54, 18,
  "https://robu.in/product/3-x-21700-battery-holder-with-21-75mm-bore-diameter/"),
 ("airframe", "Pack interconnect", "Pure nickel strip, 0.15 x 27 mm", 6500, 1, 0,
  "https://www.indiamart.com/proddetail/nickel-busbar-nickel-strip-for-21700-3p-sls-2858929058191.html"),
 ("airframe", "Group interconnect", "Tinned copper braided jumper", 500, 1, 0,
  "https://www.indiamart.com/proddetail/tinned-copper-braided-jumper-2854036769933.html"),
 ("airframe", "Balance leads", "JST-XH 6S, 200 mm, 22 AWG", 123.9, 3, 1,
  "http://zbotic.in/product/jst-xh-6s-20cm-22awg-balance-charge-wire/"),
 ("airframe", "Pack fusing", "ANL fuse holder + 150 A ANL fuses", 3000.08, 3, 1,
  "https://njour.com/categories/tools-and-home-improvement/PC61p6RfDup2b7A"),
 ("airframe", "Pack retention", "300 mm LiPo strap, reusable", 62, 6, 2,
  "https://robu.in/product/30cm-lipo-battery-strap-belt-reusable-cable-tie-wrap/"),
 ("airframe", "Main leads", "10 AWG ultra-flexible silicone wire", 149, 1, 0,
  "https://robu.in/product/high-quality-ultra-flexible-10awg-silicone-wire-200m-red/"),
 ("airframe", "Power connectors", "Amass XT90S anti-spark, M/F pair", 180, 12, 4,
  "https://robokits.co.in/batteries-chargers/plugs-and-connectors/amass-xt90s-anti-spark-connectors-male-female-pair-original"),
 ("airframe", "Signal connectors", "JST ZH 6-pin, 200 mm leads", 23, 3, 1,
  "https://robu.in/product/jst-sh-6-pin-connectors-1-0mm-pin-spacing-with-200mm-wires/"),
 ("airframe", "Antenna feeders", "SMA M-F bulkhead RG316, 150 mm + adapters", 1139, 3, 1,
  "https://www.desertcart.in/products/441705703-sma-cable-sma-male-to-sma-female-bulkhead-rg316-6"),
 ("airframe", "Insulation", "PVC heat-shrink sleeve, 150 mm", 47, 3, 1,
  "https://robu.in/product/pvc-heat-shrink-sleeve-150mm-black/"),

 # ---- flight-test support, phases 11-12 ---------------------------------
 ("flighttest", "Safety-pilot transmitter",
  "RadioMaster TX12 MKII ELRS + RP1 receiver", 16518.82, 1, 0,
  "https://zbotic.in/product/radiomaster-tx12-mkii-expresslrs-edgetx-transmitter-with-rp1-expresslrs-2-4ghz-nano-receiver/"),
 ("flighttest", "Battery charger", "ToolKitRC M6D, 500 W, 25 A, dual", 7349, 1, 0,
  "https://robu.in/product/toolkitrc-m6d-500w-25a-1-6s-dc-dual-smart-charger/"),
 ("flighttest", "Pack health monitor", "Holybro PM08-CAN, 14S, 200 A", 9058, 1, 0,
  "https://robu.in/product/holybro-pm08-power-module-14s-200a/"),
 ("flighttest", "Cable management", "Nylon zip ties, 350 mm, 100 pcs", 135, 1, 0,
  "https://robu.in/product/nylon-cable-zip-ties-350-mm-white/"),
 ("flighttest", "Heat-shrink kit", "328 pcs assorted 2:1 heat-shrink", 159, 1, 0,
  "https://robu.in/product/328pcs-heat-shrink-tube-heat-shrink-tube-kit/"),
 ("flighttest", "Mounting tape", "3M VHB 5952, 6 mm x 8.2 m", 560, 1, 0,
  "https://www.amazon.in/sc-tch-5952-Tape-size/dp/B0F43FP3CJ"),
 ("flighttest", "Hook and loop", "Self-adhesive hook and loop, 25 mm x 2 m", 145, 1, 0,
  "https://www.amazon.in/INSTITCH-Self-Adhesive-Gripping-Perfect-Crafting/dp/B0DVLVCDH6"),
 ("flighttest", "Consumables", "Fasteners, tape, connectors, filament", 5000, 1, 0, ""),

 # ---- ground segment and statutory, phases 29-32 ------------------------
 ("ground", "Video receivers", "RC832S 5.8 GHz AV receiver", 4399, 3, 0,
  "https://robu.in/product/rc832-plus-5-8g-av-receiver/"),
 ("ground", "Receive antennas", "Triple-feed 5.8 GHz patch, SMA", 839, 3, 0,
  "https://robu.in/product/triple-feed-patch-5-8ghz-antenna-sma/"),
 ("ground", "Video capture", "USB 2.0 analog AV capture adapter", 399, 3, 0,
  "https://robu.in/product/usb2-0-audio-video-capture-card-adapter-vhs-to-dvd-video-capture-converter/"),
 ("ground", "Coordination base", "EByte E22-900T22U, SX1262, USB", 1646, 1, 0,
  "https://hubtronics.in/e22-900t22u"),
 ("ground", "Base station mount", "Photographic tripod and adapter", 879, 1, 0,
  "https://www.amazon.in/Amazon-Basics-Tripod-Camera-Operating/dp/B0CX5DSRCQ"),
]

# ---------------------------------------------------------------------------
# WHICH PHASE BUYS WHAT
#
# The sheet's phase column encodes a ten-phase per-aircraft cycle offset by ten
# -- "3, 13, 21" is the same step for aircraft 1, 2 and 3 -- plus instruments
# at the front and the ground segment at the back. That is the structure the
# schedule already had, so it is kept and only the amounts are re-derived.
#
# ALLOCATION RULE. A per-aircraft line gives each of its phases ac_qty, and any
# remainder (spares) falls to the last phase. A shared line splits evenly. The
# one exception is the motors, where the whole point of the schedule is that
# ONE is measured before the other eleven are committed.
PHASE_OF = {
    "Load-cell amplifier": (1,), "Load cell": (1,), "Thrust-stand mast": (1,),
    "Fasteners": (1,), "Threadlocker": (1,),
    "Motors": (2, 10, 20, 28), "Propellers": (10, 20, 28),
    "Flight controller": (3, 13, 21), "FC vibration mount": (3, 13, 21),
    "Companion computer": (4, 14, 22), "AI accelerator": (4, 14, 22),
    "Compute cooling": (4, 14, 22), "Storage": (4, 14, 22),
    "GNSS RTK receiver": (5, 15, 23, 29),
    "Camera + lens": (6, 16, 24), "Video transmitter": (6, 16, 24),
    "Command receiver": (6, 16, 24), "Coordination radio": (6, 16, 24),
    "Arm tube": (7, 17, 25), "Motor mounts": (7, 17, 25),
    "Arm clamps": (7, 17, 25), "Landing gear": (7, 17, 25),
    "Suspension springs": (7, 17, 25), "Printed parts": (7,),
    "Cells": (8, 18, 26), "Cell holders": (8, 18, 26),
    "Balance leads": (8, 18, 26), "Pack fusing": (8, 18, 26),
    "Pack retention": (8, 18, 26), "Pack interconnect": (8,),
    "Group interconnect": (8,), "Power module": (8, 18, 26),
    "BEC, primary": (8, 18, 26), "BEC, secondary": (8, 18, 26),
    "Speed controllers": (9, 19, 27), "Release servos": (9, 19, 27),
    "Power connectors": (9, 19, 27), "Signal connectors": (9, 19, 27),
    "Antenna feeders": (9, 19, 27), "Insulation": (9, 19, 27),
    "Main leads": (9,),
    "Safety-pilot transmitter": (11,), "Battery charger": (11,),
    "Pack health monitor": (11,),
    "Cable management": (12,), "Heat-shrink kit": (12,),
    "Mounting tape": (12,), "Hook and loop": (12,), "Consumables": (12,),
    "Video receivers": (30,), "Receive antennas": (30,), "Video capture": (30,),
    "Coordination base": (30,), "Base station mount": (30,),
}

# One measured, then three to finish aircraft 1, then four per aircraft.
PHASE_QTY_OVERRIDE = {"Motors": {2: 1, 10: 3, 20: 4, 28: 4}}

# ---------------------------------------------------------------------------
# TAX TREATMENT
#
# The earlier cost model added 22 % customs duty and 18 % GST to everything.
# That was right when most lines were quotations for parts not yet sourced. It
# is wrong now: these are Indian retail listings, and a listed retail price in
# India is GST-inclusive. Adding 18 % on top of an MRP overstates the ask by
# roughly a lakh, and the duty line is obsolete outright because the importer
# has already paid it before the part reaches a domestic shelf.
#
# What remains taxable is the genuinely ex-tax share: supplier quotations and
# B2B listings, which quote before GST.
EX_GST_SUPPLIERS = ("teravolt", "indiamart", "njour")
GST = 0.18
CONTINGENCY = 0.15


def is_ex_gst(url):
    return any(f in url for f in EX_GST_SUPPLIERS) or url == ""


def phase_alloc():
    """{phase: INR of parts}, from PHASE_OF and the allocation rule."""
    out = {}
    for r in BOM:
        _, item, _model, unit, qty, ac, _url = r
        ph = PHASE_OF[item]
        ov = PHASE_QTY_OVERRIDE.get(item)
        if ov:
            alloc = ov
        else:
            each = ac if ac else qty // len(ph)
            alloc = {p: each for p in ph}
            alloc[ph[-1]] += qty - each * len(ph)
        assert sum(alloc.values()) == qty, f"{item}: {alloc} != {qty}"
        for p, q in alloc.items():
            out[p] = out.get(p, 0.0) + unit * q
    return out


def released(parts_incl, parts_ex):
    """The stated rule, corrected: retail is already GST-paid, quotations are
    not, and contingency applies to both."""
    return (parts_incl + parts_ex * (1 + GST)) * (1 + CONTINGENCY)


def phase_released():
    """{phase: INR released}, applying the rule phase by phase."""
    incl, ex = {}, {}
    for r in BOM:
        _, item, _m, unit, qty, ac, url = r
        ph = PHASE_OF[item]
        ov = PHASE_QTY_OVERRIDE.get(item)
        if ov:
            alloc = ov
        else:
            each = ac if ac else qty // len(ph)
            alloc = {p: each for p in ph}
            alloc[ph[-1]] += qty - each * len(ph)
        tgt = ex if is_ex_gst(url) else incl
        for p, q in alloc.items():
            tgt[p] = tgt.get(p, 0.0) + unit * q
    phases = sorted(set(incl) | set(ex))
    return {p: released(incl.get(p, 0.0), ex.get(p, 0.0)) for p in phases}


GROUPS = [("instruments", "Measurement instruments", "1--2"),
          ("avionics",    "Per aircraft, avionics and sensing", "3--6"),
          ("airframe",    "Per aircraft, airframe and drive", "7--10"),
          ("flighttest",  "Flight-test support", "11--12"),
          ("ground",      "Ground segment and statutory", "29--32")]

GST = 0.18

# What the source sheet stated for itself, kept so the discrepancy stays visible.
SHEET_STATED_TOTAL = 592572.09
SHEET_OMITTED = 549 * 3 + 2 * 32 + 949  # landing gear, springs, filament
ADDED_AFTER_SHEET = 0                  # nothing added; the scale is institutional

PACK_PROTECTION = """Why there is no BMS in this BOM.

The mentor brief funded "6S 60 A BMS, distribution board, regulator" as one
8,500 line. Two thirds of that is already bought under other names: the
distribution board is the Holybro PM07 and the regulators are the two UBECs.
What remained was cell protection, and a series BMS is the wrong device for it
at this current.

The pack draws 42 A in hover and 115 A at the T/W = 2 peak. A 60 A board
trips in normal flight and the 100 A board stocked in India trips at full
thrust -- a nuisance cut-out at maximum thrust is a crash, not a protection.
A board that did clear 115 A would put its FETs in series with the main path,
adding resistance and heat exactly where sim_pack_sag already shows the pack
reaching its 18.0 V failsafe floor at 64 % state of charge.

The protection is therefore distributed across parts already in the BOM:
  short circuit      150 A ANL fuse per pack
  over-discharge     flight controller low-voltage failsafe, 18.0 V pack
  balance            JST-XH 6S leads, balanced on the charger
  current, voltage   PM07 telemetry to the autopilot
  per-cell floor     the cell monitor added above -- the one real gap, since
                     the failsafe watches PACK volts and a single sagging cell
                     is invisible to it
"""


def line_total(r):
    return r[3] * r[4]


def group_total(key):
    return sum(line_total(r) for r in BOM if r[0] == key)


def per_aircraft(key):
    return sum(r[3] * r[5] for r in BOM if r[0] == key)


def total():
    return sum(line_total(r) for r in BOM)


# The sheet's own total, plus what its SUM range missed, plus what was added
# after it, must be what we hold. This is the transcription guard: it fails if
# any line is mistyped, dropped or double-counted.
assert abs(total() - (SHEET_STATED_TOTAL + SHEET_OMITTED + ADDED_AFTER_SHEET)) < 1.0, (
    f"transcription drift: {total():.2f} vs sheet {SHEET_STATED_TOTAL:.2f} "
    f"+ omitted {SHEET_OMITTED} + added {ADDED_AFTER_SHEET}")

if __name__ == "__main__":
    print(f"\n  {'group':<40}{'lines':>6}{'per ac':>11}{'programme':>12}")
    print("  " + "-" * 69)
    for key, label, phases in GROUPS:
        n = sum(1 for r in BOM if r[0] == key)
        tag = f"{label}  (ph {phases.replace('--', '-')})"
        print(f"  {tag:<40}{n:>6}{per_aircraft(key):>11,.0f}{group_total(key):>12,.0f}")
    print("  " + "-" * 69)
    print(f"  {'TOTAL PARTS':<40}{len(BOM):>6}{'':>11}{total():>12,.0f}")
    print(f"  {'with 18 % GST':<40}{'':>6}{'':>11}{total() * (1 + GST):>12,.0f}")
    print(f"\n  source sheet stated {SHEET_STATED_TOTAL:,.2f}; its SUM range omits "
          f"the landing gear ({SHEET_OMITTED:,.0f})\n")
