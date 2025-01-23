#!/bin/env python

import argparse
from pathlib import Path

from configuration import Configuration
import configuration
import evaluation

benchmarks = {
    'batik' : Configuration().bm('batik').version('1.0').source_version('8')
}

def main(args):
    config = benchmarks['batik']

    # BM
    #config.bm('batik')
    #config.version('1.0')
    #config.source_version('8')

    # JDK Options
    config.jdk(['8.0.432-tem'])
    config.target_version('8')

    # JRE Options
    config.jre(['8.0.432-tem'])
    config.jit_enabled('true')
    config.heap_size('512M')

    # BM Options
    config.size('default')

    # TODO: Consider assigning this name based on 'configs/<name>' argument.
    # If we do this, then we only have two top-level arguments: 'config' and 'tag',
    # and possibly 'data-root'.
    # We could also use a temporary directory as experiment folder
    # ('data-root', 'config', 'tag') => ex = <data-root>/<tmp ...>/{workspace,data/<tag>}
    bm  = 'batik'
    ex  = 'experiments/batik'
    tag = 'batik'
    cf  = 'configs/batik-default'
    evaluation.create(bm, Path(ex), Path(cf))
    evaluation.refactor(Path(ex), tag, configuration.get_random_refactoring_configuration(), 0)
    evaluation.benchmark(Path(ex), tag, config)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    #parser.add_argument('--x', required = True,
    #    help = "The experiment name.")
    #parser.add_argument('--x-location', required = False,
    #    help = "Location where experiments are stored. Defaults to 'experiments'.")
    #parser.add_argument('--bm', required = True,
    #    help = "Benchmark name")
    #parser.add_argument('--tag', required = True,
    #    help = "Data tag for use when storing refactorings"
    #parser.add_argument('--create', required = False,
    #    help = "Create experiment workspace from specified template")
    #parser.add_argument('--benchmark', required = False, action = 'store_true',
    #    help = "Benchmark refactoring(s)")
    #parser.add_argument('--data', required = False,
    #    help = "A specific refactoring folder name") 
    #parser.add_argument('--refactor', required = False,
    #    help = "Refactor specified experiment workspace")
    #parser.add_argument('--type', required = False,
    #    help = "Refactoring type")
    args = parser.parse_args()

    main(args)
