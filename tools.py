from pathlib import Path
import shutil
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
