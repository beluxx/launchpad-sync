#!/usr/bin/python2 -S
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import _pythonpath  # noqa: F401

from lp.archivepublisher.scripts.publishdistro import PublishDistro


if __name__ == "__main__":
    script = PublishDistro('publish-distro', dbuser='publish_distro')
    script.lock_and_run()
