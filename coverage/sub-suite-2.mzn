
% Find sub suite that maximize coverage on a time budge.

%QuadrFloat=true;

% DATA

% Use case 1:
% - Maximize coverage for time budge
% Use case 2:
% - Search for a suite that provides at least coverage C and runs in less than T units of time
% Use case 3:
% - Compute minimum suite that provides max coverage (removes overlapping tests)
%   (Requires a binary coverage measure. Works best when applied to line coverage but may be too high resolution.)

int : target_time;     % The desired execution time of the computed test sub-suite.
%int : target_coverage; % The desired total coverage.

int : Tn; % Number of test programs.
int : Un; % Number of covered units. (Methods or classes or lines. Depends on what input data represents.)
array [0..Tn-1, 0..Un-1] of float : uc;    % Test coverage matrix. "Element m[i,j] is test coverage on unit 'j' by test 'i' per unit time."
array [0..Tn-1]          of int   : txms; % Test execution times. This is just for printing a total execution time of computed suite.

% PARAMETERS

var int   : time; % Total execution time.
var float : cptu; % Coverage per time unit.
array [0..Tn-1] of var 0..1  : suite;
array [0..Un-1] of var float : coverage;
array [0..Tn-1] of var 0..1  : active;   % Register active tests to avoid including tests with no coverage.

% CONSTRAINTS

constraint forall(i in 0..Tn-1) (
  active[i] = (sum (j in 0..Un-1) (uc[i, j]) > 0)
);

constraint forall(j in 0..Un-1) (
  coverage[j] = sum(i in 0..Tn-1) (active[i] * suite[i] * uc[i, j])
);

% We add 1 to total time to avoid division by zero
% in the trivial case where all tests provide zero
% coverage.
%   Ideally, all input tests should provide some
% coverage, and zero coverage tests be filtered
% out from the input. But just in case...
var int   : total_time         = sum (i in 0..Tn-1) (active[i] * suite[i] * txms[i]) + 1;
var float : total_coverage     = sum (i in 0..Un-1) (coverage[i]);
%var float : is_time_acceptable = bool2float(total_time <= target_time); 
%constraint cptu = is_time_acceptable * total_coverage / total_time;% / (target_time / total_time); % Multiply by time constraint to drive score to zero when target time is exceeded.
constraint cptu = total_coverage * 2 * target_time * total_time / (target_time*target_time + total_time*total_time); % Use seconds instead to reduce magnitudes?
solve maximize cptu;
output [ "TTime ", show(total_time - 1), "\nTCoverage ", show(total_coverage), "\nSuite\n", show(suite), "\n", "\nCoverage\n", show(coverage) ];
