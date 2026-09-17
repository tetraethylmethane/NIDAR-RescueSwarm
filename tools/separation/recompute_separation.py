#!/usr/bin/env python3
"""Recompute the separation results from the committed SITL telemetry.

WHY THIS EXISTS
---------------
Three separation numbers used to live in HANDOFF.md as prose, and two of them
did not reproduce. They were marked "definition-sensitive and left alone",
which is an honest thing to say about a number and a bad place to leave it: a
disagreement between a document and a recording that nobody can settle without
re-deriving the definition from scratch.

The definitions are therefore HERE, in code, applied to the committed
recordings, with the output compared byte for byte by CI. If the definition is
wrong, change it here and the documents follow. If a recording is replaced, the
numbers move and CI says so.

The phases, stated exactly:

  launch    every airborne pair, from the start of the recording until the last
            aircraft first reaches the search deck. This is the departure
            fan-out that NAV_DELAY is there to create.

  en route  every airborne pair, excluding any sample where EITHER aircraft is
            within PAD_RADIUS_M of the pad. The exclusion is the whole reason
            the en-route figure was ambiguous: three aircraft parked 1.22 m
            apart are 1.22 m apart by design, and counting the pad as a
            conflict drowns the part of the flight where separation is earned.

  recovery  every airborne pair while EITHER aircraft is within PAD_RADIUS_M
            of the pad and above the ground. This is the stacked descent, and
            it is the tightest phase of the flight.

Separation is 3-D slant range. An aircraft below GROUND_ALT_M is on the ground
and is not counted: two landed aircraft are a parking problem, not a
separation one.

Run:  python tools/separation/recompute_separation.py
"""
from __future__ import annotations

import itertools
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
RECORDINGS = os.path.join(ROOT, "simulations", "recordings")

# A sample below this is on the ground, not flying.
GROUND_ALT_M = 1.0
# The pad neighbourhood. 60 m is the radius HANDOFF.md's en-route figure used;
# it is stated here rather than implied so the two figures cannot diverge again.
PAD_RADIUS_M = 60.0
# The minimum the flight is required to hold between airborne aircraft.
MIN_SEPARATION_M = 5.0

FILES = [
    ("mission-telemetry.json",
     "SIM_SPEEDUP 3, RTL_LOIT_TIME 0/20/40 s -- SUPERSEDED, see below"),
    ("mission-telemetry-speedup1.json",
     "SIM_SPEEDUP 1, RTL_LOIT_TIME 0/60/120 s -- current configuration"),
]


def load(name):
    with open(os.path.join(RECORDINGS, name), encoding="utf-8") as fh:
        return json.load(fh)


def sample_grid(tracks):
    """Pair up the aircraft SAMPLE BY INDEX, not by timestamp.

    The recorder writes one row per aircraft per poll, so index k is the same
    poll for all three and the tracks are equal length with identical `t`
    arrays. That is asserted below rather than assumed.

    Index alignment is not a convenience here, it is the only correct choice:
    the timestamps in these recordings are NOT monotonic. The speedup-1
    recording steps BACKWARDS 17 times, worst -2.14 s. Nearest-timestamp
    matching against a clock that repeats values silently pairs samples from
    completely different parts of the flight -- the first version of this
    script did exactly that and reported a 27 m minimum where the true figure
    is 5.34 m. The clock is a label on the samples; the index is the sample.
    """
    keys = sorted(tracks)
    lengths = {k: len(tracks[k]) for k in keys}
    if len(set(lengths.values())) != 1:
        raise SystemExit(f"tracks are not the same length: {lengths} -- "
                         "index alignment is not valid for this recording")
    arrays = [tuple(s["t"] for s in tracks[k]) for k in keys]
    if len(set(arrays)) != 1:
        raise SystemExit("tracks do not share a timestamp sequence -- "
                         "index alignment is not valid for this recording")
    ts = arrays[0]
    return [(ts[i], {k: tracks[k][i] for k in keys}) for i in range(len(ts))]


def clock_report(rec):
    """Both directions of clock defect, because only one was ever checked.

    verify_flight.py tests `gap > MAX_CLOCK_GAP_S`, which is forward-only. A
    clock that runs backwards produces a negative gap, never exceeds the
    threshold, and passes. The speedup-3 recording fails the forward test with
    a 453.93 s jump; the speedup-1 recording passes it and steps backwards 17
    times. Both are reported here so neither can be described as clean.
    """
    ts = [s["t"] for s in next(iter(rec["tracks"].values()))]
    gaps = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]
    back = [g for g in gaps if g < 0]
    return max(gaps), len(back), (min(back) if back else 0.0)


def search_deck_reached(grid, search_alt):
    """INDEX by which every aircraft has first reached the search deck.

    An index, not a timestamp, for the same reason sample_grid aligns on one:
    a non-monotonic clock makes "before time T" an unreliable phase boundary.
    """
    first = {}
    for i, (_, row) in enumerate(grid):
        for k, sm in row.items():
            if k not in first and sm["alt"] >= search_alt * 0.95:
                first[k] = i
    if len(first) < len(grid[0][1]):
        return None
    return max(first.values())


def pad_centre(rec):
    """`pad_xy` is the three SLOT positions, not a centre. Use their centroid.

    Reading it as a point is the first thing this script got wrong, which is a
    small illustration of why the definition belongs in code: the same mistake
    made by hand produces a number, not an exception.
    """
    slots = rec["pad_xy"]
    return (sum(sl[0] for sl in slots) / len(slots),
            sum(sl[1] for sl in slots) / len(slots))


def phase_minima(rec):
    tracks = rec["tracks"]
    pad = pad_centre(rec)
    grid = sample_grid(tracks)
    launch_ends = search_deck_reached(grid, rec["search_alt"])

    best = {"launch": None, "en route": None, "recovery": None,
            "whole flight": None}

    def keep(phase, dist, t, a, b):
        cur = best[phase]
        if cur is None or dist < cur[0]:
            best[phase] = (dist, t, a, b)

    for i, (t, row) in enumerate(grid):
        for a, b in itertools.combinations(sorted(row), 2):
            pa, pb = row[a], row[b]
            if pa["alt"] < GROUND_ALT_M or pb["alt"] < GROUND_ALT_M:
                continue
            dist = math.dist((pa["x"], pa["y"], pa["alt"]),
                             (pb["x"], pb["y"], pb["alt"]))
            near = (math.dist((pa["x"], pa["y"]), pad) < PAD_RADIUS_M or
                    math.dist((pb["x"], pb["y"]), pad) < PAD_RADIUS_M)
            keep("whole flight", dist, t, a, b)
            if launch_ends is not None and i <= launch_ends:
                keep("launch", dist, t, a, b)
            if near:
                keep("recovery", dist, t, a, b)
            else:
                keep("en route", dist, t, a, b)
    return best, launch_ends, grid


def main():
    print("SEPARATION, RECOMPUTED FROM THE COMMITTED TELEMETRY")
    print("=" * 70)
    print(f"ground threshold   {GROUND_ALT_M:.1f} m   "
          f"pad radius {PAD_RADIUS_M:.0f} m   "
          f"minimum {MIN_SEPARATION_M:.1f} m")
    print()

    failures = []
    for name, note in FILES:
        rec = load(name)
        best, launch_ends, grid = phase_minima(rec)
        superseded = "SUPERSEDED" in note
        fwd, n_back, worst_back = clock_report(rec)

        print(f"{name}")
        print(f"  {note}")
        print(f"  speedup {rec['speedup']:g}   {len(grid)} samples/aircraft   "
              f"search deck {rec['search_alt']:g} m")
        if launch_ends is not None:
            print(f"  launch phase ends at sample {launch_ends} "
                  f"(last aircraft reaches the deck)")
        print(f"  clock: max forward gap {fwd:.2f} s, "
              f"{n_back} backward step(s), worst {worst_back:.2f} s")
        print()
        for phase in ("launch", "en route", "recovery", "whole flight"):
            got = best[phase]
            if got is None:
                print(f"    {phase:<14}      no airborne pair in this phase")
                continue
            dist, t, a, b = got
            flag = "" if dist >= MIN_SEPARATION_M else "   << UNDER MINIMUM"
            print(f"    {phase:<14} {dist:8.2f} m   at t = {t:7.1f} s   "
                  f"drones {a}-{b}{flag}")
            if dist < MIN_SEPARATION_M and not superseded:
                failures.append((name, phase, dist))
        print()

    print("=" * 70)
    if failures:
        for name, phase, dist in failures:
            print(f"FAIL  {name}: {phase} closes to {dist:.2f} m, "
                  f"under the {MIN_SEPARATION_M:.1f} m minimum")
        raise SystemExit(1)
    print("All current recordings hold the minimum between airborne aircraft.")
    print()
    print("The superseded recording is kept and reported, not deleted: it is")
    print("the evidence that the 0/20/40 s stagger was not sufficient, and the")
    print("figures in simulations/recordings/ are still rendered from it.")
    print()
    print("NEITHER recording has a clean clock. The speedup-3 one jumps 453.93 s")
    print("forward once; the speedup-1 one steps backwards 17 times. Separation")
    print("is computed by SAMPLE INDEX and is unaffected, but every t= above is")
    print("a label from that clock and should not be quoted as a mission time.")


if __name__ == "__main__":
    main()
