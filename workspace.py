#!/bin/env python3

import argparse
import io
import os
from pathlib import Path
import shutil
import tempfile

import daivy_commands
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
# Dependencies of test projects are source dependencies if
# they are also source dependencies of the main target.
# Otherwise, they are added as binary dependencies.
#
# TODO
#   Source tree splitting results in distinct patches.
#   We have to apply these patches onto respective paths
#   on an original unzip of the '-build.zip' archive to
#   then generate a single patch containing all changes.
#   Alternatively, we could have daivy apply a list of
#   patches on the build folder.
#
#   Another approach would be to change the refactoring
#   framework to use the layout exported from daivy in
#   '-build.zip'.

def generate_eclipse_workspace_configuration(coord, location, out):
    # TODO: Wrap all calls to daivy in an in-memory cache backed by disk
    #       to avoid resolving things multiple times.
    source_projects, build_order = daivy_commands.get_project_info(coord)
    source_projects  = set(source_projects)
    libs             = set()
    defined_projects = set()
    for p in build_order:
        master_jar  = daivy_commands.resolve_classpath(p, ['master'])[0]
        master_stem = Path(master_jar).stem
        master_main = master_stem + "-main-src.jar"

        if not p in source_projects:
            libs.add(master_jar)
            continue

        if not (location / master_main).exists():
            raise ValueError("Missing source archive", master_main, "in", str(location))

        # Main
        out.write(master_stem + " {" + os.linesep)
        for d in daivy_commands.resolve_classpath(p, ['compile']):
            d_path = Path(d)
            d_stem = d_path.stem
            if d_stem in defined_projects:
                out.write("   dep " + d_stem + os.linesep) # Eclipse project dependency
            else:
                out.write("   lib " + d_path.name + " ?" + os.linesep)
        out.write("   src / " + master_stem + "-main-src.jar" + os.linesep)
        out.write("}" + os.linesep)

        defined_projects.add(master_stem)

    for p in build_order:
        if not p in source_projects:
            continue
        master_jar  = daivy_commands.resolve_classpath(p, ['master'])[0]
        master_stem = Path(master_jar).stem
        master_test = master_stem + "-test-src.jar"

        if not (location / master_test).exists():
            continue

        # Test
        out.write(master_stem + "-test {" + os.linesep)
        out.write("   dep " + master_stem + os.linesep)
        ds = []
        for d in daivy_commands.resolve_classpath(p, ['test']):
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

    libs_dir = location / 'libs'
    libs_dir.mkdir()
    for lib in libs:
        dst = libs_dir / Path(lib).name
        shutil.copy2(lib, libs_dir)

def generate_workspace_resources(project):
    location = daivy_commands.export_project_sources(project)
    print("Source location", location)
    test_projects = []
    with tempfile.TemporaryDirectory(dir = location) as unpack_dir:
        for root, dirs, files in os.walk(location):
            for file in files:
                if not file.endswith("-build.zip"):
                    continue
                with tempfile.TemporaryDirectory(dir = location) as t:
                    print("Unpack", file, "into", t)
                    stem     = file[:file.rfind('-')]
                    src_jar  = location / (stem + "-main-src.jar")
                    test_jar = location / (stem + "-test-src.jar")

                    d = tools.unzip(location / file, Path(t))
                    d_main = d / 'src/main/java'
                    d_test = d / 'src/test/java'
                    if next(os.scandir(d_main), None):
                        tools.jar(d_main, src_jar)
                    if next(os.scandir(d_test), None):
                        tools.jar(d_test, test_jar)

    with io.StringIO() as out:
        generate_eclipse_workspace_configuration(project, location, out)
        with open(location / "workspace.config", "w") as f:
            f.write(out.getvalue())

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required = True,
        help = "Coordinate of project to operate on")
    args = parser.parse_args()
    generate_workspace_resources(args.project)

