import os
from pathlib import Path
import subprocess
import tempfile

# Not very nice but works...
# TODO: Would be better if we could distribute daivy as a package and import it here.

def resolve_classpath(coord, confs):
    classpath = []
    DAIVY_HOME = os.environ['DAIVY_HOME']
    with tempfile.TemporaryDirectory(dir = Path(os.getcwd()) / 'temp') as tempdir:
        with tempfile.NamedTemporaryFile(delete_on_close=False, dir = tempdir) as classpath_file:
            classpath_file.close()
            cmd = " ".join([
                '${DAIVY_HOME}/ivy_cache_resolver.py',
                '-m',
                coord,
                '--classpath',
                '--classpath-file',
                classpath_file.name,
                '--confs',
                ",".join(confs)
            ])
            subprocess.run(cmd, shell = True, cwd = DAIVY_HOME)

            with open(classpath_file.name, 'r') as cpf:
                classpath.extend([ x.strip() for x in cpf.readlines()])
    print("--- Found dependencies ---", coord, confs)
    for d in classpath:
        print(" ", d)
    print("--------------------------")
    return classpath

def get_project_info(coord):
    source_projects = []
    build_order     = []

    DAIVY_HOME = os.environ['DAIVY_HOME']
    temp       = Path(os.getcwd()) / 'temp'
    with tempfile.TemporaryDirectory(dir = temp) as tempdir:
        cmd = " ".join([
            '${DAIVY_HOME}/build.py',
            '--context',
            'context',  # TODO: Don't use this shared directory...
            '--project',
            coord,
            '--info',
            tempdir
        ])
        subprocess.run(cmd, shell = True, cwd = DAIVY_HOME)
        with open(Path(tempdir) / 'build-order.txt', 'r') as f:
            build_order.extend([x.strip() for x in f.readlines()])
        with open(Path(tempdir) / 'source-projects.txt', 'r') as f:
            source_projects.extend([x.strip() for x in f.readlines()])

    return source_projects, build_order

def export_project_sources(coord):
    DAIVY_HOME = os.environ['DAIVY_HOME']
    temp       = Path(os.getcwd()) / 'temp'
    export_dir = None
    with tempfile.TemporaryDirectory(delete = False, dir = temp) as tempdir:
        export_dir = Path(tempdir)
        cmd = " ".join([
            '${DAIVY_HOME}/build.py',
            '--context',
            'context',  # TODO: Don't use this shared directory...
            '--project',
            coord,
            '--export',
            '--export-path',
            tempdir,
            '--clean'
        ])
        subprocess.run(cmd, shell = True, cwd = DAIVY_HOME)
    return export_dir

