#!/bin/env python3

import argparse
import os
from pathlib import Path
import shutil
import tempfile

import run_benchmark as bm_script
import collect_hot_methods as jfr

def get_all_sampled_methods(cache_location, configuration):
    return [m for (m,_,_) in _filter_methods(cache_location, configuration, 0.0)]

def decimals(num):
    s = str(num)
    n = len(s[s.rfind('.')+1:])
    return n

def get_cache_location(cache_location, configuration):
    return cache_location / configuration.id()

def get_cache_stem(configuration):
    return '-'.join([configuration.bm(), configuration.bm_workload()])

def get_cache_methods(cache_location, configuration):
    return get_cache_location(cache_location, configuration) / (get_cache_stem(configuration) + '.methods.summary.txt')

def get_cache_jfr(cache_location, configuration):
    return get_cache_location(cache_location, configuration) / (get_cache_stem(configuration) + '.jfr')

# Return list of methods with a sample count
# above or equal to the specified threshold.
def _filter_methods(cache_location, configuration, sample_threshold):
    total, methods = _load_method_samples(cache_location, configuration)
    filtered_methods = []
    n                = decimals(sample_threshold)
    for m, c in methods:
        frac1 = c / total
        frac2 = round(frac1, n)
        if frac2 >= sample_threshold:
            filtered_methods.append((m, c, frac2))
    return filtered_methods

def _load_method_samples(cache_location, configuration):
    summary  = get_cache_methods(cache_location, configuration)
    if not summary.exists():
        _generate_steering_for_workload(cache_location, configuration)

    total   = 0
    methods = []
    with open(summary, 'r') as f:
        for line in f:
            sep      = line.rfind(')')
            method   = line[:sep + 1]
            samples  = int(line[sep+2:])

            total                         = total + samples
            methods.append((method.strip(), samples))
    return total, methods

def _save_method_samples(cache_location, configuration, method__count):
    summary = get_cache_methods(cache_location, configuration)
    with open(summary, 'w') as f:
        for m, c in reversed(sorted(method__count.items(), key = lambda it: it[1])):
            f.write('{},{}'.format(m, c) + os.linesep)

def _generate_steering_for_workload(cache_location, configuration):
    location = get_cache_location(cache_location, configuration)
    if not location.exists():
        location.mkdir(parents = True)

    summary  = get_cache_methods(cache_location, configuration)
    jfr_save = get_cache_jfr(cache_location, configuration)
    clean    = True
    with tempfile.TemporaryDirectory(delete = True, dir = 'temp') as location:
        temp_location = Path(location)
        deploy_dir    = temp_location / 'deployment'
        jfr_file      = temp_location / 'flight.jfr'
        deploy_dir.mkdir()
        bm_script.deploy_benchmark(configuration, clean, deploy_dir)
        bm_script.run_benchmark(configuration, deploy_dir, True, str(jfr_file))

        # Save the jfr file used to compute steering.
        shutil.copy2(jfr_file, jfr_save)

        method__count = jfr.get_method_samples(str(jfr_file))

        _save_method_samples(cache_location, configuration, method__count)

#def _main(args):
#    bm        = args.bm
#    workload  = args.workload
#    threshold = args.threshold
#    methods   = _filter_methods(bm, workload, threshold)
#
#    pad_count = lambda str_c: str_c if len(str_c) >= 8 else (' '*(8-len(str_c)) + str_c)
#
#    n = decimals(threshold)
#    
#    if not args.table and not args.methods:
#        print("--- SAMPLES(n), n/N, METHOD ---")
#        for (m, c, frac) in methods:
#            print(pad_count(str(c)), ('{:.' + str(n) + 'f}').format(round(frac, n)), m)
#        print("-------------------------------")
#
#    if args.methods:
#        for (m, c, frac) in methods:
#            print(m)
#
#    if args.table:
#        for (m, c, frac) in methods:
#            print(pad_count(str(c)), '&', ('{:.' + str(n) + 'f}').format(round(frac, n)), '&', m)
#    
#if __name__ == '__main__':
#    parser = argparse.ArgumentParser()
#    parser.add_argument('--bm', required = True,
#        help = "Benchmark name")
#    parser.add_argument('--workload', required = True,
#        help = "The workload to run when benchmarking.")
#    parser.add_argument('--threshold', required = False, type=float, default=0.0,
#        help = "The method sample threshold to apply in range [0, 1].")
#    parser.add_argument('--methods', required = False, action = 'store_true',
#        help = "If specified, the output will be a list of methods ordered by decreasing sample count.")
#    parser.add_argument('--table', required = False, action = 'store_true',
#        help = "Print table rows for report.")
#    args = parser.parse_args()
#
#    _main(args)
