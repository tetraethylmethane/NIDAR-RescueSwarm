#!/usr/bin/env python3
r"""Radio links, as adopted, and the margin arithmetic over them.

WHY THIS IS ITS OWN MODULE. The link parameters were about to exist in three
places at once -- the MATLAB export, the generated proposal section, and the
prose in Section IV-H -- which is exactly the defect this repository keeps
finding in itself. They live here, and everything else imports them.

WHAT CHANGED, AND WHY THE WITHDRAWN ROW IS STILL HERE. The original design put
video, telemetry and swarm coordination on a single 5.8 GHz 802.11 mesh. At the
600 m geofence that link has 8.7 dB of margin: the thinnest path in the system
and simultaneously the one carrying the most data. Meshing does not repair it,
because a relay hop is the same weak link with the same margin. The 802.11 row
is retained in the table because the withdrawal is an argument, and the
argument is the margin column.

CONVENTIONS. tx_dbm is at the transmitter output, before feedline. Gains are
per end, from the antenna actually specified in the BOM. sens_dbm is the
receiver sensitivity for the modulation actually used -- not the best figure on
the datasheet. Margin is therefore what remains after free-space loss only:
rain, body blocking, a banked airframe and antenna misalignment all draw on it,
and none of them is in this number.
"""
from __future__ import annotations

import math

# Design slant range. The geofence is a horizontal radius; at 40 m AGL the
# slant range differs from it by 0.13 %, which is below every other uncertainty
# here, so the two are used interchangeably.
GEOFENCE_M = 600.0

LINKS = [
    dict(name="Analog video, 5.8 GHz", f_mhz=5800, tx_dbm=27.8,
         g_tx_dbi=2, g_rx_dbi=12, sens_dbm=-90, adopted=True,
         hw="800 mW VTX, 5.8 GHz dipole to a 12 dBi patch at the GCS",
         role="Video downlink, one channel per aircraft"),
    dict(name="ExpressLRS, 2.4 GHz", f_mhz=2400, tx_dbm=20,
         g_tx_dbi=2, g_rx_dbi=2, sens_dbm=-108, adopted=True,
         hw="ELRS 2.4 GHz, 100 mW, LR12 packet rate",
         role="Command, abort, and RTK corrections"),
    dict(name="LoRa, 865 MHz SF7", f_mhz=865, tx_dbm=14,
         g_tx_dbi=2, g_rx_dbi=2, sens_dbm=-123, adopted=True,
         hw="SX1262, 865--867 MHz delicensed SRD band, 25 mW",
         role="Mission data, detections, and swarm coordination"),
    dict(name="802.11, 5.8 GHz (withdrawn)", f_mhz=5800, tx_dbm=20,
         g_tx_dbi=5, g_rx_dbi=5, sens_dbm=-82, adopted=False,
         hw="MT7612U mesh point, MCS0 20 MHz",
         role="Original single-mesh design; withdrawn on margin"),
]


def fspl_db(f_mhz: float, d_m: float) -> float:
    """Free-space path loss, Friis, in dB. d in metres, f in MHz."""
    return 20 * math.log10(d_m / 1000) + 20 * math.log10(f_mhz) + 32.44


def margin_db(link: dict, d_m: float = GEOFENCE_M) -> float:
    """Link margin over the receiver's sensitivity floor, free space only."""
    return (link["tx_dbm"] + link["g_tx_dbi"] + link["g_rx_dbi"]
            - fspl_db(link["f_mhz"], d_m) - link["sens_dbm"])


def range_at_zero_margin_m(link: dict) -> float:
    """Range at which the link reaches its sensitivity floor, free space only.

    This is not an operating range. It is the point at which the link stops
    working with nothing at all left over, which is why the adopted links are
    flown at a fraction of it.
    """
    eirp = link["tx_dbm"] + link["g_tx_dbi"] + link["g_rx_dbi"] - link["sens_dbm"]
    return 1000 * 10 ** ((eirp - 20 * math.log10(link["f_mhz"]) - 32.44) / 20)


ADOPTED = [k for k in LINKS if k["adopted"]]
WITHDRAWN = [k for k in LINKS if not k["adopted"]]


# ---------------------------------------------------------------------------
# What the 865 MHz link has to carry, and whether it can
#
# WHY THIS IS HERE. Withdrawing the 802.11 mesh moved mission data and swarm
# coordination onto a narrowband link. The old mesh budget offered 235 kbps per
# aircraft of non-video traffic; LoRa SF7 carries 5469 bps for the whole fleet.
# Nothing in the earlier document noticed the factor of 129, because the two
# architectures were never costed against the same traffic. This is that
# costing, and its first result was that the obvious allocation does not fit.
#
# Airtime follows the SX127x/SX126x formulation (Semtech AN1200.13) rather than
# payload divided by bit rate. For the short packets this mission sends, LoRa's
# preamble and coded header dominate: a 20-byte report costs 56.6 ms, not the
# 29 ms the nominal bit rate would suggest.

LORA_BW_HZ = 125e3     # 865-867 MHz in India permits <= 200 kHz per carrier,
LORA_SF = 7            # so 250 kHz is not available and SF7 is the fastest
LORA_CR = 1            # coding rate 4/5, i.e. CR = 1 in the datasheet notation
LORA_PREAMBLE = 8
N_AIRCRAFT = 3

# GFSK is the same SX1262 in its other modulation. The link budget is what
# makes it available: LoRa SF7 closes the 600 m geofence with 54.3 dB, and
# nothing in this mission needs 54 dB. Spending 19 dB of that surplus to buy a
# 9x rate increase is the trade the margin column exists to license.
GFSK_BPS = 50e3
GFSK_OVERHEAD_B = 8    # preamble, sync word, length byte, CRC-16
GFSK_SENS_DBM = -104   # SX1262 datasheet, 50 kbps GFSK, 156 kHz RX bandwidth

# Slotted-ALOHA throughput peaks at 37 % and pure ALOHA at 18 %, both with
# collisions degrading the channel well before the peak. The swarm shares a
# GNSS time base, so transmission is TDMA-slotted and collisions are designed
# out rather than tolerated; the ceiling is kept as headroom for retries, a
# fourth node, and the ground station's own traffic.
OCCUPANCY_CEILING = 0.25

# One consolidated frame per aircraft per second, not one packet per message
# type. This is the correction the first run of this model forced: three
# separate messages pay three preambles and three coded headers, and that
# overhead alone was what pushed the channel over its ceiling.
FRAME_B = 36           # state 20 B + task and consensus 16 B
FRAME_DET_B = 60       # the same frame with a detection report appended
FRAME_HZ = 1.0
DET_FRACTION = 0.20    # share of frames carrying a detection


# What the withdrawn mesh offered per aircraft, for the comparison in the
# proposal. From the original data-rate budget: MAVLink telemetry at 10 Hz,
# swarm state and task consensus at 5 Hz, and detection metadata with
# thumbnails. Video is excluded -- it is analog now and on its own carrier.
MESH_NONVIDEO_KBPS = 60 + 25 + 150

# The allocation that did NOT fit, kept because the failure is the finding:
# three separate messages pay three preambles and three coded headers.
NAIVE_TRAFFIC = [
    dict(name="Aircraft state", bytes=20, rate_hz=1.0),
    dict(name="Task and consensus", bytes=16, rate_hz=0.5),
    dict(name="Detection report", bytes=24, rate_hz=0.2),
]


def naive_occupancy():
    return N_AIRCRAFT * sum(t["rate_hz"] * lora_airtime_s(t["bytes"])
                            for t in NAIVE_TRAFFIC)


def lora_bitrate_bps(sf=LORA_SF, bw_hz=LORA_BW_HZ, cr=LORA_CR):
    """Nominal LoRa bit rate, SF x BW / 2^SF x 4/(4+CR)."""
    return sf * bw_hz / (2 ** sf) * (4 / (4 + cr))


def lora_airtime_s(payload_bytes, sf=LORA_SF, bw_hz=LORA_BW_HZ, cr=LORA_CR,
                   preamble=LORA_PREAMBLE, explicit_header=True,
                   low_dr_opt=False):
    """Time on air for one LoRa packet, seconds."""
    t_sym = (2 ** sf) / bw_hz
    de = 1 if low_dr_opt else 0
    h = 0 if explicit_header else 1
    num = 8 * payload_bytes - 4 * sf + 28 + 16 - 20 * h
    n_payload = 8 + max(math.ceil(num / (4 * (sf - 2 * de))) * (cr + 4), 0)
    return (preamble + 4.25) * t_sym + n_payload * t_sym


def gfsk_airtime_s(payload_bytes):
    """Time on air for one GFSK packet, seconds."""
    return 8 * (payload_bytes + GFSK_OVERHEAD_B) / GFSK_BPS


def mean_frame_airtime_s(mode="lora"):
    """Airtime of the consolidated frame, averaged over frames with and
    without a detection report appended."""
    f = lora_airtime_s if mode == "lora" else gfsk_airtime_s
    return (1 - DET_FRACTION) * f(FRAME_B) + DET_FRACTION * f(FRAME_DET_B)


def occupancy(mode="lora"):
    """Fraction of the 865 MHz channel consumed by the whole fleet."""
    return N_AIRCRAFT * FRAME_HZ * mean_frame_airtime_s(mode)


def max_frame_hz(mode="lora"):
    """Frame rate that would exhaust the occupancy ceiling."""
    return OCCUPANCY_CEILING / (N_AIRCRAFT * mean_frame_airtime_s(mode))


def gfsk_margin_db(d_m=GEOFENCE_M):
    """Margin for the coordination link in its GFSK mode. Same radio, same
    antennas and same power as the LoRa row; only the sensitivity changes."""
    k = next(x for x in LINKS if x["f_mhz"] == 865)
    return (k["tx_dbm"] + k["g_tx_dbi"] + k["g_rx_dbi"]
            - fspl_db(k["f_mhz"], d_m) - GFSK_SENS_DBM)


if __name__ == "__main__":
    print(f"\n  margin at the {GEOFENCE_M:.0f} m geofence, free space only\n")
    print(f"  {'link':<30}{'margin':>9}{'0 dB at':>11}")
    print("  " + "-" * 50)
    for k in LINKS:
        print(f"  {k['name']:<30}{margin_db(k):8.1f} dB"
              f"{range_at_zero_margin_m(k)/1000:8.2f} km")

    print(f"\n  coordination channel: {N_AIRCRAFT} aircraft, one {FRAME_B} B "
          f"frame at {FRAME_HZ:.0f} Hz each\n")
    print(f"  {'mode':<22}{'rate':>9}{'frame':>10}{'occupancy':>12}"
          f"{'margin':>10}{'max rate':>11}")
    print("  " + "-" * 74)
    for mode, label, rate, mg in (
            ("lora", "LoRa SF7, 125 kHz", lora_bitrate_bps(),
             margin_db(next(x for x in LINKS if x["f_mhz"] == 865))),
            ("gfsk", "GFSK 50 kbps", GFSK_BPS, gfsk_margin_db())):
        print(f"  {label:<22}{rate/1000:>7.1f}k{mean_frame_airtime_s(mode)*1000:>9.1f}ms"
              f"{100*occupancy(mode):>11.1f}%{mg:>9.1f}dB"
              f"{max_frame_hz(mode):>10.1f}Hz")
    print(f"\n  ceiling {100*OCCUPANCY_CEILING:.0f} %")
    for mode in ("lora", "gfsk"):
        o = occupancy(mode)
        print(f"    {mode:<6}{100*o:6.1f} %  ->  "
              f"{'FITS' if o < OCCUPANCY_CEILING else 'EXCEEDS'}, "
              f"headroom {OCCUPANCY_CEILING/o:.2f}x")
    print()
