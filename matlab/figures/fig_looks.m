function fig_looks()
%FIG_LOOKS  Temporal sampling: the shortfall, and what closing it costs.
%
%   Multi-frame fusion needs twelve independent looks at a target. At the
%   adopted 40 m and 8 m/s the geometry supplies 7.9 at 2 Hz, so the budget
%   does not close. Panel (b) is the part that is usually left out: raising the
%   rate to 3.06 Hz closes the look count but pushes the inference load past
%   what the accelerator measures, which is what the water gate would buy back.

J = rs_model(); p = J.primitives; d = J.derived; C = rs_style();

f = figure('Units','inches','Position',[0 0 C.FULL 2.5],'Color','w');
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

r = linspace(1, 5, 300);

%% (a) looks per target ----------------------------------------------------
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);
alts = [30 40 60]; cols = {C.light, C.blue, C.orange};
for k = 1:3
    D = 2*alts(k)*tand(d.vfov_deg/2);                % along-track footprint
    plot(ax, r, D./p.groundspeed_ms.*r, 'Color', cols{k}, 'LineWidth', 1.4, ...
         'DisplayName', sprintf('%d m', alts(k)));
end
yline(ax, p.fusion_min_frames, '-.', 'Color', C.red, 'LineWidth', 1);
text(ax, 1.05, p.fusion_min_frames+0.7, ...
     sprintf('fusion requires %d looks', p.fusion_min_frames), ...
     'Color', C.red, 'FontSize', C.fs_note, 'FontName','Times New Roman');

plot(ax, 2.0, d.looks_at_2Hz, 'o', 'Color', C.blue, ...
     'MarkerFaceColor', C.blue, 'MarkerSize', 5);
text(ax, 2.15, 3.4, sprintf('2 Hz today, %.1f looks', d.looks_at_2Hz), ...
     'Color', C.blue, 'FontSize', C.fs_note, 'FontName','Times New Roman');
plot(ax, d.rate_for_12_looks_Hz, p.fusion_min_frames, 's', 'Color', C.green, ...
     'MarkerFaceColor', C.green, 'MarkerSize', 5);
text(ax, 3.35, 8.2, sprintf('%.2f Hz closes it', d.rate_for_12_looks_Hz), ...
     'Color', C.green, 'FontSize', C.fs_note, 'FontName','Times New Roman');

xlim(ax,[1 5]); ylim(ax,[0 24]);
xlabel(ax,'Capture rate (Hz)'); ylabel(ax,'Looks per target per pass');
title(ax,'(a) The shortfall, and the rate that closes it');
lg = legend(ax,'Location','northwest'); lg.Box='off';
lg.FontSize = C.fs_note; lg.FontName='Times New Roman';
title(lg,'altitude');

%% (b) what that costs in inferences ---------------------------------------
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);

% Tile count from the sensor geometry, not written in: 640 px tiles on a
% 512 px stride over the native frame.
tile = 640; stride = 512;
nt = (ceil((p.px_w-tile)/stride)+1) * (ceil((p.px_h-tile)/stride)+1);

plot(ax, r, nt.*r, 'Color', C.blue, 'LineWidth', 1.4, ...
     'DisplayName', sprintf('%d native tiles', nt));
patch(ax, [1 5 5 1], [130 130 160 160], C.green, ...
      'FaceAlpha', 0.16, 'EdgeColor','none', 'HandleVisibility','off');
text(ax, 1.08, 145, 'accelerator, measured', 'Color', C.green, ...
     'FontSize', C.fs_note, 'FontName','Times New Roman');

xline(ax, 2.0, ':', 'Color', C.grey, 'LineWidth', 0.9);
xline(ax, d.rate_for_12_looks_Hz, ':', 'Color', C.red, 'LineWidth', 0.9);
text(ax, 3.15, 52, sprintf('%.2f Hz needs\n%.0f inf/s', ...
     d.rate_for_12_looks_Hz, nt*d.rate_for_12_looks_Hz), ...
     'Color', C.red, 'FontSize', C.fs_note, 'FontName','Times New Roman');

% With a gate discarding open water: gate passes cost (640/96)^2 less each.
gate_px = 96; water = 0.87;
eq = nt*d.rate_for_12_looks_Hz/((tile/gate_px)^2) ...
   + nt*d.rate_for_12_looks_Hz*(1-water);
plot(ax, d.rate_for_12_looks_Hz, eq, 'p', 'Color', C.green, ...
     'MarkerFaceColor', C.green, 'MarkerSize', 9);
text(ax, 3.15, 8, sprintf('with a water gate: ~%.0f', eq), ...
     'Color', C.green, 'FontSize', C.fs_note, 'FontName','Times New Roman');

xlim(ax,[1 5]); ylim(ax,[0 250]);
xlabel(ax,'Capture rate (Hz)'); ylabel(ax,'Inferences per second');
title(ax,'(b) Why the gate is a throughput argument');

rs_save(f, 'fig-looks.pdf');
end
