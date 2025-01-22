from pathlib import Path
import subprocess
import tempfile

import tools

def apply_patch(patch, target_dir):
    if patch.exists():
        cmd = ' '.join([
            "patch",
            "-p4",    # Removes: /tmp/<tmp>/new/
            "<",
            str(patch)
        ])
        subprocess.run(cmd, shell = True, cwd = str(target_dir))

def create_patch(old, new, out):
    # We use the /tmp directory as root here
    # so that there is a known (fixed-length)
    # path prefix that we remove when we apply
    # the patch. 
    with tempfile.TemporaryDirectory() as tmp:
        d_old = Path(tmp) / 'old'
        d_new = Path(tmp) / 'new'
        d_old.mkdir()
        d_new.mkdir()

        tools.unzip(old, d_old)
        tools.unzip(new, d_new)

        diff_cmd = ' '.join([
            "diff",
            '-ur',
            '--unidirectional-new-file',
            str(d_old),
            str(d_new),
            ">",
            str(out)
        ])
        subprocess.run(diff_cmd, shell = True)
