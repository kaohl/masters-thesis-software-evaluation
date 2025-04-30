#!/bin/env bash

location=
plots_location=
#pascal_f1200_n10
#pascal_f3500_n10

if [ "$location" == "" ]; then
    echo "Please specify a location"
    exit 1
fi

if [ ! -d "$location" ]; then
    echo "Please specify an existing location"
fi

./plots.py --print-btable \
           --baseline-out "$location"/chapters/btables \
           --baseline-files results-from-bm-machine/baseline-*

./plots.py --print-ptables \
           --print-ptables-path "$location"/chapters/ptables

if [ "$plots_location" == "" ]; then
    echo "Please specify the plots output location"
fi

./plots.py --plots-out "$location"/chapters/plots/"$plots_location"

