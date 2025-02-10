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

def deploy_benchmark(bm, clean, context = None, import_dir = None):
    if not context:
        context = Path(os.getcwd()) / 'deployments'

    options = [
        "./build.py",
        "--project",
        "dacapo:@BM:1.0".replace("@BM", bm),
        "--context",
        str(context),
        ("--clean" if clean else ""),
        ("--import-path" if not import_dir is None else ""),
        str((import_dir if not import_dir is None else "")),
        "--verbose"
    ]
    cmd        = " ".join(options)
    DAIVY_HOME = os.environ['DAIVY_HOME']
    subprocess.run(cmd, shell = True, cwd = DAIVY_HOME)

def run_benchmark(bm, deployment, bm_options, jfr, jfr_file):
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
        code,
        shell  = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT
    )
    p    = re.compile('PASSED in (\\d+) msec')
    text = result.stdout.decode('utf-8')
    execution_time = p.findall(text)[0]
    print("--- BENCHMARK OUTPUT ---")
    print(text)
    print("--- BENCHMARK OUTPUT END ---")
    print("CAPTURED EXECUTION TIME", execution_time, "ms")
    return execution_time

#def _main(bm, size, clean = False, jfr = False, jfr_file = 'flight.jfr'):
#    deploy_benchmark(bm, clean)
#    run_benchmark(bm, Path('deployments'), { '-size' : size }, jfr, jfr_file)

def prime_import_location(bm, location, data):
    # Assume that we have workspaces available.
    # However, at this point we are only interested
    # in the orignal '-build.zip' files and patches.
    name = "dacapo:{}:1.0".format(bm).replace(":", '-').replace('.', '_')
    ws   = Path('workspaces') / name
    # TODO: There is no need to do a walk here.
    #       All the files we need are in the 'ws'
    #       folder.
    for root, dirs, files in os.walk(ws):
        for file in files:
            if not file.endswith("-build.zip"):
                continue

            with tempfile.TemporaryDirectory(dir = location) as tmp:
                temp           = Path(tmp)
                stem           = file[:file.rfind('-')]
                main_jar_patch = data / (stem + "-main-src.jar.patch")
                test_jar_patch = data / (stem + "-test-src.jar.patch")

                tools.unzip(ws / file, tmp)

                if main_jar_patch.exists():
                    patch.apply_patch(main_jar_patch, temp / 'src/main/java')

                if test_jar_patch.exists():
                    patch.apply_patch(test_jar_patch, temp / 'src/test/java')

                tools.zip(temp, location / file)

def build_and_benchmark_refactoring(args):
    bm       = args.bm
    clean    = args.clean
    jfr      = args.jfr
    jfr_file = args.jfr_file
    data     = args.data and Path(args.data)
    size     = args.size or 'default' # DaCapo option.
    with tempfile.TemporaryDirectory(delete = False, dir = 'temp') as location:
        import_dir = Path(location)
        deploy_dir = Path(location) / 'deployment'
        deploy_dir.mkdir()
        if data is None:
            deploy_benchmark(bm, clean, deploy_dir)
        else:
            prime_import_location(bm, import_dir, data)
            deploy_benchmark(bm, clean, deploy_dir, import_dir)
        run_benchmark(bm, deploy_dir, { '-size' : size }, jfr, jfr_file)

def build_and_benchmark(data_location, configuration, jfr = True):
    bm       = configuration.bm()
    jfr_file = 'flight.jfr'
    data     = data_location # args.data and Path(args.data)
    size     = configuration.size() # DaCapo option.
    with tempfile.TemporaryDirectory(delete = False, dir = 'temp') as location:
        import_dir = Path(location)
        deploy_dir = Path(location) / 'deployment'
        deploy_dir.mkdir()
        prime_import_location(bm, import_dir, data)
        deploy_benchmark(bm, True, deploy_dir, import_dir)
        run_benchmark(bm, deploy_dir, { '-size' : size }, jfr, jfr_file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bm', required = True,
        help = "Coordinate of project to operate on")
    parser.add_argument('--size', required = False,
        help = "Workload size indicator")
    parser.add_argument('--clean', required = False, action = 'store_true',
        help = "Redeploy benchmark from build framework.")
    parser.add_argument('--jfr', required = False, action = 'store_true',
        help = "Run with Java Flight Recorder enabled.")
    parser.add_argument('--jfr-file', required = False,
        help = "The file to which the JFR recording is written.")
    parser.add_argument('--data', required = False,
        help = "Path to data directory output by refactoring framework.")
    args = parser.parse_args()

    build_and_benchmark_refactoring(args)

