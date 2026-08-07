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
