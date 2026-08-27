function out = rs_save(fig, name)
%RS_SAVE  Write a figure to the proposal's figure directory as vector PDF.
%
%   Vector, not raster: the proposal is set in LaTeX and a raster figure at
%   any sane file size looks soft next to Type-1 text.
%
%   ContentType 'vector' is required -- exportgraphics will silently
%   rasterise transparency and some patch objects otherwise, which is the
%   quiet way a figure ends up blurry in print.

here = fileparts(mfilename('fullpath'));
root = fileparts(fileparts(here));                  % repo root
dest = fullfile(root, 'docs', 'proposal', 'figures');
if ~isfolder(dest), mkdir(dest); end

% The interactive axes toolbar is exported into the PDF as a row of grey
% icons unless it is removed first. exportgraphics warns about it but still
% writes the file, so it is easy to ship a figure with a hover menu in it.
for ax = findall(fig, 'Type', 'axes')'
    ax.Toolbar = [];
    ax.Interactions = [];
end

out = fullfile(dest, name);
exportgraphics(fig, out, 'ContentType', 'vector', 'BackgroundColor', 'white');
fprintf('  wrote %s\n', name);
close(fig);
end
