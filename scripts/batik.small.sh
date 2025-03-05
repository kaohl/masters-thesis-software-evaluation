#!/bin/env bash

m=$1
n=$2

for i in $(seq $2); do
    echo "--------------------------------------------------"
    echo "Attempting to generate $1 refactorings ($i / $2)"
    echo "--------------------------------------------------"
    ./evaluation.py --x batik --refactor --bm batik --workload small --n "$1"
    k=`./evaluation.py --x batik --bm batik --workload small --show-execution-plan | wc -l`

    echo "Running $k benchmarks"
    ./evaluation.py --x batik --benchmark --bm batik --workload small --n "$k"
done

