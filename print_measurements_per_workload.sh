#!/bin/env bash

file=$1

if [ ! -f "$file" ]; then
    echo "Please specify a data file."
    exit 1
fi

function print_count {
    n=`cat "$file" | grep -E $1 | grep -E $2 | wc -l`
    echo "$1 $2 $n"
}

print_count batik small
print_count batik default
print_count jacop mzc18_1
print_count jacop mzc18_2
print_count jacop mzc18_3
print_count jacop mzc18_4
print_count luindex small
print_count luindex default
print_count lusearch small
print_count lusearch default
print_count xalan small
print_count xalan default

