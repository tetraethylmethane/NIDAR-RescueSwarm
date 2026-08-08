# perception

Detection, tiled inference, geotagging, calibration

**Status: not yet written.** Planned for the phase noted in
[`../docs/development-plan.md`](../docs/development-plan.md).

> **Read [`../docs/perception-integration-plan.md`](../docs/perception-integration-plan.md)
> before writing anything here.** Datasets and the detector are owned by one
> person, the geotag by another, and the interface between them is the only
> thing that has to be agreed up front. Geotag gates **450 of the 600 flight
> points** and is worth **102 points** between a naive implementation and a
> good one — none of which the detector can recover.

Requirements this directory must satisfy: SYS-07, SYS-12, SYS-33, SYS-48 — see
[`../docs/requirements/requirements-baseline.md`](../docs/requirements/requirements-baseline.md).
