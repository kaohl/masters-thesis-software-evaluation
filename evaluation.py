#!/bin/env python3

import argparse
import configuration
import logging
import os
from pathlib import Path
from random import randrange
import shutil
import tempfile

import patch
import run_benchmark as bm_script
import steering
import tools
import workspace     as ws_script

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
log = logging.getLogger(__name__)

_method_filters = {
    'batik'    : ['batik'],
    'lusearch' : ['lucene'],
    'luindex'  : ['lucene']
}

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
    config = configuration.Configuration().load(x_folder(args) / 'workloads' / bm / workload / 'parameters.txt')
    # Add default values given by resource organisation.
    if config.bm() is None:
        config.bm(bm)

    if config.bm_version() is None:
        config.bm_version('1.0')

    if config.bm_workload() is None:
        config.bm_workload(workload)

    return config

def add_workload_steering(args, bm, workload, workspace_src):
    target  = workspace_src / 'methods.config'
    if target.exists():
        return
    methods = steering.get_all_sampled_methods(bm, workload)
    with open(target, 'w') as f:
        for method in methods:
            for filter_text in _method_filters[bm]:
                if method.find(filter_text) != -1:
                    f.write(method + os.linesep)
                    break

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
    if args.bm is None:
        raise ValueError("Please specify a benchmark.")

    if args.workload is None:
        raise ValueError("Please specify a workload.")

    if args.n <= 0:
        raise ValueError("Please specify the number of refactorings to generate using a positive integer.")
        return

    bm        = args.bm
    workload  = args.workload
    workspace = x_folder(args) / 'workspaces' / bm / workload / 'workspace'
    data      = x_folder(args) / 'data' / bm / workload

    i = 0
    n = args.n
    while i < n:
        # TODO: Allow user to specify refactoring options on command line.
        options = configuration.get_random_refactoring_configuration()
        ws_script.refactor(workspace, data, options, proc_id)
        i = i + 1

def prime_import_location(args, configuration, location, data):
    # Assume that we have workspaces available.
    # However, at this point we are only interested
    # in the orignal '-build.zip' files and patches.
    ws = x_folder(args) / 'workspaces' / configuration.bm() / configuration.bm_workload() / 'workspace'
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
    global log

    bm                 = configuration.bm()
    workload           = configuration.bm_workload()

    store              = data_location / 'stats' / configuration.id()
    failure            = store / 'FAILURE'
    success            = store / 'SUCCESS'
    jfr_save           = store / 'flight.jfr'
    metrics_save       = store / 'metrics.txt'
    configuration_save = store / 'configuration.txt'

    store.mkdir(parents = True, exist_ok = True)

    try:
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

            with open(success, 'w'):
                pass
        return True
    except AttributeError as e:
        raise e
    except TypeError as e:
        raise e
    except Exception as e:
        log.warning("Benchmark failure: {}", configuration._values)
        with open(failure, 'w') as f:
            f.write(str(e))
        return False

def get_valid_configurations(args):
    configs    = []
    has_errors = False
    for (bm, workload) in get_workloads(args):
        config = get_workload_configuration(args, bm, workload)
        for c in config.get_all_combinations():
            try:
                if not c.is_valid():
                    continue
            except TypeError as e:
                raise e
            except AttributeError as e:
                raise e
            except Exception as e:
                log.error(str(e))
                has_errors = True
                continue
            configs.append((bm, workload, c))
    if has_errors:
        raise ValueError("Bad configuration")
    return configs

def get_benchmark_execution_plan(args):
    plan = []
    for (bm, workload, configuration) in get_valid_configurations(args):
        for dir, folders, files in os.walk(x_folder(args) / 'data' / bm / workload):
            for refactoring in folders:
                stats_c = Path(dir) / refactoring / 'stats' / configuration.id()
                if not stats_c.exists():
                    plan.append((bm, workload, refactoring, configuration))
            break
    return plan

# Usage:
#   ./evaluation.py --bm <bm> --x <ex> --tag <tag> --benchmark [--data <tmp...>]
#
def benchmark(args):
    #
    # TODO: Do we need a better strategy to avoid generating duplicates of refactorings?
    #
    i = 0
    n = args.n

    if n <= 0:
        raise ValueError("Please specify the number of benchmark executions to run using a positive integer.")

    for (bm, workload, refactoring, configuration) in get_benchmark_execution_plan(args):
        data_location = Path(os.getcwd()) / x_folder(args) / 'data' / bm / workload / refactoring
        build_and_benchmark(args, configuration, data_location)
        i = i + 1
        if i >= n:
            break

def report(args):
    for (bm, workload) in get_workloads(args):
        print("---", bm, workload, "---")
        for dir, refactorings, files in os.walk(x_folder(args) / 'data' / bm / workload):
            for refactoring in refactorings:
                for dir_2, ids, files_2 in os.walk(Path(dir) / refactoring / 'stats'):
                    for id in ids:
                        # TODO: Investigate how input should be formatted for statistics tools.
                        #       Consider letting the user specify the column headers (keys as CSV) and then print CSV rows.
                        config  = configuration.Configuration().load(Path(dir) / refactoring / 'stats' / id / 'configuration.txt')
                        metrics = configuration.Metrics().load(Path(dir) / refactoring / 'stats' / id / 'metrics.txt')
                        print({ **config._values, **metrics._values })
                    break
            print("-------------------------------------")
            break

def print_configurations(args):
    for (bm, workload, configuration) in get_valid_configurations(args):
        print(bm, workload, configuration._values)

def print_execution_plan(args):
    for (bm, workload, refactoring, configuration) in get_benchmark_execution_plan(args):
        print(bm, workload, refactoring, configuration._values)

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
    parser.add_argument('--n', required = False, type = int, default = 1,
        help = "The number of refactorings or benchmarks to run.")
    parser.add_argument('--report', required = False, action = 'store_true',
        help = "Print statistics")
    parser.add_argument('--show-configurations', required = False, action = 'store_true',
        help = "Print all valid configurations to standard out")
    parser.add_argument('--show-execution-plan', required = False, action = 'store_true',
        help = "Print all pending benchmark executions")
    args = parser.parse_args()

    if args.show_configurations:
        print_configurations(args)
        exit(0)

    if args.show_execution_plan:
        print_execution_plan(args)
        exit(0)

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

