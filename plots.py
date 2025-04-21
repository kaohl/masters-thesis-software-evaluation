#!/bin/env python3

import argparse
import json
import matplotlib.pyplot as plt
import numpy             as np
import os

from pathlib import Path

from configuration     import Configuration, Metrics, RefactoringConfiguration
from opportunity_cache import RefactoringDescriptor

# Violin plots for speedup graphs.
#
# I have adapted example code from the following resources to plot graphs:
#   https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.violinplot.html
#   https://matplotlib.org/stable/gallery/statistics/customized_violin.html#sphx-glr-gallery-statistics-customized-violin-py
#
# Compare with 'Plot.show()' below.

#
# Speedup plots:
#
# - speedup 1 (independent of refactoring configurations):
#   - x: ((refactoring type, refactoring configuration={all}), {workload}={one,all}, {configuration}={one,all})
#
# - speedup 2 (depends on refactoring configuration):
#   - x: ((refactoring type, refactoring configuration={one}), {workload}={one,all}, {configuration}={one,all})
#

class ColumnConstraints:
    def __init__(self, b, w, c, t, tc):
        self.b  = b
        self.w  = w
        self.c  = c
        self.t  = t
        self.tc = tc

    def title_from_constraints(self):
        return ';'.join([
            ('All' if self.b  == None else 'One') + ' B',
            ('All' if self.w  == None else 'One') + ' W',
            ('All' if self.c  == None else 'One') + ' C',
            ('All' if self.t  == None else 'One') + ' T',
            ('All' if self.tc == None else 'One') + ' R',
        ])

class Column:
    def __init__(self, t, tc, data, count, constraints):
        self.ref_type      = t
        self.ref_conf      = tc
        self.data          = data
        self.count         = count
        self.constraints   = constraints

        ylim_below = 0.5
        ylim_above = 1.5

        self.data_outliers_below = [ x for x in data if x <= ylim_below ]
        self.data_outliers_above = [ x for x in data if x >= ylim_above ]
        self.data_filtered       = [ x for x in data if x > ylim_below and x < ylim_above ]

    # The 'tag' could be 'a' or '1a' etc.
    def get_xlabel(self, tag):
        target_configuration             = self.constraints.c
        target_refactoring_configuration = self.constraints.tc
        targeted_workloads               = set(self.count.keys())

        benchmarks         = ','.join(sorted(set([ b for b, w in sorted(targeted_workloads) ])))
        configurations     = target_configuration.key_value_string() if target_configuration != None else 'All'
        ref_configurations = target_refactoring_configuration.key_value_string() if target_refactoring_configuration != None else 'All'
        outliers           = [ x for x in self.data if x <= 0.5 or x >= 1.5 ]
        outliers_message   = f" Removed {len(outliers)} outliers." if len(outliers) > 0 else ""
        xlabel = [
            f"{tag}) Shows {len(self.data)} measurements across {len(self.count)} workload(s) for benchmark(s): {benchmarks}, using parameters: {configurations}, and refactoring parameters: {ref_configurations}.{outliers_message}"
        ]
        #xlabel.append(f"W:{';'.join([ '-'.join([b, w]) + '(' + str(self.count[(b, w)]) + ')'for b, w in sorted(targeted_workloads) ])}")
        #xlabel.append(f"{len(self.data)} measurements across workloads: {workloads}")
        #xlabel.append(f"P:{configurations}")
        #xlabel.append(f"R:{ref_configurations}")
        return ','.join(xlabel)

class Plot:

    _labels = {
        'org.eclipse.jdt.ui.inline.constant'         : 'IC',
        'org.eclipse.jdt.ui.inline.method'           : 'IM',
        'org.eclipse.jdt.ui.inline.temp'             : 'IT',
        'org.eclipse.jdt.ui.extract.constant'        : 'EC',
        'org.eclipse.jdt.ui.extract.method'          : 'EM',
        'org.eclipse.jdt.ui.extract.temp'            : 'ET',
        'org.eclipse.jdt.ui.introduce.indirection'   : 'II',
        'org.eclipse.jdt.ui.rename.field'            : 'RF',
        'org.eclipse.jdt.ui.rename.local.variable'   : 'RV',
        'org.eclipse.jdt.ui.rename.method'           : 'RM',
        'org.eclipse.jdt.ui.rename.type'             : 'RT',
        'org.eclipse.jdt.ui.rename.type.parameter'   : 'TP'
    }

    def __init__(self, title, columns):
        self.title   = title
        self.columns = columns

    def show(self):
        if len(self.columns) == 0:
            return
        Plot.show_plots([self])

    def _plot(plot, ax, caption):
        vp = ax.violinplot(
            [ column.data_filtered for column in sorted(plot.columns, key = lambda it: it.ref_type) ],
            showmeans   = True,
            showmedians = True
        )

        medians = vp['cmedians'].get_paths()[0].vertices
        plt.plot((medians[0][0] + medians[1][0]) / 2.0, medians[0,1], 'rx', label = 'Median')

        means   = vp['cmeans'].get_paths()[0].vertices
        plt.plot((means[0][0] + means[1][0]) / 2.0, means[0,1], 'r+', label = 'Mean')

        ax.legend()

        labels = [ Plot._labels[column.ref_type] for column in sorted(plot.columns, key = lambda it: it.ref_type) ]
        ax.set_xticks(np.arange(1, len(labels) + 1), labels=labels)
        ax.set_xlim(0.25, len(labels) + 0.75)
        ax.set_ylim(0.5, 1.5)
        #ax.set_xlabel(','.join([ column.get_xlabel() for column in sorted(self.columns, key = lambda it: it.ref_type) ]))
        caption.append(','.join([ column.get_xlabel(f"{i}{Plot._labels[column.ref_type]}") for i, column in enumerate(sorted(plot.columns, key = lambda it: it.ref_type)) ]))

        xoffset = 1
        for column in plot.columns:
            plt.annotate(f"{len(column.data_filtered)}", (xoffset, 0.55))
            xoffset = xoffset + 1

    def show_plots(plots, nrows = 1, ncols = 1):
        plots = [ plot for plot in plots if len(plot.columns) > 0 ]

        if len(plots) == 0:
            return

        caption = []
        if len(plots) > 1:
            fig, xs = plt.subplots(nrows = nrows, ncols = ncols, figsize = (9, 4), sharey = True, sharex = True)
            for i, ax in enumerate(xs.flat):
                plot = plots[i] if len(plots) > i else None
                if plot is None:
                    continue
                Plot._plot(plot, ax, caption)                
        else:
            fig, ax = plt.subplots(nrows = 1, ncols = 1, figsize = (9, 4), sharey = True, sharex = True)
            plot    = plots[0]
            ax.set_ylabel("Speedup (baseline/measure)")
            Plot._plot(plot, ax, caption)

        plt.axhline(y = 1.0, color = 'C1', linestyle = '--')

        #plt.show()

        p = Path('figures')
        saved = False
        for i in range(10000):
            x = p / (str(i) + '.png')
            if not x.exists():
                plt.savefig(x)
                saved = True
                with open(p / (str(i) + '.tex'), 'w') as f:
                    f.write("""
\\begin{figure}[h]
    \\centering
    \\includegraphics[width=0.25\\textwidth]{mesh}
    \\caption{@CAPTION}
    \\label{fig:@NAME}
\\end{figure}
                    """.replace("@NAME", str(i)).replace("@CAPTION", '\\newline'.join(caption)))
                    # .replace("@CAPTION", '\newline'.join([ str(i) + ") " + cap for cap in caption])))
                
                break
        plt.close()
        if not saved:
            raise ValueError("Too many figures!")

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
        target_refactoring_id            = constraints.t
        target_refactoring_configuration = constraints.tc

        print("Compute", target_b, target_w, target_configuration, target_refactoring_id, target_refactoring_configuration)

        baseline   = self.get_baseline()
        benchmarks = dict() # { (<refactoring id>, <refactoring config id>) : (refactoring_config, [<data path>], count) }
        for b in self.get_folders(self.location / 'data'):
            if target_b != None and b != target_b:
                continue
            data_b = self.location / 'data' / b
            for opportunity in self.get_folders(data_b):
                for instance in self.get_folders(data_b / opportunity):
                    for execution in self.get_folders(data_b / opportunity / instance):
                        for configuration_id in self.get_folders(data_b / opportunity / instance / execution / 'stats'):
                            #print("Found benchmark", data_b / opportunity / instance / execution / 'stats' / configuration_id)
                            instance_location = data_b / opportunity / instance

                            if (instance_location / execution / 'stats' / configuration_id / 'FAILURE').exists():
                                continue
                            
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
                            if target_refactoring_id != None and data_descriptor.refactoring_id() != target_refactoring_id:
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

                            baseline_key = '-'.join([data_configuration.bm(), data_configuration.bm_workload(), data_configuration.id()])
                            benchmarks[key][1].append(int(data_metrics._values['EXECUTION_TIME']) / int(baseline[baseline_key]))
        return [ Column(t, tc, data, count, constraints) for (t, tc_id), (tc, data, count) in benchmarks.items() ]

    def create_data_file(self, the_file):
        for b in self.get_folders(self.location / 'data'):
            data_b = self.location / 'data' / b
            for opportunity in self.get_folders(data_b):
                for instance in self.get_folders(data_b / opportunity):
                    for execution in self.get_folders(data_b / opportunity / instance):
                        for configuration_id in self.get_folders(data_b / opportunity / instance / execution / 'stats'):
                            instance_location = data_b / opportunity / instance

                            if (instance_location / execution / 'stats' / configuration_id / 'FAILURE').exists():
                                continue

                            data_descriptor = RefactoringDescriptor.load(
                                instance_location / 'descriptor.txt'
                            )
                            data_configuration = Configuration().load(
                                instance_location / execution / 'stats' / configuration_id / 'configuration.txt'
                            )
                            data_metrics = Metrics().load(
                                instance_location / execution / 'stats' / configuration_id / 'metrics.txt'
                            )

                            t = data_descriptor.refactoring_id()
                            b = data_configuration.bm()
                            w = data_configuration.bm_workload()
                            x = data_configuration
                            r = data_descriptor._params

                            the_file.write(json.dumps({
                                'T' : { 'type' : t },
                                'B' : { 'name' : b },
                                'W' : { 'name' : w },
                                'X' : x._values,
                                'R' : r,
                                'M' : data_metrics._values
                            }) + os.linesep)

    def filter_data_file(self, path, filter):
        baseline = self.get_baseline()
        entries  = []
        with open(path, 'r') as f:
            for line in f:
                entry = json.loads(line)

                is_match = True
                for name, params in filter.items():
                    values = entry[name]
                    for p, v in params.items():
                        if not v == values[p]:
                            is_match = False
                            break
                if is_match:
                    tms          = entry['M']['EXECUTION_TIME']
                    x            = Configuration().init_from_dict(entry['X'])
                    baseline_key = '-'.join([x.bm(), x.bm_workload(), x.id()])
                    speedup      = int(tms) / int(baseline[baseline_key])
                    entries.append((entry, speedup))
        return entries

def _main(args):
    repo = Experiments(args.x_location)
    xbw  = repo.get_xbw()

    # Write all data to specified file.
    with open('all-data-file.txt', 'w') as f:
        repo.create_data_file(f)

    print(repo.filter_data_file('all-data-file.txt', { 'B' : { 'name' : 'xalan' } }))

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

    bs        = set([ b for x, b, w in xbw if len(args.bs) == 0 or b in args.bs ])
    ws        = set([ (b, w) for x, b, w in xbw if len(args.bs) == 0 or b in args.bs ])
    ref_types = [ k for k in ref_config.keys() ]

    # Note: There is only one benchmark per experiment folder.
    # Note: The experiment folder is named after the benchmark.

    # All benchmarks; All workloads; All configurations; All refactoring configurations.
    print('-' * 20)
    Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(None, None, None, None, None))).show()

    # For each benchmark (all workloads); All configurations; All refactoring configurations.
    print('-' * 20)
    for b in bs:
        Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(b, None, None, None, None))).show()

    # For each workload; All configurations; All refactoring configurations.
    print('-' * 20)
    for b, w in ws:
        Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(b, w, None, None, None))).show()

    # All workloads; foreach configuration; All refactoring configurations.
    print('-' * 20)
    plots = []
    for xc in exp_config:
        plots.append(Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(None, None, xc, None, None))))
    Plot.show_plots(plots, 2, 2)

    # For each benchmark (all workloads); For each configuration; All refactoring configurations.
    print('-' * 20)
    plots = []
    for b in bs:
        for xc in exp_config:
            plots.append(Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(b, None, xc, None, None))))
    Plot.show_plots(plots, 2, 2)

    # For each workload; foreach configuration.
    print('-' * 20)
    plots = []
    for b, w in ws:
        for xc in exp_config:
            plots.append(Plot("Title", repo.for_workloads_and_configurations(ColumnConstraints(b, w, xc, None, None))))
    Plot.show_plots(plots, 2, 2)

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
    #    # Here we collect one column per refactoring type and configuration for different settings.
    #
    #    columns = []
    #    for rc in ref_config[type]:
    #        columns.extend(repo.for_workloads_and_configurations(ColumnConstraints(None, None, None, type, rc)))
    #    Plot("All B, All W, All C, One type, One Refactoring Configuration", columns).show()
    #
    #    for b in bs:
    #        # One benchmark; All workloads; All configurations; One type; One refactoring configuration.
    #        columns = []
    #        for rc in ref_config[type]:
    #            columns.extend(repo.for_workloads_and_configurations(ColumnConstraints(b, None, None, type, rc)))
    #        Plot("Title", columns).show()
    #
    #        for xc in exp_config:
    #            columns = []
    #            for rc in ref_config[type]:
    #                # One benchmark; All workloads; One configuration; One type; One refactoring configuration.
    #                columns.extend(repo.for_workloads_and_configurations(ColumnConstraints(b, None, xc, type, rc)))
    #
    #    for b, w in ws:
    #        columns = []
    #        for rc in ref_config[type]:
    #            # One benchmark; One workload; All configurations; One type; One refactoring configuration.
    #            columns.extend(repo.for_workloads_and_configurations(ColumnConstraints(b, w, None, type, rc)))
    #        Plot("Title", columns).show()
    #
    #        for xc in exp_config:
    #            columns = []
    #            for rc in ref_config[type]:
    #                # One benchmark; One workload; One configuration; One type; One refactoring configuration.
    #                columns.extend(repo.for_workloads_and_configurations(ColumnConstraints(b, w, xc, type, rc)))
    #            Plot("Title", columns).show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x-location', required = False, default = 'experiments',
        help = "Path to location.")
    parser.add_argument('--bs', required = False, nargs = '+', default = [],
        help = "Benchmarks to plot.")
    args = parser.parse_args()
    _main(args)

