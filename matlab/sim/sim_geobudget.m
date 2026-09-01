function sim_geobudget()
%SIM_GEOBUDGET  Monte Carlo of survivor geolocation error by receiver class.
%
% WHY A SIMULATION RATHER THAN THE RSS.
% The proposal quotes a root-sum-square, which is a 1-sigma scalar. What a
% rescue coordinator needs is a radius that contains the survivor with stated
% confidence -- CEP50 and CEP95 -- and those come from the distribution, not
% from the RSS. Summing independent 2-D Gaussian terms gives a Rayleigh-like
% radial distribution whose quantiles are NOT simple multiples of the RSS, so
% they have to be sampled.
%
% WHAT IT SETTLES.
% Section IV-D calls RTK "a mission requirement rather than an optimisation".
% The case-C budget contains no GNSS position term at all, because with RTK it
% is ~0.01 m and was dropped as negligible. Putting a worse receiver back in
% shows what RTK actually buys against terms it cannot touch -- unmodelled
% error at 0.70 m and target centroid at 0.50 m, which together are 95 % of
% the variance.
%
% Run:  matlab -batch "cd matlab; run_all('sim')"
% Emits: docs/proposal/figures/fig-geobudget.pdf
%        matlab/data/geobudget_results.json

close all;
here = fileparts(mfilename('fullpath'));
J = rs_model(); C = rs_style();

% Read as name/value lists so the labels survive intact -- jsondecode would
% otherwise turn "target extent, centroid" into a MATLAB identifier and put
% that on the axis of a published figure.
T = J.geotag_terms_m;
names = arrayfun(@(t) string(t.name), T);
sig   = arrayfun(@(t) t.sigma_m,      T)';

RC = J.receiver_classes_m;
rnames = arrayfun(@(t) string(t.name), RC);
rsig   = arrayfun(@(t) t.sigma_m,      RC);

N = 200000;
rng(20260830, 'twister');          % fixed seed: the figure must reproduce

%% -- sample ---------------------------------------------------------------
% Each term is an independent 2-D error of the stated per-axis sigma. Radial
% error is the magnitude of their vector sum.
% CONVENTION. The sizing document quotes every term as an RSS 1-sigma over TWO
% axes, so per-axis sigma is term/sqrt(2). Sampling the quoted figure as a
% per-axis sigma inflates the result by sqrt(2) -- the first run of this script
% did exactly that and returned CEP50 = 1.04 m against the document's own
% SYS-12 requirement of 0.75 m. The assertion below now catches it.
base_x = zeros(N,1); base_y = zeros(N,1);
for k = 1:numel(sig)
    s_axis = sig(k)/sqrt(2);
    base_x = base_x + s_axis*randn(N,1);
    base_y = base_y + s_axis*randn(N,1);
end

res = struct();
R = cell(1, numel(rnames));
for i = 1:numel(rnames)
    g = rsig(i);
    x = base_x + (g/sqrt(2))*randn(N,1);
    y = base_y + (g/sqrt(2))*randn(N,1);
    r = hypot(x, y);
    R{i} = r;
    fn = matlab.lang.makeValidName(rnames(i));
    res.(fn).name  = rnames(i);
    res.(fn).cep50 = median(r);
    res.(fn).cep95 = quantile(r, 0.95);
    res.(fn).rss   = sqrt(sum(sig.^2) + g^2);
end

%% -- report ---------------------------------------------------------------
fprintf('\n  %-24s %8s %8s %8s\n','receiver','RSS','CEP50','CEP95');
fprintf('  %s\n', repmat('-',1,52));
for i = 1:numel(rnames)
    f = matlab.lang.makeValidName(rnames{i});
    fprintf('  %-24s %7.2fm %7.2fm %7.2fm\n', rnames{i}, ...
            res.(f).rss, res.(f).cep50, res.(f).cep95);
end
fprintf('\n');

% For a circular Gaussian with a 2-axis RSS of E, the radial miss is Rayleigh
% distributed and CEP50 = 0.8326*E exactly. If the sampling convention is ever
% wrong again, this fails rather than quietly publishing an inflated figure.
for i = 1:numel(rnames)
    fn = matlab.lang.makeValidName(rnames(i));
    expect = 0.8326*res.(fn).rss;
    if abs(res.(fn).cep50 - expect)/expect > 0.02
        error('sim_geobudget:convention', ...
              ['%s: sampled CEP50 %.3f m against analytic 0.8326*RSS = %.3f m. ' ...
               'The per-axis sigma convention is wrong.'], ...
              rnames(i), res.(fn).cep50, expect);
    end
end
fprintf('  CEP50 matches the analytic 0.8326*RSS for every class.\n\n');

fid = fopen(fullfile(fileparts(here),'data','geobudget_results.json'),'w');
fwrite(fid, jsonencode(res,'PrettyPrint',true)); fclose(fid);

%% -- figure ---------------------------------------------------------------
f = figure('Units','inches','Position',[0 0 C.FULL 2.6],'Color','w');
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

% (a) where the variance actually lives
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);
[sv, ord] = sort(sig, 'descend');
sn = names(ord);
share = 100*sv.^2/sum(sv.^2);
cols = [C.blue; C.orange; C.grey; C.light; C.light; C.light];
for k = 1:numel(sv)
    barh(ax, numel(sv)-k+1, share(k), 0.62, ...
         'FaceColor', cols(min(k,size(cols,1)),:), 'EdgeColor','none');
    text(ax, share(k)+1.5, numel(sv)-k+1, sprintf('%.1f%%  (%.2f m)', share(k), sv(k)), ...
         'FontSize', C.fs_note, 'FontName','Times New Roman', 'VerticalAlignment','middle');
end
set(ax,'YTick',1:numel(sv),'YTickLabel',flipud(sn(:)),'TickLabelInterpreter','none');
xlim(ax,[0 95]); xlabel(ax,'Share of variance (%)');
title(ax,'(a) Where the error actually lives');
text(ax, 34, 1.6, 'no GNSS term: with RTK it is 0.01 m', ...
     'FontSize', C.fs_note, 'FontName','Times New Roman', 'Color', C.red);

% (b) what each receiver class costs
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);
cc = {C.blue, C.orange, C.grey};
for i = 1:numel(rnames)
    [fq, xq] = ecdf(R{i});
    plot(ax, xq, 100*fq, 'Color', cc{i}, 'LineWidth', 1.5, ...
         'DisplayName', sprintf('%s (%.2f m)', rnames(i), rsig(i)));
end
yline(ax, 50, ':', 'Color', C.grey, 'LineWidth', 0.9, 'HandleVisibility','off');
yline(ax, 95, ':', 'Color', C.grey, 'LineWidth', 0.9, 'HandleVisibility','off');
text(ax, 0.06, 53, 'CEP50', 'FontSize', C.fs_note, 'FontName','Times New Roman', 'Color', C.grey);
text(ax, 0.06, 98, 'CEP95', 'FontSize', C.fs_note, 'FontName','Times New Roman', 'Color', C.grey);
xlim(ax,[0 5]); ylim(ax,[0 104]);
xlabel(ax,'Radial geolocation error (m)'); ylabel(ax,'Cumulative probability (%)');
title(ax,'(b) What the receiver class buys');
lg = legend(ax,'Location','southeast'); lg.Box='off';
lg.FontSize = C.fs_note; lg.FontName='Times New Roman';

rs_save(f, 'fig-geobudget.pdf');
end
