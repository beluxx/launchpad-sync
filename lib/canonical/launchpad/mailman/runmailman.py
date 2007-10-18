# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Start and stop the Mailman processes."""

__metaclass__ = type
__all__ = [
    'start_mailman',
    'stop_mailman',
    ]


import os
import sys
import subprocess

from canonical.config import config
from canonical.launchpad.mailman.monkeypatches import monkey_patch


def stop_mailman():
    """Stop the Mailman master qrunner, which kills all its subprocesses."""
    mailman_path = config.mailman.build.prefix
    mailman_bin  = os.path.join(mailman_path, 'bin')
    code = subprocess.call(('./mailmanctl', 'stop'), cwd=mailman_bin)
    if code:
        print >> sys.stderr, 'mailmanctl did not stop cleanly:', code


def start_mailman():
    """Start the Mailman master qrunner.

    The client of start_mailman() is responsible for ensuring that
    stop_mailman() is called at the appropriate time.
    """
    # We need the Mailman bin directory so we can run some of Mailman's
    # command line scripts.
    mailman_path = config.mailman.build.prefix
    mailman_bin  = os.path.join(mailman_path, 'bin')
    # Monkey-patch the installed Mailman 2.1 tree.
    monkey_patch(mailman_path, config)
    # Start the Mailman master qrunner.
    code = subprocess.call(('./mailmanctl', 'start'), cwd=mailman_bin)
    if code:
        print >> sys.stderr, 'mailmanctl did not start cleanly'
        sys.exit(code)
