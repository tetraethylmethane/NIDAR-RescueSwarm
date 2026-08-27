function run_all(what)
%RUN_ALL  Verification, figures and simulations for RescueSwarm.
%
%   run_all            everything
%   run_all('verify')  cross-checks only
%   run_all('figs')    figures only
%   run_all('sim')     simulations only
%
%   Regenerate the model first if the design changed:
%       python matlab/export_model.py
%
%   Exit status is non-zero if any verification check fails, so this can be
%   wired into CI alongside the Python checks.

if nargin < 1, what = 'all'; end

here = fileparts(mfilename('fullpath'));
addpath(fullfile(here,'lib'), fullfile(here,'calc'), ...
        fullfile(here,'verify'), fullfile(here,'figures'), ...
        fullfile(here,'sim'));

t0 = tic; nfail = 0;

if any(strcmp(what, {'all','verify'}))
    fprintf('\n>> VERIFICATION\n');
    try
        verify_model();
    catch ME
        fprintf(2, '   FAILED: %s\n', ME.message);
        nfail = nfail + 1;
    end
end

if any(strcmp(what, {'all','figs'}))
    fprintf('\n>> FIGURES\n');
    for fn = {@fig_detect, @fig_looks, @fig_energy}
        try
            fn{1}();
        catch ME
            fprintf(2, '   FAILED %s: %s\n', func2str(fn{1}), ME.message);
            nfail = nfail + 1;
        end
    end
end

if any(strcmp(what, {'all','sim'}))
    fprintf('\n>> SIMULATIONS\n');
    try
        sim_pack_sag();
    catch ME
        fprintf(2, '   FAILED sim_pack_sag: %s\n', ME.message);
        nfail = nfail + 1;
    end
end

fprintf('\n%s\n', repmat('=',1,60));
if nfail == 0
    fprintf(' all stages completed in %.1f s\n', toc(t0));
else
    fprintf(2, ' %d stage(s) FAILED in %.1f s\n', nfail, toc(t0));
end
fprintf('%s\n\n', repmat('=',1,60));

if nfail > 0, error('run_all:failed','%d stage(s) failed', nfail); end
end
