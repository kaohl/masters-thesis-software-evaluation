#!/bin/env bash

location=

if [ "$location" == "" ]; then
    echo "Please specify an output location"
    exit 1
fi

./plots.py --print-btable \
           --baseline-out "$location"/chapters/btables \
           --baseline-files results-from-bm-machine/baseline-*

./plots.py --print-ptables \
           --print-ptables-path "$location"/chapters/ptables

