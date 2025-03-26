#!/bin/env bash

export DAIVY_HOME=~/daivy
n=`./evaluation.py --show-execution-plan | wc -l`
rm -rf DONE_F DONE_T; ./evaluation.py --benchmark --n "$n" > /dev/null 2>&1; touch DONE_T || touch DONE_F

# Here is a fast test to see that things are working:
#rm -rf DONE_F DONE_T; ./evaluation.py --benchmark --xs xalan --bs xalan --ws small
