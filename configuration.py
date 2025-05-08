import io
import os
import re
import hashlib
import sys

from functools import reduce
from random    import randrange

import tools

class ConfigurationBase:
    def __init__(self, configuration_type):
        self._values             = dict()
        self._options            = dict()
        self._configuration_type = configuration_type

    def id(self):
        with io.StringIO() as text:
            for k, v in sorted(self._values.items(), key = lambda it: it[0]):
                text.write('='.join([str(k), str(v)]) + os.linesep)
            return hashlib.md5(bytes(text.getvalue(), encoding = 'utf-8')).hexdigest()

    def is_valid_key(self, key):
        raise ValueError("Unimplemented")

    def to_dict(self):
        return dict({ (k, v) for k, v in self._values.items() })

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
        parameters = [ (key, options) for key, options in sorted(self._options.items(), key = lambda it: it[0]) ]
        return [ self._configuration_type().init_from_dict(dict(value_list)) for value_list in self._all_rec(parameters) ]

    def _clobber(self, key, value = None):
        if not value is None:
            options = None
            if isinstance(value, list):
                options = value
                value   = value[0]
            #elif isinstance(value, set):
            #    options = [ v for v in value ]
            #    value   = options[0]
            else:
                options = [value]
            self._options[key] = options
            self._values[key]  = value
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
            largest_n, _ = reduce(lambda a, b: a if a[0] > b[0] else b, [ (len(x), x) for x in self._values.keys() ], (0, ''))
            for key, value in sorted(self._values.items(), key = lambda it: it[0]):
                f.write((' '*(largest_n - len(key)) + ' = ').join([key, value]) + os.linesep)

    def store_options(self, file):
        with open(file, 'w') as f:
            largest_n, _ = reduce(lambda a, b: a if a[0] > b[0] else b, [ (len(x), x) for x in self._options.keys() ], (0, ''))
            for key, options in sorted(self._options.items(), key = lambda it: it[0]):
                f.write((' '*(largest_n - len(key)) + ' = ').join([key, ', '.join(options)]) + os.linesep)

    def key_value_string(self):
        return ';'.join([ f"{key}={value}" for key, value in sorted(self._values.items(), key = lambda it: it[0]) ])

# Experimental build and runtime parameters.
#
# NOTE
# It appears newer JDKs phase out target compatibility with
# older versions so the set of allowed target versions
# depends both on the source version and on the JDK.
# No validation is currently performed for these implementation
# specific constraints so please consult the JDK documentation
# to find what works.
#
class Configuration(ConfigurationBase):
    BM             = 'bm'
    BM_VERSION     = 'bm_version'     # The benchmark version. Not the version of the benchmarked library.
    BM_WORKLOAD    = 'bm_workload'
    SOURCE_VERSION = 'source_version' # Used to constrain target_version.
    TARGET_VERSION = 'target_version' # Any version compatible with source_version and JDK.
    JDK            = 'jdk'
    JRE            = 'jre'
    HEAP_SIZE      = 'heap_size'
    STACK_SIZE     = 'stack_size'

    # These attributes should be considered when computing
    # a unique ID for the experimental configuration. This
    # is used to name configuration folders in 'stats'
    # folders when storing benchmark results to avoid
    # duplicating executions for shared refactorings
    # between workloads and experiments.
    _experimental_parameters = set({
        SOURCE_VERSION,
        TARGET_VERSION,
        JDK,
        JRE,
        HEAP_SIZE,
        STACK_SIZE
    })

    size_option_pattern = re.compile("(\\d+)([KkMmGg])")

    # TODO: Configuration constraints should be loaded from file.

    _constraints = {
        'batik:1.0' : {
            'bm'             : { 'batik' },                     # Values
            'bm_version'     : { '1.0' },                       # Values
            'bm_workload'    : { 'small', 'default', 'large' }, # Values
            'source_version' : { '8' },                         # Values
            'jre'            : set(tools.get_installed_sdks()), # Values
            'jdk'            : set(tools.get_installed_sdks())  # Values
        },
        'jacop:1.0' : {
            'bm'             : { 'jacop' },                     # Values
            'bm_version'     : { '1.0' },                       # Values
            'bm_workload'    : { 'mzc18_1','mzc18_2','mzc18_3','mzc18_4','mzc18_5','mzc18_6' }, # Values
            'source_version' : { '8' },                         # Values
            'jre'            : set(tools.get_installed_sdks()), # Values
            'jdk'            : set(tools.get_installed_sdks())  # Values
        },
        'xalan:1.0' : {
            'bm'             : { 'xalan' },                     # Values
            'bm_version'     : { '1.0' },                       # Values
            'bm_workload'    : { 'small', 'default', 'large' }, # Values
            'source_version' : { '8' },                         # Values
            'jre'            : set(tools.get_installed_sdks()), # Values
            'jdk'            : set(tools.get_installed_sdks())  # Values
        },
        'lusearch:1.0' : {
            'bm'             : { 'lusearch' },                  # Values
            'bm_version'     : { '1.0' },                       # Values
            'bm_workload'    : { 'small', 'default', 'large' }, # Values
            'source_version' : { '11' },                        # Values
            'jre'            : set(tools.get_installed_sdks()), # Values
            'jdk'            : set(tools.get_installed_sdks())  # Values
        },
        'luindex:1.0' : {
            'bm'             : { 'luindex' },                   # Values
            'bm_version'     : { '1.0' },                       # Values
            'bm_workload'    : { 'small', 'default', 'large' }, # Values
            'source_version' : { '11' },                        # Values
            'jre'            : set(tools.get_installed_sdks()), # Values
            'jdk'            : set(tools.get_installed_sdks())  # Values
        }
    }

    _compare_units = {
        ('K', 'M') : -1,
        ('K', 'G') : -2,
        ('M', 'K') :  1,
        ('M', 'G') : -1,
        ('G', 'K') :  2,
        ('G', 'M') :  1
    }
    def compare_size_units(x, y):
        if x == y:
            return 0
        else:
            return Configuration._compare_units[(x.upper(), y.upper())]

    def test_size_option(opt, val, test):
        opt_a, opt_u = Configuration.size_option_pattern.findall(opt)[0]
        val_a, val_u = Configuration.size_option_pattern.findall(val)[0]
        opt_a        = int(opt_a)
        val_a        = int(val_a)
        c            = Configuration.compare_size_units(val_u, opt_u)
        # Change to the smaller unit unless units are equal.
        if c < 0:
            while c < 0:
                opt_a = opt_a * 1024
                c     = c + 1
        elif c > 0:
            while c > 0:
                val_a = val_a * 1024
                c     = c - 1
        # Compare constants now that units are equal.
        return test(val_a, opt_a)

    def test_size_ge(opt, val):
        return Configuration.test_size_option(opt, val, Configuration.test_int_ge)

    def test_int_ge(x, y):
        return int(x) >= int(y)

    def test_int_eq(x, y):
        return int(x) == int(y)

    def get_option_constraints(self, key):
        bm         = self.bm()
        bm_version = self.bm_version()
        return Configuration._constraints[':'.join([self.bm(), self.bm_version()])].get(key)

    def has_option_constraints(self, key):
        return Configuration._constraints[':'.join([self.bm(), self.bm_version()])].get(key) != None

    def is_valid_key(self, key):
        return key in {
            Configuration.BM,
            Configuration.BM_VERSION,
            Configuration.BM_WORKLOAD,
            Configuration.SOURCE_VERSION,
            Configuration.TARGET_VERSION,
            Configuration.JDK,
            Configuration.JRE,
            Configuration.HEAP_SIZE,
            Configuration.STACK_SIZE
        }

    def _raise_errors(self):
        is_valid_option           = lambda k: not self.has_option_constraints(k) or self._clobber(k) in self.get_option_constraints(k)
        is_valid_option_test      = lambda k, test: not self.has_option_constraints(k) or len({ x for x in self.get_option_constraints(k) if test(x, self._clobber(k)) }) > 0
        is_valid_size_option_test = lambda k, test: not self.has_option_constraints(k) or len({ x for x in self.get_option_constraints(k) if test(x, self._clobber(k)) }) > 0
        bad_option_message        = "Option '{}'=\"{}\" does not satisfy constraint: {}"
        errors                    = []
        if not is_valid_option(Configuration.BM):
            errors.append(bad_option_message.format(
                Configuration.BM,
                self.bm(),
                self.get_option_constraints(Configuration.BM)
            ))
        if not is_valid_option(Configuration.BM_VERSION):
            errors.append(bad_option_message.format(
                Configuration.BM_VERSION,
                self.bm_version(),
                self.get_option_constraints(Configuration.BM_VERSION)
            ))
        if not is_valid_option(Configuration.BM_WORKLOAD):
            errors.append(bad_option_message.format(
                Configuration.BM_WORKLOAD,
                self.bm_workload(),
                self.get_option_constraints(Configuration.BM_WORKLOAD)
            ))
        if not is_valid_option_test(Configuration.SOURCE_VERSION, Configuration.test_int_eq):
            errors.append(bad_option_message.format(
                Configuration.SOURCE_VERSION,
                self.source_version(),
                self.get_option_constraints(Configuration.SOURCE_VERSION)
            ))
        if not is_valid_size_option_test(Configuration.HEAP_SIZE, Configuration.test_size_ge):
            errors.append(bad_option_message.format(
                Configuration.HEAP_SIZE,
                self.heap_size(),
                self.get_option_constraints(Configuration.HEAP_SIZE)
            ))
        if not is_valid_size_option_test(Configuration.STACK_SIZE, Configuration.test_size_ge):
            errors.append(bad_option_message.format(
                Configuration.STACK_SIZE,
                self.stack_size(),
                self.get_option_constraints(Configuration.STACK_SIZE)
            ))
        if not is_valid_option(Configuration.JRE):
            errors.append(bad_option_message.format(
                Configuration.JRE,
                self.jre(),
                self.get_option_constraints(Configuration.JRE)
            ))
        if not is_valid_option(Configuration.JDK):
            errors.append(bad_option_message.format(
                Configuration.JDK,
                self.jdk(),
                self.get_option_constraints(Configuration.JDK)
            ))
        if len(errors) > 0:
            raise ValueError("Bad configuration", errors)

    def _check_constraints(self):
        source_version    = int(self.source_version())
        target_version    = int(self.target_version())
        jre_major_version = int(self.jre()[:self.jre().find('.')])
        jdk_major_version = int(self.jdk()[:self.jdk().find('.')])

        if target_version < source_version:
            return False

        if jre_major_version < target_version:
            return False

        if jdk_major_version < source_version:
            return False

        if jdk_major_version < target_version:
            return False

        return True

    def is_valid(self):
        self._raise_errors()
        return self._check_constraints()

    def params_id(self):
        # Note: We need to have the params_id() depend on workload.
        #       The following is incorrect. We should return 'self.id()'.
        #with io.StringIO() as text:
        #    for k, v in sorted(self._values.items(), key = lambda it: it[0]):
        #        if k in Configuration._experimental_parameters:
        #            text.write('='.join([str(k), str(v)]) + os.linesep)
        #    return hashlib.md5(bytes(text.getvalue(), encoding = 'utf-8')).hexdigest()
        return self.id()

    def parameters(self):
        return dict({ (k, v) for k, v in self._values.items() if k in Configuration._experimental_parameters })

    def __init__(self):
        super().__init__(Configuration)

    def bm(self, value = None):
        return self._clobber(Configuration.BM, value)

    def bm_version(self, value = None):
        return self._clobber(Configuration.BM_VERSION, value)

    def bm_workload(self, value = None):
        return self._clobber(Configuration.BM_WORKLOAD, value)

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

    def stack_size(self, value = None):
        return self._clobber(Configuration.STACK_SIZE, value)

class Metrics(ConfigurationBase):
    EXECUTION_TIME = 'EXECUTION_TIME'

    def is_valid_key(self, key):
        return key in { Metrics.EXECUTION_TIME }

    def __init__(self):
        super().__init__(Metrics)

    def execution_time(self, value = None):
        return self._clobber(Metrics.EXECUTION_TIME, value)

class RefactoringConfiguration(ConfigurationBase):
    def __init__(self):
        super().__init__(RefactoringConfiguration)

    def is_valid_key(self, key):
        return True # We don't have dedicated classes for all different types so accept all for now.

#class RefactoringConfiguration(ConfigurationBase):
#    LIMIT   = '--limit'
#    TYPE    = '--type'
#    SEED    = '--seed'
#    SHUFFLE = '--shuffle'
#    SELECT  = '--select'
#
#    def __init__(self, type):
#        super().__init__()
#        defaults = {
#            RefactoringConfiguration.LIMIT   : '1000', # Number of opportunities to try before failing.
#            RefactoringConfiguration.TYPE    : type,
#            RefactoringConfiguration.SEED    : '0',
#            RefactoringConfiguration.SHUFFLE : '0',
#            RefactoringConfiguration.SELECT  : '0'
#        }
#        self._values = { **self._values, **defaults }
#
#    def limit(self, value = None):
#        return self._clobber(RefactoringConfiguration.LIMIT, value)
#
#    def type(self, value = None):
#        return self._clobber(RefactoringConfiguration.TYPE, value)
#
#    def seed(self, value = None):
#        return self._clobber(RefactoringConfiguration.SEED, value)
#
#    def shuffle(self, value = None):
#        return self._clobber(RefactoringConfiguration.SHUFFLE, value)
#
#    def select(self, value = None):
#        return self._clobber(RefactoringConfiguration.SELECT, value)
#
#class Rename(RefactoringConfiguration):
#    LENGTH = '--length'
#
#    def __init__(self, length = 0):
#        super().__init__('rename')
#        defaults = {
#            Rename.LENGTH : str(length)
#        }
#        self._values = { **self._values, **defaults }
#
#    def length(self, value = None):
#        return self._clobber(Rename.LENGTH, value)
#
#class InlineMethod(RefactoringConfiguration):
#    def __init__(self):
#        super().__init__('inline-method')
#
#class ExtractMethod(RefactoringConfiguration):
#    def __init__(self):
#        super().__init__('extract-method')
#
#class InlineConstant(RefactoringConfiguration):
#    def __init__(self):
#        super().__init__('inline-constant')
#
#class ExtractConstant(RefactoringConfiguration):
#    def __init__(self):
#        super().__init__('extract-constant')
#
#def get_random_refactoring_configuration():
#    configs = [
#        Rename,
#        InlineMethod,
#        ExtractMethod,
#        InlineConstant,
#        ExtractConstant
#    ]
#    config = configs[randrange(len(configs))]()
#    config.seed   (randrange(sys.maxsize))
#    config.shuffle(randrange(sys.maxsize))
#    config.select (randrange(sys.maxsize))
#
#    if isinstance(config, Rename):
#        config.length(str(randrange(100))) # Arbitrary range.
#
#    return config
    
