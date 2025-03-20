#!/bin/env bash

./evaluation.py --xs jacop --bs jacop --create   # All <xs>/jacop/jacop workloads.
./evaluation.py --xs jacop --bs jacop --refactor # All <xs>/jacop/jacop workloads and lists.
n=`./evaluation.py --xs jacop --bs jacop --show-execution-plan | wc -l`
./evaluation.py --xs jacop --bs jacop --benchmark --n "$n"

#./evaluation.py --xs jacop --bs jacop --ws mzc18_1 --create
#./evaluation.py --xs jacop --bs jacop --ws mzc18_1 --ls list-1 --refactor
#n=`./evaluation.py --xs jacop --bs jacop --ws mzc18_1 --ls list-1 --show-execution-plan | wc -l`
#./evaluation.py --xs jacop --bs jacop --ws mzc18_1 --ls list-1 --benchmark --n "$n"

