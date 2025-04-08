#!/bin/env bash

location=

if [ ! -d "$location" ]; then
    echo "Please specify a location."
    exit 1
fi

if [ ! -d "$location"/data ]; then
    echo "The specified location '$location' does not contain a data folder."
    exit 1
fi

./results.py --x-location "$location" --x xalan --bm xalan --workload small  --compute-results
./results.py --x-location "$location" --x xalan --bm xalan --workload default --compute-results

./results.py --x-location "$location" --x batik --bm batik --workload small --compute-results
./results.py --x-location "$location" --x batik --bm batik --workload default --compute-results

./results.py --x-location "$location" --x lusearch --bm lusearch --workload small --compute-results
./results.py --x-location "$location" --x lusearch --bm lusearch --workload default --compute-results

./results.py --x-location "$location" --x luindex --bm luindex --workload small --compute-results
./results.py --x-location "$location" --x luindex --bm luindex --workload default --compute-results

./results.py --x-location "$location" --x jacop --bm jacop --workload mzc18_1 --compute-results
./results.py --x-location "$location" --x jacop --bm jacop --workload mzc18_2 --compute-results
./results.py --x-location "$location" --x jacop --bm jacop --workload mzc18_3 --compute-results
./results.py --x-location "$location" --x jacop --bm jacop --workload mzc18_4 --compute-results

