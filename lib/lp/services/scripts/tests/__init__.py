# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'find_lp_scripts',
    ]


import os
import subprocess

import lp
from lp.services.config import config


LP_TREE = os.path.dirname(os.path.dirname(os.path.dirname(lp.__file__)))


SCRIPT_LOCATIONS = [
    'cronscripts',
    'scripts',
    ]


def find_lp_scripts():
    """Find all scripts/ and cronscripts/ files in the current tree.

    Skips filename starting with '_' or not ending with '.py' or
    listed in the KNOWN_BROKEN blacklist.
    """
    scripts = []
    for script_location in SCRIPT_LOCATIONS:
        location = os.path.join(LP_TREE, script_location)
        for path, dirs, filenames in os.walk(location):
            for filename in filenames:
                script_path = os.path.join(path, filename)
                if (filename.startswith('_') or
                    not filename.endswith('.py')):
                    continue
                scripts.append(script_path)
    return sorted(scripts)


def run_script(script_relpath, args, expect_returncode=0, extra_env=None,
               universal_newlines=True):
    """Run a script for testing purposes.

    :param script_relpath: The relative path to the script, from the tree
        root.
    :param args: Arguments to provide to the script.
    :param expect_returncode: The return code expected.  If a different value
        is returned, and exception will be raised.
    :param extra_env: A dictionary of extra environment variables to provide
        to the script, or None.
    :param universal_newlines: Passed to `subprocess.Popen`, defaulting to
        True.
    """
    script = os.path.join(config.root, script_relpath)
    args = [script] + args
    env = dict(os.environ)
    if extra_env is not None:
        env.update(extra_env)
    process = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
        universal_newlines=universal_newlines)
    stdout, stderr = process.communicate()
    if process.returncode != expect_returncode:
        raise AssertionError('Failed:\n%s\n%s' % (stdout, stderr))
    return (process.returncode, stdout, stderr)
