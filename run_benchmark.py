#!/bin/env python3

import argparse
from multiprocessing import Process
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import patch
import tools

# Timeout configuration json object (integer timeouts in seconds):
# { 'default' : int, 'defaults' : { '<bm>' : int }, '<bm>' : { '<wl>' : int } }

_empty                     = dict()
_default_timeout           = 40 # 40 seconds covers all small and default workloads that we use on our machines.
_configured_timeout        = None
_configured_timeout_path   = Path('timeout.config')

def get_configured_benchmark_timeout(configuration):
    global _configured_timeout_path
    global _configured_timeout
    global _default_timeout
    global _empty

    if _configured_timeout is None and _configured_timeout_path.exists():
        with open(_configured_timeout_path, 'r') as f:
            _configured_timeout = json.load(f)

    if _configured_timeout is None:
        print(f"Using default benchmark timeout: {_default_timeout} seconds")
        print(f"Please create '{_configured_timeout_path}' to customize benchmark timeouts.")
        return int(_default_timeout)

    bm_timeout = _configured_timeout.get(configuration.bm(), _empty)
    wl_timeout = bm_timeout.get(configuration.bm_workload(), None)

    if not wl_timeout is None:
        return int(wl_timeout)

    defaults   = _configured_timeout.get('defaults', _empty)
    bm_default = defaults.get(configuration.bm(), None)

    if not bm_default is None:
        return int(bm_default)

    return int(_configured_timeout.get('default', _default_timeout))

def get_runtime_options(configuration):
    java_options = []
    if configuration.stack_size() != None:
        java_options.append("-Xss" + configuration.stack_size())
    if configuration.heap_size() != None:
        java_options.append("-Xmx" + configuration.heap_size())
    return java_options

def get_harness_options(configuration):
    options = [ '-size', configuration.bm_workload() ]
    return options

def deploy_benchmark(configuration, clean, context = None, import_dir = None):
    if not context:
        context = Path(os.getcwd()) / 'deployments'

    options = [
        "./build.py",
        "--project",
        f"dacapo:{configuration.bm()}:1.0",
        "--context",
        str(context),
        ("--clean" if clean else ""),
        "--verbose",
        ("--import-path " + str(import_dir) if import_dir != None else ""),
        ("--target-version " + configuration.target_version() if configuration.target_version() != None else "")
    ]
    cmd        = " ".join(options)
    DAIVY_HOME = os.environ['DAIVY_HOME']
    result     = subprocess.run(
        tools.sdk_run(configuration.jdk(), cmd),
        stdout     = subprocess.PIPE,
        stderr     = subprocess.STDOUT,
        shell      = True,
        executable = '/bin/bash',
        cwd        = DAIVY_HOME
    )

    if result.returncode != 0:
        raise ValueError(result.stdout.decode('utf-8'))

def run_benchmark(configuration, deployment, jfr, jfr_file):

    bm         = configuration.bm()
    workload   = configuration.bm_workload()

    options  = []
    features = []

    # https://developers.redhat.com/blog/2020/08/25/get-started-with-jdk-flight-recorder-in-openjdk-8u#
    # https://docs.redhat.com/en/documentation/red_hat_build_of_openjdk/17/html/using_jdk_flight_recorder_with_red_hat_build_of_openjdk/configure-jfr-options#configure-jfr-options

    if jfr:
        # Seems like different JDKs ship different default configurations (atleast by checksum).
        # Best to generate a configuration that is compatible with the one that is actually used.
        result = subprocess.run(
            tools.sdk_run(
                configuration.jre(),
                "${JAVA_HOME}/bin/jfr configure --output jfr/custom.jfc method-profiling=max"
            ),
            shell      = True,
            executable = '/bin/bash',
            stdout     = subprocess.PIPE,
            stderr     = subprocess.STDOUT,
            timeout    = 10 # Raises subprocess.TimeoutExpired.
        )

        if result.returncode != 0:
            text = result.stdout.decode('utf-8')
            raise ValueError("Benchmark failed. Failed to configure JFR.", text)

        jfr_options = [
            "samplethreads=true",
        ]
        jfr_start_options = [
            "disk=false",
            "dumponexit=true",
            "filename=" + jfr_file,
            "settings=jfr/custom.jfc"
        ]
        features.extend([
            "-XX:FlightRecorderOptions=" + ",".join(jfr_options),
            "-XX:StartFlightRecording=" + ",".join(jfr_start_options)
        ])
    options.extend(features)
    options.extend([
        "-jar",
        str(deployment / f"{bm}-1.0.jar {bm} -n 10") # Run -n times and return exec-time of last iteration.
    ])
    options.extend(get_harness_options(configuration))

    java_options = get_runtime_options(configuration)

    code = ' '.join(['java', ' '.join(java_options), ' '.join(options)])
    print("--- Run benchmark using ---")
    print(code)
    print("-" * 27)
    result = subprocess.run(
        tools.sdk_run(configuration.jre(), code),
        shell      = True,
        executable = '/bin/bash',
        stdout     = subprocess.PIPE,
        stderr     = subprocess.STDOUT,
        timeout    = get_configured_benchmark_timeout(configuration) # Raises subprocess.TimeoutExpired.
    )
    text = result.stdout.decode('utf-8')
    print("--- BENCHMARK OUTPUT ---")
    print(text)
    print("--- BENCHMARK OUTPUT END ---")
    if result.returncode != 0:
        raise ValueError("Benchmark failed", text)
    if text.find('Benchmark failed to converge') != -1:
        raise ValueError("Benchmark failed to converge")
    p    = re.compile('PASSED in (\\d+) msec')
    execution_time = p.findall(text)[0]
    print("CAPTURED EXECUTION TIME", execution_time, "ms")
    return execution_time

