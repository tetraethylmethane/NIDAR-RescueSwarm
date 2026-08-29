#!/usr/bin/env python3
"""What the gate has to achieve to be worth having, and what it costs if it misses.

WHY THIS EXISTS. "Use a cheap model to skip empty tiles" sounds obviously good
and is not obviously good. It is worth having only if the rejection rate clears
a threshold set by the ratio of gate cost to detector cost, and it is SAFE only
if the recall it gives up is smaller than the recall the extra resolution buys
back. Both are arithmetic, and both should be settled before anyone downloads
13 GB.

THE TRADE, STATED ONCE. Our current pipeline downsamples 2x and tiles to 12
crops, which puts the target at ~19 px -- TinyPerson's `tiny3` band, the hardest
one the literature reports. Tiling natively puts it at ~39 px, outside that band
entirely, but costs 48 crops instead of 12. The cascade is the proposal that we
pay for native resolution by not running the detector on empty water.

So the question is not "does the gate save compute". It is:

    can the gate reject enough tiles that NATIVE tiling costs no more than
    what we already spend on DOWNSAMPLED tiling?

That is one number, and `break_even_rejection` computes it.

THE PART THAT IS EASY TO GET WRONG. Multi-frame fusion makes a detector's
per-look recall look much better than it is, because twelve independent looks
at p = 0.5 give 1 - 0.5^12 = 99.98 %. Gate failures are NOT independent. A
survivor whose appearance the gate reads as water reads as water in every frame
of the pass. `per_target_recall` models both, and the gap between them is the
risk this whole idea carries.

Pure arithmetic. No data, no model, no torch.
"""
from __future__ import annotations

from dataclasses import dataclass

# Forward-pass cost, GFLOP. Order-of-magnitude figures for the model classes,
# used to set a threshold rather than to predict a runtime -- the experiment
# measures the real thing.
YOLO_N_640 = 8.7          # YOLOv8n at 640x640
GATE_COST = {             # candidate gates, by input resolution
    160: 0.03,            # MCUNetV2-class person detector
    320: 0.12,            # MobileNetV3-small class
    640: 0.48,            # same backbone at full tile resolution
}


@dataclass(frozen=True)
class Pipeline:
    """One way of getting from a frame to detections."""
    name: str
    n_tiles: int
    target_px: float
    gate_input: int | None = None      # None = no cascade

    def cost_gflop(self, rejection: float = 0.0) -> float:
        if self.gate_input is None:
            return self.n_tiles * YOLO_N_640
        gate = self.n_tiles * GATE_COST[self.gate_input]
        detector = self.n_tiles * (1.0 - rejection) * YOLO_N_640
        return gate + detector


def break_even_rejection(baseline: Pipeline, cascade: Pipeline) -> float:
    """Rejection rate at which `cascade` costs the same as `baseline`.

    Returns a fraction in [0, 1], or >1 if no rejection rate can pay for it --
    which happens when the gate alone already costs more than the baseline.
    """
    budget = baseline.cost_gflop()
    gate = cascade.n_tiles * GATE_COST[cascade.gate_input]
    detector_full = cascade.n_tiles * YOLO_N_640
    if detector_full <= 0:
        return 0.0
    return 1.0 - (budget - gate) / detector_full


def per_target_recall(per_look: float, n_looks: int,
                      correlation: float = 0.0) -> float:
    """Probability a target is caught at least once across a pass.

    `correlation` interpolates between the two regimes that matter:

      0.0  every look is an independent draw. Fusion is enormously forgiving.
      1.0  the outcome is decided by the target's appearance, so all looks
           agree. Fusion buys nothing and per-target recall IS per-look recall.

    Reality sits between, and where it sits is an empirical question about the
    failure mode -- which is precisely what the experiment has to measure. It is
    not safe to assume 0.
    """
    if not 0.0 <= correlation <= 1.0:
        raise ValueError("correlation must be in [0, 1]")
    independent = 1.0 - (1.0 - per_look) ** n_looks
    return correlation * per_look + (1.0 - correlation) * independent


def required_per_look(target_recall: float, n_looks: int,
                      correlation: float) -> float:
    """Per-look recall needed to hit a per-target recall requirement.

    Bisection rather than algebra because the mixture above has no tidy inverse.
    """
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if per_target_recall(mid, n_looks, correlation) < target_recall:
            lo = mid
        else:
            hi = mid
    return hi


def verdict(rejection: float, gate_recall: float, baseline: Pipeline,
            cascade: Pipeline, n_looks: int = 12,
            sys07_recall: float = 0.90) -> dict:
    """Does a measured (rejection, gate_recall) pair justify adopting this?

    Two independent tests, and BOTH must pass:
      cost -- the cascade must not cost more than what we already spend
      recall -- per-target recall must clear SYS-07 even if gate failures are
                fully correlated, because that is the case we cannot detect
                from the air and cannot recover afterwards
    """
    be = break_even_rejection(baseline, cascade)
    cost_ok = rejection >= be
    worst = per_target_recall(gate_recall, n_looks, correlation=1.0)
    best = per_target_recall(gate_recall, n_looks, correlation=0.0)
    return {
        "break_even_rejection": be,
        "measured_rejection": rejection,
        "cost_ok": cost_ok,
        "cascade_gflop": cascade.cost_gflop(rejection),
        "baseline_gflop": baseline.cost_gflop(),
        "per_target_recall_worst_case": worst,
        "per_target_recall_if_independent": best,
        "recall_ok": worst >= sys07_recall,
        "adopt": bool(cost_ok and worst >= sys07_recall),
        "target_px_gain": cascade.target_px / baseline.target_px,
    }


# --------------------------------------------------------------- our numbers
DOWNSAMPLED = Pipeline("2x downsample, 12 tiles", n_tiles=12, target_px=19.4)
NATIVE = Pipeline("native, 48 tiles", n_tiles=48, target_px=38.7)


def cascade_at(gate_input: int) -> Pipeline:
    return Pipeline(f"native + gate@{gate_input}", n_tiles=48,
                    target_px=38.7, gate_input=gate_input)


def main() -> None:
    print("=" * 78)
    print("CASCADE ECONOMICS  --  what the experiment has to show")
    print("=" * 78)
    print(f"  baseline: {DOWNSAMPLED.name:28} "
          f"{DOWNSAMPLED.cost_gflop():7.1f} GFLOP/frame, target {DOWNSAMPLED.target_px:.0f} px")
    print(f"  native, no cascade:{'':17} {NATIVE.cost_gflop():7.1f} GFLOP/frame, "
          f"target {NATIVE.target_px:.0f} px  ({NATIVE.cost_gflop()/DOWNSAMPLED.cost_gflop():.1f}x too expensive)")
    print()
    print("  REJECTION RATE NEEDED to buy native resolution at today's cost:")
    for g in (160, 320, 640):
        be = break_even_rejection(DOWNSAMPLED, cascade_at(g))
        feasible = "" if be < 1.0 else "   <- gate alone exceeds the budget"
        print(f"    gate @{g:>3} px input ({GATE_COST[g]:.2f} GFLOP/tile):  "
              f"{be:6.1%}{feasible}")

    print()
    print("  PER-TARGET RECALL from per-look recall, 12 looks:")
    print(f"    {'per-look':>9}{'independent':>14}{'correlated':>13}")
    for p in (0.50, 0.70, 0.80, 0.90, 0.95, 0.99):
        print(f"    {p:>9.0%}{per_target_recall(p, 12, 0.0):>14.1%}"
              f"{per_target_recall(p, 12, 1.0):>13.1%}")
    print()
    print("    Independence is what makes a mediocre gate look excellent, and")
    print("    it is exactly what a systematic appearance failure destroys.")
    print(f"    Per-look recall needed for SYS-07's 90 %, if fully correlated: "
          f"{required_per_look(0.90, 12, 1.0):.1%}")

    print()
    print("=" * 78)
    print("DECISION RULE  --  fix this before looking at any result")
    print("=" * 78)
    print("  ADOPT the cascade only if BOTH hold on held-out data:")
    print(f"    1. tile rejection  >= {break_even_rejection(DOWNSAMPLED, cascade_at(320)):.1%}"
          "   (gate @320, else it costs more than it saves)")
    print("    2. per-target recall >= 90 % ASSUMING FULLY CORRELATED gate")
    print("       failures -- the case we cannot see from the air.")
    print("  Report per-TARGET recall, not per-tile. A tile is not a survivor.")


if __name__ == "__main__":
    main()
