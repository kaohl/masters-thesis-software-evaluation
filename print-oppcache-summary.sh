#!/bin/env bash

cache=$1

if [ "$cache" == "" ]; then
    echo "Please specify cache location."
    exit 1
fi

# Note, there is no distinction between method parameters and local variables.
# Both are stored with id: org.eclipse.jdt.ui.rename.local.variable. However,
# there should be a meta attribute 'is_param' that tells us when a rename local
# refers to a parameter or not.

declare -a filters=(
    "{\"id\":\"org.eclipse.jdt.ui.inline.constant\"}"
    "{\"id\":\"org.eclipse.jdt.ui.inline.method\"}"
    "{\"id\":\"org.eclipse.jdt.ui.inline.temp\"}"
    "{\"id\":\"org.eclipse.jdt.ui.introduce.indirection\"}"
    "{\"id\":\"org.eclipse.jdt.ui.rename.field\"}"
    "{\"id\":\"org.eclipse.jdt.ui.rename.local.variable\"}"
    "{\"id\":\"org.eclipse.jdt.ui.rename.method\"}"
    "{\"id\":\"org.eclipse.jdt.ui.rename.type\"}"
    "{\"id\":\"org.eclipse.jdt.ui.rename.type.parameter\"}"
    "{\"id\":\"org.eclipse.jdt.ui.extract.constant\"}"
    "{\"id\":\"org.eclipse.jdt.ui.extract.method\"}"
    "{\"id\":\"org.eclipse.jdt.ui.extract.temp\"}"
)

for filter in "${filters[@]}"
do
    n=$(./opportunity_cache.py --cache $cache --filter $filter | wc -l)
    echo "FILTER=$filter; $n"
done

