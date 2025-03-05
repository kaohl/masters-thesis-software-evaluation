#!/bin/env python3

import argparse
import json
import os
import pandas
from pathlib import Path
from patsy import dmatrices
import statsmodels.api as sm
from statsmodels.formula.api import ols

import configuration
from opportunity_cache import RefactoringDescriptor

def compute_results(args):
    x_location     = Path(args.x_location) / args.x
    bm             = args.bm
    workload       = args.workload
    views_location = Path(x_location) / 'workloads' / bm / workload / 'views'
    views          = []
    if not views_location.exists():
        print("No views to compute", str(views_location))
    for dir, folders, files in os.walk(views_location):
        for file in files:
            with open(Path(dir) / file, 'r') as f:
                views.append((Path(file).stem, json.load(f)))
        break
    variables                     = set() # All.
    results_independent_variables = set() # See 'parameters.txt'.
    results_dependent_variables   = set() # See 'metrics.txt'.
    results_location = Path(x_location) / 'results'
    for name, queries in views:
        results = []
        for lst, filters in queries.items(): # [{ "<list>": [<filter>], ... }]
            data_list_location = Path(x_location) / 'data' / bm / workload / lst
            if not data_list_location.exists():
                raise ValueError("No such list", lst)
            for dir1, folders1, files1 in os.walk(data_list_location):
                for index in folders1:
                    if (Path(dir1) / index / 'FAILURE').exists():
                        continue # Refactoring failed.
                    descriptor = RefactoringDescriptor.load(Path(dir1) / index / 'descriptor.txt')
                    found_match = False
                    for filter in filters:
                        if descriptor.is_match(filter):
                            found_match = True
                            break
                    if not found_match:
                        continue
                    for dir2, folders2, files2 in os.walk(Path(dir1) / index):
                        for execution in folders2:
                            stats_location = Path(dir2) / execution / 'stats'
                            if not stats_location.exists():
                                continue
                            for dir3, folders3, files3 in os.walk(stats_location):
                                for id in folders3:
                                    if (Path(dir3) / id / 'FAILURE').exists():
                                        continue
                                    config  = configuration.Configuration().load(Path(dir3) / id / 'configuration.txt')
                                    metrics = configuration.Metrics().load(Path(dir3) / id / 'metrics.txt')
                                    results.append({ **{ 'data' : lst + '/' + index + '/' + execution }, **config._values, **metrics._values })
                                    if len(variables) == 0:
                                        # All configurations and metrics contain the same variables.
                                        for k, v in config._values.items():
                                            results_independent_variables.add(k)
                                            variables.add(k)
                                        for k, v in metrics._values.items():
                                            results_dependent_variables.add(k)
                                            variables.add(k)
                                break
                        break
                break
        results_location.mkdir(exist_ok = True)
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

def anova(i_vars, d_vars, csv_path):
    # metrics.txt gives all the dependent variables
    # parameters.txt gives all independent categorical variables and their value sets
    # configuration.txt gives a specific combination of the independent variables
    #
    df = pandas.read_csv(csv_path)
    df['EXECUTION_TIME'] = df['EXECUTION_TIME'].astype(int)
    df['bm']             = df['bm'].astype(str)
    df['bm_version']     = df['bm_version'].astype(str)
    df['bm_workload']    = df['bm_workload'].astype(str)
    df['heap_size']      = df['heap_size'].astype(str)
    df['jdk']            = df['jdk'].astype(str)
    df['jre']            = df['jre'].astype(str)
    df['source_version'] = df['source_version'].astype(str)
    if 'stack_size' in df:
        df['stack_size']     = df['stack_size'].astype(str)
    df['target_version'] = df['target_version'].astype(str)    
    #df[''] = df[''].astype(str)
    print(df.dtypes)

    for d_var in d_vars:
        ## https://www.statsmodels.org/stable/gettingstarted.html
        ## https://patsy.readthedocs.io/en/latest/formulas.html
        formula = '{} ~ {}'.format(d_var, ' + '.join(sorted(i_vars)))
        #y, X = dmatrices(formula, data=df, return_type='dataframe')
        #mod = sm.OLS(y, X)
        #res = mod.fit()
        print("-"*80)
        print("Formula", formula)
        print("-"*80)
        #print(res.summary())
        #print(res.params)
        #print(res.rsquared)
        mod = ols(formula, data = df).fit()
        res = sm.stats.anova_lm(mod)
        print(res)
        print("-"*80)

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
    args = parser.parse_args()
    compute_results(args)
