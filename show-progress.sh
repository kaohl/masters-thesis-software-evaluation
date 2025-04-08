#!/bin/env bash

./results.py --x xalan --bm xalan --workload small  --show-progress
./results.py --x xalan --bm xalan --workload default --show-progress

./results.py --x batik --bm batik --workload small --show-progress
./results.py --x batik --bm batik --workload default --show-progress

./results.py --x lusearch --bm lusearch --workload small --show-progress
./results.py --x lusearch --bm lusearch --workload default --show-progress

./results.py --x luindex --bm luindex --workload small --show-progress
./results.py --x luindex --bm luindex --workload default --show-progress

./results.py --x jacop --bm jacop --workload mzc18_1 --show-progress
./results.py --x jacop --bm jacop --workload mzc18_2 --show-progress
./results.py --x jacop --bm jacop --workload mzc18_3 --show-progress
./results.py --x jacop --bm jacop --workload mzc18_4 --show-progress

