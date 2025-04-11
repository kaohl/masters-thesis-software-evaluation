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
    echo "Removing $n deprecated refactorings"
    rm -rf `cat temp/deprecated/refactorings.txt`
    rm -rf `find experiments/data/$bm -type d -empty`
done

