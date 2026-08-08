"""Publisher tests — including a real round trip into the GCS's own ingest.

The point of the integration test at the bottom is that the producer and the
consumer were written days apart against a schema in a docstring. Nothing had
ever proved they agree. This runs the real publisher over a real socket into the
real `Fleet`, and asserts the survivors come out the far end.
"""
import json
import math
import os
import socket
import sys
import threading
import time

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "ground-station"))

from coverage_planner.geo import Frame  # noqa: E402
from coverage_planner.plan import plan_mission  # noqa: E402
from mission_state.publisher import MissionStatePublisher, from_plan  # noqa: E402


def pub(**kw):
    kw.setdefault("host", "127.0.0.1")
    kw.setdefault("port", 14699)
    return MissionStatePublisher(kw.pop("drone_id", 1), **kw)


def test_document_shape_matches_the_gcs_schema():
    p = pub()
    p.set_phase("SEARCH")
    p.set_region([(13.0, 80.0), (13.0, 80.1), (13.1, 80.1)])
    p.set_task({"type": "SEARCH"})
    p.upsert_detection(4, 13.0001, 80.0002, 0.91, 7, "RTK_FIXED")
    p.set_delivery(4, "EN_ROUTE")
    d = p.snapshot()

    assert set(d) == {"drone", "t", "state", "region", "task",
                      "detections", "deliveries"}
    assert d["drone"] == 1 and d["state"] == "SEARCH"
    assert d["detections"][0]["fix"] == "RTK_FIXED"
    assert d["deliveries"][0] == {"survivor": 4, "state": "EN_ROUTE"}
    json.dumps(d)                       # must be serialisable as-is


def test_detections_upsert_rather_than_append():
    """A survivor is re-observed every frame. Appending would grow the datagram
    without bound across an 8-minute mission."""
    p = pub()
    for i in range(200):
        p.upsert_detection(4, 13.0, 80.0, 0.5, i + 1, "RTK_FLOAT")
    d = p.snapshot()
    assert len(d["detections"]) == 1
    assert d["detections"][0]["frames"] == 200


def test_datagram_stays_small_with_a_full_mission():
    """10 survivors, 10 deliveries and a 40-vertex region must still fit in one
    UDP datagram comfortably."""
    p = pub()
    p.set_region([(13.0 + i * 1e-4, 80.0 + i * 1e-4) for i in range(40)])
    for s in range(1, 11):
        p.upsert_detection(s, 13.0 + s * 1e-4, 80.0, 0.9, 12, "RTK_FIXED")
        p.set_delivery(s, "CONFIRMED")
    size = len(p.encode())
    assert size < 4000, f"{size} B — approaching fragmentation"


def test_bad_values_are_rejected_at_the_setter():
    p = pub()
    with pytest.raises(ValueError):
        p.set_phase("CRUISING")
    with pytest.raises(ValueError):
        p.set_delivery(1, "DROPPED")
    with pytest.raises(ValueError):
        p.upsert_detection(1, 13.0, 80.0, fix="RTK")
    with pytest.raises(ValueError):
        MissionStatePublisher(0)
    with pytest.raises(ValueError):
        MissionStatePublisher(300)


def test_send_failure_is_counted_not_raised():
    """A dropped mesh mid-mission must not propagate into the autonomy."""
    p = MissionStatePublisher(1, host="192.0.2.1", port=1)   # TEST-NET-1
    p._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    p._sock.close()                                           # force EBADF
    assert p.publish_once() is False
    assert p.failed == 1
    assert p._sock is None, "socket should be dropped so the next send reopens"


def test_publishes_at_the_requested_rate():
    p = pub(rate_hz=20.0)
    p.start()
    time.sleep(0.6)
    p.stop()
    assert 8 <= p.sent <= 18, f"sent {p.sent} in 0.6 s at 20 Hz"


def test_from_plan_loads_the_assigned_region():
    f = Frame(13.0, 80.0)
    ten = [f.to_latlon(0, 0), f.to_latlon(400, 0),
           f.to_latlon(400, 250), f.to_latlon(0, 250)]
    plan = plan_mission(ten, (12.9995, 79.9995), 3)
    p = from_plan(plan.drones[1], host="127.0.0.1", port=14699)
    d = p.snapshot()
    assert d["drone"] == 2
    assert len(d["region"]) >= 4
    assert d["task"]["lines"] == len(plan.drones[1].lines)


# --------------------------------------------------------------- integration
gs = pytest.importorskip("mission_backend.fleet",
                         reason="ground-station package not on the path")


def test_publisher_reaches_the_real_gcs_fleet():
    """Producer and consumer were written days apart against a docstring.

    This proves they actually agree: three real publishers, one real UDP
    listener, one real Fleet, and the survivors must come out the far end with
    the right fix quality.
    """
    from mission_backend.fleet import Fleet
    from mission_backend.mission_ingest import MissionIngest

    fleet = Fleet()
    ing = MissionIngest(fleet, host="127.0.0.1", port=0)
    ing.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ing.sock.bind(("127.0.0.1", 0))
    port = ing.sock.getsockname()[1]
    ing.sock.settimeout(1.0)
    ing._thread = threading.Thread(target=ing._loop, daemon=True)
    ing._thread.start()

    f = Frame(13.0, 80.0)
    ten = [f.to_latlon(0, 0), f.to_latlon(400, 0),
           f.to_latlon(400, 250), f.to_latlon(0, 250)]
    plan = plan_mission(ten, (12.9995, 79.9995), 3)

    pubs = []
    try:
        for dp in plan.drones:
            p = from_plan(dp, host="127.0.0.1", port=port)
            p.set_phase("SEARCH")
            pubs.append(p)

        # drone 2 sees survivor 4 with a float fix; drone 3 re-sees it fixed.
        pubs[1].upsert_detection(4, 13.0009, 80.0009, 0.99, 3, "RTK_FLOAT")
        pubs[2].upsert_detection(4, 13.0001, 80.0001, 0.70, 9, "RTK_FIXED")
        pubs[0].upsert_detection(1, 13.0005, 80.0005, 0.88, 6, "RTK_FIXED")
        pubs[0].set_delivery(1, "RELEASED")

        for p in pubs:
            for _ in range(3):
                assert p.publish_once()

        deadline = time.time() + 3.0
        while time.time() < deadline and ing.stats.accepted < 9:
            time.sleep(0.02)
    finally:
        ing.stop()

    assert ing.stats.rejected == 0, f"GCS rejected {ing.stats.rejected} datagrams"
    assert ing.stats.accepted >= 3

    # regions arrived, one per drone
    assert all(len(fleet.mission[i].region) >= 4 for i in (1, 2, 3))

    survivors = fleet.survivors()
    assert set(survivors) == {1, 4}
    # the GCS dedup must prefer the FIXED tag from drone 3 over the newer float
    assert survivors[4].fix == "RTK_FIXED"
    assert survivors[4].reported_by == 3
    assert survivors[4].lat == pytest.approx(13.0001)

    prog = fleet.progress()
    assert prog["found"] == 2
    assert prog["delivered"] == 1
    assert fleet.warnings() == [] or all("stale" in w or "RTK" in w
                                         for w in fleet.warnings())
