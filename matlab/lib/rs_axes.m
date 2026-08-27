function ax = rs_axes(ax, C)
%RS_AXES  Apply the house axis style.
%
%   Matches the matplotlib figures already in the proposal: no top or right
%   spine, faint grid, small serif labels. Applied through one function so a
%   style change moves every figure at once rather than none of them.

if nargin < 2, C = rs_style(); end
set(ax, 'FontName','Times New Roman', 'FontSize', C.fs_tick, ...
        'Box','off', 'TickDir','out', ...
        'XGrid','on', 'YGrid','on', ...
        'GridAlpha', 0.25, 'GridLineWidth', 0.5, ...
        'LineWidth', 0.6);
ax.XAxis.Label.FontSize = C.fs;
ax.YAxis.Label.FontSize = C.fs;
ax.Title.FontSize = C.fs + 0.5;
ax.Title.FontWeight = 'normal';
end
