#!/bin/env python3

import argparse
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import daivy_commands
import patch
import tools

# We extract one '<artifact stem>-build.zip' per project which
# may contain both main and test sources. From that archive we
# generate:
#   <artifact stem>-main-src.jar and
#   <artifact stem>-test-src.jar.
# Source artifacts are only generated if corresponding source
# root is non-empty within associated '-build.zip'.
#
# Because we are splitting main and test code, we add eclipse
# configurations for both the main and test eclipse projects.
#
# Projects with main and test code in the same source tree
# must have a "test" master configuration that we can use
# to resolve test dependencies.
#
# Dependencies of test projects are added as project dependencies
# if they are also project dependencies of the main target.
# Otherwise, they are added as binary dependencies.
#

def generate_eclipse_workspace_configuration(coord, location, out):
    # TODO: Wrap all calls to daivy in an in-memory cache backed by disk
    #       to avoid resolving things multiple times.

    src_location = location / 'assets/src'
    lib_location = location / 'assets/lib'

    source_projects, build_order = daivy_commands.get_project_info(coord)
    source_projects  = set(source_projects)
    libs             = set()
    defined_projects = set()
    for p in build_order:
        # Resolve the artifact of the module (assuming there is only one per module).
        # If the 'master' configuration does not exist, or if this is an interface
        # module we will get an empty array as response.
        #   In both cases, we assume it's an interface module and ignore it with
        # a warning.
        #   Interface modules has no source code. Therefore, they do not require
        # an eclipse project. All dependencies will transfer transitively to
        # all modules depending on an interface, including 'compile' dependencies.
        master_jars = daivy_commands.resolve_classpath(p, ['master'])
        if len(master_jars) == 0:
            print("Skipping interface project", p)
            continue
        elif len(master_jars) > 1:
            # Each artifact has its own source tree.
            # Therefore, we assume only one master artifact per module.
            raise ValueError("Ambiguous master artifact", master_jars)

        master_jar  = master_jars[0]
        master_stem = Path(master_jar).stem
        master_main = master_stem + "-main-src.jar"

        if not p in source_projects:
            libs.add(master_jar)
            continue

        if not (src_location / master_main).exists():
            raise ValueError("Missing source archive", master_main, "in", str(src_location))

        # Main

        out.write(master_stem + " {" + os.linesep)

        added_deps = set()
        ds         = [] # Libs
        for d in daivy_commands.resolve_classpath(p, ['compile,optional']):
            d_path = Path(d)
            d_stem = d_path.stem
            if d_stem in defined_projects:
                out.write("   dep " + d_stem + os.linesep) # Eclipse project dependency.
                added_deps.add(d_stem)

        ## Add runtime dependencies that are also source dependencies.
        ## This is required to get lucene-core onto the module path
        ## of other lucene modules (e.g. codecs which only have core
        ## as runtime dependency)
        for d in daivy_commands.resolve_classpath(p, ['runtime,optional']):
            d_path = Path(d)
            d_stem = d_path.stem
            if d_stem in defined_projects and not d_stem in added_deps:
                out.write("   dep " + d_stem + os.linesep) # Eclipse project dependency.
                added_deps.add(d_stem)
            else:
                if not d_stem in defined_projects:
                    ds.append(d_path.name)
                    libs.add(d)
                else:
                    print("Skip lib", d)

        for d in ds:
            out.write("   lib " + d + " ?" + os.linesep)

        out.write("   src / " + master_stem + "-main-src.jar" + os.linesep)
        out.write("}" + os.linesep)

        defined_projects.add(master_stem)

    for p in build_order:
        if not p in source_projects:
            continue
        master_jar  = daivy_commands.resolve_classpath(p, ['master'])[0]
        master_stem = Path(master_jar).stem
        master_test = master_stem + "-test-src.jar"

        if not (src_location / master_test).exists():
            continue

        # Test
        out.write(master_stem + "-test {" + os.linesep)
        out.write("   dep " + master_stem + os.linesep)
        ds = []
        for d in daivy_commands.resolve_classpath(p, ['test,optional']):
            d_path = Path(d)
            d_stem = d_path.stem
            # Add as binary dependency unless source is already provided.
            # We are not interested in refactoring source dependencies
            # of tests at the moment so binary dependencies works here.
            if d_stem in defined_projects:
                out.write("   dep " + d_stem + os.linesep)
            else:
                ds.append(d_path.name)
                libs.add(d)
        for d in ds:
            out.write("   lib " + d + " ?" + os.linesep)
        out.write("   src / " + master_stem + "-test-src.jar" + os.linesep)
        out.write("}" + os.linesep)

    lib_location.mkdir()
    for lib in libs:
        shutil.copy2(lib, lib_location)

def is_empty_folder(path):
    if next(os.scandir(path), None):
        return False
    return True

def generate_workspace_resources(project):
    location     = daivy_commands.export_project_sources(project)
    src_location = location / 'assets' / 'src'
    src_location.mkdir(parents = True)
    print("Using resource location", location)
    with tempfile.TemporaryDirectory(dir = location) as unpack_dir:
        for root, dirs, files in os.walk(location):
            for file in files:
                if not file.endswith("-build.zip"):
                    continue
                with tempfile.TemporaryDirectory(dir = location) as t:
                    print("Unpack", file, "into", t)
                    stem     = file[:file.rfind('-')]
                    src_jar  = src_location / (stem + "-main-src.jar")
                    test_jar = src_location / (stem + "-test-src.jar")

                    d      = tools.unzip(location / file, Path(t))
                    d_main = d / 'src/main/java'
                    d_test = d / 'src/test/java'

                    # The 'source-artifacts.txt' file is used when
                    # generating patches for all exported archives.
                    with open(src_location / 'source-artifacts.txt', 'a') as artifacts:
                        if not is_empty_folder(d_main):
                            tools.jar(d_main, src_jar)
                            artifacts.write(src_jar.name + os.linesep)

                        if not is_empty_folder(d_test):
                            tools.jar(d_test, test_jar)
                            artifacts.write(test_jar.name + os.linesep)

    with io.StringIO() as out:
        generate_eclipse_workspace_configuration(project, location, out)
        with open(src_location / "workspace.config", "w") as f:
            f.write(out.getvalue())

    # TODO: Decide how the user should add these configurations.
    #       They should not be added here unless we want to
    #       allow the user to specify path patterns that we
    #       convert into the correct configuration files.
    #
    # When we prepare a workspace we must specify which experiment
    # to use. This is the context in which configuration files
    # and the opportunity cache is saved.
    #
    # ATTENTION
    # The generated configuration files determines
    # which packages and classes are probed for
    # refactoring opportunities. The generated
    # opportunity cache is tied to this configuration. 

    #with open(src_location / 'variable.config', 'w') as var:
    #var.write("batik-all-1.16-main-src.jar" + os.linesep)
    #
    #with open(src_location / 'units.config', 'w') as units:
    #units.write("batik-all-1.16=\\" + os.linesep)
    #units.write("    org/apache/batik/ext/awt/image/codec/png/PNGEncodeParam.java" + os.linesep)
    #
    #with open(src_location / 'units.config.helper', 'w') as units:
    #units.write("org/apache/batik/ext/awt/image/codec/png/PNGEncodeParam.java" + os.linesep)
    #
    #with open(src_location / 'packages.config', 'w') as pkgs:
    #pkgs.write("batik-all-1.16=\\" + os.linesep)
    #pkgs.write("    org.apache.batik.ext.awt.image.codec.png" + os.linesep)
    #
    #with open(src_location / 'packages.config.helper', 'w') as pkgs:
    #pkgs.write("batik-all-1.16.include=\\" + os.linesep)
    #pkgs.write("    org.apache.batik.ext.awt.image.codec.png" + os.linesep)
    ##pkgs.write("batik-all-1.16.exclude=\\" + os.linesep)
    ##pkgs.write("    org/apache/batik/ext/image/codec/png" + os.linesep)

    return location

_project_compliance = {
    'dacapo:batik:1.0'    : '1.8',
    'dacapo:xalan:1.0'    : '1.8',
    'dacapo:jacop:1.0'    : '1.8',
    'dacapo:luindex:1.0'  : '11',
    'dacapo:lusearch:1.0' : '11'
}

def prepare_eclipse_workspace(project, path):
    workspace = path
    oppcache  = workspace / 'oppcache'
    cmd = " ".join([
        './refactoring-framework/eclipse/eclipse',
        '-data',
        str(workspace),     # Workspace root.
        '--prepare',
        '--compliance',
        _project_compliance[project],
        '--src',
        'assets/src',       # <workspace>/assets/src
        '--lib',
        'assets/lib',       # <workspace>/assets/lib
        '--cache',
        oppcache.name,      # <workspace>/oppcache
        '--out',
        'output',           # <workspace>/output
    ])
    subprocess.run(tools.sdk_run(tools.sdk_of_minimum_major_version(21), cmd), shell = True)

    ## TODO: All cache files may not be generated if the refactoring scope is small.
    ##       This is a temporary fix to create them as empty files if that happens.
    ##
    ##       *** This should be fixed in the refactoring framework instead.
    ##
    #oppfiles = [
    #    'extract.field.txt',
    #    'extract.method.txt',
    #    'inline.field.txt',
    #    'inline.method.txt',
    #    'rename.field.txt',
    #    'rename.local.variable.txt',
    #    'rename.method.txt',
    #    'rename.type.parameter.txt',
    #    'rename.type.txt'
    #]
    #for f in oppfiles:
    #    with open(oppcache / f, 'a'):
    #        pass

def get_name_from_project_coordinate(coord):
    return coord.replace(':', '-').replace('.', '_')

#def create_workspace(project, clean):
#    ws_name   = get_name_from_project_coordinate(project)
#    ws_path   = Path(os.getcwd()) / 'workspaces'
#    p_ws_path = ws_path / ws_name
#
#    if not ws_path.exists():
#        ws_path.mkdir()
#    
#    if clean and p_ws_path.exists():
#        shutil.rmtree(p_ws_path)
#
#    if p_ws_path.exists():
#        return p_ws_path
#
#    temp_location = generate_workspace_resources(args.project)
#    shutil.copytree(temp_location, p_ws_path)
#    shutil.rmtree(temp_location)
#
#    # Eclipse (refactoring) output directory.
#    (p_ws_path / 'output').mkdir()
#    prepare_eclipse_workspace(p_ws_path)
#    return p_ws_path

def create_workspace_in_location(project, location):
    temp_location = generate_workspace_resources(project)
    shutil.copytree(temp_location, location, dirs_exist_ok = True)
    shutil.rmtree(temp_location)

    # Eclipse (refactoring) output directory.
    (location / 'output').mkdir()
    prepare_eclipse_workspace(project, location)
    return location

def refactor(workspace_location, data_location, descriptor):
    cached_workspace = workspace_location
    with tempfile.TemporaryDirectory(delete = False, dir = 'temp') as context:
        workspace = Path(context) / 'workspace'
        print("Using workspace", str(workspace))

        # TODO: Use a symlink for oppcache.
        shutil.copytree(cached_workspace, workspace)

        # TODO: Success tracker is outdated, we should handle this in the
        #       evaluation script instead since we now have control over
        #       all descriptors. (Remove 'report' and files.)
        #
        # TODO: Also, there is no need for 'proc_id' since each process is working against its own workspace copy.
        #       (Do we even need multiprocessing now?)

        report_dir           = workspace / 'report'
        report_file          = report_dir / 'refactoring-output.txt'
        #success_tracker_file = report_dir / 'successTrackerFile.txt'
        #failure_tracker_file = report_dir / 'failureTrackerFile.txt'

        if not report_dir.exists():
            report_dir.mkdir()
        
        # Clear file between invocations.
        #with open(report_file, 'w'):
        #    pass
        #
        # Create if not already exists. (Accumulate over multiple runs.)
        #with open(success_tracker_file, 'a'):
        #    pass
        #
        # Create if not already exists. (Accumulate over multiple runs.)
        #with open(failure_tracker_file, 'a'):
        #    pass

        cmd = " ".join([
            './refactoring-framework/eclipse/eclipse',
            '-data',
            str(workspace),     # Workspace root.
            #'--compliance',                        # TODO: Compliance should not be needed here... make optional.
            #_project_compliance[project],
            #'--report',
            #'report',           # str(report_dir),
            '--src',
            'assets/src',       # <workspace>/assets/src
            '--lib',
            'assets/lib',       # <workspace>/assets/lib
            '--cache',
            'oppcache',         # <workspace>/oppcache
            '--out',
            'output',           # <workspace>/output
            '--descriptor',
            '"{}"'.format(descriptor.get_cli_line())
        ])
        print("REFACTOR", cmd)
        # TODO: See if we can get the subprocess command to write directly to file instead of explicit redirection.
        subprocess.run(tools.sdk_run(tools.sdk_of_minimum_major_version(21), cmd + ' > ' + str(workspace / 'output.log')), shell = True)

        ws_output = workspace / 'output'

        if not data_location.exists():
            data_location.mkdir(parents = True)

        with open(data_location / 'descriptor.txt', 'w') as f:
            f.write(descriptor.line() + os.linesep)

        if is_empty_folder(ws_output):
            # Print refactoring output for immediate visual feedback.
            print("*** Refactoring failed ***") 
            with open(report_file, 'r') as f:
                for line in f:
                    print(line)
            print("**************************")
            # Register that the refactoring failed.
            with open(data_location / 'FAILURE', 'w'):
                pass
            # Store the refactoring output for later reference.
            shutil.copy2(report_file, data_location / 'refactoring-output.txt')
            raise ValueError("Refactoring failed.")

        # Create a temporary directory for each run to be able to re-run descriptors if needed.
        with tempfile.TemporaryDirectory(delete = False, dir = data_location) as data_dir:
            data = Path(data_dir)
            
            # Save refactoring framework report.
            shutil.copy2(report_file, data / 'refactoring-output.txt')

            # Save command.
            with open(data / 'cmd.txt', "w") as cmd_file:
                cmd_file.write(cmd)

            # Save standard out from refactoring framework.
            shutil.copy2(workspace / 'output.log', data / 'output.log')

            archives = []
            with open(workspace / 'assets/src/source-artifacts.txt', 'r') as artifacts:
                archives.extend([ x for x in [ archive.strip() for archive in artifacts.readlines() ] if x != "" ])

            patches_file = data / 'patches.txt'

            for name in archives:
                old = workspace / 'assets/src' / name
                new = workspace / 'output' / name
                out = data / (name + '.patch')

                if new.exists():
                    patch.create_patch(old, new, out)
                    # Append patch content to patches file.
                    with open(patches_file, 'a') as psf:
                        with open(out, 'r') as outf:
                            psf.writelines(outf.readlines())

#def refactor(args, proc_id):
#    experiment = args.experiment
#    project    = get_name_from_project_coordinate(args.project)
#    cached_workspace = create_workspace(args.project, False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', required = True,
        help = "A simple name. All experiment folders are placed in the 'experiments' folder.")
    parser.add_argument('--project', required = True,
        help = "Coordinate of project to operate on.")
    parser.add_argument('--clean', required = False, action = 'store_true',
        help = "Remove associated cached resources before executing the specified operation.")
    args = parser.parse_args()

    # TODO: This script should not be called as a main script anymore.
    #       It is time to setup the top level experiment with two
    #       entry points:
    #         1) refactor, to generate data, and
    #         2) benchmark, to build and benchmark generated refactorings one by one.
    #            - We could build in parallel but there is a time space trade-off to
    #              be made. The output of each deployment is not that small so we
    #              could run out of disk space if we don't discard the deployment
    #              after each build.
    #        

    # This is just a test to see that we get a refactoring.
    create_workspace(args.project, args.clean)
    refactor(args, 0)

