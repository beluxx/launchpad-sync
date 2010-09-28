#!/usr/bin/python -S
#
# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Handle jobs for a specified job source class."""

__metaclass__ = type

import _pythonpath
import sys
from optparse import OptionParser

from twisted.python import log

from canonical.config import config
from lp.services.job.runner import (
    JobCronScript,
    JobRunner,
    )
from lp.services.job import runner


class ProcessJobSource(JobCronScript):
    """Run jobs."""

    def __init__(self, job_source):
        self.config_name = job_source
        section = getattr(config, self.config_name)
        # The fromlist argument is necessary so that __import__()
        # returns the bottom submodule instead of the top one.
        module = __import__(section.module, fromlist=[job_source])
        self.source_interface = getattr(module, job_source)
        if getattr(section, 'runner_class', None) is None:
            runner_class = JobRunner
        else:
            runner_class = getattr(runner, section.runner_class, JobRunner)
        super(ProcessJobSource, self).__init__(
            runner_class=runner_class,
            script_name='process-job-source-%s' % job_source)

    def main(self):
        if self.options.verbose:
            log.startLogging(sys.stdout)
        super(ProcessJobSource, self).main()


class NoErrorOptionParser(OptionParser):
    """Allow any options that will be later handled by ProcessJobSource."""

    def error(self, *args, **kw):
        pass


if __name__ == '__main__':
    options, args = NoErrorOptionParser().parse_args()
    if len(args) != 1:
        print "Usage: %s [options] JOB_SOURCE" % sys.argv[0]
        print
        print "For help, run:"
        print "    cronscripts/process-job-source-groups.py --help"
        sys.exit()
    job_source = args[0]
    script = ProcessJobSource(job_source)
    script.lock_and_run()
