function fig_detect()
%FIG_DETECT  Target size against altitude and downsample, versus COCO small.
%
%   This is the figure for the paper's central claim: that only 40 m with
%   native-resolution tiling puts the target above the size at which published
%   detector accuracy collapses. Every other operating point falls below it.
%
%   The target is a person in WATER -- head and shoulders, 0.40 m across --
%   which is the posture this system exists to find. A supine adult at 1.7 m
%   overstates the apparent area roughly fourfold and makes the problem look
%   solved when it is not.

J = rs_model(); p = J.primitives; C = rs_style();

f = figure('Units','inches','Position',[0 0 C.FULL 2.6],'Color','w');
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

%% (a) continuous, against altitude ---------------------------------------
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);
h = linspace(20, 80, 300);
gsd = p.pitch_um .* h ./ p.f_mm ./ 10;              % cm/px, native
for k = 1:2
    ds  = k;                                         % 1 = native, 2 = 2x
    if k == 1, col = C.blue; lbl = 'native tiling';
    else,      col = C.orange; lbl = '2\times downsample'; end
    area = (p.water_target_m ./ (gsd.*ds./100)).^2;
    plot(ax, h, area, 'Color', col, 'LineWidth', 1.4, 'DisplayName', lbl);
end
yline(ax, p.coco_small_px2, '-.', 'Color', C.red, 'LineWidth', 1, ...
      'HandleVisibility','off');
text(ax, 55, p.coco_small_px2*1.3, 'COCO small-object threshold', ...
     'Color', C.red, 'FontSize', C.fs_note, 'FontName','Times New Roman');

% Mark the adopted point on the curve it actually lies on.
g40  = p.pitch_um * p.h_search_m / p.f_mm / 10;
a40  = (p.water_target_m / (g40/100))^2;
xline(ax, p.h_search_m, ':', 'Color', C.grey, 'LineWidth', 0.9, ...
      'HandleVisibility','off');
plot(ax, p.h_search_m, a40, 'o', 'Color', C.blue, ...
     'MarkerFaceColor', C.blue, 'MarkerSize', 5, 'HandleVisibility','off');
text(ax, 43, 330, sprintf('adopted: %g m native, %.0f px^2', p.h_search_m, a40), ...
     'Color', C.blue, 'FontSize', C.fs_note, 'FontName','Times New Roman');

set(ax, 'YScale','log'); xlim(ax,[20 80]);
xlabel(ax,'Survey altitude (m AGL)'); ylabel(ax,'Target area (px^2)');
title(ax,'(a) Only 40 m + native clears the threshold');
lg = legend(ax,'Location','northeast'); lg.Box = 'off';
lg.FontSize = C.fs_note; lg.FontName = 'Times New Roman';

%% (b) the four operating points -------------------------------------------
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);
pts = {40,1,C.blue; 60,1,C.grey; 40,2,C.orange; 60,2,C.light};
% One line per label. A newline inside an XTickLabel entry is split by MATLAB
% into two separate tick labels, which silently mislabels the bars -- the first
% render of this figure read "40 m / native / 60 m / native".
lbls = {'40 m native','60 m native','40 m 2\times','60 m 2\times'};
vals = zeros(1,4);
for k = 1:4
    g = p.pitch_um * pts{k,1} / p.f_mm / 10 * pts{k,2};
    vals(k) = (p.water_target_m / (g/100))^2;
    bar(ax, k, vals(k), 0.62, 'FaceColor', pts{k,3}, 'EdgeColor','none');
    text(ax, k, vals(k)*1.05, sprintf('%.0f', vals(k)), ...
         'HorizontalAlignment','center', 'FontSize', C.fs_note, ...
         'FontName','Times New Roman');
end
yline(ax, p.coco_small_px2, '-.', 'Color', C.red, 'LineWidth', 1, ...
      'HandleVisibility','off');
set(ax,'XTick',1:4,'XTickLabel',lbls,'TickLabelInterpreter','tex');
ylabel(ax,'Target area (px^2)'); ylim(ax,[0 max(vals)*1.25]);
title(ax,'(b) The four operating points');

rs_save(f, 'fig-detect.pdf');
end
