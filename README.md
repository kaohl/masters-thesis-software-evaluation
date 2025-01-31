# masters-thesis-software-evaluation
Master's thesis software evaluation

# Generate and benchmark refactoring
```
export DAIVY_HOME=...
mkdir -p experiments/x
./workspace.py --experiment x --project dacapo:batik:1.0
./run_benchmark.py --bm batik --data experiments/x/dacapo-batik-1_0/data/tmp...
```

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

