"""Setup-to-launch budget under the 5-minute rule, with two crew.

Setup is the only constraint in the system with under 20 % margin, and the main
model treats it as a static print block. It now needs to be recomputed, because
the organisers have ruled that the RTK base station may NOT be positioned or
started before the window opens. That pushes base setup and its survey time onto
a budget that had 15 s to spare.

MODEL. Tasks have a duration, prerequisites, and a flag for whether they occupy
a person. Automatic tasks (boots, GNSS convergence, RTK convergence) consume
wall-clock time but no crew, so they can overlap with manual work. Two crew are
available (mission brief section 6). A simple list scheduler assigns each ready
task to the earliest free slot.

THE KEY QUESTION this answers: the rule constrains setup-to-LAUNCH, not
setup-to-RTK-fix. Nothing requires an RTK fix before takeoff -- only before the
first geotag, which happens after climb and transit. Moving RTK convergence off
the pre-launch critical path is worth more than everything the base costs.

Run:  python tools/sizing-model/setup_budget.py
"""
import numpy as np

WINDOW = 300.0      # 5 minutes, mission brief section 3
CREW = 2            # mission brief section 6

# (name, duration s, prerequisites, needs a crew member)
BASE_TASKS = [
    ('unpack+power A1',      20, [],                              True),
    ('unpack+power A2',      20, [],                              True),
    ('unpack+power A3',      20, [],                              True),
    ('FC boot + EKF init',   25, ['unpack+power A3'],             False),
    ('companion boot',       75, ['unpack+power A3'],             False),
    ('mesh association',     20, ['companion boot'],              False),
    ('rover GNSS 3D fix',    45, ['unpack+power A3'],             False),
    ('load magazines x3',    45, [],                              True),
    ('mission file parse',   30, ['mesh association'],            True),
    ('pre-arm + arm',        20, ['mission file parse',
                                  'FC boot + EKF init'],          True),
]

# Base-station variants, appended to the above
BASE_IN_WINDOW = [
    ('position+power base',  30, [],                              True),
    ('base 3D fix',          30, ['position+power base'],         False),
]
SURVEY_IN = ('base survey-in',   90, ['base 3D fix'],   False)
FIXED_POS = ('base fixed-pos',    5, ['base 3D fix'],   False)
RTK_CONV = 60      # rover float -> fix once corrections flow

# --- airframe deployment: the folding-arm question --------------------------
# `unpack+power` above is 20 s and was the ONLY airframe line item, which
# silently assumed the aircraft comes out of its case ready to fly. That is a
# fixed-arm assumption, and it was never stated.
#
# Folding arms have to be unfolded, locked, and the locks VERIFIED -- the last
# of those is not optional on an airframe that will hover over people, and it
# is the part crews rush. This models it as extra crew-consuming work per
# aircraft, which is what it is: crew are the binding resource, not wall clock.
#
# Folding PROPS are already the design (18 in CF folding) and are not modelled
# here: they self-deploy on spin-up and cost seconds, not tens of seconds.
def deploy_task(i: int, seconds: float):
    return (f'deploy+lock arms A{i}', seconds, [f'unpack+power A{i}'], True)


def with_arm_deploy(tasks, seconds: float):
    """Insert per-aircraft arm deployment before pre-arm."""
    if seconds <= 0:
        return tasks
    out = []
    for t in tasks:
        if t[0] == 'pre-arm + arm':
            deps = list(t[2]) + [f'deploy+lock arms A{i}' for i in (1, 2, 3)]
            out.append((t[0], t[1], deps, t[3]))
        else:
            out.append(t)
    return out + [deploy_task(i, seconds) for i in (1, 2, 3)]


def schedule(tasks, crew=CREW):
    """Greedy list scheduler over `crew` interchangeable people."""
    dur = {t[0]: t[1] for t in tasks}
    pre = {t[0]: t[2] for t in tasks}
    man = {t[0]: t[3] for t in tasks}
    finish, start = {}, {}
    free = [0.0] * crew
    pending = [t[0] for t in tasks]
    guard = 0
    while pending and guard < 1000:
        guard += 1
        progressed = False
        for name in list(pending):
            if not all(p in finish for p in pre[name]):
                continue
            ready = max([finish[p] for p in pre[name]] + [0.0])
            if man[name]:
                i = int(np.argmin(free))
                s = max(ready, free[i])
                free[i] = s + dur[name]
            else:
                s = ready
            start[name], finish[name] = s, s + dur[name]
            pending.remove(name)
            progressed = True
        if not progressed:
            raise RuntimeError('dependency cycle: ' + ', '.join(pending))
    return start, finish


def report(label, tasks, rtk_before_launch, note=''):
    start, finish = schedule(tasks)
    launch = finish['pre-arm + arm']

    # RTK convergence needs corrections flowing AND the rover holding a 3D fix
    corr = finish.get('base fixed-pos', finish.get('base survey-in', 0.0))
    rtk_fix = max(corr, finish['rover GNSS 3D fix']) + RTK_CONV
    if rtk_before_launch:
        launch = max(launch, rtk_fix)

    margin = WINDOW - launch
    verdict = 'OK' if margin >= 0 else 'OVER'
    pess = launch + 100          # calibration offset, see warning above
    pv = 'OK' if pess <= WINDOW else 'OVER'
    print(f"\n{label}")
    print(f"  launch at {launch:5.0f} s   margin {margin:+6.0f} s   [{verdict}]"
          f"   |  +100 s calibrated: {pess:.0f} s [{pv}]")
    print(f"  RTK fixed at {rtk_fix:.0f} s "
          f"({'before launch' if rtk_before_launch else 'in flight'})")
    if note:
        print(f"  {note}")
    return launch, margin, rtk_fix


def main():
    print("=" * 78)
    print("SETUP-TO-LAUNCH BUDGET  -  5 min window, 2 crew")
    print("=" * 78)
    print("  Automatic tasks (boots, GNSS, RTK) overlap with manual work.")
    print("  Manual tasks queue on the two crew members.")
    print()
    print("  *** CALIBRATION WARNING ***")
    print("  Case A below is the same scenario the main model calls ~285 s, and")
    print("  this scheduler makes it 185 s. This model is therefore ~100 s")
    print("  OPTIMISTIC: it omits walking between aircraft, per-aircraft checks,")
    print("  fumbling, and any serialisation the main model assumed. TRUST THE")
    print("  DELTAS BETWEEN CASES, NOT THE ABSOLUTE NUMBERS. Add ~100 s to every")
    print("  case for a pessimistic read -- which puts case C over the window.")
    print("  The P1 bench test is what calibrates this.")

    # --- A: the old assumption, now disallowed --------------------------
    report("A  Base pre-surveyed and running before the window  [NO LONGER ALLOWED]",
           BASE_TASKS, rtk_before_launch=True,
           note="corrections available at t=0; this is the 285 s case in the main model")

    # --- B: base in-window, survey-in, RTK before launch ----------------
    tasks_b = BASE_TASKS + BASE_IN_WINDOW + [SURVEY_IN]
    report("B  Base set up in-window, 90 s survey-in, RTK fix required before launch",
           tasks_b, rtk_before_launch=True,
           note="the literal reading of the ruling -- this is the problem case")

    # --- C: base in-window, immediate fixed position --------------------
    tasks_c = BASE_TASKS + BASE_IN_WINDOW + [FIXED_POS]
    report("C  Base declares its first 3D fix as its reference, RTK before launch",
           tasks_c, rtk_before_launch=True,
           note="absolute position ~1-2 m off, but that error is COMMON MODE")

    # --- D: as C, but RTK converges in flight ---------------------------
    report("D  As C, but RTK converges during climb and transit  [RECOMMENDED]",
           tasks_c, rtk_before_launch=False,
           note="nothing in the rules requires an RTK fix at launch")

    # --- E: survey-in for absolute accuracy, RTK still in flight ---------
    tasks_e = BASE_TASKS + BASE_IN_WINDOW + [SURVEY_IN]
    report("E  Base survey-in 90 s for ABSOLUTE accuracy, RTK converges in flight",
           tasks_e, rtk_before_launch=False,
           note="worst-case answer to Q1 (geotag judged against surveyed truth)")

    # --- folding arms: what do they cost? --------------------------------
    print("\n" + "=" * 78)
    print("FOLDING ARMS  -  what deployment time does the window afford?")
    print("=" * 78)
    print("  Case D (recommended) with per-aircraft deploy-and-verify time added.")
    print("  Read the CALIBRATED column: case D calibrated sits at 285 s against")
    print("  a 300 s window, so there is ~15 s of real margin to spend.")
    print()
    print(f"  {'per aircraft':>13}{'launch':>9}{'margin':>9}"
          f"{'calibrated':>12}{'verdict':>10}")
    for secs in (0, 10, 15, 20, 22, 25, 28, 30, 45):
        tasks = with_arm_deploy(BASE_TASKS + BASE_IN_WINDOW + [FIXED_POS], secs)
        _, finish = schedule(tasks)
        launch = finish['pre-arm + arm']
        cal = launch + 100
        label = "fixed arms" if secs == 0 else f"{secs} s"
        print(f"  {label:>13}{launch:>8.0f}s{WINDOW - launch:>+8.0f}s"
              f"{cal:>11.0f}s{'OK' if cal <= WINDOW else 'OVER':>10}")
    print()
    print("  THE RESULT IS NOT THE ONE THE ARGUMENT EXPECTED. Deployment is FREE")
    print("  up to about 20 s per aircraft: launch stays at 185 s. It hides in")
    print("  crew slack, because the critical path in this window is not the")
    print("  crew at all -- it is the 75 s companion boot, then mesh association")
    print("  and mission-file parse. Two crew have idle time during that, and")
    print("  unfolding arms is exactly the kind of work that fits into it.")
    print()
    print("  Free to 22 s. At 25-28 s it starts pushing pre-arm and the")
    print("  calibrated case lands on 290-299 s -- inside 300 s arithmetically,")
    print("  but 1 s is not margin, it is a coin toss. Over at 30 s.")
    print()
    print("  So the honest budget is 22 s per aircraft, and 28 s is the point")
    print("  of no return. Deploy, lock and VERIFY in 22 s is achievable with")
    print("  quick-release clamps and a lock indicator you can see from a metre")
    print("  away. It is not achievable with bolts, and it is not achievable if")
    print("  the crew have to think about it.")
    print()
    print("  The launch box does not force the decision either: three aircraft")
    print("  at 1046 mm square (20 in props) sit side by side in 3138 mm, inside")
    print("  the 3.66 m box, unfolded. Folding buys TRANSPORT volume only --")
    print("  roughly 944 mm square down to ~450 mm with arms back.")
    print()
    print("  What remains against folding is structural, not schedule: a fold is")
    print("  a designed break point, and any fold between the camera and the")
    print("  GNSS antennas is a lever arm that changes on every unpack, which")
    print("  invalidates SYS-48. Keep folds strictly outboard of that core and")
    print("  the boresight objection goes away too.")

    # --- what the first geotag needs ------------------------------------
    print("\n" + "=" * 78)
    print("DOES OPTION D ACTUALLY WORK?  -  when is the first geotag needed")
    print("=" * 78)
    climb, transit = 60.0 / 3.0, 120.0 / 12.0
    for lbl, tasks, key in [('D  fixed-pos', tasks_c, 'base fixed-pos'),
                            ('E  90 s survey-in', tasks_e, 'base survey-in')]:
        start, finish = schedule(tasks)
        launch = finish['pre-arm + arm']
        rtk_fix = max(finish[key], finish['rover GNSS 3D fix']) + RTK_CONV
        first_sweep = launch + 45 + climb + transit
        slack = first_sweep - rtk_fix
        print(f"\n  {lbl}")
        print(f"    launch                     {launch:6.0f} s")
        print(f"    RTK fixed                  {rtk_fix:6.0f} s")
        print(f"    first sweep line begins    {first_sweep:6.0f} s")
        print(f"    slack before first geotag  {slack:+6.0f} s "
              f"[{'OK' if slack >= 0 else 'float for the first '
                 + str(int(-slack)) + ' s of sweep'}]")
    print()
    print("  Gate the first geotag on RTK-fixed rather than gating launch on it.")
    print("  If RTK has not fixed by the first detection, geotag in float and")
    print("  re-fuse once fixed -- the frame surplus makes that nearly free.")

    print("\n" + "=" * 78)
    print("WHY THE ABSOLUTE BASE POSITION BARELY MATTERS FOR DELIVERY")
    print("=" * 78)
    print("  The base's absolute error shifts every aircraft position by the same")
    print("  vector. The survivor is geotagged from a drone carrying that shift,")
    print("  and the delivery drone flies to that coordinate carrying the SAME")
    print("  shift -- so the kit lands on the true survivor. The error cancels.")
    print()
    print("  It does NOT cancel if the 250-point geotag score is judged by")
    print("  comparing our DISPLAYED coordinates against surveyed truth. That is")
    print("  an open question and the reason to still want a good absolute fix.")
    print()
    print("  Consequence: a long survey-in buys accuracy we mostly do not need.")
    print("  Trading 90 s of survey-in for ~1-2 m of common-mode bias is a good")
    print("  trade when the window has 15 s of margin.")


if __name__ == '__main__':
    main()
