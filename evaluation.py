#!/bin/env python3

import argparse
import configuration
import logging
import os
from pathlib import Path
from random import randrange
import shutil
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
    return Path(args.x_location)

#def x_folder(args):
#    return x_location(args) / args.x

def get_experiments(args):
    xs = []
    for dir, folders, files in os.walk(x_location(args)):
        for x in folders:
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
    # Add default values given by resource organisation.
    if config.bm() is None:
        config.bm(bm)

    if config.bm_version() is None:
        config.bm_version('1.0')

    if config.bm_workload() is None:
        config.bm_workload(workload)

    return config

def add_x_workload_steering(configuration, workspace_src):
    target  = workspace_src / 'methods.config'
    if target.exists():
        return
    methods = steering.get_all_sampled_methods(configuration)
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
    add_x_workload_steering(configuration, src)
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
    add_x_workspace_configuration(args, x, bm, workload, workspace)
    ws_script.create_workspace_in_location(f"dacapo:{bm}:1.0", workspace)
    generate_descriptor_lists(args, x, bm, workload)

def get_arg_experiments(args):
    xs = set()
    if not args.x is None:
        xs.add(args.x)
    if not args.xs is None:
        for x in args.xs:
            xs.add(x)
    return xs

def create_workspaces(args):
    for x in get_arg_experiments(args):
        for bm, workload in get_x_workloads(args, x):
            create_workspace(args, x, bm, workload)

# Usage:
#  ./evaluation.py [--data <data=experiments>] --x <x> --create
#
def create(args):
    create_workspaces(args)

# ATTENTION: This function will execute in a worker process. 
def _refactor_proxy(workspace, data, descriptor):
    if data.exists():
        print("EXISTS", descriptor.id())
        return # Nothing to do.
    print("REFACTOR", descriptor.id(), data)
    ws_script.refactor(workspace, data, descriptor)

def _create_refactor_task(workspace, data, line, counter):
    # Note: If line parsing fails, try removing the persisted
    #       file state written in the data folder. The issue
    #       is likely that there is state preserved from a
    #       previous workspace setup that is no longer valid.
    descriptor = opportunity_cache.RefactoringDescriptor(line)
    data       = data / descriptor.opportunity_id() / descriptor.id()
    if data.exists():
        return None

    # We count here, before going into the worker.
    counter['count'] = counter['count'] + 1

    func = _refactor_proxy
    argv = (workspace, data, descriptor)
    return (func, argv)

# Usage:
#  ./evaluation.py --data <data> --xs <xs> --bs <bs> --ws <wl> --ls <ls> --n <n>
#
def refactor(args):
    #if args.bm is None:
    #raise ValueError("Please specify a benchmark.")
    #
    #if args.workload is None:
    #raise ValueError("Please specify a workload.")
    #
    #if args.n <= 0:
    #raise ValueError("Please specify the number of refactorings to generate using a positive integer.")
    #return
    #
    #bm        = args.bm
    #workload  = args.workload

    # Note
    # Because duplications should be remove when assembling the
    # descriptor lists for experiments, there should be no need
    # to use the refactoring ID for folder names. We can use
    # temp folder names and then look at the descriptor to
    # determine which data folders map to each list after
    # the experiment. (Consider using sequentially numbered folders
    # per list (data/<listname>/{1,2,3,4, ...}) so that it is easy
    # to go from descriptor list index to the data folder.

    #lists = dict()
    #for dir, folders, files in os.walk(x_folder(args) / 'workloads' / bm / workload / 'lists'):
    #for name in folders:
    #lists[name] = Path(dir) / name / 'descriptors.txt'
    #break
    #
    #if len(lists) == 0:
    #raise ValueError("There are no descriptor lists defined for", bm, workload)
    #

    #
    # TODO: Get experiment location, experiment names, benchmark names, workload names, and list names from args.
    #
    lists = []
    for x in get_arg_experiments(args):
        for bm, workload in get_x_workloads(args, x):
            workspace = x_location(args) / x / 'workspaces' / bm / workload / 'workspace'
            for name, path in get_x_bm_wl_lists(args, x, bm, workload).items():
                lists.append((x, bm, workload, name, path))

    data    = x_location(args) / 'data'
    counter = {'count' : 0}
    limit   = args.n if args.n > 1 else 1
    while counter['count'] < limit:
        for x, bm, workload, name, path in lists:

            # TODO: Add CLI option to include/exclude experiments, benchmarks, workloads, and lists.
            #       --xps --bms  --wls --lists
            # ./evaluation.py --data experiments --xs jacop --bs jacop --ws mzc18_1 --ls list_1 --n 20
            #
            # The script will create <n> refactorings per specified list and then terminate.
            
            data_bm              = x_location(args) / 'data' / bm
            state_file           = data_bm / 'state.json'
            files                = [str(path)]
            tell                 = load_state(state_file, files)
            parse_task_from_line = lambda line: _create_refactor_task(workspace, data_bm, line, counter)
            do_files(files, tell, parse_task_from_line)
            save_state(state_file, tell)
            if counter['count'] >= limit:
                break

    # ABC
    #descriptors   = dict()
    #list_position = dict()
    #working_set   = set(lists.keys())
    #j = 0
    #while j < args.n and len(working_set) > 0:
    #lst  = [name for name in working_set][randrange(len(working_set))]
    #data = x_folder(args) / 'data' / bm / workload / lst
    #if not lst in descriptors:
    #with open(lists[lst], 'r') as f:
    #descriptors[lst]   = [ line for line in f if line.strip() != "" ]
    #list_position[lst] = 0
    #if list_position[lst] >= len(descriptors[lst]):
    #working_set.remove(lst)
    #continue
    #i    = list_position[lst]
    #line = descriptors[lst][i]
    #list_position[lst] = list_position[lst] + 1
    #
    #if (data / str(i)).exists():
    ## TODO: Make it possible to re-run descriptors.
    ##       Each run is stored in its own tmp folder inside data/<i>/: data/<i>/<tmp>
    #continue
    #
    #print("Refactor", bm, workload, lst, str(i), line)
    #descriptor = opportunity_cache.RefactoringDescriptor(line)
    #try:
    #ws_script.refactor(workspace, data / str(i), descriptor)
    #j = j + 1
    #if j >= args.n:
    #break
    #except ValueError as e:
    #print("ERROR", str(e))

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
        with tempfile.TemporaryDirectory(delete = True, dir = 'temp') as location:
            import_dir    = Path(location)
            deploy_dir    = Path(location) / 'deployment'
            jfr_file      = Path(location) / 'flight.jfr'
            deploy_dir.mkdir()
            prime_import_location(args, configuration, import_dir, data_location)
            bm_script.deploy_benchmark(configuration, clean, deploy_dir, import_dir)

            # Capture execution time with flight recording disabled.
            exectime = bm_script.run_benchmark(configuration, deploy_dir, False, None)

            with open(metrics_save, 'w') as f:
                f.write("EXECUTION_TIME=" + str(exectime) + os.linesep)

            configuration.store(configuration_save)

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
    except Exception as e:
        log.warning("Benchmark failure")
        log.warning(configuration._values)
        with open(failure, 'w') as f:
            f.write(str(e))
        return False

def get_valid_configurations(args, x):
    configs    = []
    has_errors = False
    for (bm, workload) in get_x_workloads(args, x):
        configs.append(((x, bm, workload), []))
        config = get_x_workload_configuration(args, x, bm, workload)
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
            configs[-1][1].append(c)
    if has_errors:
        raise ValueError("Bad configuration")
    return configs

def get_benchmark_execution_plan(args):
    # Note, sets of refactoring opportunities and configurations for a benchmark
    # may overlap between experiments and workloads. Therefore, we check so that
    # we only include each benchmark configuration once per refactoring.
    keys = set()
    plan = []
    for x in get_arg_experiments(args):
        for (x, bm, workload), configurations in get_valid_configurations(args, x):
            location = x_location(args) / 'data' / bm
            for dir1, opportunities, files1 in os.walk(location):
                for opportunity in opportunities:
                    for dir2, refactorings, files2 in os.walk(Path(dir1) / opportunity):
                        for refactoring in refactorings:
                            for dir3, executions, files3 in os.walk(Path(dir2) / refactoring):
                                for execution in executions:
                                    if (Path(dir3) / execution / 'FAILURE').exists():
                                        continue # The refactoring could not be applied.
                                    for configuration in configurations:
                                        stats_c = Path(dir3) / execution / 'stats' / configuration.id()
                                        key     = (bm, refactoring, execution, configuration.id())
                                        if not stats_c.exists() and not key in keys:
                                            plan.append((bm, refactoring, execution, configuration))
                                            keys.add(key)
                                break
                        break
                break
    return plan

# Usage:
#   ./evaluation.py [--data <data=experiments>] --xs <xs> --bs <bs> --n <n>
#
def benchmark(args):
    i = 0
    n = args.n

    if n <= 0:
        raise ValueError("Please specify the number of benchmark executions to run using a positive integer.")

    for (bm, refactoring, execution, configuration) in get_benchmark_execution_plan(args):
        print("Benchmark", bm, refactoring, execution, configuration)
        data_location = Path(os.getcwd()) / x_location(args) / 'data' / bm / refactoring / execution
        build_and_benchmark(args, configuration, data_location)
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
    for x in get_arg_experiments(args):
        for (_x, bm, workload), configurations in get_valid_configurations(args, x):
            print(_x, bm, workload, configuration._values)

def print_execution_plan(args):
    for (bm, refactoring, execution, configuration) in get_benchmark_execution_plan(args):
        print(x, bm, workload, refactoring, execution, configuration._values)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x', required = False,
        help = "A specific experiment name")
    parser.add_argument('--xs', required = False,
        help = "Limit operation to specified experiments")
    parser.add_argument('--ls', required = False,
        help = "Limit operation to specified lists")
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
    parser.add_argument('--n', required = False, type = int, default = 1,
        help = "The number of refactorings or benchmarks to run.")
    parser.add_argument('--report', required = False, action = 'store_true',
        help = "Print statistics")
    parser.add_argument('--show-configurations', required = False, action = 'store_true',
        help = "Print all valid configurations to standard out")
    parser.add_argument('--show-execution-plan', required = False, action = 'store_true',
        help = "Print all pending benchmark executions")
    parser.add_argument('--generate-lists', required = False, action = 'store_true',
        help = "Generate lists on existing workspace")
    args = parser.parse_args()

    if args.generate_lists:
        generate_descriptor_lists(args, args.bm, args.workload)
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

