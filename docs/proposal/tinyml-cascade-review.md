# Review — *TinyML Cascade for Flood-SAR Human Detection*, rev. 2

Reviewer's note against the RescueSwarm sizing model
(`tools/sizing-model/rescueswarm_sizing_model.py`, `camera_optics.py`).
Every figure below is reproducible from that model.

---

## Summary

The architecture is sound and the closing experiment is the right one. Three
things need correcting before the document is used to justify a purchase:

1. The cost and power savings are measured against hardware this programme does
   not buy. Against the actual bill of materials both savings are ~zero.
2. §4 and §10.1 assume different targets. §4's favourable conclusion depends on
   the one §10.1 says is wrong.
3. Stage 1's input resolution is never stated, and at the resolution its named
   models actually take, §3's own argument defeats it.

None of these is fatal to the cascade. The cascade has a *better* justification
than the one the document argues — see "The case that does survive".

---

## 1. The cost and power case does not apply to this aircraft

The document benchmarks a **Jetson Orin Nano Super Dev Kit, ~₹45,000, 7 W
continuous** (Table 1). The programme's compute is:

| Item | Cost |
|---|---|
| Raspberry Pi 5, 8 GB | ₹8,000 |
| Pi AI HAT+, 26 TOPS (Hailo-8) | ₹11,000 |
| **Total** | **₹19,000** |

So "₹45,000 → ₹18,000, ~60% saving" is in practice ₹19,000 → ₹18,000. The
cascade also *adds* a second computer to the airframe, with its own mass,
wiring, boot path and failure mode, which the ₹18,000 does not price.

The power case is weaker still. From the sizing model:

| Quantity | Value |
|---|---|
| Hover electrical power | 913 W |
| Mission duration | 7.6 min |
| Pack energy | 292 Wh |
| 7 W accelerator, share of hover power | **0.77 %** |
| 7 W accelerator, energy over the mission | **0.89 Wh** |
| — as a share of the pack | **0.30 %** |
| Saving from the full cascade (7 W → 0.6 W) | **0.81 Wh = 0.28 % of pack** |

The document's premise — "battery-limited flight forces duty-cycling" (Table 1)
— does not hold here. Propulsion dominates by two orders of magnitude. The
accelerator can run continuously for the whole mission on a third of one per
cent of the pack, so there is no duty cycle to remove. **91 % is correct as a
ratio and immaterial as an outcome.**

This is not a criticism of the analysis, which is careful. It is a criticism of
the baseline: a 7 W part on a 913 W aircraft is not a power problem.

## 2. §4 and §10.1 assume different targets

§4 sizes on a **supine adult, 1.7 × 0.5 m**, obtains 1,990 px² at 40 m after 2×
downsample, and concludes the target clears COCO's 1,024 px² small-object
threshold — "materially favourable". It calls the 642 px² figure "the earlier,
incorrect calculation".

§10.1 of the same document states: *"Partial submersion presents an aspect
ratio (head-and-shoulders only)."*

Both cannot hold, and §10.1 is the correct one for this mission. A person in
floodwater presents head and shoulders, roughly 0.4 m across. At 40 m, GSD
1.03 cm/px:

| Target | Native | After 2× |
|---|---|---|
| Supine adult, 1.7 m (§4) | 164.5 px | 82.3 px |
| Person in water, 0.4 m | 38.7 px | **19.4 px** |

At 19 px the target is well below COCO small and §4's conclusion inverts. The
supine-adult assumption overstates the apparent area by about fourfold, which
is why the RescueSwarm proposal moved off it.

**Action:** re-derive §4, Table 3, Table 4 and §5.3 on the 0.4 m target. The
12-looks arithmetic is unaffected — it depends on footprint and ground speed,
not target size — so §4.2's recommendation survives unchanged.

## 3. Stage 1's input resolution is unstated, and the physics matters

§3 is the strongest section: downsampling destroys the target before inference,
so a smaller model makes the problem worse. Correct, and well argued.

§5.2 then specifies Stage 1 as an *"int8-quantized binary classifier
(MCUNetV2-class or MobileNetV2-0.35) on an ESP32-S3"* deciding *"whether a tile
plausibly contains a human"*.

Those models take **96×96 or 160×160**. A 640 px tile at 96×96 is downsampled
6.7×. The §4 target lands at ~12 px; the correct 0.4 m target lands **under
3 px**. §3's argument applies with full force to §5's own gate, and the document
does not notice because it never states the Stage-1 input size.

There is a formulation that survives, and it is worth stating explicitly
because it changes what the gate is:

> A gate does not need to detect a person. It needs to answer *"is this tile
> homogeneous open water?"* — a texture question, which survives downsampling
> where person-detection does not.

That gate is defensible at 96×96. The one described in §5.2 is not.

**Action:** state the Stage-1 input resolution, and reframe the gate as a
water/not-water discriminator rather than a person-plausibility classifier. The
§9 experiment then measures the right thing: recall of *tiles containing a
person*, not recall of persons.

## 4. The tile count changes silently between sections

Three different values appear:

| Source | Tiles/frame | Implies |
|---|---|---|
| §4.2, from 36.7 inf/s ÷ 3.06 Hz | 12 | 2× downsampled frame |
| Figure 2 | 35 | — |
| RescueSwarm design | **48** | native 4056×3040, 640 px tiles, 20 % overlap |

The 12-tile figure is a 2×-downsampled frame, which contradicts §3. Native
tiling at 640/512 stride gives 8 × 6 = 48.

## 5. Smaller corrections

- **Table 2 vs Table 3.** Table 2's "~64 × 50 px raw" describes a ~0.5 × 0.39 m
  object; Table 3 gives 219 px long axis at 30 m. Different targets, same
  document.
- **§3.1** prints the pixel pitch as `1.55×10⁻⁸ m`; should be `10⁻⁶`. The
  result is right, so this is a typesetting slip.
- **References.** "Ultralytics Docs — *YOLO26* RKNN Export" names a model that
  does not exist; and TinyissimoYOLO as `arXiv:2306.00001` is implausible —
  that ID is the first submission of June 2023. SAHI (2202.06934), MCUNetV2
  (2110.15352) and SeaDronesSee (2105.01922) all verify.

## 6. The case that does survive

Drop cost and power as the argument. The cascade earns its place on
**throughput**, which the document does not claim:

Temporal confirmation needs 12 looks per target. At 40 m and 8 m/s the
along-track footprint is 31.4 m, so the required capture rate is

    r = n·v / D = 12 × 8 / 31.4 = 3.06 Hz

At native tiling that is **48 × 3.06 = 147 inferences/s**, against 130–160 FPS
measured for the accelerator — at or past the limit. A gate that discards the
~87 % of tiles that are open water reduces this to roughly 22
inference-equivalents, because a 96×96 gate costs ~45× fewer pixels than a
640×640 detector pass.

**That is the real argument: the gate is what makes 3 Hz affordable, and 3 Hz
is what closes the 12-looks shortfall.** It is a throughput case, not an energy
case, and it does not depend on any claim about watts or rupees.

It also relocates the gate. If the justification is throughput rather than
power, the gate belongs on the accelerator already in the aircraft, not on a
separate microcontroller — it costs about 3 of 130 available
inference-equivalents there, and adds no part.

## 7. What to keep unchanged

- §3, the resolution argument — the best section in the document.
- §4.2's recommendation (hold 40 m / 8 m/s, raise capture rate to ~3.1 Hz). It
  matches the sizing model exactly: 7.9 looks at 2 Hz, 3.06 Hz required.
- §7.2's gap statement. "No published result measures Stage-1 gate recall at
  80–165 px crops in turbid inland flood water" is narrow, specific and
  falsifiable — the right form for a novelty claim.
- §9's experiment, unchanged in method. Measuring a recall-vs-pixel-size curve
  on SeaDronesSee + TinyPerson crops is the correct next step and needs no new
  algorithm or collection.
- §10.1 on thermal — wet skin equilibrating toward water temperature closes
  that option, and the NIR/red-edge recommendation at 717–842 nm is the right
  replacement.
- §10.4 — recall at a fixed false-positive rate per km² is the operationally
  meaningful metric, and mAP is not.
