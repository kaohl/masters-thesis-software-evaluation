# masters-thesis-software-evaluation
Master's thesis software evaluation

# Generate and benchmark refactoring
```
export DAIVY_HOME=...
mkdir -p experiments/x
./workspace.py --experiment x --project dacapo:batik:1.0
./run_benchmark.py --bm batik --data experiments/x/dacapo-batik-1_0/data/tmp...
```

