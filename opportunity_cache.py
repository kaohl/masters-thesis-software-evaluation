#!/bin/env python3

import argparse
import json
import os

from pathlib import Path
from random import randrange


# TODO: Move all meta attributes into "__meta__" so that we can easily remove them when loading the descriptor into eclipse.
#       Or we could simply remove the "__meta__" object when serializing the '--descriptor' argument.
# TODO: Write additional meta attributes from refactoring framework
# TODO: The __meta__ object should not be included when computing the ID.
#       If we later want to add meta attributes it should not affect the ID!
#       Only real refactoring descriptor arguments should affect the ID.

# HMM, Should package, classname, and Method be meta attributes in the descriptor?
# This way, we only need a single file for all descriptors and then we can sort
# descriptors as we like. However, it is much easier to unittest if we divide
# descriptors into different files on disk from start.
# But, of course, we could use an inmemory cache and sort descriptors there for
# unittests as well...
# An advantage of makeing all this info meta attributes is that we don't have
# to try to make up path segments from different context parts, we can simply
# write any info we want as descriptor attributes and later filter on their
# values for different experiments or categorization.
# This puts all info in the descriptors.
#
# This way, it would be easy to add methods to the context:
#    "__context"="t.X.f(int).Y.g()"
#
# We could also move all meta into its own object:
#
#    {"id":"...", ..., "__meta__":{"context":"t.X"}}
#
# This also handle __block_id vs. __block_size and allows
# us to collect all __block_id(s) to make a random selection.
#
# We could set __block_id == Block.startOffset()

class RefactoringDescriptor:
    def __init__(self, line):
        self._json = json.loads(line)
        self._meta = self._json.get('__meta__')
        self._line = self._compute_line()

    def _compute_line(self):
        self._line = json.dumps(self._json, sort_keys=True)
        return self._line

    def id(self):
        # ATTENTION
        # The checksum ID produced here is not necessarily EQ with
        # one produced directly from the original cache line, for
        # two reasons:
        #   1) The different encoders have different whitespace policies, and
        #   2) Some descriptors have arguments which may have been applied here.
        #
        # The ID produced here should be used for naming data.
        #
        text = json.dumps(self._json, sort_keys=True)
        return hashlib.md5(bytes(text, encoding = 'utf-8')).hexdigest()

    def line(self):
        return self._line

    def update(self, attributes):
        for name, value in attributes.items():
            self._json[name] = value
        self._compute_line()

    def get_cli_line(self):
        return self._line.replace('"', '\\"').replace("`", "\\`") # ` is part of some some jre internal paths... should probably exclude those opportunities... TODO

class AttributeFilter:
    def __init__(self, name, values):
        self.name   = name
        self.values = set(values)

class Filter:
    def __init__(self, attribute_filters):
        self.attribute_filters = dict([(f.name, f) for f in attribute_filters])

class OppCache:
    def __init__(self, location):
        self._location    = location
        self._files       = []
        self._descriptors = dict()
        for dir, folders, files in os.walk(self._location):
            dp = Path(dir)
            for file in files:
                if file == 'descriptors.txt':
                    self._files.append(dp / file)

    def get_files(self):
        return self._files

    def get_random_descriptor(self):
        file = self._files[randrange(len(self._files))]
        if not file in self._descriptors:
            with open(file, 'r') as f:
                lines = [line for line in f]
                self._descriptors[file] = lines
        line = self._descriptors[file][randrange(len(self._descriptors[file]))]
        return RefactoringDescriptor(line)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', required = True,
        help = "Path to cache location.")
    args = parser.parse_args()

    desc = OppCache(args.cache).get_random_descriptor()
    # desc.update({'name' : 'HELLO'}) # TODO: Name generation.
    print(desc.line())
    print(desc.get_cli_line())

