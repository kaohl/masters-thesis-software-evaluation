#!/bin/env bash

#
# Run one round of refactoring and benchmarking on each list.
#

./scripts/jacop.all.sh
./scripts/batik.all.sh
./scripts/xalan.all.sh
./scripts/lusearch.all.sh
./scripts/luindex.all.sh

