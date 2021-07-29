#!/usr/bin/python2 -S
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Upload processor.

Given a bunch of context information and a bunch of files, process them as
an upload to a distro/whatever within the launchpad.
"""

import _pythonpath  # noqa: F401

from lp.archiveuploader.scripts.processupload import ProcessUpload


if __name__ == '__main__':
    script = ProcessUpload('process-upload', dbuser='process_upload')
    script.lock_and_run()
