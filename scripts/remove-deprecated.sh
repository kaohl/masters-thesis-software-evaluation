#!/bin/env bash

benchmarks=(
    "batik"
    "xalan"
    "lusearch"
    "luindex"
    "jacop"
)

for bm in "${benchmarks[@]}"; do
    ./results.py --x "$bm" --bm "$bm" --show-deprecated
    n=`cat temp/deprecated/refactorings.txt | wc -l`
    m=`cat temp/deprecated/benchmarks.txt | wc -l`
    echo "Remove deprecated: refactorings = $n, benchmarks = $m"
    rm -rf `cat temp/deprecated/refactorings.txt`
    rm -rf `cat temp/deprecated/benchmarks.txt`
    rm -rf `find experiments/data/$bm -type d -empty`
done

