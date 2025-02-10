import argparse
import os
from pathlib import Path
from random import randrange
import shutil

import workspace     as ws_script
import run_benchmark as bm_script

# File system layout
#
# Each benchmark workload is a standalone experiment.
# Because, each workload may have different hot methods
# and configuration limits (heap size; stack size; etc.).
# An experiment is therefore a set of properties and parameters
# for a given benchmark and workload.
# We record the full set of configuration and parameters per data point
# (excluding refactoring configurationso that we can 
# 
# NOTE: We don't save the information to regenerate the exact sequence of
#       refactorings. We do store the transformation as patches and measurements
#       should be reproducible given a patch.
#
#       properties.txt
#         # TODO: Is properties needed when we have BM and WORKLOAD names in path?
#         # Also, we don't record refactoring arguments (seeds, length, etc.) because
#         # experiments are reproducible from patches.
#         # The reason for this is that refactorings can be generated in batches with
#         # random seeds to avoid hitting the same refactorings over and over again,
#         # and tracking the history for each run of the refactoring generator is
#         # overkill when all we need to save is the patch.
#
# NOTE: Exported resources are stored inside each prepared workspace and can be reused.
#
# experiments/<x>/
#   benchmark-log.txt
#     - Write "DONE <config hash>" when benchmark is complete for specified configuration.
#     - Save to track finished benchmark configurations
#       - Makes parameter value lists extensible
#       - Makes it possible to terminate the experiment program and resume on restart
#       - Makes it possible to extract stats from the data tree without triggering recomputation of benchmarks
#   workload
#     jacop/default/
#       parameters.txt
#         - Text file listing experiment parameters and values
#         - Experiment loops over all configurations; extensible value lists.
#     batik/small/
#       parameters.txt
#     ...
#   steering/
#     jacop.default
#     batik.small
#     batik.default
#     ...
#   config/<bm>/<workload>/
#     packages.config  # Only required for random refactorings; not with hot method steering.
#     units.config     # Only required for random refactorings; not with hot method steering.
#     variable.config  # I believe this one is generated on export?
#   workspace/<bm>/<workload>     # Eclipse workspace.
#     ...
#   data/                            # Refactoring output.
#     <tmp 1>/                       # A specific refactoring.
#       stats/                       # Benchmark execution results.
#         <configuration 0>/         # A specific configuration.
#           configuration.txt        # Experiment parameter values (configuration vector).
#           <tmp ...>/               # A specific execution of "configuration 0".
#             <measurements>         # Benchmark execution measurements.
#


# 1. Scan experiment folder for benchmark workloads <experiments>/<x>/workload/<bm>/<workload>/parameters.txt
# 2. For each workload, generate (or copy cached files) steering and create <experiments>/<x>/steering/<bm>.<workload>
# 3. For each workload, generate a workspace with oppcache based on workload steering
# 4. Generate refactorings                        (separate invokation)
# 5. Benchmark refactorings in all configurations (separate invokation)
#
# When we refactor we should be able to run with the experiment tree on the USB.
# However, we we deploy benchmarks we should probably move benchmark data onto
# the machine disk to not communicate with the USB during benchmarks.
#
# (install-from-usb.py) Deploying the evaluation on benchmark machines
# 1. Pull <evaluation> and <daivy> repos onto the benchmark machines into assigned locations
#    - We could store gitrepos on USB and pull from there which simplify updating the framework
#      on the benchmark machine (simply update the USB and the do a new pull on the machine via USB)
# 2. Move a pre-populated ivy-cache from the USB into <daivy>
# 3. Move a pre-defined experiment folder into <evaluation> (contains configurations and potentially some refactorings)
# 4. Set DAIVY_HOME and start the 'evaluation.py' script
#
# It would be good if the 'install-from-usb.py' script works incrementally
# so that it is easy to update the installation with experiments and additions
# to ivy-cache and to daivy. This is easily done by simply removing the current
# deployed folders and then moving updated folders from the USB which can then
# be deleted from the USB if needed to make room for data. The git repos will
# be incremental by default. Of course, we could make the ivy-cache a local repo
# on the USB to also handle incremental updates of the ivy-cache.




# Usage:
#  ./evaluation.py --bm <bm> --x <ex> --config configs/<bm refactoring config name>
#
def create(bm, ex, cf):

    # 1. Create experiments/<ex>/{workspace,data}
    # 2. Copy config into workspace/assets/src
    # 3. Export benchmark into experiments/<ex>/workspace
    # 4. Prepare workspace
    
    #bm = args.bm
    #ex = Path(args.data_root or 'experiments') / args.x
    #cf = args.config and Path(args.config)

    if cf is None or not cf.is_dir():
        raise ValueError("Please specify an existing workspace configuration folder.")

    dt  = ex / 'data'
    ws  = ex / 'workspace'
    src = ws / 'assets' / 'src'

    if ws.exists():
        print("Workspace already exists")
        return

    src.mkdir(parents = True)
    dt.mkdir()

    for root, folders, files in os.walk(cf):
        print(root, folders, files)
        for file in files:
            shutil.copy2(Path(root) / file, src / file)

    ws_script.create_workspace_in_location("dacapo:{}:1.0".format(bm), ws)

# Usage:
#  ./evaluation.py --bm <bm> --x <ex> --tag <tag> --refactor --type <refactoring type> [ refactoring options ]
#
def refactor(ex, tag, options, proc_id):
    # 1. Call refactor on workspace
    # 2. Copy result into data folder
    #bm = args.bm
    #ex = Path(args.data_root or 'experiments') / args.x

    ws = ex / 'workspace'
    dt = ex / 'data' / tag

    ws_script.refactor(ws, dt, options, proc_id)

def _benchmark_data(data_location, configuration):
    print("Benchmark", str(data_location))
    bm_script.build_and_benchmark(data_location, configuration)

def _benchmark_all(data_location, configuration):
    for root, folders, files in os.walk(data_location):
        for folder in folders:
            _benchmark_data(Path(root) / folder, configuration)
        break

# Usage:
#   ./evaluation.py --bm <bm> --x <ex> --tag <tag> --benchmark [--data <tmp...>]
#
def benchmark(ex, tag, configuration, data = None):
    data_location = ex / 'data' / tag

    if data is None:
        _benchmark_all(data_location, configuration)
    else:
        _benchmark_data(data_location / data, configuration)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x', required = True,
        help = "The experiment name.")
    parser.add_argument('--x-location', required = False,
        help = "Location where experiments are stored. Defaults to 'experiments'.")
    parser.add_argument('--bm', required = True,
        help = "Benchmark name")
    parser.add_argument('--tag', required = True,
        help = "Data tag for use when storing refactorings")
    parser.add_argument('--create', required = False,
        help = "Create experiment workspace from specified template")
    parser.add_argument('--benchmark', required = False, action = 'store_true',
        help = "Benchmark refactoring(s)")
    parser.add_argument('--data', required = False,
        help = "A specific refactoring folder name") 
    parser.add_argument('--refactor', required = False,
        help = "Refactor specified experiment workspace")
    parser.add_argument('--type', required = False,
        help = "Refactoring type")
    args = parser.parse_args()

    if args.create:
        _create(args)
    elif args.benchmark:
        _benchmark(args)
    elif args.refactor:
        _refactor(args)
    else:
        parser.print_help()

# Use JDK to compile source code to target version (above or equal to source version)
# and run in JRE (above or equal to target version).
#
# - Applicable JDKs (only greater or equal to source version)
#   - Applicable target versions (only less or equal to JDK version
#     and greater than or equal to source version)
# - Applicable JREs (only greater or equal to target version)
#
# CV := Compiler Version
# RV := Runtime Version
# SV := Source Version
# TV := Target Version
#
# SV := Minimum source version required by project (multi-release possible)
# Applicable CVs (CV >= SV)
# Applicable TVs (TV >= SV and TV <= CV)
# Applicable RVs (RV >= TV)
#
# Multi-release only affects the output artifact if we can't
# compile all source trees because of missing compiler for a
# specific version. However, we could call this build failure
# if we want to be sure that the same artifact is used in all
# benchmarks. Or we could define multiple versions of each
# multi-release project where we only include source trees
# up the the target version.
#
