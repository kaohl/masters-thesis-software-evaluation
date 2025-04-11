#!/bin/env bash

if [ ! -d 'refactoring-framework' ]; then
    echo "Please deploy the refactoring framework."
    exit 1
fi

./evaluation.py --xs batik xalan lusearch luindex --bs batik xalan lusearch luindex --ws small default --create
./evaluation.py --xs jacop --bs jacop --ws mzc18_1 mzc18_2 mzc18_3 mzc18_4 --create
