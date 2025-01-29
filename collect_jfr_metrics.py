#!/bin/env python

import os
import subprocess

# See '<evaluation>/jfr/sample-events.txt' for a subset of
# available events that could be useful. Not an exhaustive
# list... Find more using: 'jfr print <file> | less',
# or by filtering using the --events flag.


def compilation_metrics(jfr_file):
    compilations = get_compilations(jfr_file)

    # - Probably need to run each benchmark a large number of times to get enough JFR statistics.
    #   It is perhaps not feasible to do this for all transformation but perhaps for a random subset
    #   or perhaps only focusing on inline/extract refactorings, or random subset of those.
    #
    # - Looks like we may need to map methods as (method, compileLevel)-pairs to get comparable numbers
    #   in each category. It would only be relevant to compare measurements on the same VM and VM configuration
    #   so perhaps compileLevel will always be the same(?) and this is not needed after all.
    #
    # - Method compilation time
    # - Method code size
    #
    # - Compilation success count (Not sure how relevant but could look for changes just in case.)

    # Sample Compilation event:
    #'duration': '365.715 ms',
    #'method': 'sun.java2d.SunGraphics2D.validateBasicStroke(BasicStroke)',
    #'compileLevel': '4',
    #'succeded': 'true',
    #'isOsr': 'false',
    #'codeSize': '2.8 kB',
    #'inlinedBytes': '193 bytes'

    # TODO: Need to think about what analysing these metrics
    #       require in terms of execution time.

    pass

def get_compilations(jfr_file):

    # TODO: It is also possible to output events on json or xml formats.
    #       Change to output json or xml and use a library to read and
    #       filter all events for metric computations.
    #
    
    cmd = ' '.join([
        'jfr',
        'print',
        #'--json', TODO
        '--events',
        'jdk.Compilation',
        jfr_file
    ])
    result = subprocess.run(
        cmd,
        shell = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT
    )
    compilations = dict() # method => dict(<attributes>)
    compilation  = None
    method       = None
    for line in result.stdout.decode('utf-8').split(os.linesep):
        line = line.strip()
        try:
            if line == '':
                continue
            if line == 'jdk.Compilation {':
                compilation = dict()
                continue
            if line == '}':
                if method is None:
                    print("ERROR: method attribute missing in compilation event.")
                compilation = None
                method      = None
                continue
            parts = [ l.strip() for l in line.split(" = ") ]
            key   = parts[0].strip()
            value = ' = '.join(parts[1:])
            if key == 'method':
                compilations[value] = compilation
                method              = value
            compilation[key] = value
        except BaseException as e:
            print("Error parsing line:", line, str(e))
    return compilations

