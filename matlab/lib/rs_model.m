function J = rs_model()
%RS_MODEL  Load the exported sizing model.
%
%   J = RS_MODEL() returns the decoded model.json, with fields:
%       J.primitives        inputs the design chooses
%       J.derived           what the Python model computed
%       J.mass_g            mass statement, must sum to MTOW
%       J.mission_segments  the flight profile
%
%   Nothing in matlab/ retypes a design constant. Every script reads this.
%   Two copies of a constant is the defect this repository keeps finding in
%   itself, and it always diverges silently.
%
%   Regenerate with:  python matlab/export_model.py

here = fileparts(mfilename('fullpath'));
root = fileparts(here);                       % matlab/
f = fullfile(root, 'data', 'model.json');

if ~isfile(f)
    error('rs_model:missing', ...
          ['model.json not found. Run:\n\n' ...
           '    python matlab/export_model.py\n']);
end
J = jsondecode(fileread(f));
end
