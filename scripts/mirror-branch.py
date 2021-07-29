#!/usr/bin/python2 -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This script uses relative imports.
"""Script run by cronscripts/supermirror-pull.py to mirror single branches.

Do NOT run this script yourself unless you really know what you are doing. Use
cronscripts/supermirror-pull.py instead.

Usage: scripts/mirror-branch.py source_url dest_url branch_id unique_name \
                                branch_type default_stacked_on_url

Where:
  source_url is the location of the branch to be mirrored.
  dest_url is the location to mirror the branch to.
  branch_id is the database ID of the branch.
  unique_name is the unique name of the branch.
  branch_type is one of HOSTED, MIRRORED, IMPORTED
  default_stacked_on_url is the default stacked-on URL of the product that
      the branch is in.
"""

# This script does not use the standard Launchpad script framework as it is
# not intended to be run by itself.


import _pythonpath  # noqa: F401

from optparse import OptionParser
import os
import resource
import sys

import breezy.repository

from lp.code.enums import BranchType
from lp.codehosting.puller.worker import (
    install_worker_ui_factory,
    PullerWorker,
    PullerWorkerProtocol,
    )
from lp.services.webapp.errorlog import globalErrorUtility


branch_type_map = {
    BranchType.MIRRORED: 'mirror',
    BranchType.IMPORTED: 'import'
    }


def shut_up_deprecation_warning():
    # XXX DavidAllouche 2006-01-29:
    # Quick hack to disable the deprecation warning for old repository
    # formats.
    breezy.repository._deprecation_warning_done = True


if __name__ == '__main__':
    parser = OptionParser()
    (options, arguments) = parser.parse_args()
    (source_url, destination_url, branch_id, unique_name,
     branch_type_name, default_stacked_on_url) = arguments

    branch_type = BranchType.items[branch_type_name]
    if branch_type == BranchType.IMPORTED and 'http_proxy' in os.environ:
        del os.environ['http_proxy']
    section_name = 'supermirror_%s_puller' % branch_type_map[branch_type]
    globalErrorUtility.configure(section_name)
    shut_up_deprecation_warning()

    resource.setrlimit(resource.RLIMIT_AS, (1500000000, 1500000000))

    # The worker outputs netstrings, which are bytes.
    protocol = PullerWorkerProtocol(getattr(sys.stdout, 'buffer', sys.stdout))
    install_worker_ui_factory(protocol)
    PullerWorker(
        source_url, destination_url, int(branch_id), unique_name, branch_type,
        default_stacked_on_url, protocol).mirror()
