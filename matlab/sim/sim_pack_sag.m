%% sim_pack_sag.m -- dynamic pack voltage over the RescueSwarm mission
%
% WHY THIS EXISTS, AND WHY IT IS NOT PYTHON.
% The Python model treats the pack statically: one DC-IR figure applied to a
% peak current. That is enough to size a pack and not enough to set a
% failsafe, because it says nothing about WHEN in the mission the aircraft is
% closest to the floor, or how much of the dip is the instantaneous ohmic drop
% versus the slower diffusion term that persists after the current goes away.
%
% WHICH PACK. The GenX 6S 16 Ah HV LiPo the aircraft actually flies, at the
% heavy end of its mass bracket, against the failsafe thresholds in params.py
% (all read from model.json's flight_pack block). Until 2026-10-30 this
% simulated the 6S3P Li-ion pack against an 18.0 V floor and showed the pack
% crossing it mid-mission; that pack is no longer in the design.
%
% MODEL. Second-order Thevenin equivalent circuit per cell, constant-power
% load (the ESCs draw more current as the voltage falls):
%
%     v = OCV(z) - i*R0 - v1 - v2,   i = P / v
%     dv1/dt = -v1/(R1*C1) + i/C1        (fast, seconds)
%     dv2/dt = -v2/(R2*C2) + i/C2        (slow, minutes)
%     dz/dt  = -i/(3600*Q)
%
% WHAT THE FAILSAFE SEES. BATT_FS_VOLTSRC = 1, so ArduPilot compares its
% sag-compensated voltage, v + i*R_est, against BATT_LOW_VOLT, and acts only
% after BATT_LOW_TIMER seconds below it. R_est is ArduPilot's own running
% estimate; this uses R0 alone, which under-compensates and is conservative.
%
% PARAMETERS are typical for a 16 Ah, 25 C LiHV pack including leads and
% connector, not measured. P2 replaces them with a loaded discharge test on
% the real pack, and that is when this becomes evidence rather than analysis.
%
% Run:  matlab -batch "cd matlab; run_all('sim')"
% Emits: docs/proposal/figures/fig-sag.pdf
%        matlab/data/pack_sag_results.json

function sim_pack_sag()
close all;

here = fileparts(mfilename('fullpath'));
J = rs_model();
fp = J.flight_pack;
S = fp.cells; Q = fp.capacity_Ah;
Vlow = fp.low_volt_V; Vcrt = fp.crt_volt_V;
reserve = fp.low_mah / (1000*Q);         % capacity failsafe, as a fraction

% Hover power scales as mass^1.5 at fixed rotor area. The sizing model's
% mission profile is at its own MTOW, so every segment, and the full-thrust
% peak, is scaled to the LiPo aircraft at its heaviest.
k = (fp.mass_worst_kg / J.derived.MTOW_kg)^1.5;
P_peak = k * J.derived.P_max_W;
segs = J.mission_segments;

%% -- cell parameters (assumed; P2 measures them) -------------------------
R0 = 0.0030;                            % ohm per cell, incl. leads/connector
R1 = 0.0010;  C1 = 5000;                % fast RC, ~5 s
R2 = 0.0015;  C2 = 60000;               % slow RC, ~90 s

% Open-circuit voltage of a LiHV cell against state of charge.
zt  = [0 .05 .10 .20 .30 .40 .50 .60 .70 .80 .90 .95 1.0];
ocv = [3.30 3.55 3.65 3.73 3.78 3.82 3.86 3.92 3.99 4.07 4.17 4.25 4.35];
OCV = @(z) interp1(zt, ocv, min(max(z,0),1), 'pchip');

%% -- build the power profile ---------------------------------------------
dt = 0.05;
p_pack = [];
for j = 1:numel(segs)
    n = max(1, round(segs(j).duration_s/dt));
    p_pack = [p_pack, repmat(k*segs(j).power_W, 1, n)];   %#ok<AGROW>
end
t = (0:numel(p_pack)-1)*dt;

% Two gust recoveries at full thrust, two seconds each: one mid-sweep, and one
% late on a partly drained pack, which is the worst case that matters.
ng = round(2/dt);
kg  = round(300/dt); p_pack(kg:kg+ng-1)   = P_peak;
kg2 = round(430/dt); p_pack(kg2:kg2+ng-1) = P_peak;

%% -- integrate -----------------------------------------------------------
z = 1.0; v1 = 0; v2 = 0; vc = OCV(1);
N = numel(t);
v_pack = zeros(1,N); v_comp = zeros(1,N); i_pack = zeros(1,N); z_hist = zeros(1,N);
for j = 1:N
    ic = p_pack(j) / (S*vc);                         % per cell, last voltage
    v1 = v1 + dt*(-v1/(R1*C1) + ic/C1);
    v2 = v2 + dt*(-v2/(R2*C2) + ic/C2);
    vc = OCV(z) - ic*R0 - v1 - v2;
    v_pack(j) = S*vc;
    v_comp(j) = S*(vc + ic*R0);
    i_pack(j) = ic;
    z_hist(j) = z;
    z = z - dt*ic/(3600*Q);
end

% Longest continuous run of the compensated voltage below BATT_LOW_VOLT.
run = 0; longest = 0;
for j = 1:N
    if v_comp(j) < Vlow, run = run + dt; else, run = 0; end
    longest = max(longest, run);
end

%% -- results -------------------------------------------------------------
[vmin_sim, kmin] = min(v_pack);
res = struct('pack', sprintf('%dS %g Ah LiHV', S, Q), ...
             'mass_kg', fp.mass_worst_kg, 'peak_current_A', max(i_pack), ...
             'v_min_V', vmin_sim, 't_at_min_s', t(kmin), ...
             'v_comp_min_V', min(v_comp), ...
             'low_volt_V', Vlow, 'crt_volt_V', Vcrt, ...
             'time_below_low_s', longest, 'low_timer_s', fp.low_timer_s, ...
             'failsafe_trips', longest >= fp.low_timer_s, ...
             'soc_end_pct', 100*z, 'soc_reserve_pct', 100*reserve, ...
             'sag_at_peak_V', S*OCV(z_hist(kmin)) - vmin_sim);
fprintf('\n  pack                    %s at %.2f kg\n', res.pack, res.mass_kg);
fprintf('  peak current            %.0f A\n', res.peak_current_A);
fprintf('  minimum raw voltage     %.2f V at t = %.0f s (sag %.2f V)\n', ...
        vmin_sim, t(kmin), res.sag_at_peak_V);
fprintf('  minimum compensated     %.2f V  (low %.1f V, critical %.1f V)\n', ...
        res.v_comp_min_V, Vlow, Vcrt);
fprintf('  longest dip below low   %.1f s  (timer %g s)\n', longest, fp.low_timer_s);
fprintf('  SOC at landing          %.1f %%  (capacity failsafe at %.0f %%)\n', ...
        res.soc_end_pct, res.soc_reserve_pct);

fid = fopen(fullfile(fileparts(here),'data','pack_sag_results.json'),'w');
fwrite(fid, jsonencode(res, 'PrettyPrint', true)); fclose(fid);

%% -- figure --------------------------------------------------------------
BLUE = [0 0.447 0.698]; ORANGE = [0.902 0.624 0]; RED = [0.835 0.369 0];
GREY = [0.5 0.5 0.5]; GREEN = [0 0.62 0.45];

f = figure('Units','inches','Position',[0 0 7.16 2.6],'Color','w');
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

nexttile; hold on; box off; grid on; set(gca,'GridAlpha',0.25,'FontSize',8);
h1 = plot(t, v_pack, 'Color', BLUE, 'LineWidth', 1.1);
h2 = plot(t, v_comp, 'Color', GREEN, 'LineWidth', 1.3);
yline(Vlow, '--', 'Color', RED, 'LineWidth', 1);
yline(Vcrt, ':',  'Color', RED, 'LineWidth', 1);
text(8, Vlow+0.3, sprintf('low battery, RTL %.1f V', Vlow), 'Color', RED, 'FontSize', 7);
text(8, Vcrt-0.35, sprintf('critical, land %.1f V', Vcrt), 'Color', RED, 'FontSize', 7);
plot(t(kmin), vmin_sim, 'o', 'Color', ORANGE, 'MarkerFaceColor', ORANGE, 'MarkerSize', 5);
text(t(kmin)-140, vmin_sim, sprintf('min %.2f V', vmin_sim), ...
     'Color', ORANGE, 'FontSize', 7);
legend([h1 h2], {'at the pack terminals', 'sag-compensated (failsafe input)'}, ...
       'Location', 'northeast', 'FontSize', 6.5, 'Box', 'off');
xlabel('Mission time (s)','FontSize',8);
ylabel('Pack voltage (V)','FontSize',8);
title('(a) Voltage under the mission profile','FontSize',8.5,'FontWeight','normal');
xlim([0 t(end)]); ylim([18 27]);

nexttile; hold on; box off; grid on; set(gca,'GridAlpha',0.25,'FontSize',8);
yyaxis left
plot(t, i_pack, 'Color', GREY, 'LineWidth', 0.9);
ylabel('Pack current (A)','FontSize',8); ylim([0 160]);
set(gca,'YColor',GREY);
yyaxis right
plot(t, 100*z_hist, 'Color', BLUE, 'LineWidth', 1.3);
yline(100*reserve, '--', 'Color', RED, 'LineWidth', 1);
text(8, 100*reserve+3, sprintf('%.0f%% capacity failsafe', 100*reserve), ...
     'Color', RED, 'FontSize', 7);
ylabel('State of charge (%)','FontSize',8); ylim([0 105]);
set(gca,'YColor',BLUE);
xlabel('Mission time (s)','FontSize',8);
title('(b) Current draw and state of charge','FontSize',8.5,'FontWeight','normal');
xlim([0 t(end)]);

rs_save(f, 'fig-sag.pdf');
end
