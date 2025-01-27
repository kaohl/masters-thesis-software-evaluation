
% Find sub suite that maximize coverage on a time budge.

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

var int   : total_time         = sum (i in 0..Tn-1) (active[i] * suite[i] * txms[i]);
var float : total_coverage     = sum (i in 0..Un-1) (coverage[i]);

% The following is the total_coverage times the alignment of total_time with target_time.
% We want a quantity that maximizes towards 1 as the variable 't' approaches the specified
% constant value 'T'. The scalar product of the two vectors u = (T,t) and v = (t,T) has this
% property. This value is their project along the diagonal line between them (y = x) in
% the first quadrant, which is 1 when t == T, and <1 when t differs from T, because of the
% angle between them. As t approaches T they meet on the diagonal. If t under- or over-shoot
% the target value, the vectors are less aligned and therefore the projection is less than 1.
% There is no bias in either direction. Also, we can scale the coordinates by 'T' without
% loss of generality, which gives:
%   u = (1, z=t/T)
%   v = (z=t/T, 1)
%   s = u*v = (1,z)*(z,1)
%     = (1*z + z*1) / (sqrt(1*1 + z*z)*sqrt(z*z + 1*1))
%     = 2z/(1 + z*z),
% where 1+z*z is the product of the two lengths: ul, vl = sqrt(1+z*z*) which normalizes the
% vectors in the scalar product.
%
constraint cptu = total_coverage * 2 * (total_time / target_time) / (1 + (total_time / target_time)*(total_time / target_time));
solve maximize cptu;
output [ "TTime ", show(total_time - 1), "\nTCoverage ", show(total_coverage), "\nSuite\n", show(suite), "\n", "\nCoverage\n", show(coverage) ];
