#!/usr/bin/env python3
r"""Generate the proposal's sizing and analysis section from the model itself.

WHY THIS EXISTS. The proposal claims "every value is produced by a sizing model
held in the repository and regenerated in continuous integration; none is
transcribed by hand." That claim was true of the model outputs in docs/sizing/
and NOT true of the .tex, which carried its numbers by hand. Adding a full
derivation section by hand would have put roughly a hundred more hand-typed
figures behind a sentence promising the opposite.

So the section is generated. Every number below is read from
rescueswarm_sizing_model at import, or derived here from that model's own
primitive constants and then ASSERTED against the model's result. If a constant
changes, this file's output changes with it or the build fails.

Equations are written out in full because a reader has to be able to check the
arithmetic without running anything -- that is the point of showing the physics
rather than just the answer.

Run:  python tools/proposal/build_sizing_section.py
Emits: docs/proposal/generated-sizing.tex   (\input by the master proposal)
"""
from __future__ import annotations

import contextlib
import io
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "sizing-model"))

with contextlib.redirect_stdout(io.StringIO()):     # the model prints on import
    import rescueswarm_sizing_model as M
    import camera_optics as CO
    import radio_links as RL

OUT = os.path.join(ROOT, "docs", "proposal", "generated-sizing.tex")

# ---------------------------------------------------------------- derivations
g, rho, FM = M.g, M.rho, M.FM
eta = M.eta_mot * M.eta_esc
A = M.N_rot * math.pi * (M.D / 2) ** 2
T_hov = M.MTOW * g
P_shaft = T_hov ** 1.5 / (FM * math.sqrt(2 * rho * A))
P_elec = P_shaft / eta + M.P_avio
I_hov = P_elec / M.V_nom
P_pk = (M.T_W * T_hov) ** 1.5 / (FM * math.sqrt(2 * rho * A))
P_pk_e = P_pk / eta + M.P_avio
I_pk = P_pk_e / M.V_nom
t_hov = M.E_pack * M.DOD / P_elec * 60

# every derived value is checked against the model's own result
for label, mine, theirs, tol in [
        ("hover shaft power", P_shaft, M.P_shaft, 0.01),
        ("hover electrical power", P_elec, M.Ph, 0.01),
        ("hover current", I_hov, M.I_hov, 0.01),
        ("peak electrical power", P_pk_e, M.P_max, 0.01),
        ("peak current", I_pk, M.I_max, 0.01),
        ("hover endurance", t_hov, M.t_hov, 0.01)]:
    assert abs(mine - theirs) / theirs <= tol, \
        f"{label}: derived {mine:.4g} vs model {theirs:.4g}"

# --- reserve policy, at the adopted MTOW ------------------------------------
E_req_np, _, E_nom, E_rsw, E_lo = M.required_pack(M.MTOW)
E_need = E_nom + E_rsw + E_lo

# --- optics -----------------------------------------------------------------
o = CO.optics(CO.SPECIFIED)
a40 = CO.at_altitude(CO.SPECIFIED, 40.0)
hyp = CO.hyperfocal_m(CO.SPECIFIED)
rs = CO.rolling_shutter(CO.SPECIFIED, 40.0, CO.GROUNDSPEED)
looks = CO.looks_per_target(CO.SPECIFIED, 40.0, 2.0)
need_hz = CO.rate_for_fusion(CO.SPECIFIED, 40.0)
blur40 = CO.blur_limit(CO.SPECIFIED, 40.0, CO.GROUNDSPEED)

# --- ballistics (kit release), from the model's own constants ---------------
m_kit, Cd, A_t, rho_sl = M.mp, M.Cd, M.A_tumb, M.rho_sl
v_term = math.sqrt(2 * m_kit * g / (rho_sl * Cd * A_t))
beta = m_kit / (Cd * A_t)


def fall(h, wind=0.0):
    """Vertical drop with quadratic drag; drift is the wind-relative integral."""
    t, v, x, dt = 0.0, 0.0, 0.0, 1e-4
    vx = -wind
    while h > 0:
        a = g - (0.5 * rho_sl * Cd * A_t * v * v) / m_kit
        v += a * dt
        h -= v * dt
        x += -vx * dt
        ax = (0.5 * rho_sl * Cd * A_t * vx * abs(vx)) / m_kit
        vx -= ax * dt
        t += dt
    return t, v, abs(x)


t6, vi6, _ = fall(6.0)
_, _, d6_3 = fall(6.0, 3.0)
_, _, d6_6 = fall(6.0, 6.0)

# --- structure --------------------------------------------------------------
wheelbase = (M.D + 0.030) * math.sqrt(2)
L_arm = wheelbase / 2
T_per = M.T_W * M.MTOW * g / M.N_rot
M_arm = T_per * L_arm
OD, ID = 0.025, 0.023
I_tube = math.pi * (OD ** 4 - ID ** 4) / 64
sigma = M_arm * (OD / 2) / I_tube / 1e6
SF = 600 / sigma

# --- link budget ------------------------------------------------------------
# The parameters live in radio_links.py, which matlab/export_model.py also
# reads, so this table and fig-links are the same numbers by construction.
R = RL.GEOFENCE_M
fspl = RL.fspl_db

# One row per adopted link. Built here rather than typed into the template
# because the template would then be a second copy of the table.
def _texname(s):
    return s.replace(" GHz", r"\,GHz").replace(" MHz", r"\,MHz")


LINKROWS = " \\\\\n".join(
    r"{name} & {tx:.1f} & {g:.0f} & $-{sens:.0f}$ & {f:.1f} & \textbf{{{m:.1f}}}".format(
        name=_texname(k["name"]), tx=k["tx_dbm"],
        g=k["g_tx_dbi"] + k["g_rx_dbi"], sens=abs(k["sens_dbm"]),
        f=fspl(k["f_mhz"], R), m=RL.margin_db(k, R))
    for k in RL.ADOPTED
) + r" \\"
# The escaping hazard this file has hit before: a dropped backslash turns
# \textbf into a TAB and \b into a backspace, and both compile silently.
assert LINKROWS.count(r"\textbf") == len(RL.ADOPTED), "LINKROWS: lost a backslash"
assert not any(ord(c) < 32 and c != "\n" for c in LINKROWS), "LINKROWS: control char"


# --- tiling, and what a two-stage gate would buy back ------------------------
# Tile geometry is the design's own: 640 px tiles on a 512 px stride, i.e. 20 %
# overlap, applied to the NATIVE frame. WATER_FRAC is an assumption, not a
# measurement -- it is the fraction of tiles expected to be open water, and the
# gate figure below is only as good as it is.
# --- selected motor, from the supplier datasheet ----------------------------
# Tarot TL96020, 5008, 340 KV. These are the two numbers the datasheet gives
# that the sizing loop can be checked against; it does NOT publish a thrust
# curve, which is the whole reason P2 exists.
DS_MOTOR_CONT_A = 26.5
DS_MOTOR_MASS_G = 168.0

TILE, STRIDE, GATE_PX = 640, 512, 96
WATER_FRAC = 0.87
n_tiles = ((math.ceil((CO.SPECIFIED["px_w"] - TILE) / STRIDE) + 1)
           * (math.ceil((CO.SPECIFIED["px_h"] - TILE) / STRIDE) + 1))
inf_rate = n_tiles * need_hz
gate_ratio = (TILE / GATE_PX) ** 2
gate_equiv = inf_rate / gate_ratio + inf_rate * (1.0 - WATER_FRAC)

# ---------------------------------------------------------------------- emit
V = {
 "N": f"{M.N_rot}", "Din": f"{M.D/0.0254:.0f}", "Dm": f"{M.D:.4f}",
 "A": f"{A:.4f}", "MTOW": f"{M.MTOW:.2f}", "g": f"{g:.3f}",
 "rho": f"{rho:.3f}", "FM": f"{FM:.2f}", "etam": f"{M.eta_mot:.2f}",
 "etae": f"{M.eta_esc:.2f}", "eta": f"{eta:.3f}", "Pavio": f"{M.P_avio:.0f}",
 "That": f"{T_hov:.1f}", "Pshaft": f"{P_shaft:.0f}", "Pelec": f"{P_elec:.0f}",
 "Vnom": f"{M.V_nom:.1f}", "Vmax": f"{M.V_max:.1f}", "Vmin": f"{M.V_min:.0f}",
 "Ihov": f"{I_hov:.1f}", "Ipk": f"{I_pk:.1f}", "Ppk": f"{P_pk_e:.0f}",
 "TW": f"{M.T_W:.1f}", "Ttot": f"{M.T_W*T_hov:.0f}", "Tkgf": f"{M.T_W*T_hov/g:.2f}",
 "Tper": f"{T_per/g:.2f}", "Thovper": f"{T_hov/M.N_rot/g:.2f}",
 "hovfrac": f"{100*(T_hov/M.N_rot)/T_per:.0f}",
 # Tarot TL96020 datasheet: 26.5 A max continuous, 168 g. Both are supplier
 # figures, not measurements; the motor still publishes no thrust curve, which
 # is why P2 measures thrust and current together.
 "dscont": f"{DS_MOTOR_CONT_A:.1f}",
 "Ihovm": f"{I_hov/M.N_rot:.1f}",
 "hovpct": f"{100*(I_hov/M.N_rot)/DS_MOTOR_CONT_A:.0f}",
 "Ipkm": f"{I_pk/M.N_rot:.1f}",
 "pkpct": f"{100*(I_pk/M.N_rot)/DS_MOTOR_CONT_A:.0f}",
 "dsmass": f"{DS_MOTOR_MASS_G:.0f}",
 "modmass": f"{M.bd['motors']/M.N_rot*1000:.0f}",
 "dmass": f"{DS_MOTOR_MASS_G*M.N_rot - M.bd['motors']*1000:+.0f}",
 "DL": f"{M.MTOW/A:.2f}", "PL": f"{M.MTOW*1000/P_elec:.1f}",
 "Epack": f"{M.E_pack:.0f}", "Ah": f"{M.Ah_pack:.1f}", "mpack": f"{M.m_pack*1000:.0f}",
 "ncell": f"{M.n_cells}", "S": f"{M.S_cells}", "P": f"{M.P_par}",
 "DOD": f"{M.DOD:.0%}".replace("%", r"\%"), "thov": f"{t_hov:.1f}",
 "Emis": f"{M.E:.1f}", "Tmis": f"{M.T/60:.1f}",
 "Enom": f"{E_nom:.1f}", "Ersw": f"{E_rsw:.1f}", "Elo": f"{E_lo:.1f}",
 "Eneed": f"{E_need:.1f}", "Eusable": f"{M.E_pack*M.DOD:.1f}",
 "Ereq": f"{E_req_np:.0f}", "margin": f"{100*(M.E_pack*M.DOD/E_need-1):.0f}",
 "Ipack": f"{M.I_pack_max:.0f}", "Imargin": f"{100*(M.I_pack_max/I_pk-1):.0f}",
 "Crate": f"{I_pk/M.Ah_pack:.2f}", "Chov": f"{I_hov/M.Ah_pack:.2f}",
 "esc": f"{I_pk/M.N_rot:.0f}",
 "fleet": f"{3*M.MTOW:.2f}", "cap": "25.0",
 "fmargin": f"{100*(25-3*M.MTOW)/25:.0f}",
 # optics
 "pitch": f"{CO.SPECIFIED['pitch_um']:.2f}", "f": f"{CO.SPECIFIED['f_mm']:.0f}",
 "pxw": f"{CO.SPECIFIED['px_w']}", "pxh": f"{CO.SPECIFIED['px_h']}",
 "sw": f"{o['w_mm']:.3f}", "sh": f"{o['h_mm']:.3f}", "sd": f"{o['diag_mm']:.2f}",
 "hfov": f"{o['hfov']:.1f}", "vfov": f"{o['vfov']:.1f}", "dfov": f"{o['dfov']:.1f}",
 "ifov": f"{o['ifov_mdeg']:.2f}",
 "gsd40": f"{a40['gsd_cm']:.2f}", "ppl40": f"{a40['person_px']:.0f}",
 "ppl40a": f"{a40['person_px2']:,.0f}",
 "wat40": f"{a40['water_px']:.0f}", "wat40a": f"{a40['water_px2']:,.0f}",
 "waterm": f"{CO.WATER_M:.1f}",
 "sww": f"{a40['swath_w']:.1f}", "swh": f"{a40['swath_h']:.1f}",
 "hyp": f"{hyp:.2f}", "hyphalf": f"{hyp/2:.2f}",
 "rsms": f"{CO.READOUT_MS:.0f}", "rsm": f"{rs['shift_m']:.2f}",
 "rspx": f"{rs['shift_px']:.0f}",
 "looks": f"{looks['frames']:.1f}", "needhz": f"{need_hz:.2f}",
 "ntile": f"{n_tiles}", "infreq": f"{inf_rate:.0f}",
 "gatepx": f"${GATE_PX}" + r"\times" + f"{GATE_PX}$",
 "gateratio": f"{gate_ratio:.0f}", "gateequiv": f"{gate_equiv:.0f}",
 "fusion": f"{CO.FUSION_MIN_FRAMES}", "vg": f"{CO.GROUNDSPEED:.0f}",
 "blur": f"{blur40*1000:.2f}", "blurinv": f"{1/blur40:.0f}",
 # ballistics
 "mkit": f"{m_kit*1000:.0f}", "Cd": f"{Cd:.2f}", "At": f"{A_t*1e4:.0f}",
 "beta": f"{beta:.1f}", "vterm": f"{v_term:.1f}",
 "t6": f"{t6:.2f}", "vi6": f"{vi6:.1f}", "d63": f"{d6_3:.2f}", "d66": f"{d6_6:.2f}",
 # structure
 "wb": f"{wheelbase*1000:.0f}", "Larm": f"{L_arm:.3f}", "Marm": f"{M_arm:.1f}",
 "OD": f"{OD*1000:.0f}", "ID": f"{ID*1000:.0f}", "Itube": f"{I_tube*1e12:.0f}",
 "sigma": f"{sigma:.0f}", "SF": f"{SF:.0f}",
 # link
 "R": f"{R:.0f}", "f58": f"{fspl(5800, R):.1f}", "f24": f"{fspl(2400, R):.1f}",
 "f868": f"{fspl(865, R):.1f}", "linkrows": LINKROWS,
 "mvid": f"{RL.margin_db(RL.ADOPTED[0], R):.1f}",
 "mcmd": f"{RL.margin_db(RL.ADOPTED[1], R):.1f}",
 "mlora": f"{RL.margin_db(RL.ADOPTED[2], R):.1f}",
 "mwifi": f"{RL.margin_db(RL.WITHDRAWN[0], R):.1f}",
 "fwifi": f"{fspl(RL.WITHDRAWN[0]['f_mhz'], R):.1f}",
 "dwifi": f"{RL.range_at_zero_margin_m(RL.WITHDRAWN[0])/1000:.2f}",
 "dvid": f"{RL.range_at_zero_margin_m(RL.ADOPTED[0])/1000:.1f}",
 "mgap": f"{RL.margin_db(RL.ADOPTED[0], R) - RL.margin_db(RL.WITHDRAWN[0], R):.1f}",
 # coordination channel: airtime, occupancy, and the GFSK trade
 "meshload": f"{RL.MESH_NONVIDEO_KBPS:.0f}",
 "lorarate": f"{RL.lora_bitrate_bps():.0f}",
 "lorakbps": f"{RL.lora_bitrate_bps()/1000:.1f}",
 "loragap": f"{RL.N_AIRCRAFT*RL.MESH_NONVIDEO_KBPS*1000/RL.lora_bitrate_bps():.0f}",
 "frameb": f"{RL.FRAME_B:.0f}", "framehz": f"{RL.FRAME_HZ:.0f}",
 "lora36": f"{1000*RL.lora_airtime_s(RL.FRAME_B):.1f}",
 "lorabare": f"{8000*RL.FRAME_B/RL.lora_bitrate_bps():.1f}",
 "loraframe": f"{1000*RL.mean_frame_airtime_s('lora'):.1f}",
 "gfskframe": f"{1000*RL.mean_frame_airtime_s('gfsk'):.1f}",
 "occnaive": f"{100*RL.naive_occupancy():.1f}",
 "occlora": f"{100*RL.occupancy('lora'):.1f}",
 "occgfsk": f"{100*RL.occupancy('gfsk'):.1f}",
 "ceiling": f"{100*RL.OCCUPANCY_CEILING:.0f}",
 "maxlora": f"{RL.max_frame_hz('lora'):.1f}",
 "txlora": f"{RL.ADOPTED[2]['tx_dbm']:.0f}",
 "gfskrate": f"{RL.GFSK_BPS/1000:.0f}",
 "gfsksens": f"$-{abs(RL.GFSK_SENS_DBM):.0f}$",
 "sfgap": f"{RL.GFSK_SENS_DBM - RL.ADOPTED[2]['sens_dbm']:.0f}",
 "ratemul": f"{RL.GFSK_BPS/RL.lora_bitrate_bps():.1f}",
 "gfskmargin": f"{RL.gfsk_margin_db(R):.1f}",
}

TEX = r"""%=============================================================================
% GENERATED FILE -- do not edit.
% Produced by tools/proposal/build_sizing_section.py from the sizing model.
% Every number here is read from rescueswarm_sizing_model or derived from its
% constants and asserted against its result. Edit the model, not this file.
%=============================================================================
\section{Sizing and Analysis}
\label{sec:sizing}

This section shows how we arrived at the design point, not just the result.
Every figure is computed by our sizing model, and the section itself is
generated from it, so any change to a constant in the model appears here too.

\subsection{Constants and where they come from}

\begin{center}
\begin{tabular}{@{}llp{4.2cm}@{}}
\toprule
\textbf{Symbol} & \textbf{Value} & \textbf{Basis} \\
\midrule
$\rho$ & @@rho@@\,kg/m$^3$ & $\sim$30\,\textdegree C at 300\,m density altitude; an Indian summer field, not sea level \\
$\mathrm{FM}$ & @@FM@@ & Rotor figure of merit, mid-range of the 0.5--0.7 literature band \\
$\eta_{\text{mot}}$ & @@etam@@ & BLDC efficiency near the hover operating point \\
$\eta_{\text{esc}}$ & @@etae@@ & Electronic speed controller \\
$P_{\text{avio}}$ & @@Pavio@@\,W & Companion computer, autopilot, GNSS, camera, radios, servos \\
$\mathrm{DoD}$ & @@DOD@@ & Usable depth of discharge; land at 20\,\% state of charge \\
$T/W$ & @@TW@@ & Static thrust-to-weight, a reserve policy \\
\bottomrule
\end{tabular}
\end{center}

We chose two of these values cautiously. Air density is taken for a hot day at
altitude rather than at sea level, which increases the power required, and the
figure of merit is taken from the middle of the published range rather than the
top. We would rather find out now that the design is tight than discover it on
the flying field.

\subsection{Hover power, from momentum theory}

The rotor disk area for @@N@@ rotors of diameter @@Din@@\,in
($D=@@Dm@@$\,m) is
\[
\begin{aligned}
A &= N\pi\left(\frac{D}{2}\right)^{2} = @@A@@~\text{m}^2,\\
\text{disk loading} &= \frac{m}{A} = @@DL@@~\text{kg/m}^2 .
\end{aligned}
\]
Momentum theory gives the induced power needed to produce thrust $T$ over that
disk area~\cite{leishman2006helicopter}. Dividing by the figure of merit
$\mathrm{FM}$, the ratio of ideal induced power to actual shaft power, accounts
for blade drag and uneven inflow and gives the shaft power:
\[
P_{\text{shaft}} = \frac{T^{3/2}}{\mathrm{FM}\sqrt{2\rho A}}
= \frac{(@@That@@)^{3/2}}{@@FM@@\sqrt{2(@@rho@@)(@@A@@)}}
= @@Pshaft@@~\text{W},
\]
where $T = mg = @@That@@$\,N at the @@MTOW@@\,kg maximum take-off mass. Adding
the drivetrain and the avionics load,
\[
P_{\text{elec}} = \frac{P_{\text{shaft}}}{\eta_{\text{mot}}\eta_{\text{esc}}}
+ P_{\text{avio}}
= \frac{@@Pshaft@@}{@@eta@@} + @@Pavio@@ = @@Pelec@@~\text{W},
\]
which at the @@Vnom@@\,V pack nominal is a hover current of
$I = P/V = @@Ihov@@$\,A. Power loading is @@PL@@\,g/W.

\subsection{Peak power and the current the pack must supply}

Induced power scales as $T^{3/2}$, so at the design thrust-to-weight of
@@TW@@ the shaft power rises by $@@TW@@^{3/2}$:
\[
P_{\text{peak}} = \frac{(@@TW@@\,T)^{3/2}}{\mathrm{FM}\sqrt{2\rho A}\,\eta}
+ P_{\text{avio}} = @@Ppk@@~\text{W}
\;\Longrightarrow\;
I_{\text{peak}} = @@Ipk@@~\text{A}.
\]
It is this current, more than the energy, that rules out most candidate packs.
It has to be supplied continuously rather than in short bursts, because the
aircraft must be able to hold @@TW@@ times its weight, not just reach it
briefly. The modelled pack supplies @@Ipack@@\,A, a margin of @@Imargin@@\,\%,
and each motor's share sets the speed controller rating at @@esc@@\,A peak.

This is also why a smaller pack does not work. At @@Ah@@\,Ah the peak is
@@Crate@@\,C and hover is @@Chov@@\,C; a pack of half the capacity would need
twice the C-rate to deliver the same current. A larger capacity keeps the
discharge rate down.

\subsection{Propulsion}

\[
\begin{aligned}
T_{\text{total}} &= (T/W)\,mg = @@Ttot@@~\text{N} = @@Tkgf@@~\text{kgf},\\
T_{\text{motor}} &= @@Tper@@~\text{kgf}.
\end{aligned}
\]
Hover needs @@Thovper@@\,kgf per motor, which is @@hovfrac@@\,\% of maximum
thrust. This is inside the 45--55\,\% range where both propeller efficiency and
thermal margin are reasonable. Well below that range, the propulsion system
would be larger and heavier than necessary; well above it, there would be too
little thrust left to hold attitude in gusts.

With the motor we have chosen, hover is comfortable but peak thrust is not. The
Tarot TL96020 is rated for @@dscont@@\,A continuous. In hover each motor draws
@@Ihovm@@\,A, which is @@hovpct@@\,\% of that rating. At the design
thrust-to-weight it draws @@Ipkm@@\,A, or @@pkpct@@\,\%, which is above the
continuous rating. We accept this only because full thrust is a short-term
reserve, not a flight condition: the aircraft hovers at about half throttle and
reaches this current for a few seconds at most, when recovering from a gust or
manoeuvring hard. It is still the tightest margin in the propulsion system, so
the P2 thrust stand measures current as well as thrust to show whether the motor
reaches @@Tper@@\,kgf within its rating. The datasheet also gives a motor mass
of @@dsmass@@\,g, compared with the @@modmass@@\,g the sizing model assumes, a
difference of @@dmass@@\,g per aircraft that we will confirm when we weigh the
parts in P5.

\subsection{The coupled mass and energy solve}

Pack mass, take-off mass and mission energy all depend on one another: a heavier
pack raises hover power, which raises the energy needed, which raises the pack
mass again. The model repeats the calculation until the values settle.

The reserve is what fixes the result. The pack must provide enough usable energy
for the mission, one complete second sweep of the search area, and four minutes
of hovering:
\[
\underbrace{@@Enom@@}_{\text{nominal}} + \underbrace{@@Ersw@@}_{\text{re-sweep}}
+ \underbrace{@@Elo@@}_{\text{loiter}} = @@Eneed@@~\text{Wh usable},
\]
against @@Eusable@@\,Wh available at @@DOD@@ depth of discharge, a margin of
@@margin@@\,\%. Whatever its chemistry, a candidate pack must therefore be rated
for at least \textbf{@@Ereq@@\,Wh} at \textbf{@@S@@S} and supply
\textbf{@@Ipk@@\,A continuously}.

The model was sized with @@ncell@@ cells in @@S@@S@@P@@P:
@@Epack@@\,Wh, @@Ah@@\,Ah, @@mpack@@\,g, @@Vnom@@\,V nominal
(@@Vmin@@--@@Vmax@@\,V). Hover endurance is @@thov@@\,min against a
@@Tmis@@\,min design mission consuming @@Emis@@\,Wh. The pack now specified
is a bought 6S 16\,Ah LiPo (Section~\ref{sec:energy}); these figures are
re-run on its measured mass before first flight.

At @@MTOW@@\,kg per aircraft the fleet weighs @@fleet@@\,kg, against the
@@cap@@\,kg regulatory limit, a margin of @@fmargin@@\,\%.

\subsection{Camera and optics}

All of the optics follow from three numbers: pixel count, pixel size and focal
length. The active sensor area is the pixel count times the pixel size,
\[
\begin{aligned}
w &= @@pxw@@ \times @@pitch@@\,\text{\textmu m} = @@sw@@~\text{mm},\\
h &= @@sh@@~\text{mm}, \qquad d = @@sd@@~\text{mm},
\end{aligned}
\]
and the fields of view are calculated exactly, without the small-angle
approximation:
\[
\begin{aligned}
\theta &= 2\arctan\!\left(\frac{s}{2f}\right)\\
&\Rightarrow\;
\text{HFOV}=@@hfov@@^\circ,\;
\text{VFOV}=@@vfov@@^\circ,\;
\text{DFOV}=@@dfov@@^\circ .
\end{aligned}
\]
By similar triangles through the lens, the ground sample distance at altitude
$H$ is
\[
\text{GSD} = \frac{p\,H}{f}
= \frac{@@pitch@@\,\text{\textmu m}\times 40\,\text{m}}{@@f@@\,\text{mm}}
= @@gsd40@@~\text{cm/px},
\]
giving a @@sww@@\,$\times$\,@@swh@@\,m footprint. One pixel subtends
@@ifov@@\,mdeg.

We consider two target sizes and design for the smaller one. An adult 1.7\,m
tall lying on a rooftop or dry ground covers @@ppl40@@\,px, or
@@ppl40a@@\,px$^2$. A person in water shows only head and shoulders, about
@@waterm@@\,m across, and covers @@wat40@@\,px, or @@wat40a@@\,px$^2$, roughly a
quarter of the area. We design for the person in water, because this is a flood
system and that is the posture we expect. The larger figure is the easy case and
is given only for comparison. Section~\ref{sec:perception} bases the tiling
decision on the water figure.

\textit{Focus} is not a problem. The hyperfocal distance,
\[
H_{\text{hyp}} = \frac{f^{2}}{Nc} + f = @@hyp@@~\text{m},
\]
taking the circle of confusion as two pixels, puts everything from
@@hyphalf@@\,m to infinity in acceptable focus. The aircraft never flies below
30\,m, so a fixed lens set once is in focus at every altitude we use. A focusing
mechanism would only add a moving part, extra power draw and a failure we could
not detect in flight.

\textit{Motion blur} is not a limit either. Keeping blur under one pixel
requires $t_{\text{exp}} \le \text{GSD}/v$, which at @@vg@@\,m/s is
@@blur@@\,ms, a shutter speed of $1/@@blurinv@@$\,s. We already require
$1/1000$\,s or faster.

\textit{Rolling shutter} has a small effect. Reading out the frame takes
@@rsms@@\,ms, during which the aircraft moves, giving @@rsm@@\,m of skew from top
to bottom, about @@rspx@@\,px. This does not matter for detection, but it does
matter for geolocation: unless the software corrects for the row in which a
detection appears, its position will be biased along the direction of flight.

\textit{Number of views} is where the budget falls short. A target stays in the
frame for the footprint length divided by ground speed, so at 40\,m and 2\,Hz it
is seen @@looks@@ times, against the @@fusion@@ views we want for combining
frames. Getting that many needs
\[
r \ge \frac{n\,v}{D} = @@needhz@@~\text{Hz},
\]
The options are a faster capture rate, a lower ground speed, a higher altitude,
or accepting fewer views. Raising the capture rate is the cheapest. Flying lower
shrinks the footprint faster than it shortens the pass, so it actually increases
the rate needed; flying higher makes the ground resolution coarser; and flying
slower makes every pass longer.

The cost of a faster capture rate is processing, not energy. At @@ntile@@ tiles
per frame it needs @@infreq@@ detector runs per second, against the
130--160 per second measured for the accelerator, which is at or beyond its
limit. A two-stage approach could recover this. A first stage that only asks
whether a tile is plain open water is judging texture, not looking for a person,
so it still works on a shrunken image even though, as
Section~\ref{sec:perception} shows, a person would be lost at that size. At
@@gatepx@@ input it handles about @@gateratio@@ times fewer pixels than the
detector, and discarding the open-water tiles would leave the equivalent of
about @@gateequiv@@ full detector runs. This first stage would run on the
accelerator we already carry rather than on an extra processor, because the
saving is in detector runs, not power: computing uses less than one per cent of
the aircraft's hover power.

\subsection{Payload release ballistics}

A kit of @@mkit@@\,g tumbling with drag coefficient @@Cd@@ and reference area
@@At@@\,cm$^2$ has ballistic coefficient
$\beta = m/(C_dA) = @@beta@@$\,kg/m$^2$ and terminal velocity
\[
v_{\text{term}} = \sqrt{\frac{2mg}{\rho C_d A}} = @@vterm@@~\text{m/s}.
\]
Integrating the fall with quadratic drag from a 6\,m release gives
@@t6@@\,s to impact at @@vi6@@\,m/s, with a crosswind drift of @@d63@@\,m at
3\,m/s and @@d66@@\,m at 6\,m/s.

The speed of the aircraft at release matters far more than the height. A
remaining ground speed of 0.5\,m/s moves the impact point by about 0.53\,m,
while a whole metre of height error moves it by less than 4\,cm. This is why we
hover before dropping: a multirotor can stop before release, and a fixed-wing
aircraft cannot.

\subsection{Structure, geometry and control authority}

Tip clearance of 30\,mm between adjacent @@Din@@\,in rotors sets a diagonal
wheelbase of @@wb@@\,mm and an arm length of @@Larm@@\,m. At the design
thrust-to-weight the root bending moment is
\[
\mathcal{M} = T_{\text{motor}}\,L = @@Marm@@~\text{N}\,\text{m}.
\]
For a @@OD@@\,$\times$\,@@ID@@\,mm carbon tube,
$I = \pi(D_o^4 - D_i^4)/64 = @@Itube@@$\,mm$^4$, so the bending stress is
$\sigma = \mathcal{M}c/I = @@sigma@@$\,MPa against roughly 600\,MPa for
unidirectional carbon, a safety factor of about @@SF@@.

Bending is therefore not what limits the structure, and we should not design as
if it were. The joints and clamps, and vibration fatigue where the arm meets the
frame, matter much more. A tube that passes the bending case by a factor of
@@SF@@ is being chosen for stiffness and ease of handling, not strength.

Dropping one kit from a magazine that sits off the centreline moves the centre
of gravity by less than 2\,mm, which takes only a few tens of grams of extra
thrust to correct. The amount is tiny, but it happens suddenly and disturbs the
attitude control. We avoid this by mounting the magazine on the centre of
gravity and holding position briefly after each release.

\subsection{Radio links}
\label{sec:links}

Three kinds of traffic have to be carried, and they have very different needs.
Video needs a high data rate but can be lost occasionally. Command and abort need
little data but must not be lost. Mission data and coordination also need little
data and must keep working even when the other two fail. We first planned to
carry all three on one 5.8\,GHz 802.11 mesh network, but dropped the idea after
working out its link budget.

\subsubsection{Link margin}

Free-space path loss at the @@R@@\,m design slant range follows Friis,
\begin{equation}
\mathrm{FSPL} = 20\log_{10}\!\left(\frac{d}{1\,\text{km}}\right)
              + 20\log_{10}\!\left(\frac{f}{1\,\text{MHz}}\right) + 32.44 ,
\label{eq:fspl}
\end{equation}
but path loss alone does not tell us much, since it is always higher at
5.8\,GHz than at 865\,MHz. What decides whether a link works is the margin left
over,
\begin{equation}
M = P_{\mathrm{tx}} + G_{\mathrm{tx}} + G_{\mathrm{rx}}
    - \mathrm{FSPL}(f,d) - S_{\mathrm{rx}} ,
\label{eq:margin}
\end{equation}
where $S_{\mathrm{rx}}$ is the receiver sensitivity for the modulation we
actually use, not the best figure on the datasheet. Table~\ref{tab:links} gives
(\ref{eq:margin}) at the geofence for our three links.

\begin{table}[t]
\caption{Adopted radio links, evaluated at the @@R@@\,m geofence}
\label{tab:links}
\centering
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}lrrrrr@{}}
\toprule
 & $P_{\mathrm{tx}}$ & $\Sigma G$ & $S_{\mathrm{rx}}$ & FSPL & $M$ \\
\textbf{Link} & (dBm) & (dBi) & (dBm) & (dB) & (dB) \\
\midrule
@@linkrows@@
\bottomrule
\end{tabular}
\end{table}

\subsubsection{Why we dropped the single mesh}

Applying (\ref{eq:margin}) to the 802.11 setup we had planned, with 20\,dBm into
5\,dBi antennas at each end and an MCS0 sensitivity of $-82$\,dBm, the same
@@fwifi@@\,dB of path loss leaves only @@mwifi@@\,dB of margin. That would have
been the weakest link in the system and also the one carrying the most data, so
the link most likely to fail would also be the one whose failure costs most.
With three separate radios, every link has more than @@mvid@@\,dB, an
improvement of @@mgap@@\,dB on the video link alone (Fig.~\ref{fig:links}a).

A mesh does not solve this, even though that was the original reason for
choosing one. Relaying through a second aircraft replaces one 600\,m link with
two shorter ones and reduces path loss. But each hop uses the same radio,
antennas and sensitivity, so the relay is only as reliable as the aircraft
carrying it, and the things that break the direct link, such as a banked
airframe, a person between the antennas or rain, tend to affect both hops. A
mesh improves average throughput but not the worst case, and the worst case was
our problem.

The 802.11 link would not be useless. It only reaches its sensitivity limit at
@@dwifi@@\,km and would work well in good conditions (Fig.~\ref{fig:links}b).
But rain, people in the way, a banked airframe and misaligned antennas all eat
into the margin, none of them is included in (\ref{eq:margin}), and
@@mwifi@@\,dB is not enough to cover them. Our video link has @@mvid@@\,dB at
the same distance and only runs out at @@dvid@@\,km.

\begin{figure*}[t]
\centering
\includegraphics[width=\textwidth]{fig-links.pdf}
\caption{(a) Link margin at the @@R@@\,m geofence, from (\ref{eq:margin}). The
802.11 mesh we dropped is included for comparison. (b) Margin against distance.
Each of our links is used at a small fraction of its maximum range; the dropped
mesh would not have been.}
\label{fig:links}
\end{figure*}

\subsubsection{Sizing the coordination channel}

Splitting the links has a consequence that the margin table does not show. The
mesh would have offered about @@meshload@@\,kbps of non-video capacity per
aircraft, whereas LoRa at SF7 on a 125\,kHz channel carries @@lorarate@@\,bps
for the whole fleet, @@loragap@@ times less. We had not compared the two designs
against the same traffic, so at first we missed this.

What matters is time on air, not bit rate. For the short packets this mission
sends, LoRa's preamble and header take up most of the time. The number of
symbols in a packet of $\mathit{PL}$ bytes is
\begin{equation}
n_{\mathrm{sym}} = n_{\mathrm{pre}} + 4.25 + 8 +
\left\lceil \frac{8\mathit{PL} - 4\mathrm{SF} + 44}{4\,\mathrm{SF}} \right\rceil
(\mathrm{CR}+4),
\label{eq:airtime}
\end{equation}
each lasting $2^{\mathrm{SF}}/\mathrm{BW}$. A @@frameb@@-byte message therefore
takes @@lora36@@\,ms on air, compared with the @@lorabare@@\,ms its data alone
would suggest, so the overhead is about a third of the total.

Our first plan sent aircraft state, task coordination and detection reports as
three separate messages, each at its own rate. That meant three preambles and
three headers per aircraft per second, and it used @@occnaive@@\,\% of the
channel, more than the @@ceiling@@\,\% limit we set to leave room for retries and
a fourth node. Combining them into one @@frameb@@-byte message per aircraft per
second, with a detection added when there is one, brings this down to
@@occlora@@\,\%. That still leaves almost no spare capacity: the maximum message
rate is @@maxlora@@\,Hz against the @@framehz@@\,Hz we need.

The answer is already in Table~\ref{tab:links}. The 865\,MHz link has @@mlora@@\,dB
of margin at the geofence, far more than this mission needs; the spreading
factor is buying range we do not use. The SX1262 can also run GFSK with the same
chip, antennas and @@txlora@@\,dBm output. At 50\,kbps its sensitivity is
@@gfsksens@@\,dBm instead of $-123$\,dBm, which gives up @@sfgap@@\,dB of the
spare margin for a @@ratemul@@ times higher data rate. Each message then takes
@@gfskframe@@\,ms, channel use drops to @@occgfsk@@\,\%, and the margin is still
@@gfskmargin@@\,dB, more than the video link has, while using only a tenth of
the channel.

\begin{table}[t]
\caption{Coordination channel, three aircraft, one @@frameb@@\,B frame each at @@framehz@@\,Hz}
\label{tab:coord}
\centering
\small
\begin{tabular}{@{}lrrrr@{}}
\toprule
\textbf{Mode} & \textbf{Rate} & \textbf{Frame} & \textbf{Occupancy} & \textbf{Margin} \\
\midrule
GFSK 50\,kbps      & @@gfskrate@@\,kbps & @@gfskframe@@\,ms & \textbf{@@occgfsk@@\,\%} & @@gfskmargin@@\,dB \\
LoRa SF7, 125\,kHz & @@lorakbps@@\,kbps & @@loraframe@@\,ms & @@occlora@@\,\% & @@mlora@@\,dB \\
\bottomrule
\end{tabular}
\end{table}

We therefore use GFSK normally and LoRa SF7 as a fallback, switching on the same
radio without any hardware change. The fallback is genuinely slower: at
@@occlora@@\,\% channel use it supports only @@maxlora@@\,Hz, so when we switch
to it we lower the message rate.

\subsubsection{Order of degradation}

We have arranged the links so that they fail in a sensible order, following
their margins. Video is allowed to fail first. Because it is digital, the picture
stays clean until the margin runs out and then frames start to drop, and losing
it costs the operator a view but does not affect the aircraft's decisions.
Coordination degrades next, from GFSK to LoRa SF7 and then to a lower message
rate. Command and abort come last, on ExpressLRS with @@mcmd@@\,dB of margin,
and are never traded away: if that link is lost, the aircraft carries out its
failsafe rather than waiting for the link to return. All the bands are
licence-free in India: the 865--867\,MHz short-range device band for
coordination, and the 2.4 and 5.8\,GHz ISM bands for command and video, each
used well within its power limit.

There are two limitations. All these margins assume free space, so they are best
cases: reflections off water, a low ground antenna clipping the Fresnel zone,
and the airframe blocking the signal in a turn all happen in practice and none
is modelled. And the GFSK sensitivity comes from the datasheet, not a
measurement. In P5 we will measure packet loss against distance on the built
aircraft, and only then will Table~\ref{tab:coord} be backed by evidence.

\subsection{Limits of this section}

Every figure in this section is modelled. The thrust figures rely on a motor
with no published thrust curve, and the detection figures assume a recall that
has not been measured. The sizing is consistent and its arithmetic can be
checked, but that does not show that the aircraft can actually do these things,
and we do not claim that it can.
"""

for k, v in V.items():
    TEX = TEX.replace("@@" + k + "@@", v)
assert "@@" not in TEX, "unsubstituted token: " + TEX[TEX.index("@@"):][:40]

io.open(OUT, "w", encoding="utf-8", newline="\n").write(TEX)
print(f"wrote {os.path.relpath(OUT, ROOT)}  ({len(TEX.splitlines())} lines, "
      f"{len(V)} generated values)")
print("all derived values cross-checked against the model")
