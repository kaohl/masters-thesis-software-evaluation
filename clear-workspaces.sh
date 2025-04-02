#/bin/env bash

rm -rf `find experiments -iname workspaces`
rm -rf `find experiments -iwholename **/lists/*/descriptors.txt`
rm -rf `find experiments/data -iname state.json`

