#!/bin/env python3

import argparse
import configuration
import itertools
import logging
import os
import random
from pathlib import Path
from random import randrange
import shutil
from subprocess import TimeoutExpired
import tempfile

from executor import load_state, save_state, do_files
import opportunity_cache
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
    'luindex'  : ['lucene'],
    'jacop'    : ['jacop'],
    'xalan'    : ['xalan']
}

def x_location(args):
    return Path(args.data)

def get_experiments(args):
    xs = []
    for dir, folders, files in os.walk(x_location(args)):
        for x in folders:
            if x == 'steering' or x == 'data':
                continue
            xs.append(x)
        break
    return xs

def get_x_workloads(args, x):
    bmwl = []
    for dir_1, bms, files_1 in os.walk(x_location(args) / x / 'workloads'):
        for bm in bms:
            for dir_2, workloads, files_2 in os.walk(x_location(args) / x / 'workloads' / bm):
                for workload in workloads:
                    bmwl.append((bm, workload))
                break
        break
    return bmwl

def get_x_bm_wl_lists(args, x, bm, workload):
    lists = dict()
    for dir, folders, files in os.walk(x_location(args) / x / 'workloads' / bm / workload / 'lists'):
        for name in folders:
            lists[name] = Path(dir) / name / 'descriptors.txt'
        break
    return lists

#def get_workloads(args):
#    bmwl = []
#    for dir_1, bms, files_1 in os.walk(x_folder(args) / 'workloads'):
#        for bm in bms:
#            for dir_2, workloads, files_2 in os.walk(x_folder(args) / 'workloads' / bm):
#                for workload in workloads:
#                    bmwl.append((bm, workload))
#                break
#        break
#    return bmwl
#
def get_x_workload_configuration(args, x, bm, workload):
    config = configuration.Configuration().load(x_location(args) / x / 'workloads' / bm / workload / 'parameters.txt')

    # Note, probably a bad idea to have defaults here since it affects the configuration ID.

    if config.bm() is None:
        raise ValueError("Missing benchmark name in configuration")

    if config.bm_version() is None:
        raise ValueError("Missing benchmark version in configuration")

    if config.bm_workload() is None:
        raise ValueError("Missing workload name in benchmark configuration")

    return config

def add_x_workload_steering(args, configuration, workspace_src):
    target  = workspace_src / 'methods.config'
    if target.exists():
        return
    methods = steering.get_all_sampled_methods(x_location(args) / 'steering', configuration)
    with open(target, 'w') as f:
        for method in methods:
            for filter_text in _method_filters[configuration.bm()]:
                if method.find(filter_text) != -1:
                    f.write(method + os.linesep)
                    break

def add_x_workspace_configuration(args, x, bm, workload, workspace):
    src           = workspace / 'assets/src'
    config        = x_location(args) / x / 'workloads' / bm / workload / 'config'
    configuration = get_x_workload_configuration(args, x, bm, workload)
    src.mkdir(parents = True, exist_ok = True)
    add_x_workload_steering(args, configuration, src)
    # Copy workspace configuration for top-level targeted refactoring
    # (not always provided; lists of packages and units).
    for dir, folders, files in os.walk(config):
        for file in files:
            shutil.copy2(Path(dir) / file, src / file)

def generate_descriptor_lists(args, x, bm, workload):
    cache_location = x_location(args) / x / 'workspaces' / bm / workload / 'workspace' / 'oppcache'
    lists_location = x_location(args) / x / 'workloads' / bm / workload / 'lists'
    opportunity_cache.ListsGenerator.generate_lists(cache_location, lists_location)

def create_workspace(args, x, bm, workload):
    workspace = x_location(args) / x / 'workspaces' / bm / workload / 'workspace'
    if workspace.exists():
        print("Workspace already exists", '/'.join([x, bm, workload]))
        return
    add_x_workspace_configuration(args, x, bm, workload, workspace)
    ws_script.create_workspace_in_location(f"dacapo:{bm}:1.0", workspace)
    generate_descriptor_lists(args, x, bm, workload)

def create_workspaces(args):
    for x, b, w in get_arg_xbw_items(args):
        create_workspace(args, x, b, w)

# Usage:
#  ./evaluation.py [--data <data=experiments>] --x <x> --create
#
def create(args):
    create_workspaces(args)

# ATTENTION: This function will execute in a worker process. 
def _refactor_proxy(workspace, data, descriptor):
    if data.exists():
        # TODO: Would it be safe to use 'log' here when we are in a different process?
        print(f"WARNING: Refactoring already exists: ID={descriptor.id()}; DATA={str(data)}")
        return
    ws_script.refactor(workspace, data, descriptor)

def _create_refactor_task(workspace, data, line, counter):
    # Note: If line parsing fails, try removing the persisted
    #       file state written in the data folder. The issue
    #       is likely that there is state preserved from a
    #       previous workspace setup that is no longer valid.
    descriptor = opportunity_cache.RefactoringDescriptor(line)
    data       = data / descriptor.opportunity_id() / descriptor.id()
    if data.exists():
        return None, None

    # We count here, before going into the worker.
    counter['count'] = counter['count'] + 1

    func = _refactor_proxy
    argv = (workspace, data, descriptor)
    return (func, argv), descriptor.id()

# Usage:
#  ./evaluation.py --data <data> --xs <xs> --bs <bs> --ws <wl> --ls <ls> --n <n>
#
def refactor(args):
    data    = x_location(args) / 'data'
    limit   = args.n if args.n > 1 else 1
    lists   = get_arg_xbwlp_items(args)
    for x, bm, workload, name, path in lists:
        print("Refactor", x, bm, workload, name, path)
        counter              = {'count' : 0}
        data_bm              = data / bm
        state_file           = data_bm / 'state.json'
        files                = [str(path)]
        tell                 = load_state(state_file, files)
        workspace            = x_location(args) / x / 'workspaces' / bm / workload / 'workspace'
        parse_task_from_line = lambda line: _create_refactor_task(workspace, data_bm, line, counter)
        while counter['count'] < limit:
            print("Select refactorings from file: ", path)
            count_before = counter['count']
            do_files(files, tell, parse_task_from_line)
            count_after  = counter['count']
            # Note, progress could have been made even if we created no new tasks.
            # For example, shared descriptors between experiments and workloads.
            # This would make the read state progress for this file but no new
            # refactorings created. Therefore, we always save the state even
            # if it appears we made no progress. However, we should still break,
            # because, if no new tasks were created then we have reached the end
            # of the current list.
            print("Save file state:", path)
            save_state(state_file, tell)
            if count_after == count_before:
                print("Reached the end of list: ", path)
                break # Could not make any progress. List is done.

def prime_import_location(args, x, configuration, location, data):
    # Assume that we have workspaces available.
    # However, at this point we are only interested
    # in the orignal '-build.zip' files and patches.
    ws = x_location(args) / x / 'workspaces' / configuration.bm() / configuration.bm_workload() / 'workspace'
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

def build_and_benchmark(args, x, configuration, data_location, capture_flight_recording = True):
    global log

    bm                 = configuration.bm()
    workload           = configuration.bm_workload()

    store              = data_location / 'stats' / configuration.params_id()
    failure            = store / 'FAILURE'
    success            = store / 'SUCCESS'
    timeout_hint       = store / 'TIMEOUT'
    generic_hint       = store / 'GENERIC'
    jfr_save           = store / 'flight.jfr'
    metrics_save       = store / 'metrics.txt'
    configuration_save = store / 'configuration.txt'

    store.mkdir(parents = True, exist_ok = True)
    configuration.store(configuration_save)

    try:
        clean = True
        with tempfile.TemporaryDirectory(delete = True, dir = 'temp') as location:
            import_dir    = Path(location)
            deploy_dir    = Path(location) / 'deployment'
            jfr_file      = Path(location) / 'flight.jfr'
            deploy_dir.mkdir()
            prime_import_location(args, x, configuration, import_dir, data_location)
            bm_script.deploy_benchmark(configuration, clean, deploy_dir, import_dir)

            # Capture execution time with flight recording disabled.
            exectime = bm_script.run_benchmark(configuration, deploy_dir, False, None)

            with open(metrics_save, 'w') as f:
                f.write("EXECUTION_TIME=" + str(exectime) + os.linesep)

            # ATTENTION
            # The captured flight recording is not for the benchmark
            # run that produced the captured execution time.

            if capture_flight_recording:
                print("Running again to capture flight recording")
                bm_script.run_benchmark(configuration, deploy_dir, True, str(jfr_file))
                shutil.copy2(jfr_file, jfr_save)

            with open(success, 'w'):
                pass
        return True
    except AttributeError as e:
        raise e
    except TypeError as e:
        raise e
    except TimeoutExpired as e:
        log.warning("--- Benchmark failure (timeout) ---")
        log.warning("Please tune configured timeouts, if needed.")
        log.warning("The error has been written to the FAILURE file.")
        log.warning("data: %s", str(store))
        log.warning("conf: %s", str(configuration._values))
        log.warning("-------------------------")
        with open(failure, 'w') as f:
            f.write(str(e))
        with open(timeout_hint, 'w') as e:
            pass
    except Exception as e:
        log.warning("--- Benchmark failure (generic) ---")
        log.warning("The error has been written to the FAILURE file.")
        log.warning("data: %s", str(store))
        log.warning("conf: %s", str(configuration._values))
        log.warning("-------------------------")
        with open(failure, 'w') as f:
            f.write(str(e))
        with open(generic_hint, 'w') as f:
            pass
    return False

def get_valid_configurations_of(args, x, bm, workload):
    configs    = []
    config     = get_x_workload_configuration(args, x, bm, workload)
    has_errors = False
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
        configs.append(c)
    if has_errors:
        raise ValueError("Bad configuration")
    return configs

#def get_valid_configurations(args, x):
#    configs    = []
#    has_errors = False
#    for (bm, workload) in get_x_workloads(args, x):
#        configs.append(((x, bm, workload), []))
#        config = get_x_workload_configuration(args, x, bm, workload)
#        for c in config.get_all_combinations():
#            try:
#                if not c.is_valid():
#                    continue
#            except TypeError as e:
#                raise e
#            except AttributeError as e:
#                raise e
#            except Exception as e:
#                log.error(str(e))
#                has_errors = True
#                continue
#            configs[-1][1].append(c)
#    if has_errors:
#        raise ValueError("Bad configuration")
#    return configs

def get_benchmark_execution_plan(args):
    # Note, sets of refactoring opportunities and configurations for a benchmark
    # may overlap between experiments and workloads. Therefore, we check so that
    # we only include each benchmark configuration once per refactoring.
    plan           = []
    keys           = set()
    configurations = dict()
    for x, b, w, l_name, l_path in get_arg_xbwlp_items(args):
        if not (x, b, w) in configurations:
            # All lists in the same (x,b,w)-tuple share the configuration set.
            # All refactorings on all lists in the same (x,b,w)-tuple should be benchmarked with these configurations.
            configurations[(x, b, w)] = get_valid_configurations_of(args, x, b, w)
        if not l_path.exists():
            continue
        with open(l_path, 'r') as f:
            for line in f:
                descriptor  = opportunity_cache.RefactoringDescriptor(line)
                opportunity = descriptor.opportunity_id()
                refactoring = descriptor.id()
                data        = x_location(args) / 'data' / b / opportunity / refactoring
                if not data.exists():
                    continue # Scan remainder of list just to be sure. (Different seeding parameters could move things around.)
                for dir1, executions, files1 in os.walk(data):
                    for execution in executions:
                        if (Path(dir1) / execution / 'FAILURE').exists():
                            continue # The refactoring could not be applied.
                        for configuration in configurations[(x, b, w)]:
                            stats_c = Path(dir1) / execution / 'stats' / configuration.params_id()
                            key     = (b, opportunity, refactoring, execution, configuration.params_id())
                            # NOTE: 'key' MUST NOT include 'x' because refactorings of a
                            #        benchmark can be shared between experiments.
                            # NOTE:  Opportunities and refactorings can be shared between
                            #        benchmark workloads. We separate their measurements
                            #        by including the workload name in the configuration.
                            #        Therefore, 'params_id' must depend on the workload.
                            if not stats_c.exists() and not key in keys:
                                # Here we can include 'x' in the result. ('w' is not needed.)
                                plan.append((x, b, opportunity, refactoring, execution, configuration))
                                keys.add(key)
                    break
    random.Random(0).shuffle(plan)
    return plan

# Usage:
#   ./evaluation.py [--data <data=experiments>] --xs <xs> --bs <bs> --n <n>
#
def benchmark(args):
    i = 0
    n = args.n

    if n <= 0:
        raise ValueError("Please specify the number of benchmark executions to run using a positive integer.")

    for (x, bm, opportunity, refactoring, execution, configuration) in get_benchmark_execution_plan(args):
        print()
        print(f"Benchmark ({i+1}/{n}) {'/'.join([bm, opportunity, refactoring, execution, 'stats', configuration.params_id()])}")
        print()
        data_location = Path(os.getcwd()) / x_location(args) / 'data' / bm / opportunity / refactoring / execution
        enable_jfr    = False
        build_and_benchmark(args, x, configuration, data_location, enable_jfr)
        i = i + 1
        if i >= n:
            break

# Print result objects to stdout.
# See 'results.py' for CSV files and statistics.
#def report(args):
#    for (bm, workload) in get_workloads(args):
#        for dir1, lists, files1 in os.walk(x_folder(args) / 'data' / bm / workload):
#            for list in lists:
#                print("---", bm, workload, list, "---")
#                for dir2, indices, files2 in os.walk(Path(dir1) / list):
#                    for index in indices:
#                        for dir3, refactorings, files3 in os.walk(Path(dir2) / index):
#                            for refactoring in refactorings:
#                                for dir4, ids, files4 in os.walk(Path(dir3) / refactoring / 'stats'):
#                                    for id in ids:
#                                        if (Path(dir4) / id / 'FAILURE').exists():
#                                            continue
#                                        config  = configuration.Configuration().load(Path(dir4) / id / 'configuration.txt')
#                                        metrics = configuration.Metrics().load(Path(dir4) / id / 'metrics.txt')
#                                        print({ **{ 'data' : list + '/' + index }, **config._values, **metrics._values })
#                                    break
#                            break
#                    break
#                print("-------------------------------------")
#            break

def print_configurations(args):
    for x, b, w in get_arg_xbw_items(args):
        for configuration in get_valid_configurations_of(args, x, b, w):
            print(x, b, w, configuration._values)

def print_execution_plan(args):
    for (x, bm, opportunity, refactoring, execution, configuration) in get_benchmark_execution_plan(args):
        print(bm, opportunity, refactoring, execution, configuration._values)

# Return [(x, b, w, l, p)] filtered by specified arguments.
def get_arg_xbwlp_items(args):
    # An empty set means "include all".
    xs    = set(get_arg_experiments(args))
    bs    = set(get_arg_benchmarks(args))
    ws    = set(get_arg_workloads(args))
    ls    = set(get_arg_lists(args))
    items = []
    for x in get_experiments(args):
        if len(xs) > 0 and not x in xs:
            continue
        for b, w in get_x_workloads(args, x):
            if len(bs) > 0 and not b in bs:
                continue
            if len(ws)> 0  and not w in ws:
                continue
            for l, path in get_x_bm_wl_lists(args, x, b, w).items():
                if len(ls) > 0 and not l in ls:
                    continue
                items.append((x, b, w, l, path))
    return items

# Return [(x, b, w)] filtered by specified arguments.
def get_arg_xbw_items(args):
    # An empty set means "include all".
    xs    = set(get_arg_experiments(args))
    bs    = set(get_arg_benchmarks(args))
    ws    = set(get_arg_workloads(args))
    items = []
    for x in get_experiments(args):
        if len(xs) > 0 and not x in xs:
            continue
        for b, w in get_x_workloads(args, x):
            if len(bs) > 0 and not b in bs:
                continue
            if len(ws)> 0  and not w in ws:
                continue
            items.append((x, b, w))
    return items

def get_arg_experiments(args):
    return args.xs

def get_arg_benchmarks(args):
    return args.bs

def get_arg_workloads(args):
    return args.ws

def get_arg_lists(args):
    return args.ls

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # Experiments, Benchmarks, Workloads, and Lists.
    parser.add_argument('--xs', nargs = '+', default = [], required = False,
        help = "Limit operation to specified experiments")
    parser.add_argument('--bs', nargs = '+', default = [], required = False,
        help = "Limit operation to specified benchmarks")
    parser.add_argument('--ws', nargs = '+', default = [], required = False,
        help = "Limit operation to specified workloads")
    parser.add_argument('--ls', nargs = '+', default = [], required = False,
        help = "Limit operation to specified lists")
    parser.add_argument('--data', required = False, default = 'experiments',
        help = "Location where experiments are stored. Defaults to 'experiments'.")

    # Operation options.
    parser.add_argument('--create', required = False, action = 'store_true',
        help = "Create experiment workspace from specified template")
    parser.add_argument('--refactor', required = False, action = 'store_true',
        help = "Refactor specified experiment workspace")
    parser.add_argument('--benchmark', required = False, action = 'store_true',
        help = "Benchmark refactoring(s)")
    parser.add_argument('--n', required = False, type = int, default = 1,
        help = "The number of refactorings or benchmarks to run.")

    # Print/Show options.
    parser.add_argument('--show-configurations', required = False, action = 'store_true',
        help = "Print all valid configurations to standard out")
    parser.add_argument('--show-execution-plan', required = False, action = 'store_true',
        help = "Print all pending benchmark executions")
    #parser.add_argument('--report', required = False, action = 'store_true',
    #    help = "Print statistics")

    # Generators.
    parser.add_argument('--generate-lists', required = False, action = 'store_true',
        help = "Generate lists on existing workspace")

    args = parser.parse_args()

    if args.generate_lists:
        for x, b, w in get_arg_xbw_items(args):
            generate_descriptor_lists(args, x, b, w)
        exit(0)

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
        refactor(args)
    elif args.report:
        report(args)
    else:
        parser.print_help()

