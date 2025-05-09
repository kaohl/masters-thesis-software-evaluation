#!/bin/env python3

import argparse
import json
import matplotlib
import matplotlib.pyplot as plt
import numpy             as np
import os
import pandas
import statsmodels.api as sm

from statsmodels.formula.api import ols
from pathlib                 import Path

import experiment
from configuration     import Configuration, Metrics, RefactoringConfiguration, ConfigurationBase
from opportunity_cache import RefactoringDescriptor

matplotlib.use('TkAgg') # Fix for some ICE error...

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
        'org.eclipse.jdt.ui.rename.type.parameter'   : 'RP'
    }

    #_labels_names = {
    #    'org.eclipse.jdt.ui.inline.constant'         : 'Inline constant',
    #    'org.eclipse.jdt.ui.inline.method'           : 'Inline method',
    #    'org.eclipse.jdt.ui.inline.temp'             : 'Inline temp',
    #    'org.eclipse.jdt.ui.extract.constant'        : 'Extract constant',
    #    'org.eclipse.jdt.ui.extract.method'          : 'Extract method',
    #    'org.eclipse.jdt.ui.extract.temp'            : 'Extract temp',
    #    'org.eclipse.jdt.ui.introduce.indirection'   : 'Introduce indirection',
    #    'org.eclipse.jdt.ui.rename.field'            : 'Rename field',
    #    'org.eclipse.jdt.ui.rename.local.variable'   : 'Rename variable',
    #    'org.eclipse.jdt.ui.rename.method'           : 'Rename method',
    #    'org.eclipse.jdt.ui.rename.type'             : 'Rename type',
    #    'org.eclipse.jdt.ui.rename.type.parameter'   : 'Rename type parameter'
    #}

    _labels_names = {
        'IC' : 'Inline constant',
        'IM' : 'Inline method',
        'IT' : 'Inline temp',
        'EC' : 'Extract constant',
        'EM' : 'Extract method',
        'ET' : 'Extract temp',
        'II' : 'Introduce indirection',
        'RF' : 'Rename field',
        'RV' : 'Rename variable',
        'RM' : 'Rename method',
        'RT' : 'Rename type',
        'RP' : 'Rename type parameter'
    }

    def __init__(self, title, columns):
        self.title   = title
        self.columns = columns

    def show(self):
        if len(self.columns) == 0:
            return
        Plot.show_plots([self])

    def plot_violins(title, violins, is_split = True, yrange = (0.5, 1.5), caption = None, label = None, output_location = Path('figures'), filename = None):
        ymin = 1
        ymax = 1
        data = []
        active_violins = []
        for violin in violins:
            print("Constellation", violin.constellation.get_name())
            violin.split(yrange)
            if len(violin.get_data()) > 0:
                data.append(violin.get_data())
                active_violins.append(violin)
            for d in violin.get_data():
                if d > ymax:
                    ymax = d
                if d < ymin:
                    ymin = d

        if len(data) == 0:
            return

        # Define split labels, since is_split is the default. Override below if not.
        labels = [active_violins[0].constellation.get_readable_name()]
        for v in active_violins[1:]:
            diff = Constellation.split_diff(active_violins[0].constellation, v.constellation)
            labels.append(diff.get_readable_name())

        fig, ax = plt.subplots(nrows = 1, ncols = 1, figsize = (9, 6), sharey = True, sharex = True)
        ax.set_ylabel("Speedup (baseline/measure)")

        vp = ax.violinplot(
            data,
            #showmeans   = True,  # The mean does not really add anything.
            showmedians = True
        )

        if 'cmedians' in vp:
            for i, p in enumerate(vp['cmedians'].get_paths()):
                medians = p.vertices
                if i == 0:
                    plt.plot((medians[0][0] + medians[1][0]) / 2.0, medians[0,1], 'rx', label = 'Median')
                else:
                    plt.plot((medians[0][0] + medians[1][0]) / 2.0, medians[0,1], 'rx')

        if 'cmeans' in vp:
            for i, p in enumerate(vp['cmeans'].get_paths()):
                means = p.vertices
                if i == 0:
                    plt.plot((means[0][0] + means[1][0]) / 2.0, means[0,1], 'r+', label = 'Mean')
                else:
                    plt.plot((means[0][0] + means[1][0]) / 2.0, means[0,1], 'r+')

        ax.legend()
        ax.fill_between((0, len(violins) + 1), (0.95, 0.95), (1.05, 1.05), color = '#0000ff0f')

        # Override labels unless it is a split of first violin.
        if not is_split:
            labels = [ v.constellation.get_readable_name() for v in active_violins ]

        apply_slanted_labels = False
        for i, label in enumerate(labels):
            if label in Plot._labels_names.keys():
                apply_slanted_labels = True
                labels[i] = f"{label} ({Plot._labels_names[label]})"

        #labels = [ Plot._labels[column.ref_type] for column in sorted(plot.columns, key = lambda it: it.ref_type) ]
        #labels = [ str(i) for i in range(1, len(violins) + 1) ]
        ax.set_xticks(np.arange(1, len(labels) + 1), labels=labels)
        ax.set_xlim(0.25, len(labels) + 0.75)
        ax.set_ylim((ymin - 0.05, ymax + 0.05)) # *yrange
        #ax.set_xlabel(','.join([ column.get_xlabel() for column in sorted(self.columns, key = lambda it: it.ref_type) ]))

        # TODO
        # caption.append(','.join([ column.get_xlabel(f"{i}{Plot._labels[column.ref_type]}") for i, column in enumerate(sorted(plot.columns, key = lambda it: it.ref_type)) ]))

        xoffset = 1
        for violin in active_violins:
            # name = violin.constellation.get_name()
            plt.annotate(f"{len(violin.get_data())}", (xoffset, ymin - 0.05))
            plt.annotate(f"{len(violin.get_data_below())}", (xoffset, ymin))
            plt.annotate(f"{len(violin.get_data_above())}", (xoffset, ymax))
            # plt.annotate(f"{name}, {len(violin.get_data())}", (xoffset, ymin - 0.05))
            # plt.annotate(f"{violin.constellation.get_name()}", (xoffset + 0.4, ymin))
            xoffset = xoffset + 1

        if apply_slanted_labels:
            plt.xticks(rotation = 15)

        plt.axhline(y = 1.0, color = 'C1', linestyle = '--')

        if is_split:
            plt.axvline(x = 1.5, color = 'b', linestyle = ':')

        #plt.show()

        if filename == None:
            plt.close()
            return

        plt.savefig(Path(output_location) / (filename + '.png'))
        #with open(Path(output_location) / (filename + '.tex'), 'w') as f:
        #    f.write("""
        #    \\begin{figure}[h]
        #    \\centering
        #    \\includegraphics[width=1.0\\textwidth, scale=1.0]{./chapters/plots/pascal_f1200_n10/lusearch_small_by_type.png}
        #    \\caption{@CAPTION}
        #    \\label{fig:@NAME}
        #    \\end{figure}
        #    """.replace("@NAME", label).replace("@CAPTION", caption))
        plt.close()

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

    def get_baseline(self, file = 'baseline.txt'):
        with open(file, 'r') as f:
            return json.load(f)

    def print_baseline(self, args):
        hw_parameters = set()
        baselines     = []
        for f in args.baseline_files:
            baseline = self.get_baseline(f)
            if not '_meta_' in baseline:
                raise ValueError("Please define '_meta_' object with hardware parameters in baseline object", f)
            meta     = baseline['_meta_']
            hardware = meta['hardware']
            hw_parameters = hw_parameters.union({ k for k in hardware.keys() })
            baselines.append((baseline, meta, hardware))

        bms       = [ 'batik', 'jacop', 'luindex', 'lusearch', 'xalan' ]
        workloads = [ 'small', 'default', 'mzc18_1', 'mzc18_2', 'mzc18_3', 'mzc18_4' ]

        hw_map     = dict()
        hw_columns = '&'.join(['H'] + [ p.capitalize() for p in sorted(hw_parameters) ])
        hw_rows    = []
        hw_i       = 0
        for i, (baseline, meta, hardware) in enumerate(baselines):
            hw_values = [ f"{hardware[p] if p in hardware else 'N/A'}" for p in sorted(hw_parameters) ]
            if not tuple(hw_values) in hw_map:
                hw_map[tuple(hw_values)] = hw_i
                hw_rows.append([f"H{hw_i}"] + hw_values)
                hw_i                     = hw_i + 1

        with open(Path(args.baseline_out) / f"hardware-table.tex", 'w') as f:
            f.write("\\begin{table}[!h]" + os.linesep)
            f.write("\\caption{The table shows all hardware configurations used in the evaluation.}" + os.linesep)
            f.write("\\begin{tabular}{l|*{@N}{l}r}".replace("@N", str(len(hw_rows[0]))) + os.linesep)
            f.write(hw_columns + "\\\\" + os.linesep)
            f.write("\\hline" + os.linesep)
            f.write(os.linesep.join([ '&'.join(row) + "\\\\" for row in hw_rows ]) + os.linesep)
            f.write("\\end{tabular}" + os.linesep)
            f.write("\\end{table}" + os.linesep)

        for i, (baseline, meta, hardware) in enumerate(baselines):
            rows = []
            for b in bms:
                for w in (workloads[:2] if b != 'jacop' else workloads[2:]):
                    config       = Configuration().load(self.get_parameters_location(b, b, w))
                    times        = []
                    column_order = []
                    for c in config.get_all_combinations():
                        config_name  = ''.join([
                            'T' if c.jdk().find('tem') != -1 else 'G',
                            'T' if c.jre().find('tem') != -1 else 'G'
                        ])
                        column_order.append(config_name)
                        # column_order.append(config_name + ' (std)')
                        baseline_key_mean = '-'.join([c.bm(), c.bm_workload(), c.id()])
                        baseline_key_std  = '-'.join([c.bm(), c.bm_workload(), c.id(), 'std'])
                        value = str(baseline[baseline_key_mean])
                        if baseline_key_std in baseline:
                            std   = round(baseline[baseline_key_std], 2)
                            value = value + f'$\\pm {std}$'
                        times.append(value)
                        #times.append(str((round(baseline[baseline_key_std], 2) if baseline_key_std in baseline else "N/A")))

                    rows.append((b, w.replace('_', '\\_'), *times))

                    hw_key = tuple([ f"{hardware[p] if p in hardware else 'N/A'}" for p in sorted(hw_parameters) ])
                    hw_i   = hw_map[hw_key]

                    nexec   = meta['nexec']   # Number of harness iterations (warmup+measure).
                    bexec   = meta['bexec']   # Number of baseline executions.

                    caption = f"The table shows baseline execution times in milliseconds, as an average over {bexec} invocations, for all workloads in the experiment, using {int(nexec) - 1} warmup runs before measurement, and hardware configuration H{hw_i}."

                    with open(Path(args.baseline_out) / f"baseline-h{hw_i}-n{nexec}-b{bexec}.tex", 'w') as f:
                        f.write("\\begin{table}[!h]" + os.linesep)
                        f.write("\\caption{@1}".replace("@1", caption) + os.linesep)
                        f.write("\\begin{tabular}{ll|*{@N}{r}r}".replace("@N", str(len(rows[0]) - 2)) + os.linesep)
                        f.write('&'.join([ "B", "W", *column_order ]) + "\\\\" + os.linesep)
                        f.write("\\hline" + os.linesep)
                        f.write(os.linesep.join([ '&'.join(list(row)) + "\\\\" for row in rows ]) + os.linesep)
                        f.write("\\end{tabular}" + os.linesep)
                        f.write("\\end{table}" + os.linesep)

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

                            t = Plot._labels[data_descriptor.refactoring_id()]
                            b = data_configuration.bm()
                            w = data_configuration.bm_workload()
                            x = data_configuration
                            r = data_descriptor._params

                            the_file.write(json.dumps({
                                'T' : { 'type' : t },
                                'B' : { 'name' : b },
                                'W' : { 'name' : w },
                                'X' : x._values,
                                t   : r,
                                'M' : data_metrics._values
                            }) + os.linesep)

    def filter_data_file(self, path, filter):
        print("FILTER", filter)
        baseline    = self.get_baseline()
        entries     = []
        coordinates = []
        with open(path, 'r') as f:
            for i, line in enumerate(f):
                entry = json.loads(line)

                is_match = True
                for name, params in filter.items():
                    values = entry[name]
                    for p, value_set in params.items():
                        if not values[p] in value_set:
                            is_match = False
                            break
                    if not is_match:
                        break
                if is_match:
                    tms          = entry['M']['EXECUTION_TIME']
                    x            = Configuration().init_from_dict(entry['X'])
                    baseline_key = '-'.join([x.bm(), x.bm_workload(), x.id()])
                    speedup      =  int(baseline[baseline_key]) / int(tms) # Speedup is defined as > 1 if speedup, < 1 if no slowdown
                    #print(f"MATCH ({i})", entry['T']['type'], x.bm(), x.bm_workload())
                    entries.append((entry, speedup))
                    coordinates.append((len(coordinates), i))
        return entries, coordinates

class ParameterSet:
    def __init__(self, name, configuration):
        self.name           = name
        self.configuration  = configuration
        self.configurations = configuration.get_all_combinations()
        # Note that adding parameters will invalidate all configuration
        # indices since the parameter vector changes for all rows in
        # the table.
        #
        # It is safest to invalidate all and revalidate all existing
        # references even if we just extend existing lines with new
        # parameters.
        #
        # Try to decide all parameters from start to avoid revalidation.

class ConstellationGuide:
    def __init__(self, parameter_sets):
        self.sets         = parameter_sets
        self.sets_by_name = dict([ (s.name, s) for s in parameter_sets ])

    def get_parameter_configurations(self, set_name):
        if set_name in self.sets_by_name:
            return [ x for x in self.sets_by_name[set_name].configurations ]
        return []

    def get_parameters(self, set_name):
        return { k for k in self.sets_by_name[set_name].configuration._options.keys() }

    def get_parameter_options_filter(self, set_name):
        if not set_name in self.sets_by_name:
            return dict()
        return dict([ (k, set(v)) for k, v in self.sets_by_name[set_name].configuration._options.items() ])

    #{
    #  'T'   : { 'type' : {'...'} },
    #  'B'   : { 'name' : {'batik'} },
    #  'W'   : { 'name' : {'small'} },
    #  'X'   : { 'jre' : {'...'}, 'jdk' : {'...'} },
    #  '<R>' : { 'visibility' : {'1'} }
    #}
    def _get_matches(self, constraints):
        matches = dict()
        for name, value_dict in constraints.items():
            if len(value_dict) == 0:
                continue # All matched by default. (Star'ed).
            matches[name] = []
            for i, c in enumerate(self.sets_by_name[name].configurations):
                is_match = True
                for param, values in value_dict.items():
                    if not c._clobber(param) in values:
                        is_match = False
                        break
                if is_match:
                    if len(matches[name]) > 0:
                        if matches[name][-1][0] + 1 == i:
                            matches[name][-1] = (i-1, i)
                        elif len(matches[name][-1]) == 2 and matches[name][-1][1] + 1 == i:
                            matches[name][-1] = (matches[name][-1][0], i)
                        else:
                            matches[name].append((i,))
                    else:
                        matches[name].append((i,))
        return matches

    def get_expression(self, constraints):
        matches = self._get_matches(constraints)
        return '/'.join([ s.name + ','.join([ (f"{x[0]}" if len(x) == 1 else f"{x[0]}-{x[1]}") for x in matches[s.name]]) for s in self.sets if s.name in matches ])

    def get_readable_name(self, constraints):
        matches = self._get_matches(constraints)
        name    = []
        for s in self.sets:
            if not s.name in matches:
                continue
            n = len(matches[s.name])
            if n == 1 and len(matches[s.name][0]) == 1 and s.configurations[matches[s.name][0][0]].name() != None:#  len(s.configurations[matches[s.name][0][0]]._values) == 1:
                # value = list(s.configurations[matches[s.name][0][0]]._values.values())[0]
                # name.append(value)
                name.append(s.configurations[matches[s.name][0][0]].name())
            else:
                name.append(s.name + ','.join([ (f"{x[0]}" if len(x) == 1 else f"{x[0]}-{x[1]}") for x in matches[s.name]]))
        return '/'.join(name)

class CustomConfig(ConfigurationBase):
    def __init__(self, name_lookup_fn = None):
        super().__init__(CustomConfig)
        self._name_lookup_fn = name_lookup_fn

    def get_all_combinations(self):
        parameters = [ (key, options) for key, options in sorted(self._options.items(), key = lambda it: it[0]) ]
        return [ self._configuration_type(self._name_lookup_fn).init_from_dict(dict(value_list)) for value_list in self._all_rec(parameters) ]

    def is_valid_key(self, key):
        return True

    def name(self):
        if self._name_lookup_fn != None:
            return self._name_lookup_fn(self)
        return None

def visibility_name_lookup(config):
    v = config._values['visibility']
    if v == '0':
        return 'package' # 'PK'
    if v == '1':
        return 'public'  # 'PL'
    if v == '2':
        return 'private' # 'PV'
    if v == '4':
        return 'protected' # 'PT'
    return None

def property_value_lookup(config, prop):
    return config._values.get(prop)

def name_value_lookup(config):
    return property_value_lookup(config, 'name')

def type_value_lookup(config):
    return property_value_lookup(config, 'type')

def name_name_lookup(config):
    n = config._values.get('name')
    return f"L{len(n)}" if n != None else None

def final_name_lookup(config):
    f = config._values['final']
    return "Final" if f == 'true' else "!Final"

def em_name_lookup(config):
    return visibility_name_lookup(config)

def et_name_lookup(config):
    return final_name_lookup(config)

def ec_name_lookup(config):
    parts = [
        visibility_name_lookup(config),
        name_name_lookup(config)
    ]
    return '/'.join([ p for p in parts if p != None ])

def ii_name_lookup(config):
    return name_name_lookup(config)

def rf_name_lookup(config):
    return name_name_lookup(config)

def rv_name_lookup(config):
    return name_name_lookup(config)

def rm_name_lookup(config):
    return name_name_lookup(config)

def rt_name_lookup(config):
    return name_name_lookup(config)

def rp_name_lookup(config):
    return name_name_lookup(config)

def no_name_lookup(config):
    return None

def x_value_lookup(config):
    jdk = config._values['jdk']
    jre = config._values['jre']
    return f"{jdk[jdk.find('-') + 1].upper()}{jre[jre.find('-') + 1].upper()}"

def create_constellation_guide():
    names      = [ 'x', 'xxxxxxxx', 'xxxxxxxxxxxxxxxx' ]
    X_names    = [ 'X', 'Xxxxxxxx', 'Xxxxxxxxxxxxxxxx' ]
    visibility = [ '0', '1', '2', '4' ] # {package:0, public:1, private:2, protected:4}
    true_false = ['true', 'false']
    parameter_sets = [
        ParameterSet('T' , CustomConfig(type_value_lookup).init_from_dict({
            'type' : [ x for x in sorted(Plot._labels.values()) ]
        })),
        ParameterSet('B' , CustomConfig(name_value_lookup).init_from_dict({
            'name' : [ 'batik', 'jacop', 'luindex', 'lusearch', 'xalan' ]
        })),
        ParameterSet('W' , CustomConfig(name_value_lookup).init_from_dict({
            'name' : [ 'small', 'default', 'mzc18_1', 'mzc18_2', 'mzc18_3', 'mzc18_4' ]
        })),
        ParameterSet('X' , CustomConfig(x_value_lookup).init_from_dict({
            'jre' : ['17.0.9-graalce', '17.0.14-tem'],
            'jdk' : ['17.0.9-graalce', '17.0.14-tem']
        })),
        # Independent refactoring configurations (Only one will be active per constellation expression.).
        # Only include the ones that we want to discuss.
        # Note: We only need to include the parameters that we want to explore.
        #       The rest will be ignored. How does this affect results?
        #       We will include multiple variations of the same refactorings for parameters that we ignore.
        ParameterSet('EM', CustomConfig(em_name_lookup).init_from_dict({
            'visibility' : visibility
        })),
        ParameterSet('ET', CustomConfig(et_name_lookup).init_from_dict({
            'final' : ['true', 'false']
        })),
        ParameterSet('EC', CustomConfig(ec_name_lookup).init_from_dict({
            # 'name'       : names,
            'visibility' : visibility
        })),
        #ParameterSet('IC', CustomConfig(no_name_lookup).init_from_dict({})),
        #ParameterSet('IM', CustomConfig(no_name_lookup).init_from_dict({})),
        #ParameterSet('IT', CustomConfig(no_name_lookup).init_from_dict({})),
        ParameterSet('II', CustomConfig(ii_name_lookup).init_from_dict({
            "name"       : names
            #,"references" : true_false
        })),
        ParameterSet('RF', CustomConfig(rf_name_lookup).init_from_dict({
            "name"       : names
        })),
        ParameterSet('RV', CustomConfig(rv_name_lookup).init_from_dict({
            "name"       : names
        })),
        ParameterSet('RM', CustomConfig(rm_name_lookup).init_from_dict({
            "name"       : names
        })),
        ParameterSet('RT', CustomConfig(rt_name_lookup).init_from_dict({
            "name"       : X_names
        })),
        ParameterSet('RP', CustomConfig(rp_name_lookup).init_from_dict({
            "name"       : X_names
        }))
    ]
    return ConstellationGuide(parameter_sets)


def print_parameter_tables(path):
    true_false = ["true", "false"]
    names      = [ 'x', 'xxxxxxxx', 'xxxxxxxxxxxxxxxx' ]
    X_names    = [ 'X', 'Xxxxxxxx', 'Xxxxxxxxxxxxxxxx' ]
    visibility = [ '0', '1', '2', '4' ] # {package:0, public:1, private:2, protected:4}
    parameter_sets = [
        ParameterSet('T' , CustomConfig(type_value_lookup).init_from_dict({ 'type' : [ x for x in sorted(Plot._labels.values()) ] })),
        ParameterSet('B' , CustomConfig(name_value_lookup).init_from_dict({ 'name' : [ 'batik', 'jacop', 'luindex', 'lusearch', 'xalan' ] })),
        ParameterSet('W' , CustomConfig(name_value_lookup).init_from_dict({ 'name' : [ 'small', 'default', 'mzc18_1', 'mzc18_2', 'mzc18_3', 'mzc18_4' ] })),
        ParameterSet('X' , CustomConfig(x_value_lookup).init_from_dict({ 'jre'  : ['17.0.9-graalce', '17.0.14-tem'], 'jdk' : ['17.0.9-graalce', '17.0.14-tem'] })),
        # Independent refactoring configurations (Only one will be active per expression.).
        # Only include the ones that we want to discuss.
        # Note: We only need to include the parameters that we want to explore.
        #       The rest will be ignored. How does this affect results?
        #       We will include multiple variations of the same refactorings for parameters that we ignore.
        
        #ParameterSet('EM', CustomConfig(em_name_lookup).init_from_dict({ 'visibility' : visibility })),
        #ParameterSet('RM', CustomConfig(rm_name_lookup).init_from_dict({ 'name' : names })),
        #ParameterSet('ET', CustomConfig(et_name_lookup).init_from_dict({ 'final' : ['true', 'false'] })),
        #ParameterSet('EC', CustomConfig(ec_name_lookup).init_from_dict({ 'name' : names, 'visibility' : visibility }))

        ParameterSet('IC', CustomConfig(no_name_lookup).init_from_dict({
            "replace" : ["false"],
            "remove"  : ["false"]
        })),
        ParameterSet('IM', CustomConfig(no_name_lookup).init_from_dict({
            "mode"   : ["0"],
            "delete" : ["false"]
        })),
        ParameterSet('IT', CustomConfig(no_name_lookup).init_from_dict({
        })),
        ParameterSet('EC', CustomConfig(ec_name_lookup).init_from_dict({
            "name"       : names,
            "visibility" : visibility,
            "qualify"    : true_false,
            "replace"    : ["false"]
        })),
        ParameterSet('EM', CustomConfig(em_name_lookup).init_from_dict({
            "name"       : names,
            "visibility" : visibility,
            "comments"   : ["false"],
            "replace"    : ["true"],
            "exceptions" : ["false"]
        })),
        ParameterSet('ET', CustomConfig(et_name_lookup).init_from_dict({
            "name"                 : names,
            "final"                : true_false,
            "replace"              : ["false"],
            "replaceAllInThisFile" : ["false"],
            "varType"              : ["false"]
        })),
        ParameterSet('II', CustomConfig(no_name_lookup).init_from_dict({
            "name"       : names,
            "references" : true_false,
        })),
        ParameterSet('RF', CustomConfig(no_name_lookup).init_from_dict({
            "name"       : names,
            "references" : ["true"],
            "textual"    : ["false"],
            "getter"     : ["false"],
            "setter"     : ["false"],
            "delegate"   : ["false"],
            "deprecate"  : ["false"]
        })),
        ParameterSet('RV', CustomConfig(no_name_lookup).init_from_dict({
            "name"       : names,
            "references" : ["true"]
        })),
        ParameterSet('RM', CustomConfig(rm_name_lookup).init_from_dict({
            "name"       : names,
            "delegate"   : ["false"],
            "deprecate"  : ["false"],
            "references" : ["true"]
        })),
        ParameterSet('RT', CustomConfig(no_name_lookup).init_from_dict({
            "name"                : X_names,
            "patterns"            : [""],
            "references"          : ["true"],
            "textual"             : ["false"],
            "qualified"           : ["false"],
            "similarDeclarations" : ["false"],
            "matchStrategy"       : ["1"]
        })),
        ParameterSet('RP', CustomConfig(no_name_lookup).init_from_dict({
            "name"       : X_names,
            "references" : ["true"]
        }))
    ]

    captions = {
        'T' : "The table shows all refactoring types that were used in the evaluation.",
        'B' : "The table shows all benchmarks that were used in the evaluation.",
        'W' : "The table shows all workloads that were used in the evaluation.",
        'X' : "The table shows the combinations of compiler (Jdk) and runtime (Jre) that were used in the evaluation.",
        'EC' : "The table shows the \\textit{extract constant} refactoring parameter configurations that were used in the evaluation.",
        'EM' : "The table shows all \\textit{extract method} refactoring parameter configurations that were used in the evaluation.",
        'ET' : "The table shows all \\textit{extract temp} refactoring parameter configurations that were used in the evaluation.",
        'IC' : "The table shows all \\textit{inline constant} refactoring parameter configurations that were used in the evaluation.",
        'IM' : "The table shows all \\textit{inline method} refactoring parameter configurations that were used in the evaluation.",
        'IT' : "The table shows all \\textit{inline temp} refactoring parameter configurations that were used in the evaluation.",
        'II' : "The table shows all \\textit{introduce indirection} refactoring parameter configurations that were used in the evaluation.",
        'RF' : "The table shows all \\textit{rename field} refactoring parameter configurations that were used in the evaluation.",
        'RV' : "The table shows all \\textit{rename local} variable refactoring parameter configurations that were used in the evaluation.",
        'RM' : "The table shows all \\textit{rename method} refactoring parameter configurations that were used in the evaluation.",
        'RT' : "The table shows all \\textit{rename type} refactoring parameter configurations that were used in the evaluation.",
        'RP' : "The table shows all \\textit{rename type} parameter refactoring parameter configurations that were used in the evaluation."
    }

    guide = create_constellation_guide()

    for ps in parameter_sets:
        params = set()
        table  = []
        for i, c in enumerate(ps.configurations):
            for k in c._values.keys():
                params.add(k.capitalize())
            name = f"{ps.name}{i}"
            if ps.name == "X":
                d = c.to_dict()
                for k, v in c.to_dict().items():
                    d[k] = {v}
                name = Constellation(guide).config(d).get_readable_name()
            table.append('&'.join([f"{name}"] + [ v.replace("_", '\\_') for k, v in sorted(c._values.items(), key = lambda it: it[0]) ]) + "\\\\")

        if len(params) == 0: # IC
            continue

        with open(path / (ps.name + '.tex'), 'w') as f:
            f.write("\\begin{table}[!h]" + os.linesep)
            f.write("\\caption{@1}".replace("@1", captions[ps.name]) + os.linesep)
            f.write("\\begin{tabular}{l|*{@N}{l}r}".replace("@N", str(len(params))) + os.linesep)
            f.write('&'.join([ ps.name ] + [ p for p in sorted(params) ]) + "\\\\" + os.linesep)
            f.write("\\hline" + os.linesep)
            f.write(os.linesep.join(table) + os.linesep)
            f.write("\\end{tabular}" + os.linesep)
            f.write("\\end{table}" + os.linesep)
            # f.write() # To separate tables into different paragraphs.

class Constellation:
    def __init__(self, guide):
        self._guide     = guide
        self._type_hint = None

        self._t = None
        self._b = None
        self._w = None
        self._x = None
        self._r = None

    def _validate_filter(filter, parameter_names = set()):
        if filter is None:
            return
        if not isinstance(filter, dict):
            raise ValueError("Expected filter to be None or a dict")
        for param, options in filter.items():
            if not param in parameter_names:
                raise ValueError(f"Expected parameter to be one of: {parameter_names}")
            if not isinstance(options, set):
                raise ValueError("Expected options to be a set of strings")
            for option in options:
                if not isinstance(option, str):
                    raise ValueError("Expected option to be of type string")

    def type(self, filter):
        Constellation._validate_filter(filter, {'type'}) # self._guide.get_parameters('T')
        self._t = filter
        return self

    def bm(self, filter):
        Constellation._validate_filter(filter, {'name'}) # self._guide.get_parameters('B')
        self._b = filter
        return self

    def workload(self, filter):
        Constellation._validate_filter(filter, {'name'}) # self._guide.get_parameters('W')
        self._w = filter
        return self

    def config(self, filter):
        Constellation._validate_filter(filter, {'jre', 'jdk'}) # self._guide.get_parameters('X')
        self._x = filter
        return self

    def _get_type(self):
        if self._t == None:
            return None
        return [ x for x in self._t['type'] ][0]

    # The type_hint is intended to handle the split_diff, where
    # the type is known, but not assigned. 
    def options(self, filter, type_hint = None):
        if filter == None:
            self._r = None
            return self
        if type_hint == None and self._t == None:
            raise ValueError("Please register the type filter first")
        if type_hint == None and len(self._t['type']) != 1:
            raise ValueError("Refactoring configuration is only applicable when a single type is specified.")
        t = type_hint if self._t == None else self._get_type()
        Constellation._validate_filter(filter, self._guide.get_parameters(t))
        if type_hint != None:
            self._type_hint = type_hint
        self._r = filter
        return self

    def get_filter(self):
        filter = dict()
        if self._t != None:
            filter['T'] = self._t
        if self._b != None:
            filter['B'] = self._b
        if self._w != None:
            filter['W'] = self._w
        if self._x != None:
            filter['X'] = self._x
        if self._r != None:
            if self._type_hint != None:
                filter[self._type_hint] = self._r
            else:
                filter[self._get_type()] = self._r
        return filter

    def get_name(self):
        return self._guide.get_expression(self.get_filter())

    def get_readable_name(self):
        return self._guide.get_readable_name(self.get_filter())

    def split_diff(a, b):
        _t = b._t if a._t == None else (a._t if b._t == None else None)
        _b = b._b if a._b == None else (a._b if b._b == None else None)
        _w = b._w if a._w == None else (a._w if b._w == None else None)
        _x = b._x if a._x == None else (a._x if b._x == None else None)
        _r = b._r if a._r == None else (a._r if b._r == None else None)
        return Constellation(a._guide).type(_t).bm(_b).workload(_w).config(_x).options(_r, a._get_type())

class ANOVATable:
    def __init__(self, experiments, repo, file, constellation):
        self._experiments  = experiments
        self.constellation = constellation
        self.data, self.coordinates = repo.filter_data_file(file, constellation.get_filter())

    def compute(self, label = None, caption = None, filename = None, output_location = None):
        i_vars    = set()
        d_vars    = set()
        variables = set()
        results   = []
        is_r_set  = self.constellation._r != None

        required_baselines = set()

        for d, speedup in self.data:
            t = d['T']['type']
            b = d['B']['name']
            w = d['W']['name']
            x = d['X']
            m = d['M']
            r = d[t]

            xc = Configuration().init_from_dict(x)
            required_baselines.add((b, w, xc.id()))

            entry = { **x, **m, 'R' : t, **(r if is_r_set else {}) }
            entry['EXECUTION_TIME'] = float(speedup)
            results.append(entry)

            for k in m.keys():
                d_vars.add(k)
                variables.add(k)

            for k in x.keys():
                i_vars.add(k)
                variables.add(k)

            if is_r_set:
                # Include refactoring parameters.
                for k in r.keys():
                    i_vars.add(k)
                    variables.add(k)

        variables.add('R')
        i_vars.add('R')

        for (x, b, w), combinations in self._experiments.workloads().parameter_combinations().items():
            for c in combinations:
                if (b, w, c.id()) in required_baselines:
                    # Baseline value is always 1.0 for all dependent variables.
                    baseline_metrics = dict([ (v, 1.0) for v in d_vars ])
                    results.append({**c._values, **baseline_metrics, 'R' : 'N/A'})

        try:
            ANOVATable.anova(variables, d_vars, i_vars, results, filename, output_location)
        except Exception as e:
            print()
            print("ERROR", str(e)) # TODO: For some reason this happens in the ols method for RT_rc
            print()

    def setdftype(df, name, type):
        if name in df:
            df[name] = df[name].astype(type)

    def anova(variables, d_vars, i_vars, data, filename, output_location):
        # metrics.txt gives all the dependent variables
        # parameters.txt gives all independent categorical variables and their value sets
        # configuration.txt gives a specific combination of the independent variables

        csv_path = output_location / f'{filename}.csv'

        print("Computing ANOVA", str(csv_path), d_vars, i_vars, "DATA LEN:", len(data))

        with open(csv_path, 'w') as f:
            header = ','.join(sorted(variables))
            f.write(header + os.linesep)
            for d in data:
                f.write(','.join([ str(d[var] if var in d else 'N/A') for var in sorted(variables) ]) + os.linesep)

        df = pandas.read_csv(csv_path)

        for v in d_vars:
            ANOVATable.setdftype(df, v, float)

        for v in i_vars:
            ANOVATable.setdftype(df, v, str)

        for d_var in d_vars:
            ## https://www.statsmodels.org/stable/gettingstarted.html
            ## https://patsy.readthedocs.io/en/latest/formulas.html
            formula = '{} ~ {}'.format(d_var, ' + '.join(sorted(i_vars)))
            #print("-"*80)
            #print("Formula", formula)
            #print("-"*80)
            mod = ols(formula, data = df).fit()
            res = sm.stats.anova_lm(mod)
            #print(res)
            table_path = output_location / f"{filename}.{d_var}.table"
            with open(table_path, 'w') as f:
                f.write(str(res))

            params_filter = { 'R', 'bm', 'bm_workload', 'jdk', 'jre', 'name', 'visibility', 'final' } # Focus for analysis.
            rows = []
            for i, l in enumerate(str(res).split(os.linesep)):
                if l.find('NaN') == -1:
                    found = False
                    for p in params_filter:
                        if p in l:
                            found = True
                            break
                    if found or i == 0:
                        l = l.replace('bm_workload', 'workload')
                        l = l.replace('bm', 'benchmark')
                        rows.append((['param'] if i == 0 else []) + [ x.strip().replace('_', '\\_') for x in [ y for y in l.strip().split(' ') if y.strip() != "" ] ])

            columns = '&'.join(rows[0])
            rows    = rows[1:]

            caption = f"The table shows the ANOVA results for model: ${formula}$. The computation was based on {len(data)} measurements."
            with open(f'{output_location}/{filename}_{d_var}_N{len(data)}.tex', 'w') as f:
                #f.write("\\begin{table}[!h]" + os.linesep)
                #f.write("\\caption{@CAPTION}".replace('@CAPTION', caption) + os.linesep)
                f.write("\\begin{tabular}{c|*{@N}{r}r}".replace("@N", str(len(rows[0]) - 1)) + os.linesep)
                f.write(columns + "\\\\" + os.linesep)
                f.write("\\hline" + os.linesep)
                f.write(os.linesep.join([ '&'.join(row) + "\\\\" for row in rows ]) + os.linesep)
                f.write("\\end{tabular}" + os.linesep)
                #f.write("\\end{table}" + os.linesep)

            #print("-"*80)

class Violin:
    def __init__(self, repo, file, constellation):
        self.constellation = constellation
        self.data, self.coordinates = repo.filter_data_file(file, constellation.get_filter())
        # self.caption = f"The {constellation.get_name()} constellation with {len(self.data)} measurements."

    def split(self, yrange):
        data       = []
        data_below = []
        data_above = []
        for entry, speedup in self.data:
            if speedup <= yrange[0]:
                data_below.append(speedup)
            elif speedup >= yrange[1]:
                data_above.append(speedup)
            else:
                data.append(speedup)
        self._data       = data
        self._data_below = data_below
        self._data_above = data_above
        return self

    def get_data_below(self):
        return self._data_below

    def get_data_above(self):
        return self._data_above

    def get_data(self):
        return self._data

def _plot_from_file(args):
    output_location       = Path(args.plots_out)
    table_output_location = Path(args.tables_out)

    repo = Experiments(args.x_location)
    file = Path(args.file)

    if not file.exists():
        with open(file, 'w') as f:
            repo.create_data_file(f)

    guide = create_constellation_guide()

    rtypes     = sorted(Plot._labels.values())
    benchmarks = ['batik', 'jacop', 'luindex', 'lusearch', 'xalan']
    workloads  = {
        'batik'    : ['small', 'default'],
        'jacop'    : ['mzc18_1', 'mzc18_2', 'mzc18_3', 'mzc18_4'],
        'luindex'  : ['small', 'default'],
        'lusearch' : ['small', 'default'],
        'xalan'    : ['small', 'default']
    }

    config           = Configuration().jdk(['17.0.9-graalce', '17.0.14-tem']).jre(['17.0.9-graalce', '17.0.14-tem']).get_all_combinations()
    config_to_filter = lambda c: dict([ (k, {v}) for k, v in c.to_dict().items() ])

    # TODO: Consider which tables we want to look at.

    ANOVATable(experiment.Experiments(args.x_location), repo, file, Constellation(guide).type({ 'type' : set(rtypes) }))\
        .compute(filename = "all_workloads_and_types", output_location = table_output_location)

    for rtype in rtypes:
        all_options_filter = guide.get_parameter_options_filter(rtype)
        constellation      = Constellation(guide).type({ 'type' : {rtype} })
        if len(all_options_filter) != 0:
            constellation = constellation.options(all_options_filter)
        ANOVATable(experiment.Experiments(args.x_location), repo, file, constellation)\
            .compute(filename = f'{rtype}_rc', output_location = table_output_location)

    return

    # Split T by R
    for rtype in rtypes:
        r_config = guide.get_parameter_configurations(rtype)
        violins = [
            Violin(repo, file,
                Constellation(guide).type({ 'type' : {rtype} })
            )
        ] + [
            Violin(repo, file,
                Constellation(guide).type({ 'type' : {rtype} }).options(config_to_filter(rc))
            ) for rc in r_config
        ]
        Plot.plot_violins(f"{rtype} by R", violins,
                          label           = f"{rtype}_by_rc",
                          caption         = f"The figure show a speedup plot where all {rtype} data is split by corresponding refactoring configurations.",
                          output_location = output_location,
                          filename        = f"{rtype}_by_rc")

    for b in benchmarks:
        ANOVATable(
            experiment.Experiments(args.x_location),
            repo,
            file,
            Constellation(guide).bm({ 'name' : {b} })
        )\
        .compute(filename = f"{b}_all_types", output_location = table_output_location)

    # Split all by type.
    violins = [
        Violin(repo, file,
            Constellation(guide).type({ 'type' : {rtype} })
        )
        for rtype in rtypes
    ]
    Plot.plot_violins("All types", violins, is_split = False,
                      label           = "all_by_type",
                      caption         = "The figure shows a speedup plot where all data is split by refactoring type.",
                      output_location = output_location,
                      filename        = "all_by_type"
                      )

    # Split all by X (/X)
    violins = [
        Violin(repo, file,
            Constellation(guide)
        )
    ] + [
        Violin(repo, file,
            Constellation(guide).config(config_to_filter(c))
        ) for c in config
    ]
    Plot.plot_violins(f"All by X", violins,
                      label           = f"all_by_X",
                      caption         = f"The figure show a speedup plot where all data is split by JDK and JRE configurations.",
                      output_location = output_location,
                      filename        = f"all_by_X")

    # Split B by X (B/X)
    for bm in benchmarks:
        violins = [
            Violin(repo, file,
                Constellation(guide).bm({ 'name' : {bm} })
            )
        ] + [
            Violin(repo, file,
                Constellation(guide).bm({ 'name' : {bm} }).config(config_to_filter(c))
            ) for c in config
        ]
        Plot.plot_violins(f"Split {bm} by configurations", violins,
                          label           = f"{bm}_by_X",
                          caption         = f"The figure show a speedup plot where {bm} data is split by JDK and JRE configurations.",
                          output_location = output_location,
                          filename        = f"{bm}_by_X"
                          )

    # Split B/W by X (B/W/X)
    for bm in benchmarks:
        for w in workloads[bm]:
            violins = [
                Violin(repo, file,
                    Constellation(guide).bm({ 'name' : {bm} }).workload({ 'name' : {w} })
                )
            ] + [
                Violin(repo, file,
                    Constellation(guide).bm({ 'name' : {bm} }).workload({ 'name' : {w} }).config(config_to_filter(c))
                ) for c in config
            ]
            w_ = w.replace('_', '\\_')
            Plot.plot_violins(f"Split {bm} by configurations", violins,
                              label           = f"{bm}_{w_}_by_X",
                              caption         = f"The figure show a speedup plot where {bm}/{w_} is split by JDK and JRE configurations.",
                              output_location = output_location,
                              filename        = f"{bm}_{w}_by_X"
                              )

    # Split B/W by T (B/W/T)
    for bm in benchmarks:
        for w in workloads[bm]:
            violins = [
                Violin(repo, file,
                    Constellation(guide).bm({ 'name' : {bm} }).workload({ 'name' : {w} })
                )
            ] + [
                Violin(repo, file,
                    Constellation(guide).bm({ 'name' : {bm} }).workload({ 'name' : {w} }).type({ 'type' : {rtype} })
                ) for rtype in rtypes
            ]
            w_ = w.replace('_', '\\_')
            Plot.plot_violins(f"Split {bm} by configurations", violins,
                              label           = f"{bm}_{w_}_by_type",
                              caption         = f"The figure show a speedup plot where {bm}/{w_} is split by type.",
                              output_location = output_location,
                              filename        = f"{bm}_{w}_by_type"
                              )

    # Split B/W/X by T (B/W/X/T)
    for bm in benchmarks:
        for w in workloads[bm]:
            for c in config:
                violins = [
                    Violin(repo, file,
                        Constellation(guide).bm({ 'name' : {bm} }).workload({ 'name' : {w} }).config(config_to_filter(c))
                    )
                ] + [
                    Violin(repo, file,
                        Constellation(guide).bm({ 'name' : {bm} }).workload({ 'name' : {w} }).config(config_to_filter(c)).type({ 'type' : {rtype} })
                    ) for rtype in rtypes
                ]
                w_ = w.replace('_', '\\_')
                x_ = ''.join([
                    'T' if c.jdk().find('tem') != -1 else 'G',
                    'T' if c.jre().find('tem') != -1 else 'G'
                ])
                Plot.plot_violins(f"Split {bm}/{w}/{x_} by type", violins,
                                  label           = f"{bm}_{w_}_{x_}_by_type",
                                  caption         = f"The figure show a speedup plot where {bm}/{w_}/{x_} is split by type.",
                                  output_location = output_location,
                                  filename        = f"{bm}_{w}_{x_}_by_type"
                                  )

    # Split B/X by T (B/X/T)
    for bm in benchmarks:
        for c in config:
            violins = [
                Violin(repo, file,
                    Constellation(guide).bm({ 'name' : {bm} }).config(config_to_filter(c))
                )
            ] + [
                Violin(repo, file,
                    Constellation(guide).bm({ 'name' : {bm} }).config(config_to_filter(c)).type({ 'type' : {rtype} })
                ) for rtype in rtypes
            ]
            c_ = ''.join([
                'T' if c.jdk().find('tem') != -1 else 'G',
                'T' if c.jre().find('tem') != -1 else 'G'
            ])
            Plot.plot_violins(f"Split {bm} by configurations", violins,
                              label           = f"{bm}_{c_}_by_type",
                              caption         = f"The figure show a speedup plot where {bm}/{c_} is split by type.",
                              output_location = output_location,
                              filename        = f"{bm}_{c_}_by_type"
                              )

    # Selection of benchmarks, workloads, and types that show signs of
    # performance effects on average based on manual inspection of violins.
    # Since some violins have shown signs of being a "poor" fitting to some
    # of the data, we could missing interesting effects by only investigating
    # a subset of splits here.
    rc_benchmarks = {
        'jacop' : {
            'mzc18_2' : {
                'TG' : ['EM', 'IC', 'RF']
            },
            'mzc18_3' : {
                'GG' : ['EM'],
                'TG' : ['IC'],
                'TT' : ['IT', 'RM', 'RV']
            }
        },
        'lusearch' : {
            'small' : {
                'GG' : ['IC', 'IT', 'RF', 'RT'],
                'GT' : ['EC', 'EM', 'ET', 'IC', 'II', 'IT', 'RF', 'RM', 'RT', 'RV'],
                'TG' : ['EM', 'IC', 'II', 'RM', 'RT', 'RV'],
                'TT' : ['EC']
            }
        },
        'xalan' : {
            'small' : {
                'GG' : ['RT'],
                'GT' : ['EC', 'IC', 'II', 'IT', 'RT'],
                'TT' : ['RT']
            }
        }
    }
    for rtype in rtypes:
        # Split TBX by R (TBX/R)
        r_config = guide.get_parameter_configurations(rtype)
        if len(r_config) == 0:
            continue
        for bm in benchmarks:
            #if not bm in rc_benchmarks:
            #    continue
            for w in workloads[bm]:
                #if not w in rc_benchmarks[bm]:
                #    continue
                # Split TBWX by R (TBWX/R)
                for c in config:
                    c_ = ''.join([
                        'T' if c.jdk().find('tem') != -1 else 'G',
                        'T' if c.jre().find('tem') != -1 else 'G'
                    ])
                    #if not c_ in rc_benchmarks[bm][w]:
                    #    continue
                    #if not rtype in rc_benchmarks[bm][w][c_]:
                    #    continue
                    violins = [
                        Violin(repo, file,
                            Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {bm} }).workload({ 'name' : {w} }).config(config_to_filter(c))
                        )
                    ] + [
                        Violin(repo, file,
                               Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {bm} }).workload({ 'name' : {w} }).config(config_to_filter(c)).options(config_to_filter(rc))
                               ) for rc in r_config
                    ]
                    w_ = w.replace('_', '\\_')
                    Plot.plot_violins(f"Split {bm}/{w_}/{c_}/{rtype} by refactoring configurations", violins,
                                      label           = f"{bm}_{w_}_{c_}_{rtype}_by_rc",
                                      caption         = f"The figure show a speedup plot where {bm}/{w_}/{c_}/{rtype} is split by refactoring configuration.",
                                      output_location = output_location,
                                      filename        = f"{bm}_{w}_{c_}_{rtype}_by_rc"
                                      )

    return

    b_data1 = dict()
    b_data2 = dict()

    off = 0
    for rtype in rtypes:
        violins = [
            Violin(repo, file,
                Constellation(guide).type({ 'type' : {rtype} })
            ),
            Violin(repo, file,
                Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {'batik'} })
            ),
            Violin(repo, file,
                Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {'jacop'} })
            ),
            Violin(repo, file,
                Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {'luindex'} })
            ),
            Violin(repo, file,
                Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {'lusearch'} })
            ),
            Violin(repo, file,
                Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {'xalan'} })
            )
        ]
        Plot.plot_violins(f"{rtype}", violins)

        # The following plots are just for data validation.
        # But they are not very clear. Therefore, I also
        # effectively check the set intersection between
        # data indices for different refactoring types
        # which shows that all datapoints are selected
        # at most once.
        loff = 0
        for i, violin in enumerate(violins[1:]):
            if not i in b_data1:
                b_data1[i] = []
                b_data2[i] = []
            b_data1[i].append((range(0, len(violin.get_data())), [ x + off for x in violin.get_data() ], f"C{i}"))
            xs = [ x for x, y in violin.coordinates ]
            ys = [ y for x, y in violin.coordinates ]
            b_data2[i].append((xs, ys, f"C{i}"))
            plt.plot(range(0, len(violin.get_data())), [ x + loff for x in violin.get_data() ], f"C{i}")
            loff = loff + 2
        plt.show()
        plt.close()
        off = off + 2

        # Split T by X (T/X)
        violins = [
            Violin(repo, file,
                Constellation(guide).type({ 'type' : {rtype} })
            )
        ] + [
            Violin(repo, file,
                Constellation(guide).type({ 'type' : {rtype} }).config(config_to_filter(c))
            ) for c in config
        ]
        Plot.plot_violins(f"{rtype} by configurations", violins)

        # Split TB by X (TB/X)
        for bm in ['batik', 'jacop', 'luindex', 'lusearch', 'xalan']:
            violins = [
                Violin(repo, file,
                    Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {bm} })
                )
            ] + [
                Violin(repo, file,
                    Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {bm} }).config(config_to_filter(c))
                ) for c in config
            ]
            Plot.plot_violins(f"{bm} configurations", violins)

        # Split TBX by R (TBX/R)
        r_config = guide.get_parameter_configurations(rtype)
        if len(r_config) == 0:
            print("No refactoring configurations registered for type: " + rtype)
            continue
        for bm in ['batik', 'jacop', 'luindex', 'lusearch', 'xalan']:
            # Split TB by R (TB/R)
            violins = [
                Violin(repo, file,
                    Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {bm} })
                )
            ] + [
                Violin(repo, file,
                    Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {bm} }).options(config_to_filter(rc))
                ) for rc in r_config
            ]
            Plot.plot_violins(f"{rtype}/{bm}", violins)

            # Split TBX by R (TBX/R)
            for c in config:
                violins = [
                    Violin(repo, file,
                        Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {bm} }).config(config_to_filter(c))
                    )
                ] + [
                    Violin(repo, file,
                        Constellation(guide).type({ 'type' : {rtype} }).bm({ 'name' : {bm} }).config(config_to_filter(c)).options(config_to_filter(rc))
                    ) for rc in r_config
                ]
                Plot.plot_violins(f"{bm} configurations", violins)

    for i, vs in b_data1.items():
        for v in vs:
            plt.plot(*v)
        plt.show()
        plt.close()

    for i, vs in b_data2.items():
        indices = set()
        for v in vs:
            idxs = v[1]
            for j in idxs:
                if j in indices:
                    raise ValueError("ERROR: Overlapping data indices for distinct refactoring types", i, j)
                indices.add(j)
            plt.plot(*v)
        plt.show()
        plt.close()

def _main(args):
    repo = Experiments(args.x_location)
    xbw  = repo.get_xbw()

    # Write all data to specified file.
    #with open('all-data-file.txt', 'w') as f:
    #    repo.create_data_file(f)

    _plot_from_file(args)

    return

    # print(repo.filter_data_file('all-data-file.txt', { 'B' : { 'name' : 'xalan' } }))

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
    parser.add_argument('--file', required = False, default = 'data.txt',
        help = "File into which all measurements are written.")
    parser.add_argument('--bs', required = False, nargs = '+', default = [],
        help = "Benchmarks to plot.")
    parser.add_argument('--print-ptables', required = False, default = False, action = 'store_true',
        help = "Print parameter tables to stdout.")
    parser.add_argument('--print-ptables-path', required = False, default = 'tables',
        help = "Output folder path parameter tables")
    parser.add_argument('--print-btable', required = False, default = False, action = 'store_true',
        help = "Print baseline table to standard output.")
    parser.add_argument('--baseline-files', required = False, nargs = '+',  default = ['baseline.txt'],
        help = "Baseline input files for --print-btable")
    parser.add_argument('--baseline-out', required = False,
        help = "Baseline tables output folder.")
    parser.add_argument('--plots-out', required = False, default = 'figures',
        help = "Plots output folder.")
    parser.add_argument('--tables-out', required = False, default = 'tables/anova',
        help = "ANOVA tables output folder.")
    args = parser.parse_args()

    if args.print_ptables:
        print_parameter_tables(Path(args.print_ptables_path))
        exit(0)

    if args.print_btable:
        if not len(args.baseline_files) > 0:
            raise ValueError("Please specify one or more baseline files")
        if not Path(args.baseline_out).exists():
            raise ValueError("Please create the output location")
        Experiments(args.x_location).print_baseline(args)
        exit(0)

    _main(args)

