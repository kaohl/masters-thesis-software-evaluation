#!/bin/env python3

import json
import os

from multiprocessing import Process, Queue

# Example adapted from here:
# https://docs.python.org/3/library/multiprocessing.html

def get_number_of_cores():
    result = subprocess.run(
        "nproc --all",
        shell  = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT
    )
    return int(result.stdout.decode('utf-8').strip())

NUMBER_OF_WORKERS = get_number_of_cores()
BATCH_SIZE        = NUMBER_OF_WORKERS

def worker(input, output):
    for func, args in iter(input.get, 'STOP'):
        try:
            output.put(func(*args))
        except BaseException as e:
            output.put(None)
            print("Task Exception", func, args, str(e))

def run(tasks):
    global NUMBER_OF_WORKERS

    task_queue = Queue()
    done_queue = Queue()

    for i in range(NUMBER_OF_WORKERS):
        Process(target = worker, args=(task_queue, done_queue)).start()

    # Note, the following works even if NUMBER_OF_WORKERS
    # is greater than the number of tasks, because of how
    # [:x] and [x:] works when 'x' is larger than the len
    # of the list.

    posted = 0
    for task in tasks[:NUMBER_OF_WORKERS]:
        task_queue.put(task)
        posted = posted + 1

    for task in tasks[NUMBER_OF_WORKERS:]:
        # We consume one result and add a new task,
        # i.e. 'posted' is unchanged: -1 + 1 = 0.
        result = done_queue.get()
        task_queue.put(task)

    while posted > 0:
        result = done_queue.get()
        posted = posted - 1

    for i in range(NUMBER_OF_WORKERS):
        task_queue.put('STOP')

def run_batch(tasks, ids, do_run):
    if do_run:
        run([ task for task in tasks ])
        tasks.clear()
        ids.clear()

def do_files(files, tell, parse_task_from_line, max_size = BATCH_SIZE):
    global BATCH_SIZE

    print("Executor: Process files: " + os.linesep + os.linesep.join([str(f) for f in files]))

    active_files = set(files)
    done_files   = set()
    n            = 0
    while len(active_files) > 0 and n < max_size:
        active_files = active_files - done_files
        tasks        = []
        ids          = set() # Track ids to avoid duplications within a batch.
        for name in active_files:
            with open(name, 'r') as f:
                f.seek(tell[name])
                done = False
                while not done and len(tasks) < BATCH_SIZE:
                    line = f.readline()
                    if line == "": # EOF
                        done_files.add(name)
                        done = True
                        continue
                    line = line.strip()
                    if line == "": # Empty line.
                        continue
                    task, id = parse_task_from_line(line)
                    if not task is None and not id in ids:
                        tasks.append(task)
                        ids.add(id)
                        n = n + 1
                tell[name] = f.tell()
            run_batch(tasks, ids, len(tasks) >= BATCH_SIZE)
        run_batch(tasks, ids, len(tasks) > 0)

def load_state(file, files):
    tell = dict()
    if file.exists():
        with open(file, 'r') as f:
            try:
                tell = json.loads(f.readline())
            except Exception as e:
                print("Failed to load state")
                print(str(e))
                print("Resuming with reset read state.")
                tell = dict()
    for name in files:
        if not name in tell:
            tell[name] = 0
    return tell

def save_state(file, tell):
    if not file.parent.exists():
        file.parent.mkdir(parents = True)

    with open(file, 'w') as f:
        f.write(json.dumps(tell) + os.linesep)

