#!/bin/env bash

data=$1 # Experiments
xp=$2 # Experiment
bm=$3 # Benchmark

# Here we must use a runtime capable of running all benchmarks.
# Because, we need to run the benchmark to generate steering
# for the refactoring framework when setting up the eclipse
# workspace. When benchmarking, the JDK/JRE is set internally
# based on experimental parameters instead, ignoring this sdk.

sdk use java 17.0.14-tem

./evaluation.py --data $data --xs $xp --bs $bm --create
./evaluation.py --data $data --xs $xp --bs $bm --refactor
n=`./evaluation.py --data $data --xs $xp --bs $bm --show-execution-plan | wc -l`
./evaluation.py --data $data --xs $xp --bs $bm --benchmark --n $n

