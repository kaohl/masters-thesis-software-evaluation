#!/bin/env python3

import argparse
import json
import os

from pathlib import Path

from configuration     import Configuration, Metrics, RefactoringConfiguration
from opportunity_cache import RefactoringDescriptor

#
# Speedup plots:
#
# - speedup 1 (independent of refactoring configurations):
#   - x: (refactoring type, {workload}={one,all}, {configuration}={one,all})
#
# - speedup 2 (depends on refactoring configuration):
#   - x: ((refactoring type, refactoring configuration), {workload}={one,all}, {configuration}={one,all})
#

class Experiments:
    def __init__(self, location):
        self.location = Path(location)

    def get_experiments(self):
        for dir, xs, files in os.walk(self.location):
            p = Path(dir)
            return [ p / x for x in xs if not (x == "steering" or x == "data") ]
        return []

    def get_x_workloads(self, x):
        bw = []
        for dir1, bs, files1 in os.walk(x / 'workloads'):
            for b in bs:
                for dir2, ws, files2 in os.walk(x / 'workloads' / b):
                    for w in ws:
                        bw.append((b, w))
                    break
            break
        return bw

    def get_xbw(self):
        xbw = []
        for x in self.get_experiments():
            for b, w in self.get_x_workloads(x):
                xbw.append((x.name, b, w))
        return xbw

    def lists_location(self, x, b, w):
        return self.location / x / 'workloads' / b / w / 'lists'

    def get_parameters_location(self, x, b, w):
        return self.location / x / 'workloads' / b / w / 'parameters.txt'

    def get_folders(self, path):
        for dir, folders, files in os.walk(path):
            return [ f for f in folders ]
        return []

    def for_workloads_and_configurations(self, target_b, target_w, target_configuration, target_refactoring_ids, target_refactoring_configuration = None):
        print(
            "Compute",
            target_b,
            target_w,
            "TC" if target_configuration != None else None,
            "RC" if target_refactoring_configuration != None else None
        )
        visited    = set()
        benchmarks = dict() # { (<refactoring id>, <refactoring config id>) : (refactoring_config, [<data path>]) }
        for b in self.get_folders(self.location / 'data'):
            if target_b != None and b != target_b:
                continue
            for opportunity in self.get_folders(self.location / 'data' / b):
                for instance in self.get_folders(self.location / 'data' / b / opportunity):
                    for execution in self.get_folders(self.location / 'data' / b / opportunity / instance):
                        for configuration_id in self.get_folders(self.location / 'data' / b / opportunity / instance / execution / 'stats'):
                            print("Found benchmark", self.location / 'data' / b / opportunity / instance / execution / 'stats' / configuration_id)
                            instance_location = self.location / 'data' / b / opportunity / instance
                            data_descriptor = RefactoringDescriptor.load(
                                instance_location / 'descriptor.txt'
                            )
                            data_configuration = Configuration().load(
                                instance_location / execution / 'stats' / configuration_id / 'configuration.txt'
                            )
                            data_metrics = Metrics().load(
                                instance_location / execution / 'stats' / configuration_id / 'metrics.txt'
                            )
                            if not (data_configuration.bm() == target_b and data_configuration.bm_workload() == target_w):
                                continue
                            if target_configuration != None:
                                is_match = True
                                for param in target_configuration._values.keys():
                                    if data_configuration._values[param] != target_configuration._values[param]:
                                        is_match = False
                                        break
                                if not is_match:
                                    continue
                            if target_refactoring_configuration != None:
                                is_match = True
                                for param in target_refactoring_configuration._values.keys():
                                    if data_descriptor._params[param] != target_refactoring_configuration._values[param]:
                                        is_match = False
                                        break
                                if not is_match:
                                    continue

                            key = (data_descriptor.refactoring_id(), target_refactoring_configuration.id() if target_refactoring_configuration else None)
                            if not key in benchmarks:
                                benchmarks[key] = (target_refactoring_configuration, [])

                            benchmarks[key][1].append(data_metrics._values['EXECUTION_TIME'])
        if len(benchmarks) == 0:
            print("    No data for plot.")
            return

        print(benchmarks)

def _main(args):
    repo = Experiments(args.x_location)
    xbw  = repo.get_xbw()

    # ATTENTION
    # This code will break if anything in the experimental setup changes.
    # To fully generalize this code takes more effort than it is worth at the moment.

    ref_config = dict()
    exp_config = Configuration().jdk(['17.0.9-graalce', '17.0.14-tem']).jre(['17.0.9-graalce', '17.0.14-tem']).get_all_combinations()

    for x, b, w in xbw:
        # Load refactoring configuration per type from lists.
        # We assume all experiments and benchmarks have the same lists.
        lists_location = repo.lists_location(x, b, w)
        for dir, list_names, files in os.walk(lists_location):
            for list_name in list_names:
                q_filter   = Path(dir) / list_name / 'q.filter'
                q_config   = Path(dir) / list_name / 'q.config'
                id = None
                with open(q_filter, 'r') as f:
                     id = json.load(f)['id']
                ref_config[id] = RefactoringConfiguration().load(q_config).get_all_combinations()
            break
        break # We only need to load one since all are the same.

    ws        = set([ (b, w) for x, b, w in xbw ])
    ref_types = [ k for k in ref_config.keys() ]

    # Note: There is only one benchmark per experiment folder.
    # Note: The experiment folder is named after the benchmark.

    # All workloads; all configurations.
    print('-' * 20)
    repo.for_workloads_and_configurations(None, None, None, ref_types, None)

    # For each workload; all configurations.
    print('-' * 20)
    for b, w in ws:
        repo.for_workloads_and_configurations(b, w, None, ref_types, None)

    # All workloads; foreach configuration.
    print('-' * 20)
    for xc in exp_config:
        repo.for_workloads_and_configurations(None, None, xc, ref_types, None)

    # Foreach workload; foreach configuration.
    print('-' * 20)
    for b, w in ws:
        for xc in exp_config:
            repo.for_workloads_and_configurations(b, w, xc, ref_types, None)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x-location', default = 'experiments', required = False,
        help = "Path to  location.")
    args = parser.parse_args()
    _main(args)

