#!/bin/env bash

location=experiments

echo "Using location: '$location'"

benchmarks=("batik" "lusearch" "luindex" "xalan")
workloads=("small" "default")

for bm in "${benchmarks[@]}"; do
    for wl in "${workloads[@]}"; do
        for f in `ls "$location/$bm/results/$bm/$wl"/*.table`; do
            echo "$f";
            cat  "$f";
            echo ""
            echo "--------------------";
        done
    done
done

bm="jacop"
jacop_workloads=("mzc18_1" "mzc18_2" "mzc18_3" "mzc18_4")

for wl in "${jacop_workloads[@]}"; do
    for f in `ls "$location/$bm/results/$bm/$wl"/*.table`; do
        echo "$f";
        cat  "$f";
        echo "";
        echo "------------------";
    done
done
