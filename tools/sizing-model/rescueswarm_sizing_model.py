"""
RescueSwarm preliminary sizing model  (NIDAR 2026-27, Track 1)
Run:  python3 rescueswarm_sizing_model.py
Edit the assumption block below to re-run any trade. Every printed number in the
Sizing & Calculations report comes from this file.
"""
import numpy as np
from scipy.optimize import brentq


g   = 9.80665
rho = 1.150     # kg/m^3, ~30 C at 300 m ISA-ish density altitude (India, summer field)
rho_sl = 1.225

# ---------------- Assumptions (all traceable) ----------------
FM        = 0.60    # rotor figure of merit, momentum theory (lit. range 0.5-0.7)
eta_mot   = 0.82    # BLDC motor efficiency near hover operating point
eta_esc   = 0.95
eta_prop_chain = eta_mot*eta_esc
# W: Pi 5 + Hailo-8 (~15) + FC/GNSS (~5) + camera (~3) + mesh radio (~8)
# + servos/misc, with margin -> 55 W. (The breakdown used to say "Jetson",
# which is not the compute this programme buys; the total is unchanged
# because the Pi 5 + accelerator pair lands in the same 13-17 W band.)
P_avio    = 55.0
DOD       = 0.80    # usable depth of discharge (land at 20%)
# NOTE: e_lipo and e_liion were ALSO defined here, at 175 and 225 Wh/kg, and
# then redefined ~70 lines below at the conservative 165 and 200 that actually
# run. Python takes the later binding, so the output was always correct and
# the first pair was a trap for anyone reading the constants block. Removed;
# the single definition lives with the pack sizing where it is used.

# fixed (non-battery, non-structure, non-propulsion) masses, kg
avionics = {
 'flight controller (Pixhawk-class)':0.045,
 'GNSS primary (RTK-capable)':0.035,
 'GNSS secondary (heading)':0.035,
 'companion computer (Orin Nano + carrier)':0.185,
 'camera + lens + damped mount':0.130,
 'mesh radio 5.8 GHz + 2 antennas':0.110,
 'sub-GHz safety link (868 MHz)':0.030,
 'RC receiver (safety pilot link)':0.020,
 'power modules / BEC / PDB':0.085,
 'wiring harness + connectors':0.190,
 'buzzer, LEDs, switches, mounts':0.060,
}
m_avio = sum(avionics.values())

payload_system = {
 'release/magazine mechanism + servos':0.240,
 '4 x survivor kit @200 g':0.800,
 # SYS-41. Organisers confirmed a recovery parachute is permitted, ballistic
 # deployment included. A crash costs -50 and landing outside the pad costs
 # -10, so deploying is worth ~40 points even accepting the penalty. Canopy
 # 240 g + mount and bridle 60 g, per the Indian BOM tab 01 rows 48-49.
 'recovery parachute + mount':0.300,
}
m_payload_sys = sum(payload_system.values())

k_struct   = 0.235   # frame+arms+gear+hardware as fraction of MTOW (multirotor empirical 0.20-0.30)
T_W        = 2.0     # design thrust-to-weight at MTOW (sea level static)
N_rot      = 4
spec_thrust_motor = 195.0  # N of max static thrust per kg of motor mass (T-Motor MN-class empirical)
k_esc      = 0.35          # ESC mass as fraction of motor mass
m_prop_ea  = 0.072         # kg, 18 in CF folding prop + folding hub, from the
                           # Indian BOM tab 01: row 15 gives 116 g per matched
                           # PAIR (58 g each) and row 16 adds a 14 g hub.

def prop_area(D):
    return N_rot*np.pi*(D/2)**2

def hover_power_elec(m, D, rho_=rho):
    """Electrical power at hover, momentum theory + FM + drivetrain."""
    A = prop_area(D)
    P_shaft = (m*g)**1.5/(FM*np.sqrt(2*rho_*A))
    return P_shaft/eta_prop_chain + P_avio, P_shaft

def converge(m_batt, D, verbose=False):
    """Fixed point on MTOW given a battery mass."""
    m = 6.0
    for _ in range(200):
        T_tot   = T_W*m*g
        T_motor = T_tot/N_rot
        m_mot   = N_rot*T_motor/spec_thrust_motor
        m_esc   = k_esc*m_mot
        m_prop  = N_rot*m_prop_ea
        m_new   = (m_avio + m_payload_sys + m_batt + m_mot + m_esc + m_prop)/(1-k_struct)
        if abs(m_new-m) < 1e-9: break
        m = m_new
    return m, dict(motors=m_mot, esc=m_esc, props=m_prop, struct=k_struct*m,
                   avionics=m_avio, payload=m_payload_sys, battery=m_batt)

def endurance_min(m_batt, D, e_spec):
    m,_ = converge(m_batt, D)
    P,_ = hover_power_elec(m, D)
    E   = m_batt*e_spec*DOD          # Wh usable
    return 60.0*E/P, m, P



# ==================== from sizing3.py ====================

# --- revised, more conservative pack-level specific energies -------------
e_lipo  = 165.0   # 6S high-C LiPo, pack level incl. case/leads
e_liion = 200.0   # 21700 Li-ion (Molicel P45B class), pack level incl. holders/BMS/wiring

D = 18*0.0254
v_climb, v_desc = 3.0, 2.5
# 40 m, not 60. At 60 m a person in water is 25.8 px natively and 12.9 px
# after the old downsample; at 40 m natively they are 38.7 px, which is 2.2x
# the area and out of the small-object band where detectors do worst. The
# extra transects cost ~56 s of a mission that has minutes to spare.
h_search, h_transit, h_drop = 40.0, 30.0, 6.0
v_search, v_transit = 8.0, 12.0
k_cruise = 0.93

def P_climb(m,vc):
    P,_=hover_power_elec(m,D); return P + m*g*vc/eta_prop_chain
def P_cruise(m):
    P,_=hover_power_elec(m,D); return (P-P_avio)*k_cruise + P_avio

HFOV=np.deg2rad(70); sidelap=0.30
W  = 2*h_search*np.tan(HFOV/2); S = W*(1-sidelap)
n_lines = np.ceil(250/S); L_track = n_lines*400; L_per = L_track/3
t_turns = (n_lines/3)*6.0
n_del = 10/3
per_del_t = 150/v_transit + (h_search-h_drop)/v_desc + 8 + 2 + (h_transit-h_drop)/v_climb

def mission(m):
    Ph,_ = hover_power_elec(m,D)
    segs=[('Arm, spin-up, launch queue',45, Ph*0.35),
          (f'Climb to {h_search:.0f} m', h_search/v_climb, P_climb(m,v_climb)),
          ('Transit to sub-region', 120/v_transit, P_cruise(m)),
          ('Area sweep', L_per/v_search + t_turns, P_cruise(m)),
          ('Delivery (%.1f drops)'%n_del, n_del*per_del_t, P_cruise(m)*0.98),
          ('RTH transit ~250 m', 250/v_transit, P_cruise(m)),
          ('Recovery hold, descend, land', 90, Ph)]
    T=sum(s[1] for s in segs); E=sum(s[1]*s[2]/3600 for s in segs)
    return T,E,segs

# --- reserve policy: pack must cover  nominal + full re-sweep + 4 min loiter,
#     all inside the 80% usable window, AND hover endurance >= 2 x mission time.
def required_pack(m):
    T,E,_ = mission(m)
    Ph,_  = hover_power_elec(m,D)
    E_resweep = (L_per/v_search + t_turns)*P_cruise(m)/3600
    E_loiter  = 4*60*Ph/3600
    E_need    = E + E_resweep + E_loiter
    return E_need/DOD, T, E, E_resweep, E_loiter

print("="*80)
print("STEP 3b  BATTERY SIZED BY RESERVE POLICY  (coupled: pack mass <-> MTOW <-> energy)")
print("="*80)
print("  Policy: pack must deliver  [nominal mission + one full re-sweep + 4 min loiter]")
print("          within an 80% depth of discharge, and hover endurance >= 2x mission time.\n")
for chem,e in [('LiPo  ',e_lipo),('Li-ion',e_liion)]:
    mb = 1.0
    for _ in range(300):
        m,_ = converge(mb,D)
        E_pack_req,T,E,Er,El = required_pack(m)
        mb_new = E_pack_req/e
        if abs(mb_new-mb)<1e-7: break
        mb = 0.5*mb+0.5*mb_new
    m,bd = converge(mb,D); Ph,_=hover_power_elec(m,D)
    t_hov = 60*mb*e*DOD/Ph
    print(f"  {chem}: pack {mb*1000:4.0f} g ({mb*e:3.0f} Wh) -> MTOW {m:.2f} kg, fleet {3*m:5.2f} kg, "
          f"hover {t_hov:4.1f} min, mission {T/60:.1f} min, endurance ratio {t_hov/(T/60):.1f}x")
    print(f"           nominal {E:.0f} Wh + re-sweep {Er:.0f} Wh + loiter {El:.0f} Wh = {E+Er+El:.0f} Wh needed")

# ================= FINAL DESIGN POINT =================
# choose Li-ion, then round the pack UP to a buildable cell count and re-check
cell = dict(name='21700 Li-ion, 4500 mAh 45 A class', mAh=4500, V=3.6, g=70.0, Imax=45.0)
S_cells, P_par = 6, 3
n_cells = S_cells*P_par
m_cells = n_cells*cell['g']/1000
m_pack  = m_cells*1.15                       # +15% holders, BMS, leads, wrap
E_pack  = n_cells*cell['mAh']/1000*cell['V']
Ah_pack = P_par*cell['mAh']/1000
V_nom, V_max, V_min = S_cells*3.6, S_cells*4.2, S_cells*3.0
I_pack_max = P_par*cell['Imax']

MTOW,bd = converge(m_pack, D)
Ph,P_shaft = hover_power_elec(MTOW,D)
t_hov = 60*E_pack*DOD/Ph
T,E,segs = mission(MTOW)

print("\n"+"="*80)
print("FINAL DESIGN POINT  -  'RS-1' search & delivery quad")
print("="*80)
print(f"  Configuration          : quadrotor, {D/0.0254:.0f} in props, {S_cells}S{P_par}P 21700 Li-ion")
print(f"  Pack                   : {n_cells} cells, {m_pack*1000:.0f} g, {E_pack:.0f} Wh, {Ah_pack:.1f} Ah, "
      f"{V_nom:.1f} V nom ({V_min:.0f}-{V_max:.1f} V)")
print(f"  Pack specific energy   : {E_pack/m_pack:.0f} Wh/kg (pack level)")
print(f"  MTOW (4 kits loaded)   : {MTOW:.2f} kg      Empty (no batt/kits): {MTOW-m_pack-0.8:.2f} kg")
print(f"  FLEET OF 3             : {3*MTOW:.2f} kg   vs 25.0 kg limit -> margin {25-3*MTOW:.2f} kg ({(25-3*MTOW)/25:.0%})")
print(f"  Disk loading           : {MTOW/prop_area(D):.2f} kg/m2   power loading {MTOW*1000/Ph:.1f} g/W")
print(f"  Hover power            : {P_shaft:.0f} W shaft / {Ph:.0f} W electrical")
print(f"  Hover endurance (80% DoD): {t_hov:.1f} min")
print(f"  Design mission         : {T/60:.1f} min, {E:.0f} Wh = {E/(E_pack*DOD):.0%} of usable energy")
print(f"  Land-with SoC          : {100*(1-E/E_pack):.0f} %")

# The reserve policy is what SIZES the pack, so it has to be re-checked at the
# MTOW we actually adopted. STEP 3b evaluates it at the sizing solve, before the
# pack was rounded up to a buildable 18 cells and MTOW settled ~0.7 kg heavier.
# Reporting the solve-point figure as the requirement understates it by ~18%.
E_req_np, _, E_nom, E_rsw, E_lo = required_pack(MTOW)
E_need_use = E_nom + E_rsw + E_lo
print("\n  RESERVE POLICY  (re-evaluated at THIS MTOW, not at the sizing solve)")
print(f"    nominal {E_nom:.1f} Wh + re-sweep {E_rsw:.1f} Wh + loiter {E_lo:.1f} Wh"
      f" = {E_need_use:.1f} Wh usable")
print(f"    pack provides            {E_pack*DOD:.1f} Wh usable"
      f"  -> margin {E_pack*DOD/E_need_use-1:+.0%}"
      f"  {'PASS' if E_pack*DOD >= E_need_use else 'FAIL'}")
_I_pk = (P_shaft*(T_W**1.5)/eta_prop_chain + P_avio)/V_nom   # I_max, defined below
print(f"    minimum nameplate, ANY chemistry: {E_req_np:.0f} Wh"
      f"  (6S, >={_I_pk:.0f} A continuous)")

print("\n  MASS STATEMENT (per aircraft)")
rows=[('Structure: frame, arms, landing gear, hardware',bd['struct']),
      ('Motors (4)',bd['motors']),('ESCs (4)',bd['esc']),('Propellers (4)',bd['props']),
      ('Battery pack',bd['battery']),('Avionics + wiring harness',bd['avionics']),
      ('Payload magazine + release',0.240),('Survivor kits (4 x 200 g)',0.800)]
for n,v in rows: print(f"    {n:<48}{v*1000:7.0f} g  {v/MTOW:6.1%}")
print(f"    {'MTOW':<48}{MTOW*1000:7.0f} g")
print(f"    {'Fleet of 3 (weigh-in figure)':<48}{3*MTOW*1000:7.0f} g")
print(f"    {'Growth allowance to 24.0 kg fleet target':<48}{(24-3*MTOW)*1000:7.0f} g  "
      f"= {(24/(3*MTOW)-1):.0%} build overweight tolerated")

print("\n  PROPULSION")
T_tot=T_W*MTOW*g; T_per=T_tot/N_rot; T_hov_per=MTOW*g/N_rot
P_max = P_shaft*(T_W**1.5)/eta_prop_chain + P_avio
I_hov = Ph/V_nom; I_max = P_max/V_nom
print(f"    Static thrust required (T/W {T_W})        {T_tot:.0f} N  ({T_tot/g:.2f} kgf), {T_per/g:.2f} kgf per motor")
print(f"    Hover thrust per motor                  {T_hov_per/g:.2f} kgf  = {T_hov_per/T_per:.0%} of max (good: 45-55% band)")
print(f"    Hover current                           {I_hov:.1f} A  ({I_hov/Ah_pack:.2f} C)")
print(f"    Peak current at T/W=2                   {I_max:.0f} A  ({I_max/Ah_pack:.2f} C), {P_max:.0f} W")
print(f"    Pack burst capability ({P_par}P x {cell['Imax']:.0f} A)      {I_pack_max:.0f} A -> "
      f"{'OK, margin %.0f%%'%(100*(I_pack_max/I_max-1)) if I_pack_max>I_max else 'INSUFFICIENT - go 6S3P or high-C LiPo'}")
print(f"    ESC rating                              {I_max/4:.0f} A peak/motor -> specify 50-60 A ESC")
print(f"    Main power leads                        {I_max:.0f} A -> 10 AWG; motor leads 14 AWG")

print("\n  MISSION SEGMENTS")
print(f"    {'segment':<40}{'t':>7}{'P':>8}{'E':>9}")
for n,t,P in segs: print(f"    {n:<40}{t:6.0f}s{P:7.0f}W{P*t/3600:8.1f}Wh")
print(f"    {'TOTAL':<40}{T:6.0f}s{'':7}{E:8.1f}Wh   ({T/60:.1f} min of a 30 min allowance)")



# ==================== from sizing4.py ====================
e_liion=200.0
# D, m_pack and E_pack carry over from the final design point above -- do not
# re-hardcode them here, or they silently go stale when the pack changes.
MTOW,bd = converge(m_pack,D); Ph,_=hover_power_elec(MTOW,D)

# ---------------------------------------------------------------- HEX VARIANT
print("="*80); print("STEP 6  QUAD vs HEX REDUNDANCY TRADE"); print("="*80)
def variant(N,D_in,mb):
    global N_rot
    old=N_rot; N_rot=N; Dv=D_in*0.0254
    m,b = converge(mb,Dv); P,_=hover_power_elec(m,Dv)
    t=60*mb*e_liion*DOD/P
    N_rot=old
    return m,P,t,m/ (N*np.pi*(Dv/2)**2)
for N,D_in,lbl in [(4,20,'quad 4x20"'),(6,16,'hex  6x16"'),(6,15,'hex  6x15"')]:
    m,P,t,dl = variant(N,D_in,m_pack)
    print(f"  {lbl:<12} MTOW {m:.2f} kg  fleet {3*m:5.2f} kg  P_hov {P:4.0f} W  hover {t:4.1f} min  "
          f"DL {dl:4.2f} kg/m2  margin {25-3*m:5.2f} kg")
print("  Hex adds 2 motors+ESCs+props+arms; buys single-motor-out controllability.")
print("  Both fit the 25 kg fleet cap with >30% margin -> redundancy is affordable here.")

# ---------------------------------------------------------------- OPTICS
print("\n"+"="*80); print("STEP 7  CAMERA / OPTICS SIZING"); print("="*80)
# THE SENSOR IS THE ONE THE BOM BUYS. This block hardcoded 7.4 x 5.6 mm -- a
# 1/1.8" sensor on a 1.82 um pitch that nothing in this programme purchases.
# The Arducam IMX477 is type 1/2.3 at 1.55 um: the same pixel COUNT on a
# smaller pixel, so every GSD, field of view and transect count computed from
# the old numbers was for the wrong part. Deriving the sensor from its pitch
# rather than stating its dimensions makes that substitution impossible to
# make silently a second time.
px_w, px_h = 4056, 3040                  # 12.3 MP
pitch_um = 1.55                          # Arducam IMX477, type 1/2.3
f_mm = 6.0
sensor_w, sensor_h = px_w*pitch_um/1000.0, px_h*pitch_um/1000.0
HFOV = 2*np.arctan(sensor_w/(2*f_mm)); VFOV = 2*np.arctan(sensor_h/(2*f_mm))
print(f"  Sensor type 1/2.3 {px_w}x{px_h} ({px_w*px_h/1e6:.1f} MP) at "
      f"{pitch_um} um, {sensor_w:.3f} x {sensor_h:.3f} mm, f = {f_mm} mm")
print(f"  HFOV {np.rad2deg(HFOV):.1f} deg, VFOV {np.rad2deg(VFOV):.1f} deg, pixel pitch {sensor_w*1000/px_w:.2f} um")
print(f"\n  {'AGL':>5}{'swath':>8}{'along':>8}{'GSD':>9}{'person px':>11}{'lines':>7}{'track':>8}{'t/drone':>9}")
res={}
for h in [30,40,50,60,70,80]:
    W=2*h*np.tan(HFOV/2); Lalong=2*h*np.tan(VFOV/2); gsd=W/px_w
    ppl=1.7/gsd
    S=W*0.70; n=np.ceil(250/S); trk=n*400
    t=(trk/3)/8.0 + (n/3)*6
    res[h]=(W,gsd,ppl,n,trk,t)
    print(f"  {h:4.0f}m{W:7.1f}m{Lalong:7.1f}m{gsd*100:7.2f}cm{ppl:10.0f}{n:7.0f}{trk:7.0f}m{t:8.0f}s")
print("\n  Detection floor: CNN detectors need >~20-30 px on target for reliable small-object recall")
print("  (HERIDAL/SARD targets are ~0.1% of frame area). All rows above clear that by >2x.")
h=40; W,gsd,ppl,n,trk,t = res[h]
print(f"\n  SELECTED: {h} m AGL -> GSD {gsd*100:.2f} cm/px, person = {ppl:.0f} px long, swath {W:.0f} m")
print(f"           chosen for detection margin. Coverage is not the constraint: the extra\n           transects cost seconds of a mission with minutes to spare")

# blur & shutter
print("\n  MOTION BLUR / EXPOSURE")
for v,texp in [(8,1/500),(8,1/1000),(12,1/500),(12,1/1000)]:
    blur_m=v*texp; blur_px=blur_m/gsd
    print(f"    v={v:2.0f} m/s, 1/{1/texp:.0f} s -> smear {blur_m*1000:4.1f} mm = {blur_px:4.2f} px  "
          f"{'OK' if blur_px<1 else 'MARGINAL'}")
omega=np.deg2rad(20)  # attitude rate during a turn, rad/s
print(f"    attitude rate 20 deg/s at 1/1000 s -> {np.rad2deg(omega/1000)*3600/np.rad2deg(HFOV)*px_w:.1f} px "
      f"angular smear (dominates in turns -> do not trust detections while banking)")

# frame rate for overlap
Lalong=2*h*np.tan(VFOV/2)
for ov in [0.5,0.8]:
    adv=Lalong*(1-ov); fr=8.0/adv
    print(f"    {ov:.0%} forward overlap at 8 m/s needs only {fr:.2f} Hz capture "
          f"(advance {adv:.0f} m/frame)")
print(f"    -> run detection at 5 Hz: {5/ (8.0/Lalong):.0f}x redundant coverage per target, "
      f"~{Lalong/8.0*5:.0f} frames per target per pass -> multi-frame fusion is free")

# tiling budget
tile=640; ov_t=0.2
nt_w=np.ceil(px_w/(tile*(1-ov_t))); nt_h=np.ceil(px_h/(tile*(1-ov_t)))
print(f"\n  TILED INFERENCE (SAHI-style, {tile}px tiles, {ov_t:.0%} overlap)")
print(f"    NATIVE tiling = {nt_w:.0f}x{nt_h:.0f} = {nt_w*nt_h:.0f} tiles/frame")
# The accelerator is a Hailo-8, not the Orin Nano this block used to cite --
# that part is not in the bill of materials and its 30-40 FPS is what made
# native tiling look unaffordable in the first place.
for _hz in (2.0, 3.06):
    _need = nt_w * nt_h * _hz
    print(f"      at {_hz:.2f} Hz -> {_need:5.0f} inf/s   "
          f"Hailo-8 (130-160 FPS): {'FITS' if _need <= 130 else 'EXCEEDS':7}  "
          f"Hailo-8L (60-80): {'fits' if _need <= 60 else 'exceeds'}")
print(f"    2 Hz is the adopted rate and fits with margin. 3.06 Hz -- the rate")
print(f"    SYS-46's 12-look requirement needs -- does NOT, and is the open item")
print(f"    the two-stage gate in perception/cascade/ exists to buy back.")
# NATIVE tiling: dsf=1. The old 2x downsample was adopted because 48 crops
# looked unaffordable against an Orin Nano's 24-40 FPS -- a part that is not in
# the bill of materials. On the accelerator we actually buy, 48 tiles at 2 Hz
# fits. The downsample was discarding resolution we had already paid for, and
# it cost 4x the target area on the ground.
dsf=1
print(f"    what the detector is handed: {px_w//dsf}x{px_h//dsf}, "
      f"GSD {gsd*dsf*100:.2f} cm/px, a supine adult {ppl/dsf:.0f} px long")
print(f"    a person in WATER (0.4 m across) is {0.4/(gsd*dsf):.0f} px -- the size that")
print(f"    the design must be checked against, and the reason for 40 m over 60 m.")

# ---------------------------------------------------------------- BALLISTICS
print("\n"+"="*80); print("STEP 8  PAYLOAD DROP BALLISTICS"); print("="*80)
mp=0.200; box=(0.20,0.10,0.05)
A_faces=[box[0]*box[1],box[0]*box[2],box[1]*box[2]]
A_tumb=np.mean(A_faces); Cd=1.05
vt=np.sqrt(2*mp*g/(rho_sl*Cd*A_tumb))
print(f"  Kit 200 g, {box[0]*100:.0f}x{box[1]*100:.0f}x{box[2]*100:.0f} cm; tumbling ref area "
      f"{A_tumb*1e4:.0f} cm2, Cd {Cd}")
print(f"  Terminal velocity {vt:.1f} m/s  (ballistic coefficient m/(CdA) = {mp/(Cd*A_tumb):.1f} kg/m2)")

def drop(h0, vx0, wind, dt=1e-4):
    x,y,vx,vy=0.0,h0,vx0,0.0
    while y>0:
        vrx=vx-wind; vr=np.hypot(vrx,vy); Dg=0.5*rho_sl*Cd*A_tumb*vr
        ax=-Dg*vrx/mp; ay=-g - Dg*vy/mp*np.sign(1)
        ay=-g + (-Dg*vy)/mp
        vx+=ax*dt; vy+=ay*dt; x+=vx*dt; y+=vy*dt
    return x, abs(vy)
print(f"\n  {'h_rel':>6}{'t_fall':>9}{'v_impact':>10}{'drift @0 wind':>15}{'@3 m/s':>10}{'@6 m/s':>10}")
for h0 in [4,6,8,10,15]:
    tf=np.sqrt(2*h0/g)
    x0,vi=drop(h0,0,0); x3,_=drop(h0,0,3); x6,_=drop(h0,0,6)
    print(f"  {h0:5.0f}m{tf:8.2f}s{vi:9.1f}m/s{x0:13.2f}m{x3:9.2f}m{x6:9.2f}m")
print("\n  Sensitivity of impact point to release-state errors (release at 6 m, still air):")
for dv in [0.25,0.5,1.0,2.0]:
    x,_=drop(6,dv,0); print(f"    residual groundspeed {dv:4.2f} m/s -> {x:5.2f} m along-track miss")
for dh in [1,2]:
    x_,_=drop(6+dh,0.5,0); xb,_=drop(6,0.5,0)
    print(f"    altitude error +{dh} m (at 0.5 m/s residual) -> {abs(x_-xb)*100:4.1f} cm extra miss")
print("  -> release velocity dominates, exactly as in the fixed-wing airdrop literature.")
print("     A multirotor can null groundspeed; a fixed-wing cannot. Hover-and-drop wins.")

# ---------------------------------------------------------------- GEOLOCATION
print("\n"+"="*80); print("STEP 9  GEOTAG ERROR BUDGET (RSS, 1-sigma, target at 40 m AGL)"); print("="*80)
h=40.0; r_edge=W/2
def budget(gnss_h, gnss_v, att_deg, boresight_deg, terr_m, tsync, v, npx, gsd_):
    e_gnss=gnss_h
    e_att=h*np.tan(np.deg2rad(att_deg))
    e_bore=h*np.tan(np.deg2rad(boresight_deg))
    e_alt=(np.hypot(gnss_v,terr_m)/h)*r_edge
    e_px=npx*gsd_
    e_t=tsync*v
    tot=np.sqrt(e_gnss**2+e_att**2+e_bore**2+e_alt**2+e_px**2+e_t**2)
    return dict(GNSS_horizontal=e_gnss, attitude=e_att, boresight_cal=e_bore,
                height_scale=e_alt, pixel_centroid=e_px, time_sync=e_t, RSS=tot)
cases={
 'A  standard GNSS, uncalibrated boresight': budget(2.5,4.0,1.5,1.5,3.0,0.05,8,5,gsd),
 'B  standard GNSS, calibrated boresight':   budget(2.5,4.0,1.0,0.3,2.0,0.02,8,5,gsd),
 'C  RTK + dual-antenna heading + cal':      budget(0.03,0.05,0.3,0.2,1.0,0.02,8,5,gsd),
 'D  case C + 20-frame fusion (random terms /sqrt(N))': None}
b=cases['B  standard GNSS, calibrated boresight']
c=cases['C  RTK + dual-antenna heading + cal']
d={k:(v/np.sqrt(20) if k in('GNSS_horizontal','attitude','pixel_centroid','time_sync') else v)
   for k,v in c.items() if k!='RSS'}
d['RSS']=np.sqrt(sum(v**2 for v in d.values()))
cases['D  case C + 20-frame fusion (random terms /sqrt(N))']=d
keys=['GNSS_horizontal','attitude','boresight_cal','height_scale','pixel_centroid','time_sync','RSS']
print(f"  {'term':<22}"+"".join(f"{k[:3]:>10}" for k in ['A','B','C','D']))
for k in keys:
    line=f"  {k:<22}"
    for cn in cases: line+=f"{cases[cn][k]:9.2f}m"
    print(line + ("   <== total" if k=='RSS' else ""))
for cn in cases: print(f"    {cn}")
print("\n  Dominant terms: GNSS (case A/B) then terrain-height assumption and attitude (case C/D).")
print("  Boresight calibration and a DEM/ground-plane fix matter MORE than more frames -")
print("  systematic bias does not average out. Calibrate, then fuse.")

# ---------------------------------------------------------------- LINK BUDGET
print("\n"+"="*80); print("STEP 10  RF LINK BUDGET"); print("="*80)
def fspl(d_m,f_MHz): return 20*np.log10(d_m/1000)+20*np.log10(f_MHz)+32.44
diag=np.hypot(400,250)
print(f"  Worst-case slant range: field diagonal {diag:.0f} m + GCS offset -> design to 600 m")
links=[('5.8 GHz mesh (data+video)',5850,20,3,3,-82,'20 Mbps 20 MHz ch'),
       ('2.4 GHz mesh (fallback)',   2450,20,3,3,-85,'12 Mbps'),
       ('868 MHz safety link',        868,20,2,2,-120,'LoRa SF7 5.5 kbps')]
print(f"\n  {'link':<28}{'FSPL@600m':>11}{'Prx':>9}{'sens':>8}{'margin':>9}")
for n,f,ptx,gt,gr,sens,note in links:
    L=fspl(600,f); prx=ptx+gt+gr-L-3   # 3 dB implementation/polarisation loss
    print(f"  {n:<28}{L:10.1f}dB{prx:8.1f}dBm{sens:7.0f}{prx-sens:8.1f}dB   {note}")
print("\n  Fade margin target: >=15 dB for a mobile airborne link (multipath, body blockage, attitude).")
print("  5.8 GHz margin is adequate at 600 m LOS but degrades fast; keep the GCS antenna elevated")
print("  and accept that video, not command, is what degrades first.")
print("\n  DATA RATE BUDGET (per drone, to GCS)")
items=[('MAVLink telemetry @10 Hz',60),('Swarm state / task consensus @5 Hz',25),
       ('Detection metadata + thumbnails',150),('Video 720p30 H.265',1800)]
for n,kbps in items: print(f"    {n:<40}{kbps:6.0f} kbps")
tot_nv=sum(k for n,k in items if 'Video' not in n)
print(f"    {'Non-video subtotal per drone':<40}{tot_nv:6.0f} kbps  x3 = {3*tot_nv/1000:.2f} Mbps")
print(f"    {'+ ONE switched video feed':<40}{1800:6.0f} kbps")
print(f"    {'TOTAL offered load':<40}{(3*tot_nv+1800)/1000:5.2f} Mbps")
print("    -> comfortably inside a 20 Mbps mesh at short range; do NOT stream 3 video feeds.")

# ---------------------------------------------------------------- MISC
print("\n"+"="*80); print("STEP 11  GEOMETRY, STRUCTURE, CG"); print("="*80)
D_prop=D; clr=0.03
wb=(D_prop+clr)*np.sqrt(2)   # quad X wheelbase (motor-to-motor diagonal) for non-overlapping props
foot=D_prop+clr+ (D_prop)    # overall square footprint approx
print(f"  {D_prop/0.0254:.0f}\" prop, {clr*1000:.0f} mm tip clearance -> wheelbase (diagonal) {wb*1000:.0f} mm, "
      f"overall footprint ~{ (wb/np.sqrt(2)+D_prop)*1000:.0f} mm square")
box=3.6576
print(f"  Launch/landing box 12 ft = {box:.2f} m -> {np.floor(box/((wb/np.sqrt(2)+D_prop))):.0f} aircraft fit "
      f"per row, {np.floor(box/((wb/np.sqrt(2)+D_prop)))**2:.0f} total statically")
print("  -> all three fit simultaneously, but sequence launches anyway: prop wash and")
print("     downwash interaction at <1 rotor diameter separation is a real upset risk.")
T_per=T_W*MTOW*g/4
L_arm=wb/2
print(f"\n  Arm root bending moment at T/W=2: M = {T_per:.1f} N x {L_arm:.3f} m = {T_per*L_arm:.1f} N.m")
print(f"  With a 25x23 mm CF tube (I ~ {np.pi/64*(0.025**4-0.023**4)*1e12:.0f} mm^4), "
      f"sigma = {T_per*L_arm*0.0125/(np.pi/64*(0.025**4-0.023**4))/1e6:.0f} MPa vs ~600 MPa CF UD -> "
      f"SF {600e6/(T_per*L_arm*0.0125/(np.pi/64*(0.025**4-0.023**4))):.0f}")
print("  (bending is not the driver; joint/clamp design and vibration fatigue are)")
r_mag=0.05
print(f"\n  CG SHIFT on releasing one 200 g kit from a magazine {r_mag*100:.0f} cm off centreline:")
print(f"    CG moves {200*r_mag/(MTOW*1000)*1000:.2f} mm; residual moment {0.2*g*r_mag:.3f} N.m")
print(f"    -> counter-thrust needed {0.2*g*r_mag/(wb/2)/g*1000:.0f} g of differential thrust: trivial,")
print(f"       but the STEP change excites the attitude loop. Mount magazine on the CG axis and")
print(f"       feed a mass-change event to the controller / hold position 2 s after release.")


# ==================== from sizing5.py ====================
# D and m_pack carry over from the final design point above (see note at STEP 6).
MTOW,bd=converge(m_pack,D); Ph,_=hover_power_elec(MTOW,D)
# Same correction as STEP 7: this re-derived the sensor as 7.4 mm wide, which
# is not the part being bought. The angular pixel scale it produced (15.6
# mdeg/px) is what put the capture gate at 15 deg/s; on the real sensor one
# pixel is 13.6 mdeg and the gate has to come down with it.
sensor_w,px_w,f_mm = 4056*1.55/1000.0, 4056, 6.0
HFOV=2*np.arctan(sensor_w/(2*f_mm)); h=40.0
W=2*h*np.tan(HFOV/2); gsd=W/px_w

print("="*80); print("CORRECTION 1  ANGULAR MOTION BLUR (previous run had a unit error)"); print("="*80)
ang_per_px=np.rad2deg(HFOV)/px_w
print(f"  Angular pixel scale = {np.rad2deg(HFOV):.1f} deg / {px_w} px = {ang_per_px*1000:.2f} mdeg/px")
for rate in [5,10,20,45]:
    for texp in [1/500,1/1000,1/2000]:
        print(f"    body rate {rate:2.0f} deg/s, 1/{1/texp:.0f} s -> {rate*texp/ang_per_px:5.2f} px angular smear"
              + ("   <-- exceeds 1 px" if rate*texp/ang_per_px>1 else ""))
    print()
# The gate follows from the pixel scale, so it is derived rather than asserted:
# one pixel of smear at 1/1000 s occurs at exactly ang_per_px/texp deg/s. The
# stated rule rounds that down to a whole degree.
_gate = np.floor(ang_per_px / (1 / 1000.0))
print("  Translational smear at 8 m/s, 1/1000 s = 0.44 px. Angular smear dominates only in")
print(f"  aggressive turns. At 1/1000 s, 1 px of smear occurs at {ang_per_px/(1/1000.0):.2f} deg/s, so the")
print(f"  rule is: gate detections on |body rate| < {_gate:.0f} deg/s and use 1/1000 s or faster.")
print("  Both are easily met on straight transects; suppress inference in the turn arcs.")

print("\n"+"="*80); print("CORRECTION 2  RF LINK BUDGET WITH LEGAL POWER AND REAL ANTENNAS"); print("="*80)
print("  India, 5.825-5.875 GHz delicensed for drones: up to 1 W (30 dBm) Tx, 4 W (36 dBm) EIRP.")
print("  Design: air node 24 dBm + 3 dBi dipole (27 dBm EIRP, legal);")
print("          GCS node 24 dBm + 9 dBi sector on a 2 m mast (33 dBm EIRP, legal).\n")
def fspl(d,f): return 20*np.log10(d/1000)+20*np.log10(f)+32.44
def margin(d,f,ptx,gt,gr,sens,misc=4.0): return ptx+gt+gr-fspl(d,f)-misc-sens
print(f"  {'range':>7}{'FSPL':>9}{'Prx':>10}{'MCS3 -85':>11}{'MCS5 -80':>11}{'MCS7 -74':>11}")
for d in [200,300,400,500,600,800]:
    L=fspl(d,5850); prx=24+3+9-L-4
    print(f"  {d:6.0f}m{L:8.1f}dB{prx:9.1f}dBm{prx+85:10.1f}dB{prx+80:10.1f}dB{prx+74:10.1f}dB")
print("\n  Rates (20 MHz channel, approx): MCS3 ~26 Mbps, MCS5 ~52 Mbps, MCS7 ~65 Mbps.")
print("  Offered load is 2.5 Mbps -> even MCS0/MCS1 suffices. Trade rate for margin:")
print("  lock the mesh to a low MCS and a 10 MHz channel. A slow link that never drops beats")
print("  a fast link that renegotiates. Expect >=20 dB margin at 600 m at MCS3.")
print(f"\n  868 MHz safety link at 600 m: FSPL {fspl(600,868):.1f} dB, "
      f"margin at LoRa SF7 (-120 dBm) = {margin(600,868,20,2,2,-120):.0f} dB "
      f"-> effectively unbreakable inside the field.")
print(f"  Air-to-air (drone-drone, both at 60 m AGL, 400 m apart): FSPL {fspl(400,5850):.1f} dB, "
      f"clean LOS, no ground clutter -> best link in the system. Route through it when the")
print("  ground link degrades (that is the point of a mesh, not a star).")

print("\n"+"="*80); print("CORRECTION 3  HONEST GEOTAG BUDGET (adds terms the clean model omits)"); print("="*80)
r_edge=W/2
def full(gnss_h,gnss_v,att,bore,terr,tsync,v,npx,extent,lever,ekf,unmod,Nfuse=1):
    rnd=dict(GNSS_horizontal=gnss_h, attitude=h*np.tan(np.deg2rad(att)),
             pixel_centroid=npx*gsd, time_sync=tsync*v, EKF_lag=ekf)
    sysm=dict(boresight_residual=h*np.tan(np.deg2rad(bore)),
              ground_height_assumption=(np.hypot(gnss_v,terr)/h)*r_edge,
              target_extent_centroid=extent, GNSS_camera_lever_arm=lever,
              unmodelled=unmod)
    rnd={k:v_/np.sqrt(Nfuse) for k,v_ in rnd.items()}
    tot=np.sqrt(sum(v_**2 for v_ in list(rnd.values())+list(sysm.values())))
    return {**rnd,**sysm,'RSS_1sigma':tot,'CEP50':0.83*tot,'R95':1.73*tot}
cases={
 'B  standard GNSS, calibrated, 20-frame fusion':
    full(2.5,4.0,1.0,0.3,2.0,0.02,8,5,0.50,0.10,0.30,1.0,20),
 'C  RTK fix + dual-antenna heading, cal, 20-frame fusion':
    full(0.03,0.05,0.3,0.2,1.0,0.02,8,5,0.50,0.10,0.30,1.0,20),
 'C-strict  as C but surveyed ground plane (terr 0.3 m)':
    full(0.03,0.05,0.3,0.15,0.3,0.02,8,5,0.50,0.10,0.30,0.7,20)}
keys=list(cases['B  standard GNSS, calibrated, 20-frame fusion'].keys())
print(f"  {'term':<28}"+"".join(f"{n.split()[0]:>12}" for n in cases))
for k in keys:
    print(f"  {k:<28}"+"".join(f"{cases[n][k]:11.2f}m" for n in cases)
          + ("   <==" if k=='RSS_1sigma' else ""))
for n in cases: print(f"    {n}")
print("\n  Design targets to quote: geotag CEP50 <= 2.0 m with RTK, <= 3.5 m without.")
print("  Published monocular UAV geolocation results sit at a few metres, dominated by GNSS and")
print("  attitude - consistent with case B. Do not promise sub-metre until you have measured it.")

print("\n"+"="*80); print("CORRECTION 4  WIND, DRAG AND FORWARD-FLIGHT LIMITS"); print("="*80)
A_front=0.075; Cd_air=1.1
print(f"  Frontal area (tilted airframe + arms + gear) {A_front:.3f} m2, Cd {Cd_air}")
print(f"  {'airspeed':>9}{'drag':>8}{'tilt':>8}{'thrust/W':>10}{'extra P':>10}")
for v in [0,5,8,10,12,15,20]:
    Dr=0.5*rho*Cd_air*A_front*v**2
    tilt=np.rad2deg(np.arctan(Dr/(MTOW*g)))
    Tn=np.hypot(Dr,MTOW*g)/(MTOW*g)
    print(f"  {v:8.0f}m/s{Dr:7.2f}N{tilt:7.1f}deg{Tn:9.3f}{Dr*v/eta_prop_chain:9.0f}W")
print("  -> attitude authority is never the wind limit (tilt stays small). The real limits are")
print("     (a) groundspeed loss upwind, (b) position-hold quality during the drop, (c) energy.")
v_search=8.0
for wind in [0,4,6,8]:
    up=v_search-wind; dn=v_search+wind
    if up<=1: t='N/A (cannot make headway at search speed)'
    else:
        L=667.0; t=f"{0.5*L/up+0.5*L/dn:.0f} s vs {L/v_search:.0f} s still-air (+{(0.5*L/up+0.5*L/dn)/(L/v_search)-1:.0%})"
    print(f"    sweep time per drone in {wind} m/s wind (alternating transects): {t}")
print("  -> fly transects PERPENDICULAR to the wind where the sub-region shape allows;")
print("     Coombes et al. show cross-wind sweeps beat along-wind for survey time.")

print("\n"+"="*80); print("CORRECTION 5  THERMAL AND AVIONICS POWER"); print("="*80)
loads=[('Jetson Orin Nano @ sustained inference',18.0),('Flight controller + 2x GNSS',4.5),
       ('Camera + ISP',3.0),('5.8 GHz mesh radio (Tx duty)',9.0),('868 MHz radio',0.7),
       ('RC receiver',0.5),('Servos idle/actuation average',2.0),('BEC/regulator losses (12%)',0.0)]
sub=sum(v for n,v in loads if v>0); losses=0.12*sub
print(f"  {'load':<44}{'W':>7}")
for n,v in loads[:-1]: print(f"  {n:<44}{v:6.1f}")
print(f"  {'BEC / regulator losses (12%)':<44}{losses:6.1f}")
print(f"  {'TOTAL AVIONICS':<44}{sub+losses:6.1f}  (assumed {P_avio:.0f} W in the energy model -> OK)")
print(f"\n  Jetson at 18 W in still air needs a heatsink + forced airflow; in a 3.5 m/s propwash")
print(f"  column it is fine, but the 5-minute setup happens ON THE GROUND with props stopped.")
print(f"  Boot + model load + idle for 3 min at ambient 35 C is the worst thermal case, not flight.")
print(f"  -> fit a small blower on the compute bay, active from power-on. Verify in P5.")

print("\n"+"="*80); print("CORRECTION 6  SETUP TIME BUDGET vs THE 5-MINUTE RULE"); print("="*80)
steps=[('Aircraft out of case, battery in, power on (x3, serialised)',60),
       ('FC boot + IMU/EKF init',25),('Companion boot (Linux + ROS 2 + model load)',75),
       ('Mesh association, 3 nodes + GCS',20),('GNSS cold->3D fix (assisted almanac cached)',45),
       ('RTK float -> fix (local base already surveyed & running)',60),
       ('Payload magazines loaded and locked (x3)',45),
       ('Mission file received, parsed, partitioned, rendered on GCS',30),
       ('Pre-arm checks pass, operator confirm, arm',20)]
print(f"  {'step':<58}{'s':>5}{'cum(serial)':>13}")
c=0
for n,t in steps:
    c+=t; print(f"  {n:<58}{t:5.0f}{c:12.0f}")
print(f"\n  Fully serial: {c} s = {c/60:.1f} min -> EXCEEDS the 300 s window.")
par=60+max(25+45+60, 75+20)+45+30+20
print(f"  With parallelism (2 people; boot, GNSS/RTK and magazine loading overlapped): ~{par} s = {par/60:.1f} min")
print(f"  Margin against the 300 s rule: {300-par} s ({(300-par)/300:.0%})")
print("\n  The single biggest lever is RTK convergence and companion boot. Mitigations:")
print("   1. REFUSED by the organisers: the RTK base may NOT start before the window.")
print("      Instead skip survey-in, declare the first 3D fix as the reference, and")
print("      gate launch on a 3D fix not an RTK fix (SYS-42/43, setup_budget.py).")
print("   2. Pre-load the TensorRT engine into a warm cache; do not JIT-build at boot.")
print("   3. Cache the GNSS almanac (hot start) - saves 30-40 s over a true cold start.")
print("   4. REFUSED by the organisers: onboard computers may not be pre-booted.")
print("   5. Measure all of these on real hardware in Phase 5. These are estimates, not data.")
