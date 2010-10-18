# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Soyuz buildd slave manager logic."""

__metaclass__ = type

__all__ = [
    'BaseDispatchResult',
    'BuilddManager',
    'BUILDD_MANAGER_LOG_NAME',
    'FailDispatchResult',
    'ResetDispatchResult',
    ]

import logging

import transaction
from twisted.application import service
from twisted.internet import (
    defer,
    reactor,
    )
from twisted.internet.task import LoopingCall
from twisted.python import log
from zope.component import getUtility

from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    BuildBehaviorMismatch,
    )
from lp.buildmaster.interfaces.builder import (
    BuildDaemonError,
    BuildSlaveFailure,
    CannotBuild,
    CannotFetchFile,
    CannotResumeHost,
    )


BUILDD_MANAGER_LOG_NAME = "slave-scanner"


def get_builder(name):
    """Helper to return the builder given the slave for this request."""
    # Avoiding circular imports.
    from lp.buildmaster.interfaces.builder import IBuilderSet
    return getUtility(IBuilderSet)[name]


def assessFailureCounts(builder, fail_notes):
    """View builder/job failure_count and work out which needs to die.  """
    # XXX: completely lacks tests
    # XXX: Change behaviour to allow for more builder failures.

    # builder.currentjob hides a complicated query, don't run it twice.
    # See bug 623281.
    current_job = builder.currentjob
    build_job = current_job.specific_job.build

    if builder.failure_count == build_job.failure_count:
        # If the failure count for the builder is the same as the
        # failure count for the job being built, then we cannot
        # tell whether the job or the builder is at fault. The  best
        # we can do is try them both again, and hope that the job
        # runs against a different builder.
        current_job.reset()
        return

    if builder.failure_count > build_job.failure_count:
        # The builder has failed more than the jobs it's been
        # running, so let's disable it and re-schedule the build.
        builder.failBuilder(fail_notes)
        current_job.reset()
    else:
        # The job is the culprit!  Override its status to 'failed'
        # to make sure it won't get automatically dispatched again,
        # and remove the buildqueue request.  The failure should
        # have already caused any relevant slave data to be stored
        # on the build record so don't worry about that here.
        build_job.status = BuildStatus.FAILEDTOBUILD
        builder.currentjob.destroySelf()

        # N.B. We could try and call _handleStatus_PACKAGEFAIL here
        # but that would cause us to query the slave for its status
        # again, and if the slave is non-responsive it holds up the
        # next buildd scan.


class SlaveScanner:
    """A manager for a single builder."""

    # The interval between each poll cycle, in seconds.  We'd ideally
    # like this to be lower but 5 seems a reasonable compromise between
    # responsivity and load on the database server, since in each cycle
    # we can run quite a few queries.
    SCAN_INTERVAL = 5

    def __init__(self, builder_name, logger):
        self.builder_name = builder_name
        self.logger = logger

    def startCycle(self):
        """Scan the builder and dispatch to it or deal with failures."""
        self.loop = LoopingCall(self.singleCycle)
        self.stopping_deferred = self.loop.start(self.SCAN_INTERVAL)
        return self.stopping_deferred

    def stopCycle(self):
        """Terminate the LoopingCall."""
        self.loop.stop()

    def singleCycle(self):
        self.logger.debug("Scanning builder: %s" % self.builder_name)
        d = self.scan()

        d.addErrback(self._scanFailed)
        return d

    def _scanFailed(self, failure):
        """Deal with failures encountered during the scan cycle.

        1. Print the error in the log
        2. Increment and assess failure counts on the builder and job.
        """
        # Make sure that pending database updates are removed as it
        # could leave the database in an inconsistent state (e.g. The
        # job says it's running but the buildqueue has no builder set).
        transaction.abort()

        # If we don't recognise the exception include a stack trace with
        # the error.
        error_message = failure.getErrorMessage()
        if failure.check(
            BuildSlaveFailure, CannotBuild, BuildBehaviorMismatch,
            CannotResumeHost, BuildDaemonError, CannotFetchFile):
            self.logger.info("Scanning failed with: %s" % error_message)
        else:
            self.logger.info("Scanning failed with: %s\n%s" %
                (failure.getErrorMessage(), failure.getTraceback()))

        # Decide if we need to terminate the job or fail the
        # builder.
        try:
            builder = get_builder(self.builder_name)
            builder.gotFailure()
            # XXX: There might not be a current job so check for that
            # first before trying to fail it.
            builder.getCurrentBuildFarmJob().gotFailure()
            self.logger.info(
                "builder failure count: %s, job failure count: %s" % (
                    builder.failure_count,
                    builder.getCurrentBuildFarmJob().failure_count))
            assessFailureCounts(builder, failure.getErrorMessage())
            transaction.commit()
        except:
            # Catastrophic code failure! Not much we can do.
            self.logger.error(
                "Miserable failure when trying to examine failure counts:\n",
                exc_info=True)
            transaction.abort()

    def scan(self):
        """Probe the builder and update/dispatch/collect as appropriate.

        There are several steps to scanning:

        1. If the builder is marked as "ok" then probe it to see what state
            it's in.  This is where lost jobs are rescued if we think the
            builder is doing something that it later tells us it's not,
            and also where the multi-phase abort procedure happens.
            See IBuilder.rescueIfLost, which is called by
            IBuilder.updateStatus().
        2. If the builder is still happy, we ask it if it has an active build
            and then either update the build in Launchpad or collect the
            completed build. (builder.updateBuild)
        3. If the builder is not happy or it was marked as unavailable
            mid-build, we need to reset the job that we thought it had, so
            that the job is dispatched elsewhere.
        4. If the builder is idle and we have another build ready, dispatch
            it.

        :return: A Deferred that fires when the scan is complete, whose
            value is A `BuilderSlave` if we dispatched a job to it, or None.
        """
        # We need to re-fetch the builder object on each cycle as the
        # Storm store is invalidated over transaction boundaries.

        self.builder = get_builder(self.builder_name)

        if self.builder.builderok:
            d = self.builder.updateStatus(self.logger)
        else:
            d = defer.succeed(None)

        def status_updated(ignored):
            # Commit the changes done while possibly rescuing jobs, to
            # avoid holding table locks.
            transaction.commit()

            # See if we think there's an active build on the builder.
            buildqueue = self.builder.getBuildQueue()

            # Scan the slave and get the logtail, or collect the build if
            # it's ready.  Yes, "updateBuild" is a bad name.
            if buildqueue is not None:
                return self.builder.updateBuild(buildqueue)

        def build_updated(ignored):
            # Commit changes done while updating the build, to avoid
            # holding table locks.
            transaction.commit()

            # If the builder is in manual mode, don't dispatch anything.
            if self.builder.manual:
                self.logger.debug(
                    '%s is in manual mode, not dispatching.' %
                    self.builder.name)
                return

            # If the builder is marked unavailable, don't dispatch anything.
            # Additionaly, because builders can be removed from the pool at
            # any time, we need to see if we think there was a build running
            # on it before it was marked unavailable. In this case we reset
            # the build thusly forcing it to get re-dispatched to another
            # builder.

            return self.builder.isAvailable().addCallback(got_available)

        def got_available(available):
            if not available:
                job = self.builder.currentjob
                if job is not None and not self.builder.builderok:
                    self.logger.info(
                        "%s was made unavailable, resetting attached "
                        "job" % self.builder.name)
                    job.reset()
                    transaction.commit()
                return

            # See if there is a job we can dispatch to the builder slave.

            d = self.builder.findAndStartJob()
            def job_started(candidate):
                if self.builder.currentjob is not None:
                    # After a successful dispatch we can reset the
                    # failure_count.
                    self.builder.resetFailureCount()
                    transaction.commit()
                    return self.builder.slave
                else:
                    return None
            return d.addCallback(job_started)

        d.addCallback(status_updated)
        d.addCallback(build_updated)
        return d


class NewBuildersScanner:
    """If new builders appear, create a scanner for them."""

    # How often to check for new builders, in seconds.
    SCAN_INTERVAL = 300

    def __init__(self, manager, clock=None):
        self.manager = manager
        # Use the clock if provided, it's so that tests can
        # advance it.  Use the reactor by default.
        if clock is None:
            clock = reactor
        self._clock = clock
        # Avoid circular import.
        from lp.buildmaster.interfaces.builder import IBuilderSet
        self.current_builders = [
            builder.name for builder in getUtility(IBuilderSet)]

    def stop(self):
        """Terminate the LoopingCall."""
        self.loop.stop()

    def scheduleScan(self):
        """Schedule a callback SCAN_INTERVAL seconds later."""
        self.loop = LoopingCall(self.scan)
        self.loop.clock = self._clock
        self.stopping_deferred = self.loop.start(self.SCAN_INTERVAL)
        return self.stopping_deferred

    def scan(self):
        """If a new builder appears, create a SlaveScanner for it."""
        new_builders = self.checkForNewBuilders()
        self.manager.addScanForBuilders(new_builders)

    def checkForNewBuilders(self):
        """See if any new builders were added."""
        # Avoid circular import.
        from lp.buildmaster.interfaces.builder import IBuilderSet
        new_builders = set(
            builder.name for builder in getUtility(IBuilderSet))
        old_builders = set(self.current_builders)
        extra_builders = new_builders.difference(old_builders)
        return list(extra_builders)


class BuilddManager(service.Service):
    """Main Buildd Manager service class."""

    def __init__(self, clock=None):
        self.builder_slaves = []
        self.logger = self._setupLogger()
        self.new_builders_scanner = NewBuildersScanner(
            manager=self, clock=clock)

    def _setupLogger(self):
        """Set up a 'slave-scanner' logger that redirects to twisted.

        Make it less verbose to avoid messing too much with the old code.
        """
        level = logging.INFO
        logger = logging.getLogger(BUILDD_MANAGER_LOG_NAME)

        # Redirect the output to the twisted log module.
        channel = logging.StreamHandler(log.StdioOnnaStick())
        channel.setLevel(level)
        channel.setFormatter(logging.Formatter('%(message)s'))

        logger.addHandler(channel)
        logger.setLevel(level)
        return logger

    def startService(self):
        """Service entry point, called when the application starts."""

        # Get a list of builders and set up scanners on each one.

        # Avoiding circular imports.
        from lp.buildmaster.interfaces.builder import IBuilderSet
        builder_set = getUtility(IBuilderSet)
        builders = [builder.name for builder in builder_set]
        self.addScanForBuilders(builders)
        self.new_builders_scanner.scheduleScan()

        # Events will now fire in the SlaveScanner objects to scan each
        # builder.

    def stopService(self):
        """Callback for when we need to shut down."""
        # All the SlaveScanner objects need to be halted gracefully.
        deferreds = [slave.stopping_deferred for slave in self.builder_slaves]
        deferreds.append(self.new_builders_scanner.stopping_deferred)

        self.new_builders_scanner.stop()
        for slave in self.builder_slaves:
            slave.stopCycle()

        # The 'stopping_deferred's are called back when the loops are
        # stopped, so we can wait on them all at once here before
        # exiting.
        d = defer.DeferredList(deferreds, consumeErrors=True)
        return d

    def addScanForBuilders(self, builders):
        """Set up scanner objects for the builders specified."""
        for builder in builders:
            slave_scanner = SlaveScanner(builder, self.logger)
            self.builder_slaves.append(slave_scanner)
            slave_scanner.startCycle()

        # Return the slave list for the benefit of tests.
        return self.builder_slaves
