function sim_receivers()
%SIM_RECEIVERS  What each GNSS class buys, and where the budget actually breaks.
%
% WHY THIS EXISTS SEPARATELY FROM SIM_GEOBUDGET.
% sim_geobudget answers "what does the receiver class cost in metres". This
% answers the question that keeps being asked in review: why not the cheaper
% receiver -- GPS on its own, or NavIC, which is Indian and costs a fifth of
% the RTK unit. That is a different question, because it is not about which
% class is best but about which classes still CLEAR the requirement, and by
% how much.
%
% THE RESULT THAT MATTERS is panel (b). The delivery requirement is 5 m at
% CEP95 and the non-GNSS part of the budget is 0.88 m, so the requirement
% survives a GNSS term of about 2.75 m. That single number decides the whole
% question: SBAS and multi-band clear it comfortably, GPS alone is marginal,
% and NavIC's published SPS accuracy does not clear it at all. Nothing about
% the receiver's price enters the argument.
%
% NavIC IS NOT AN ALTERNATIVE TO RTK, which is the confusion this figure is
% meant to end. NavIC is a constellation; RTK is a correction technique
% applied on top of a constellation. The comparison here is between
% AUGMENTATION classes, and NavIC appears at its standalone accuracy because
% that is how it would actually be flown.
%
% Run:  matlab -batch "cd matlab; run_all('sim')"
% Emits: docs/proposal/figures/fig-receivers.pdf
%        matlab/data/receiver_results.json

close all;
here = fileparts(mfilename('fullpath'));
J = rs_model(); C = rs_style();

T   = J.geotag_terms_m;
sig = arrayfun(@(t) t.sigma_m, T)';
base_var = sum(sig.^2);                 % everything the receiver cannot touch
REQ = J.delivery_requirement_m;

RC     = J.receiver_classes_m;
rnames = arrayfun(@(t) string(t.name), RC);
rsig   = arrayfun(@(t) t.sigma_m,      RC);
n      = numel(rnames);

N = 200000;
rng(20260831, 'twister');               % fixed seed: the figure must reproduce

%% -- sample ---------------------------------------------------------------
% Same convention as sim_geobudget: every quoted term is a two-axis RSS, so
% the per-axis sigma is term/sqrt(2). Getting this wrong inflates by sqrt(2),
% which is exactly the error that script caught in itself.
bx = zeros(N,1); by = zeros(N,1);
for k = 1:numel(sig)
    s_axis = sig(k)/sqrt(2);
    bx = bx + s_axis*randn(N,1);
    by = by + s_axis*randn(N,1);
end

R = cell(1,n); res = struct();
for i = 1:n
    g = rsig(i);
    r = hypot(bx + (g/sqrt(2))*randn(N,1), by + (g/sqrt(2))*randn(N,1));
    R{i} = r;
    fn = matlab.lang.makeValidName(rnames(i));
    res.(fn).name  = rnames(i);
    res.(fn).sigma = g;
    res.(fn).rss   = sqrt(base_var + g^2);
    res.(fn).cep50 = median(r);
    res.(fn).cep95 = quantile(r, 0.95);
    res.(fn).pass  = res.(fn).cep95 <= REQ;
end

% The GNSS term at which CEP95 exactly reaches the requirement. This is the
% number the whole trade turns on.
g_break = sqrt((REQ/1.7308)^2 - base_var);

%% -- the fleet as actually configured -------------------------------------
% One aircraft on RTK, two on SBAS. The fleet does not have a single accuracy;
% it has one instrumented aircraft and two that fly the mission.
F = J.fleet_receivers_m;
fprintf('\n  %-26s %7s %8s %8s %8s\n','receiver class','sigma','RSS','CEP50','CEP95');
fprintf('  %s\n', repmat('-',1,62));
for i = 1:n
    fn = matlab.lang.makeValidName(rnames(i));
    verdict = "clears"; if ~res.(fn).pass, verdict = "FAILS"; end
    fprintf('  %-26s %6.2fm %7.2fm %7.2fm %7.2fm  %s\n', rnames(i), rsig(i), ...
            res.(fn).rss, res.(fn).cep50, res.(fn).cep95, verdict);
end
fprintf('\n  non-GNSS budget            %6.2f m\n', sqrt(base_var));
fprintf('  requirement                %6.2f m at CEP95\n', REQ);
fprintf('  breaks at a GNSS term of   %6.2f m\n\n', g_break);
for i = 1:numel(F)
    fprintf('  fleet: %-28s %d aircraft at %.2f m\n', F(i).name, F(i).count, F(i).sigma_m);
end
fprintf('\n');

% Guard the sampling convention against the analytic Rayleigh result.
for i = 1:n
    fn = matlab.lang.makeValidName(rnames(i));
    expect = 0.8326*res.(fn).rss;
    if abs(res.(fn).cep50 - expect)/expect > 0.02
        error('sim_receivers:convention', ...
              '%s: sampled CEP50 %.3f m vs analytic %.3f m.', ...
              rnames(i), res.(fn).cep50, expect);
    end
end

fid = fopen(fullfile(fileparts(here),'data','receiver_results.json'),'w');
fwrite(fid, jsonencode(res,'PrettyPrint',true)); fclose(fid);

%% -- figure ---------------------------------------------------------------
cc = {C.blue, C.green, C.grey, C.orange, C.red};

f = figure('Units','inches','Position',[0 0 C.FULL 2.7],'Color','w');
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

% (a) where each class lands
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);
for i = 1:n
    [fq, xq] = ecdf(R{i});
    plot(ax, xq, 100*fq, 'Color', cc{min(i,numel(cc))}, 'LineWidth', 1.5, ...
         'DisplayName', sprintf('%s (%.2f m)', rnames(i), rsig(i)));
end
xline(ax, REQ, '--', 'Color', C.red, 'LineWidth', 1.1, 'HandleVisibility','off');
text(ax, REQ-0.18, 30, sprintf('%.0f m requirement', REQ), 'Rotation', 90, ...
     'FontSize', C.fs_note, 'FontName','Times New Roman', 'Color', C.red);
yline(ax, 95, ':', 'Color', C.grey, 'LineWidth', 0.9, 'HandleVisibility','off');
text(ax, 6.6, 96.5, 'CEP95', 'FontSize', C.fs_note, ...
     'FontName','Times New Roman', 'Color', C.grey);
lg = legend(ax,'Location','southeast'); lg.Box='off';
lg.FontSize = 6.2; lg.FontName='Times New Roman';
xlim(ax,[0 8]); ylim(ax,[0 104]);
xlabel(ax,'Radial geolocation error (m)');
ylabel(ax,'Cumulative probability (%)');
title(ax,'(a) Where each receiver class lands');

% (b) the sensitivity that decides it
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);
gg = linspace(0, 6, 400);
plot(ax, gg, 1.7308*sqrt(base_var + gg.^2), '-', 'Color', C.blue, 'LineWidth', 1.6);
yline(ax, REQ, '--', 'Color', C.red, 'LineWidth', 1.1);
plot(ax, g_break, REQ, 'o', 'MarkerSize', 5, 'MarkerFaceColor', C.red, ...
     'MarkerEdgeColor','none');
text(ax, g_break+0.18, REQ-0.75, sprintf('breaks at %.2f m', g_break), ...
     'FontSize', C.fs_note, 'FontName','Times New Roman', 'Color', C.red);
for i = 1:n
    fn = matlab.lang.makeValidName(rnames(i));
    plot(ax, rsig(i), res.(fn).cep95, 's', 'MarkerSize', 5, ...
         'MarkerFaceColor', cc{min(i,numel(cc))}, 'MarkerEdgeColor','none');
end
% The markers are not labelled: panel (a) names all five with their sigmas and
% the colours carry across, so repeating the names here only collided them.
text(ax, 0.15, 10.1, sprintf(['everything except the receiver contributes ' ...
     '%.2f m;\nthat is the floor the curve starts from'], sqrt(base_var)), ...
     'FontSize', C.fs_note, 'FontName','Times New Roman', 'Color', C.grey);
xlim(ax,[0 6]); ylim(ax,[0 11]);
xlabel(ax,'GNSS horizontal error, 1\sigma (m)');
ylabel(ax,'Delivery CEP95 (m)');
title(ax,'(b) How good the receiver has to be');

rs_save(f, 'fig-receivers.pdf');
end
