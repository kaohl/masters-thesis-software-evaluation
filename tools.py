#!/bin/env python3

import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
from zipfile import ZipFile

def unzip(src, dst):

    if not zipfile.is_zipfile(src):
        raise ValueError('Specified file is not a zip file', src)

    with ZipFile(src, 'r') as z:
        print('[unzip]', src, 'into', dst)
        z.extractall(dst)

    return dst

def _zip(src, dst):
    if src is None or dst is None:
        raise ValueError('Cannot zip', src, dst)
    if dst.suffix == '.zip':
        dst = dst.parent / dst.stem
    print("[zip]", str(src), str(dst))
    shutil.make_archive(dst, 'zip', src)

def zip(src, dst):
    _zip(src, dst) # Call internal.

def jar(src, dst):
    print("[jar]", str(src), str(dst))
    _zip(src, dst) # Call internal to avoid collision with builtin 'zip'.
    shutil.move(str(dst) + '.zip', dst)

def sdkman_command(command):
    # NOTE: The command string is what SDKMAN! puts into .bashrc.
    #       The .bashrc file appears not to be sourced by subprocess.run().
    base = 'export SDKMAN_DIR="$HOME/.sdkman"; [[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ]] && source "$HOME/.sdkman/bin/sdkman-init.sh"; '
    return base + command + ';'

# The sdk command is a bit slow, so cache installed sdks.
_installed_sdks_cache = None

def get_installed_sdks(refresh = False):
    global _installed_sdks_cache
    if not refresh and not _installed_sdks_cache is None:
        return _installed_sdks_cache
    result = subprocess.run(
        sdkman_command('sdk list java'),
        shell = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT
    )
    p    = re.compile('\\| installed  \\| ([\\d.\\w-]+)')
    sdks = []
    for line in result.stdout.decode('utf-8').split(os.linesep):
        matches = p.findall(line)
        if len(matches) > 0:
            for sdk in matches:
                sdks.append(sdk)
    _installed_sdks_cache = sdks
    return sdks

def sdk_install(sdk):
    if sdk in get_installed_sdks():
        return
    result = subprocess.run(
        sdkman_command('sdk install java {}'.format(sdk)),
        shell = True
    )
    if not result.returncode == 0:
        raise ValueError("Could not install specified sdk: " + sdk)

def sdk_home(sdk):
    result = subprocess.run(
        sdkman_command('sdk home java {}'.format(sdk)),
        shell = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT
    )
    if result.returncode != 0:
        raise ValueError("Could not resolve home for sdk {}".format(sdk))
    return result.stdout.decode(encoding = 'utf-8').strip()

# Add an 'sdk use java <version>' header to the specified command string.
# The returned command string is compatible with e.g. 'subprocess.run()'.
# Raises ValueError if the specified sdk is not installed.
def sdk_run(sdk, command):
    if not sdk in get_installed_sdks():
        raise ValueError("The specified sdk '{}' is not installed".format(sdk))
    return sdkman_command(' '.join(['sdk use java', sdk])) + command

def sdk_of_minimum_major_version(major_version):
    min_version = int(major_version)
    candidate   = None
    candidate_v = None
    for sdk in get_installed_sdks():
        v = int(sdk[:sdk.find('.')])
        if v >= min_version:
            if candidate is None or v < candidate_v:
                candidate   = sdk
                candidate_v = v
    if candidate is None:
        raise ValueError("Could not satisfy SDK minimum major version: {}. Found SDKs: {}".format(min_version, get_installed_sdks()))
    return candidate

