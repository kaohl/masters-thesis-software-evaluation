#!/bin/env bash

# This script can be used with 'find -exec' to locate all
# occurrences of <KEYWORD> within regular files in the
# specified filetree.
#
# The first argument is the text to search for, and the second
# argument is the file to search.
#
# Example:
#   find . -exec 'bash' 'find_all_occurrences.sh' '<KEYWORD>' '{}' ';'
#

test -f $2 && grep -iH $1 $2
