#!/bin/env python3

import argparse
from multiprocessing import Process
import os
from pathlib import Path
import re
import subprocess
import tempfile

import patch
import tools

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

def deploy_benchmark(args, configuration, clean, context = None, import_dir = None):
    if not context:
        context = Path(os.getcwd()) / 'deployments'

    options = [
        "./build.py",
        "--project",
        "dacapo:@BM:1.0".replace("@BM", configuration.bm()), # TODO: Add project coordinate as a derived attribute on configuration?
        "--context",
        str(context),
        ("--clean" if clean else ""),
        "--verbose",
        ("--import-path " + str(import_dir) if import_dir != None else ""),
        ("--target-version " + configuration.target_version() if configuration.target_version() != None else "")
    ]
    cmd        = " ".join(options)
    DAIVY_HOME = os.environ['DAIVY_HOME']
    result     = subprocess.run(tools.sdk_run(configuration.jdk(), cmd), shell = True, cwd = DAIVY_HOME)

    if result.returncode != 0:
        raise ValueError("Benchmark deployment failed")

def run_benchmark(args, configuration, deployment, jfr, jfr_file):

    bm         = configuration.bm()
    workload   = configuration.bm_workload()

    options  = []
    features = []

    # TODO: I belive this works only for java 8.
    #       Need other options with later versions. 

    if jfr:
        jfr_options = [
            "samplethreads=true",
        ]
        jfr_start_options = [
            "disk=false",
            "dumponexit=true",
            "filename=" + jfr_file,
            "settings=jfr/custom-profile.jfr"
        ]
        features.extend([
            # TODO: Looks like this option is only for Oracle < 11.
            #"-XX:+UnlockCommercialFeatures",

            "-XX:+UnlockDiagnosticVMOptions",
            "-XX:+DebugNonSafepoints",
            "-XX:+FlightRecorder",
            "-XX:FlightRecorderOptions=" + ",".join(jfr_options),
            "-XX:StartFlightRecording=" + ",".join(jfr_start_options)
        ])
    options.extend(features)
    options.extend([
        "-jar",
        str(deployment / "@BM-1.0.jar @BM".replace("@BM", bm))
    ])
    options.extend(get_harness_options(configuration))

    java_options = get_runtime_options(configuration)

    code = ' '.join(['java', ' '.join(java_options), ' '.join(options)])
    print("--- Run benchmark using ---")
    print(code)
    print("-" * 27)
    result = subprocess.run(
        tools.sdk_run(configuration.jre(), code),
        shell  = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT
    )
    if result.returncode != 0:
        raise ValueError("Benchmark failed")
    p    = re.compile('PASSED in (\\d+) msec')
    text = result.stdout.decode('utf-8')
    execution_time = p.findall(text)[0]
    print("--- BENCHMARK OUTPUT ---")
    print(text)
    print("--- BENCHMARK OUTPUT END ---")
    print("CAPTURED EXECUTION TIME", execution_time, "ms")
    return execution_time

