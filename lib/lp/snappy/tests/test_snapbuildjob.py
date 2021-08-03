# Copyright 2016-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for snap build jobs."""

__metaclass__ = type

from datetime import timedelta

from fixtures import FakeLogger
import six
from testtools.matchers import (
    Equals,
    Is,
    MatchesDict,
    MatchesListwise,
    MatchesStructure,
    )
import transaction
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import BuildStatus
from lp.services.config import config
from lp.services.database.interfaces import IStore
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.runner import JobRunner
from lp.services.webapp.publisher import canonical_url
from lp.services.webhooks.testing import LogsScheduledWebhooks
from lp.snappy.interfaces.snap import SNAP_TESTING_FLAGS
from lp.snappy.interfaces.snapbuildjob import (
    ISnapBuildJob,
    ISnapStoreUploadJob,
    )
from lp.snappy.interfaces.snapstoreclient import (
    BadRefreshResponse,
    ISnapStoreClient,
    ScanFailedResponse,
    UnauthorizedUploadResponse,
    UploadFailedResponse,
    UploadNotScannedYetResponse,
    )
from lp.snappy.model.snapbuild import SnapBuild
from lp.snappy.model.snapbuildjob import (
    SnapBuildJob,
    SnapBuildJobType,
    SnapStoreUploadJob,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.fakemethod import FakeMethod
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.testing.mail_helpers import pop_notifications


def run_isolated_jobs(jobs):
    """Run a sequence of jobs, ensuring transaction isolation.

    We abort the transaction after each job to make sure that there is no
    relevant uncommitted work.
    """
    for job in jobs:
        JobRunner([job]).runAll()
        transaction.abort()


@implementer(ISnapStoreClient)
class FakeSnapStoreClient:

    def __init__(self):
        self.upload = FakeMethod()
        self.checkStatus = FakeMethod()
        self.listChannels = FakeMethod(result=[])


class TestSnapBuildJob(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapBuildJob, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_provides_interface(self):
        # `SnapBuildJob` objects provide `ISnapBuildJob`.
        snapbuild = self.factory.makeSnapBuild()
        self.assertProvides(
            SnapBuildJob(snapbuild, SnapBuildJobType.STORE_UPLOAD, {}),
            ISnapBuildJob)


class TestSnapStoreUploadJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestSnapStoreUploadJob, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))
        self.status_url = "http://sca.example/dev/api/snaps/1/builds/1/status"
        self.store_url = "http://sca.example/dev/click-apps/1/rev/1/"

    def test_provides_interface(self):
        # `SnapStoreUploadJob` objects provide `ISnapStoreUploadJob`.
        snapbuild = self.factory.makeSnapBuild()
        job = SnapStoreUploadJob.create(snapbuild)
        self.assertProvides(job, ISnapStoreUploadJob)

    def test___repr__(self):
        # `SnapStoreUploadJob` objects have an informative __repr__.
        snapbuild = self.factory.makeSnapBuild()
        job = SnapStoreUploadJob.create(snapbuild)
        self.assertEqual(
            "<SnapStoreUploadJob for ~%s/+snap/%s/+build/%d>" % (
                snapbuild.snap.owner.name, snapbuild.snap.name, snapbuild.id),
            repr(job))

    def makeSnapBuild(self, **kwargs):
        # Make a build with a builder and a webhook.
        snapbuild = self.factory.makeSnapBuild(
            builder=self.factory.makeBuilder(), **kwargs)
        snapbuild.updateStatus(BuildStatus.FULLYBUILT)
        self.factory.makeWebhook(
            target=snapbuild.snap, event_types=["snap:build:0.1"])
        return snapbuild

    def assertWebhookDeliveries(self, snapbuild,
                                expected_store_upload_statuses, logger):
        hook = snapbuild.snap.webhooks.one()
        deliveries = list(hook.deliveries)
        deliveries.reverse()
        expected_payloads = [{
            "snap_build": Equals(
                canonical_url(snapbuild, force_local_path=True)),
            "action": Equals("status-changed"),
            "snap": Equals(
                canonical_url(snapbuild.snap, force_local_path=True)),
            "build_request": Is(None),
            "status": Equals("Successfully built"),
            "store_upload_status": Equals(expected),
            } for expected in expected_store_upload_statuses]
        matchers = [
            MatchesStructure(
                event_type=Equals("snap:build:0.1"),
                payload=MatchesDict(expected_payload))
            for expected_payload in expected_payloads]
        self.assertThat(deliveries, MatchesListwise(matchers))
        with dbuser(config.IWebhookDeliveryJobSource.dbuser):
            for delivery in deliveries:
                self.assertEqual(
                    "<WebhookDeliveryJob for webhook %d on %r>" % (
                        hook.id, hook.target),
                    repr(delivery))
            self.assertThat(
                logger.output, LogsScheduledWebhooks([
                    (hook, "snap:build:0.1", MatchesDict(expected_payload))
                    for expected_payload in expected_payloads]))

    def test_run(self):
        # The job uploads the build to the store and records the store URL
        # and revision.
        logger = self.useFixture(FakeLogger())
        snapbuild = self.makeSnapBuild()
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.result = (self.store_url, 1)
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertEqual(self.store_url, job.store_url)
        self.assertEqual(1, job.store_revision)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())
        self.assertWebhookDeliveries(
            snapbuild, ["Pending", "Uploaded"], logger)

    def test_run_failed(self):
        # A failed run sets the store upload status to FAILED.
        logger = self.useFixture(FakeLogger())
        snapbuild = self.makeSnapBuild()
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.failure = ValueError("An upload failure")
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertIsNone(job.store_revision)
        self.assertEqual("An upload failure", job.error_message)
        self.assertEqual([], pop_notifications())
        self.assertWebhookDeliveries(
            snapbuild, ["Pending", "Failed to upload"], logger)

    def test_run_unauthorized_notifies(self):
        # A run that gets 401 from the store sends mail.
        logger = self.useFixture(FakeLogger())
        requester = self.factory.makePerson(name="requester")
        requester_team = self.factory.makeTeam(
            owner=requester, name="requester-team", members=[requester])
        snapbuild = self.makeSnapBuild(
            requester=requester_team, name="test-snap", owner=requester_team)
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.failure = UnauthorizedUploadResponse(
            "Authorization failed.")
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertIsNone(job.store_revision)
        self.assertEqual("Authorization failed.", job.error_message)
        [notification] = pop_notifications()
        self.assertEqual(
            config.canonical.noreply_from_address, notification["From"])
        self.assertEqual(
            "Requester <%s>" % requester.preferredemail.email,
            notification["To"])
        subject = notification["Subject"].replace("\n ", " ")
        self.assertEqual("Store authorization failed for test-snap", subject)
        self.assertEqual(
            "Requester @requester-team",
            notification["X-Launchpad-Message-Rationale"])
        self.assertEqual(
            requester_team.name, notification["X-Launchpad-Message-For"])
        self.assertEqual(
            "snap-build-upload-unauthorized",
            notification["X-Launchpad-Notification-Type"])
        body, footer = six.ensure_text(
            notification.get_payload(decode=True)).split("\n-- \n")
        self.assertIn(
            "http://launchpad.test/~requester-team/+snap/test-snap/+authorize",
            body)
        self.assertEqual(
            "http://launchpad.test/~requester-team/+snap/test-snap/+build/%d\n"
            "Your team Requester Team is the requester of the build.\n" %
            snapbuild.id, footer)
        self.assertWebhookDeliveries(
            snapbuild, ["Pending", "Failed to upload"], logger)

    def test_run_502_retries(self):
        # A run that gets a 502 error from the store schedules itself to be
        # retried.
        logger = self.useFixture(FakeLogger())
        snapbuild = self.makeSnapBuild()
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.failure = UploadFailedResponse(
            "Proxy error", can_retry=True)
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertIsNone(job.store_revision)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())
        self.assertEqual(JobStatus.WAITING, job.job.status)
        self.assertWebhookDeliveries(snapbuild, ["Pending"], logger)
        # Try again.  The upload part of the job is retried, and this time
        # it succeeds.
        job.scheduled_start = None
        client.upload.calls = []
        client.upload.failure = None
        client.upload.result = self.status_url
        client.checkStatus.result = (self.store_url, 1)
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertEqual(self.store_url, job.store_url)
        self.assertEqual(1, job.store_revision)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())
        self.assertEqual(JobStatus.COMPLETED, job.job.status)
        self.assertWebhookDeliveries(
            snapbuild, ["Pending", "Uploaded"], logger)

    def test_run_refresh_failure_notifies(self):
        # A run that gets a failure when trying to refresh macaroons sends
        # mail.
        logger = self.useFixture(FakeLogger())
        requester = self.factory.makePerson(name="requester")
        requester_team = self.factory.makeTeam(
            owner=requester, name="requester-team", members=[requester])
        snapbuild = self.makeSnapBuild(
            requester=requester_team, name="test-snap", owner=requester_team)
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.failure = BadRefreshResponse("SSO melted.")
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertIsNone(job.store_revision)
        self.assertEqual("SSO melted.", job.error_message)
        [notification] = pop_notifications()
        self.assertEqual(
            config.canonical.noreply_from_address, notification["From"])
        self.assertEqual(
            "Requester <%s>" % requester.preferredemail.email,
            notification["To"])
        subject = notification["Subject"].replace("\n ", " ")
        self.assertEqual(
            "Refreshing store authorization failed for test-snap", subject)
        self.assertEqual(
            "Requester @requester-team",
            notification["X-Launchpad-Message-Rationale"])
        self.assertEqual(
            requester_team.name, notification["X-Launchpad-Message-For"])
        self.assertEqual(
            "snap-build-upload-refresh-failed",
            notification["X-Launchpad-Notification-Type"])
        body, footer = six.ensure_text(
            notification.get_payload(decode=True)).split("\n-- \n")
        self.assertIn(
            "http://launchpad.test/~requester-team/+snap/test-snap/+authorize",
            body)
        self.assertEqual(
            "http://launchpad.test/~requester-team/+snap/test-snap/+build/%d\n"
            "Your team Requester Team is the requester of the build.\n" %
            snapbuild.id, footer)
        self.assertWebhookDeliveries(
            snapbuild, ["Pending", "Failed to upload"], logger)

    def test_run_upload_failure_notifies(self):
        # A run that gets some other upload failure from the store sends
        # mail.
        logger = self.useFixture(FakeLogger())
        requester = self.factory.makePerson(name="requester")
        requester_team = self.factory.makeTeam(
            owner=requester, name="requester-team", members=[requester])
        snapbuild = self.makeSnapBuild(
            requester=requester_team, name="test-snap", owner=requester_team)
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.failure = UploadFailedResponse(
            "Failed to upload", detail="The proxy exploded.\n")
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertIsNone(job.store_revision)
        self.assertEqual("Failed to upload", job.error_message)
        [notification] = pop_notifications()
        self.assertEqual(
            config.canonical.noreply_from_address, notification["From"])
        self.assertEqual(
            "Requester <%s>" % requester.preferredemail.email,
            notification["To"])
        subject = notification["Subject"].replace("\n ", " ")
        self.assertEqual("Store upload failed for test-snap", subject)
        self.assertEqual(
            "Requester @requester-team",
            notification["X-Launchpad-Message-Rationale"])
        self.assertEqual(
            requester_team.name, notification["X-Launchpad-Message-For"])
        self.assertEqual(
            "snap-build-upload-failed",
            notification["X-Launchpad-Notification-Type"])
        body, footer = six.ensure_text(
            notification.get_payload(decode=True)).split("\n-- \n")
        self.assertIn("Failed to upload", body)
        build_url = (
            "http://launchpad.test/~requester-team/+snap/test-snap/+build/%d" %
            snapbuild.id)
        self.assertIn(build_url, body)
        self.assertEqual(
            "%s\nYour team Requester Team is the requester of the build.\n" %
            build_url, footer)
        self.assertWebhookDeliveries(
            snapbuild, ["Pending", "Failed to upload"], logger)
        self.assertIn(
            ("error_detail", "The proxy exploded.\n"), job.getOopsVars())

    def test_run_scan_pending_retries(self):
        # A run that finds that the store has not yet finished scanning the
        # package schedules itself to be retried.
        logger = self.useFixture(FakeLogger())
        snapbuild = self.makeSnapBuild()
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.failure = UploadNotScannedYetResponse()
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertIsNone(job.store_revision)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())
        self.assertEqual(JobStatus.WAITING, job.job.status)
        self.assertWebhookDeliveries(snapbuild, ["Pending"], logger)
        # Try again.  The upload part of the job is not retried, and this
        # time the scan completes.
        job.scheduled_start = None
        client.upload.calls = []
        client.checkStatus.calls = []
        client.checkStatus.failure = None
        client.checkStatus.result = (self.store_url, 1)
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertEqual(self.store_url, job.store_url)
        self.assertEqual(1, job.store_revision)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())
        self.assertEqual(JobStatus.COMPLETED, job.job.status)
        self.assertWebhookDeliveries(
            snapbuild, ["Pending", "Uploaded"], logger)

    def test_run_scan_failure_notifies(self):
        # A run that gets a scan failure from the store sends mail.
        logger = self.useFixture(FakeLogger())
        requester = self.factory.makePerson(name="requester")
        requester_team = self.factory.makeTeam(
            owner=requester, name="requester-team", members=[requester])
        snapbuild = self.makeSnapBuild(
            requester=requester_team, name="test-snap", owner=requester_team)
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.failure = ScanFailedResponse(
            "Scan failed.\nConfinement not allowed.",
            messages=[
                {"message": "Scan failed.", "link": "link1"},
                {"message": "Confinement not allowed.", "link": "link2"}])
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertIsNone(job.store_revision)
        self.assertEqual(
            "Scan failed.\nConfinement not allowed.", job.error_message)
        self.assertEqual([
            {"message": "Scan failed.", "link": "link1"},
            {"message": "Confinement not allowed.", "link": "link2"}],
            job.error_messages)
        [notification] = pop_notifications()
        self.assertEqual(
            config.canonical.noreply_from_address, notification["From"])
        self.assertEqual(
            "Requester <%s>" % requester.preferredemail.email,
            notification["To"])
        subject = notification["Subject"].replace("\n ", " ")
        self.assertEqual("Store upload scan failed for test-snap", subject)
        self.assertEqual(
            "Requester @requester-team",
            notification["X-Launchpad-Message-Rationale"])
        self.assertEqual(
            requester_team.name, notification["X-Launchpad-Message-For"])
        self.assertEqual(
            "snap-build-upload-scan-failed",
            notification["X-Launchpad-Notification-Type"])
        body, footer = six.ensure_text(
            notification.get_payload(decode=True)).split("\n-- \n")
        self.assertIn("Scan failed.", body)
        self.assertEqual(
            "http://launchpad.test/~requester-team/+snap/test-snap/+build/%d\n"
            "Your team Requester Team is the requester of the build.\n" %
            snapbuild.id, footer)
        self.assertWebhookDeliveries(
            snapbuild, ["Pending", "Failed to upload"], logger)

    def test_run_scan_review_queued(self):
        # A run that finds that the store has queued the package behind
        # others for manual review completes, but without recording a store
        # URL or revision.
        logger = self.useFixture(FakeLogger())
        snapbuild = self.makeSnapBuild()
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.result = (None, None)
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertIsNone(job.store_revision)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())
        self.assertWebhookDeliveries(
            snapbuild, ["Pending", "Uploaded"], logger)

    def test_run_release(self):
        # A run configured to automatically release the package to certain
        # channels does so.
        logger = self.useFixture(FakeLogger())
        snapbuild = self.makeSnapBuild(store_channels=["stable", "edge"])
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.result = (self.store_url, 1)
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertEqual(self.store_url, job.store_url)
        self.assertEqual(1, job.store_revision)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())
        self.assertWebhookDeliveries(
            snapbuild, ["Pending", "Uploaded"], logger)

    def test_retry_delay(self):
        # The job is retried every minute, unless it just made one of its
        # first four attempts to poll the status endpoint, in which case the
        # delays are 15/15/30/30 seconds.
        self.useFixture(FakeLogger())
        snapbuild = self.makeSnapBuild()
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.failure = UploadFailedResponse(
            "Proxy error", can_retry=True)
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertNotIn("status_url", job.metadata)
        self.assertEqual(timedelta(seconds=60), job.retry_delay)
        job.scheduled_start = None
        client.upload.failure = None
        client.upload.result = self.status_url
        client.checkStatus.failure = UploadNotScannedYetResponse()
        for expected_delay in (15, 15, 30, 30, 60):
            with dbuser(config.ISnapStoreUploadJobSource.dbuser):
                run_isolated_jobs([job])
            self.assertIn("status_url", job.snapbuild.store_upload_metadata)
            self.assertIsNone(job.store_url)
            self.assertEqual(
                timedelta(seconds=expected_delay), job.retry_delay)
            job.scheduled_start = None
        client.checkStatus.failure = None
        client.checkStatus.result = (self.store_url, 1)
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])
        self.assertEqual(self.store_url, job.store_url)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())
        self.assertEqual(JobStatus.COMPLETED, job.job.status)

    def test_retry_after_upload_does_not_upload(self):
        # If the job has uploaded, but failed to release, it should
        # not attempt to upload again on the next run.
        self.useFixture(FakeLogger())
        snapbuild = self.makeSnapBuild(store_channels=["stable", "edge"])
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.result = (self.store_url, 1)
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])

        previous_upload = client.upload.calls
        previous_checkStatus = client.checkStatus.calls

        # Check we uploaded as expected
        self.assertEqual(self.store_url, job.store_url)
        self.assertEqual(1, job.store_revision)
        self.assertEqual(timedelta(seconds=60), job.retry_delay)
        self.assertEqual(1, len(client.upload.calls))
        self.assertIsNone(job.error_message)

        # Run the job again
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            run_isolated_jobs([job])

        # Release is not called due to release intent in upload
        # but ensure that we have not called upload twice
        self.assertEqual(previous_upload, client.upload.calls)
        self.assertEqual(previous_checkStatus, client.checkStatus.calls)
        self.assertIsNone(job.error_message)

    def test_with_snapbuild_metadata_as_none(self):
        db_build = self.factory.makeSnapBuild()
        unsecure_db_build = removeSecurityProxy(db_build)
        unsecure_db_build.store_upload_metadata = None
        store = IStore(SnapBuild)
        store.flush()
        loaded_build = store.find(SnapBuild, id=unsecure_db_build.id).one()

        job = SnapStoreUploadJob.create(loaded_build)
        self.assertEqual({}, job.store_metadata)

    def test_with_snapbuild_metadata_as_none_set_status(self):
        db_build = self.factory.makeSnapBuild()
        unsecure_db_build = removeSecurityProxy(db_build)
        unsecure_db_build.store_upload_metadata = None
        store = IStore(SnapBuild)
        store.flush()
        loaded_build = store.find(SnapBuild, id=unsecure_db_build.id).one()

        job = SnapStoreUploadJob.create(loaded_build)
        job.status_url = 'http://example.org'
        store.flush()

        loaded_build = store.find(SnapBuild, id=unsecure_db_build.id).one()
        self.assertEqual(
            'http://example.org',
            loaded_build.store_upload_metadata['status_url']
            )
