%% sim_pack_sag.m -- dynamic pack voltage over the RescueSwarm mission
%
% WHY THIS EXISTS, AND WHY IT IS NOT PYTHON.
% The Python model treats the pack statically: one DC-IR figure applied to a
% peak current, giving "4.6 V of sag". That is enough to size a pack and not
% enough to set a failsafe, because it says nothing about WHEN in the mission
% the aircraft is closest to the floor, or how much of the dip is the
% instantaneous ohmic drop versus the slower diffusion term that persists after
% the current goes away. Those are dynamics, and dynamics is what this tool is
% for. Everything static stays in the Python model, which the document already
% asserts against -- this deliberately does not recompute any of it.
%
% MODEL. Second-order Thevenin equivalent circuit per cell:
%
%     v = OCV(z) - i*R0 - v1 - v2
%     dv1/dt = -v1/(R1*C1) + i/C1        (fast, seconds)
%     dv2/dt = -v2/(R2*C2) + i/C2        (slow, minutes)
%     dz/dt  = -i/(3600*Q)
%
% PARAMETERS are Molicel P45B where published, and typical high-drain 21700
% values where not. R0 is set so the peak sag matches the 4.6 V the proposal
% assumes, which makes this a consistency check on that assumption rather than
% an independent measurement of it. P2 replaces R0 with a measured value.
%
% Run:  matlab -batch "cd matlab; run_all('sim')"
% Emits: docs/proposal/figures/fig-sag.pdf
%        matlab/data/pack_sag_results.json

function sim_pack_sag()
close all;

here = fileparts(mfilename('fullpath'));
J = rs_model();
prof = struct(); prof.S = J.primitives.S_cells; prof.P = J.primitives.P_par;
prof.Ah = J.derived.Ah_pack; prof.V_nom = J.primitives.V_nom;
prof.V_min = J.primitives.V_min; prof.DOD = J.primitives.DOD;
prof.I_max = J.derived.I_max_A;
prof.segs = J.mission_segments;

S = prof.S; P = prof.P;                 % 6S3P
Qcell = prof.Ah / P;                    % Ah per cell
Vnom = prof.V_nom; Vmin = prof.V_min;

%% -- cell parameters -----------------------------------------------------
% R0 chosen so pack sag at the design peak equals the 4.6 V the proposal
% assumes: R0_pack = 4.6 / I_peak, and R0_cell = R0_pack * P / S.
R0 = (4.6 / prof.I_max) * P / S;        % ohm per cell
R1 = 0.006;  C1 = 900;                  % fast RC, ~5 s
R2 = 0.010;  C2 = 9000;                 % slow RC, ~90 s

% Open-circuit voltage of an NMC 21700 against state of charge.
zt  = [0 .05 .10 .20 .30 .40 .50 .60 .70 .80 .90 .95 1.0];
ocv = [3.00 3.30 3.45 3.55 3.63 3.70 3.76 3.83 3.91 3.99 4.08 4.14 4.20];
OCV = @(z) interp1(zt, ocv, min(max(z,0),1), 'pchip');

%% -- build the current profile -------------------------------------------
dt = 0.05;
t = []; i_pack = [];
for k = 1:numel(prof.segs)
    dur = prof.segs(k).duration_s;  W = prof.segs(k).power_W;
    n = max(1, round(dur/dt));
    t = [t, numel(t)*dt + (0:n-1)*dt];               %#ok<AGROW>
    i_pack = [i_pack, repmat(W/Vnom, 1, n)];         %#ok<AGROW>
end
t = (0:numel(i_pack)-1)*dt;

% A gust-recovery transient at T/W 2.0, two seconds, during the sweep. This is
% the case the static calculation says breaches the floor.
tg = 300; ng = round(2/dt); kg = round(tg/dt);
i_pack(kg:kg+ng-1) = prof.I_max;

% A second one late, on a depleted pack -- the worst case that matters.
tg2 = 430; kg2 = round(tg2/dt);
i_pack(kg2:kg2+ng-1) = prof.I_max;

%% -- integrate -----------------------------------------------------------
z = 1.0; v1 = 0; v2 = 0;
N = numel(t);
v_pack = zeros(1,N); z_hist = zeros(1,N);
for k = 1:N
    ic = i_pack(k)/P;                                % per cell
    v1 = v1 + dt*(-v1/(R1*C1) + ic/C1);
    v2 = v2 + dt*(-v2/(R2*C2) + ic/C2);
    vc = OCV(z) - ic*R0 - v1 - v2;
    v_pack(k) = S*vc;
    z_hist(k) = z;
    z = z - dt*ic/(3600*Qcell);
end

%% -- results -------------------------------------------------------------
[vmin_sim, kmin] = min(v_pack);
sag_peak = S*(OCV(z_hist(kg)) - v_pack(kg)/S);
res = struct('v_min_V', vmin_sim, 't_at_min_s', t(kmin), ...
             'soc_end_pct', 100*z, 'floor_V', Vmin, ...
             'margin_V', vmin_sim - Vmin, ...
             'sag_at_first_gust_V', sag_peak, ...
             'assumed_static_sag_V', 4.6);
fprintf('\n  minimum pack voltage   %.2f V at t = %.0f s\n', vmin_sim, t(kmin));
fprintf('  failsafe floor         %.2f V\n', Vmin);
fprintf('  margin                 %+.2f V\n', vmin_sim - Vmin);
fprintf('  SOC at landing         %.1f %%\n', 100*z);
fprintf('  sag at first gust      %.2f V (static model assumes 4.60)\n', sag_peak);

fid = fopen(fullfile(fileparts(here),'data','pack_sag_results.json'),'w');
fwrite(fid, jsonencode(res, 'PrettyPrint', true)); fclose(fid);

%% -- figure --------------------------------------------------------------
BLUE = [0 0.447 0.698]; ORANGE = [0.902 0.624 0]; RED = [0.835 0.369 0];
GREY = [0.5 0.5 0.5];

f = figure('Units','inches','Position',[0 0 7.16 2.6],'Color','w');
tl = tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

nexttile; hold on; box off; grid on; set(gca,'GridAlpha',0.25,'FontSize',8);
plot(t, v_pack, 'Color', BLUE, 'LineWidth', 1.3);
yline(Vmin, '--', 'Color', RED, 'LineWidth', 1);
text(8, Vmin+0.35, sprintf('failsafe floor %.1f V', Vmin), ...
     'Color', RED, 'FontSize', 7);
plot(t(kmin), vmin_sim, 'o', 'Color', ORANGE, 'MarkerFaceColor', ORANGE, 'MarkerSize', 5);
text(t(kmin)-150, vmin_sim-0.55, sprintf('min %.2f V', vmin_sim), ...
     'Color', ORANGE, 'FontSize', 7);
xlabel('Mission time (s)','FontSize',8);
ylabel('Pack voltage (V)','FontSize',8);
title('(a) Voltage under the mission profile','FontSize',8.5,'FontWeight','normal');
xlim([0 t(end)]); ylim([16 26]);

nexttile; hold on; box off; grid on; set(gca,'GridAlpha',0.25,'FontSize',8);
yyaxis left
plot(t, i_pack, 'Color', GREY, 'LineWidth', 0.9);
ylabel('Pack current (A)','FontSize',8); ylim([0 130]);
set(gca,'YColor',GREY);
yyaxis right
plot(t, 100*z_hist, 'Color', BLUE, 'LineWidth', 1.3);
yline(100*(1-prof.DOD), '--', 'Color', RED, 'LineWidth', 1);
text(8, 100*(1-prof.DOD)+3, sprintf('%.0f%% DoD limit', 100*prof.DOD), ...
     'Color', RED, 'FontSize', 7);
ylabel('State of charge (%)','FontSize',8); ylim([0 105]);
set(gca,'YColor',BLUE);
xlabel('Mission time (s)','FontSize',8);
title('(b) Current draw and state of charge','FontSize',8.5,'FontWeight','normal');
xlim([0 t(end)]);

rs_save(f, 'fig-sag.pdf');
end
