#!/bin/env bash

find experiments/data -iname metrics.txt > temp/all_metrics.txt

while read p; do
    d=`dirname $p`
    echo "Clear $d"
    rm -rf "$d"
done <temp/all_metrics.txt

# Remove empty 'stats' folders.
rm -rf `find experiments/data -empty -type d`

