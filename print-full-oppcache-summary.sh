#!/bin/env bash

for x in `find experiments -iname oppcache`; do
    echo "-------------------"
    echo "$x"
    echo "-------------------"
    ./print-oppcache-summary.sh "$x"
    echo "-------------------"
done

