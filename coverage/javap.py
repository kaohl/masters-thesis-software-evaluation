#!/bin/env python

import argparse
import os
from pathlib import Path
import re
import subprocess

class JavaP:

    def __init__(self, class_tree_root):
        self._location = class_tree_root
        self._cache    = dict() # {class name => {lino => method name}}

    def _load_line_number_to_method_mapping(self, qualified_class):
        cmd = ' '.join([
            'javap -l -p',
            qualified_class.replace('.', '/')
        ])
        result = subprocess.run(
            cmd,
            shell = True,
            cwd = self._location,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT
        )
        from_pattern   = re.compile('^Compiled from \\"(\\w+\\.java)\\"')
        #class_pattern  = re.compile('class ([\\w.]+) {')
        method_pattern = re.compile('(\\w+\\([^\\)]+\\));')
        line_pattern   = re.compile('line (\\d+):')

        filename = None
        clazz    = qualified_class
        method   = None

        self._cache[clazz] = dict()

        for i, line in enumerate(result.stdout.decode('utf-8').split(os.linesep)):
            if i == 0:
                filename = from_pattern.match(line).groups()[0]
            #elif i == 1:
            #    clazz = class_pattern.findall(line)[0]
            else:
                method_match = method_pattern.findall(line)
                if len(method_match) > 0:
                    if len(method_match) > 1:
                        raise ValueError("Unexpected number of method signature matches.") 
                    method = '.'.join([clazz, method_match[0]])

                line_match = line_pattern.findall(line)
                if len(line_match) == 1:
                    if len(line_match) > 1:
                        raise ValueError('Unexpected number of line number matches')
                    lino                     = int(line_match[0])
                    #print("Associate line", str(lino), "with method", method)
                    self._cache[clazz][lino] = method

    def get_method_by_line_number(self, qualified_class, lino):
        if not qualified_class in self._cache:
            self._load_line_number_to_method_mapping(qualified_class)
        return self._cache[qualified_class][lino]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--qclass', required = True,
        help = "Qualified class name to load.")
    parser.add_argument('-l', '--lino', required = True, type = int,
        help = "The line number for which we want to determine the associated method.")
    parser.add_argument('-t', '--tree', required = True,
        help = "Path to top-level folder of binary tree.")
    args = parser.parse_args()

    print(JavaP(Path(args.tree)).get_method_by_line_number(args.qclass, args.lino))

    # Example: ./javap.py -t ../../alfine-repos/daivy/projects/batik-1.16/build/dist -c org.apache.batik.anim.AbstractAnimation -l 117

