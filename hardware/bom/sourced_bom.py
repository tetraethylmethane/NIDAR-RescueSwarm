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
  3. It does the same to the arm clamps: cost/drone 12,048.44 is four packs,
     but the programme quantity is 3, i.e. one pack per aircraft. The quantity
     column is the consistent one and is what ac_qty follows.
  4. Its own Qty column sums to 311, not the 276 it states, and its
     weight-per-drone (4,516 g) and cost-per-drone (182,547.44) footers do not
     reproduce from its own columns (4,746 g and 178,458.44) -- the two ESC and
     arm-clamp errors above account for most of that gap. None of these footers
     is used here; the line rows are.

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
 # A motor on a stand needs something to command it. The safety-pilot
 # transmitter is not bought until phase 11, long after the thrust test.
 ("instruments", "Throttle source", "Servo tester / ESC consistency tester, PPM", 111, 1, 0,
  "https://robokits.co.in/motors/rc-servo-motor/servo-tester-esc-consistency-tester-ppm-generator"),

 # ---- per aircraft, avionics and sensing, phases 3-6 --------------------
 # REVISED 2026-09-19 (the team's BOM improvement list): Pixhawk 6C Mini
 # 22,049 -> Kakute H7 V1.5. Same ArduPilot, H743 MCU, 30.5 mm stack that the
 # 4-in-1 ESC below bolts under. Two consequences carried elsewhere in this
 # file: it has NO magnetometer (the GenX rover carries the compass), and its
 # 8 outputs are exactly 4 motors + 4 release servos, with none spare. UARTs are
 # tight too, so the E22 coordination radio hangs off the Pi, not the FC.
 ("avionics", "Flight controller", "Holybro Kakute H7 V1.5, no Bluetooth", 9269, 3, 1,
  "https://indianrobostore.com/product/holybro-kakute-h7-v15-flight-controller-without-bluetooth"),
 ("avionics", "FC vibration mount", "Glass-fibre anti-vibration shock absorber", 161, 3, 1,
  "https://robu.in/product/glass-fiber-flight-controller-anti-vibration-set-shock-absorber-apmkkmwc/"),
 # The autopilot ships without one and logs nothing without it. Separate from
 # the companion computer's card, which is a different slot on a different board.
 ("avionics", "Autopilot log card", "SanDisk 32 GB microSDHC, class 10", 1549, 3, 1,
  "https://robocraze.com/products/sandisk-32gb-micro-sd-sdhc-card"),
 # 4 GB, not 8: inference runs on the Hailo, not in the Pi's RAM.
 ("avionics", "Companion computer", "Raspberry Pi 5, 4 GB", 11049.15, 3, 1,
  "https://www.yantronix.in/products/raspberry-pi-5-model-b---4gb-ram/1414116000000634900"),
 ("avionics", "AI accelerator", "Raspberry Pi AI HAT+, 26 TOPS", 11749, 3, 1,
  "https://robu.in/product/raspberry-pi-ai-hat-26-tops/"),
 ("avionics", "Compute cooling", "Official Raspberry Pi 5 active cooler", 519, 3, 1,
  "https://robu.in/product/official-raspberry-pi-5-active-cooler/"),
 ("avionics", "Storage", "SanDisk High Endurance 128 GB microSD", 3989, 3, 1,
  "https://www.flipkart.com/sandisk-high-endurance-128-gb-microsd-card-class-10-100-mb-s-memory/p/itmb71522dd1ecd0"),
 # REVISED 2026-09-19: DIY ZED-F9P RTK on ALL THREE aircraft plus a local base,
 # replacing Teravolt RTK on aircraft 1 and SBAS M9N on 2 and 3.
 # Rovers: GenX F9P Air, which has the ZED-F9P, a dual-band helix AND a compass
 # in one ~20 g unit. The compass matters because the Kakute H7 has none and the
 # M9N that used to carry one is gone. It wires straight to the FC's GPS UART
 # plus I2C. CONFIRM L1/L2 in the cart: the listing does not state its bands.
 ("avionics", "GNSS RTK rover", "GenX F9P Air: ZED-F9P + helix + compass, ~20 g",
  15392, 3, 1,
  "https://robokits.co.in/multirotor-spare-parts/genx-uav-product/genx-uav-zed-f9p-air-lightweight-rtk-gnss-module-with-integrated-helical-antenna-and-compass-made-in-india"),
 # The base: a bare F9P board, a survey antenna and its own E22, so it sends
 # RTCM with no laptop, internet or NTRIP in the loop. Price from Robocraze
 # (same SmartElex part), because Robu refuses automated fetches.
 ("avionics", "GNSS RTK base", "SmartElex ZED-F9P-04B RTK board, U.FL", 17965, 1, 0,
  "https://robocraze.com/products/smartelex-gps-rtk-board-ufl-zed-f9p-04b"),
 ("avionics", "GNSS antenna, base", "LS-125-A L1/L2/L5 survey antenna", 8123, 1, 0,
  "https://robokits.co.in/multirotor-spare-parts/gps-sensors/rtk-gps-base-station-survey-grade-cors-high-precision-industrial-l1-l2-l5-antenna"),
 # The board is U.FL. Check the survey antenna's connector (usually TNC) on
 # arrival; this pigtail covers U.FL to SMA only.
 ("avionics", "GNSS feeder, base", "U.FL to SMA female pigtail, 10 cm", 49, 1, 0,
  "https://robocraze.com/products/mini-pci-u-fl-to-sma-female-pigtail-cable-10cm-ipx-to-sma-extension"),
 # The E22 is kept PRIMARILY for RTK: four-constellation RTCM is ~16-32 kbps
 # against a 62.5 kbps air-rate ceiling. Trim the base to MSM4 at 1 Hz, and do
 # not load swarm traffic onto this link as well.
 ("avionics", "RTK base radio", "EByte E22-900T22D-V2, SX1262, 22 dBm", 989, 1, 0,
  "https://robu.in/product/lora-868mhz-wireless-module-uart/"),
 # True height above whatever is below -- water, ground or a rooftop. The
 # release gate is specified at 6 m AGL and the barometer measures height above
 # the launch point, which over floodwater of unknown level is a different
 # quantity. 12 m indoors, about 7 m outdoors, so it acquires during the
 # descent and gates the release; it does not see forward.
 ("avionics", "Height rangefinder", "Benewake TFmini-S, 12 m lidar, UART", 2827, 3, 1,
  "https://indianrobostore.com/product/benewake-12m-tfmini-s-micro-lidar-distance-sensor-for-drones-uav-uas-robots-uart"),
 ("avionics", "Camera + lens", "Arducam 12.3 MP 1/2.3 in HQ module, 6 mm CS lens", 6799, 3, 1,
  "https://robu.in/product/arducam-high-quality-camera-for-raspberry-pi-12-3mp-1-2-3-inch-hq-camera-module-with-6mm-cs-lens-for-pi-4b-3b-2b-3a-pi-zero-and-more/"),
 # REVISED 2026-09-19: analog TS832 out, digital video generated by the Pi
 # (wfb-ng on stock Pi OS, so CV and video run together; OpenHD is its own OS
 # image and would displace the CV stack). The downlink now carries the CV output
 # with its bounding boxes, not the raw camera. Bare module: 5 V at up to
 # 1.8 A, USB 2.0, two IPEX antenna ports, and it needs a heatsink.
 ("avionics", "Video transmitter", "LB-Link BL-M8812EU2, RTL8812EU, 5 GHz 2T2R", 1849, 3, 1,
  "https://hubtronics.in/BL-M8812EU2"),
 ("avionics", "Video antennas", "6 dBi 5 GHz dipole + 165 mm U.FL lead", 75, 6, 2,
  "https://robocraze.com/products/6dbi-2-4ghz-5ghz-dual-band-wifi-rp-sma-antenna-20cm-u-fl-ipex-cable"),
 ("avionics", "Command receiver", "ExpressLRS RX24T, 2.4 GHz", 1439, 3, 1,
  "https://robu.in/product/expresslrs-rx24t-2-4g-receiver/"),
 ("avionics", "Coordination radio", "EByte E22-900T22D-V2, SX1262, 22 dBm", 989, 3, 1,
  "https://robu.in/product/lora-868mhz-wireless-module-uart/"),
 # PM07 dropped 2026-09-19 (was 5,249 x3): on a Kakute + 4-in-1 stack the ESC's
 # current sensor and battery voltage reach the FC over the stack cable, so the
 # PM07 duplicated them. BATT_MONITOR reads the ESC's sensor.
 # The Pi 5 + AI HAT+ + camera draw ~3-4 A, so the 8 A unit stays for them alone.
 ("avionics", "BEC, primary", "8 A UBEC, 5/6 V out, 2-6S in", 3939, 3, 1,
  "https://www.amazon.in/FEICHAO-Output-7V-25-5V-Switch-Helicopters/dp/B07DD9L6P6"),
 # The BL-M8812EU2 draws up to 1.8 A at 5 V, so it gets its own regulator
 # instead of sharing the Pi's rail or loading the Pi's USB port.
 ("avionics", "BEC, video radio", "Hobbywing 3 A UBEC, 5/6 V, 5 A peak, 2-6S", 369, 3, 1,
  "https://kitsguru.com/products/hobbywing-3a-ubec-5v-6v-max-5a-lowest-rf-noise-be-hwbec?variant=40708943577269"),
 # The servo rail, kept apart so a jammed servo cannot sag the autopilot.
 ("avionics", "BEC, secondary", "ReadytoSky 2-6S 5V/3A + 12V/3A switchable UBEC", 279, 3, 1,
  "https://robu.in/product/readytosky-2-6s-5v-3a-and-12v-3a-switchable-ubec/"),

 # ---- per aircraft, airframe and drive, phases 7-10 ---------------------
 ("airframe", "Motors", "Tarot TL96020, 5008, 340 KV", 4703, 12, 4,
  "https://robokits.co.in/multirotor-spare-parts/brushless-motor-propeller-esc/brushless-motor/tarot-tl96020-5008-340kv-high-power-brushless-motor"),
 ("airframe", "Propellers", "1855 counter-rotating carbon fibre, CW+CCW pair", 1641, 16, 4,
  "https://robokits.co.in/multirotor-spare-parts/brushless-motor-propeller-esc/propellers/11-to-20-inch/counter-rotating-carbon-fiber-propeller-1855-cw-ccw"),
 # REVISED 2026-09-19: Vishnu 50 A (5,189) -> 65 A, for current margin on
 # 5008 340 KV / 6S / 18 in. The peak is ~29 A per motor (115 A pack), so do
 # not go to 80-100 A unless the phase-2 stand says so. A CANDIDATE, not a
 # freeze: 50 A vs 65 A is decided on the phase-2 stand, testing 18 in + 340 KV
 # for desync, current and temperature. It is an FPV ESC, so desync is the
 # real risk. 30.5 mm,
 # stacks under the Kakute. The team's link is ElectroPi, which hides its
 # price from automated fetches; this price is RC Mumbai's for the same part.
 ("airframe", "Speed controllers", "Hobbywing XRotor FPV G2, 4-in-1, 65 A, 3-6S", 6500, 3, 1,
  "https://rcmumbai.com/hobbywing-xrotor-fpv-g2-65a-4in1-esc.html"),
 ("airframe", "Arm tube", "3K carbon fibre, OD25 x ID23 x 1000 mm", 2259, 6, 2,
  "https://robu.in/product/3k-carbon-fiber-tube-hollow-od25-x-id23-x-l1000-mm/"),
 # The arms are tubes; this is what they bolt to. One sheet yields the top and
 # bottom plate of a centre section at this wheelbase.
 ("airframe", "Frame plate stock", "3K carbon fibre sheet, 300 x 200 x 2 mm", 2895, 3, 1,
  "https://indianrobostore.com/product/3k-carbon-fiber-sheet-300mm200mm2mm"),
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
 # REVISED 2026-09-19: the DIY 6S3P Li-ion pack (54 P45B cells, holders, nickel,
 # braid and balance leads) is replaced by a bought 6S LiPo, one per aircraft.
 # CAPACITY IS NOT FROZEN. This is the 12,000 mAh pack already vetted for the
 # MVP: 266 Wh against the 244 Wh the sizing model requires of any chemistry,
 # 25 C (300 A) against the 115 A peak, and ~1424 g, about what the Li-ion pack
 # weighed, so the T/W 2.0 design point holds. The team's alternative, GenX
 # 22,000 mAh 25C at 13,815 (AS150), is ~2x the energy and very roughly
 # +1.2-1.4 kg, which the design point does not carry. Size it from the final
 # AUW and hover current before ordering. Confirm 10,000 vs 12,000 mAh in the
 # cart: the Robokits listing conflates them.
 ("airframe", "Battery pack", "GenX 22.2V 6S 12000mAh 25C/50C LiPo, XT90", 9088, 3, 1,
  "https://robokits.co.in/batteries-chargers/drone-batteries/"
  "genx-power-premium-lipo-battery/genxpower-22.2v-lipo-batteries/"
  "genx-22.2v-6s-10000mah-25c-50c-premium-lipo-battery-with-xt-90-connector"),
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
 # REVISED 2026-09-19: the analog RC832S receivers, patches and capture cards
 # are gone. The ground end is one computer plus digital receivers. The team's
 # list wants to avoid one receiver per drone, but OpenHD/wfb-ng puts each
 # aircraft on its own channel and each adapter listens on one channel, so
 # three are bought. Same module as the air side: 1.8 A each, so it needs a
 # powered USB hub, not laptop ports. The directional ground antenna is still
 # open; these omnis are the placeholder until it is chosen.
 ("ground", "Video receivers", "LB-Link BL-M8812EU2, RTL8812EU, one per aircraft channel", 1849, 3, 0,
  "https://hubtronics.in/BL-M8812EU2"),
 ("ground", "Receive antennas", "6 dBi 5 GHz dipole + U.FL lead, 2 per receiver", 75, 6, 0,
  "https://robocraze.com/products/6dbi-2-4ghz-5ghz-dual-band-wifi-rp-sma-antenna-20cm-u-fl-ipex-cable"),
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
    "Fasteners": (1,), "Threadlocker": (1,), "Throttle source": (1,),
    "Motors": (2, 10, 20, 28), "Propellers": (2, 10, 20, 28),
    "Flight controller": (3, 13, 21), "FC vibration mount": (3, 13, 21),
    "Autopilot log card": (3, 13, 21),
    "Companion computer": (4, 14, 22), "AI accelerator": (4, 14, 22),
    "Compute cooling": (4, 14, 22), "Storage": (4, 14, 22),
    # Both RTK units in one step. A rover without its base is not an RTK
    # receiver, it is an ordinary one, so splitting them across phases 5 and
    # 29 would have left aircraft 1 flying uncorrected for the whole build
    # and no ground truth surveyable until the programme was nearly over.
    "GNSS RTK rover": (5, 15, 23), "GNSS RTK base": (5,),
    "GNSS antenna, base": (5,), "GNSS feeder, base": (5,), "RTK base radio": (5,),
    "Camera + lens": (6, 16, 24), "Height rangefinder": (6, 16, 24), "Video transmitter": (6, 16, 24),
    "Video antennas": (6, 16, 24),
    "Command receiver": (6, 16, 24), "Coordination radio": (6, 16, 24),
    "Arm tube": (7, 17, 25), "Frame plate stock": (7, 17, 25), "Motor mounts": (7, 17, 25),
    "Arm clamps": (7, 17, 25), "Landing gear": (7, 17, 25),
    "Suspension springs": (7, 17, 25), "Printed parts": (7,),
    "Battery pack": (8, 18, 26), "Pack fusing": (8, 18, 26),
    "Pack retention": (8, 18, 26),
    "BEC, primary": (8, 18, 26), "BEC, video radio": (8, 18, 26),
    "BEC, secondary": (8, 18, 26),
    "Speed controllers": (2, 19, 27), "Release servos": (9, 19, 27),
    "Power connectors": (9, 19, 27), "Signal connectors": (9, 19, 27),
    "Antenna feeders": (9, 19, 27), "Insulation": (9, 19, 27),
    "Main leads": (9,),
    "Safety-pilot transmitter": (11,), "Battery charger": (11,),
    "Cable management": (12,), "Heat-shrink kit": (12,),
    "Mounting tape": (12,), "Hook and loop": (12,), "Consumables": (12,),
    "Video receivers": (29,), "Receive antennas": (29,),
    "Coordination base": (29,), "Base station mount": (29,),
}

# One measured, then three to finish aircraft 1, then four per aircraft.
# Phase 2 measures one motor. A motor alone measures nothing: it needs a
# propeller to load it and a speed controller to drive it, so phase 2 buys the
# whole test set. The controller it uses is aircraft 1's, brought forward from
# phase 9 rather than bought twice -- the point of measuring with the hardware
# that will fly is lost if the bench runs a different controller.
PHASE_QTY_OVERRIDE = {
    "Motors":            {2: 1, 10: 3, 20: 4, 28: 4},
    "Propellers":        {2: 1, 10: 5, 20: 5, 28: 5},
    "Speed controllers": {2: 1, 19: 1, 27: 1},
}

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


def _alloc(r):
    """{phase: quantity} for one BOM row, by the allocation rule above."""
    _, item, _model, _unit, qty, ac, _url = r
    ph = PHASE_OF[item]
    ov = PHASE_QTY_OVERRIDE.get(item)
    if ov:
        alloc = dict(ov)
    else:
        each = ac if ac else qty // len(ph)
        alloc = {p: each for p in ph}
        alloc[ph[-1]] += qty - each * len(ph)
    assert sum(alloc.values()) == qty, f"{item}: {alloc} != {qty}"
    return alloc


def phase_lines():
    """{phase: [(item, model, qty, unit, line_total)]} -- what each phase buys."""
    out = {}
    for r in BOM:
        _, item, model, unit, _qty, _ac, _url = r
        for p, q in _alloc(r).items():
            if q:
                out.setdefault(p, []).append((item, model, q, unit, unit * q))
    return {p: sorted(v, key=lambda x: -x[4]) for p, v in sorted(out.items())}


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
SHEET_STATED_TOTAL = 556450.09
SHEET_OMITTED = 549 * 3 + 2 * 32 + 949  # landing gear, springs, filament

# CORRECTED 2026-09-18 against the source sheet itself.
#
# SHEET_STATED_TOTAL read 592,572.09 against a sheet that states 556,450.09 --
# an anchor 36,122 too high. ADDED_AFTER_SHEET carried a compensating
# -50,000 + 7,200*2 - (7,200-6,939)*2 for "two RTK units out, two M9N in,
# M9N repriced", and those adjustments had ALREADY been applied to the sheet:
# it now shows RTK qty 2 and M9N qty 2 at 6,939 directly. So the repository was
# re-applying a change the sheet already contained and absorbing the error in a
# wrong anchor. Both sides were wrong by the same 36,122, the assertion below
# subtracted one from the other, and it passed.
#
# Nothing in the parts list moved: every one of the 55 sheet rows agrees with
# this file line for line, and total() was and remains 581,034.09. What was
# wrong was only the audit trail -- which is the one thing this block exists to
# be, so it is worth having right.
#
# The reconciliation is now the straightforward one:
#     556,450.09  the sheet's own stated total
#     +   2,660    its SUM range starts below the three landing-gear rows
#     +  21,924    four parts added after the sheet was frozen
#     = 581,034.09
ADDED_AFTER_SHEET = (1549 * 3          # autopilot log cards, not shipped with it
                     + 2895 * 3        # frame plate stock, the arms bolt to it
                     + 111             # bench throttle source
                     + 2827 * 3)       # height rangefinders for the release gate

# The 2026-09-19 revision from the team's BOM improvement list, as signed
# deltas against the lines it replaced. Stated line by line so the guard
# below still catches a mistyped row rather than absorbing it.
REVISED_2026_09_19 = (
    (9269 - 22049) * 3                 # Pixhawk 6C Mini -> Kakute H7 V1.5
    + (11049.15 - 19999) * 3           # Pi 5 8 GB -> 4 GB
    - 25000 * 2 - 6939 * 2             # Teravolt RTK x2 and M9N x2 out
    + 15392 * 3                        # GenX F9P Air rovers, compass included
    + 17965 + 8123 + 49 + 989          # base: F9P, survey antenna, feeder, E22
    + (1849 - 4239) * 3 + 75 * 6       # TS832 -> BL-M8812EU2, air antennas
    - 5249 * 3                         # PM07 out: the ESC stack reports current
    + 369 * 3                          # own 3 A BEC for the video radio
    + (6500 - 5189) * 3                # Vishnu 50 A -> XRotor G2 65 A
    - 509 * 54 - 12 * 54 - 6500 - 500 - 123.9 * 3   # DIY 21700 pack out
    + 9088 * 3                         # bought 6S LiPo, one per aircraft
    - 9058                             # PM08-CAN out
    + (1849 - 4399) * 3                # RC832S -> BL-M8812EU2 ground receivers
    + 75 * 6 - 839 * 3                 # patches -> omnis, 2 per receiver
    - 399 * 3)                         # analog capture cards out

PACK_PROTECTION = """Why there is no BMS in this BOM.

(Written for the DIY 6S3P Li-ion pack. Since 2026-09-19 the pack is a bought
LiPo with its own balance lead, and the PM07 is gone: pack current and voltage
now come from the 4-in-1 ESC's sensor over the stack cable. The reasoning
against a series BMS at 115 A is unchanged.)

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
assert abs(total() - (SHEET_STATED_TOTAL + SHEET_OMITTED + ADDED_AFTER_SHEET
                      + REVISED_2026_09_19)) < 1.0, (
    f"transcription drift: {total():.2f} vs sheet {SHEET_STATED_TOTAL:.2f} "
    f"+ omitted {SHEET_OMITTED} + added {ADDED_AFTER_SHEET} "
    f"+ revised {REVISED_2026_09_19:.2f}")

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
