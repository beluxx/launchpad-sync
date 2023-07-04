# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Facilities for running Jobs."""

__all__ = [
    "BaseJobRunner",
    "BaseRunnableJob",
    "BaseRunnableJobSource",
    "celery_enabled",
    "JobRunner",
    "JobRunnerProcess",
    "QuietAMPConnector",
    "TwistedJobRunner",
    "VirtualEnvProcessStarter",
]


import contextlib
import logging
import os
import sys
from calendar import timegm
from datetime import datetime, timedelta, timezone
from resource import RLIMIT_AS, getrlimit, setrlimit
from signal import SIGHUP, signal
from uuid import uuid4

import transaction
from ampoule import child, main, pool
from lazr.delegates import delegate_to
from lazr.jobrunner.jobrunner import JobRunner as LazrJobRunner
from lazr.jobrunner.jobrunner import LeaseHeld
from storm.exceptions import LostObjectError
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, succeed
from twisted.protocols import amp
from twisted.python import failure, log
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.services import scripts
from lp.services.config import config, dbconfig
from lp.services.database.policy import DatabaseBlockedPolicy
from lp.services.features import getFeatureFlag
from lp.services.job.interfaces.job import IJob, IRunnableJob
from lp.services.mail.sendmail import (
    MailController,
    set_immediate_mail_delivery,
)
from lp.services.messaging import rabbit
from lp.services.statsd.interfaces.statsd_client import IStatsdClient
from lp.services.timeout import (
    get_default_timeout_function,
    set_default_timeout_function,
)
from lp.services.twistedsupport import run_reactor
from lp.services.webapp import errorlog
from lp.services.webapp.adapter import (
    clear_request_started,
    set_request_started,
)


class BaseRunnableJobSource:
    """Base class for job sources for the job runner."""

    memory_limit = None

    @staticmethod
    @contextlib.contextmanager
    def contextManager():
        yield


class JobState:
    """Extract some state from a job.

    This is just enough to allow `BaseRunnableJob.runViaCelery` to run
    without database access.
    """

    def __init__(self, runnable_job):
        self.job_id = runnable_job.job.id
        self.task_id = runnable_job.taskId()
        self.scheduled_start = runnable_job.scheduled_start
        self.lease_expires = runnable_job.lease_expires


@delegate_to(IJob, context="job")
class BaseRunnableJob(BaseRunnableJobSource):
    """Base class for jobs to be run via JobRunner.

    Derived classes should implement IRunnableJob, which requires implementing
    IRunnableJob.run.  They should have a `job` member which implements IJob.

    Subclasses may provide getOopsRecipients, to send mail about oopses.
    If so, they should also provide getOperationDescription.
    """

    user_error_types = ()

    retry_error_types = ()

    task_queue = "launchpad_job"

    celery_responses = None

    lease_duration = timedelta(minutes=5)
    retry_delay = timedelta(minutes=10)
    soft_time_limit = timedelta(minutes=5)

    timeline_detail_filter = None

    job_state = None

    # We redefine __eq__ and __ne__ here to prevent the security proxy
    # from mucking up our comparisons in tests and elsewhere.
    def __eq__(self, job):
        naked_job = removeSecurityProxy(job)
        return (
            self.__class__ is naked_job.__class__
            and self.__dict__ == naked_job.__dict__
        )

    def __ne__(self, job):
        return not (self == job)

    def __hash__(self):
        return hash(tuple([self.__class__] + sorted(self.__dict__.items())))

    def __lt__(self, job):
        naked_job = removeSecurityProxy(job)
        if self.__class__ is naked_job.__class__:
            return self.__dict__ < naked_job.__dict__
        else:
            return NotImplemented

    def getOopsRecipients(self):
        """Return a list of email-ids to notify about oopses."""
        return self.getErrorRecipients()

    def getOperationDescription(self):
        return "unspecified operation"

    def getErrorRecipients(self):
        """Return a list of email-ids to notify about user errors."""
        return []

    def getOopsMailController(self, oops_id):
        """Return a MailController for notifying people about oopses.

        Return None if there is no-one to notify.
        """
        recipients = self.getOopsRecipients()
        if len(recipients) == 0:
            return None
        subject = "Launchpad internal error"
        body = (
            "Launchpad encountered an internal error during the following"
            " operation: %s.  It was logged with id %s.  Sorry for the"
            " inconvenience." % (self.getOperationDescription(), oops_id)
        )
        from_addr = config.canonical.noreply_from_address
        return MailController(from_addr, recipients, subject, body)

    def getUserErrorMailController(self, e):
        """Return a MailController for notifying about user errors.

        Return None if there is no-one to notify.
        """
        recipients = self.getErrorRecipients()
        if len(recipients) == 0:
            return None
        subject = "Launchpad error while %s" % self.getOperationDescription()
        body = (
            "Launchpad encountered an error during the following"
            " operation: %s.  %s" % (self.getOperationDescription(), str(e))
        )
        from_addr = config.canonical.noreply_from_address
        return MailController(from_addr, recipients, subject, body)

    def notifyOops(self, oops):
        """Report this oops."""
        ctrl = self.getOopsMailController(oops["id"])
        if ctrl is not None:
            ctrl.send()

    def getOopsVars(self):
        """See `IRunnableJob`."""
        return [("job_id", self.job.id)]

    def notifyUserError(self, e):
        """See `IRunnableJob`."""
        ctrl = self.getUserErrorMailController(e)
        if ctrl is not None:
            ctrl.send()

    def makeOopsReport(self, oops_config, info):
        """Generate an OOPS report using the given OOPS configuration."""
        return oops_config.create(context=dict(exc_info=info))

    def acquireLease(self, duration=None):
        if duration is None:
            duration = self.lease_duration.total_seconds()
        self.job.acquireLease(duration)

    def taskId(self):
        """Return a task ID that gives a clue what this job is about.

        Though we intend to drop the result return by a Celery job
        (in the sense that we don't care what
        lazr.jobrunner.celerytask.RunJob.run() returns), we might
        accidentally create result queues, for example, when a job fails.
        The messages stored in these queues are often not very specific,
        the queues names are just the IDs of the task, which are by
        default just strings returned by Celery's uuid() function.

        If we put the job's class name and the job ID into the task ID,
        we have better chances to figure out what went wrong than by just
        look for example at a message like

            {'status': 'FAILURE',
            'traceback': None,
            'result': SoftTimeLimitExceeded(1,),
            'task_id': 'cba7d07b-37fe-4f1d-a5f6-79ad7c30222f'}
        """
        return "%s_%s_%s" % (self.__class__.__name__, self.job_id, uuid4())

    def runViaCelery(self, ignore_result=False):
        """Request that this job be run via celery."""
        # Avoid importing from lp.services.job.celeryjob where not needed, to
        # avoid configuring Celery when Rabbit is not configured.
        from lp.services.job.celeryjob import (
            celery_run_job,
            celery_run_job_ignore_result,
        )

        if ignore_result:
            task = celery_run_job_ignore_result
        else:
            task = celery_run_job
        db_class = self.getDBClass()
        ujob_id = (
            self.job_state.job_id,
            db_class.__module__,
            db_class.__name__,
        )
        eta = self.job_state.scheduled_start
        # Don't schedule the job while its lease is still held, or
        # celery will skip it.
        if self.job_state.lease_expires is not None and (
            eta is None or eta < self.job_state.lease_expires
        ):
            eta = self.job_state.lease_expires
        return task.apply_async(
            (ujob_id, self.config.dbuser),
            queue=self.task_queue,
            eta=eta,
            soft_time_limit=self.soft_time_limit.total_seconds(),
            task_id=self.job_state.task_id,
        )

    def getDBClass(self):
        return self.context.__class__

    def extractJobState(self):
        """Hook function to call before starting a commit."""
        self.job_state = JobState(self)

    def celeryCommitHook(self, succeeded):
        """Hook function to call when a commit completes.

        extractJobState must have been run first.
        """
        if self.job_state is None:
            raise AssertionError(
                "extractJobState was not run before celeryCommitHook."
            )
        try:
            with DatabaseBlockedPolicy():
                if succeeded:
                    ignore_result = bool(
                        BaseRunnableJob.celery_responses is None
                    )
                    response = self.runViaCelery(ignore_result)
                    if not ignore_result:
                        BaseRunnableJob.celery_responses.append(response)
        finally:
            self.job_state = None

    def celeryRunOnCommit(self):
        """Configure transaction so that commit runs this job via Celery."""
        if not rabbit.is_configured() or not celery_enabled(
            self.__class__.__name__
        ):
            return
        current = transaction.get()
        current.addBeforeCommitHook(self.extractJobState)
        current.addAfterCommitHook(self.celeryCommitHook)

    def queue(self, manage_transaction=False, abort_transaction=False):
        """See `IJob`."""
        if self.job.attempt_count > 0:
            self.job.scheduled_start = (
                datetime.now(timezone.utc) + self.retry_delay
            )
        # If we're aborting the transaction, we probably don't want to
        # start the task again
        if manage_transaction and abort_transaction:
            commit_hook = None
        else:
            commit_hook = self.celeryRunOnCommit
        self.job.queue(
            manage_transaction, abort_transaction, add_commit_hook=commit_hook
        )

    def start(self, manage_transaction=False):
        """See `IJob`."""
        self.job.start(manage_transaction=manage_transaction)
        statsd = getUtility(IStatsdClient)
        statsd.incr(
            "job.start_count", labels={"type": self.__class__.__name__}
        )

    def complete(self, manage_transaction=False):
        """See `IJob`."""
        self.job.complete(manage_transaction=manage_transaction)
        statsd = getUtility(IStatsdClient)
        statsd.incr(
            "job.complete_count", labels={"type": self.__class__.__name__}
        )

    def fail(self, manage_transaction=False):
        """See `IJob`."""
        # The job may have failed due to an error in an SQL statement, and
        # `self.job` may not have been loaded since it was invalidated by
        # the commit in `BaseRunnableJob.start`.  To avoid hitting an
        # `InFailedSqlTransaction` exception here, we manage the transaction
        # manually so that the rollback happens before trying to load
        # `self.job`.
        if manage_transaction:
            transaction.abort()
        self.job.fail()
        if manage_transaction:
            transaction.commit()
        statsd = getUtility(IStatsdClient)
        statsd.incr("job.fail_count", labels={"type": self.__class__.__name__})


class BaseJobRunner(LazrJobRunner):
    """Runner of Jobs."""

    def __init__(self, logger=None, error_utility=None):
        self.oops_ids = []
        if error_utility is None:
            self.error_utility = errorlog.globalErrorUtility
        else:
            self.error_utility = error_utility
        super().__init__(
            logger,
            oops_config=self.error_utility._oops_config,
            oopsMessage=self.error_utility.oopsMessage,
        )

    def acquireLease(self, job):
        self.logger.debug(
            "Trying to acquire lease for job in state %s" % (job.status.title,)
        )
        try:
            job.acquireLease()
        except LeaseHeld:
            self.logger.info(
                "Could not acquire lease for %s" % self.job_str(job)
            )
            self.incomplete_jobs.append(job)
            return False
        return True

    def runJob(self, job, fallback):
        original_timeout_function = get_default_timeout_function()
        if job.lease_expires is not None:
            set_default_timeout_function(lambda: job.getTimeout())
        try:
            super().runJob(IRunnableJob(job), fallback)
        finally:
            set_default_timeout_function(original_timeout_function)

    def runJobHandleError(self, job, fallback=None):
        set_request_started(
            enable_timeout=False, detail_filter=job.timeline_detail_filter
        )
        try:
            return super().runJobHandleError(job, fallback=fallback)
        finally:
            clear_request_started()

    def userErrorTypes(self, job):
        return removeSecurityProxy(job).user_error_types

    def retryErrorTypes(self, job):
        return removeSecurityProxy(job).retry_error_types

    def _doOops(self, job, info):
        """Report an OOPS for the provided job and info.

        :param job: The IRunnableJob whose run failed.
        :param info: The standard sys.exc_info() value.
        :return: the Oops that was reported.
        """
        oops = self.error_utility.raising(info)
        job.notifyOops(oops)
        self._logOopsId(oops["id"])
        return oops

    def _logOopsId(self, oops_id):
        """Report oopses by id to the log."""
        if self.logger is not None:
            self.logger.info("Job resulted in OOPS: %s" % oops_id)
        self.oops_ids.append(oops_id)


class JobRunner(BaseJobRunner):
    def __init__(self, jobs, logger=None):
        BaseJobRunner.__init__(self, logger=logger)
        self.jobs = jobs

    @classmethod
    def fromReady(cls, job_class, logger=None):
        """Return a job runner for all ready jobs of a given class."""
        return cls(job_class.iterReady(), logger)

    @classmethod
    def runFromSource(cls, job_source, dbuser, logger):
        """Run all ready jobs provided by the specified source.

        The dbuser parameter is ignored.
        """
        with removeSecurityProxy(job_source.contextManager()):
            logger.info("Running synchronously.")
            runner = cls.fromReady(job_source, logger)
            runner.runAll()
        return runner

    def runAll(self):
        """Run all the Jobs for this JobRunner."""
        for job in self.jobs:
            job = IRunnableJob(job)
            if not self.acquireLease(job):
                continue
            # Commit transaction to clear the row lock.
            transaction.commit()
            self.runJobHandleError(job)


class RunJobCommand(amp.Command):
    arguments = [(b"job_id", amp.Integer())]
    response = [(b"success", amp.Integer()), (b"oops_id", amp.Unicode())]


def import_source(job_source_name):
    """Return the IJobSource specified by its full name."""
    module, name = job_source_name.rsplit(".", 1)
    source_module = __import__(module, fromlist=[name])
    return getattr(source_module, name)


class JobRunnerProcess(child.AMPChild):
    """Base class for processes that run jobs."""

    def __init__(self, job_source_name, dbuser):
        child.AMPChild.__init__(self)
        self.job_source = import_source(job_source_name)
        self.context_manager = self.job_source.contextManager()
        # icky, but it's really a global value anyhow.
        self.__class__.dbuser = dbuser

    @classmethod
    def __enter__(cls):
        def handler(signum, frame):
            # We raise an exception **and** schedule a call to exit the
            # process hard.  This is because we cannot rely on the exception
            # being raised during useful code.  Sometimes, it will be raised
            # while the reactor is looping, which means that it will be
            # ignored.
            #
            # If the exception is raised during the actual job, then we'll get
            # a nice traceback indicating what timed out, and that will be
            # logged as an OOPS.
            #
            # Regardless of where the exception is raised, we'll hard exit the
            # process and have a TimeoutError OOPS logged, although that will
            # have a crappy traceback. See the job_raised callback in
            # TwistedJobRunner.runJobInSubprocess for the other half of that.
            reactor.callFromThread(
                reactor.callLater, 0, os._exit, TwistedJobRunner.TIMEOUT_CODE
            )
            raise TimeoutError

        scripts.execute_zcml_for_scripts(use_web_security=False)
        signal(SIGHUP, handler)
        dbconfig.override(dbuser=cls.dbuser, isolation_level="read_committed")
        # XXX wgrant 2011-09-24 bug=29744: initZopeless used to do this.
        # Should be removed from callsites verified to not need it.
        set_immediate_mail_delivery(True)

    @staticmethod
    def __exit__(exc_type, exc_val, exc_tb):
        pass

    def makeConnection(self, transport):
        """The Job context is entered on connect."""
        child.AMPChild.makeConnection(self, transport)
        self.context_manager.__enter__()

    def connectionLost(self, reason):
        """The Job context is left on disconnect."""
        self.context_manager.__exit__(None, None, None)
        child.AMPChild.connectionLost(self, reason)

    @RunJobCommand.responder
    def runJobCommand(self, job_id):
        """Run a job from this job_source according to its job id."""
        runner = BaseJobRunner()
        job = self.job_source.get(job_id)
        if self.job_source.memory_limit is not None:
            soft_limit, hard_limit = getrlimit(RLIMIT_AS)
            if soft_limit != self.job_source.memory_limit:
                limits = (self.job_source.memory_limit, hard_limit)
                setrlimit(RLIMIT_AS, limits)
        oops = runner.runJobHandleError(job)
        if oops is None:
            oops_id = ""
        else:
            oops_id = oops["id"]
        return {"success": len(runner.completed_jobs), "oops_id": oops_id}


class VirtualEnvProcessStarter(main.ProcessStarter):
    """A `ProcessStarter` that sets up Launchpad's virtualenv correctly.

    `ampoule.main` doesn't make it very easy to use `env/bin/python` rather
    than the bare `sys.executable`; we have to clone-and-hack the innards of
    `ProcessStarter.startPythonProcess`.  (The alternative would be to use
    `sys.executable` with the `-S` option and then `import _pythonpath`, but
    `ampoule.main` also makes it hard to insert `-S` at the right place in
    the command line.)

    On the other hand, the cloned-and-hacked version can be much simpler,
    since we don't need to worry about PYTHONPATH; entering the virtualenv
    correctly will deal with everything that we care about.
    """

    @property
    def _executable(self):
        return os.path.join(config.root, "env", "bin", "python")

    def startPythonProcess(self, prot, *args):
        env = self.env.copy()
        args = (self._executable, "-c", self.bootstrap) + self.args + args
        # The childFDs variable is needed because sometimes child processes
        # misbehave and use stdout to output stuff that should really go to
        # stderr.
        reactor.spawnProcess(
            prot,
            self._executable,
            args,
            env,
            self.path,
            self.uid,
            self.gid,
            self.usePTY,
            childFDs={0: "w", 1: "r", 2: "r", 3: "w", 4: "r"},
        )
        return prot.amp, prot.finished


class QuietAMPConnector(main.AMPConnector):
    """An `AMPConnector` that logs stderr output more quietly."""

    def errReceived(self, data):
        for line in data.strip().splitlines():
            # Unlike the default implementation, we log this at INFO rather
            # than ERROR.  Launchpad generates OOPSes for anything at
            # WARNING or above; we still want to do that if a child process
            # exits fatally, but not if it just writes something to stderr.
            main.log.info("FROM {n}: {l}", n=self.name, l=line)


class TwistedJobRunner(BaseJobRunner):
    """Run Jobs via twisted."""

    TIMEOUT_CODE = 42

    def __init__(self, job_source, dbuser, logger=None, error_utility=None):
        env = {"PATH": os.environ["PATH"]}
        if "LPCONFIG" in os.environ:
            env["LPCONFIG"] = os.environ["LPCONFIG"]
        starter = VirtualEnvProcessStarter(env=env)
        starter.connectorFactory = QuietAMPConnector
        super().__init__(logger, error_utility)
        self.job_source = job_source
        self.import_name = "%s.%s" % (
            removeSecurityProxy(job_source).__module__,
            job_source.__name__,
        )
        self.pool = pool.ProcessPool(
            JobRunnerProcess,
            ampChildArgs=[self.import_name, str(dbuser)],
            starter=starter,
            min=0,
            timeout_signal=SIGHUP,
        )

    def runJobInSubprocess(self, job):
        """Run the job_class with the specified id in the process pool.

        :return: a Deferred that fires when the job has completed.
        """
        job = IRunnableJob(job)
        if not self.acquireLease(job):
            return succeed(None)
        # Commit transaction to clear the row lock.
        transaction.commit()
        job_id = job.id
        deadline = timegm(job.lease_expires.timetuple())

        # Log the job class and database ID for debugging purposes.
        self.logger.info("Running %s." % self.job_str(job))
        self.logger.debug(
            "Running %s, lease expires %s",
            self.job_str(job),
            job.lease_expires,
        )
        deferred = self.pool.doWork(
            RunJobCommand, job_id=job_id, _deadline=deadline
        )

        def update(response):
            if response is None:
                self.incomplete_jobs.append(job)
                self.logger.debug("No response for %s", self.job_str(job))
                return
            if response["success"]:
                self.completed_jobs.append(job)
                self.logger.debug("Finished %s", self.job_str(job))
            else:
                self.incomplete_jobs.append(job)
                self.logger.debug("Incomplete %s", self.job_str(job))
                # Kill the worker that experienced a failure; this only
                # works because there's a single worker.
                self.pool.stopAWorker()
            if response["oops_id"] != "":
                self._logOopsId(response["oops_id"])

        def job_raised(failure):
            try:
                exit_code = getattr(failure.value, "exitCode", None)
                if exit_code == self.TIMEOUT_CODE:
                    # The process ended with the error code that we have
                    # arbitrarily chosen to indicate a timeout. Rather than log
                    # that error (ProcessDone), we log a TimeoutError instead.
                    self._logTimeout(job)
                else:
                    info = (failure.type, failure.value, failure.tb)
                    oops = self._doOops(job, info)
                    self._logOopsId(oops["id"])
            except LostObjectError:
                # The job may have been deleted, so we can ignore this error.
                pass
            else:
                self.incomplete_jobs.append(job)

        deferred.addCallbacks(update, job_raised)
        return deferred

    def _logTimeout(self, job):
        try:
            raise TimeoutError
        except TimeoutError:
            oops = self._doOops(job, sys.exc_info())
            self._logOopsId(oops["id"])

    @inlineCallbacks
    def runAll(self):
        """Run all ready jobs."""
        self.pool.start()
        try:
            try:
                job = None
                for job in self.job_source.iterReady():
                    yield self.runJobInSubprocess(job)
                if job is None:
                    self.logger.info("No jobs to run.")
                self.terminated()
            except BaseException:
                self.failed(failure.Failure())
        except BaseException:
            self.terminated()
            raise

    def terminated(self, ignored=None):
        """Callback to stop the processpool and reactor."""
        deferred = self.pool.stop()
        deferred.addBoth(lambda ignored: reactor.stop())

    def failed(self, failure):
        """Callback for when the job fails."""
        failure.printTraceback()
        self.terminated()

    @classmethod
    def runFromSource(cls, job_source, dbuser, logger, _log_twisted=False):
        """Run all ready jobs provided by the specified source.

        The dbuser parameter is not ignored.
        :param _log_twisted: For debugging: If True, emit verbose Twisted
            messages to stderr.
        """
        logger.info("Running through Twisted.")
        if _log_twisted:
            logging.getLogger().setLevel(0)
            logger_object = logging.getLogger("twistedjobrunner")
            handler = logging.StreamHandler(sys.stderr)
            logger_object.addHandler(handler)
            observer = log.PythonLoggingObserver(loggerName="twistedjobrunner")
            log.startLoggingWithObserver(observer.emit)
        runner = cls(job_source, dbuser, logger)
        reactor.callWhenRunning(runner.runAll)
        run_reactor()
        return runner


class TimeoutError(Exception):
    def __init__(self):
        Exception.__init__(self, "Job ran too long.")


def celery_enabled(class_name):
    """Determine whether a given class is configured to run via Celery.

    The name of a BaseRunnableJob must be specified.
    """
    flag = getFeatureFlag("jobs.celery.enabled_classes")
    if flag is None:
        return False
    return class_name in flag.split(" ")
