#!/bin/env python3

import argparse
import json
import matplotlib.pyplot as plt
import numpy             as np
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

class ColumnConstraints:
    def __init__(self, b, w, c, t, tc):
        self.b  = b
        self.w  = w
        self.c  = c
        self.t  = t
        self.tc = tc

class Column:
    def __init__(self, t, tc, data, count, constraints):
        self.ref_type    = t
        self.ref_conf    = tc
        self.data        = data
        self.count       = count
        self.constraints = constraints

    def get_xlabel(self):
        target_configuration             = self.constraints.c
        target_refactoring_configuration = self.constraints.tc
        targeted_workloads               = set(self.count.keys())

        xlabel = []
        xlabel.append(f"W:{';'.join([ '-'.join([b, w]) + '(' + str(self.count[(b, w)]) + ')'for b, w in sorted(targeted_workloads) ])}")
        xlabel.append(f"P:{target_configuration.key_value_string() if target_configuration != None else 'All'}")
        xlabel.append(f"R:{target_refactoring_configuration.key_value_string() if target_refactoring_configuration != None else 'All'}")
        return ','.join(xlabel)

class Plot:
    def __init__(self, title, columns):
        self.title   = title
        self.columns = columns

    def show(self):
        if len(self.columns) == 0:
            return

        fig, ax = plt.subplots(nrows = 1, ncols = 1, figsize = (9, 4), sharey = True)
        ax.set_title(self.title)
        ax.set_ylabel("Speedup (baseline/measure)")
        ax.violinplot([ column.data for column in sorted(self.columns, key = lambda it: it.ref_type) ])

        labels = [ column.ref_type[len('org.eclipse.jdt.ui.'):] for column in sorted(self.columns, key = lambda it: it.ref_type) ]
        ax.set_xticks(np.arange(1, len(labels) + 1), labels=labels)
        ax.set_xlim(0.25, len(labels) + 0.75)
        ax.set_xlabel(','.join([ column.get_xlabel() for column in sorted(self.columns, key = lambda it: it.ref_type) ]))

        plt.show()

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

    def get_baseline(self):
        with open('baseline.txt', 'r') as f:
            return json.load(f)

    def for_workloads_and_configurations(self, constraints):
        target_b                         = constraints.b
        target_w                         = constraints.w
        target_configuration             = constraints.c
        target_refactoring_ids           = constraints.t
        target_refactoring_configuration = constraints.tc

        baseline            = self.get_baseline()
        benchmarks          = dict() # { (<refactoring id>, <refactoring config id>) : (refactoring_config, [<data path>]) }
        #targeted_workloads  = set() # Note: This is now 'count.keys()'
        #count               = dict() # { (b, w) : nbr_included_benchmarks }
        for b in self.get_folders(self.location / 'data'):
            if target_b != None and b != target_b:
                continue
            data_b = self.location / 'data' / b
            for opportunity in self.get_folders(data_b):
                for instance in self.get_folders(data_b / opportunity):
                    for execution in self.get_folders(data_b / opportunity / instance):
                        for configuration_id in self.get_folders(data_b / opportunity / instance / execution / 'stats'):
                            print("Found benchmark", data_b / opportunity / instance / execution / 'stats' / configuration_id)
                            instance_location = data_b / opportunity / instance
                            data_descriptor = RefactoringDescriptor.load(
                                instance_location / 'descriptor.txt'
                            )
                            data_configuration = Configuration().load(
                                instance_location / execution / 'stats' / configuration_id / 'configuration.txt'
                            )
                            data_metrics = Metrics().load(
                                instance_location / execution / 'stats' / configuration_id / 'metrics.txt'
                            )
                            if target_w != None and data_configuration.bm_workload() != target_w:
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
                                benchmarks[key] = (target_refactoring_configuration, [], dict())

                            bw_key                     = (data_configuration.bm(), data_configuration.bm_workload())
                            benchmarks[key][2][bw_key] = (benchmarks[key][2][bw_key] + 1) if bw_key in benchmarks[key][2] else 1
                            # targeted_workloads.add(bw_key) # This is now 'count.keys()'.

                            baseline_key = '-'.join([data_configuration.bm(), data_configuration.bm_workload(), data_configuration.id()])
                            benchmarks[key][1].append(int(data_metrics._values['EXECUTION_TIME']) / int(baseline[baseline_key]))

        return [ Column(t, tc, data, count, constraints) for (t, tc_id), (tc, data, count) in benchmarks.items() ]

        #print(
        #    "Compute",
        #    f"BS: {target_b if target_b else 'All'}",
        #    f"WS: {target_w if target_w else 'All'}",
        #    xlabel[0],
        #    xlabel[1],
        #    xlabel[2]
        #)
        #if len(benchmarks) == 0:
        #    print("    No data for plot.")
        #    return

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

    bs        = set([ b for x, b, w in xbw ])
    ws        = set([ (b, w) for x, b, w in xbw ])
    ref_types = [ k for k in ref_config.keys() ]

    # Note: There is only one benchmark per experiment folder.
    # Note: The experiment folder is named after the benchmark.

    # All benchmarks; All workloads; All configurations; All refactoring configurations.
    print('-' * 20)
    Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(None, None, None, ref_types, None))).show()

    # For each benchmark (all workloads); All configurations; All refactoring configurations.
    print('-' * 20)
    for b in bs:
        Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(b, None, None, ref_types, None))).show()

    # For each workload; All configurations; All refactoring configurations.
    print('-' * 20)
    for b, w in ws:
        Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(b, w, None, ref_types, None))).show()

    # All workloads; foreach configuration; All refactoring configurations.
    print('-' * 20)
    for xc in exp_config:
        Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(None, None, xc, ref_types, None))).show()

    # For each benchmark (all workloads); For each configuration; All refactoring configurations.
    print('-' * 20)
    for b in bs:
        for xc in exp_config:
            Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(b, None, xc, ref_types, None))).show()

    # For each workload; foreach configuration.
    print('-' * 20)
    for b, w in ws:
        for xc in exp_config:
            Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(b, w, xc, ref_types, None))).show()

    #for type in ref_types:
    #    
    #    # For each refactoring type; All refactoring configurations
    #    # 1. Across all benchmarks and workloads
    #    #    - for each and all configurations
    #    # 2. Across all workloads for the same benchmark
    #    #    - for each and all configurations
    #    #
    #    # For each refactoring type; For each refactoring configuration.
    #    # 1. All benchmarks; All workloads
    #    #    - All / One configurations
    #    # 2. One benchmark ; All workloads
    #    #    - All / One configurations
    #    
    #    # TODO: Här vill man ju ha en kolumn per refactoring configuration istället för refactoring type
    #    # eftersom man jobbar med (refactoring type, refactoring configuration)-par. Alltså, [type] är
    #    # konstant.
    #    
    #    for b in bs:
    #        # One benchmark; All workloads; All configurations; One type; One refactoring configuration.
    #        repo.for_workloads_and_configurations(b, None, None, [type], ref_config[type])
    #        for xc in exp_config:
    #            # One benchmark; All workloads; One configuration; One type; One refactoring configuration.
    #            repo.for_workloads_and_configuration(b, None, xc, [type], ref_config[type])
    #    
    #    for b, w in ws:
    #        # One benchmark; One workload; All configurations; One type; One refactoring configuration.
    #        repo.for_workloads_and_configurations(b, w, None, [type], ref_config[type])
    #        for xc in exp_config:
    #            # One benchmark; One workload; One configuration; One type; One refactoring configuration.
    #            repo.for_workloads_and_configuration(b, w, xc, [type], ref_config[type])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x-location', default = 'experiments', required = False,
        help = "Path to  location.")
    args = parser.parse_args()
    _main(args)

