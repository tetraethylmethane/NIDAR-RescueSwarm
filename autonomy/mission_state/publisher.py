"""The 5 Hz mission-state producer — the missing half of the GCS link.

The ground station has consumed this document since `mission_ingest.py` was
written, and nothing has ever produced it. This is that producer. It runs on the
companion computer and is the reason the GCS can show anything at all.

    companion ──5 Hz JSON over the mesh──► GCS Fleet.update_mission()

WHY NOT MAVLINK. Telemetry — position, mode, battery, GNSS fix — already flows
over MAVLink via mavlink-router and needs nothing here. What MAVLink has no
message for is "survivor 4 at 13.0001, 80.0002, confidence 0.91, confirmed over
7 frames, tagged with an RTK-fixed solution". Encoding that into
`NAMED_VALUE_FLOAT` or `DEBUG_VECT` is a trap: it costs more code than JSON,
loses the field names, and has to be decoded by hand at the other end.

The RF budget already allocates this: 25 kbps of swarm state plus 150 kbps of
detection metadata per drone (sizing §12.1), separate from telemetry.

THIS RUNS DURING A SCORED MISSION AND MUST NEVER TAKE THE AUTONOMY DOWN.
Every public method is non-blocking, the publish loop swallows every exception,
and a failed send is counted rather than raised. Losing the display costs the
evidence for 250 points; crashing the companion costs the aircraft.
"""
from __future__ import annotations

import json
import logging
import socket
import threading
import time
from typing import Any

log = logging.getLogger("autonomy.publisher")

PHASES = ("IDLE", "SETUP", "CLIMB", "SEARCH", "DELIVER", "RTH", "LANDED")
DELIVERY_STATES = ("UNASSIGNED", "ASSIGNED", "EN_ROUTE", "RELEASED",
                   "CONFIRMED", "FAILED")
FIXES = ("NONE", "2D", "3D", "DGPS", "RTK_FLOAT", "RTK_FIXED")


class MissionStatePublisher:
    """Holds this drone's mission state and broadcasts it at a fixed rate."""

    def __init__(self, drone_id: int, host: str = "255.255.255.255",
                 port: int = 14660, rate_hz: float = 5.0) -> None:
        if not 1 <= drone_id <= 250:
            raise ValueError("drone_id must be a valid MAVLink system id")
        self.drone_id = drone_id
        self.host = host
        self.port = port
        self.period = 1.0 / rate_hz

        self._lock = threading.Lock()
        self._phase = "IDLE"
        self._region: list[list[float]] = []
        self._task: dict[str, Any] = {}
        self._detections: dict[int, dict[str, Any]] = {}
        self._deliveries: dict[int, str] = {}

        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

        self.sent = 0
        self.failed = 0

    # ------------------------------------------------------------- state in
    def set_phase(self, phase: str) -> None:
        if phase not in PHASES:
            raise ValueError(f"unknown phase {phase!r}; expected one of {PHASES}")
        with self._lock:
            self._phase = phase

    def set_region(self, polygon) -> None:
        """The strip this drone was assigned, from the coverage planner."""
        with self._lock:
            self._region = [[float(a), float(b)] for a, b in polygon]

    def set_task(self, task: dict[str, Any] | None) -> None:
        with self._lock:
            self._task = dict(task) if task else {}

    def upsert_detection(self, survivor_id: int, lat: float, lon: float,
                         confidence: float = 0.0, frames: int = 1,
                         fix: str = "NONE") -> None:
        """Add or update a survivor observation.

        Upsert rather than append: a survivor is re-observed on every frame, and
        appending would grow the datagram without bound over an 8-minute
        mission. The GCS deduplicates across drones; this deduplicates within
        one.
        """
        if fix not in FIXES:
            raise ValueError(f"unknown fix {fix!r}")
        with self._lock:
            self._detections[int(survivor_id)] = {
                "id": int(survivor_id),
                "lat": float(lat), "lon": float(lon),
                "conf": round(float(confidence), 3),
                "frames": int(frames),
                "fix": fix,
            }

    def set_delivery(self, survivor_id: int, state: str) -> None:
        if state not in DELIVERY_STATES:
            raise ValueError(f"unknown delivery state {state!r}")
        with self._lock:
            self._deliveries[int(survivor_id)] = state

    def clear_detections(self) -> None:
        with self._lock:
            self._detections.clear()

    # ------------------------------------------------------------ state out
    def snapshot(self) -> dict[str, Any]:
        """The document as it will be sent. Safe to call from any thread."""
        with self._lock:
            return {
                "drone": self.drone_id,
                "t": time.time(),
                "state": self._phase,
                "region": [list(p) for p in self._region],
                "task": dict(self._task),
                "detections": list(self._detections.values()),
                "deliveries": [{"survivor": s, "state": st}
                               for s, st in sorted(self._deliveries.items())],
            }

    def encode(self) -> bytes:
        return json.dumps(self.snapshot(), separators=(",", ":")).encode("utf-8")

    # ---------------------------------------------------------------- loop
    def _open(self) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        return s

    def publish_once(self) -> bool:
        """Send one datagram. Returns success. Never raises."""
        try:
            if self._sock is None:
                self._sock = self._open()
            payload = self.encode()
            self._sock.sendto(payload, (self.host, self.port))
            self.sent += 1
            return True
        except OSError as exc:
            # A dropped mesh, a reconfigured interface, an unreachable host --
            # all expected mid-mission. Count it, drop the socket so the next
            # attempt reopens, and carry on flying.
            self.failed += 1
            log.debug("mission-state send failed: %s", exc)
            try:
                if self._sock:
                    self._sock.close()
            except OSError:
                pass
            self._sock = None
            return False
        except Exception:                       # pragma: no cover - never fatal
            self.failed += 1
            log.exception("unexpected error publishing mission state")
            return False

    def _loop(self) -> None:
        next_at = time.monotonic()
        while not self._stop.is_set():
            self.publish_once()
            next_at += self.period
            delay = next_at - time.monotonic()
            if delay < 0:                       # fell behind; resync, do not spin
                next_at = time.monotonic()
                delay = 0
            self._stop.wait(delay)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name=f"mission-pub-{self.drone_id}")
        self._thread.start()
        log.info("mission-state publisher %d -> %s:%d at %.1f Hz",
                 self.drone_id, self.host, self.port, 1.0 / self.period)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None


def from_plan(drone_plan, host: str = "255.255.255.255", port: int = 14660,
              rate_hz: float = 5.0) -> MissionStatePublisher:
    """Build a publisher already loaded with a coverage-planner assignment."""
    p = MissionStatePublisher(drone_plan.drone_id, host, port, rate_hz)
    p.set_region(drone_plan.region)
    p.set_phase("SETUP")
    p.set_task({"type": "SEARCH", "lines": len(drone_plan.lines)})
    return p
