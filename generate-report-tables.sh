#!/bin/env bash

location=
plots_location=pascal_f3500_n10_b10
#pascal_f1200_n10
#pascal_f3500_n10_b1
#pascal_f3500_n10_b10
tables_location=f3500/anova

if [ "$location" == "" ]; then
    echo "Please specify a location"
    exit 1
fi

if [ ! -d "$location" ]; then
    echo "Please specify an existing location"
    exit 1
fi

./plots.py --print-btable \
           --baseline-out "$location"/chapters/btables \
           --baseline-files results-from-bm-machine/baseline-*

./plots.py --print-ptables \
           --print-ptables-path "$location"/chapters/ptables

if [ "$plots_location" == "" ]; then
    echo "Please specify the plots output location"
    exit 1
fi
if [ "$tables_location" == "" ]; then
    echo "Please specify the tables output location"
    exit 1
fi
./plots.py --plots-out "$location"/chapters/plots/"$plots_location" \
           --tables-out "$location"/chapters/tables/"$tables_location"

X1200=experiments-1200-290425
if [ -d "$X1200" ]; then
    ./print_progress.py --x-location "$X1200" --dataset-name "F1200" --output-location "$location"/chapters/tables/f1200
fi

X3500=experiments-3500-090525
if [ -d "$X3500" ]; then
    ./print_progress.py --x-location "$X3500" --dataset-name "F3500" --output-location "$location"/chapters/tables/f3500
fi

