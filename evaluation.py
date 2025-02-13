#!/bin/env python3

import argparse
import configuration
import os
from pathlib import Path
from random import randrange
import shutil
import tempfile

import run_benchmark as bm_script
import steering
import workspace     as ws_script

def x_folder(args):
    return Path(args.x_location) / args.x

def get_workloads(args):
    bmwl = []
    for dir_1, bms, files_1 in os.walk(x_folder(args) / 'workloads'):
        for bm in bms:
            for dir_2, workloads, files_2 in os.walk(x_folder(args) / 'workloads' / bm):
                for workload in workloads:
                    bmwl.append((bm, workload))
                break
        break
    return bmwl

def get_workload_configuration(args, bm, workload):
    return configuration.Configuration().load(x_folder(args) / 'workloads' / bm / workload / 'parameters.txt')

def add_workload_steering(args, bm, workload, workspace_src):
    target  = workspace_src / 'methods.config'
    if target.exists():
        return
    methods = steering.get_all_sampled_methods(bm, workload)
    with open(target, 'w') as f:
        for method in methods:
            if method.find(bm) != -1:
                f.write(method + os.linesep)

def add_workspace_configuration(args, bm, workload, workspace):
    src    = workspace / 'assets/src'
    config = x_folder(args) / 'workloads' / bm / workload / 'config'
    src.mkdir(parents = True, exist_ok = True)
    add_workload_steering(args, bm, workload, src)
    for dir, folders, files in os.walk(config):
        for file in files:
            shutil.copy2(Path(dir) / file, src / file)

def create_workspace(args, bm, workload):
    workspace = x_folder(args) / 'workspaces' / bm / workload / 'workspace'
    add_workspace_configuration(args, bm, workload, workspace)
    ws_script.create_workspace_in_location("dacapo:{}:1.0".format(bm), workspace)

def create_workspaces(args):
    for bm, workload in get_workloads(args):
        create_workspace(args, bm, workload)

# Usage:
#  ./evaluation.py --x <ex> --create
#
def create(args):
    create_workspaces(args)

# Usage:
#  ./evaluation.py --bm <bm> --x <ex> --tag <tag> --refactor --type <refactoring type> [ refactoring options ]
#
def refactor(args, proc_id):
    if not 'bm' in args:
        raise ValueError("Please specify a benchmark.")

    if not 'workload' in args:
        raise ValueError("Please specify a workload.")

    bm        = args.bm
    workload  = args.workload
    workspace = x_folder(args) / 'workspaces' / bm / workload / 'workspace'
    data      = x_folder(args) / 'data' / bm / workload

    # TODO: Allow user to specify refactoring options on command line.
    options = configuration.get_random_refactoring_configuration()

    ws_script.refactor(workspace, data, options, proc_id)

def prime_import_location(args, configuration, location, data):
    # Assume that we have workspaces available.
    # However, at this point we are only interested
    # in the orignal '-build.zip' files and patches.
    ws = x_folder(args) / 'workspaces' / configuration.bm() / configuration.workload() / 'workspace'
    for root, dirs, files in os.walk(ws):
        for file in files:
            if not file.endswith("-build.zip"):
                continue

            with tempfile.TemporaryDirectory(dir = location) as tmp:
                temp           = Path(tmp)
                stem           = file[:file.rfind('-')]
                main_jar_patch = data / (stem + "-main-src.jar.patch")
                test_jar_patch = data / (stem + "-test-src.jar.patch")

                tools.unzip(ws / file, tmp)

                if main_jar_patch.exists():
                    patch.apply_patch(main_jar_patch, temp / 'src/main/java')

                if test_jar_patch.exists():
                    patch.apply_patch(test_jar_patch, temp / 'src/test/java')

                tools.zip(temp, location / file)
        break

def build_and_benchmark(args, configuration, data_location, capture_flight_recording = True):
    bm                 = configuration.bm()
    workload           = configuration.workload()

    store              = data_location / 'stats' / configuration.id()
    jfr_save           = store / 'flight.jfr'
    metrics_save       = store / 'metrics.txt'
    configuration_save = store / 'configuration.txt'

    clean = True
    with tempfile.TemporaryDirectory(delete = False, dir = 'temp') as location:
        import_dir    = Path(location)
        deploy_dir    = Path(location) / 'deployment'
        jfr_file      = Path(location) / 'flight.jfr'
        deploy_dir.mkdir()
        prime_import_location(args, configuration, import_dir, data_location)
        bm_script.deploy_benchmark(args, configuration, clean, deploy_dir, import_dir)

        # Capture execution time with flight recording disabled.
        exectime = bm_script.run_benchmark(args, configuration, deploy_dir, False, None)

        store.mkdir(parents = True, exist_ok = True)

        with open(metrics_save, 'w') as f:
            f.write("EXECUTION_TIME=" + str(exectime) + os.linesep)

        configuration.store(configuration_save)

        # ATTENTION
        # The captured flight recording is not for the benchmark
        # run that produced the captured execution time.

        if capture_flight_recording:
            print("Running again to capture flight recording")
            bm_script.run_benchmark(args, configuration, deploy_dir, True, str(jfr_file))
            shutil.copy2(jfr_file, jfr_save)

# TODO: Not sure caching the plan is needed.
def create_benchmark_execution_plan(args):
    errors = []
    plan   = []
    for (bm, workload) in get_workloads(args):
        config = get_workload_configuration(args, bm, workload)
        # Add options given by resource organisation.
        config.bm(bm)
        config.bm_workload(workload)
        for c in config.get_all_combinations():
            try:
                if not config.is_valid():
                    continue
            except OSError as e:
                errors.append(e)
                continue
            for dir, folders, files in os.walk(x_folder(args) / 'data' / bm / workload):
                for refactoring in folders:
                    stats_c = Path(dir) / refactoring / 'stats' / c.id()
                    if not stats_c.exists():
                        plan.append((bm, workload, refactoring, c))
                break
    if len(errors) > 0:
        raise ValueError("Configuration Errors", errors)
    #plan_file = x_folder(args) / 'benchmark-execution-plan.txt'
    #with open(plan_file, 'w') as f:
    #    for (bm, workload, configuration) in plan:
    #        f.write(','.join([bm, workload, configuration.id()]))
    return plan#, configurations

def get_benchmark_execution_plan(args):
    return create_benchmark_execution_plan(args)

# Usage:
#   ./evaluation.py --bm <bm> --x <ex> --tag <tag> --benchmark [--data <tmp...>]
#
def benchmark(args):
    # TODO: Do we need a better strategy to avoid generating duplicates of refactorings?
    # TODO: Handle benchmark failure.
    i = 0 # TODO: Add as input parameter.
    for (bm, workload, refactoring, configuration) in get_benchmark_execution_plan(args):
        data_location = x_folder(args) / 'data' / bm / workload / refactoring
        build_and_benchmark(args, configuration, data_location)
        i = i + 1
        if i == 5:
            break

def report(args):
    for (bm, workload) in get_workloads(args):
        for dir, refactorings, files in os.walk(x_folder(args) / 'data' / bm / workload):
            for refactoring in refactorings:
                for dir_2, ids, files_2 in os.walk(Path(dir) / refactoring / 'stats'):
                    for id in ids:
                        # TODO: Investigate how input should be formatted for statistics tools.
                        #       Consider letting the user specify the column headers (keys as CSV) and then print CSV rows.
                        config  = configuration.Configuration().load(Path(dir) / refactoring / 'stats' / id / 'configuration.txt')
                        metrics = configuration.Metrics().load(Path(dir) / refactoring / 'stats' / id / 'metrics.txt')
                        print(config._values, metrics._values)
                    break
            break

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x', required = True,
        help = "The experiment name.")
    parser.add_argument('--x-location', required = False, default = 'experiments',
        help = "Location where experiments are stored. Defaults to 'experiments'.")
    parser.add_argument('--bm', required = False,
        help = "Benchmark name")
    parser.add_argument('--workload', required = False,
        help = "Benchmark workload")
    parser.add_argument('--create', required = False, action = 'store_true',
        help = "Create experiment workspace from specified template")
    parser.add_argument('--benchmark', required = False, action = 'store_true',
        help = "Benchmark refactoring(s)")
    parser.add_argument('--data', required = False,
        help = "A specific refactoring folder name") 
    parser.add_argument('--refactor', required = False, action = 'store_true',
        help = "Refactor specified experiment workspace")
    parser.add_argument('--type', required = False,
        help = "Refactoring type")
    parser.add_argument('--report', required = False, action = 'store_true',
        help = "Print statistics")
    args = parser.parse_args()

    if args.create:
        create(args)
    elif args.benchmark:
        benchmark(args)
    elif args.refactor:
        refactor(args, 0)
    elif args.report:
        report(args)
    else:
        parser.print_help()

