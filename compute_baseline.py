#!/bin/env python3

import argparse
import json
import numpy as np
import os
import tempfile

from pathlib    import Path
from subprocess import TimeoutExpired

import run_benchmark as bm_script

from configuration import Configuration

def benchmark(configuration, n = 10):
    try:
        bm = configuration.bm()
        wl = configuration.bm_workload()
        with tempfile.TemporaryDirectory(delete = True, dir = 'temp') as location:
            deploy_dir = Path(location)
            bm_script.deploy_benchmark(configuration, True, deploy_dir, None)
            xs = []
            for i in range(n):
                x = bm_script.run_benchmark(configuration, deploy_dir, False, None)
                xs.append(int(x))
            return np.mean(xs), np.std(xs, ddof=1)
    except TimeoutExpired as e:
        print(f"Benchmark timed out: {bm} {wl}")
    except Exception as e:
        print("Exception:", str(e))
    return None

def compute_baseline(args):
    baseline       = dict()
    configurations = dict() # { <bm> : [ <configuration> ] }
    for dir1, xs, files1 in os.walk(args.x_location):
        for x in xs:
            if x == 'steering' or x == 'data':
                continue
            for dir2, bs, files2 in os.walk(Path(dir1) / x / 'workloads'):
                for b in bs:
                    for dir3, ws, files3 in os.walk(Path(dir2) / b):
                        for w in ws:
                            configurations[(x, b, w)] = Configuration().load(Path(dir3) / w / 'parameters.txt').get_all_combinations()
                        break
                break
        break
    for (x, b, w), combinations in configurations.items():
        for configuration in combinations:
            bm  = configuration.bm()
            wl  = configuration.bm_workload()
            id  = configuration.id()
            key = '-'.join([bm, wl, id])
            if not key in baseline:
                mean, std = benchmark(configuration)
                baseline[key          ] = int(mean)
                baseline[key + '-mean'] = mean      # In case we need the precision... not likely.
                baseline[key + '-std' ] = std
                with open('baseline.txt', 'w') as f:
                    f.write(json.dumps(baseline, sort_keys = True))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x-location', required = False, default = "experiments", help = "Experiment location")
    args = parser.parse_args()
    compute_baseline(args)

