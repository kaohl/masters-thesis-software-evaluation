#!/bin/env python3

import argparse
import tempfile

from pathlib import Path

import run_benchmark as bm_script
import tools

from configuration import Configuration

def _test(config, deploy_dir, N, sizes):
    for size in sizes:
        config.stack_size(f"{size}M")
        successful_runs = 0
        for i in range(N):
            try:
                exectime        = bm_script.run_benchmark(config, deploy_dir, False, None)
                successful_runs = successful_runs + 1
                print(f"Benchmark passed, using stack size: {config.stack_size()}")
                if successful_runs != i + 1:
                    return None # Benchmark failed but now succeeded.
            except Exception as e:
                print(f"Benchmark failed, using stack size: {config.stack_size()}")
                print(str(e))
                if successful_runs > 0:
                    return None # Benchmark succeeded but now failed.
        if successful_runs == 0:
            continue # All runs failed. Need larger stack.
        return size if successful_runs == N else None
    raise ValueError("Benchmark failed consistently within specified constraints. Try increasing value ranges.")

def test_determinism(bm, version, workloads, N, sizes):
    config = Configuration()
    config.bm(bm)
    config.bm_version(version)
    config.jdk(tools.sdk_current())
    config.jre(tools.sdk_current())
    with tempfile.TemporaryDirectory(delete = True, dir = 'temp') as location:
        deploy_dir = Path(location)
        bm_script.deploy_benchmark(config, True, deploy_dir)
        for workload in workloads:
            config.bm_workload(workload)
            try:
                size = _test(config, deploy_dir, N, sizes)
                if size is None:
                    print(f"Workload {workload} is non-deterministic")
                else:
                    print(f"Workload {workload} succeeded with stack size: {size}M")
            except Exception as e:
                print(str(e))

def main(args):
    test_determinism(args.bm, '1.0', args.ws, int(args.n), [ int(size) for size in args.stack_sizes ])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bm', required = True,
        help = "Benchmark to test")
    parser.add_argument('--ws', nargs = '+', required = True,
        help = "Benchmark workloads to test")
    parser.add_argument('--n', default = 10, type = int, required = False,
        help = "Number of benchmark runs that must pass to consider a workload to be deterministic")
    parser.add_argument('--stack-sizes', nargs = '+', default = [1, 2, 4, 8, 16, 32], required = False,
        help = "Stack sizes to test")

    main(parser.parse_args())

