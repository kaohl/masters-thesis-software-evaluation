#!/bin/env python3

import os
import shutil
import subprocess

from pathlib import Path

import configuration

# Migrate data folders from the full unique ID
# to the parameter based ID to be able to share
# data folders between workloads and experiments.

def main():
    result = subprocess.run(
        "find experiments/data -iname stats",
        shell = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT
    )
    paths = result.stdout.decode('utf-8').strip().split(os.linesep)

    for stats_path in paths:
        for dir, ids, files in os.walk(stats_path):
            for id in ids:
                config   = configuration.Configuration().load(Path(dir) / id / 'configuration.txt')
                old_path = Path(dir) / id
                new_path = Path(dir) / config.params_id()
                if new_path.exists():
                    if old_path != new_path:
                        print(f"Remove duplicate measurement: {old_path}")
                        shutil.rmtree(old_path)
                    continue
                print(f"Move {old_path}{os.linesep}  to {new_path}")
                shutil.move(old_path, new_path)
            break

if __name__ == '__main__':
    main()

