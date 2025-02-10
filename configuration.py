import io
import os
import hashlib
from random import randrange
import sys

# TODO: Build compatibility matrix for benchmarks so that we don't
#       waste time running configurations that always crash because
#       of some incompatibility in parameters.

# - Benchmark parameters (name, version, source_version) # Identification.
# - Build     parameters (jdk, target_version)           #
# - Runtime   parameters (jre, heap_size)                #

#parameters = ['bm', 'version', 'source_version', 'target_version', 'jdk', 'jre', 'heap_size']
    
# Build options
#jdk       = ['8.0.432-tem', '11.0.25-tem', '17.0.13-tem']
#target    = ['8', '11', '17']

# Benchmark options
#jre       = ['8.0.432-tem', '11.0.25-tem', '17.0.13-tem']
#heap_size = ['64M', '128M', '256M', '512M', '1G', '2G', '4G', '8G']

class ConfigurationBase:
    def __init__(self):
        self._values  = dict()
        self._options = dict()

    def id(self):
        with io.StringIO() as text:
            for k, v in sorted(self._values.items(), key = lambda it: it[0]):
                text.write('='.join([str(k), str(v)]) + os.linesep)
            return hashlib.md5(bytes(text.getvalue(), encoding = 'utf-8')).hexdigest()

    def is_valid_key(self, key):
        raise ValueError("Unimplemented")

    def init_from_dict(self, parameters):
        for key, options in parameters.items():
            if not self.is_valid_key(key):
                raise ValueError("Invalid configuration key", key)
            self._clobber(key, options)
        return self

    def _all_rec(self, parameters, level = 0):
        if level >= len(parameters):
            return [[]]
        value_lists      = self._all_rec(parameters, level + 1)
        next_value_lists = []
        key, options     = parameters[level]
        for option in options:
            for value_list in value_lists:
                tmp = value_list + [(key, option)]
                next_value_lists.append(tmp)
        return next_value_lists

    def get_all_combinations(self):
        parameters = [ (key, options) for key, options in self._options.items() ]
        return [ Configuration().init_from_dict(dict(value_list)) for value_list in self._all_rec(parameters) ]

    def _clobber(self, key, value):
        if not value is None:
            if isinstance(value, list):
                self._options[key] = value
                value = value[0]
            self._values[key] = value
            return self
        return self._values.get(key)

    # Create a new configuration with a random selection
    # of values for attributes with specified options.
    # Attributes without options are copied without change.
    def random(self):
        # Select random values for attributes with specified options.
        random_selection = dict([
            (k, opts[randrange(len(opts))]) for k, opts in self._options.items()
        ])
        config          = type(self)()
        config._values  = { **self.values, **random_selection }
        config._options = { **self._options }
        return config

    def load(self, file):
        params = dict()
        with open(file, 'r') as f:
            for line in f:
                line   = line.strip()
                if line == '':
                    continue
                parts  = line.split('=')
                name   = parts[0].strip()
                values = [ x.strip() for x in parts[1].split(',') ]
                params[name] = values
        return self.init_from_dict(params)

    def store(self, file):
        with open(file, 'w') as f:
            for key, value in sorted(self._values.items(), key = lambda it: it[0]):
                f.write('='.join([key, value]) + os.linesep)

class Configuration(ConfigurationBase):
    BM             = 'bm'
    SIZE           = 'size'
    VERSION        = 'version'
    SOURCE_VERSION = 'source_version'
    TARGET_VERSION = 'target_version'
    JDK            = 'jdk'
    JRE            = 'jre'
    HEAP_SIZE      = 'heap_size'
    JIT_ENABLED    = 'jit_enabled'

    def is_valid_key(self, key):
        return key in {
            Configuration.BM,
            Configuration.SIZE,
            Configuration.VERSION,
            Configuration.SOURCE_VERSION,
            Configuration.TARGET_VERSION,
            Configuration.JDK,
            Configuration.JRE,
            Configuration.HEAP_SIZE,
            Configuration.JIT_ENABLED
        }

    def __init__(self):
        super().__init__()

    def bm(self, value = None):
        return self._clobber(Configuration.BM, value)

    # Payload size.
    def size(self, value = None):
        return self._clobber(Configuration.SIZE, value)

    def version(self, value = None):
        return self._clobber(Configuration.VERSION, value)

    def source_version(self, value = None):
        return self._clobber(Configuration.SOURCE_VERSION, value)

    def target_version(self, value = None):
        return self._clobber(Configuration.TARGET_VERSION, value)

    def jdk(self, value = None):
        return self._clobber(Configuration.JDK, value)

    def jre(self, value = None):
        return self._clobber(Configuration.JRE, value)

    def heap_size(self, value = None):
        return self._clobber(Configuration.HEAP_SIZE, value)

    def jit_enabled(self, value = None):
        return self._clobber(Configuration.JIT_ENABLED, value)

class Metrics(ConfigurationBase):
    EXECUTION_TIME = 'EXECUTION_TIME'

    def is_valid_key(self, key):
        return key in { Metrics.EXECUTION_TIME }

    def __init__(self):
        super().__init__()

    def execution_time(self, value = None):
        return self._clobber(Metrics.EXECUTION_TIME, value)

class RefactoringConfiguration(ConfigurationBase):
    LIMIT   = '--limit'
    TYPE    = '--type'
    SEED    = '--seed'
    SHUFFLE = '--shuffle'
    SELECT  = '--select'

    def __init__(self, type):
        super().__init__()
        defaults = {
            RefactoringConfiguration.LIMIT   : '1000', # Number of opportunities to try before failing.
            RefactoringConfiguration.TYPE    : type,
            RefactoringConfiguration.SEED    : '0',
            RefactoringConfiguration.SHUFFLE : '0',
            RefactoringConfiguration.SELECT  : '0'
        }
        self._values = { **self._values, **defaults }

    def limit(self, value = None):
        return self._clobber(RefactoringConfiguration.LIMIT, value)

    def type(self, value = None):
        return self._clobber(RefactoringConfiguration.TYPE, value)

    def seed(self, value = None):
        return self._clobber(RefactoringConfiguration.SEED, value)

    def shuffle(self, value = None):
        return self._clobber(RefactoringConfiguration.SHUFFLE, value)

    def select(self, value = None):
        return self._clobber(RefactoringConfiguration.SELECT, value)

class Rename(RefactoringConfiguration):
    LENGTH = '--length'

    def __init__(self, length = 0):
        super().__init__('rename')
        defaults = {
            Rename.LENGTH : str(length)
        }
        self._values = { **self._values, **defaults }

    def length(self, value = None):
        return self._clobber(Rename.LENGTH, value)

class InlineMethod(RefactoringConfiguration):
    def __init__(self):
        super().__init__('inline-method')

class ExtractMethod(RefactoringConfiguration):
    def __init__(self):
        super().__init__('extract-method')

class InlineConstant(RefactoringConfiguration):
    def __init__(self):
        super().__init__('inline-constant')

class ExtractConstant(RefactoringConfiguration):
    def __init__(self):
        super().__init__('extract-constant')

def get_random_refactoring_configuration():
    configs = [
        Rename,
        InlineMethod,
        ExtractMethod,
        InlineConstant,
        ExtractConstant
    ]
    config = configs[randrange(len(configs))]()
    config.seed   (randrange(sys.maxsize))
    config.shuffle(randrange(sys.maxsize))
    config.select (randrange(sys.maxsize))

    if isinstance(config, Rename):
        config.length(str(randrange(100))) # Arbitrary range.

    return config
    
