#!/bin/env python3

import os
import subprocess

def deploy_benchmark(bm):
    options = [
        "./build.py",
        "--project dacapo:@BM:1.0".replace("@BM", bm),
        "--context @CWD/deployments".replace("@CWD", os.getcwd()),
        "--clean",
        "--verbose"
    ]
    cmd  = " ".join(options)
    code = 'if [ "$DAIVY_HOME" = "" ]; then echo "Please set DAIVY_HOME"; else X=`pwd`; cd $DAIVY_HOME; @CMD; cd $X; fi'\
        .replace("@CMD", cmd)
    subprocess.run(code, shell = True)

def run_benchmark(bm, bm_options, jfr = False):
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
            "filename=flight-123.jfr",
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
    options.append(
        "-jar deployments/@BM-1.0.jar @BM".replace("@BM", bm)
    )
    for name, value in bm_options.items():
        options.append(name)
        options.append(value)
    code = "java " + " ".join(options)
    print("--- Run benchmark using ---")
    print(code)
    print("-" * 27)
    subprocess.run(code, shell = True)

def _main():
    #run_benchmark("batik", {'-size' : 'small'}, True)
    #run_benchmark("batik", {'-size' : 'default'}, True)
    run_benchmark("xalan", {}, True)

if __name__ == '__main__':
    #deploy_benchmark("batik")
    #deploy_benchmark("xalan")
    _main()
