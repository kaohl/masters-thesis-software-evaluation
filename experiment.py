import json
import os

from pathlib import Path

from configuration     import Configuration
from opportunity_cache import RefactoringDescriptor

class List:
    def __init__(self, workload, name):
        self._workload = workload
        self._name     = name

    def location(self):
        return self._workload.location() / 'lists' / self._name

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

class Data:
    def __init__(self, experiments):
        self._experiments = experiments

    def location(self):
        return self._experiments.location() / 'data'

    def descriptor_location(self, bm, descriptor):
        opp_id = descriptor.opportunity_id()
        des_id = descriptor.id()
        return self.location() / bm / opp_id / des_id

class Experiments:

    _special_experiment_folders = set(['data', 'steering'])

    def __init__(self, location):
        self._location = Path(location)
        self._data     = Data(self)

    def location(self):
        return self._location

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
        return self._data

    def compute_progress(self):
        return ComputeProgress(self).compute_progress()

class ComputeProgress:
    def __init__(self, experiments):
        self._experiments = experiments

    def compute_progress(self):
        p = self._experiments.location() / 'progress.json'
        if not p.exists():
            progress_objects = self._compute_progress_json()
            with open(p, 'w') as f:
                for po in progress_objects:
                    f.write(json.dumps(po) + os.linesep)
            return progress_objects
        progress_objects = []
        with open(p, 'r') as f:
            for line in f:
                progress_objects.append(json.loads(line))
        return progress_objects

    def _compute_progress_json(self):
        results    = []
        parameters = self._experiments.workloads().parameters()
        bt_totals  = dict() # { <b> : { <opp> } }
        for (x, b, w), lists in self._experiments.workloads().lists().items():
            xbw_parameters     = parameters[(x, b, w)]
            xbw_parameters_ids = set([ p.id() for p in xbw_parameters.get_all_combinations() ])
            for lst_name, lst in lists.items():
                print(x, b, w, lst_name)
                list_descriptors = lst.location() / 'descriptors.txt'
                if not list_descriptors.exists():
                    continue
                opportunities_total                 = set()
                opportunities_patch_success         = set() # Note that patch success and failure could potentially overlap.
                opportunities_patch_failure         = set()
                opportunities_bench_success         = set() # I believe bench success and failure can NOT overlap.
                opportunities_bench_failure_generic = set()
                opportunities_bench_failure_timeout = set()
                with open(list_descriptors, 'r') as f:
                    for line in f:
                        descriptor    = RefactoringDescriptor(line)
                        opp_id        = descriptor.opportunity_id()
                        des_id        = descriptor.id()
                        data_location = self._experiments.data().descriptor_location(b, descriptor)
                        opportunities_total.add(opp_id)
                        if not data_location.exists():
                            continue
                        if (data_location / 'FAILURE').exists():
                            opportunities_patch_failure.add(opp_id)
                            continue
                        opportunities_patch_success.add(opp_id)
                        for dir2, executions, files2 in os.walk(data_location):
                            for execution in executions:
                                # ATTENTION
                                # An opportunity may be shared between workloads of the same benchmarks.
                                # However, each workload has a unique set of configuration IDs because
                                # the workload is part of the parameter set, and this is how it should
                                # be since measurements cannot be shared even if the opportunity is shared
                                # because each workload has a unique performance characteristic, because
                                # it is a different exercise. As a result, we should only consider the
                                # configuration IDs that belong to the workload that we are currently
                                # scanning.
                                for dir3, configurations, files3 in os.walk(Path(dir2) / execution / 'stats'):
                                    for config_id in configurations:
                                        if not config_id in xbw_parameters_ids:
                                            continue # Belongs to another workload.
                                        measurement_location = Path(dir3) / config_id
                                        if (measurement_location / 'FAILURE').exists():
                                            if (measurement_location / 'GENERIC').exists():
                                                opportunities_bench_failure_generic.add(opp_id)
                                            elif (measurement_location / 'TIMEOUT').exists():
                                                opportunities_bench_failure_timeout.add(opp_id)
                                            else:
                                                raise ValueError("Unknown bench failure cause", x, b, w, lst_name, opp_id, des_id, config_id)
                                        elif (measurement_location / 'SUCCESS').exists():
                                            opportunities_bench_success.add(opp_id)
                                        else:
                                            raise ValueError("Unknown status of measurement", x, b, w, lst_name, opp_id, des_id, config_id)
                                    break
                            break

                # Aggregate bt_total across workloads.
                if not (b, lst_name) in bt_totals:
                    bt_totals[(b, lst_name)] = set()

                bt_total = bt_totals[(b, lst_name)]
                for opp in opportunities_total:
                    bt_total.add(opp)

                # Save result.
                results.append({
                    '_id' : {
                        'x' : x,
                        'b' : b,
                        'w' : w,
                        't' : lst_name
                    },
                    # bt_total is assigned at the end.
                    'bt_total' : None,                     # Total opportunities across all workloads for current benchmark and type.
                    'wt_total' : len(opportunities_total), # Total opportunities for current workload and type.
                    'patch' : {
                        'success' : len(opportunities_patch_success),
                        'failure' : len(opportunities_patch_failure),
                        'between' : len(
                            opportunities_patch_success.intersection(
                                opportunities_patch_failure
                            )
                        )
                     },
                    'bench' : {
                        'success' : len(opportunities_bench_success),
                        'failure' : {
                            'generic' : len(opportunities_bench_failure_generic),
                            'timeout' : len(opportunities_bench_failure_timeout)
                        },
                        'between' : len(
                            opportunities_bench_success.intersection(
                                opportunities_bench_failure_generic.union(
                                    opportunities_bench_failure_timeout
                                )
                            )
                        )
                    }
                })
        for r in results:
            b = r['_id']['b']
            t = r['_id']['t']
            r['bt_total'] = len(bt_totals[(b, t)])

        return results

