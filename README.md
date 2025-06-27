# Overview
This is one of three repositories developed for my [master's thesis](https://lup.lub.lu.se/student-papers/search/publication/9204484) in software engineering, where we explored the impact of Java refactoring on execution performance.

See also the [refactoring framework](https://github.com/kaohl/alfine-refactoring) and the [build framework](https://github.com/kaohl/daivy).

> [!NOTE]
> Derived works should reference the thesis, which provides context for this work, and links to all repositories.

# Java Performance Evaluation Framework
The evaluation framework utilizes the refactoring framework and the build framework, linked above, to provide the infrastructure required to study the impact of Java refactoring on execution performance.

The benchmarks and refactoring types available for experimentation can be found in the build and refactoring frameworks, respectively.

# Create an experiment, refactor, and benchmark refactorings
## Prerequisites
- Requires SDKMAN! to be installed, including at least one SDK
- Generate (recommended) an *experiments* folder with configuration (see *generate_experiment.py*)

> [!CAUTION]
> If additional parameters are added after after an experiment is started, the parameter files in all existing data will be incomplete and data processing may fail because of missing values.
>
> It is possible to upgrade an existing dataset, but only if you know the values that should be applied to these parameters for each existing benchmark execution.
>
> Take care to add all parameters from the start.

## Procedure
Note that the `--x-location' argument is optional and defaults to 'experiments'.
```
mkdir -p experiments/<name>/<bm>/<workload>/{lists,views}
cp examples/<bm>.<workload>.parameters.txt experiments/<name>/<bm>/<workload>/parameters.txt

<adapt experiments/x/batik/small/parameters.txt>
<create/copy/adapt lists and views>

export DAIVY_HOME=...
./evaluation.py --x y --create
./evaluation.py --x y --refactor --bm batik --workload small --n <number of runs>
./evaluation.py --x y --benchmark --n <number of runs>
./results.py --x jacop --bm jacop --workload default

# Dump result objects to stdout. (Precursor to 'results.py'.)
./evaluation.py --x y --report

# Helpers for estimating size and time.
# Use in conjunction with 'wc -l' to find appropriate values for the --n parameter to --benchmark and --refactor.
# Multiply by two times the average EXECUTION_TIME of a given workload to get an upper estimate for the time it
# takes to run all remaining configurations for all created refactorings.
./evaluation.py --x y --show-configurations
./evaluation.py --x y --show-execution-plan
```

Example of descriptor attribute filter matching (for debugging):
```
./opportunity_cache.py \
    --cache experiments/jacop/workspaces/jacop/default/workspace/oppcache \
    --filter "{\"id\":\"org.eclipse.jdt.ui.extract.method\"}" | wc -l
```
The evaluation script uses the stream variant to write matching descriptors
directly to the target file inside the experiment configuration.
Currently, only meta attribute filtering is supported. But easy to extend
to args filtering as well if/when needed.

# Troubleshooting
## Missing data
If you get the following error, make sure that the linked in
data folder actually exists. In this case, the folder linked
symbolically at '<...>/luindex-1.0/dat' had been removed to
save space.
```
===== DaCapo unknown luindex starting =====
FATAL ERROR: Failed to find data at <...>/luindex-1.0

Please run DaCapo with --data-set-location <parent-dir-name> to reset the location of the parent directory.
```

