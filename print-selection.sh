#!/bin/env bash

# Example to print refactoring argument "selection" given by "5017 9" ("offset length")
# ./<SCRIPT> 5017 9 <path>/org/jacop/constraints/Constraint.java

eval "cat $3 | tail -c+$1 | head -c$2"

