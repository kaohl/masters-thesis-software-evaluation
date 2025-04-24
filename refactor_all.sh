#!/bin/env bash

n=8

lists=(
    #"extract_temp"
    "inline_temp"
    #"rename_local_variable"
    "rename_type_parameter"
    #"extract_constant"
    "inline_constant"
    #"introduce_indirection"
    "rename_method"
    #"extract_method"
    "inline_method"
    "rename_field"
    "rename_type"
)

benchmarks=(
    "batik"
    #"jacop"
    "luindex"
    "lusearch"
    "xalan"
)

workloads=(
    "small"
    "default"
)

for b in "${benchmarks[@]}"; do
    for w in "${workloads[@]}"; do
	for l in "${lists[@]}"; do
	    echo "$b $w $l"
	    time ./evaluation.py --xs "$b" --bs "$b" --ws "$w" --ls "$l" --refactor --n "$n"
	done
    done
done

jacop_workloads=(
    "mzc18_1"
    "mzc18_2"
    "mzc18_3"
    "mzc18_4"
)

for w in "${jacop_workloads[@]}"; do
    for l in "${lists[@]}"; do
	echo "jacop $w $l"
	time ./evaluation.py --xs "jacop" --bs "jacop" --ws "$w" --ls "$l" --refactor --n "$n"
    done
done
