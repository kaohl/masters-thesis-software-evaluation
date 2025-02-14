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
        ("--import-path" if not import_dir is None else ""),
        str((import_dir if not import_dir is None else "")),
        "--verbose"
    ]
    cmd        = " ".join(options)
    DAIVY_HOME = os.environ['DAIVY_HOME']
    result     = subprocess.run(tools.sdk_run(configuration.jdk(), cmd), shell = True, cwd = DAIVY_HOME)

    if result.returncode != 0:
        raise ValueError("Benchmark deployment failed")

def run_benchmark(args, configuration, deployment, jfr, jfr_file):

    bm         = configuration.bm()
    workload   = configuration.bm_workload()

    bm_options = { '-size' : workload }

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
    for name, value in bm_options.items():
        options.append(name)
        options.append(value)
    code = "java -Xss4M " + " ".join(options) # TODO: Parameterize stack size
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

