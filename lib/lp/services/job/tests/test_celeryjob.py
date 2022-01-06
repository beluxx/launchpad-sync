# Copyright 2012-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import sys
from time import sleep

from lazr.jobrunner.bin.clear_queues import clear_queues
import six
from testtools.content import text_content

from lp.code.model.branchjob import BranchScanJob
from lp.scripts.helpers import TransactionFreeOperation
from lp.services.database.sqlbase import flush_database_updates
from lp.services.features.testing import FeatureFixture
from lp.services.job.tests import (
    celery_worker,
    drain_celery_queues,
    monitor_celery,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.layers import ZopelessAppServerLayer


class TestRunMissingJobs(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def setUp(self):
        super().setUp()
        from lp.services.job.celeryjob import (
            find_missing_ready,
            run_missing_ready,
            )
        self.find_missing_ready = find_missing_ready
        self.run_missing_ready = run_missing_ready

    def createMissingJob(self):
        job = BranchScanJob.create(self.factory.makeBranch())
        self.addCleanup(drain_celery_queues)
        return job

    def getFMR(self, job_source, expected_len):
        """Get a FindMissingReady object when job queue reaches expected size.

        Fails if the queue never reaches the expected size.
        """
        from lp.services.job.celeryjob import FindMissingReady
        for x in range(600):
            find_missing = FindMissingReady(job_source)
            if len(find_missing.queue_contents) == expected_len:
                return find_missing
            sleep(0.1)
        self.fail('Queue size did not reach %d; still at %d' %
                  (expected_len, len(find_missing.queue_contents)))

    def assertQueueSize(self, app, queues, expected_len):
        """Assert the message queue (eventually) reaches the specified size.

        This can be used to avoid race conditions with RabbitMQ's message
        delivery.
        """
        from lazr.jobrunner.celerytask import list_queued
        for x in range(600):
            actual_len = len(list_queued(app, queues))
            if actual_len == expected_len:
                return
            sleep(0.1)
        self.fail('Queue size did not reach %d; still at %d' %
                  (expected_len, actual_len))

    def addTextDetail(self, name, text):
        self.addDetail(name, text_content(text))

    def test_find_missing_ready(self):
        """A job which is ready but not queued is "missing"."""
        job = self.createMissingJob()
        flush_database_updates()
        self.addTextDetail(
            'job_info', 'job.id: %d, job.job_id: %d' % (job.id, job.job_id))
        find_missing_ready_obj = self.getFMR(BranchScanJob, 0)
        self.assertEqual([job], find_missing_ready_obj.find_missing_ready())
        job.extractJobState()
        job.runViaCelery()
        find_missing_ready_obj = self.getFMR(BranchScanJob, 1)
        missing_ready = find_missing_ready_obj.find_missing_ready()
        try:
            self.assertEqual([], missing_ready)
        except Exception:
            # XXX AaronBentley: 2012-08-01 bug=1031018: Extra diagnostic info
            # to help diagnose this hard-to-reproduce failure.
            self.addTextDetail('queued_job_ids',
                               '%r' % (find_missing_ready_obj.queued_job_ids))
            self.addTextDetail('queue_contents',
                               repr(find_missing_ready_obj.queue_contents))
            self.addTextDetail(
                'missing_ready_job_id', repr([missing.job_id for missing in
                missing_ready]))
            raise
        drain_celery_queues()
        find_missing_ready_obj = self.getFMR(BranchScanJob, 0)
        self.assertEqual([job], find_missing_ready_obj.find_missing_ready())

    def test_run_missing_ready_not_enabled(self):
        """run_missing_ready does nothing if the class isn't enabled."""
        self.createMissingJob()
        with monitor_celery() as responses:
            with dbuser('run_missing_ready'):
                with TransactionFreeOperation.require():
                    self.run_missing_ready.run(_no_init=True)
        self.assertEqual([], responses)

    def test_run_missing_ready(self):
        """run_missing_ready requests the job to run if not scheduled."""
        self.createMissingJob()
        self.useFixture(
            FeatureFixture({'jobs.celery.enabled_classes': 'BranchScanJob'}))
        with monitor_celery() as responses:
            with dbuser('run_missing_ready'):
                with TransactionFreeOperation.require():
                    self.run_missing_ready.run(_no_init=True)
        self.assertEqual(1, len(responses))

    def test_run_missing_ready_does_not_return_results(self):
        """The celerybeat task run_missing_ready does not create a
        result queue."""
        from lp.services.job.tests.celery_helpers import noop
        job_queue_name = 'celerybeat'
        request = self.run_missing_ready.apply_async(
            kwargs={'_no_init': True}, queue=job_queue_name)
        self.assertTrue(request.task_id.startswith('RunMissingReady_'))
        result_queue_name = request.task_id.replace('-', '')
        # Paranoia check: This test intends to prove that a Celery
        # result queue for the task created above will _not_ be created.
        # This would also happen when "with celery_worker()" would do nothing.
        # So let's be sure that a task is queued...
        # Give the system some time to deliver the message
        self.assertQueueSize(self.run_missing_ready.app, [job_queue_name], 1)
        # Wait at most 60 seconds for "celery worker" to start and process
        # the task.
        with celery_worker(job_queue_name):
            # Due to FIFO ordering, this will only return after
            # run_missing_ready has finished.
            noop.apply_async(queue=job_queue_name).wait(60)
        # But now the message has been consumed by "celery worker".
        self.assertQueueSize(self.run_missing_ready.app, [job_queue_name], 0)
        # No result queue was created for the task.
        try:
            real_stdout = sys.stdout
            real_stderr = sys.stderr
            sys.stdout = fake_stdout = six.StringIO()
            sys.stderr = fake_stderr = six.StringIO()
            clear_queues(
                ['script_name', '-c', 'lp.services.job.celeryconfig',
                 result_queue_name])
        finally:
            sys.stdout = real_stdout
            sys.stderr = real_stderr
        fake_stdout = fake_stdout.getvalue()
        fake_stderr = fake_stderr.getvalue()
        self.assertEqual(
            '', fake_stdout,
            "Unexpected output from clear_queues:\n"
            "stdout: %r\n"
            "stderr: %r" % (fake_stdout, fake_stderr))
        self.assertEqual(
            "NOT_FOUND - no queue '%s' in vhost '/'\n" % result_queue_name,
            fake_stderr,
            "Unexpected output from clear_queues:\n"
            "stdout: %r\n"
            "stderr: %r" % (fake_stdout, fake_stderr))
