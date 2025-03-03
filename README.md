# masters-thesis-software-evaluation
Master's thesis software evaluation

# Create an experiment, refactor, and benchmark refactorings
## Prerequisites
- Requires SDKMAN! to be installed, including at least one SDK
- Create experiments/<name>/workloads/<bm>/<workload>/parameters.txt
  - See 'examples/'
  - WARNING: If additional parameters are added after after an experiment
             is started the parameter files in all existing data will be
             incomplete, and the generated results may be incomplete or
             simply fail because values are missing.
             
             *** Take care to add all parameters from start... ***

- Create experiments/<name>/workloads/<bm>/<workload>/lists/<list i name>/{q_j.filters,q_j.params,q_j.defaults}
  - See 'lists/' for examples
- Create experiments/<name>/workloads/<bm>/<workload>/views/{<view name k>.json}
  - See 'views/' for examples

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

