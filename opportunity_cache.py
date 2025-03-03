#!/bin/env python3

import argparse
import io
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

    def load(path):
        with open(path, 'r') as f:
            return RefactoringDescriptor(json.dumps(json.load(f), sort_keys = True))

    def __init__(self, line):
        self._json = json.loads(line)
        self._args = self._json.get('args')
        self._meta = self._json.get('meta')
        self._line = self._compute_line()

    def _compute_line(self):
        self._line = json.dumps(self._json, sort_keys=True)
        return self._line

    def refactoring_id(self):
        return self._meta['id']

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

    def get_cli_line(self):
        # ` is part of some some jre internal paths... should probably exclude those opportunities... TODO
        return self._line.replace('"', '\\"').replace("`", "\\`")

    def get_arg(self, name):
        return self._args.get(name)

    def set_arg(self, name, value):
        self._args[name] = value

    def update_args(self, attributes):
        for name, value in attributes.items():
            self._args[name] = value
        self._compute_line()

    def update_meta(self, attributes):
        for name, value in attributes.items():
            self._meta[name] = value
        self._compute_line()

    # Match meta attributes against specified attribute filters.
    def is_match(self, filters):
        for k, v in filters.items():
            if not (k in self._meta and self._meta[k] == v):
                return False
        return True

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

    # This was originally for testing purposes but could be of practical use, maybe.
    def get_random_descriptor(self):
        file = self._files[randrange(len(self._files))]
        if not file in self._descriptors:
            with open(file, 'r') as f:
                lines = [line for line in f]
                self._descriptors[file] = lines
        line = self._descriptors[file][randrange(len(self._descriptors[file]))]
        return RefactoringDescriptor(line)

    # This method assumes all matching descriptors can be loaded into memory.
    # Use the 'stream()' variant to write directly to file.
    def filter(self, filters):
        descriptors = []
        for file in sorted(self._files):
            with open(file, 'r') as f:
                for line in f:
                    desc = RefactoringDescriptor(line)
                    if desc.is_match(filters):
                        descriptors.append(desc)
        return descriptors

    def stream(self, filter, accept_fn):
        for file in sorted(self._files):
            with open(file, 'r') as f:
                for line in f:
                    desc = RefactoringDescriptor(line)
                    if desc.is_match(filter):
                        accept_fn(desc)

# TODO/NOTE
# We could generalize the filter functionality to include arbitrary comparisons.
# However, lets keep it simple and only expand what we need, and at the moment
# we only need equality testing:
#   { "$eq": { 'attr' : '<name>', 'value' : '<value>' } }
# which is just as well represented by:
#   { '<name>' : '<value>' }
#
# And we should not need $and or $or. (All eq tests are ANDed for now.)
#
# Regex matching against 'input' and 'element' arguments may be useful
# to target opportunities in a specific class or method.

class Query:

    def _load_filter(path):
        if not path.exists():
            raise ValueError("Bad filter path")
        with open(path, 'r') as f:
            return json.load(f) # This is a single object for now.

    def _load_params(path):
        # If the path does not exists, the user implies that matching
        # descriptors should be complete and ready for application.
        # The user have to add an explicit empty argument object to
        # activate this behavior if the path exists.
        if not path.exists():
            return [dict()]
        params = []
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line == "":
                    continue
                params.append(json.loads(line))
        return params

    def _load_defaults(path):
        if not path.exists():
            return dict() # Optional; default to empty.
        with open(path, 'r') as f:
            return json.load(f)

    def __init__(self, cache, filter, params, local_defaults, global_defaults):
        self._cache           = cache
        self._filter          = Query._load_filter(Path(filter))
        self._params          = Query._load_params(Path(params))
        self._local_defaults  = Query._load_defaults(Path(local_defaults))
        self._global_defaults = global_defaults      # Assume that the caller has already loaded this one and is providing the result.

    def _apply_defaults(self, descriptor):
        id = descriptor.refactoring_id()
        if id in self._global_defaults:
            descriptor.update_args(self._global_defaults[id])
        else:
            # Note: Types without arguments should be listed with an empty object.
            raise ValueError("No default arguments registered for type", id)

        # Override global defaults if specified for this particular query.
        if id in self._local_defaults:
            descriptor.update_args(self._local_defaults[id])

    def _produce(self, descriptor, stream):
        self._apply_defaults(descriptor)
        for params in self._params:
            copy = RefactoringDescriptor(descriptor.line())
            copy.update_args(params)
            stream.write(copy.line() + os.linesep)

    def run(self, stream):
        self._cache.stream(self._filter, lambda desc: self._produce(desc, stream))

class ListsGenerator:

    def _load_json(path):
        with open(path, 'r') as f:
            return json.load(f)

    def generate_lists(cache_location, lists_location):
        cache        = OppCache(cache_location)
        default_args = ListsGenerator._load_json(Path(lists_location) / 'default.args')
        for dir, folders, files in os.walk(lists_location):
            for folder in folders:
                ListsGenerator._generate_list(cache, default_args, Path(dir) / folder)
            break

    def _generate_list(cache, default_args, list):
        with open(list / 'descriptors.txt', 'w') as descriptors:
            for dir, folders, files in os.walk(list):
                dp = Path(dir)
                for file in files:
                    fp = Path(file)
                    if file.endswith('.filter'):
                        filter             = dp / file
                        params             = dp / (fp.stem + '.params')
                        local_default_args = dp / (fp.stem + '.defaults')
                        Query(cache, filter, params, local_default_args, default_args).run(descriptors)
                break

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', required = True,
        help = "Path to cache location.")
    parser.add_argument('--filter', required = True,
        help = "JSON object meta attribute filter")

    # TODO: Consider adding an argument filter as well.

    args   = parser.parse_args()
    filter = json.loads(args.filter)

    #for desc in OppCache(args.cache).filter(filter):
    #    print(desc.line())

    OppCache(args.cache).stream(filter, lambda desc: print(desc.line()))

    #desc = OppCache(args.cache).get_random_descriptor()
    #print(desc.line())
    #print(desc.get_cli_line())

