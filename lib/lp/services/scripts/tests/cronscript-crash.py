#!/usr/bin/python2 -S
# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Cronscript that raises an unhandled exception."""

__metaclass__ = type
__all__ = []

import _pythonpath  # noqa: F401

from lp.services.scripts.base import LaunchpadCronScript
from lp.services.webapp.errorlog import globalErrorUtility


class CrashScript(LaunchpadCronScript):

    def main(self):
        self.oopses = []

        def publish(report):
            self.oopses.append(report)
            return []

        globalErrorUtility._oops_config.publisher = publish

        self.logger.debug("This is debug level")
        # Debug messages do not generate an OOPS.
        assert not self.oopses, "oops reported %r" % (self.oopses,)

        self.logger.warning("This is a warning")
        if len(self.oopses):
            self.logger.info("New OOPS detected")
        del self.oopses[:]

        self.logger.critical("This is critical")
        if len(self.oopses):
            self.logger.info("New OOPS detected")

        raise NotImplementedError("Whoops")


if __name__ == "__main__":
    script = CrashScript("crash")
    script.lock_and_run()
