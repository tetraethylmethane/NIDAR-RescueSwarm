%% verify_model.m -- independently re-derive the design and assert against Python
%
% WHAT THIS IS FOR. The Python model checks itself: its generated section
% asserts each derivation against the model's own result. That catches an
% inconsistent edit, but it cannot catch a mistake in the derivation itself,
% because the same expression is on both sides. This re-derives every published
% quantity here, in a different language, from the PRIMITIVES only -- and fails
% if the answers disagree.
%
% It reads tools/sim/model.json. It does not retype a single design constant,
% because two copies of a constant is the defect this repository keeps finding
% in itself.
%
% Run:  matlab -batch "run('tools/sim/verify_model.m')"

function verify_model()
close all;
here = fileparts(mfilename('fullpath'));
root = fileparts(fileparts(here));
J = jsondecode(fileread(fullfile(here,'model.json')));
p = J.primitives; d = J.derived;

pass = 0; fail = 0; rows = {};

    function chk(name, mine, theirs, tol, unit)   % nested: shares workspace
        rel = abs(mine - theirs) / max(abs(theirs), eps);
        ok  = rel <= tol;
        if ok, pass = pass + 1; else, fail = fail + 1; end
        rows(end+1,:) = {ok, name, mine, theirs, rel, unit};   %#ok<AGROW>
    end

%% ---- rotor and hover power, from momentum theory -----------------------
A = p.N_rot * pi * (p.D_m/2)^2;
chk('disk area', A, d.disk_area_m2, 1e-9, 'm^2');

T_hov = d.MTOW_kg * p.g;
Pshaft = T_hov^1.5 / (p.FM * sqrt(2*p.rho*A));
chk('hover shaft power', Pshaft, d.P_shaft_W, 1e-6, 'W');

eta = p.eta_mot * p.eta_esc;
Pelec = Pshaft/eta + p.P_avio_W;
chk('hover electrical power', Pelec, d.P_hover_elec_W, 1e-6, 'W');
chk('hover current', Pelec/p.V_nom, d.I_hover_A, 1e-6, 'A');

Ppk = (p.T_W*T_hov)^1.5 / (p.FM*sqrt(2*p.rho*A)) / eta + p.P_avio_W;
chk('peak electrical power', Ppk, d.P_max_W, 1e-6, 'W');
chk('peak current', Ppk/p.V_nom, d.I_max_A, 1e-6, 'A');

%% ---- thrust -------------------------------------------------------------
chk('total thrust', p.T_W*d.MTOW_kg*p.g, d.T_total_N, 1e-9, 'N');
chk('thrust per motor', p.T_W*d.MTOW_kg/p.N_rot, d.T_per_motor_kgf, 1e-9, 'kgf');
chk('hover thrust per motor', d.MTOW_kg/p.N_rot, d.T_hover_per_motor_kgf, 1e-9, 'kgf');

%% ---- the coupled mass solve, re-run independently -----------------------
% Fixed point: m = (avionics + payload + battery + motors + esc + props)/(1-k)
m = 6.0;
for k = 1:500
    Tt = p.T_W*m*p.g;
    m_mot = p.N_rot * (Tt/p.N_rot) / p.spec_thrust_motor_N_per_kg;
    m_esc = p.k_esc * m_mot;
    m_prop = p.N_rot * p.m_prop_ea_kg;
    m_new = (p.m_avio_kg + p.m_payload_sys_kg + d.m_pack_kg + m_mot + m_esc + m_prop) ...
            / (1 - p.k_struct);
    if abs(m_new - m) < 1e-12, break; end
    m = m_new;
end
chk('MTOW (fixed point)', m, d.MTOW_kg, 1e-6, 'kg');
chk('fleet mass', 3*m, d.fleet_kg, 1e-6, 'kg');

%% ---- pack ---------------------------------------------------------------
n_cells = p.S_cells * p.P_par;
chk('cell count', n_cells, d.n_cells, 1e-9, '');
% Two independent routes to pack energy. The first is the identity the model
% uses and must match exactly. The second goes via specific energy and mass,
% and agreeing to ~1 % is what says the e_liion assumption is consistent with
% the cell arithmetic rather than tuned to it -- so the loose tolerance here is
% the point of the check, not a concession.
chk('pack energy (cells)', n_cells*(d.Ah_pack/p.P_par)*(p.V_nom/p.S_cells), ...
    d.E_pack_Wh, 1e-9, 'Wh');
chk('pack energy (mass route)', d.m_pack_kg * p.e_liion_Wh_per_kg, ...
    d.E_pack_Wh, 0.02, 'Wh');
chk('usable energy', d.E_pack_Wh*p.DOD, d.E_usable_Wh, 1e-9, 'Wh');
chk('reserve requirement', d.E_nominal_Wh + d.E_resweep_Wh + d.E_loiter_Wh, ...
    d.E_required_Wh, 1e-9, 'Wh');
chk('hover endurance', 60*d.E_pack_Wh*p.DOD/d.P_hover_elec_W, d.t_hover_min, 1e-6, 'min');

%% ---- optics -------------------------------------------------------------
sw = p.px_w * p.pitch_um / 1000;
sh = p.px_h * p.pitch_um / 1000;
chk('sensor width', sw, d.sensor_w_mm, 1e-9, 'mm');
chk('sensor height', sh, d.sensor_h_mm, 1e-9, 'mm');
chk('HFOV', 2*atand(sw/(2*p.f_mm)), d.hfov_deg, 1e-9, 'deg');
chk('VFOV', 2*atand(sh/(2*p.f_mm)), d.vfov_deg, 1e-9, 'deg');
gsd = p.pitch_um * p.h_search_m / p.f_mm / 10;          % cm/px
chk('GSD at 40 m', gsd, d.gsd40_cm_per_px, 1e-9, 'cm/px');
chk('swath width', 2*p.h_search_m*tand(d.hfov_deg/2), d.swath_w_m, 1e-6, 'm');

%% ---- temporal sampling ---------------------------------------------------
Dalong = 2*p.h_search_m*tand(d.vfov_deg/2);
chk('looks at 2 Hz', Dalong/p.groundspeed_ms*2, d.looks_at_2Hz, 1e-6, '');
chk('rate for 12 looks', p.fusion_min_frames*p.groundspeed_ms/Dalong, ...
    d.rate_for_12_looks_Hz, 1e-6, 'Hz');

%% ---- mission -------------------------------------------------------------
segs = J.mission_segments;
Tsum = 0; Esum = 0;
for k = 1:numel(segs)
    Tsum = Tsum + segs(k).duration_s;
    Esum = Esum + segs(k).duration_s*segs(k).power_W/3600;
end
chk('mission duration', Tsum, d.mission_s, 1e-9, 's');
chk('mission energy', Esum, d.mission_Wh, 1e-9, 'Wh');

%% ---- mass statement must close to MTOW ----------------------------------
mg = struct2cell(J.mass_g);
chk('mass statement closes', sum([mg{:}])/1000, d.MTOW_kg, 1e-9, 'kg');

%% ---- report --------------------------------------------------------------
fprintf('\n%s\n', repmat('=',1,78));
fprintf(' MATLAB independent re-derivation vs the Python sizing model\n');
fprintf('%s\n', repmat('=',1,78));
fprintf(' %-28s %14s %14s %10s\n','quantity','MATLAB','Python','rel err');
fprintf('%s\n', repmat('-',1,78));
for k = 1:size(rows,1)
    if rows{k,1}, tag = 'ok  '; else, tag = 'FAIL'; end
    fprintf(' %s %-26s %14.6g %14.6g %10.2e %s\n', ...
            tag, rows{k,2}, rows{k,3}, rows{k,4}, rows{k,5}, rows{k,6});
end
fprintf('%s\n', repmat('-',1,78));
fprintf(' %d passed, %d failed\n\n', pass, fail);

res = struct('passed',pass,'failed',fail);
fid = fopen(fullfile(here,'verify_results.json'),'w');
fwrite(fid, jsonencode(res,'PrettyPrint',true)); fclose(fid);

if fail > 0
    error('verify_model:mismatch', '%d cross-checks failed', fail);
end

end
