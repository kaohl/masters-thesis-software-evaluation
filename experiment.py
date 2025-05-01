import os

from pathlib import Path

from configuration import Configuration

class Data:
    def __init__(self, experiments):
        self._experiments = experiments

class List:
    def __init__(self, workload, name):
        self._workload = workload
        self._name     = name

class Workload:
    def __init__(self, experiment, benchmark, workload):
        self._experiment = experiment
        self._benchmark  = benchmark
        self._workload   = workload

    def xbw(self):
        return (self._experiment._name, self._benchmark, self._workload)

    def location(self):
        return self._experiment.location() / 'workloads' / self._benchmark / self._workload

    def parameters(self):
        return Configuration().load(self.location() / 'parameters.txt')

    def lists(self):
        list_map = dict()
        for dir, lists, files in os.walk(self.location() / 'lists'):
            for lst in lists:
                list_map[lst] = List(self, lst)
            break
        return list_map

class Experiment:
    def __init__(self, experiments, name):
        self._experiments = experiments
        self._name        = name

    def location(self):
        return self._experiments._location / self._name

    def workloads(self):
        workload_map = dict()
        for dir1, benchmarks, files1 in os.walk(self.location() / 'workloads'):
            for b in benchmarks:
                for dir2, workloads, files2 in os.walk(Path(dir1) / b):
                    for w in workloads:
                        workload_map[(self._name, b, w)] = Workload(self, b, w)
                    break
            break
        return workload_map

class WorkloadsAPI:
    def __init__(self, experiments):
        self._experiments = experiments

    def workload_mapping(self, mapping = lambda w: (w.xbw(), w)):
        m = dict()
        for x_name, x in self._experiments.experiments().items():
            for w_name, w in x.workloads().items():
                k, v = mapping(w)
                m[k] = v
        return m

    # { (x, b, w) : Configuration }
    def parameters(self, key = lambda w: w.xbw()):
        return self.workload_mapping(lambda w: (key(w), w.parameters()))

    # { (x, b, w) : { <list name> : List } }
    def lists(self, key = lambda w: w.xbw()):
        return self.workload_mapping(lambda w: (key(w), w.lists()))

    # { (x, b, w) : Path }
    def locations(self, key = lambda w: w.xbw()):
        return self.workload_mapping(lambda w: (key(w), w.location()))

    # { (x, b, w) : [ Configuration ]
    def parameter_combinations(self, key = lambda w: w.xbw()):
        return self.workload_mapping(lambda w: (key(w), w.parameters().get_all_combinations()))

class DataAPI:
    def __init__(self, experiments):
        self._experiments = experiments

class Experiments:

    _special_experiment_folders = set(['data', 'steering'])

    def __init__(self, location):
        self._location = Path(location)
        self._data     = Data(self)

    def experiments(self):
        x_map = dict()
        for dir, experiments, files in os.walk(self._location):
            for x in experiments:
                if x in Experiments._special_experiment_folders:
                    continue
                x_map[x] = Experiment(self, x)
            break
        return x_map

    def workloads(self):
        return WorkloadsAPI(self)

    def data(self):
        return DataAPI(self)

