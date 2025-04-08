#!/bin/env bash

./results.py --x xalan --bm xalan --workload small  --compute-results
./results.py --x xalan --bm xalan --workload default --compute-results

./results.py --x batik --bm batik --workload small --compute-results
./results.py --x batik --bm batik --workload default --compute-results

./results.py --x lusearch --bm lusearch --workload small --compute-results
./results.py --x lusearch --bm lusearch --workload default --compute-results

./results.py --x luindex --bm luindex --workload small --compute-results
./results.py --x luindex --bm luindex --workload default --compute-results

./results.py --x jacop --bm jacop --workload mzc18_1 --compute-results
./results.py --x jacop --bm jacop --workload mzc18_2 --compute-results
./results.py --x jacop --bm jacop --workload mzc18_3 --compute-results
./results.py --x jacop --bm jacop --workload mzc18_4 --compute-results

