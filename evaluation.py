import argparse
import os
from pathlib import Path
from random import randrange
import shutil

import workspace     as ws_script
import run_benchmark as bm_script

# File system layout
#
# configs/
#   <bm refactoring config name>/   # Example: '<bm>-default' or <bm>-<md5(config)>
#     packages.config
#     packages.config.helper
#     units.config
#     units.config.helper
#     variable.config
#     methods.config        (TODO: Generate)
#     methods.config.helper (TODO: Generate)
#
# experiments/<ex>/
#   workspace/     # Eclipse workspace.
#     ...
#   data/          # Refactoring output.
#     <tag>/       # Data set label (e.g., "batch-1" or 'rename-1' or 'inline-method-4').
#       <tmp 1>/                       # A specific refactoring.
#         stats/                       # Benchmark execution results.
#           <configuration 0>/         # A specific configuration.
#             configuration.txt        # Experiment parameter values (configuration vector).
#             <tmp ...>/               # A specific execution of "configuration 0".
#               <measurements>         # Benchmark execution measurements.
#

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
