#!/usr/bin/env python3
"""The scenario the two fixes exist for: three aircraft, one pack design, one pad.

They take off to their own strips and hold. Nothing is scripted after that. The
battery drains on its own until BATT_LOW_MAH trips, and because all three fly
the same aircraft on the same mission profile, all three trip within seconds of
each other and every one turns for the same 3.66 m pad.

That is the collision the reported video showed and the return-to-pad it did
not. Both, in one recording, with no intervention.
"""
from __future__ import annotations

import json
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

from coverage_planner.geo import Frame                       # noqa: E402
from coverage_planner.plan import pad_slots, plan_mission     # noqa: E402
from pymavlink import mavutil                                 # noqa: E402

AP = os.path.expanduser("~/ardupilot")
BIN = f"{AP}/build/sitl/bin/arducopter"
RUN = os.path.expanduser("~/endurance-run")
SPEEDUP = 20
N = 3
OUT = os.environ.get("NIDAR_OUT", os.path.join(SYS, "simulations", "recordings"))
PAD = (12.99700, 80.00000)
BOUNDARY = [(12.99800, 79.99862), (12.99800, 80.00138),
            (13.00160, 80.00138), (13.00160, 79.99862)]
MODES = {0: "STABILIZE", 2: "ALT_HOLD", 3: "AUTO", 4: "GUIDED", 5: "LOITER",
         6: "RTL", 9: "LAND", 16: "POSHOLD"}


def setp(m, n, v):
    m.mav.param_set_send(m.target_system, m.target_component, n.encode(),
                         float(v), mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
    time.sleep(0.25)


def main():
    frame = Frame.from_points(BOUNDARY)
    plan = plan_mission(BOUNDARY, PAD, n_drones=N)
    slots = pad_slots(PAD, N, frame)
    # Hold point: the centre of each drone's own strip, at its search altitude.
    holds = []
    for d in plan.drones:
        xs = [frame.to_xy(a, b) for a, b in d.region]
        holds.append((sum(p[0] for p in xs) / len(xs),
                      sum(p[1] for p in xs) / len(xs)))

    os.makedirs(RUN, exist_ok=True)
    subprocess.run(["pkill", "-f", "bin/arducopter"], check=False)
    time.sleep(2)
    for i in range(1, N + 1):
        d = f"{RUN}/sitl{i}"
        os.makedirs(d, exist_ok=True)
        subprocess.Popen(
            [BIN, "--model", "quad", "--instance", str(i - 1),
             "--sysid", str(i),
             "--home", f"{slots[i-1][0]:.8f},{slots[i-1][1]:.8f},10,0",
             "--serial0", f"udpclient:127.0.0.1:{14550 + i}",
             "--defaults", ",".join([
                 f"{AP}/Tools/autotest/default_params/copter.parm",
                 f"{SYS}/firmware/ardupilot-params/rescueswarm-drone{i}.parm",
                 f"{SCR}/scripts/sitl-sim.parm"])],
            cwd=d, stdout=open(f"{d}/sitl.log", "w"),
            stderr=subprocess.STDOUT)
    print("SITL x3 launched"); time.sleep(10)

    links = []
    for i in range(1, N + 1):
        m = mavutil.mavlink_connection(f"udpin:0.0.0.0:{14550+i}",
                                       source_system=250)
        if not m.wait_heartbeat(timeout=90):
            print(f"drone {i}: no heartbeat"); return 1
        links.append(m)
        setp(m, "SIM_SPEEDUP", SPEEDUP)
        setp(m, "DISARM_DELAY", 0)
        for mid, hz in ((0, 3), (33, 4), (147, 2), (253, 4)):
            m.mav.command_long_send(
                m.target_system, m.target_component,
                mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
                mid, int(1e6 / hz), 0, 0, 0, 0, 0)
    print("all three up")

    time.sleep(35)
    for i, m in enumerate(links, start=1):
        armed, dl = False, time.time() + 90
        while time.time() < dl and not armed:
            m.set_mode("GUIDED"); time.sleep(1)
            m.mav.command_long_send(
                m.target_system, m.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
                1, 0, 0, 0, 0, 0, 0)
            end = time.time() + 6
            while time.time() < end:
                hb = m.recv_match(type="HEARTBEAT", blocking=True, timeout=2)
                if hb and (hb.base_mode & 128):
                    armed = True; break
        print(f"drone {i}: armed={armed}")
        if not armed:
            return 1
        # Climb to the SEARCH deck, all three at the same altitude -- uniform
        # GSD is the whole reason search is not stratified.
        m.mav.command_long_send(m.target_system, m.target_component,
                                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                                0, 0, 0, 0, 0, 0, 0, 40)

    time.sleep(3)
    for i, m in enumerate(links, start=1):
        lat, lon = frame.to_latlon(*holds[i - 1])
        m.mav.set_position_target_global_int_send(
            0, m.target_system, m.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            0b0000111111111000, int(lat * 1e7), int(lon * 1e7), 40.0,
            0, 0, 0, 0, 0, 0, 0, 0)
    print("holding on station; draining the packs\n")

    rec = {i: [] for i in range(1, N + 1)}
    events, T0 = [], time.time()
    state = {i: {"mode": "?", "alt": 0.0, "x": 0.0, "y": 0.0, "volt": 0.0,
                 "mah": 0.0, "armed": True} for i in range(1, N + 1)}
    stop = threading.Event()
    lock = threading.Lock()

    def pump(i, m):
        while not stop.is_set():
            msg = m.recv_match(blocking=True, timeout=1)
            if msg is None:
                continue
            t, s = msg.get_type(), state[i]
            if t == "GLOBAL_POSITION_INT":
                s["x"], s["y"] = frame.to_xy(msg.lat / 1e7, msg.lon / 1e7)
                s["alt"] = msg.relative_alt / 1000.0
            elif t == "HEARTBEAT":
                s["mode"] = MODES.get(msg.custom_mode, str(msg.custom_mode))
                s["armed"] = bool(msg.base_mode & 128)
            elif t == "BATTERY_STATUS":
                s["volt"] = msg.voltages[0] / 1000.0
                s["mah"] = msg.current_consumed or 0.0
            elif t == "STATUSTEXT":
                with lock:
                    events.append([round(time.time() - T0, 1), i,
                                   msg.text.strip()])

    for th in [threading.Thread(target=pump, args=(i, m), daemon=True)
               for i, m in enumerate(links, start=1)]:
        th.start()

    seen = {}
    t0 = time.time()
    while time.time() - t0 < 700:
        now = time.time() - t0
        for i in range(1, N + 1):
            rec[i].append({"t": round(now, 2), **dict(state[i])})
            if state[i]["mode"] in ("RTL", "LAND") and i not in seen:
                seen[i] = now
                print(f"  t+{now:6.1f}s  drone {i} -> {state[i]['mode']}  "
                      f"{state[i]['mah']:.0f} mAh consumed")
        if len(seen) == N and all(not state[i]["armed"]
                                  for i in range(1, N + 1)):
            print(f"  t+{now:6.1f}s  all three disarmed")
            break
        time.sleep(0.4)
    stop.set(); time.sleep(1)

    json.dump({"n": N, "speedup": SPEEDUP, "kind": "endurance",
               "pad_xy": [list(frame.to_xy(*s)) for s in slots],
               "boundary_xy": [list(frame.to_xy(a, b)) for a, b in BOUNDARY],
               "strips": [[list(frame.to_xy(a, b)) for a, b in d.region]
                          for d in plan.drones],
               "rtl_alt": [25.0, 30.0, 35.0],
               "loiter_s": [0, 20, 40],
               "tracks": rec, "events": events},
              open(f"{OUT}/telemetry_endurance.json", "w"))
    print(f"\nwrote telemetry_endurance.json "
          f"({sum(len(v) for v in rec.values())} samples)")
    subprocess.run(["pkill", "-f", "bin/arducopter"], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
