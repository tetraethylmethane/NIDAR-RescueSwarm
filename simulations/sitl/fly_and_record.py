#!/usr/bin/env python3
"""Fly the real planned mission on three SITL aircraft and record everything.

Produces telemetry.json for render.py. The point is to show the two fixes doing
their job under the conditions that break them: a low battery that hits all
three aircraft at once, so every one of them turns for the same 3.66 m pad.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import threading
import time

# Repo root. Override with NIDAR_SYS; defaults to two levels up from
# this file, which is correct for a normal checkout.
SYS = os.environ.get("NIDAR_SYS", os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
SCR = os.environ.get("NIDAR_GSC",
                    os.path.join(os.path.dirname(SYS), "NIDAR-GSC"))
sys.path.insert(0, os.path.join(SYS, "autonomy"))

from coverage_planner.geo import Frame                      # noqa: E402
from coverage_planner.plan import pad_slots, plan_mission    # noqa: E402
from pymavlink import mavutil                                # noqa: E402

AP = os.path.expanduser("~/ardupilot")
BIN = f"{AP}/build/sitl/bin/arducopter"
RUN = os.path.expanduser("~/swarm-run")
SPEEDUP = 15
N = 3
OUT = os.environ.get("NIDAR_OUT", os.path.join(SYS, "simulations", "recordings"))

# A 400 m square, pad to the south. Smaller than the competition area so the
# sweep and the battery event both fit inside one recording.
PAD = (12.99700, 80.00000)
# INSIDE THE GEOFENCE. The first attempt put the far edge ~650 m from the pad
# against FENCE_RADIUS = 600 m, and all three aircraft breached and RTL'd three
# seconds into the sweep. Worth knowing before the competition: the fence
# radius is a hard limit on how far the search area can sit from launch, and
# 600 m was chosen to match the link budget, not the search geometry.
BOUNDARY = [(12.99800, 79.99862), (12.99800, 80.00138),
            (13.00160, 80.00138), (13.00160, 79.99862)]

# Shrink the SIMULATED pack so the failsafe lands mid-sweep instead of 44
# simulated minutes in. The aircraft's own thresholds are untouched: this
# changes the world, not the vehicle. BATT_LOW_VOLT (20.4 V, 3.40 V/cell) is
# the threshold that fires, which is the real voltage failsafe path.
SIM_BATT_CAP_AH = 1.35


def build_missions():
    frame = Frame.from_points(BOUNDARY)
    # Take the shipped defaults rather than restating them. Pinning
    # transit_alt_m=25 here is what this harness used to do, and plan_mission
    # now rejects it: 25/30/35 leaves the top band 5 m under the search deck.
    plan = plan_mission(BOUNDARY, PAD, n_drones=N, altitude_m=40.0,
                        speed_ms=8.0)
    slots = pad_slots(PAD, N, frame)
    return plan, slots, frame


def launch(i, slot):
    d = f"{RUN}/sitl{i}"
    os.makedirs(d, exist_ok=True)
    cmd = [
        BIN, "--model", "quad", "--instance", str(i - 1), "--sysid", str(i),
        "--home", f"{slot[0]:.8f},{slot[1]:.8f},10,0",
        "--serial0", f"udpclient:127.0.0.1:{14550 + i}",
        "--defaults", ",".join([
            f"{AP}/Tools/autotest/default_params/copter.parm",
            f"{SYS}/firmware/ardupilot-params/rescueswarm-drone{i}.parm",
            f"{SCR}/scripts/sitl-sim.parm",
        ]),
    ]
    log = open(f"{d}/sitl.log", "w")
    return subprocess.Popen(cmd, cwd=d, stdout=log, stderr=subprocess.STDOUT)


def upload(m, items):
    """Classic mission upload. Items are coverage_planner mission.Item."""
    m.mav.mission_count_send(m.target_system, m.target_component, len(items))
    sent = 0
    t0 = time.time()
    while sent < len(items) and time.time() - t0 < 60:
        req = m.recv_match(type=["MISSION_REQUEST", "MISSION_REQUEST_INT"],
                           blocking=True, timeout=10)
        if req is None:
            break
        it = items[req.seq]
        m.mav.mission_item_int_send(
            m.target_system, m.target_component, req.seq, it.frame,
            it.command, it.current, it.autocontinue,
            it.p1, it.p2, it.p3, it.p4,
            int(it.lat * 1e7), int(it.lon * 1e7), it.alt)
        sent = req.seq + 1
    ack = m.recv_match(type="MISSION_ACK", blocking=True, timeout=15)
    return ack is not None and sent == len(items)


def setp(m, name, val):
    m.mav.param_set_send(m.target_system, m.target_component, name.encode(),
                         float(val), mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
    time.sleep(0.25)


MODES = {0: "STABILIZE", 2: "ALT_HOLD", 3: "AUTO", 4: "GUIDED", 5: "LOITER",
         6: "RTL", 9: "LAND", 16: "POSHOLD", 20: "GUIDED_NOGPS"}


def main():
    plan, slots, frame = build_missions()
    print(plan.summary())
    os.makedirs(RUN, exist_ok=True)
    subprocess.run(["pkill", "-f", "bin/arducopter"], check=False)
    time.sleep(2)

    procs = [launch(i, slots[i - 1]) for i in range(1, N + 1)]
    print("SITL launched"); time.sleep(10)

    links = []
    for i in range(1, N + 1):
        m = mavutil.mavlink_connection(f"udpin:0.0.0.0:{14550 + i}",
                                       source_system=250)
        if not m.wait_heartbeat(timeout=90):
            print(f"drone {i}: no heartbeat"); return 1
        links.append(m)
        print(f"drone {i}: heartbeat")

    for i, m in enumerate(links, start=1):
        setp(m, "SIM_SPEEDUP", SPEEDUP)
        setp(m, "SIM_BATT_CAP_AH", SIM_BATT_CAP_AH)
        setp(m, "AUTO_OPTIONS", 3)
        setp(m, "DISARM_DELAY", 0)
        for mid, hz in ((0, 3), (33, 4), (147, 2), (253, 5)):
            m.mav.command_long_send(
                m.target_system, m.target_component,
                mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
                mid, int(1e6 / hz), 0, 0, 0, 0, 0)
        ok = upload(m, plan.drones[i - 1].items)
        print(f"drone {i}: mission {len(plan.drones[i-1].items)} items "
              f"{'uploaded' if ok else 'UPLOAD FAILED'}")
        if not ok:
            return 1

    print("waiting for EKF / pre-arm...")
    time.sleep(35)

    for i, m in enumerate(links, start=1):
        armed = False
        deadline = time.time() + 90
        while time.time() < deadline and not armed:
            m.set_mode("GUIDED")
            time.sleep(1)
            m.mav.command_long_send(
                m.target_system, m.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
                1, 0, 0, 0, 0, 0, 0)
            end = time.time() + 6
            while time.time() < end:
                hb = m.recv_match(type="HEARTBEAT", blocking=True, timeout=2)
                if hb and (hb.base_mode & 128):
                    armed = True
                    break
        print(f"drone {i}: armed={armed}")
        if not armed:
            return 1
        m.set_mode("AUTO")
        time.sleep(0.5)

    print("\nrecording...")
    rec = {i: [] for i in range(1, N + 1)}
    events = []
    T0 = [time.time()]
    state = {i: {"mode": "?", "alt": 0.0, "x": 0.0, "y": 0.0,
                 "volt": 0.0, "mah": 0.0} for i in range(1, N + 1)}
    stop = threading.Event()

    def pump(i, m):
        while not stop.is_set():
            msg = m.recv_match(blocking=True, timeout=1)
            if msg is None:
                continue
            t = msg.get_type()
            s = state[i]
            if t == "GLOBAL_POSITION_INT":
                x, y = frame.to_xy(msg.lat / 1e7, msg.lon / 1e7)
                s["x"], s["y"] = x, y
                s["alt"] = msg.relative_alt / 1000.0
            elif t == "HEARTBEAT":
                s["mode"] = MODES.get(msg.custom_mode, str(msg.custom_mode))
                s["armed"] = bool(msg.base_mode & 128)
            elif t == "BATTERY_STATUS":
                s["volt"] = msg.voltages[0] / 1000.0
                s["mah"] = msg.current_consumed or 0.0
            elif t == "STATUSTEXT":
                txt = msg.text.strip()
                events.append((round(time.time() - T0[0], 1), i, txt))
                if any(w in txt.lower() for w in
                       ("failsafe", "fence", "rtl", "land", "breach",
                        "mission", "disarm", "crash", "ekf")):
                    print(f"  [{time.time() - T0[0]:5.1f}s d{i}] {txt}")

    threads = [threading.Thread(target=pump, args=(i, m), daemon=True)
               for i, m in enumerate(links, start=1)]
    for th in threads:
        th.start()

    t0 = time.time()
    seen_rtl, done_at = set(), None
    while time.time() - t0 < 900:
        now = time.time() - t0
        for i in range(1, N + 1):
            rec[i].append({"t": round(now, 2), **{k: v for k, v in
                                                  state[i].items()}})
        for i in range(1, N + 1):
            if state[i]["mode"] in ("RTL", "LAND") and i not in seen_rtl:
                seen_rtl.add(i)
                print(f"  t+{now:5.0f}s  drone {i} -> {state[i]['mode']} "
                      f"({state[i]['volt']:.1f} V, {state[i]['mah']:.0f} mAh)")
        landed = sum(1 for i in range(1, N + 1)
                     if not state[i].get("armed", True))
        if len(seen_rtl) == N and landed == N:
            done_at = now
            print(f"  t+{now:5.0f}s  all three disarmed on the pad")
            break
        time.sleep(0.5)

    stop.set()
    time.sleep(1)
    out = {
        "n": N, "speedup": SPEEDUP, "done_at": done_at,
        "pad_xy": [list(frame.to_xy(*s)) for s in slots],
        "boundary_xy": [list(frame.to_xy(a, b)) for a, b in BOUNDARY],
        "strips": [[list(frame.to_xy(a, b)) for a, b in d.region]
                   for d in plan.drones],
        "transit_alt": [d.transit_alt_m for d in plan.drones],
        "search_alt": plan.drones[0].altitude_m,
        "tracks": rec, "events": events,
    }
    with open(f"{OUT}/telemetry.json", "w") as fh:
        json.dump(out, fh)
    print(f"\nwrote telemetry.json  "
          f"({sum(len(v) for v in rec.values())} samples)")
    subprocess.run(["pkill", "-f", "bin/arducopter"], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
