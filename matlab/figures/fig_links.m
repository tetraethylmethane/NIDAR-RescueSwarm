function fig_links()
%FIG_LINKS  Link margin by radio, at the geofence and against range.
%
% WHY THIS FIGURE EXISTS. The original design put video, telemetry and
% coordination on one 5.8 GHz 802.11 mesh. At the 600 m geofence that link has
% 8.7 dB of margin -- the thinnest path in the system, and simultaneously the
% one carrying the most data. A mesh does not repair that, because a relay hop
% is the same weak link. The three-radio split that replaced it puts every
% remaining path above 28 dB.
%
% Panel (b) is the part a table cannot show: where each link actually runs out.
% The withdrawn 802.11 path reaches its sensitivity floor at roughly 1.6 km,
% but margin is not headroom -- rain, body blocking, a banked airframe and
% antenna misalignment all draw on it, and 8.7 dB does not cover them.

J = rs_model(); C = rs_style();
L = J.links;
d_fence = J.geofence_m;

fspl = @(f_mhz, d_m) 20*log10(d_m/1000) + 20*log10(f_mhz) + 32.44;
margin = @(k, d) L(k).tx_dbm + L(k).g_tx_dbi + L(k).g_rx_dbi ...
                 - fspl(L(k).f_mhz, d) - L(k).sens_dbm;

n = numel(L);
cc = {C.blue, C.green, C.orange, C.grey};

f = figure('Units','inches','Position',[0 0 C.FULL 2.7],'Color','w');
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

%% (a) margin at the geofence ---------------------------------------------
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);
m = arrayfun(@(k) margin(k, d_fence), 1:n);
lbl = arrayfun(@(k) string(L(k).name), 1:n);
for k = 1:n
    barh(ax, n-k+1, m(k), 0.6, 'FaceColor', cc{k}, 'EdgeColor','none');
    text(ax, m(k)+1.2, n-k+1, sprintf('%.1f dB', m(k)), ...
         'FontSize', C.fs_note, 'FontName','Times New Roman', ...
         'VerticalAlignment','middle');
end
set(ax,'YTick',1:n,'YTickLabel',flipud(lbl(:)),'TickLabelInterpreter','none');
xlim(ax,[0 66]); xlabel(ax,'Link margin at 600 m (dB)');
title(ax,'(a) Margin at the geofence');
% The withdrawn row sits last; mark why.
text(ax, 15.5, 1.42, 'withdrawn: thinnest path, most data', ...
     'FontSize', C.fs_note, 'FontName','Times New Roman', 'Color', C.red, ...
     'VerticalAlignment','middle');

%% (b) margin against range ------------------------------------------------
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);
% Four curves label better at their right-hand ends than in a legend box,
% which had to sit on top of one of them.
d = logspace(log10(50), log10(3000), 300);
d_lab = 3150;
for k = 1:n
    st = '-'; if k == n, st = '--'; end
    plot(ax, d, arrayfun(@(x) margin(k,x), d), st, 'Color', cc{k}, ...
         'LineWidth', 1.5);
    text(ax, d_lab, margin(k, 3000), L(k).name, 'Color', cc{k}, ...
         'FontSize', 6.4, 'FontName','Times New Roman', ...
         'VerticalAlignment','middle');
end
yline(ax, 0, '-', 'Color', C.red, 'LineWidth', 1.1, 'HandleVisibility','off');
text(ax, 58, 3.4, 'sensitivity floor', 'FontSize', C.fs_note, ...
     'FontName','Times New Roman', 'Color', C.red);
xline(ax, d_fence, ':', 'Color', C.grey, 'LineWidth', 1, 'HandleVisibility','off');
text(ax, d_fence*1.10, 67, sprintf('%.0f m geofence', d_fence), ...
     'FontSize', C.fs_note, 'FontName','Times New Roman', 'Color', C.grey);
set(ax,'XScale','log');
xlim(ax,[50 9000]); ylim(ax,[-10 72]);
xlabel(ax,'Slant range (m)'); ylabel(ax,'Link margin (dB)');
title(ax,'(b) Where each link runs out');
rs_save(f, 'fig-links.pdf');
end
