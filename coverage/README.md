# Finding a minimal testsuite
The goal of this excursion was to compute a minimal testsuite
for the JaCoP library based on refactoring changes, because the
full testsuite takes to long time to run to validate refactorings.

Initially this was not part of the project synopsis and ended up
taking too long time. Also the runtime of computing an optimal
test suite is not feasible in the way I initially planned.
Eventually we decided to excluded this from the project and
skip not validate refactorings through unittesting, instead
falling back on benchmark output validation which was already
built into the benchmark harness. Less reliable but more time-
effective.

The plan was to:
1. Map line numbers to methods using the javap program
2. Run unit tests with jacoco to generate coverage reports
  => This gives us covered line numbers which should match
     the line numbers displayed by javap
3. Parse the coverage reports to produce a unittest-to-method-mapping
  => This also means that we must execute enough tests to complete
     the mapping over our sampled methods (very time-consuming)
4. Compute an optimal testsuite (maximum coverage given a specified
   testsuite execution time of T milliseconds) by maximizing "coverage"
   times a geometric constraint that maximizes when the testsuite
   execution time is equal to T. For example, the scalar product of
   vectors (1, t/T) and (t/T, 1) after normalization, where t is the
   execution time of the selected testsuite, and T is the target
   execution time.

However, running all tests (even a large subset of the upTo5Sec tests)
the "real" data vectors becomes impractically large and even for small
"test" datasets the computation takes hours.

An alternative is to create a test-to-line mapping and pick a random
suite of tests that covers all required lines. (Iterate over the
compilation units and lines that we want covered based on the patch,
and then pick a random test for each line using the test-to-line mapping.
Whenever we pick a test we could check if it covers more of the lines we
want covered to reduce exeuction time.)

The patch files of a refactoring gives us the modified chunks
of each file. Adding and removing lines invalidates the line
numbers that comes after each modification. As a result we
must perform a line number translation. We can perform this
on-the-fly as we process chunks top-to-bottom of each file.

... TODO

# Issues
Looking at the html page in the browser I expected to find 1008
hit methods for upTo5sec/rcpsp-data_psplib-J60/J60_19_7, but
only found around 650. Not sure why that is...

