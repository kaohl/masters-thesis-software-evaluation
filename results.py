#!/bin/env python3

import argparse
import json
import os
import pandas
import shutil
import statsmodels.api as sm

from functools               import reduce
from pathlib                 import Path
from patsy                   import dmatrices
from statsmodels.formula.api import ols

from configuration import Configuration, Metrics
from opportunity_cache import RefactoringDescriptor

# TODO
# Add method signature to meta data of all descriptors so
# that we can determine our coverage across the set of
# sampled methods.

def get_bm_workloads(args):
    bm = args.bm
    for dir, experiments, files in os.walk(args.x_location):
        for experiment in experiments:
            if experiment == 'steering':
                continue
            for dir1, benchmarks, files1 in os.walk(Path(dir) / experiment / 'workloads'):
                for benchmark in benchmarks:
                    if not benchmark == bm:
                        continue
                    for dir2, workloads, files2 in os.walk(Path(dir1) / benchmark):
                        return [ Path(dir2) / workload for workload in workloads ]
                break
        break
    return []

def get_refactorings_and_benchmarks(args):
    data_location = Path(args.x_location) / 'data' / args.bm
    refactorings  = set()
    benchmarks    = set()
    opportunities = get_opportunities(data_location)
    for opportunity in opportunities:
        instances = get_instances(opportunity)
        for instance in instances:
            refactorings.add((opportunity.name, instance.name))
            for execution in get_executions(instance):
                for configuration in get_configurations(execution):
                    # Executions don't matter here. We add all configurations
                    # that exists below the refactoring in all executions.
                    benchmarks.add((opportunity.name, instance.name, configuration.name))
    return refactorings, benchmarks

# Print all refactorings and/or benchmarks that no
# longer match a descriptor list entry or an active
# configuration.
#   This is useful when configuration changes in a
# way that invalidates descriptors or configurations.
def show_deprecated(args):
    x_location    = Path(args.x_location) / args.x
    data_location = Path(args.x_location) / 'data' / args.bm

    refactorings, benchmarks = get_refactorings_and_benchmarks(args)

    listed_refactorings = set()
    listed_benchmarks   = set()

    output_location = Path('temp/deprecated')
    if output_location.exists():
        shutil.rmtree(output_location)
    output_location.mkdir(parents = True)

    statistics = dict() # { refactoring-id : count }

    for w_location in get_bm_workloads(args):
        lists_location = w_location / 'lists'
        combinations   = Configuration().load(w_location / 'parameters.txt').get_all_combinations()
        for dir1, lists, files1 in os.walk(lists_location):
            for lst in lists:
                list_descriptors = lists_location / lst / 'descriptors.txt'
                if not list_descriptors.exists():
                    continue
                with open(list_descriptors, 'r') as f:
                    for line in f:
                        descriptor = RefactoringDescriptor(line)
                        key        = (descriptor.opportunity_id(), descriptor.id())
                        if not key in refactorings:
                            # The refactoring has not yet been created
                            # and is therefore irrelevant here.
                            continue
                        listed_refactorings.add(key)

                        ref_id = descriptor.refactoring_id()
                        if not ref_id in statistics:
                            statistics[ref_id] = 0
                        statistics[ref_id] = statistics[ref_id] + 1

                        # Add all valid configurations for which we have
                        # already captured measurements.
                        for configuration in combinations:
                            if (*key, configuration.id()) in benchmarks:
                                listed_benchmarks.add((*key, configuration.id()))
            break

    with open(output_location / 'counts.txt', 'w') as f:
        for k, v in statistics.items():
            f.write(f"{k}={v}{os.linesep}")
        f.write(f"all={reduce(lambda x,y: x+y, statistics.values(), 0)}{os.linesep}")

    deprecated_refactorings = refactorings - listed_refactorings
    deprecated_benchmarks   = benchmarks   - listed_benchmarks

    with open(output_location / 'refactorings.txt', 'w') as f:
        for (opportunity_id, instance_id) in deprecated_refactorings:
            instance = data_location / opportunity_id / instance_id
            f.write(f"{instance}{os.linesep}")

    with open(output_location / 'benchmarks.txt', 'w') as f:
        for (opportunity_id, instance_id, configuration_id) in deprecated_benchmarks:
            instance = data_location / opportunity_id / instance_id
            for execution in get_executions(instance):
                f.write(f"{execution / 'stats' / configuration_id}{os.linesep}")

class FailureReport:
    def __init__(self):
        self._r_failure         = []
        self._b_generic_failure = []
        self._b_timeout_failure = []
        self._b_unknown_failure = []

    def refactoring_failure(self, descriptor, path):
        self._r_failure.append((descriptor, path))

    def benchmark_failure(self, descriptor, path):
        if (path / 'GENERIC').exists():
            self._b_generic_failure.append((descriptor, path))
        elif (path / 'TIMEOUT').exists():
            self._b_generic_failure.append((descriptor, path))
        else:
            self._b_unknown_failure.append((descriptor, path))

    def publish(self, r = False, g = False, t = False):
        if r:
            print("Refactoring Failures")
            for e in self._r_failure:
                with open(e[1] / 'refactoring-output.txt', 'r') as f:
                    print('-' * 20)
                    print(f"{e[0].line()}")
                    print(''.join(f.readlines()))
                    print('-' * 20)
        if g:
            print("Benchmark Generic Failures")
            for e in self._b_generic_failure:
                with open(e[1] / 'FAILURE', 'r') as f:
                    print('-' * 20)
                    print(f"{e[0].line()}")
                    print(''.join(f.readlines()))
                    print('-' * 20)
        if t:
            print("Benchmark Timeout Failures")
            for e in self._b_timeout_failure:
                with open(e[1] / 'FAILURE', 'r') as f:
                    print('-' * 20)
                    print(f"{e[0].line()}")
                    print(''.join(f.readlines()))
                    print('-' * 20)

def create_failure_report(args):
    x_location    = Path(args.x_location) / args.x
    data_location = Path(args.x_location) / 'data' / args.bm
    report        = FailureReport()

    opportunities = get_opportunities(data_location)
    for opportunity in opportunities:
        instances = get_instances(opportunity)
        for instance in instances:
            descriptor = get_descriptor(instance)
            if (instance / 'FAILURE').exists():
                report.refactoring_failure(descriptor, instance)
            executions = get_executions(instance)
            for execution in executions:
                configurations = get_configurations(execution)
                for configuration in configurations:
                    if (configuration / 'FAILURE').exists():
                        report.benchmark_failure(descriptor, configuration)
    report.publish(
        'refactor' in args.report,
        'generic'  in args.report,
        'timeout'  in args.report
    )

class Results:

    def __init__(self, x_location, bm, wl, ls):
        self._x_location = x_location
        self._bm         = bm
        self._wl         = wl
        self._ls         = ls

        self._variables   = set()
        self._i_variables = set()
        self._d_variables = set()
        self._results     = []

    def add_benchmark(self, descriptor, location):
        if (location / 'FAILURE').exists():
            return
        config   = Configuration().load(location / 'configuration.txt')
        # Only include data for specified workload to get all comparable results.
        if not config.bm_workload() == self._wl:
            return
        metrics  = Metrics().load(location / 'metrics.txt')
        identity = { 'data' : str(location) }
        params   = config.parameters()
        self._results.append({ **identity, **params, **metrics._values })
        if len(self._variables) == 0:
            for k, v in params.items():
                self._i_variables.add(k)
                self._variables.add(k)
            for k, v in metrics._values.items():
                self._d_variables.add(k)
                self._variables.add(k)

    def compute_statistics(self):
        if len(self._results) == 0:
            return

        results_location = Path(self._x_location) / 'results' / self._bm / self._wl
        results_location.mkdir(exist_ok = True, parents = True)

        with open(results_location / (self._ls + '.results'), 'w') as f:
            for result in self._results:
                f.write(str(result) + os.linesep)

        csv_path = results_location / (self._ls + '.csv')
        with open(csv_path, 'w') as f:
            header = ','.join(sorted(self._variables))
            f.write(header + os.linesep)
            for result in self._results:
                f.write(','.join([ result[var] for var in sorted(self._variables) ]) + os.linesep)

        anova(self._i_variables, self._d_variables, csv_path)

def get_opportunities(location):
    for dir, folders, files in os.walk(location):
        return [ Path(dir) / folder for folder in folders ]
    return []

def get_instances(opportunity):
    for dir, folders, files in os.walk(opportunity):
        return [ Path(dir) / folder for folder in folders ]
    return []

def get_descriptor(instance):
    return RefactoringDescriptor.load(instance / 'descriptor.txt')

def get_executions(instance):
    for dir, folders, files in os.walk(instance):
        return [ Path(dir) / folder for folder in folders ]
    return []

def get_configurations(execution):
    for dir, folders, files in os.walk(execution / 'stats'):
        return [ Path(dir) / folder for folder in folders ]
    return []

# Compute results per benchmark, ignoring lists.
def compute_all(args):
    x_location    = Path(args.x_location) / args.x
    data_location = Path(args.x_location) / 'data' / args.bm
    results       = Results(x_location, args.bm, args.workload, 'all')

    opportunities = get_opportunities(data_location)
    for opportunity in opportunities:
        instances = get_instances(opportunity)
        for instance in instances:
            descriptor = get_descriptor(instance)
            executions = get_executions(instance)
            for execution in executions:
                configurations = get_configurations(execution)
                for configuration in configurations:
                    results.add_benchmark(descriptor, configuration)
    results.compute_statistics()

def compute_progress(args):
    x_location = Path(args.x_location) / args.x
    bm         = args.bm
    workload   = args.workload
    lists_location = x_location / 'workloads' / bm / workload / 'lists'
    n_combinations = len(Configuration().load(x_location / 'workloads' / bm / workload / 'parameters.txt').get_all_combinations())
    for dir1, lists, files1 in os.walk(lists_location):
        for lst in lists:
            list_descriptors = lists_location / lst / 'descriptors.txt'
            if not list_descriptors.exists():
                continue
            n_success = 0
            n_failure = 0
            n_total   = 0
            n_benched = 0
            with open(list_descriptors, 'r') as f:
                for line in f:
                    descriptor    = RefactoringDescriptor(line)
                    data_location = Path(args.x_location) / 'data' / bm / descriptor.opportunity_id() / descriptor.id()
                    n_total       = n_total + 1
                    if not data_location.exists():
                        continue
                    if (data_location / 'FAILURE').exists():
                        n_failure = n_failure + 1
                        continue
                    n_success = n_success + 1
                    for dir2, executions, files2 in os.walk(data_location):
                        for execution in executions:
                            for dir3, configurations, files3 in os.walk(Path(dir2) / execution / 'stats'):
                                n_benched = n_benched + len(configurations)
                                break
                        break
            result = f"{(bm, workload, lst)}: {n_success}/{n_failure}/{n_total}, {n_benched}/{n_total * n_combinations}"
            print(result)
        break

def compute_results(args):
    x_location     = Path(args.x_location) / args.x
    bm             = args.bm
    workload       = args.workload
    views_location = x_location / 'workloads' / bm / workload / 'views'
    lists_location = x_location / 'workloads' / bm / workload / 'lists'
    views          = []
    if not views_location.exists():
        print("No views to compute", str(views_location))
    for dir, folders, files in os.walk(views_location):
        for file in files:
            with open(Path(dir) / file, 'r') as f:
                views.append((Path(file).stem, json.load(f)))
        break
    for name, queries in views:
        variables                     = set() # All.
        results_independent_variables = set() # See 'parameters.txt'.
        results_dependent_variables   = set() # See 'metrics.txt'.
        results_location              = Path(x_location) / 'results' / bm / workload
        results                       = []
        for lst, filters in queries.items(): # [{ "<list>": [<filter>], ... }]
            list_location = lists_location / lst
            list_file     = list_location / 'descriptors.txt'
            if not list_location.exists():
                raise ValueError("No such list", str(list_location))
            with open(list_file, 'r') as f:
                for index, line in enumerate(f):
                    descriptor    = RefactoringDescriptor(line)
                    data_location = Path(args.x_location) / 'data' / bm / descriptor.opportunity_id() / descriptor.id()
                    if not data_location.exists():
                        # We have not yet created the corresponding refactoring.
                        # However, if the refactoring framework changes, or the
                        # seed for shuffling opportunities, then there might be
                        # refactorings ahead that we would miss unless we process
                        # the whole list. Therefore, we continue down the list.
                        continue

                    # Validate the stored descriptor.
                    stored_id = RefactoringDescriptor.load(data_location / 'descriptor.txt').id()
                    if stored_id != descriptor.id():
                        raise ValueError(
                            f"The ID of the stored descriptor '{stored_id}' does not match the expected value '{descriptor.id()}'"
                        )

                    for dir1, executions, files1 in os.walk(data_location):
                        for execution in executions:
                            if (Path(dir1) / execution / 'FAILURE').exists():
                                continue # Refactoring failed.
                            found_match = False
                            for filter in filters:
                                if descriptor.is_match(filter):
                                    found_match = True
                                    break
                            if not found_match:
                                continue
                            stats_location = Path(dir1) / execution / 'stats'
                            if not stats_location.exists():
                                continue # Not benchmarked yet.
                            for dir2, configuration_ids, files2 in os.walk(stats_location):
                                for id in configuration_ids:
                                    if (Path(dir2) / id / 'FAILURE').exists():
                                        continue # Benchmark failed.
                                    #
                                    # TODO: Consider which parameters and meta attributes are of interest in the analysis, if any.
                                    #
                                    config   = Configuration().load(Path(dir2) / id / 'configuration.txt')

                                    # Only include measurements for the specified workload.
                                    if not config.bm_workload() == workload:
                                        continue

                                    metrics  = Metrics().load(Path(dir2) / id / 'metrics.txt')
                                    identity = { 'data' : '/'.join([descriptor.opportunity_id(), descriptor.id(), execution, 'stats', id]) }
                                    results.append({ **identity, **config._values, **metrics._values })
                                    if len(variables) == 0:
                                        # All configurations and metrics contain the same variables.
                                        #
                                        # TODO: This will not be true when we involve meta attributes
                                        #       or mix refactorings of different types.
                                        #
                                        for k, v in config._values.items():
                                            results_independent_variables.add(k)
                                            variables.add(k)
                                        for k, v in metrics._values.items():
                                            results_dependent_variables.add(k)
                                            variables.add(k)
                                break
                        break

        if len(results) == 0:
            continue

        results_location.mkdir(exist_ok = True, parents = True)
        with open(results_location / (name + '.results'), 'w') as f:
            for result in results:
                f.write(str(result) + os.linesep)

        csv_path = results_location / (name + '.csv')
        with open(csv_path, 'w') as f:
            header = ','.join(sorted(variables))
            f.write(header + os.linesep)
            for result in results: # TODO: Consider sorting on 'data' attribute (which is our ID variable)
                f.write(','.join([ result[var] for var in sorted(variables) ]) + os.linesep)

        anova(results_independent_variables, results_dependent_variables, csv_path)

def setdftype(df, name, type):
    if name in df:
        df[name] = df[name].astype(type)

def anova(i_vars, d_vars, csv_path):
    # metrics.txt gives all the dependent variables
    # parameters.txt gives all independent categorical variables and their value sets
    # configuration.txt gives a specific combination of the independent variables
    #
    df = pandas.read_csv(csv_path)
    setdftype(df, 'EXECUTION_TIME', int)
    setdftype(df, 'bm'            , str)
    setdftype(df, 'bm_version'    , str)
    setdftype(df, 'bm_workload'   , str)
    setdftype(df, 'heap_size'     , str)
    setdftype(df, 'jdk'           , str)
    setdftype(df, 'jre'           , str)
    setdftype(df, 'source_version', str)
    setdftype(df, 'target_version', str)
    setdftype(df, 'stack_size'    , str)
    #print(df.dtypes)

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
        table_path = csv_path.parent / f"{csv_path.stem}.{d_var}.table"
        with open(table_path, 'w') as f:
            f.write(str(res))
        #print("-"*80)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x-location', required = False, default = 'experiments',
        help = "Location where experiments are stored. Defaults to 'experiments'.")
    parser.add_argument('--x', required = True,
        help = "The experiment name.")
    parser.add_argument('--bm', required = False,
        help = "Benchmark name")
    parser.add_argument('--workload', required = False,
        help = "Benchmark workload")
    parser.add_argument('--compute-results', required = False, action = 'store_true',
        help = "Compute benchmark results by processing views")
    parser.add_argument('--show-progress', required = False, action = 'store_true',
        help = "Print list progress")
    parser.add_argument('--show-deprecated', required = False, action = 'store_true',
        help = "Print deprectated refactorings and benchmarks")
    parser.add_argument('--report', required = False, nargs = '+', choices = ['refactor', 'timeout', 'generic'],
        help = "Print failure report")

    args = parser.parse_args()

    if args.compute_results:
        compute_results(args)
        compute_all(args)

    if args.show_progress:
        compute_progress(args)

    if args.report:
        create_failure_report(args)

    if args.show_deprecated:
        show_deprecated(args)

    if not args.compute_results and not args.show_progress and not args.report and not args.show_deprecated:
        parser.print_help()

