#!/bin/env python

import argparse
import os
import subprocess

import collect_jfr_metrics

# Return a dictionary mapping method signature to sample count
# given a dictionary from (method signature, line number) pairs
# to sample count.
def get_method_count(method_line__count):
    method__count = dict() # method => count
    for (m, l), c in method_line__count.items():
        if not m in method__count:
            method__count[m] = c
        else:
            method__count[m] = method__count[m] + c
    return method__count

# Return a dictionary mapping (method signature, line number)
# pairs to sample count.
def get_method_line_count(jfr_file):
    cmd = ' '.join([
        'jfr',
        'print',
        '--events',
        'jdk.ExecutionSample',
        '--stack-depth',
        '1',
        jfr_file,
        #'|',
        #'grep',
        #'-E',
        #bm
    ])
    result = subprocess.run(
        cmd,
        shell      = True,
        executable = '/bin/bash',
        stdout     = subprocess.PIPE,
        stderr     = subprocess.STDOUT
    )
    methods = dict() # (name, lino) => count
    for line in result.stdout.decode('utf-8').split(os.linesep):
        if line == '':
            continue
        try:
            method, lino = line.split(" line: ")
            method = method.strip()
            lino   = lino.strip()
            if not (method, lino) in methods:
                methods[(method, lino)] = 1
            else:
                methods[(method, lino)] = methods[(method, lino)] + 1
        except:
            #print("Could not parse line:", line)
            pass
    return methods

def get_hot_methods_based_on_method_samples(method__count, threshold = 2):
    hot_methods = dict()
    for m, c in method__count.items():
        if c < threshold:
            #print("Exclude [ Below threshold (" + str(c) + ") ]", m)
            continue
        hot_methods[m] = c
    return hot_methods

def get_hot_methods_based_on_sample_fraction(method__count, threshold = 0.05):
    hot_methods = dict()
    total = 0
    for m, c in method__count.items():
        total = total + c
    for m, c in method__count.items():
        frac = c / total
        if frac < threshold:
            continue
        hot_methods[m] = (c, frac)
    return hot_methods

def get_compiled_methods(jfr_file):
    methods      = set()
    compilations = collect_jfr_metrics.get_compilations(jfr_file)
    for m, compilation_attrs in compilations.items():
        methods.add(m)
    return methods

# Return dict from method signature to sample count.
def get_method_samples(jfr_file):
    method_line__count = get_method_line_count(jfr_file)
    method__count      = get_method_count(method_line__count)
    return method__count

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    #parser.add_arugment('--sample-packages', required = True,
    #    help = "The package names to look for in the benchmark
    parser.add_argument('--sample-threshold', required = False, type=int, default = 2,
        help = "The method sample threshold for a method to be considered 'hot'.")
    parser.add_argument('--jfr-file', required = True,
        help = "The .jfr file to read events from.")
    parser.add_argument('--outfile', required = True,
        help = "A file into which hot qualified method names are written.")
    args = parser.parse_args()

    method_line__count = get_method_line_count('batik', args.jfr_file)
    method__count      = get_method_count(method_line__count)
    pad_count          = lambda str_c: str_c if len(str_c) >= 8 else (' '*(8-len(str_c)) + str_c)
    print("Found", str(len(method__count)), "methods")
    for m, c in reversed(sorted(method__count.items(), key = lambda it: it[1])):
        print(pad_count(str(c)), m)

    hot_methods = get_hot_methods_based_on_method_samples(method__count, args.sample_threshold)
    print("Found hot methods", len(hot_methods))
    for m, c in reversed(sorted(hot_methods.items(), key = lambda it: it[1])):
        print(pad_count(str(c)), m)

    compilations = get_compiled_methods(args.jfr_file)
    print("Found", len(compilations), "compilations")
    for m in compilations:
        print("Compilation (REFS " + pad_count(str(hot_methods[m] if m in hot_methods else 0)) + ")", m)

    with open(args.outfile, 'w') as f:
        # TODO: May want to weight entries in these two sets.
        for m, c in reversed(sorted(hot_methods.items(), key = lambda it: it[1])):
            f.write(m + os.linesep)
        for m in compilations:
            f.write(m + os.linesep)

