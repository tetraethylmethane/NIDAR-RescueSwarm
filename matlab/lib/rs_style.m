function C = rs_style(fig)
%RS_STYLE  House style for every figure in this project.
%
%   C = RS_STYLE()     returns the colour struct only.
%   C = RS_STYLE(fig)  also applies figure-level defaults.
%
%   Colours are Okabe-Ito, which stays distinguishable under the common forms
%   of colour blindness and survives greyscale printing. They match the
%   matplotlib figures already in the proposal so a reader cannot tell which
%   tool drew which plot.
%
%   Sizes are IEEEtran column widths in inches, so \includegraphics never
%   rescales -- rescaling is how axis labels end up unreadable.

C.blue   = [0.000 0.447 0.698];
C.orange = [0.902 0.624 0.000];
C.green  = [0.000 0.620 0.451];
C.red    = [0.835 0.369 0.000];
C.purple = [0.800 0.475 0.655];
C.grey   = [0.498 0.498 0.498];
C.light  = [0.851 0.851 0.851];

C.COL  = 3.5;      % one IEEE column, inches
C.FULL = 7.16;     % \textwidth, inches

C.fs      = 8;     % body
C.fs_tick = 7.5;
C.fs_note = 6.5;   % in-plot annotation

if nargin > 0 && ~isempty(fig)
    set(fig, 'Color', 'w', 'Units', 'inches');
    set(findall(fig,'-property','FontName'), 'FontName', 'Times New Roman');
end
end
