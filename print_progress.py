#!/bin/env python3

import argparse
import os

from experiment import Experiments

type_names = {
    'extract_constant'      : 'Extract constant',
    'extract_method'        : 'Extract method',
    'extract_temp'          : 'Extract temp',
    'inline_constant'       : 'Inline constant',
    'inline_method'         : 'Inline method',
    'inline_temp'           : 'Inline temp',
    'introduce_indirection' : 'Introduce indirection',
    'rename_field'          : 'Rename field',
    'rename_local_variable' : 'Rename variable',
    'rename_method'         : 'Rename method',
    'rename_type'           : 'Rename type',
    'rename_type_parameter' : 'Rename type parameter'
}

def _main(args):
    dataset_name     = args.dataset_name
    output_location  = args.output_location
    progress_objects = Experiments(args.x_location).compute_progress()
    xbw_pos          = dict()
    bms              = set()
    for po in progress_objects:
        _id = po['_id']
        x   = _id['x']
        b   = _id['b']
        w   = _id['w']
        t   = _id['t']
        xbw_pos[(x, b, w, t)] = po
        bms.add(b)

    columns = '&'.join([ x.replace('_', '\\_') for x in [
        #'Benchmark',
        #'Workload',
        'Type',
        'BT', # 'nopps_total',
        'WT',
        'pS', # 'patches_success',
        'pF', # 'patches_failure',
        'bS', # 'bench_success',
        'bFG', # 'bench_failure_generic',
        'bFT' # 'bench_failure_timeout'
    ]])

    rows = dict()
    for (x, b, w, t), po in sorted(xbw_pos.items()):
        values = [str(x).replace('_', '\\_') for x in [
            #b,
            #w,
            type_names[t],
            po['bt_total'],
            po['wt_total'],
            po['patch']['success'],
            po['patch']['failure'],
            po['bench']['success'],
            po['bench']['failure']['generic'],
            po['bench']['failure']['timeout']
        ]]
        if not (b, w) in rows:
            rows[(b, w)] = []
        rows[(b, w)].append(values)

    for (b, w), rows in rows.items():
        w_      = w.replace('_', '\\_')
        caption = "The table shows the number of refactoring opportunities per refactoring type that is available for workload \\textit{@W} (WT), and the number of available opportunities across all \\textit{@B} workloads (BT), in dataset \\textit{@D}. The following numbers are derived from the intersection of BT and WT. pS is the number of opportunities that have been successfully converted into patches. pF is the number of opportunities for which refactoring failed. bS is the number of successfully benchmarked opportunities. bFG is the number of opportunities for which benchmarking failed due to 'generic' errors, including build errors, and bFT is the number of opportunities for which benchmarking failed because of benchmark timeout, 'timeout' errors.".replace('@W', f"{b}/{w_}").replace('@B', b).replace('@D', dataset_name)
        with open(f'{output_location}/{b}_{w}_opportunity_counts.tex', 'w') as f:
            f.write("\\begin{table}[!h]" + os.linesep)
            f.write("\\caption{@CAPTION}".replace('@CAPTION', caption) + os.linesep)
            f.write("\\begin{tabular}{c|*{@N}{r}r}".replace("@N", str(len(rows[0]) - 1)) + os.linesep)
            f.write(columns + "\\\\" + os.linesep)
            f.write("\\hline" + os.linesep)
            f.write(os.linesep.join([ '&'.join(row) + "\\\\" for row in rows ]) + os.linesep)
            f.write("\\end{tabular}" + os.linesep)
            f.write("\\end{table}" + os.linesep)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x-location', required = False, default = 'experiments',
        help = "Location where experiments are stored. Defaults to 'experiments'.")
    parser.add_argument('--output-location', required = False, default = 'tables',
        help = "The folder into which files are written.")
    parser.add_argument('--dataset-name', required = True,
        help = "The name if the data set. Used in the table caption.")
    args = parser.parse_args()
    _main(args)
