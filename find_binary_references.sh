#!/bin/env bash

x="experiments/$1"

if [ ! -d "$x" ] || [ "$1" = "" ]; then
    echo "No such experiment: $x"
    exit 1
fi

grep -E "\`" $(find $x -iwholename */lists/**/descriptors.txt)

