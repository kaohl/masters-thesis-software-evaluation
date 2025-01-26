
/*
# See
#   https://docs.minizinc.dev/en/stable/sat.html
#   https://docs.minizinc.dev/en/stable/modelling2.html#sec-arrayset
#   https://docs.minizinc.dev/en/stable/flattening.html
#
# - The quantity we want to maximize is total coverage based on "unit coverage per time unit per test"
#   given a time constraint.
# - The implementation below falls short. See next version with unit coverage per time unit per test.
*/

% DATA

int : target_time;
int : Tn; % Number of test programs.
int : Un; % Number of units of coverage. (Methods; could be lines.)
array [0..Tn-1, 0..Un-1] of 0..1 : m;    % Test coverage matrix.
array [0..Tn-1]          of int  : txms; % Test execution times.  (This is too unspecific... need to couple with time, need coverage per unit time per method)

% PARAMETERS

var int   : time; % Total execution time.
var float : cptu; % Coverage per time unit.
array [0..Tn-1] of var 0..1 : suite;
array [0..Un-1] of var 0..1 : coverage;
array [0..Tn-1] of var 0..1 : active;   % Register active tests to avoid including tests with no coverage.

% CONSTRAINTS

constraint forall(i in 0..Tn-1) (
  active[i] = (sum (j in 0..Un-1) (m[i, j]) > 0)
);

constraint forall(j in 0..Un-1) (
  coverage[j] = sum(i in 0..Tn-1) (active[i] * suite[i] * m[i, j])
);

% We add 1 to total time to avoid division by zero
% in the trivial case where all tests provide zero
% coverage.
%   Ideally, all input tests should provide some
% coverage, and zero coverage tests be filtered
% out from the input. But just in case...
var int : total_time     = sum (i in 0..Tn-1) (active[i] * suite[i] * txms[i]) + 1;
var int : total_coverage = sum (i in 0..Un-1) (coverage[i]);
constraint cptu = total_coverage / (target_time / total_time);

solve maximize cptu;
output [ "TTime ", show(total_time - 1), "\nTCoverage ", show(total_coverage), "\nSuite\n", show(suite), "\n", "\nCoverage\n", show(coverage) ];
