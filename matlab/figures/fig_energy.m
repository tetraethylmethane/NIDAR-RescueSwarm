function fig_energy()
%FIG_ENERGY  Reserve policy against pack capacity, and the motor's operating point.
%
%   Panel (a) is the reserve policy: the pack must carry the nominal mission,
%   a full second sweep of the search area, and four minutes of loiter, all
%   inside the 80 % usable window. Every term is read from the model rather
%   than written in -- an earlier draft of this figure retyped two of them from
%   a stale PDF and disagreed with the document by 9 Wh.
%
%   Panel (b) puts the Tarot TL96020 against its own datasheet. Hover is
%   comfortable. The peak at the design thrust-to-weight is above the rated
%   continuous current, which is defensible only because T/W 2.0 is a transient
%   authority reserve rather than a flight condition -- and is worth showing
%   rather than leaving a reviewer to compute.

J = rs_model(); p = J.primitives; d = J.derived; C = rs_style();

f = figure('Units','inches','Position',[0 0 C.FULL 2.5],'Color','w');
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

%% (a) reserve stack -------------------------------------------------------
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);
terms = [d.E_nominal_Wh, d.E_resweep_Wh, d.E_loiter_Wh];
names = {'Nominal mission','Full re-sweep','4 min loiter'};
cols  = {C.blue, C.orange, C.green};
bottom = 0;
for k = 1:3
    bar(ax, 1, terms(k), 0.5, 'FaceColor', cols{k}, 'EdgeColor','none', ...
        'BaseValue', bottom, 'DisplayName', ...
        sprintf('%s (%.1f Wh)', names{k}, terms(k)));
    bottom = bottom + terms(k);
end
bar(ax, 2, d.E_usable_Wh, 0.5, 'FaceColor', C.light, 'EdgeColor','none', ...
    'DisplayName', sprintf('Usable at %g%% DoD (%.1f Wh)', 100*p.DOD, d.E_usable_Wh));
yline(ax, d.E_required_Wh, '-.', 'Color', C.red, 'LineWidth', 1);
text(ax, 2.32, d.E_required_Wh+6, sprintf('required %.1f Wh', d.E_required_Wh), ...
     'Color', C.red, 'FontSize', C.fs_note, 'FontName','Times New Roman', ...
     'HorizontalAlignment','right');
text(ax, 2, d.E_usable_Wh+9, sprintf('+%.0f %% margin', ...
     100*(d.E_usable_Wh/d.E_required_Wh - 1)), ...
     'HorizontalAlignment','center', 'Color', C.grey, ...
     'FontSize', C.fs, 'FontName','Times New Roman');
set(ax,'XTick',[1 2],'XTickLabel',{'Required','Available'});
xlim(ax,[0.4 2.6]); ylim(ax,[0 280]);
ylabel(ax,'Energy (Wh)');
title(ax,'(a) Reserve policy against pack capacity');
lg = legend(ax,'Location','northwest'); lg.Box='off';
lg.FontSize = 6.4; lg.FontName='Times New Roman';

%% (b) motor operating point ----------------------------------------------
ax = nexttile; hold(ax,'on'); rs_axes(ax,C);
DS = p.motor_datasheet_cont_A;
vals = [1.1, d.I_hover_A/p.N_rot, d.I_max_A/p.N_rot];
names = {'Idle','Hover','Peak at T/W 2'};
cols  = {C.light, C.green, C.orange};
for k = 1:3
    bar(ax, k, vals(k), 0.6, 'FaceColor', cols{k}, 'EdgeColor','none');
    text(ax, k, vals(k)+1.0, sprintf('%.1f A\n%.0f %%', vals(k), 100*vals(k)/DS), ...
         'HorizontalAlignment','center', 'FontSize', C.fs_note, ...
         'FontName','Times New Roman');
end
yline(ax, DS, '-.', 'Color', C.red, 'LineWidth', 1.2);
text(ax, 0.55, DS+1.3, sprintf('datasheet max continuous %.1f A', DS), ...
     'Color', C.red, 'FontSize', C.fs_note, 'FontName','Times New Roman');
set(ax,'XTick',1:3,'XTickLabel',names);
ylabel(ax,'Current per motor (A)'); ylim(ax,[0 36]);
title(ax,'(b) Tarot TL96020 operating point');

rs_save(f, 'fig-motor.pdf');
end
