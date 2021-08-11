# Copyright 2012-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for running jobs via Celery."""


from datetime import (
    datetime,
    timedelta,
    )
from time import sleep
from unittest import mock

import iso8601
from lazr.delegates import delegate_to
from lazr.jobrunner.celerytask import drain_queues
from pytz import UTC
from testtools.matchers import (
    GreaterThan,
    HasLength,
    LessThan,
    MatchesAll,
    MatchesListwise,
    )
import transaction
from zope.interface import implementer

from lp.services.config import config
from lp.services.database.interfaces import IStore
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import (
    IJob,
    IRunnableJob,
    JobStatus,
    )
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.services.job.tests import (
    block_on_job,
    monitor_celery,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.layers import CeleryJobLayer


@implementer(IRunnableJob)
@delegate_to(IJob, context='job')
class TestJob(BaseRunnableJob):
    """A dummy job."""

    config = config.launchpad

    def __init__(self, job_id=None, scheduled_start=None):
        if job_id is not None:
            store = IStore(Job)
            self.job = store.find(Job, id=job_id)[0]
        else:
            self.job = Job(max_retries=2, scheduled_start=scheduled_start)

    def run(self):
        pass

    @classmethod
    def makeInstance(cls, job_id):
        return cls(job_id)

    @classmethod
    def getDBClass(cls):
        return cls


class RetryException(Exception):
    """An exception used as a retry exception in TestJobWithRetryError."""


class TestJobWithRetryError(TestJob):
    """A dummy job."""

    retry_error_types = (RetryException, )

    retry_delay = timedelta(seconds=5)

    def acquireLease(self, duration=10):
        return self.job.acquireLease(duration)

    def storeDateStarted(self):
        existing = self.job.base_json_data or {}
        existing.setdefault('dates_started', [])
        existing['dates_started'].append(self.job.date_started.isoformat())
        self.job.base_json_data = existing

    def run(self):
        """Concoct various retry scenarios."""
        self.storeDateStarted()
        if self.job.attempt_count == 1:
            # First test without a conflicting lease. The job should be
            # rescheduled for 5 seconds (retry_delay) in the future.
            self.job.lease_expires = datetime.now(UTC)
            raise RetryException
        elif self.job.attempt_count == 2:
            # The retry delay is 5 seconds, but the lease is for nearly 10
            # seconds. However, the job releases the lease when it's
            # requeued, so the job will again be rescheduled for 5 seconds
            # (retry_delay) in the future.
            raise RetryException


class TestJobsViaCelery(TestCaseWithFactory):
    """Tests for running jobs via Celery."""

    layer = CeleryJobLayer

    def test_TestJob(self):
        # TestJob can be run via Celery.
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes': 'TestJob'
        }))
        with block_on_job(self):
            job = TestJob()
            job.celeryRunOnCommit()
            job_id = job.job_id
            transaction.commit()
        store = IStore(Job)
        dbjob = store.find(Job, id=job_id)[0]
        self.assertEqual(JobStatus.COMPLETED, dbjob.status)

    def test_scheduled_start(self):
        # Submit four jobs: one in the past, one in the far future, one
        # in 10 seconds, and one at any time.  Wait up to a minute and
        # ensure that the correct three have completed, and that they
        # completed in the expected order.
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes': 'TestJob'
        }))
        now = datetime.now(UTC)
        job_past = TestJob(scheduled_start=now - timedelta(seconds=60))
        job_past.celeryRunOnCommit()
        self.assertTrue(job_past.is_runnable)
        job_forever = TestJob(scheduled_start=now + timedelta(seconds=600))
        job_forever.celeryRunOnCommit()
        self.assertFalse(job_forever.is_runnable)
        job_future = TestJob(scheduled_start=now + timedelta(seconds=10))
        job_future.celeryRunOnCommit()
        self.assertFalse(job_future.is_runnable)
        job_whenever = TestJob(scheduled_start=None)
        job_whenever.celeryRunOnCommit()
        self.assertTrue(job_whenever.is_runnable)
        transaction.commit()

        count = 0
        while (count < 300
                and (job_past.is_pending or job_future.is_pending
                     or job_whenever.is_pending)):
            sleep(0.2)
            count += 1
            transaction.abort()

        self.assertEqual(JobStatus.COMPLETED, job_past.status)
        self.assertEqual(JobStatus.COMPLETED, job_future.status)
        self.assertEqual(JobStatus.COMPLETED, job_whenever.status)
        self.assertEqual(JobStatus.WAITING, job_forever.status)
        self.assertThat(
            job_future.date_started, GreaterThan(job_past.date_started))

    def test_jobs_with_retry_exceptions_are_queued_again(self):
        # A job that raises a retry error is automatically queued
        # and executed again.
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes': 'TestJobWithRetryError'
        }))

        # Set scheduled_start on the job to ensure that retry delays
        # override it.
        job = TestJobWithRetryError(
            scheduled_start=datetime.now(UTC) + timedelta(seconds=1))
        job.celeryRunOnCommit()
        transaction.commit()

        count = 0
        while count < 300 and job.is_pending:
            # We have a maximum wait of one minute.  We should not get
            # anywhere close to that on developer machines (10 seconds was
            # working fine), but when the test suite is run in parallel we
            # can need a lot more time (see bug 1007576).
            sleep(0.2)
            count += 1
            transaction.abort()

        # Collect the start times recorded by the job.
        dates_started = [
            iso8601.parse_date(d)
            for d in job.job.base_json_data['dates_started']]

        # The first attempt's lease is set to the end of the job, so the
        # second attempt should start roughly 5 seconds after the first. The
        # third attempt should start roughly 5 seconds after the second.
        self.assertThat(dates_started, HasLength(3))
        self.assertThat(dates_started,
            MatchesListwise([
                MatchesAll(),
                MatchesAll(
                    GreaterThan(dates_started[0] + timedelta(seconds=4)),
                    LessThan(dates_started[0] + timedelta(seconds=8))),
                MatchesAll(
                    GreaterThan(dates_started[1] + timedelta(seconds=4)),
                    LessThan(dates_started[1] + timedelta(seconds=8))),
                ]))
        self.assertEqual(3, job.attempt_count)
        self.assertEqual(JobStatus.COMPLETED, job.status)

    def test_without_rabbitmq(self):
        # If no RabbitMQ host is configured, the job is not run via Celery.
        self.pushConfig('rabbitmq', host='none')
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes': 'TestJob'
        }))
        with monitor_celery() as responses:
            job = TestJob()
            job.celeryRunOnCommit()
            job_id = job.job_id
            transaction.commit()
        self.assertEqual([], responses)
        store = IStore(Job)
        dbjob = store.find(Job, id=job_id)[0]
        self.assertEqual(JobStatus.WAITING, dbjob.status)


class TestTimeoutJob(TestJob):

    def storeDateStarted(self):
        existing = self.job.base_json_data or {}
        existing.setdefault('dates_started', [])
        existing['dates_started'].append(self.job.date_started.isoformat())
        self.job.base_json_data = existing

    def run(self):
        """Concoct various retry scenarios."""

        if self.job.attempt_count == 1:
            from celery.exceptions import SoftTimeLimitExceeded
            raise SoftTimeLimitExceeded


class TestCeleryLaneFallback(TestCaseWithFactory):

    layer = CeleryJobLayer

    def test_fallback_to_slow_lane(self):
        # Check that we re-queue a slow task into the correct queue
        from lp.services.job.celeryjob import celery_app
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes': 'TestTimeoutJob'}))

        with block_on_job(self):
            job = TestTimeoutJob()
            job.celeryRunOnCommit()
            transaction.commit()

        message_drain = mock.Mock()

        drain_queues(
            celery_app,
            ['launchpad_job', 'launchpad_job_slow'], callbacks=[message_drain])

        self.assertEqual(1, job.attempt_count)
        self.assertEqual(1, message_drain.call_count)
        self.assertEqual(
            'launchpad_job_slow',
            message_drain.call_args[0][1].delivery_info['routing_key'])
