#!/bin/env bash

function count_files {
    find $1 -iname $2 | wc -l
}

data=experiments/data

for bm in `ls $data`; do
    location="$data/$bm"

    metrics_count=`count_files $location metrics.txt`
    success_refactor=`count_files $location patches.txt`
    stats=`count_files $location stats`
    success_benchmark=`count_files $location SUCCESS`
    failure=`count_files $location FAILURE`
    failure_generic=`count_files $location GENERIC`
    failure_timeout=`count_files $location TIMEOUT`
    failure_benchmark=$((failure_generic + failure_timeout))
    failure_refactor=$((failure - failure_benchmark))

    benchmark_patch_coverage="$stats/$success_refactor"

    printf "Benchmark = %-8s, Refactor { success = %-4d, failure = %-4d }, Benchmark { success = %-4d, failure = { generic = %-4d, timeout = %-4d }, patch_coverage = %10s, measurements = %-6d }\n" \
        "$bm"                       \
        "$success_refactor"         \
        "$failure_refactor"         \
        "$success_benchmark"        \
        "$failure_generic"          \
        "$failure_timeout"          \
        "$benchmark_patch_coverage" \
        "$metrics_count"
done

