# Copyright 2014-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test live filesystems."""

from datetime import datetime, timedelta, timezone

import transaction
from fixtures import FakeLogger
from storm.exceptions import LostObjectError
from storm.locals import Store
from testtools.matchers import Equals, MatchesDict, MatchesStructure
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.interfaces.launchpad import IPrivacy
from lp.buildmaster.enums import BuildQueueStatus, BuildStatus
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.registry.enums import PersonVisibility
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.config import config
from lp.services.database.constants import UTC_NOW
from lp.services.features.testing import FeatureFixture
from lp.services.webapp import canonical_url
from lp.services.webapp.interfaces import OAuthPermission
from lp.services.webapp.snapshot import notify_modified
from lp.services.webhooks.testing import LogsScheduledWebhooks
from lp.soyuz.interfaces.livefs import (
    LIVEFS_FEATURE_FLAG,
    LIVEFS_WEBHOOKS_FEATURE_FLAG,
    CannotDeleteLiveFS,
    ILiveFS,
    ILiveFSSet,
    ILiveFSView,
    LiveFSBuildAlreadyPending,
    LiveFSFeatureDisabled,
)
from lp.soyuz.interfaces.livefsbuild import ILiveFSBuild
from lp.testing import (
    ANONYMOUS,
    StormStatementRecorder,
    TestCaseWithFactory,
    api_url,
    celebrity_logged_in,
    login,
    logout,
    person_logged_in,
)
from lp.testing.dbuser import dbuser
from lp.testing.layers import DatabaseFunctionalLayer, LaunchpadZopelessLayer
from lp.testing.matchers import DoesNotSnapshot, HasQueryCount
from lp.testing.pages import webservice_for_person


class TestLiveFSFeatureFlag(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_feature_flag_disabled(self):
        # Without a feature flag, we will not create new LiveFSes.
        person = self.factory.makePerson()
        self.assertRaises(
            LiveFSFeatureDisabled,
            getUtility(ILiveFSSet).new,
            person,
            person,
            None,
            None,
            True,
            None,
        )


class TestLiveFS(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))

    def test_implements_interfaces(self):
        # LiveFS implements ILiveFS and IPrivacy.
        livefs = self.factory.makeLiveFS()
        with person_logged_in(livefs.owner):
            self.assertProvides(livefs, ILiveFS)
            self.assertProvides(livefs, IPrivacy)

    def test_avoids_problematic_snapshots(self):
        self.assertThat(
            self.factory.makeLiveFS(),
            DoesNotSnapshot(
                ["builds", "completed_builds", "pending_builds"], ILiveFSView
            ),
        )

    def test_initial_date_last_modified(self):
        # The initial value of date_last_modified is date_created.
        livefs = self.factory.makeLiveFS(
            date_created=datetime(2014, 4, 25, 10, 38, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(livefs.date_created, livefs.date_last_modified)

    def test_modifiedevent_sets_date_last_modified(self):
        # When a LiveFS receives an object modified event, the last modified
        # date is set to UTC_NOW.
        livefs = self.factory.makeLiveFS(
            date_created=datetime(2014, 4, 25, 10, 38, 0, tzinfo=timezone.utc)
        )
        with notify_modified(removeSecurityProxy(livefs), ["name"]):
            pass
        self.assertSqlAttributeEqualsDate(
            livefs, "date_last_modified", UTC_NOW
        )

    def test_private_owner(self):
        # A LiveFS is private if its owner is.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=person, visibility=PersonVisibility.PRIVATE
        )
        with person_logged_in(person):
            livefs = self.factory.makeLiveFS(registrant=person, owner=team)
            self.assertTrue(livefs.private)

    def test_public(self):
        # A LiveFS is public if its owner is.
        livefs = self.factory.makeLiveFS()
        self.assertFalse(livefs.private)

    def test_relative_build_score(self):
        # Buildd admins can change the relative build score of a LiveFS, but
        # ordinary users cannot.
        livefs = self.factory.makeLiveFS()
        with person_logged_in(livefs.owner):
            self.assertRaises(
                Unauthorized, setattr, livefs, "relative_build_score", 100
            )
        with celebrity_logged_in("buildd_admin"):
            livefs.relative_build_score = 100

    def test_keep_binary_files_days(self):
        # Buildd admins can change the binary file retention period of a
        # LiveFS, but ordinary users cannot.
        livefs = self.factory.makeLiveFS()
        self.assertEqual(1, livefs.keep_binary_files_days)
        with person_logged_in(livefs.owner):
            self.assertRaises(
                Unauthorized, setattr, livefs, "keep_binary_files_days", 2
            )
        with celebrity_logged_in("buildd_admin"):
            livefs.keep_binary_files_days = 2
        self.assertEqual(2, livefs.keep_binary_files_days)
        self.assertEqual(
            timedelta(days=2),
            removeSecurityProxy(livefs).keep_binary_files_interval,
        )
        with celebrity_logged_in("buildd_admin"):
            livefs.keep_binary_files_days = None
        self.assertIsNone(livefs.keep_binary_files_days)
        self.assertIsNone(
            removeSecurityProxy(livefs).keep_binary_files_interval
        )

    def test_requestBuild(self):
        # requestBuild creates a new LiveFSBuild.
        livefs = self.factory.makeLiveFS()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=livefs.distro_series
        )
        build = livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
        )
        self.assertTrue(ILiveFSBuild.providedBy(build))
        self.assertEqual(livefs.owner, build.requester)
        self.assertEqual(livefs.distro_series.main_archive, build.archive)
        self.assertEqual(distroarchseries, build.distro_arch_series)
        self.assertEqual(PackagePublishingPocket.RELEASE, build.pocket)
        self.assertIsNone(build.unique_key)
        self.assertIsNone(build.metadata_override)
        self.assertEqual(BuildStatus.NEEDSBUILD, build.status)
        store = Store.of(build)
        store.flush()
        build_queue = store.find(
            BuildQueue,
            BuildQueue._build_farm_job_id
            == removeSecurityProxy(build).build_farm_job_id,
        ).one()
        self.assertProvides(build_queue, IBuildQueue)
        self.assertEqual(
            livefs.distro_series.main_archive.require_virtualized,
            build_queue.virtualized,
        )
        self.assertEqual(BuildQueueStatus.WAITING, build_queue.status)

    def test_requestBuild_score(self):
        # Build requests have a relatively low queue score (2510).
        livefs = self.factory.makeLiveFS()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=livefs.distro_series
        )
        build = livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
        )
        queue_record = build.buildqueue_record
        queue_record.score()
        self.assertEqual(2510, queue_record.lastscore)

    def test_requestBuild_relative_build_score(self):
        # Offsets for archives and livefses are respected.
        livefs = self.factory.makeLiveFS()
        removeSecurityProxy(livefs).relative_build_score = 50
        archive = self.factory.makeArchive(owner=livefs.owner)
        removeSecurityProxy(archive).relative_build_score = 100
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=livefs.distro_series
        )
        build = livefs.requestBuild(
            livefs.owner,
            archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
        )
        queue_record = build.buildqueue_record
        queue_record.score()
        self.assertEqual(2660, queue_record.lastscore)

    def test_requestBuild_rejects_repeats(self):
        # requestBuild refuses if there is already a pending build.
        livefs = self.factory.makeLiveFS()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=livefs.distro_series
        )
        old_build = livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
        )
        self.assertRaises(
            LiveFSBuildAlreadyPending,
            livefs.requestBuild,
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
        )
        # We can build for a different archive.
        livefs.requestBuild(
            livefs.owner,
            self.factory.makeArchive(owner=livefs.owner),
            distroarchseries,
            PackagePublishingPocket.RELEASE,
        )
        # We can build for a different distroarchseries.
        livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            self.factory.makeDistroArchSeries(
                distroseries=livefs.distro_series
            ),
            PackagePublishingPocket.RELEASE,
        )
        # We can specify a unique key.
        livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
            unique_key="foo",
        )
        livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
            unique_key="bar",
        )
        self.assertRaises(
            LiveFSBuildAlreadyPending,
            livefs.requestBuild,
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
            unique_key="bar",
        )
        # We can apply different metadata overrides.
        livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
            metadata_override={"proposed": True},
        )
        livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
            metadata_override={"project": "foo", "proposed": True},
        )
        livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
            metadata_override={"project": "foo"},
        )
        self.assertRaises(
            LiveFSBuildAlreadyPending,
            livefs.requestBuild,
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
            metadata_override={"project": "foo", "proposed": True},
        )
        # Changing the status of the old build allows a new build.
        old_build.updateStatus(BuildStatus.BUILDING)
        old_build.updateStatus(BuildStatus.FULLYBUILT)
        livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
        )

    def test_requestBuild_virtualization(self):
        # New builds are virtualized if any of the processor, livefs or
        # archive require it.
        for proc_nonvirt, livefs_virt, archive_virt, build_virt in (
            (True, False, False, False),
            (True, False, True, True),
            (True, True, False, True),
            (True, True, True, True),
            (False, False, False, True),
            (False, False, True, True),
            (False, True, False, True),
            (False, True, True, True),
        ):
            distroarchseries = self.factory.makeDistroArchSeries(
                processor=self.factory.makeProcessor(
                    supports_nonvirtualized=proc_nonvirt
                )
            )
            livefs = self.factory.makeLiveFS(
                distroseries=distroarchseries.distroseries,
                require_virtualized=livefs_virt,
            )
            archive = self.factory.makeArchive(
                distribution=distroarchseries.distroseries.distribution,
                owner=livefs.owner,
                virtualized=archive_virt,
            )
            build = livefs.requestBuild(
                livefs.owner,
                archive,
                distroarchseries,
                PackagePublishingPocket.RELEASE,
            )
            self.assertEqual(build_virt, build.virtualized)

    def test_requestBuild_version(self):
        # requestBuild may optionally override the version.
        livefs = self.factory.makeLiveFS()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=livefs.distro_series
        )
        build = livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
        )
        self.assertEqual(
            build.date_created.strftime("%Y%m%d-%H%M%S"), build.version
        )
        build.updateStatus(BuildStatus.BUILDING)
        build.updateStatus(BuildStatus.FULLYBUILT)
        build = livefs.requestBuild(
            livefs.owner,
            livefs.distro_series.main_archive,
            distroarchseries,
            PackagePublishingPocket.RELEASE,
            version="20150101",
        )
        self.assertEqual("20150101", build.version)

    def test_getBuilds(self):
        # Test the various getBuilds methods.
        livefs = self.factory.makeLiveFS()
        builds = [
            self.factory.makeLiveFSBuild(livefs=livefs) for x in range(3)
        ]
        # We want the latest builds first.
        builds.reverse()

        self.assertEqual(builds, list(livefs.builds))
        self.assertEqual([], list(livefs.completed_builds))
        self.assertEqual(builds, list(livefs.pending_builds))

        # Change the status of one of the builds and retest.
        builds[0].updateStatus(BuildStatus.BUILDING)
        builds[0].updateStatus(BuildStatus.FULLYBUILT)
        self.assertEqual(builds, list(livefs.builds))
        self.assertEqual(builds[:1], list(livefs.completed_builds))
        self.assertEqual(builds[1:], list(livefs.pending_builds))

    def test_getBuilds_cancelled_never_started_last(self):
        # A cancelled build that was never even started sorts to the end.
        livefs = self.factory.makeLiveFS()
        fullybuilt = self.factory.makeLiveFSBuild(livefs=livefs)
        instacancelled = self.factory.makeLiveFSBuild(livefs=livefs)
        fullybuilt.updateStatus(BuildStatus.BUILDING)
        fullybuilt.updateStatus(BuildStatus.FULLYBUILT)
        instacancelled.updateStatus(BuildStatus.CANCELLED)
        self.assertEqual([fullybuilt, instacancelled], list(livefs.builds))
        self.assertEqual(
            [fullybuilt, instacancelled], list(livefs.completed_builds)
        )
        self.assertEqual([], list(livefs.pending_builds))

    def test_getBuilds_privacy(self):
        # The various getBuilds methods exclude builds against invisible
        # archives.
        livefs = self.factory.makeLiveFS()
        archive = self.factory.makeArchive(
            distribution=livefs.distro_series.distribution,
            owner=livefs.owner,
            private=True,
        )
        with person_logged_in(livefs.owner):
            build = self.factory.makeLiveFSBuild(
                livefs=livefs, archive=archive
            )
            self.assertEqual([build], list(livefs.builds))
            self.assertEqual([build], list(livefs.pending_builds))
        self.assertEqual([], list(livefs.builds))
        self.assertEqual([], list(livefs.pending_builds))

    def test_delete_without_builds(self):
        # A live filesystem with no builds can be deleted.
        owner = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
        livefs = self.factory.makeLiveFS(
            registrant=owner,
            owner=owner,
            distroseries=distroseries,
            name="condemned",
        )
        self.assertTrue(
            getUtility(ILiveFSSet).exists(owner, distroseries, "condemned")
        )
        with person_logged_in(livefs.owner):
            livefs.destroySelf()
        self.assertFalse(
            getUtility(ILiveFSSet).exists(owner, distroseries, "condemned")
        )

    def test_delete_with_builds(self):
        # A live filesystem with builds cannot be deleted.
        owner = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
        livefs = self.factory.makeLiveFS(
            registrant=owner,
            owner=owner,
            distroseries=distroseries,
            name="condemned",
        )
        self.factory.makeLiveFSBuild(livefs=livefs)
        self.assertTrue(
            getUtility(ILiveFSSet).exists(owner, distroseries, "condemned")
        )
        with person_logged_in(livefs.owner):
            self.assertRaises(CannotDeleteLiveFS, livefs.destroySelf)
        self.assertTrue(
            getUtility(ILiveFSSet).exists(owner, distroseries, "condemned")
        )

    def test_requestBuild_triggers_webhooks(self):
        # Requesting a build triggers webhooks.
        logger = self.useFixture(FakeLogger())
        with FeatureFixture(
            {LIVEFS_FEATURE_FLAG: "on", LIVEFS_WEBHOOKS_FEATURE_FLAG: "on"}
        ):
            livefs = self.factory.makeLiveFS()
            distroarchseries = self.factory.makeDistroArchSeries(
                distroseries=livefs.distro_series
            )
            hook = self.factory.makeWebhook(
                target=livefs, event_types=["livefs:build:0.1"]
            )
            build = livefs.requestBuild(
                livefs.owner,
                livefs.distro_series.main_archive,
                distroarchseries,
                PackagePublishingPocket.RELEASE,
            )

        expected_payload = {
            "livefs_build": Equals(
                canonical_url(build, force_local_path=True)
            ),
            "action": Equals("created"),
            "livefs": Equals(canonical_url(livefs, force_local_path=True)),
            "status": Equals("Needs building"),
        }
        with person_logged_in(livefs.owner):
            delivery = hook.deliveries.one()
            self.assertThat(
                delivery,
                MatchesStructure(
                    event_type=Equals("livefs:build:0.1"),
                    payload=MatchesDict(expected_payload),
                ),
            )
            with dbuser(config.IWebhookDeliveryJobSource.dbuser):
                self.assertEqual(
                    "<WebhookDeliveryJob for webhook %d on %r>"
                    % (hook.id, hook.target),
                    repr(delivery),
                )
                self.assertThat(
                    logger.output,
                    LogsScheduledWebhooks(
                        [
                            (
                                hook,
                                "livefs:build:0.1",
                                MatchesDict(expected_payload),
                            )
                        ]
                    ),
                )

    def test_related_webhooks_deleted(self):
        owner = self.factory.makePerson()
        with FeatureFixture(
            {LIVEFS_FEATURE_FLAG: "on", LIVEFS_WEBHOOKS_FEATURE_FLAG: "on"}
        ):
            livefs = self.factory.makeLiveFS(registrant=owner, owner=owner)
            webhook = self.factory.makeWebhook(target=livefs)
        with person_logged_in(livefs.owner):
            webhook.ping()
            livefs.destroySelf()
            transaction.commit()
            self.assertRaises(LostObjectError, getattr, webhook, "target")


class TestLiveFSSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))

    def test_class_implements_interfaces(self):
        # The LiveFSSet class implements ILiveFSSet.
        self.assertProvides(getUtility(ILiveFSSet), ILiveFSSet)

    def makeLiveFSComponents(self, metadata={}):
        """Return a dict of values that can be used to make a LiveFS.

        Suggested use: provide as kwargs to ILiveFSSet.new.

        :param metadata: A dict to set as LiveFS.metadata.
        """
        registrant = self.factory.makePerson()
        return dict(
            registrant=registrant,
            owner=self.factory.makeTeam(owner=registrant),
            distro_series=self.factory.makeDistroSeries(),
            name=self.factory.getUniqueString("livefs-name"),
            metadata=metadata,
        )

    def test_creation(self):
        # The metadata entries supplied when a LiveFS is created are present
        # on the new object.
        components = self.makeLiveFSComponents(metadata={"project": "foo"})
        livefs = getUtility(ILiveFSSet).new(**components)
        transaction.commit()
        self.assertEqual(components["registrant"], livefs.registrant)
        self.assertEqual(components["owner"], livefs.owner)
        self.assertEqual(components["distro_series"], livefs.distro_series)
        self.assertEqual(components["name"], livefs.name)
        self.assertEqual(components["metadata"], livefs.metadata)
        self.assertTrue(livefs.require_virtualized)

    def test_exists(self):
        # ILiveFSSet.exists checks for matching LiveFSes.
        livefs = self.factory.makeLiveFS()
        self.assertTrue(
            getUtility(ILiveFSSet).exists(
                livefs.owner, livefs.distro_series, livefs.name
            )
        )
        self.assertFalse(
            getUtility(ILiveFSSet).exists(
                self.factory.makePerson(), livefs.distro_series, livefs.name
            )
        )
        self.assertFalse(
            getUtility(ILiveFSSet).exists(
                livefs.owner, self.factory.makeDistroSeries(), livefs.name
            )
        )
        self.assertFalse(
            getUtility(ILiveFSSet).exists(
                livefs.owner, livefs.distro_series, "different"
            )
        )

    def test_getByPerson(self):
        # ILiveFSSet.getByPerson returns all LiveFSes with the given owner.
        owners = [self.factory.makePerson() for i in range(2)]
        livefses = []
        for owner in owners:
            for i in range(2):
                livefses.append(
                    self.factory.makeLiveFS(registrant=owner, owner=owner)
                )
        self.assertContentEqual(
            livefses[:2], getUtility(ILiveFSSet).getByPerson(owners[0])
        )
        self.assertContentEqual(
            livefses[2:], getUtility(ILiveFSSet).getByPerson(owners[1])
        )

    def test_getAll(self):
        # ILiveFSSet.getAll returns all LiveFSes.
        livefses = [self.factory.makeLiveFS() for i in range(3)]
        self.assertContentEqual(livefses, getUtility(ILiveFSSet).getAll())

    def test_getAll_privacy(self):
        # ILiveFSSet.getAll hides LiveFSes whose owners are invisible.
        registrants = [self.factory.makePerson() for i in range(2)]
        owners = [
            self.factory.makeTeam(owner=registrants[0]),
            self.factory.makeTeam(
                owner=registrants[1], visibility=PersonVisibility.PRIVATE
            ),
        ]
        livefses = []
        for registrant, owner in zip(registrants, owners):
            with person_logged_in(registrant):
                livefses.append(
                    self.factory.makeLiveFS(registrant=registrant, owner=owner)
                )
        self.assertContentEqual([livefses[0]], getUtility(ILiveFSSet).getAll())
        with person_logged_in(registrants[0]):
            self.assertContentEqual(
                [livefses[0]], getUtility(ILiveFSSet).getAll()
            )
        with person_logged_in(registrants[1]):
            self.assertContentEqual(livefses, getUtility(ILiveFSSet).getAll())


class TestLiveFSWebservice(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super().setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))
        self.person = self.factory.makePerson(displayname="Test Person")
        self.webservice = webservice_for_person(
            self.person, permission=OAuthPermission.WRITE_PUBLIC
        )
        self.webservice.default_api_version = "devel"
        login(ANONYMOUS)

    def getURL(self, obj):
        return self.webservice.getAbsoluteUrl(api_url(obj))

    def makeLiveFS(
        self, owner=None, distroseries=None, metadata=None, webservice=None
    ):
        if owner is None:
            owner = self.person
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries(registrant=owner)
        if metadata is None:
            metadata = {"project": "flavour"}
        if webservice is None:
            webservice = self.webservice
        transaction.commit()
        distroseries_url = api_url(distroseries)
        owner_url = api_url(owner)
        logout()
        response = webservice.named_post(
            "/livefses",
            "new",
            owner=owner_url,
            distro_series=distroseries_url,
            name="flavour-desktop",
            metadata=metadata,
        )
        self.assertEqual(201, response.status)
        livefs = webservice.get(response.getHeader("Location")).jsonBody()
        return livefs, distroseries_url

    def getCollectionLinks(self, entry, member):
        """Return a list of self_link attributes of entries in a collection."""
        collection = self.webservice.get(
            entry["%s_collection_link" % member]
        ).jsonBody()
        return [entry["self_link"] for entry in collection["entries"]]

    def test_new(self):
        # Ensure LiveFS creation works.
        team = self.factory.makeTeam(owner=self.person)
        livefs, distroseries_url = self.makeLiveFS(owner=team)
        with person_logged_in(self.person):
            self.assertEqual(
                self.getURL(self.person), livefs["registrant_link"]
            )
            self.assertEqual(self.getURL(team), livefs["owner_link"])
            self.assertEqual(
                self.webservice.getAbsoluteUrl(distroseries_url),
                livefs["distro_series_link"],
            )
            self.assertEqual("flavour-desktop", livefs["name"])
            self.assertEqual({"project": "flavour"}, livefs["metadata"])
            self.assertTrue(livefs["require_virtualized"])

    def test_duplicate(self):
        # An attempt to create a duplicate LiveFS fails.
        team = self.factory.makeTeam(owner=self.person)
        _, distroseries_url = self.makeLiveFS(owner=team)
        with person_logged_in(self.person):
            owner_url = api_url(team)
        response = self.webservice.named_post(
            "/livefses",
            "new",
            owner=owner_url,
            distro_series=distroseries_url,
            name="flavour-desktop",
            metadata={},
        )
        self.assertEqual(400, response.status)
        self.assertEqual(
            b"There is already a live filesystem with the same name, owner, "
            b"and distroseries.",
            response.body,
        )

    def test_not_owner(self):
        # If the registrant is not the owner or a member of the owner team,
        # LiveFS creation fails.
        other_person = self.factory.makePerson(displayname="Other Person")
        other_team = self.factory.makeTeam(
            owner=other_person, displayname="Other Team"
        )
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        transaction.commit()
        other_person_url = api_url(other_person)
        other_team_url = api_url(other_team)
        distroseries_url = api_url(distroseries)
        logout()
        response = self.webservice.named_post(
            "/livefses",
            "new",
            owner=other_person_url,
            distro_series=distroseries_url,
            name="dummy",
            metadata={},
        )
        self.assertEqual(401, response.status)
        self.assertEqual(
            b"Test Person cannot create live filesystems owned by Other "
            b"Person.",
            response.body,
        )
        response = self.webservice.named_post(
            "/livefses",
            "new",
            owner=other_team_url,
            distro_series=distroseries_url,
            name="dummy",
            metadata={},
        )
        self.assertEqual(401, response.status)
        self.assertEqual(
            b"Test Person is not a member of Other Team.", response.body
        )

    def test_getByName(self):
        # lp.livefses.getByName returns a matching LiveFS.
        livefs, distroseries_url = self.makeLiveFS()
        with person_logged_in(self.person):
            owner_url = api_url(self.person)
        response = self.webservice.named_get(
            "/livefses",
            "getByName",
            owner=owner_url,
            distro_series=distroseries_url,
            name="flavour-desktop",
        )
        self.assertEqual(200, response.status)
        self.assertEqual(livefs, response.jsonBody())

    def test_getByName_missing(self):
        # lp.livefses.getByName returns 404 for a non-existent LiveFS.
        livefs, distroseries_url = self.makeLiveFS()
        with person_logged_in(self.person):
            owner_url = api_url(self.person)
        response = self.webservice.named_get(
            "/livefses",
            "getByName",
            owner=owner_url,
            distro_series=distroseries_url,
            name="nonexistent",
        )
        self.assertEqual(404, response.status)
        self.assertEqual(
            b"No such live filesystem with this owner/distroseries: "
            b"'nonexistent'.",
            response.body,
        )

    def test_requestBuild(self):
        # Build requests can be performed and end up in livefs.builds and
        # livefs.pending_builds.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person
        )
        distroarchseries_url = api_url(distroarchseries)
        archive_url = api_url(distroseries.main_archive)
        livefs, _ = self.makeLiveFS(distroseries=distroseries)
        response = self.webservice.named_post(
            livefs["self_link"],
            "requestBuild",
            archive=archive_url,
            distro_arch_series=distroarchseries_url,
            pocket="Release",
        )
        self.assertEqual(201, response.status)
        build = self.webservice.get(response.getHeader("Location")).jsonBody()
        self.assertEqual(
            [build["self_link"]], self.getCollectionLinks(livefs, "builds")
        )
        self.assertEqual(
            [], self.getCollectionLinks(livefs, "completed_builds")
        )
        self.assertEqual(
            [build["self_link"]],
            self.getCollectionLinks(livefs, "pending_builds"),
        )

    def test_requestBuild_rejects_repeats(self):
        # Build requests are rejected if already pending.
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person
        )
        distroarchseries_url = api_url(distroarchseries)
        archive_url = api_url(distroseries.main_archive)
        livefs, _ = self.makeLiveFS(distroseries=distroseries)
        response = self.webservice.named_post(
            livefs["self_link"],
            "requestBuild",
            archive=archive_url,
            distro_arch_series=distroarchseries_url,
            pocket="Release",
        )
        self.assertEqual(201, response.status)
        response = self.webservice.named_post(
            livefs["self_link"],
            "requestBuild",
            archive=archive_url,
            distro_arch_series=distroarchseries_url,
            pocket="Release",
        )
        self.assertEqual(400, response.status)
        self.assertEqual(
            b"An identical build of this live filesystem image is already "
            b"pending.",
            response.body,
        )

    def test_requestBuild_not_owner(self):
        # If the requester is not the owner or a member of the owner team,
        # build requests are rejected.
        other_team = self.factory.makeTeam(displayname="Other Team")
        distroseries = self.factory.makeDistroSeries(registrant=self.person)
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person
        )
        distroarchseries_url = api_url(distroarchseries)
        archive_url = api_url(distroseries.main_archive)
        other_webservice = webservice_for_person(
            other_team.teamowner, permission=OAuthPermission.WRITE_PUBLIC
        )
        other_webservice.default_api_version = "devel"
        login(ANONYMOUS)
        livefs, _ = self.makeLiveFS(
            owner=other_team,
            distroseries=distroseries,
            webservice=other_webservice,
        )
        response = self.webservice.named_post(
            livefs["self_link"],
            "requestBuild",
            archive=archive_url,
            distro_arch_series=distroarchseries_url,
            pocket="Release",
        )
        self.assertEqual(401, response.status)
        self.assertEqual(
            b"Test Person cannot create live filesystem builds owned by Other "
            b"Team.",
            response.body,
        )

    def test_requestBuild_archive_disabled(self):
        # Build requests against a disabled archive are rejected.
        distroseries = self.factory.makeDistroSeries(
            distribution=getUtility(IDistributionSet)["ubuntu"],
            registrant=self.person,
        )
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person
        )
        distroarchseries_url = api_url(distroarchseries)
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution,
            owner=self.person,
            enabled=False,
            displayname="Disabled Archive",
        )
        archive_url = api_url(archive)
        livefs, _ = self.makeLiveFS(distroseries=distroseries)
        response = self.webservice.named_post(
            livefs["self_link"],
            "requestBuild",
            archive=archive_url,
            distro_arch_series=distroarchseries_url,
            pocket="Release",
        )
        self.assertEqual(403, response.status)
        self.assertEqual(b"Disabled Archive is disabled.", response.body)

    def test_requestBuild_archive_private_owners_match(self):
        # Build requests against a private archive are allowed if the LiveFS
        # and Archive owners match exactly.
        distroseries = self.factory.makeDistroSeries(
            distribution=getUtility(IDistributionSet)["ubuntu"],
            registrant=self.person,
        )
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person
        )
        distroarchseries_url = api_url(distroarchseries)
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution,
            owner=self.person,
            private=True,
        )
        archive_url = api_url(archive)
        livefs, _ = self.makeLiveFS(distroseries=distroseries)
        private_webservice = webservice_for_person(
            self.person, permission=OAuthPermission.WRITE_PRIVATE
        )
        private_webservice.default_api_version = "devel"
        response = private_webservice.named_post(
            livefs["self_link"],
            "requestBuild",
            archive=archive_url,
            distro_arch_series=distroarchseries_url,
            pocket="Release",
        )
        self.assertEqual(201, response.status)

    def test_requestBuild_archive_private_owners_mismatch(self):
        # Build requests against a private archive are rejected if the
        # LiveFS and Archive owners do not match exactly.
        distroseries = self.factory.makeDistroSeries(
            distribution=getUtility(IDistributionSet)["ubuntu"],
            registrant=self.person,
        )
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person
        )
        distroarchseries_url = api_url(distroarchseries)
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution, private=True
        )
        archive_url = api_url(archive)
        livefs, _ = self.makeLiveFS(distroseries=distroseries)
        response = self.webservice.named_post(
            livefs["self_link"],
            "requestBuild",
            archive=archive_url,
            distro_arch_series=distroarchseries_url,
            pocket="Release",
        )
        self.assertEqual(403, response.status)
        self.assertEqual(
            b"Live filesystem builds against private archives are only "
            b"allowed if the live filesystem owner and the archive owner are "
            b"equal.",
            response.body,
        )

    def test_getBuilds(self):
        # The builds, completed_builds, and pending_builds properties are as
        # expected.
        distroseries = self.factory.makeDistroSeries(
            distribution=getUtility(IDistributionSet)["ubuntu"],
            registrant=self.person,
        )
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, owner=self.person
        )
        distroarchseries_url = api_url(distroarchseries)
        archives = [
            self.factory.makeArchive(
                distribution=distroseries.distribution, owner=self.person
            )
            for x in range(4)
        ]
        archive_urls = [api_url(archive) for archive in archives]
        livefs, _ = self.makeLiveFS(distroseries=distroseries)
        builds = []
        for archive_url in archive_urls:
            response = self.webservice.named_post(
                livefs["self_link"],
                "requestBuild",
                archive=archive_url,
                distro_arch_series=distroarchseries_url,
                pocket="Proposed",
            )
            self.assertEqual(201, response.status)
            build = self.webservice.get(
                response.getHeader("Location")
            ).jsonBody()
            builds.insert(0, build["self_link"])
        self.assertEqual(builds, self.getCollectionLinks(livefs, "builds"))
        self.assertEqual(
            [], self.getCollectionLinks(livefs, "completed_builds")
        )
        self.assertEqual(
            builds, self.getCollectionLinks(livefs, "pending_builds")
        )
        livefs = self.webservice.get(livefs["self_link"]).jsonBody()

        with person_logged_in(self.person):
            db_livefs = getUtility(ILiveFSSet).getByName(
                self.person, distroseries, livefs["name"]
            )
            db_builds = list(db_livefs.builds)
            db_builds[0].updateStatus(
                BuildStatus.BUILDING, date_started=db_livefs.date_created
            )
            db_builds[0].updateStatus(
                BuildStatus.FULLYBUILT,
                date_finished=db_livefs.date_created + timedelta(minutes=10),
            )
        livefs = self.webservice.get(livefs["self_link"]).jsonBody()
        # Builds that have not yet been started are listed last.  This does
        # mean that pending builds that have never been started are sorted
        # to the end, but means that builds that were cancelled before
        # starting don't pollute the start of the collection forever.
        self.assertEqual(builds, self.getCollectionLinks(livefs, "builds"))
        self.assertEqual(
            builds[:1], self.getCollectionLinks(livefs, "completed_builds")
        )
        self.assertEqual(
            builds[1:], self.getCollectionLinks(livefs, "pending_builds")
        )

        with person_logged_in(self.person):
            db_builds[1].updateStatus(
                BuildStatus.BUILDING, date_started=db_livefs.date_created
            )
            db_builds[1].updateStatus(
                BuildStatus.FULLYBUILT,
                date_finished=db_livefs.date_created + timedelta(minutes=20),
            )
        livefs = self.webservice.get(livefs["self_link"]).jsonBody()
        self.assertEqual(
            [builds[1], builds[0], builds[2], builds[3]],
            self.getCollectionLinks(livefs, "builds"),
        )
        self.assertEqual(
            [builds[1], builds[0]],
            self.getCollectionLinks(livefs, "completed_builds"),
        )
        self.assertEqual(
            builds[2:], self.getCollectionLinks(livefs, "pending_builds")
        )

    def test_query_count(self):
        # LiveFS has a reasonable query count.
        livefs = self.factory.makeLiveFS(
            registrant=self.person, owner=self.person
        )
        url = api_url(livefs)
        logout()
        store = Store.of(livefs)
        store.flush()
        store.invalidate()
        with StormStatementRecorder() as recorder:
            self.webservice.get(url)
        self.assertThat(recorder, HasQueryCount(Equals(16)))
