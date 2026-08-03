# NIDAR RescueSwarm

> An autonomous multi-drone system for rapid flood survivor search, localization, and emergency aid delivery.

---

## Overview

RescueSwarm is a coordinated fleet of autonomous drones designed for disaster response in communication-denied environments. The system collaboratively searches flood-affected areas, detects stranded survivors, geotags their locations, delivers emergency medical kits, and reports the entire mission to a single operator.

<p align="center">
  <img src="docs/images/system-overview.png" width="900" alt="System Overview">
</p>

---

## Mission Flow

```text
Launch
   │
   ▼
Load Mission Boundary
   │
   ▼
Divide Search Area
   │
   ▼
Parallel Autonomous Search
   │
   ▼
Detect Survivors
   │
   ▼
Geotag Locations
   │
   ▼
Assign Delivery Drone
   │
   ▼
Deliver Medical Kit
   │
   ▼
Mission Complete
   │
   ▼
Return to Home
```

---

## Features

| Capability             | Description                                           |
| ---------------------- | ----------------------------------------------------- |
| Autonomous Search      | Multiple drones collaboratively scan the mission area |
| Survivor Detection     | Detects and localizes stranded survivors              |
| Geotagging             | Records GPS coordinates automatically                 |
| Collaborative Planning | Dynamic task allocation between drones                |
| Medical Delivery       | Drops emergency aid near survivors                    |
| Local Communication    | Fully offline drone-to-drone coordination             |
| Ground Station         | Single interface for monitoring the entire mission    |
| Safety System          | Automatic failsafe and emergency recall               |

---

## System Architecture

<p align="center">
  <img src="docs/images/architecture.png" width="900" alt="Architecture">
</p>

```
                    Ground Control Station
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
     Drone A           Drone B           Drone C
        │                  │                  │
        └──────── Shared Local Network ───────┘
                 Search • Detect • Deliver
```

---

## Mission Constraints

| Requirement        | Value                  |
| ------------------ | ---------------------- |
| Minimum Drones     | 2                      |
| Search Area        | Up to 10 hectares      |
| Mission Time       | ≤ 30 minutes           |
| Total Drone Weight | ≤ 25 kg                |
| Payload            | 200 g (20 × 10 × 5 cm) |
| Launch Area        | 12 × 12 ft             |
| Human Operators    | 1                      |
| External Network   | Not Allowed            |

---

## Autonomous Workflow

* Load mission boundary
* Divide search area
* Coordinate multiple drones
* Detect survivors
* Geotag locations
* Assign delivery tasks
* Deliver medical kits
* Return to launch point

---

## Safety

* Return-to-Home
* Low Battery Failsafe
* Command Link Loss Recovery
* Geofence Protection
* Mission Abort
* Emergency Recall

---

## Repository Structure

```text
.
├── firmware/
├── autonomy/
├── perception/
├── communication/
├── ground-station/
├── simulations/
├── hardware/
├── docs/
│   ├── images/
│   └── diagrams/
└── README.md
```

---

## Technologies

* PX4 / ArduPilot
* ROS 2
* MAVLink
* Computer Vision
* Multi-Agent Mission Planning
* Edge AI
* Local Mesh Communication

---

## Project Goal

Develop a fully autonomous multi-drone rescue system capable of locating flood survivors and delivering emergency aid quickly, safely, and without reliance on external communication networks.

---
