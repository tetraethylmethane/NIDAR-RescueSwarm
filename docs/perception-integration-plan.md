# Perception integration plan

**Audience:** whoever is building the datasets and the vision model, plus
whoever is building the rest of the aircraft software. It is written to be read
cold — no prior context assumed.

**Purpose:** agree the seam between "the detector found something" and "the
ground station shows a survivor at a lat/lon", before either side writes code
that assumes the other's shape.

---

## 1. Why this document exists at all

Detection and geotagging are **one scored item worth 250 points** (SYS-07,
SYS-12), and delivery accuracy is a further 200 that is aimed using the geotag.
So the geotag gates **450 of the 600 flight points**.

The delivery model ([`sizing/delivery-accuracy-output.txt`](sizing/delivery-accuracy-output.txt))
puts numbers on it:

| Case | geotag RSS | pts/drop | 10 drops |
|:--|--:|--:|--:|
| A — no RTK, single frame | 3.09 m | 7.5 | **75** |
| B — RTK, single frame | 1.36 m | 15.7 | **157** |
| C — RTK + multi-frame fusion + calibrated | 1.00 m | 17.7 | **177** |

**102 points separate A from C, and none of that gap is the detector's doing.**
Geotag is 74.9 % of the delivery error variance. A very good detector with a
naive geotag scores 75; an average detector with a good geotag scores 177.

The risk this document addresses is not technical, it is organisational: geotag
sits between two people, each of whom can reasonably assume it belongs to the
other. It then surfaces in P7 with no calendar left.

---

## 2. Division of labour

| | Owner | Deliverable |
|:--|:--|:--|
| Datasets, training, the detector | **Vision** | A model that emits `Detection` (§3) per frame |
| Tiled inference, on-SBC throughput | **Vision** | ≥ 2 Hz end-to-end on the target compute |
| Ray→ground geotag, fusion, calibration | **Platform** | `Detection` → `(lat, lon, fix)` |
| Publishing to the GCS | **Platform** | Already built — `autonomy/mission_state/publisher.py` |
| Recall measurement | **Both** | Real imagery, real dummies, agreed protocol (§7) |

If Vision would rather own the geotag too, say so **before** Platform starts —
the point of this document is that exactly one of us writes it.

---

## 3. The interface contract

This is the only thing both sides must agree on. Everything else is internal.

**Vision emits, per detection, per frame:**

```python
@dataclass(frozen=True)
class Detection:
    frame_id: int          # monotonic, per camera
    t_capture: float       # UNIX seconds, CAMERA EXPOSURE time, not receipt
    bbox: tuple[float, float, float, float]   # x, y, w, h in PIXELS, full-res frame
    confidence: float      # 0..1, calibrated if possible
    class_id: int          # 0 = person; reserve others
    camera_id: int = 0
```

Platform consumes that and produces:

```python
@dataclass(frozen=True)
class Geotag:
    lat: float
    lon: float
    fix: str               # NONE | 2D | 3D | DGPS | RTK_FLOAT | RTK_FIXED
    sigma_m: float         # 1-sigma horizontal, for fusion and for the GCS
    off_nadir_deg: float   # SYS-33 gate, see §5
```

which feeds the already-built publisher:

```python
publisher.upsert_detection(survivor_id, lat, lon, confidence, frames, fix)
```

### Three details that are easy to get wrong and expensive to fix late

**1. `t_capture` must be the exposure timestamp, not when your code saw the
frame.** The geotag interpolates aircraft attitude and position to that instant.
At 8 m/s a 100 ms timestamp error is **0.8 m of position error** — comparable to
the entire 0.91 m budget. If the camera driver can give a hardware timestamp,
use it and tell Platform which clock it is on.

**2. Bounding boxes in full-resolution pixel coordinates.** If inference runs on
a downsampled or tiled image — the plan is 2× downsample and 12 tiles — map the
box back to full-res before emitting. Platform should never need to know the
tiling scheme, and a factor-of-two coordinate bug is invisible in a demo and
fatal in scoring.

**3. Emit every frame's detections, not just new ones.** Deduplication and
identity are Platform's job (§4). Vision does not need to track survivors
between frames, and should not try — repeated independent observations are what
multi-frame fusion needs, and suppressing them costs the 20 points/drop that
separate case B from case C.

---

## 4. What Platform builds

**`perception/geotagging/`**

1. **Ray → ground intersection.** Pixel centroid → camera ray using intrinsics →
   rotate by gimbal + aircraft attitude → intersect the local ground plane at
   the aircraft's AGL → offset from the RTK position. Pure geometry; fully
   testable with no camera and no aircraft.
2. **Multi-frame fusion.** Cluster observations that fall within a gate, then
   combine inverse-variance weighted. This is the B → C step: **+20 points per
   drop**.
3. **Identity and confirmation.** Assign a stable `survivor_id`, count
   `frames`, and only publish once confirmed. The GCS already ranks competing
   observations by **fix quality first, then frames, then confidence** — a later
   `RTK_FLOAT` tag is metres worse than an earlier `RTK_FIXED` one — so the
   aircraft side must report the fix honestly rather than optimistically.
4. **Wire to the publisher**, replacing `sim_mission.py` as the source.

**`perception/calibration/` (SYS-48)**

Boresight and lever-arm. **No accuracy claim is valid before this is done** —
that is the requirement, not a preference. A 1° boresight error at 60 m AGL is
**1.05 m on the ground**, which alone blows the whole budget.

---

## 5. Constraints that come from the rules and the model

- **SYS-12: CEP50 ≤ 0.75 m** (0.91 m RSS). At the older 2.0 m target, Zone A
  (≤ 1 m, 20 pts) is unreachable no matter how good the drop is.
- **SYS-33: only geotag detections within ≤ 20° off-nadir.** Edge-of-frame
  detections must be re-acquired near nadir rather than tagged where they lie.
  Platform enforces this; Vision does not need to filter.
- **SYS-07: ≥ 90 % recall**, up to 10 survivors. Currently *asserted, not
  demonstrated* — see §7.
- **Datum is the survivor**, confirmed with the organisers. Kits are scored from
  the person, so a drop is never better than the tag it aimed at.
- **The organisers supply human-looking dummies.** Train and validate against
  that, not against upright walking adults.

**Camera and geometry, from the sizing model:**

| | value |
|:--|:--|
| HFOV / VFOV | 63.3° / 50.0° |
| Selected search altitude | 60 m AGL *(40 m under review — see below)* |
| GSD at 60 m | 1.82 cm/px → a person ≈ **93 px** long |
| Swath at 60 m | 74 m |
| Planned inference | 2× downsample (3.65 cm GSD, person ≈ 47 px), 12 tiles, 60 inferences/s |

> **Open decision that affects Vision directly.** 40 m AGL is recommended over
> 60 m: it gives **140 px on a person instead of 93**, for 2.5 min of a 15 min
> allowance. It is unresolved pending recall data. If recall at 47 px after
> downsampling is marginal, that is the argument for 40 m — so **measure recall
> as a function of pixels-on-target**, not just a single number.

---

## 6. How we test without an aircraft

Already working and available today:

- **ArduPilot SITL** flying the real coverage plan on three aircraft
  ([`NIDAR-GSC/scripts/sim-flight.sh`](https://github.com/tetraethylmethane/NIDAR-GSC/blob/main/scripts/sim-flight.sh)).
- **Gazebo with a downward camera** producing 640×480 frames from a flying
  aircraft ([`gz-flight.sh`](https://github.com/tetraethylmethane/NIDAR-GSC/blob/main/scripts/gz-flight.sh)).
- **The ground station** rendering all eight rule-8.14 displays, verified in a
  real browser.

So the full chain can be exercised end to end before any hardware exists:

```
Gazebo camera → detector → geotag → publisher → GCS map
```

**Use this for plumbing, not for recall.** See §7.

Geotag geometry additionally gets a stronger test than any simulator: Gazebo
knows the true position of every object, so a geotag can be scored against
ground truth to centimetres, automatically, in CI.

---

## 7. The one thing not to get wrong

**Do not measure recall on synthetic imagery.**

Synthetic humanoids on a synthetic flood plane will make any detector look far
better than it is. Recall is worth 250 points and is the number most likely to
be believed and least likely to be true. A simulator that inflates it is worse
than no simulator, because it removes the pressure to collect real data.

Recall must be measured on **real flood imagery and real human-shaped dummies,
at the altitude actually flown, through the actual downsampling and tiling
path**, and reported as a function of pixels-on-target so the altitude decision
in §5 can be made on evidence.

Monsoon closes flying until late September. That time is for datasets and
throughput on the SBC — the parts with irreducible calendar cost.

---

## 8. Sequence

| Step | Owner | Blocking? |
|:--|:--|:--|
| 1. Agree §3, or replace it with Vision's existing format | Both | **Yes — everything else waits** |
| 2. Geotag geometry + unit tests | Platform | No |
| 3. Detector emitting `Detection` on recorded frames | Vision | No |
| 4. Geotag scored against Gazebo ground truth in CI | Platform | Needs 2 |
| 5. Fusion + confirmation + publisher wiring | Platform | Needs 2 |
| 6. End-to-end on Gazebo frames | Both | Needs 3, 5 |
| 7. Recall on real imagery, vs pixels-on-target | Vision | Needs real data |
| 8. Boresight + lever-arm calibration (SYS-48) | Platform | Needs hardware |
| 9. Geotag vs surveyed ground truth (SYS-12 verification) | Both | P7, needs hardware |

**Step 1 is the only one that blocks anything, and it is a conversation, not
code.** If Vision already has an output format, Platform will build to it —
there is nothing sacred about §3 beyond the three details called out under it,
which are not preferences but error-budget consequences.

---

## 9. Where the numbers here come from

Everything quoted is generated, not asserted, and CI re-checks it on every push:

- [`docs/sizing/delivery-accuracy-output.txt`](sizing/delivery-accuracy-output.txt) — the A/B/C table
- [`docs/sizing/model-output.txt`](sizing/model-output.txt) — camera, GSD, altitude
- [`docs/requirements/requirements-baseline.md`](requirements/requirements-baseline.md) — SYS-07, 12, 33, 48
- [`docs/requirements/rulebook-compliance.md`](requirements/rulebook-compliance.md) — the scoring

If any document disagrees with the model output, the model wins and the document
gets fixed.
