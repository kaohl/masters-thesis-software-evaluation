#!/bin/env bash

data=$1 # Experiments
xp=$2 # Experiment
bm=$3 # Benchmark

./evaluation.py --data $data --xs $xp --bs $bm --create
./evaluation.py --data $data --xs $xp --bs $bm --refactor
n=`./evaluation.py --data $data --xs $xp --bs $bm --show-execution-plan | wc -l`
./evaluation.py --data $data --xs $xp --bs $bm --benchmark --n $n

