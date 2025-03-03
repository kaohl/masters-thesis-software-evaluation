# masters-thesis-software-evaluation
Master's thesis software evaluation

# Create an experiment, refactor, and benchmark refactorings
## Prerequisites
- Requires SDKMAN! to be installed, including at least one SDK
- Update the parameter file after copying it to the specified experiment directory with valid SDK options (jdk; jre)
  (see procedure below)
## Procedure
Note that the `--x-location' argument is optional and defaults to 'experiments'.
```
mkdir -p experiments/x/batik/small
cp examples/batik.small.parameters.txt experiments/x/batik/small/parameters.txt

<adapt parameter file: experiments/x/batik/small/parameters.txt>

export DAIVY_HOME=...
./evaluation.py --x y --create
./evaluation.py --x y --refactor --bm batik --workload small
./evaluation.py --x y --benchmark
./evaluation.py --x y --report

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

