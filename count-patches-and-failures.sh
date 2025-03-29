#!/bin/env bash

for bm in `ls experiments/data`; do
    ok=`find experiments/data/"$bm" -iname patches.txt | wc -l`
    nk=`find experiments/data/"$bm" -iname FAILURE | wc -l`     # Warning: Includes bm failure as well.
    echo "Benchmark = $bm, Patches = $ok, Failures = $nk"
done

