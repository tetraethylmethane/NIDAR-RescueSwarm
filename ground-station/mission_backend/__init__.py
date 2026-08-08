"""Mission-side ground station backend.

Multi-vehicle fleet model, KML boundary parsing, and the SYS-20 module split.
Drops into the existing Flask server; see ../PLAN.md.
"""
from .fleet import Delivery, Detection, Fleet, MissionState, VehicleState
from .kml import Boundary, KMLError, parse_boundary
from .mavlink_ingest import MavlinkIngest, handle_message
from .mission_ingest import MissionIngest, handle_datagram

__all__ = ["Fleet", "VehicleState", "MissionState", "Detection", "Delivery",
           "Boundary", "KMLError", "parse_boundary",
           "MavlinkIngest", "handle_message",
           "MissionIngest", "handle_datagram"]
