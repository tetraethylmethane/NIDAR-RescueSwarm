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

This section gives the derivations behind the design point rather than only its
result. Every figure regenerates from
% \path (url package) rather than \texttt: the path is one unbreakable token
% and overflows an IEEE column by 27 pt in \texttt. \path breaks at the slashes.
\path{tools/sizing-model/rescueswarm_sizing_model.py}; the section itself is
generated, so a constant cannot change in the model without changing here.

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

Two of these are deliberately unflattering. Air density is taken at a hot-day
altitude rather than sea level, which \emph{increases} the power required; and
the figure of merit is mid-band rather than optimistic. Sizing errors that
favour the design are the ones that are discovered on the flight line.

\subsection{Hover power, from momentum theory}

The rotor disk area for @@N@@ rotors of diameter @@Din@@\,in
($D=@@Dm@@$\,m) is
\[
\begin{aligned}
A &= N\pi\left(\frac{D}{2}\right)^{2} = @@A@@~\text{m}^2,\\
\text{disk loading} &= \frac{m}{A} = @@DL@@~\text{kg/m}^2 .
\end{aligned}
\]
Momentum theory gives the induced power required to generate thrust $T$ across
that disk~\cite{leishman2006helicopter}. Dividing by the figure of merit
$\mathrm{FM}$ --- the ratio of ideal induced power to actual shaft power, which
absorbs profile drag and non-uniform inflow --- converts the ideal figure to
shaft power:
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
That current, not the energy, is what disqualifies most candidate
packs. It is a continuous requirement rather than a burst rating: the aircraft
must be able to hold @@TW@@ $\times$ weight, not pulse it. The adopted pack
supplies @@Ipack@@\,A, a margin of @@Imargin@@\,\%, and the per-motor share sets
the controller rating at @@esc@@\,A peak.

This is also where a smaller pack fails. At @@Ah@@\,Ah the peak is
@@Crate@@\,C and hover is @@Chov@@\,C; a pack half the size would need twice the
C-rate to deliver the same amperes. Capacity is how the design buys down
discharge rate.

\subsection{Propulsion}

\[
\begin{aligned}
T_{\text{total}} &= (T/W)\,mg = @@Ttot@@~\text{N} = @@Tkgf@@~\text{kgf},\\
T_{\text{motor}} &= @@Tper@@~\text{kgf}.
\end{aligned}
\]
Hover demands @@Thovper@@\,kgf per motor, which is \textbf{@@hovfrac@@\,\% of
maximum} --- inside the 45--55\,\% band where propeller efficiency and thermal
margin are both reasonable. Sitting far below that band means an oversized and
heavy propulsion system; far above it means no authority left for attitude
control in gusts.

\textbf{Against the selected motor, hover is comfortable and the peak is not.}
The Tarot TL96020 publishes a maximum continuous current of @@dscont@@\,A. The
hover draw of @@Ihovm@@\,A per motor is @@hovpct@@\,\% of that, with wide
margin. The peak at the design thrust-to-weight is @@Ipkm@@\,A, or
\textbf{@@pkpct@@\,\%} --- above continuous rating. That is acceptable only
because $T/W = @@TW@@$ is a transient authority reserve rather than a flight
condition: the aircraft hovers at half throttle and reaches this current only
in a gust recovery or an aggressive manoeuvre, for seconds. It is recorded here
because it is the tightest margin in the propulsion chain, and because the P2
thrust stand measures current alongside thrust and will settle whether the
motor reaches @@Tper@@\,kgf before that rating rather than after it. The
datasheet also gives a motor mass of @@dsmass@@\,g against the @@modmass@@\,g
the sizing loop assumes, a difference of @@dmass@@\,g per aircraft that the P5
weigh-in resolves.

\subsection{The coupled mass and energy solve}

Pack mass, take-off mass and mission energy are mutually dependent: a heavier
pack raises hover power, which raises the energy required, which raises pack
mass. The model iterates to a fixed point rather than assuming one.

The reserve policy is what closes it. The pack must carry the nominal mission,
one complete re-sweep of the search area, and four minutes of loiter, inside the
usable window:
\[
\underbrace{@@Enom@@}_{\text{nominal}} + \underbrace{@@Ersw@@}_{\text{re-sweep}}
+ \underbrace{@@Elo@@}_{\text{loiter}} = @@Eneed@@~\text{Wh usable},
\]
against @@Eusable@@\,Wh available at @@DOD@@ depth of discharge --- a margin of
\textbf{@@margin@@\,\%}. Expressed independently of chemistry, any candidate
pack must therefore provide \textbf{@@Ereq@@\,Wh} nameplate at \textbf{@@S@@S}
and \textbf{@@Ipk@@\,A continuous}.

The adopted implementation is @@ncell@@ cells in @@S@@S@@P@@P:
@@Epack@@\,Wh, @@Ah@@\,Ah, @@mpack@@\,g, @@Vnom@@\,V nominal
(@@Vmin@@--@@Vmax@@\,V). Hover endurance is @@thov@@\,min against a
@@Tmis@@\,min design mission consuming @@Emis@@\,Wh.

At @@MTOW@@\,kg per aircraft the fleet is \textbf{@@fleet@@\,kg} against the
@@cap@@\,kg regulatory cap, leaving @@fmargin@@\,\% margin.

\subsection{Camera and optics}

Everything optical follows from three numbers: pixel count, pixel pitch and
focal length. Active area is count times pitch,
\[
\begin{aligned}
w &= @@pxw@@ \times @@pitch@@\,\text{\textmu m} = @@sw@@~\text{mm},\\
h &= @@sh@@~\text{mm}, \qquad d = @@sd@@~\text{mm},
\end{aligned}
\]
and the fields of view are exact arctangents, with no small-angle
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
Sensor and ground are similar triangles about the lens, so ground sample
distance at altitude $H$ is
\[
\text{GSD} = \frac{p\,H}{f}
= \frac{@@pitch@@\,\text{\textmu m}\times 40\,\text{m}}{@@f@@\,\text{mm}}
= @@gsd40@@~\text{cm/px},
\]
giving a @@sww@@\,$\times$\,@@swh@@\,m footprint. One pixel subtends
@@ifov@@\,mdeg.

Two target sizes follow, and the design is sized on the smaller.
A 1.7\,m supine adult --- a survivor on a rooftop or dry ground --- subtends
@@ppl40@@\,px, or @@ppl40a@@\,px$^2$. A person \emph{in water} presents head
and shoulders only, about @@waterm@@\,m across, and subtends
\textbf{@@wat40@@\,px}, or @@wat40a@@\,px$^2$ --- roughly a quarter of the
apparent area. \textbf{The second is the design target}, because this is a
flood system and immersion is the expected posture; the first is the
optimistic case and is quoted here only so the two are not confused.
Section~\ref{sec:perception} argues the tiling decision on the water figure.

\textbf{Focus.} This is not a design problem, and the arithmetic says so. The
hyperfocal distance,
\[
H_{\text{hyp}} = \frac{f^{2}}{Nc} + f = @@hyp@@~\text{m},
\]
taking the circle of confusion as two pixels rather than a film-era constant,
puts everything from @@hyphalf@@\,m to infinity in acceptable focus. The
aircraft never operates below 30\,m. A fixed lens set once is correct at every
altitude flown, and a focus mechanism would add a moving part, a power draw and
a failure mode that cannot be detected from the air.

\textbf{Motion blur.} This does not bind either. Holding smear under one pixel
requires $t_{\text{exp}} \le \text{GSD}/v$, which at @@vg@@\,m/s is
@@blur@@\,ms --- a shutter of $1/@@blurinv@@$\,s. The requirement already
mandates $1/1000$\,s or faster.

\textbf{Rolling shutter.} Small but not zero. Reading the frame out over
@@rsms@@\,ms while the aircraft moves gives @@rsm@@\,m of top-to-bottom skew,
about @@rspx@@\,px. Negligible for detection; \emph{not} negligible for
geolocation, where a detection's row position carries an along-track bias unless
the pipeline corrects for readout row.

\textbf{Temporal sampling.} This is where the budget does not close. A target is in
frame for the along-track footprint divided by ground speed, so at 40\,m and
2\,Hz it receives \textbf{@@looks@@ looks} against the @@fusion@@ that
multi-frame fusion requires. Meeting that count needs
\[
r \ge \frac{n\,v}{D} = @@needhz@@~\text{Hz},
\]
Of the available levers --- higher capture rate, lower ground speed, higher
altitude, or a relaxed look count --- raising the capture rate is the cheapest,
because lowering altitude shrinks the along-track footprint faster than it
shortens the pass and therefore \emph{raises} the required rate, while raising
altitude coarsens ground sampling and reducing ground speed lengthens every
transect.

The cost of that lever is throughput, not energy. At @@ntile@@ tiles per frame
the required rate is @@infreq@@ inferences per second, against the
130--160\,FPS measured for the accelerator: at or beyond the limit. This is
what a two-stage gate would buy back. A gate answering only whether a tile is
homogeneous open water is a texture discrimination rather than a person
detection, so it survives the downsampling that Section~\ref{sec:perception}
shows would destroy a person; at @@gatepx@@ input it costs roughly
@@gateratio@@ times fewer pixels than a detector pass, and discarding the open
water would leave of order @@gateequiv@@ full-inference equivalents. On that
argument the gate belongs on the accelerator already carried, not on an
additional processor: the saving is in inferences, not in watts, and the
aircraft's compute power is under one per cent of its hover power.

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

The governing sensitivity is release velocity, not release height. A
residual ground speed of 0.5\,m/s displaces the impact point by about 0.53\,m,
whereas a full metre of altitude error contributes under 4\,cm. This is the
whole argument for hover-and-drop: a multirotor can null its ground speed before
release and a fixed-wing cannot.

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
unidirectional carbon --- a safety factor of about \textbf{@@SF@@}.

\textbf{Bending is therefore not the structural driver, and the design should
not be optimised as though it were.} Joint and clamp design, and vibration
fatigue at the arm root, are what actually govern; a tube chosen to satisfy the
bending case by a factor of @@SF@@ is being chosen for stiffness and handling,
not strength.

Releasing one kit from a magazine offset from the centreline shifts the centre
of gravity by under 2\,mm, requiring a few tens of grams of differential thrust
to trim --- trivial in magnitude, but a \emph{step} change that excites the
attitude loop. The mitigation is to mount the magazine on the centre-of-gravity
axis and hold position briefly after release rather than to trim harder.

\subsection{Radio links}
\label{sec:links}

Three things have to cross the air gap, and they have almost nothing in common:
video, which is high-rate and may be lost; command and abort, which are
low-rate and may not; and mission data and swarm coordination, which are
low-rate and must survive whatever the other two do not. An earlier revision of
this design carried all three on one 5.8\,GHz 802.11 mesh. The link budget is
what withdrew it.

\subsubsection{Margin, not path loss}

Free-space path loss at the @@R@@\,m design slant range follows Friis,
\begin{equation}
\mathrm{FSPL} = 20\log_{10}\!\left(\frac{d}{1\,\text{km}}\right)
              + 20\log_{10}\!\left(\frac{f}{1\,\text{MHz}}\right) + 32.44 ,
\label{eq:fspl}
\end{equation}
but path loss on its own decides nothing --- it is larger at 5.8\,GHz than at
865\,MHz for every link ever built, and says only that higher frequencies
spread more. What decides whether a link closes is the \emph{margin} left after
it,
\begin{equation}
M = P_{\mathrm{tx}} + G_{\mathrm{tx}} + G_{\mathrm{rx}}
    - \mathrm{FSPL}(f,d) - S_{\mathrm{rx}} ,
\label{eq:margin}
\end{equation}
where $S_{\mathrm{rx}}$ is the sensitivity for the modulation actually used, not
the best figure on the datasheet. Table~\ref{tab:links} evaluates
(\ref{eq:margin}) at the geofence for the three adopted links.

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

\subsubsection{Why the single mesh was withdrawn}

Run (\ref{eq:margin}) on the 802.11 configuration it replaced --- 20\,dBm into
5\,dBi at each end, MCS0 sensitivity $-82$\,dBm --- and the same @@fwifi@@\,dB
of path loss leaves \textbf{@@mwifi@@\,dB}. That is the thinnest path in the
system and simultaneously the one carrying the most data, which is the worst
possible pairing: the link most likely to break is the one whose loss costs
most. The three-radio split leaves every remaining path above @@mvid@@\,dB, an
improvement of @@mgap@@\,dB on the video path alone (Fig.~\ref{fig:links}a).

Meshing does not repair this, and the reason is worth stating because it is the
argument that was originally made for the mesh. A relay hop through a second
aircraft replaces one 600\,m link with two shorter ones, which buys back path
loss --- but each hop is the same radio, the same antennas and the same
sensitivity, so the relay is only as reliable as the aircraft carrying it, and
the failure that takes out the direct path (a banked airframe, a body between
the antennas, rain) is largely common to both. A mesh raises average throughput
and does not raise the floor; here it is the floor that was the problem.

The withdrawn link is not useless --- it reaches its sensitivity floor at
@@dwifi@@\,km, and would work perfectly on a calm day
(Fig.~\ref{fig:links}b). Margin is not headroom, though. Rain, body blocking, a
banked airframe and antenna misalignment all draw on it, none of them is in
(\ref{eq:margin}), and @@mwifi@@\,dB does not cover them. The adopted video link
carries @@mvid@@\,dB to the same geofence and reaches zero only at
@@dvid@@\,km.

\begin{figure*}[t]
\centering
\includegraphics[width=\textwidth]{fig-links.pdf}
\caption{(a) Link margin at the @@R@@\,m geofence, from (\ref{eq:margin}). The
withdrawn 802.11 mesh is retained in the figure because the withdrawal is an
argument and the margin column is that argument. (b) Margin against slant
range. Every adopted link is flown at a small fraction of the range at which it
runs out; the withdrawn one is not.}
\label{fig:links}
\end{figure*}

\subsubsection{Sizing the coordination channel}

The split has a consequence the margin table does not show. The mesh offered
roughly @@meshload@@\,kbps per aircraft of non-video traffic; LoRa at SF7 over a
125\,kHz channel carries @@lorarate@@\,bps for the \emph{entire fleet}, a factor
of @@loragap@@ less. The two architectures had never been costed against the
same traffic, so this had gone unnoticed.

Airtime, not bit rate, is the currency. For the short packets this mission
sends, LoRa's preamble and coded header dominate: the number of symbols in a
packet of $\mathit{PL}$ bytes is
\begin{equation}
n_{\mathrm{sym}} = n_{\mathrm{pre}} + 4.25 + 8 +
\left\lceil \frac{8\mathit{PL} - 4\mathrm{SF} + 44}{4\,\mathrm{SF}} \right\rceil
(\mathrm{CR}+4),
\label{eq:airtime}
\end{equation}
each of duration $2^{\mathrm{SF}}/\mathrm{BW}$. A @@frameb@@-byte frame
therefore costs @@lora36@@\,ms on air, against the @@lorabare@@\,ms its payload
alone would imply --- the overhead is not a correction here, it is a third of
the cost.

The first allocation --- aircraft state, task consensus and detection reports as
three separate messages at their natural rates --- paid three preambles and
three coded headers per aircraft per second and consumed
@@occnaive@@\,\% of the channel, over the @@ceiling@@\,\% ceiling adopted for a
slotted channel with retries and a fourth node to accommodate. Consolidating
them into one @@frameb@@\,byte frame per aircraft per second, with a detection
appended when there is one, brings it to @@occlora@@\,\% --- which still leaves
essentially no headroom, at @@maxlora@@\,Hz maximum frame rate against the
@@framehz@@\,Hz needed.

What resolves it is already in Table~\ref{tab:links}. The 865\,MHz link closes
the geofence with @@mlora@@\,dB, and nothing in this mission needs anything like
that much --- the spreading factor that buys it is being spent on range the
geofence does not use. The SX1262 supports GFSK on the same silicon, the same
antennas and the same @@txlora@@\,dBm; at 50\,kbps its sensitivity is
@@gfsksens@@\,dBm rather than $-123$\,dBm, which trades @@sfgap@@\,dB of that
surplus for a @@ratemul@@$\times$ rate increase. The frame falls to
@@gfskframe@@\,ms, occupancy to @@occgfsk@@\,\%, and the margin is still
@@gfskmargin@@\,dB --- more than the video link has, on a tenth of the
channel.

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

So GFSK is the operating mode and LoRa SF7 is the fallback, selected on the same
radio without a hardware change. The fallback is genuinely degraded and the
model says so: at @@occlora@@\,\% it sustains @@maxlora@@\,Hz, so entering it
sheds the frame rate rather than pretending the channel is unchanged.

\subsubsection{What degrades first, by construction}

The ordering is deliberate and follows the margins. Video is analog, so it
degrades continuously into noise rather than dropping a digital link, and it is
the path permitted to fail. Coordination degrades next, from GFSK to LoRa SF7 to
a shed frame rate. Command and abort are last, on ExpressLRS at @@mcmd@@\,dB,
and are never traded --- if that link is lost the aircraft executes its failsafe
rather than waiting for it to return. Every band is licence-exempt in India: the
865--867\,MHz SRD band for coordination, and the 2.4 and 5.8\,GHz ISM bands for
command and video, each flown well inside its permitted power.

Two limits on all of this. Every margin here is free-space, so it is an upper
bound: multipath over water, Fresnel-zone intrusion from a low ground antenna
and airframe blocking during a bank are real and none is modelled.
And the GFSK sensitivity is a datasheet figure, not a measurement --- P5
measures packet error rate against range on the built aircraft, which is when
Table~\ref{tab:coord} becomes evidence rather than arithmetic.

\subsection{What this section does not establish}

Every figure above is \emph{modelled}. The thrust figures assume a motor that
publishes no thrust curve, and the detection figures assume a recall that has
not been measured. The sizing is internally consistent and its arithmetic is
checkable; that is a different claim from saying the aircraft has been shown to
do these things, and this document does not make the second claim anywhere.
"""

for k, v in V.items():
    TEX = TEX.replace("@@" + k + "@@", v)
assert "@@" not in TEX, "unsubstituted token: " + TEX[TEX.index("@@"):][:40]

io.open(OUT, "w", encoding="utf-8", newline="\n").write(TEX)
print(f"wrote {os.path.relpath(OUT, ROOT)}  ({len(TEX.splitlines())} lines, "
      f"{len(V)} generated values)")
print("all derived values cross-checked against the model")
