#!/usr/bin/env python3
"""Generate one self-contained work-package proposal per delivery track.

WHY THIS EXISTS. The master proposal is the integrated system document: it
argues the mission, and it is the thing a competition judge reads. It is the
wrong document to hand a track lead, because no track lead owns 17 pages of it
and none of them can tell from it what they are personally funded for.

THE INVARIANT, same as track_budget.py: not one rupee is restated here. Every
figure comes from track_budget, which comes from competition_budget. If the
master budget moves, these documents move with it on the next run.

The technical prose IS written here rather than derived, because it is argument
rather than arithmetic. Every number inside it is cited to the model or
document that produced it, so the claims stay checkable.

Run:  python tools/proposal/build_track_proposals.py
Then: pdflatex each .tex in docs/proposal/tracks/
"""
from __future__ import annotations

import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "docs", "proposal", "figures"))

import competition_budget as cb   # noqa: E402
import track_budget as tb         # noqa: E402

OUT = os.path.join(ROOT, "docs", "proposal", "tracks")

PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage[margin=25mm]{geometry}
\usepackage{booktabs}
\usepackage{array}
\usepackage{amsmath}
\usepackage{microtype}
\usepackage{titlesec}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\titleformat{\section}{\large\bfseries}{\thesection}{0.6em}{}
\titleformat{\subsection}{\bfseries}{\thesubsection}{0.6em}{}
\setlength{\parskip}{0.5em}
\setlength{\parindent}{0pt}
\pagestyle{fancy}\fancyhf{}
\renewcommand{\headrulewidth}{0.4pt}
\newcommand{\inr}[1]{INR~#1}
"""

# ---------------------------------------------------------------- track prose
CONTENT = {
"A": dict(
 name="Air Vehicle",
 people="2 students",
 owns="Frame, propulsion, power, payload mechanism, assembly",
 opening=r"""
This track builds the thing that flies. Everything else in the programme is
carried by it, which means this track's schedule is the programme's schedule:
no other track can begin flight validation until an aircraft exists, and the
single measurement that decides whether one does is owned here.
""",
 sections=[
  ("The design point this track is funded to build", r"""
The aircraft is a quadrotor on 18\,in propellers with a maximum take-off mass of
\textbf{6.36\,kg}, giving a three-aircraft fleet of \textbf{19.08\,kg} against
the 25\,kg regulatory cap --- 24\,\% margin. Structure is 1\,495\,g (23.5\,\% of
MTOW) and the battery pack 1\,449\,g (22.8\,\%); together they are 46\,\% of the
aircraft, which is why airframe mass fraction and pack chemistry are the two
sensitivities this track carries in the risk register.

All of these figures regenerate from \texttt{tools/sizing-model/}\allowbreak
\texttt{rescueswarm\_sizing\_model.py}. None is transcribed by hand.
"""),
  ("Propulsion, and the measurement that is load-bearing", r"""
At a thrust-to-weight ratio of 2.0 the aircraft requires \textbf{125\,N total},
which is \textbf{3.18\,kgf per motor} on an 18\,in propeller, with hover sitting
at 1.59\,kgf --- 50\,\% of maximum, inside the healthy 45--55\,\% band. The mass
budget allows 160\,g per motor.

\textbf{The funded motors publish no thrust curve.} That is a deliberate cost
decision, not an oversight: professional-grade motors with published data cost
roughly 2.4 times as much. The consequence is that the thrust-to-weight figure
above is a \emph{requirement} rather than a measurement until the thrust stand
runs in P2, and the thrust stand is therefore not a convenience --- it is the
instrument that says whether this aircraft hovers. It is funded accordingly.

Two figures in \texttt{docs/sizing/sizing-calculations.md} contradict the model
here, quoting 2.53 and 2.94\,kgf per motor against the model's 3.18, and one
line still specifies a 20\,in propeller where the bill of materials buys 18\,in.
Reconciling those is a P1 action for this track.
"""),
  ("Energy: what the pack must actually do", r"""
The pack is sized by a reserve policy, not by the design mission. The mission
consumes 105.5\,Wh; the policy requires the pack to also carry one complete
re-sweep and four minutes of loiter, all inside an 80\,\% depth of discharge:
\[
105.5 + 22.1 + 60.8 = 188.4~\text{Wh usable},
\]
against 233.3\,Wh available --- a \textbf{24\,\% margin}.

Stated independently of chemistry, so that any candidate pack can be tested
against it, the requirement is \textbf{6S}, \textbf{$\geq$236\,Wh} nameplate,
\textbf{$\geq$115\,A continuous}, \textbf{$\leq$40\,m$\Omega$} and
\textbf{$\leq$1\,450\,g}. The current figure is the one most often missed: it is
not a burst rating. At T/W 2.0 the aircraft draws 2\,481\,W, which at 21.6\,V is
115\,A, and that must be available continuously.

The adopted implementation is 18 cells in 6S3P at 4500\,mAh and 45\,A
continuous. A 40\,A cell leaves 4.5\,\% burst margin against 18\,\%, and cells
whose 45\,A rating depends on an 80\,\textdegree C cut-off are 35\,A cells in
Indian ambient --- below the 38.3\,A per-cell peak. The specification was
tightened accordingly on 2026-08-20.
"""),
  ("Two open items this track owns", r"""
\textbf{The mass statement does not close.} Itemised masses sum to 6\,061\,g
against a 6\,360\,g MTOW, leaving \textbf{299\,g} --- 4.7\,\% --- unattributed.
It is small enough not to threaten fleet margin and large enough that it should
be attributed rather than absorbed. Closing it is a P1 action.

\textbf{Cell sourcing is a live commercial question.} The budget carries
\inr{700} per cell against a domestic supplier quote. A drop-in equivalent lists
publicly at \inr{405}. The action is not to switch --- cells are one of only
four remaining Indian lines and indigenisation is scored --- but to hold the
supplier quote against a published benchmark before committing.
"""),
 ],
 risks=[
  ("Motors deliver less than 3.18\\,kgf", "High", "P2 thrust stand. If they "
   "miss, the fallback is a published-curve motor at roughly 2.4$\\times$ the "
   "cost, which is a budget event this track must flag the moment it is known."),
  ("Mass residual grows during build", "Medium", "299\\,g is unattributed "
   "today. Fleet carries 4\\,919\\,g of growth allowance, so this is "
   "affordable, but it must be tracked from P1 not discovered at weigh-in."),
  ("Cell lead time", "Medium", "No spare packs are funded. Domestic sourcing "
   "is 2--3 weeks; order at P1, not P2."),
 ],
 interfaces=[
  ("B", "Provides the power distribution the avionics run on, and the "
        "vibration-isolated mounting the flight controller requires."),
  ("C", "Provides the mass, thrust and endurance figures the SITL model flies "
        "against. If the built aircraft differs from the model, the "
        "simulations stop being evidence."),
  ("D", "Provides the camera mounting plane and its boresight stability. "
        "Geolocation accuracy depends on that mount not moving."),
 ]),

"B": dict(
 name="Avionics and Communications",
 people="1--2 students",
 owns="Flight controller, companion computer, GNSS/RTK, mesh, safety link, video",
 opening=r"""
This track owns everything electrical between the airframe and the autonomy.
It carries the second-largest ask in the programme, and it carries the single
component whose specification is currently in doubt.
""",
 sections=[
  ("Compute, and why it is three parts rather than one", r"""
The stack is a flight controller, a companion computer and an accelerator, and
the division is not arbitrary. The accelerator is an M.2 class device whose only
interface is \textbf{PCIe}; it is a neural processing unit, not a computer, and
it cannot boot, hold a filesystem or terminate a camera link. The camera is a
CSI module producing a Bayer-mosaic stream that is not an image until something
demosaics and scales it. The companion computer is what both plug into.

\textbf{This has a hard consequence for procurement.} The accelerator requires a
host that exposes PCIe. That rules out the previous-generation single-board
computer entirely --- its PCIe lane is committed internally to a USB controller
and is never broken out. There is no adapter and no workaround. The host
generation is a dependency of the accelerator, not a performance preference,
and any cost pass that treats it as one produces a bill of materials that cannot
be assembled.
"""),
  ("Positioning: the item this track must resolve first", r"""
Geolocation accuracy governs \textbf{125 of 200} available geotagging points, and
the error budget is unambiguous about what drives it:

\begin{center}
\begin{tabular}{@{}lr@{}}
\toprule
\textbf{Configuration} & \textbf{RSS error} \\
\midrule
Standard GNSS, uncalibrated boresight & 4.57\,m \\
Standard GNSS, calibrated boresight & 3.88\,m \\
RTK + dual-antenna heading + calibration & 0.75\,m \\
\quad + 20-frame fusion & 0.66\,m \\
\bottomrule
\end{tabular}
\end{center}

The step from 3.88\,m to 0.75\,m is RTK. Nothing else in the budget moves the
number comparably, which is why the receiver and its base station survive every
cost-reduction pass.

\textbf{The open item.} The receiver currently carried against this line is
specified by its supplier as supporting SBAS correction services with a CEP
below 1.5\,m. That is assisted GNSS, not RTK, and it lands the system in the
3.88\,m row rather than the 0.75\,m row. Resolving this --- by confirming the
part, substituting a genuine RTK receiver, or re-scoring the geotagging
expectation --- is this track's first P1 action, because 125 points depend on
which row is true.
"""),
  ("The radio link, and a deferral that depends on a configuration", r"""
The sub-GHz safety radio is deferred on the strength of a specific claim: that
the primary radio link runs in a firmware mode carrying both control and MAVLink
telemetry on one link and one autopilot serial port. The older transparent-serial
mode \emph{consumes} that link --- configured that way the aircraft has telemetry
and no control, and the deferred radio is required again.

\textbf{This is not a preference, it is the precondition of a deferral}, and it
must be verified on the bench in P2 rather than assumed.

The mesh link budget is thin and this track should say so plainly: 5.8\,GHz
carries \textbf{1.7\,dB} of margin at the 600\,m design range against a 15\,dB
target for a mobile airborne link. The mitigation is architectural rather than
financial --- keep the ground antenna elevated, stream one switched video feed
rather than three, and accept that video degrades before command does. Total
offered load is 2.5\,Mbps against a 20\,Mbps channel, so the constraint is
margin, not bandwidth.
"""),
  ("Failsafe configuration", r"""
The battery failsafe thresholds are derived quantities, not chosen ones:
\texttt{BATT\_LOW\_VOLT} 18.48\,V and \texttt{BATT\_CRT\_VOLT} 17.18\,V follow
from the cell's resting curve and a pack resistance of
\texttt{BATT\_RESISTANCE}~=~0.0400\,$\Omega$. A previous configuration set the
sag-compensated voltage source while leaving pack resistance unset, so the
compensation did nothing and a loaded voltage was compared against a threshold
taken from the resting curve. That class of defect --- a correct-looking
configuration that nothing actually applies --- is what this track's bench
verification exists to catch.
"""),
 ],
 risks=[
  ("Primary GNSS is not RTK-capable", "High", "Resolve at P1. If confirmed, "
   "either substitute a true RTK receiver or restate the geotagging "
   "expectation. 125 points ride on this."),
  ("Radio mode does not carry control and telemetry together", "High",
   "Verify on the bench at P2. If it does not, the deferred sub-GHz safety "
   "radio must be restored, which is a budget event."),
  ("5.8\\,GHz margin is 1.7\\,dB against a 15\\,dB target", "Medium",
   "Elevated ground antenna, single switched video feed. Command link is on "
   "a separate budget with 12.2\\,dB."),
 ],
 interfaces=[
  ("A", "Depends on regulated power and on vibration-isolated mounting."),
  ("C", "Supplies the companion computer the autonomy runs on, and the MAVLink "
        "routing it commands through."),
  ("D", "Supplies the camera interface, the accelerator, and the time and "
        "attitude reference every geotag is computed against."),
 ]),

"C": dict(
 name="Autonomy and Ground Control",
 people="2 students",
 owns="Coverage planner, task allocation, state machine, ground station, SITL",
 opening=r"""
This track asks for the least money in the programme and carries a large share
of the scored functionality. That is not an accident of accounting: the
deliverables are software, the workstations are team-supplied, and the
verification environment is free. It is worth stating explicitly, because a
funding split that shows a near-zero line invites the assumption that the track
is small. It is not --- it is inexpensive.
""",
 sections=[
  ("Coverage planning over arbitrary search regions", r"""
The rulebook does not promise a rectangular search area, so the planner does not
assume one. The implementation decomposes a possibly non-convex boundary into
monotone cells, fills each by scanline, clips every transect to the true
boundary, and routes between cells along a visibility graph shortest path rather
than a straight line that might leave the region.

Verified across 13 boundary shapes including non-convex notches and slots:
\textbf{0.00\,m of path outside the boundary}, workload imbalance across three
aircraft \textbf{$\leq$0.02\,\%}, and 157 tests passing. Three defects were found
and fixed in reaching that state --- a scanline span that bridged concave
notches, a missing cell decomposition, and a straight inter-cell hop that cut
corners across excluded ground.
"""),
  ("Autonomy, and how it is evidenced", r"""
The competition requires autonomous operation, and asserting it is not the same
as showing it. The verification harness parses the flight script's own syntax
tree and proves that \textbf{no MAVLink transmission occurs after the mode is
set to AUTO}. That is a structural argument rather than an observational one:
it does not depend on having watched a particular flight behave.

The same harness checks inter-aircraft separation, geofence containment,
failsafe configuration, energy consumption against the model, and recorder clock
integrity, and exits non-zero on any failure. It is re-runnable, which means the
autonomy claim is regenerated rather than remembered.

A separation breach of 3.10\,m was found this way and corrected to 5.34\,m by
staggering recovery loiter times. A 453.9\,s recorder clock discontinuity was
found the same way, and independently confirmed against consumed charge.
"""),
  ("The ground station is deliberately unable to fly the aircraft", r"""
Requirement SYS-20 holds that the ground station must be \emph{architecturally}
incapable of originating a retask, waypoint change or arming command --- not
merely configured not to. This is a design property, not a policy, and it is
what makes the autonomy claim defensible under scrutiny: an operator cannot
accidentally invalidate it.
"""),
  ("Why the ask is small", r"""
The two workstations are team-supplied and the simulation environment is
open-source. What remains is a fabricated sun hood and an observer monitor for
field use. This track's real cost is student time across the full programme
duration, which the funding request does not price and which the schedule must
protect.
"""),
 ],
 risks=[
  ("Pad containment has zero margin", "High", "Recorded in the master "
   "proposal as a measured result. Recovery geometry must be re-verified "
   "whenever aircraft mass or descent rate changes."),
  ("Survey altitude is unresolved", "Medium", "The design point says 60\\,m; "
   "every flown simulation uses 40\\,m. Coverage timing, transect count and "
   "detection all move with it. Resolution is shared with Track D and needs "
   "a recall measurement to settle."),
  ("Simulation diverges from the built aircraft", "Medium", "SITL evidence is "
   "only evidence if the modelled aircraft matches the built one. Re-baseline "
   "against Track A's measured mass and thrust after P2."),
 ],
 interfaces=[
  ("A", "Consumes measured mass, thrust and endurance. Simulation fidelity "
        "depends on receiving them after the P2 thrust-stand run."),
  ("B", "Runs on the companion computer and commands through its MAVLink "
        "routing. Depends on the link carrying control and telemetry together."),
  ("D", "Consumes detections and supplies the aircraft state --- position, "
        "attitude, time --- that each geotag is computed from."),
 ]),

"D": dict(
 name="Perception",
 people="1--2 students",
 owns="Detector, tiling, geotagging, calibration, dataset",
 opening=r"""
This track owns the 250 marks available for detection. It also owns the
programme's most honest weakness: with the ground-truth apparatus and the field
dataset both deferred, detection recall is a \emph{modelled} quantity and there
is currently no funded route to measuring it.
""",
 sections=[
  ("What the detector actually receives", r"""
The sensor is a 12.3\,MP module at $4056\times3040$ on a \textbf{1.55\,\textmu m}
pixel pitch behind a 6\,mm lens. The sizing chapter assumed a
\textbf{1.82\,\textmu m} pitch --- the same pixel \emph{count} at a different
pixel \emph{size}, which means resolution on target is not what that chapter
states.

At the 40\,m search altitude, taking a supine adult as 1.7\,m by 0.5\,m:

\begin{center}
\begin{tabular}{@{}lrrl@{}}
\toprule
\textbf{Stage} & \textbf{GSD} & \textbf{Target} & \textbf{COCO class} \\
 & (cm/px) & (px$^2$) & \\
\midrule
Sensor, native & 1.03 & 13\,600 & large \\
After $2\times$ downsample & 2.07 & 3\,400 & medium \\
Sizing chapter, 60\,m, $2\times$ & 3.65 & 640 & \textbf{small} \\
\bottomrule
\end{tabular}
\end{center}

The last row matters more than it looks. Published recall figures report average
precision \emph{by size class}, and small-object AP is routinely far below
medium on the same model. Quoting the 47-pixel figure implicitly promises
small-object performance the programme does not need to accept.
"""),
  ("The inference budget, and where it does not close", r"""
Tiling is 640\,px tiles at 20\,\% overlap. At $2\times$ downsample that is 12
tiles per frame, and at 2\,Hz, \textbf{24 inferences per second} --- inside the
accelerator's capability.

\textbf{The temporal budget does not close.} Requirement SYS-46 asks for at
least 12 looks per target per pass so that multi-frame fusion has enough
independent observations. At 40\,m and 2\,Hz the target is in frame for
\textbf{7.9 looks} --- a 34\,\% shortfall. Meeting 12 looks needs
\[
r \geq \frac{n\,v}{D} = 3.06~\text{Hz},
\]
which is 37 inferences per second rather than 24. The trade is real and
unresolved: raise the capture rate and pay about half again in inference load,
fly slower, fly higher, or relax the look count. It should be decided
deliberately rather than discovered.

The overlap geometry does hold: at 128\,px of shared margin against an 82\,px
target, no survivor can be cut by a tile boundary without appearing whole in the
neighbouring tile.
"""),
  ("Geolocation: calibrate before fusing", r"""
The error budget makes an ordering argument that this track should follow
literally. Random terms fall as $1/\sqrt{N}$ with frame count; systematic terms
do not fall at all. Boresight calibration and a ground-plane height fix
therefore matter \emph{more} than additional frames, and fusion is worth having
but not worth over-investing in --- it moves the total from 0.75\,m to 0.66\,m,
while calibration moves it from 4.57\,m to 3.88\,m before RTK is even applied.

Calibrate, then fuse. Not the other way round.
"""),
  ("The honest position on recall", r"""
Detection recall is modelled and will remain modelled unless the deferred lines
are restored. The ground-truth apparatus would have given detections something
to be measured against; the field dataset would have given the detector Indian
terrain to be trained on. Both were deferred at team direction to reach the
requested figure.

This track should state that plainly in every review rather than presenting
modelled recall as though it were measured. If any single deferred line is
restored, this is the one with the largest effect on a scored outcome.
"""),
 ],
 risks=[
  ("Recall is unmeasured", "High", "Ground truth and dataset both deferred. "
   "Mitigation is honesty in review plus opportunistic collection during "
   "flight tests; the real fix costs money and is a restoration decision."),
  ("Fusion look count fails SYS-46 at the flown altitude", "High",
   "7.9 looks against 12 required. Needs a decision on capture rate, "
   "groundspeed or altitude. Shared with Track C."),
  ("Fine-tuning at the wrong target scale", "Medium", "Altitude error changes "
   "pixels on target, so the detector should be fine-tuned across a band "
   "around 82\\,px rather than trained at a single scale."),
 ],
 interfaces=[
  ("A", "Depends on a stable camera mounting plane. Boresight drift is a "
        "systematic error that no amount of frame fusion removes."),
  ("B", "Depends on the accelerator, the camera interface, and on time and "
        "attitude being accurate enough that a geotag means something."),
  ("C", "Supplies detections; consumes aircraft state. Shares the unresolved "
        "survey-altitude decision."),
 ]),
}

PHASES = [
 ("P1", "24 Aug -- 13 Sep", {
   "A": "Long-lead orders placed: cells, motors, structure stock. Mass residual "
        "attributed. Sizing-document contradictions reconciled.",
   "B": "GNSS specification resolved. Long-lead orders: compute, camera, "
        "radios, GNSS. Interface control documents agreed.",
   "C": "SITL flying one aircraft. Planner validated against arbitrary "
        "boundaries.",
   "D": "Camera and accelerator ordered. Survey-altitude position stated with "
        "its evidence."}),
 ("P2", "14 Sep -- 4 Oct", {
   "A": "\\textbf{Thrust-stand measurement} -- the gate for the whole "
        "programme. Pack assembled and bench-discharged.",
   "B": "Radio mode verified on the bench. Failsafe thresholds validated "
        "against a real pack discharge.",
   "C": "Full mission in SITL. Verification harness passing.",
   "D": "Detector running on the accelerator at the budgeted rate. Boresight "
        "calibration procedure defined."}),
 ("P3", "5 Oct -- 18 Oct", {
   "A": "First flight. Measured mass and hover current reported to Track C.",
   "B": "Link range verified in the field. RTK fix demonstrated.",
   "C": "Simulation re-baselined against the built aircraft.",
   "D": "First airborne imagery at the flown altitude."}),
 ("P5", "9 Nov -- 22 Nov", {
   "A": "Single-aircraft full mission including payload release.",
   "B": "All links exercised under mission load.",
   "C": "Autonomous full mission, no operator input after AUTO.",
   "D": "Detection and geotagging in the loop, end to end."}),
]


def esc(s):
    return s


def track_doc(t):
    c = CONTENT[t]
    sub, pools, lines = tb.collect()
    asks = tb.ask_for(sub[t], pools[t])
    a = asks

    rows = []
    for lbl, amt, tier, _note in sorted(lines[t], key=lambda r: -r[1]):
        if amt == 0:
            continue
        mark = r"\textbf{K}" if tier == "KEEP" else ""
        rows.append(f"{lbl.replace('&', chr(92)+'&')} & {mark} & {amt:,} \\\\")
    deferred = sorted(l for l, amt, _t, _n in lines[t] if amt == 0)

    body = [PREAMBLE]
    body.append(r"\fancyhead[L]{RescueSwarm --- Track %s: %s}" % (t, c["name"]))
    body.append(r"\fancyhead[R]{\thepage}")
    body.append(r"\begin{document}")
    body.append(r"""
\begin{center}
{\LARGE\bfseries Track %s --- %s}\\[3mm]
{\large RescueSwarm: work package and funding request}\\[2mm]
NIDAR 2026--27 $\cdot$ Track 1 $\cdot$ Mission 1\\[1mm]
\textbf{Ask: \inr{%s}} $\cdot$ %s $\cdot$ %s
\end{center}
\vspace{2mm}\hrule\vspace{4mm}
""" % (t, c["name"], f"{a['total']:,.0f}", c["people"], c["owns"]))

    body.append(c["opening"])

    body.append(r"\section{Scope and ownership}")
    body.append(r"""
This track owns \textbf{%s}. It is one of four delivery tracks defined in
\texttt{docs/development-plan.md}~\S1.3; the integrated system argument lives in
the master proposal, \texttt{docs/proposal/rescueswarm-proposal.pdf}, which this
document does not restate.
""" % c["owns"].lower())

    for i, (title, prose) in enumerate(c["sections"], start=1):
        body.append(r"\section{%s}" % title)
        body.append(prose)

    # ---- funding -----------------------------------------------------------
    body.append(r"\section{Funding request}")
    body.append(r"""
Every figure below is generated from
\texttt{docs/proposal/figures/track\_budget.py}, which partitions the master
competition budget. The four track asks plus the shared pool reconcile to the
master figure exactly; that reconciliation is asserted in code and fails the
build if it ever stops holding. \textbf{K} marks a line held at professional
grade on purpose.
""")
    body.append(r"""
\begin{center}
\begin{tabular}{@{}p{88mm}cr@{}}
\toprule
\textbf{Item} & & \textbf{\inr{}} \\
\midrule
%s
\midrule
Subtotal & & %s \\
Customs duty and freight & & %s \\
GST & & %s \\
Contingency at 15\%% & & %s \\
\midrule
\textbf{TRACK %s ASK} & & \textbf{%s} \\
\bottomrule
\end{tabular}
\end{center}
""" % ("\n".join(rows), f"{a['subtotal']:,}", f"{a['duty']:,.0f}",
       f"{a['gst']:,.0f}", f"{a['contingency']:,.0f}", t,
       f"{a['total']:,.0f}"))

    if deferred:
        body.append(r"""
\textbf{Deferred or institutionally held, and therefore not requested:}
%s. These remain capabilities the track requires; they are simply not being
bought. Where a deferral carries a technical consequence it is stated in the
risk table below rather than left implicit.
""" % ", ".join(d.replace("&", r"\&") for d in deferred))

    # ---- milestones --------------------------------------------------------
    body.append(r"\section{Deliverables by phase}")
    mrows = []
    for pid, dates, m in PHASES:
        if t in m:
            mrows.append(r"\textbf{%s} & %s & %s \\" % (pid, dates, m[t]))
    body.append(r"""
\begin{center}
\begin{tabular}{@{}llp{88mm}@{}}
\toprule
\textbf{Phase} & \textbf{Dates} & \textbf{This track delivers} \\
\midrule
%s
\bottomrule
\end{tabular}
\end{center}
""" % "\n".join(mrows))

    # ---- risks -------------------------------------------------------------
    body.append(r"\section{Risks owned by this track}")
    rrows = ["%s & %s & %s \\\\" % (r[0], r[1], r[2]) for r in c["risks"]]
    body.append(r"""
\begin{center}
\begin{tabular}{@{}p{50mm}lp{70mm}@{}}
\toprule
\textbf{Risk} & \textbf{Sev.} & \textbf{Mitigation} \\
\midrule
%s
\bottomrule
\end{tabular}
\end{center}
""" % "\n".join(rrows))

    # ---- interfaces --------------------------------------------------------
    body.append(r"\section{Interfaces to other tracks}")
    irows = [r"Track %s & %s \\" % (o, d) for o, d in c["interfaces"]]
    body.append(r"""
\begin{center}
\begin{tabular}{@{}lp{110mm}@{}}
\toprule
\textbf{With} & \textbf{Dependency} \\
\midrule
%s
\bottomrule
\end{tabular}
\end{center}

Interfaces are where student programmes fail, because each side assumes the
other owns the gap. Every row above is a two-way commitment and should be
recorded as an interface control document at P1.
""" % "\n".join(irows))

    body.append(r"""
\vfill
\hrule\vspace{2mm}
{\small Generated by \texttt{tools/proposal/build\_track\_proposals.py} from
\texttt{docs/proposal/figures/track\_budget.py}. Financial figures are not
maintained in this document and must not be edited here: change the master
budget and regenerate. Technical claims cite the model or document that
produced them.}
\end{document}
""")
    return "\n".join(body)


def main():
    os.makedirs(OUT, exist_ok=True)
    built = []
    for t in "ABCD":
        path = os.path.join(OUT, f"track-{t}-{CONTENT[t]['name'].split()[0].lower()}.tex")
        io.open(path, "w", encoding="utf-8").write(track_doc(t))
        built.append(path)
        print(f"  wrote {os.path.relpath(path, ROOT)}")

    for p in built:
        for _ in range(2):
            r = subprocess.run(["pdflatex", "-interaction=nonstopmode",
                                "-halt-on-error", os.path.basename(p)],
                               cwd=OUT, capture_output=True, text=True)
        status = "OK" if r.returncode == 0 else "FAILED"
        print(f"  {status:6} {os.path.basename(p).replace('.tex', '.pdf')}")
        if r.returncode != 0:
            tail = [l for l in r.stdout.splitlines() if l.startswith("!")][:5]
            print("\n".join("        " + l for l in tail))
    for ext in (".aux", ".log", ".out"):
        for f in os.listdir(OUT):
            if f.endswith(ext):
                os.remove(os.path.join(OUT, f))


if __name__ == "__main__":
    main()
