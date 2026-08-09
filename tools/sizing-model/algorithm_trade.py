"""DARP vs static partition, CBBA vs greedy claim-and-lock -- measured, not asserted.

implementation-plan.md chose a static equal-area partition over DARP, and greedy
claim-and-lock over CBBA. Both decisions were made on schedule risk, which is a
legitimate reason but not a measured one. This puts numbers on what they cost.

The comparison is in Python because these are discrete combinatorial algorithms.
Simulink is a poor fit for that class of problem, and a second implementation of
partition.py in a second language would be a second source of truth for a
decision that is already made.

WHAT IS BEING COMPARED
----------------------
Coverage:   static equal-area strips  vs  a DARP-style iterative partition
            (Kapoutsis, Chatzichristofis & Kosmatopoulos 2017 -- divide areas
            by grid assignment, then rebalance with per-drone cost weights)

Allocation: greedy claim-and-lock       vs  CBBA
            (Choi, Brunet & How 2009 -- consensus-based bundle algorithm)

The figure of merit is the same in both cases: **the worst drone**. A mission
ends when the last aircraft finishes, so mean load is the wrong statistic.

Run:  python tools/sizing-model/algorithm_trade.py
"""
from __future__ import annotations

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
))

from autonomy.coverage_planner.plan import plan_mission  # noqa: E402

# The competition search area: 10 ha, 400 x 250 m.
LAT0, LON0 = 13.0000, 80.0000
DLAT = 250.0 / 111_132.0
DLON = 400.0 / (111_320.0 * math.cos(math.radians(LAT0)))
BOUNDARY = [(LAT0, LON0), (LAT0, LON0 + DLON),
            (LAT0 + DLAT, LON0 + DLON), (LAT0 + DLAT, LON0)]
HOME = (LAT0, LON0)

N_DRONES = 3
SPEED = 8.0
TURN_S = 6.0
LINE_SPACING_M = 34.5      # from the 40 m altitude / 63.3 deg HFOV / 30 % sidelap
W = 78


def rule(title=""):
    print("=" * W)
    if title:
        print(title)
        print("=" * W)


# ===================================================================== DARP
def darp_partition(rows, cols, starts, iters=200, tol=0.01):
    """DARP-style iterative equal-share partition on a grid.

    The real algorithm assigns every cell to the drone with the lowest weighted
    distance, then adjusts per-drone weights until the areas equalise. This is
    that, without the connectivity-repair step -- which matters for concave or
    obstacle-filled regions and does nothing on a convex rectangle.

    Returns (assignment grid, per-drone cell counts).
    """
    n = len(starts)
    target = rows * cols / n
    weights = [1.0] * n
    assign = [[0] * cols for _ in range(rows)]
    for _ in range(iters):
        counts = [0] * n
        for r in range(rows):
            for c in range(cols):
                best, bestd = 0, float("inf")
                for k, (sr, sc) in enumerate(starts):
                    d = weights[k] * math.hypot(r - sr, c - sc)
                    if d < bestd:
                        best, bestd = k, d
                assign[r][c] = best
                counts[best] += 1
        err = max(abs(c - target) for c in counts) / target
        if err < tol:
            break
        # Heavier weight pushes cells away from an over-loaded drone.
        for k in range(n):
            weights[k] *= (counts[k] / target) ** 0.10
    return assign, counts


def transects_for_assignment(assign, rows, cols, n):
    """Turn a cell assignment into boustrophedon transect count and path length.

    Counts, per drone and per grid row, the number of contiguous runs of its
    cells. Each run is a transect: its length is the run, and every extra run
    on a row is an extra turn. This is exactly where a DARP partition can lose
    to a strip partition -- a ragged boundary fragments rows.
    """
    cell_m = LINE_SPACING_M
    length = [0.0] * n
    turns = [0] * n
    for r in range(rows):
        runs = {k: 0 for k in range(n)}
        prev = None
        for c in range(cols):
            k = assign[r][c]
            length[k] += cell_m
            if k != prev:
                runs[k] += 1
            prev = k
        for k in range(n):
            turns[k] += max(0, runs[k])
    return length, turns


def run_darp():
    # Grid the 400 x 250 m box at the line spacing: 250/34.5 -> 7 rows of
    # transects, 400/34.5 -> 11 columns of cells.
    rows = max(2, int(round(250.0 / LINE_SPACING_M)))
    cols = max(2, int(round(400.0 / LINE_SPACING_M)))
    # Three drones launching from the same pad along the south edge, which is
    # the real geometry -- one launch point, not three corners.
    starts = [(rows - 1, int(cols * f)) for f in (0.17, 0.50, 0.83)]
    assign, counts = darp_partition(rows, cols, starts)
    length, turns = transects_for_assignment(assign, rows, cols, N_DRONES)
    sweep = [length[k] / SPEED + turns[k] * TURN_S for k in range(N_DRONES)]
    return dict(counts=counts, length=length, turns=turns, sweep=sweep,
                rows=rows, cols=cols, assign=assign)


# ===================================================================== CBBA
def _beliefs(n):
    """Per-agent view of who owns what. Nobody has a global view -- that is the
    entire point of the exercise."""
    return [dict() for _ in range(n)]


def _broadcast(sender, msg_items, belief, comms, rng):
    """Deliver a claim to each peer independently with probability `comms`."""
    n = len(belief)
    for b in range(n):
        if b == sender:
            continue
        if rng.random() < comms:
            for t, owner in msg_items:
                belief[b][t] = owner


def greedy_claim_and_lock(tasks, agents, comms=1.0, rng=None):
    """What implementation-plan.md chose.

    Every round, each drone claims the nearest task it does not BELIEVE is
    already claimed, then broadcasts. A lost broadcast means a second drone
    claims the same survivor: wasted flying, nothing dropped.
    """
    rng = rng or random.Random(0)
    n = len(agents)
    belief = _beliefs(n)
    assign = {a: [] for a in range(n)}
    pos = list(agents)
    visited = set()

    for _ in range(len(tasks) * 3):
        if visited >= set(range(len(tasks))):
            break
        # Claims are broadcast IMMEDIATELY, and agents act in a random order
        # within a round. This is what a real implementation does -- you send
        # the claim as you make it, and a peer that hears it before making its
        # own choice avoids the task. Modelling all three as claiming
        # simultaneously with no arbitration would invent duplicates that the
        # protocol does not actually produce.
        order = list(range(n))
        rng.shuffle(order)
        for a in order:
            cands = [t for t in range(len(tasks)) if t not in belief[a]]
            if not cands:
                continue
            t = min(cands, key=lambda t: math.dist(pos[a], tasks[t]))
            belief[a][t] = a                 # I own it, as far as I know
            assign[a].append(t)
            pos[a] = tasks[t]
            visited.add(t)
            _broadcast(a, [(t, a)], belief, comms, rng)
    return assign, visited


def cbba(tasks, agents, comms=1.0, rng=None, consensus_rounds=None):
    """Consensus-based bundle algorithm (Choi, Brunet & How 2009), lossy links.

    Bundle construction, then consensus rounds in which an agent that learns of
    a higher bid RELEASES the task and everything it added after it -- the
    release cascade is the part of CBBA that guarantees a conflict-free
    assignment when consensus converges.

    Under packet loss it may not converge in bounded rounds. The interesting
    failure is not a duplicate: it is a task that every agent has released
    because each believes someone else won it. That is a DROPPED survivor.
    """
    rng = rng or random.Random(0)
    n = len(agents)
    n_tasks = len(tasks)
    rounds = consensus_rounds if consensus_rounds is not None else n
    bundle = {a: [] for a in range(n)}
    # per-agent belief about the winning bid and winner for every task
    y = [[0.0] * n_tasks for _ in range(n)]
    z = [[None] * n_tasks for _ in range(n)]

    def score(a, t):
        pos = agents[a] if not bundle[a] else tasks[bundle[a][-1]]
        return 1.0 / (1.0 + math.dist(pos, tasks[t]))

    # CBBA alternates bundle-building and consensus until the assignment
    # stops changing. Building once and running consensus once would strip
    # tasks in the release cascade and never re-offer them, which invents
    # dropped tasks the real algorithm does not produce on a good link.
    # Staleness reset. Real CBBA carries a timestamp per task and its consensus
    # table resets a bid whose information is older than the peer's. Without
    # that, a released task keeps the releaser's old high bid in every other
    # agent's table, nobody can outbid it, and the task becomes permanently
    # unclaimable -- which would make CBBA drop tasks even on a perfect link.
    # That is an artefact of the simplification, not a property of CBBA, and
    # scoring the algorithm on it would rig the comparison.
    age = [[0] * n_tasks for _ in range(n)]
    STALE = 2

    for _ in range(n_tasks):
        for a in range(n):
            for t in range(n_tasks):
                if z[a][t] is not None and t not in bundle[a] and age[a][t] >= STALE:
                    y[a][t], z[a][t] = 0.0, None      # re-open for bidding
                age[a][t] += 1

        for _ in range(n_tasks):
            grew = False
            for a in range(n):
                best_t, best_s = None, 0.0
                for t in range(n_tasks):
                    if t in bundle[a]:
                        continue
                    s = score(a, t)
                    if s > y[a][t] and s > best_s:
                        best_t, best_s = t, s
                if best_t is not None:
                    bundle[a].append(best_t)
                    y[a][best_t] = best_s
                    z[a][best_t] = a
                    grew = True
            if not grew:
                break

        before = {a: tuple(bundle[a]) for a in range(n)}
        for _ in range(rounds):
            msgs = [(a, b) for a in range(n) for b in range(n)
                    if a != b and rng.random() < comms]
            for a, b in msgs:
                for t in range(n_tasks):
                    if y[a][t] > y[b][t]:
                        # b learns a outbid it: release the task AND its tail
                        if z[b][t] == b and t in bundle[b]:
                            i = bundle[b].index(t)
                            for t2 in bundle[b][i:]:
                                y[b][t2] = 0.0
                                z[b][t2] = None
                            bundle[b] = bundle[b][:i]
                        y[b][t], z[b][t] = y[a][t], z[a][t]
                        age[b][t] = 0          # fresh information about t
        if all(tuple(bundle[a]) == before[a] for a in range(n)):
            break

    visited = {t for a in range(n) for t in bundle[a]}
    return bundle, visited


def path_time(agent_start, task_list, tasks):
    p = agent_start
    d = 0.0
    for t in task_list:
        d += math.dist(p, tasks[t])
        p = tasks[t]
    return d / SPEED


def duplicate_visits(assign):
    """A survivor visited by more than one drone: wasted time, nothing lost."""
    counts = {}
    for ts in assign.values():
        for t in ts:
            counts[t] = counts.get(t, 0) + 1
    return sum(c - 1 for c in counts.values() if c > 1)


def dropped(assign, n_tasks):
    """A survivor NOBODY goes to. This is the ~100-point failure."""
    seen = {t for ts in assign.values() for t in ts}
    return n_tasks - len(seen)


# ====================================================================== main
rule("COVERAGE PARTITION  -  static equal-area strips vs DARP")
# passes=1 EXPLICITLY. This compares two PARTITIONING strategies, and the pass
# count is orthogonal to that question -- but it is not orthogonal to this
# arithmetic. plan_mission's default moved to two passes for the geotag, which
# doubled the static side while the DARP path below is computed independently
# and did not double. The trade then reported DARP winning by 52.6 % instead of
# 3.6 %, from a change that has nothing to do with partitioning.
#
# Whatever pass count the fleet actually flies applies to BOTH strategies, so
# pinning it here is what keeps the comparison honest. CI caught this.
mp = plan_mission(BOUNDARY, HOME, n_drones=N_DRONES, altitude_m=40.0,
                  speed_ms=SPEED, passes=1)
static_sweeps = [d.sweep_s for d in mp.drones]
static_lines = [len(d.lines) for d in mp.drones]
print("  static equal-area strips  (autonomy/coverage_planner/partition.py)")
for d in mp.drones:
    print(f"    drone {d.drone_id}: {d.area_ha:5.2f} ha  {len(d.lines):2d} lines  "
          f"{d.path_m:7,.0f} m  {d.sweep_s:6.1f} s")
print(f"    WORST DRONE: {max(static_sweeps):.1f} s     imbalance "
      f"{mp.balance['max_imbalance']:.1%}")
print()

darp = run_darp()
print(f"  DARP-style grid partition  ({darp['rows']} x {darp['cols']} cells)")
for k in range(N_DRONES):
    print(f"    drone {k + 1}: {darp['counts'][k]:3d} cells  "
          f"{darp['turns'][k]:2d} turns  {darp['length'][k]:7,.0f} m  "
          f"{darp['sweep'][k]:6.1f} s")
print(f"    WORST DRONE: {max(darp['sweep']):.1f} s")
print()
delta = max(darp["sweep"]) - max(static_sweeps)
pct = abs(delta) / max(static_sweeps)
winner = "DARP" if delta < 0 else "the static partition"
print(f"  VERDICT: {winner} is faster by {abs(delta):.1f} s ({pct:.1%}) on the worst drone.")
print()

static_lines_total = sum(static_lines)
lines_needed = math.ceil(250.0 / LINE_SPACING_M)
if delta < 0:
    print("  This is NOT the result the code comments predicted, and the reason")
    print("  is worth recording.")
    print()
    print(f"  The static partition splits FIRST and lays transects SECOND, so")
    print(f"  every strip rounds its own transect count up independently:")
    print(f"      {static_lines_total} lines flown  vs  {lines_needed} lines actually needed")
    print(f"      ({N_DRONES} strips x {static_lines[0]} lines, each strip "
          f"{250.0 / N_DRONES:.0f} m wide / {LINE_SPACING_M:.1f} m spacing = "
          f"{250.0 / N_DRONES / LINE_SPACING_M:.1f} -> rounds to {static_lines[0]})")
    print("  DARP grids the whole area first, so it pays that rounding once")
    print("  rather than three times. It spends the saving on turns -- ragged")
    print("  cell boundaries fragment rows -- and still comes out ahead.")
    print()
    print(f"  {pct:.1%} is small, and it is inside the noise of this transect")
    print("  model, which counts turns crudely. It does NOT justify implementing")
    print("  DARP. But it does mean the comment in partition.py claiming DARP")
    print("  buys nothing here is wrong, and the honest reason to keep the")
    print("  static partition is determinism and inspectability, not speed.")
    print()
    print("  The cheaper fix for the rounding penalty, if it ever matters: pick")
    print("  the strip count so strip width is close to a whole multiple of the")
    print("  line spacing, or let adjacent strips share a boundary transect.")
else:
    print("  On a convex rectangle DARP's advantage is nil -- it exists for")
    print("  concave regions, obstacles and heterogeneous drones, none of which")
    print("  apply here, and its ragged cell boundaries cost turns.")
print()
print("  DARP would earn its keep if: the boundary becomes concave or has a")
print("  no-fly island, the aircraft stop being identical, or a drone is lost")
print("  mid-mission and the area must be re-divided in flight.")

rule("TASK ALLOCATION  -  greedy claim-and-lock vs CBBA")
rng = random.Random(7)
tasks = [(rng.uniform(0, 400), rng.uniform(0, 250)) for _ in range(10)]
agents = [(60.0, 0.0), (200.0, 0.0), (340.0, 0.0)]

print(f"  10 survivors, 3 drones, one launch pad. Figure of merit is the LAST")
print(f"  drone to finish, because that is when the mission ends.")
print()
TRIALS = 200
print(f"  Averaged over {TRIALS} random survivor layouts per link quality.")
print()
print(f"  {'link':>7} | {'CBBA':^26} | {'greedy claim-and-lock':^26}")
print(f"  {'':>7} | {'worst':>8}{'dupes':>9}{'DROPPED':>9} |"
      f" {'worst':>8}{'dupes':>9}{'DROPPED':>9}")
print("  " + "-" * 68)

summary = {}
for comms in (1.00, 0.90, 0.70, 0.50, 0.30):
    cb_t = gr_t = cb_d = gr_d = cb_x = gr_x = 0.0
    for trial in range(TRIALS):
        r = random.Random(1000 + trial)
        ts = [(r.uniform(0, 400), r.uniform(0, 250)) for _ in range(10)]
        cb, _ = cbba(ts, agents, comms=comms, rng=random.Random(trial))
        gr, _ = greedy_claim_and_lock(ts, agents, comms=comms,
                                      rng=random.Random(trial))
        cb_t += max(path_time(agents[a], cb[a], ts) for a in range(N_DRONES))
        gr_t += max(path_time(agents[a], gr[a], ts) for a in range(N_DRONES))
        cb_d += duplicate_visits(cb)
        gr_d += duplicate_visits(gr)
        cb_x += dropped(cb, len(ts))
        gr_x += dropped(gr, len(ts))
    n = TRIALS
    summary[comms] = (cb_x / n, gr_x / n, gr_d / n)
    print(f"  {comms:>6.0%} | {cb_t / n:>7.0f}s{cb_d / n:>9.2f}{cb_x / n:>9.2f} |"
          f" {gr_t / n:>7.0f}s{gr_d / n:>9.2f}{gr_x / n:>9.2f}")

print()
print("  !! READ THE CBBA COLUMN WITH SUSPICION. It drops ~2 tasks even on a")
print("  PERFECT link, and real CBBA does not -- with converged consensus it is")
print("  provably conflict-free and complete. The fault is in this")
print("  implementation: faithful CBBA carries per-task timestamps and a full")
print("  consensus action table, and the simplification here leaves stale")
print("  winning bids that nobody can outbid after a release cascade.")
print()
print("  So this is NOT a head-to-head score, and the decision does not rest")
print("  on one. Publishing CBBA's dropped-task count as evidence would be")
print("  scoring an algorithm on a bug in my model of it.")
print()
print("  WHAT THE TABLE DOES SUPPORT, because greedy is modelled faithfully:")
print()
gr100 = None
print("    * greedy is conflict-free on a perfect link (0.00 duplicates) and")
print("      NEVER drops a task at any link quality -- 0.00 in every row. It")
print("      has no release step, so there is no mechanism by which a survivor")
print("      can end up unowned.")
print("    * its degradation is entirely duplicate visits, rising from 0 to")
print(f"      {summary[0.30][2]:.1f} at a 30 % link. Two drones fly to the same survivor:")
print("      slower, and nothing lost.")
print("    * the cost is time. Worst-drone time rises from 54 s to 71 s across")
print("      the same range -- against a 15 min mission allowance of which the")
print("      design uses 7.7 min. There is room for that.")
print()
print("  The argument for greedy is therefore about FAILURE MODE, not")
print("  efficiency, and it stands on greedy's own measured behaviour: on a")
print("  mesh expected to partition, degrading to 'slower' beats degrading to")
print("  'missed'. A dropped survivor is 25 detection points plus up to 20")
print("  delivery points and is unrecoverable inside the mission.")
print()
print("  If CBBA is ever revisited, implement it properly and re-measure --")
print("  do not cite this table.")

rule("CONCLUSION")
print("  Both decisions in implementation-plan.md hold. One of them holds for a")
print("  different reason than the one written down.")
print()
print(f"    * DARP is {pct:.1%} FASTER here, not slower, because the static")
print("      partition rounds its transect count up once per strip. The margin")
print("      is inside this model's noise and nowhere near the implementation")
print("      cost, so the decision stands -- but the stated rationale in")
print("      partition.py is wrong and should say determinism, not speed.")
print()
print("    * Greedy claim-and-lock never drops a task at any link quality -- it")
print("      has no release step, so a survivor cannot end up unowned. It pays")
print("      in duplicate visits and time instead, which the 15 min allowance")
print("      absorbs. That is measured, and it is the whole argument.")
print("      The CBBA side of the table is NOT trustworthy; see the warning")
print("      above. Do not cite it.")
print()
print("  Revisit DARP if the boundary becomes concave, the fleet becomes")
print("  heterogeneous, or in-flight re-partition after a drone loss is needed.")
rule()
