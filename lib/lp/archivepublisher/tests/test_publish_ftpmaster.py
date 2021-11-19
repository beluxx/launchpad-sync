# Copyright 2011-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test publish-ftpmaster cron script."""

import logging
import os
import stat
from textwrap import dedent
import time

from apt_pkg import TagFile
from fixtures import MonkeyPatch
import six
from testtools.matchers import (
    ContainsDict,
    Equals,
    MatchesException,
    MatchesStructure,
    Not,
    PathExists,
    Raises,
    StartsWith,
    )
from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.archivepublisher.scripts.publish_ftpmaster import (
    get_working_dists,
    newer_mtime,
    PublishFTPMaster,
    )
from lp.archivepublisher.tests.test_run_parts import RunPartsMixin
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    pocketsuffix,
    )
from lp.registry.interfaces.series import SeriesStatus
from lp.services.database.interfaces import IMasterStore
from lp.services.log.logger import (
    BufferLogger,
    DevNullLogger,
    )
from lp.services.osutils import write_file
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.services.utils import file_exists
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    PackageUploadCustomFormat,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    run_script,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import LaunchpadZopelessLayer


def path_exists(*path_components):
    """Does the given file or directory exist?"""
    return file_exists(os.path.join(*path_components))


def name_pph_suite(pph):
    """Return name of `pph`'s suite."""
    return pph.distroseries.name + pocketsuffix[pph.pocket]


def get_pub_config(distro):
    """Find the publishing config for `distro`."""
    return getUtility(IPublisherConfigSet).getByDistribution(distro)


def get_archive_root(pub_config):
    """Return the archive root for the given publishing config."""
    return os.path.join(pub_config.root_dir, pub_config.distribution.name)


def get_dists_root(pub_config):
    """Return the dists root directory for the given publishing config."""
    return os.path.join(get_archive_root(pub_config), "dists")


def get_distscopy_root(pub_config):
    """Return the "distscopy" root for the given publishing config."""
    return get_archive_root(pub_config) + "-distscopy"


def write_marker_file(path, contents, mode=None):
    """Write a marker file for checking directory movements.

    :param path: A list of path components.
    :param contents: Text to write into the file.
    :param mode: If given, explicitly set the file to this permission mode.
    """
    with open(os.path.join(*path), "w") as marker:
        marker.write(contents)
        marker.flush()
        if mode is not None:
            os.fchmod(marker.fileno(), mode)


def read_marker_file(path):
    """Read the contents of a marker file.

    :param return: Contents of the marker file.
    """
    with open(os.path.join(*path)) as marker:
        return marker.read()


def get_a_suite(distroseries):
    """Return some suite name for `distroseries`."""
    # Don't pick Release; it's too easy.
    return distroseries.getSuite(PackagePublishingPocket.SECURITY)


def get_marker_files(script, distroseries):
    """Return filesystem paths for all indexes markers for `distroseries`."""
    suites = [distroseries.getSuite(pocket) for pocket in pocketsuffix]
    distro = distroseries.distribution
    return [script.locateIndexesMarker(distro, suite) for suite in suites]


class HelpersMixin:
    """Helpers for the PublishFTPMaster tests."""

    def makeDistroWithPublishDirectory(self):
        """Create a `Distribution` for testing.

        The distribution will have a publishing directory set up, which
        will be cleaned up after the test.
        """
        return self.factory.makeDistribution(
            publish_root_dir=six.ensure_text(self.makeTemporaryDirectory()))

    def makeScript(self, distro=None, extra_args=[]):
        """Produce instance of the `PublishFTPMaster` script."""
        if distro is None:
            distro = self.makeDistroWithPublishDirectory()
        script = PublishFTPMaster(test_args=["-d", distro.name] + extra_args)
        script.txn = self.layer.txn
        script.logger = DevNullLogger()
        return script

    def setUpForScriptRun(self, distro):
        """Mock up config to run the script on `distro`."""
        pub_config = getUtility(IPublisherConfigSet).getByDistribution(distro)
        pub_config.root_dir = six.ensure_text(self.makeTemporaryDirectory())


class TestNewerMtime(TestCase):

    def setUp(self):
        super().setUp()
        tempdir = self.useTempDir()
        self.a = os.path.join(tempdir, "a")
        self.b = os.path.join(tempdir, "b")

    def test_both_missing(self):
        self.assertFalse(newer_mtime(self.a, self.b))

    def test_one_missing(self):
        write_file(self.b, b"")
        self.assertFalse(newer_mtime(self.a, self.b))

    def test_other_missing(self):
        write_file(self.a, b"")
        self.assertTrue(newer_mtime(self.a, self.b))

    def test_older(self):
        write_file(self.a, b"")
        os.utime(self.a, (0, 0))
        write_file(self.b, b"")
        self.assertFalse(newer_mtime(self.a, self.b))

    def test_equal(self):
        now = time.time()
        write_file(self.a, b"")
        os.utime(self.a, (now, now))
        write_file(self.b, b"")
        os.utime(self.b, (now, now))
        self.assertFalse(newer_mtime(self.a, self.b))

    def test_newer(self):
        write_file(self.a, b"")
        write_file(self.b, b"")
        os.utime(self.b, (0, 0))
        self.assertTrue(newer_mtime(self.a, self.b))


class TestPublishFTPMasterScript(
        TestCaseWithFactory, RunPartsMixin, HelpersMixin):
    layer = LaunchpadZopelessLayer

    # Location of shell script.
    SCRIPT_PATH = "cronscripts/publish-ftpmaster.py"

    def prepareUbuntu(self):
        """Obtain a reference to Ubuntu, set up for testing.

        A temporary publishing directory will be set up, and it will be
        cleaned up after the test.
        """
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.setUpForScriptRun(ubuntu)
        return ubuntu

    def readReleaseFile(self, filename):
        """Read a Release file, return as a keyword/value dict."""
        with open(filename) as f:
            sections = list(TagFile(f))
        self.assertEqual(1, len(sections))
        return dict(sections[0])

    def installRunPartsScript(self, distro, parts_dir, script_code):
        """Set up a run-parts script, and configure it to run.

        :param distro: The `Distribution` you're testing on.  Must have
            a temporary directory as its publishing root directory.
        :param parts_dir: The run-parts subdirectory to execute:
            publish-distro.d or finalize.d.
        :param script_code: The code to go into the script.
        """
        distro_config = get_pub_config(distro)
        parts_base = os.path.join(distro_config.root_dir, "distro-parts")
        self.enableRunParts(parts_base)
        script_dir = os.path.join(parts_base, distro.name, parts_dir)
        os.makedirs(script_dir)
        script_path = os.path.join(script_dir, self.factory.getUniqueString())
        with open(script_path, "w") as script_file:
            script_file.write(script_code)
        os.chmod(script_path, 0o755)

    def test_script_runs_successfully(self):
        self.prepareUbuntu()
        self.layer.txn.commit()
        stdout, stderr, retval = run_script(
            self.SCRIPT_PATH + " -d ubuntu")
        self.assertEqual(0, retval, "Script failure:\n" + stderr)

    def test_getConfigs_maps_distro_and_purpose_to_matching_config(self):
        distro = self.makeDistroWithPublishDirectory()
        script = self.makeScript(distro)
        script.setUp()
        reference_config = getPubConfig(distro.main_archive)
        config = script.getConfigs()[distro][ArchivePurpose.PRIMARY]
        self.assertThat(
            config, MatchesStructure.fromExample(
                reference_config, 'temproot', 'distroroot', 'archiveroot'))

    def test_getConfigs_maps_distros(self):
        distro = self.makeDistroWithPublishDirectory()
        script = self.makeScript(distro)
        script.setUp()
        self.assertEqual([distro], list(script.getConfigs()))

    def test_getConfigs_skips_configless_distros(self):
        distro = self.factory.makeDistribution(no_pubconf=True)
        script = self.makeScript(distro)
        script.setUp()
        self.assertEqual({}, script.getConfigs()[distro])

    def test_script_is_happy_with_no_publications(self):
        distro = self.makeDistroWithPublishDirectory()
        self.makeScript(distro).main()

    def test_script_is_happy_with_no_pubconfigs(self):
        distro = self.factory.makeDistribution(no_pubconf=True)
        self.makeScript(distro).main()

    def test_can_run_twice(self):
        test_publisher = SoyuzTestPublisher()
        distroseries = test_publisher.setUpDefaultDistroSeries()
        distro = distroseries.distribution
        self.factory.makeComponentSelection(
            distroseries=distroseries, component="main")
        self.factory.makeArchive(
            distribution=distro, purpose=ArchivePurpose.PARTNER)
        test_publisher.getPubSource()

        self.setUpForScriptRun(distro)
        self.makeScript(distro).main()
        self.makeScript(distro).main()

    def test_publishes_package(self):
        test_publisher = SoyuzTestPublisher()
        distroseries = test_publisher.setUpDefaultDistroSeries()
        distro = distroseries.distribution
        pub_config = get_pub_config(distro)
        self.factory.makeComponentSelection(
            distroseries=distroseries, component="main")
        self.factory.makeArchive(
            distribution=distro, purpose=ArchivePurpose.PARTNER)
        test_publisher.getPubSource()

        self.setUpForScriptRun(distro)
        self.makeScript(distro).main()

        archive_root = get_archive_root(pub_config)
        dists_root = get_dists_root(pub_config)

        dsc = os.path.join(
            archive_root, 'pool', 'main', 'f', 'foo', 'foo_666.dsc')
        with open(dsc) as dsc_file:
            self.assertEqual("I do not care about sources.", dsc_file.read())
        overrides = os.path.join(
            archive_root + '-overrides', distroseries.name + '_main_source')
        with open(overrides) as overrides_file:
            self.assertEqual(dsc, overrides_file.read().rstrip())
        self.assertTrue(path_exists(
            dists_root, distroseries.name, 'main', 'source', 'Sources.gz'))
        self.assertTrue(path_exists(
            dists_root, distroseries.name, 'main', 'source', 'Sources.bz2'))

        distcopyseries = os.path.join(dists_root, distroseries.name)
        release = self.readReleaseFile(
            os.path.join(distcopyseries, "Release"))
        self.assertEqual(distro.displayname, release['Origin'])
        self.assertEqual(distro.displayname, release['Label'])
        self.assertEqual(distroseries.name, release['Suite'])
        self.assertEqual(distroseries.name, release['Codename'])
        self.assertEqual("main", release['Components'])
        self.assertEqual("", release["Architectures"])
        self.assertIn("Date", release)
        self.assertIn("Description", release)
        self.assertNotEqual("", release["MD5Sum"])
        self.assertNotEqual("", release["SHA1"])
        self.assertNotEqual("", release["SHA256"])

        main_release = self.readReleaseFile(
            os.path.join(distcopyseries, 'main', 'source', "Release"))
        self.assertEqual(distroseries.name, main_release["Archive"])
        self.assertEqual("main", main_release["Component"])
        self.assertEqual(distro.displayname, main_release["Origin"])
        self.assertEqual(distro.displayname, main_release["Label"])
        self.assertEqual("source", main_release["Architecture"])

    def test_getDirtySuites_returns_suite_with_pending_publication(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        distro = spph.distroseries.distribution
        script = self.makeScript(spph.distroseries.distribution)
        script.setUp()
        self.assertContentEqual(
            [name_pph_suite(spph)], script.getDirtySuites(distro))

    def test_getDirtySuites_returns_suites_with_pending_publications(self):
        distro = self.makeDistroWithPublishDirectory()
        spphs = [
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=self.factory.makeDistroSeries(
                    distribution=distro))
            for counter in range(2)]

        script = self.makeScript(distro)
        script.setUp()
        self.assertContentEqual(
            [name_pph_suite(spph) for spph in spphs],
            script.getDirtySuites(distro))

    def test_getDirtySuites_ignores_suites_without_pending_publications(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        distro = spph.distroseries.distribution
        script = self.makeScript(spph.distroseries.distribution)
        script.setUp()
        self.assertContentEqual([], script.getDirtySuites(distro))

    def test_getDirtySuites_returns_suites_with_pending_binaries(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        distro = bpph.distroseries.distribution
        script = self.makeScript(bpph.distroseries.distribution)
        script.setUp()
        self.assertContentEqual(
            [name_pph_suite(bpph)], script.getDirtySuites(distro))

    def test_getDirtySecuritySuites_returns_security_suites(self):
        distro = self.makeDistroWithPublishDirectory()
        spphs = [
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=self.factory.makeDistroSeries(
                    distribution=distro),
                pocket=PackagePublishingPocket.SECURITY)
            for counter in range(2)]

        script = self.makeScript(distro)
        script.setUp()
        self.assertContentEqual(
            [name_pph_suite(spph) for spph in spphs],
            script.getDirtySecuritySuites(distro))

    def test_getDirtySecuritySuites_ignores_non_security_suites(self):
        distroseries = self.factory.makeDistroSeries()
        pockets = [
            PackagePublishingPocket.RELEASE,
            PackagePublishingPocket.UPDATES,
            PackagePublishingPocket.PROPOSED,
            PackagePublishingPocket.BACKPORTS,
            ]
        for pocket in pockets:
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=distroseries, pocket=pocket)
        script = self.makeScript(distroseries.distribution)
        script.setUp()
        self.assertEqual(
            [], script.getDirtySecuritySuites(distroseries.distribution))

    def test_rsync_copies_files(self):
        distro = self.makeDistroWithPublishDirectory()
        script = self.makeScript(distro)
        script.setUp()
        dists_root = get_dists_root(get_pub_config(distro))
        dists_backup = os.path.join(
            get_distscopy_root(get_pub_config(distro)), "dists")
        os.makedirs(dists_backup)
        os.makedirs(dists_root)
        write_marker_file([dists_root, "new-file"], "New file")
        script.rsyncBackupDists(distro)
        self.assertEqual(
            "New file", read_marker_file([dists_backup, "new-file"]))

    def test_rsync_cleans_up_obsolete_files(self):
        distro = self.makeDistroWithPublishDirectory()
        script = self.makeScript(distro)
        script.setUp()
        dists_backup = os.path.join(
            get_distscopy_root(get_pub_config(distro)), "dists")
        os.makedirs(dists_backup)
        old_file = [dists_backup, "old-file"]
        write_marker_file(old_file, "old-file")
        os.makedirs(get_dists_root(get_pub_config(distro)))
        script.rsyncBackupDists(distro)
        self.assertFalse(path_exists(*old_file))

    def test_setUpDirs_creates_directory_structure(self):
        distro = self.makeDistroWithPublishDirectory()
        pub_config = get_pub_config(distro)
        archive_root = get_archive_root(pub_config)
        dists_root = get_dists_root(pub_config)
        script = self.makeScript(distro)
        script.setUp()

        self.assertFalse(file_exists(archive_root))

        script.setUpDirs()

        self.assertTrue(file_exists(archive_root))
        self.assertTrue(file_exists(dists_root))
        self.assertTrue(file_exists(get_distscopy_root(pub_config)))

    def test_setUpDirs_does_not_mind_if_dist_directories_already_exist(self):
        distro = self.makeDistroWithPublishDirectory()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.setUpDirs()
        self.assertTrue(file_exists(get_archive_root(get_pub_config(distro))))

    def test_publishDistroArchive_runs_parts(self):
        distro = self.makeDistroWithPublishDirectory()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        run_parts_fixture = self.useFixture(MonkeyPatch(
            "lp.archivepublisher.scripts.publish_ftpmaster.run_parts",
            FakeMethod()))
        script.publishDistroArchive(distro, distro.main_archive)
        self.assertEqual(1, run_parts_fixture.new_value.call_count)
        args, _ = run_parts_fixture.new_value.calls[0]
        run_distro_name, parts_dir = args
        self.assertEqual(distro.name, run_distro_name)
        self.assertEqual("publish-distro.d", parts_dir)

    def test_runPublishDistroParts_passes_parameters(self):
        distro = self.makeDistroWithPublishDirectory()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        run_parts_fixture = self.useFixture(MonkeyPatch(
            "lp.archivepublisher.scripts.publish_ftpmaster.run_parts",
            FakeMethod()))
        script.runPublishDistroParts(distro, distro.main_archive)
        _, kwargs = run_parts_fixture.new_value.calls[0]
        distro_config = get_pub_config(distro)
        self.assertThat(kwargs["env"], ContainsDict({
            "ARCHIVEROOT": Equals(get_archive_root(distro_config)),
            "DISTSROOT": Equals(
                os.path.join(get_distscopy_root(distro_config), "dists")),
            "OVERRIDEROOT": Equals(
                get_archive_root(distro_config) + "-overrides"),
            }))

    def test_clearEmptyDirs_cleans_up_empty_directories(self):
        distro = self.makeDistroWithPublishDirectory()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        empty_dir = os.path.join(
            get_dists_root(get_pub_config(distro)), 'empty-dir')
        os.makedirs(empty_dir)
        script.clearEmptyDirs(distro)
        self.assertFalse(file_exists(empty_dir))

    def test_clearEmptyDirs_does_not_clean_up_nonempty_directories(self):
        distro = self.makeDistroWithPublishDirectory()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        nonempty_dir = os.path.join(
            get_dists_root(get_pub_config(distro)), 'nonempty-dir')
        os.makedirs(nonempty_dir)
        write_marker_file([nonempty_dir, "placeholder"], "Data here!")
        script.clearEmptyDirs(distro)
        self.assertTrue(file_exists(nonempty_dir))

    def test_processOptions_finds_distribution(self):
        distro = self.makeDistroWithPublishDirectory()
        script = self.makeScript(distro)
        script.processOptions()
        self.assertEqual(distro.name, script.options.distribution)
        self.assertEqual([distro], script.distributions)

    def test_processOptions_for_all_derived_finds_derived_distros(self):
        dsp = self.factory.makeDistroSeriesParent()
        script = PublishFTPMaster(test_args=['--all-derived'])
        script.processOptions()
        self.assertIn(dsp.derived_series.distribution, script.distributions)

    def test_processOptions_for_all_derived_ignores_nonderived_distros(self):
        distro = self.factory.makeDistribution()
        script = PublishFTPMaster(test_args=['--all-derived'])
        script.processOptions()
        self.assertNotIn(distro, script.distributions)

    def test_processOptions_complains_about_unknown_distribution(self):
        script = self.makeScript()
        script.options.distribution = self.factory.getUniqueString()
        self.assertRaises(LaunchpadScriptFailure, script.processOptions)

    def test_runFinalizeParts_passes_parameters(self):
        script = self.makeScript(self.prepareUbuntu())
        script.setUp()
        distro = script.distributions[0]
        run_parts_fixture = self.useFixture(MonkeyPatch(
            "lp.archivepublisher.scripts.publish_ftpmaster.run_parts",
            FakeMethod()))
        script.runFinalizeParts(distro)
        _, kwargs = run_parts_fixture.new_value.calls[0]
        env = kwargs["env"]
        required_parameters = {"ARCHIVEROOTS", "SECURITY_UPLOAD_ONLY"}
        missing_parameters = required_parameters.difference(set(env.keys()))
        self.assertEqual(set(), missing_parameters)

    def test_publishSecurityUploads_skips_pub_if_no_security_updates(self):
        script = self.makeScript()
        script.setUp()
        distro = script.distributions[0]
        script.setUpDirs()
        script.installDists = FakeMethod()
        has_published = script.publishSecurityUploads(distro)
        self.assertFalse(has_published)
        self.assertEqual(0, script.installDists.call_count)

    def test_publishSecurityUploads_returns_true_when_publishes(self):
        distro = self.makeDistroWithPublishDirectory()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries,
            pocket=PackagePublishingPocket.SECURITY)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.installDists = FakeMethod()
        has_published = script.publishSecurityUploads(distro)
        self.assertTrue(has_published)

    def test_publishDistroUploads_publishes_all_distro_archives(self):
        distro = self.makeDistroWithPublishDirectory()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        partner_archive = self.factory.makeArchive(
            distribution=distro, purpose=ArchivePurpose.PARTNER)
        for archive in distro.all_distro_archives:
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=distroseries,
                archive=archive)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.publishDistroArchive = FakeMethod()
        script.publishDistroUploads(distro)
        published_archives = [
            args[1] for args, kwargs in script.publishDistroArchive.calls]

        self.assertContentEqual(
            distro.all_distro_archives, published_archives)
        self.assertIn(distro.main_archive, published_archives)
        self.assertIn(partner_archive, published_archives)

    def test_recoverWorkingDists_is_quiet_normally(self):
        script = self.makeScript()
        script.setUp()
        script.logger = BufferLogger()
        script.logger.setLevel(logging.INFO)
        script.recoverWorkingDists()
        self.assertEqual('', script.logger.getLogBuffer())

    def test_recoverWorkingDists_recovers_working_directory(self):
        distro = self.makeDistroWithPublishDirectory()
        script = self.makeScript(distro)
        script.setUp()
        script.logger = BufferLogger()
        script.logger.setLevel(logging.INFO)
        script.setUpDirs()
        archive_config = getPubConfig(distro.main_archive)
        backup_dists = os.path.join(
            archive_config.archiveroot + "-distscopy", "dists")
        working_dists = get_working_dists(archive_config)
        os.rename(backup_dists, working_dists)
        write_marker_file([working_dists, "marker"], "Recovered")
        script.recoverWorkingDists()
        self.assertEqual(
            "Recovered", read_marker_file([backup_dists, "marker"]))
        self.assertNotEqual('', script.logger.getLogBuffer())

    def test_publishes_first_security_updates_then_all_updates(self):
        script = self.makeScript()
        script.publish = FakeMethod()
        script.main()
        self.assertEqual(2, script.publish.call_count)
        args, kwargs = script.publish.calls[0]
        self.assertEqual({'security_only': True}, kwargs)
        args, kwargs = script.publish.calls[1]
        self.assertEqual(False, kwargs.get('security_only', False))

    def test_security_run_publishes_only_security_updates(self):
        script = self.makeScript(extra_args=['--security-only'])
        script.runFinalizeParts = FakeMethod()
        script.publish = FakeMethod(result=True)
        script.main()
        self.assertEqual(1, script.publish.call_count)
        args, kwargs = script.publish.calls[0]
        self.assertEqual({'security_only': True}, kwargs)
        self.assertEqual(1, script.runFinalizeParts.call_count)

    def test_security_run_empty_security_does_not_finalize(self):
        script = self.makeScript(extra_args=['--security-only'])
        script.runFinalizeParts = FakeMethod()
        script.publish = FakeMethod(result=False)
        script.main()
        self.assertEqual(1, script.publish.call_count)
        self.assertEqual(0, script.runFinalizeParts.call_count)

    def test_publishDistroUploads_processes_all_archives(self):
        distro = self.makeDistroWithPublishDirectory()
        partner_archive = self.factory.makeArchive(
            distribution=distro, purpose=ArchivePurpose.PARTNER)
        script = self.makeScript(distro)
        script.publishDistroArchive = FakeMethod()
        script.setUp()
        script.publishDistroUploads(distro)
        published_archives = [
            args[1] for args, kwargs in script.publishDistroArchive.calls]
        self.assertContentEqual(
            [distro.main_archive, partner_archive], published_archives)

    def test_runFinalizeParts_passes_archiveroots_correctly(self):
        # The ARCHIVEROOTS environment variable may contain spaces, and
        # these are passed through correctly.  It'll go wrong if the
        # configured archive root contains whitespace, but works with
        # Unix-sensible paths.
        distro = self.makeDistroWithPublishDirectory()
        self.factory.makeArchive(
            distribution=distro, purpose=ArchivePurpose.PARTNER)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()

        # Create a run-parts script that creates marker files in each of
        # the archive roots, and writes an expected string to them.
        # Doesn't write to a marker file that already exists, because it
        # might be a sign that the path it received is ridiculously
        # wrong.  Don't want to go overwriting random files now do we?
        self.installRunPartsScript(distro, "finalize.d", dedent("""\
            #!/bin/sh -e
            MARKER_NAME="marker file"
            for DIRECTORY in $ARCHIVEROOTS
            do
                MARKER="$DIRECTORY/$MARKER_NAME"
                if [ -e "$MARKER" ]
                then
                    echo "Marker file $MARKER already exists." >&2
                    exit 1
                fi
                echo "This is an archive root." >"$MARKER"
            done
            """))

        script.runFinalizeParts(distro)

        for archive in [distro.main_archive, distro.getArchive("partner")]:
            archive_root = getPubConfig(archive).archiveroot
            self.assertEqual(
                "This is an archive root.",
                read_marker_file([archive_root, "marker file"]).rstrip(),
                "Did not find expected marker for %s."
                % archive.purpose.title)

    def test_updateStagedFilesForSuite_installs_changed(self):
        distro = self.makeDistroWithPublishDirectory()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        archive_config = getPubConfig(distro.main_archive)
        contents_filename = "Contents-%s" % das.architecturetag
        backup_suite = os.path.join(
            archive_config.archiveroot + "-distscopy", "dists",
            distroseries.name)
        os.makedirs(backup_suite)
        write_marker_file(
            [backup_suite, "%s.gz" % contents_filename], "Old Contents")
        os.utime(
            os.path.join(backup_suite, "%s.gz" % contents_filename), (0, 0))
        staging_suite = os.path.join(
            archive_config.stagingroot, distroseries.name)
        os.makedirs(staging_suite)
        write_marker_file(
            [staging_suite, "%s.gz" % contents_filename], "Contents")
        self.assertTrue(script.updateStagedFilesForSuite(
            archive_config, distroseries.name))
        self.assertEqual(
            "Contents",
            read_marker_file([backup_suite, "%s.gz" % contents_filename]))
        self.assertThat(
            os.path.join(staging_suite, "%s.gz" % contents_filename),
            Not(PathExists()))

    def test_updateStagedFilesForSuite_installs_changed_dep11(self):
        # updateStagedFilesForSuite installs changed files other than
        # Contents files, such as DEP-11 metadata.
        distro = self.makeDistroWithPublishDirectory()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        archive_config = getPubConfig(distro.main_archive)
        backup_dep11 = os.path.join(
            archive_config.archiveroot + "-distscopy", "dists",
            distroseries.name, "main", "dep11")
        os.makedirs(backup_dep11)
        write_marker_file([backup_dep11, "a"], "Old A")
        os.utime(os.path.join(backup_dep11, "a"), (0, 0))
        staging_dep11 = os.path.join(
            archive_config.stagingroot, distroseries.name, "main", "dep11")
        os.makedirs(os.path.join(staging_dep11, "subdir"))
        write_marker_file([staging_dep11, "a"], "A")
        write_marker_file([staging_dep11, "subdir", "b"], "B")
        self.assertTrue(script.updateStagedFilesForSuite(
            archive_config, distroseries.name))
        self.assertEqual("A", read_marker_file([backup_dep11, "a"]))
        self.assertEqual("B", read_marker_file([backup_dep11, "subdir", "b"]))
        self.assertThat(os.path.join(staging_dep11, "a"), Not(PathExists()))
        self.assertThat(
            os.path.join(staging_dep11, "subdir", "b"), Not(PathExists()))

    def test_updateStagedFilesForSuite_twice(self):
        # If updateStagedFilesForSuite is run twice in a row, it does not
        # update the files the second time.
        distro = self.makeDistroWithPublishDirectory()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        archive_config = getPubConfig(distro.main_archive)
        contents_filename = "Contents-%s" % das.architecturetag
        backup_suite = os.path.join(
            archive_config.archiveroot + "-distscopy", "dists",
            distroseries.name)
        os.makedirs(backup_suite)
        staging_suite = os.path.join(
            archive_config.stagingroot, distroseries.name)
        os.makedirs(staging_suite)
        write_marker_file(
            [staging_suite, "%s.gz" % contents_filename], "Contents")
        self.assertTrue(script.updateStagedFilesForSuite(
            archive_config, distroseries.name))
        self.assertFalse(script.updateStagedFilesForSuite(
            archive_config, distroseries.name))

    def test_updateStagedFilesForSuite_ensures_world_readable(self):
        # updateStagedFilesForSuite ensures that files it stages have
        # sufficient permissions not to break mirroring.
        distro = self.makeDistroWithPublishDirectory()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        archive_config = getPubConfig(distro.main_archive)
        backup_suite = os.path.join(
            archive_config.archiveroot + "-distscopy", "dists",
            distroseries.name)
        os.makedirs(backup_suite)
        staging_suite = os.path.join(
            archive_config.stagingroot, distroseries.name)
        os.makedirs(staging_suite)
        for name, mode in (
                ("Commands-amd64", 0o644), ("Commands-i386", 0o600)):
            write_marker_file([staging_suite, name], name, mode=mode)
        self.assertTrue(script.updateStagedFilesForSuite(
            archive_config, distroseries.name))
        for name in ("Commands-amd64", "Commands-i386"):
            self.assertEqual(name, read_marker_file([backup_suite, name]))
            self.assertEqual(
                0o644,
                stat.S_IMODE(
                    os.stat(os.path.join(backup_suite, name)).st_mode))

    def test_updateStagedFiles_marks_suites_dirty(self):
        # updateStagedFiles marks the suites for which it updated staged
        # files as dirty.
        distro = self.makeDistroWithPublishDirectory()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        archive_config = getPubConfig(distro.main_archive)
        contents_filename = "Contents-%s" % das.architecturetag
        backup_suite = os.path.join(
            archive_config.archiveroot + "-distscopy", "dists",
            distroseries.name)
        os.makedirs(backup_suite)
        staging_suite = os.path.join(
            archive_config.stagingroot, distroseries.name)
        os.makedirs(staging_suite)
        write_marker_file(
            [staging_suite, "%s.gz" % contents_filename], "Contents")
        script.updateStagedFiles(distro)
        self.assertEqual([distroseries.name], distro.main_archive.dirty_suites)

    def test_updateStagedFiles_considers_partner_archive(self):
        # updateStagedFiles considers the partner archive as well as the
        # primary archive.
        distro = self.makeDistroWithPublishDirectory()
        self.factory.makeArchive(
            distribution=distro, owner=distro.owner,
            purpose=ArchivePurpose.PARTNER)
        distroseries = self.factory.makeDistroSeries(
            distribution=distro, status=SeriesStatus.DEVELOPMENT)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.updateStagedFilesForSuite = FakeMethod()
        script.updateStagedFiles(distro)
        expected_args = []
        for purpose in ArchivePurpose.PRIMARY, ArchivePurpose.PARTNER:
            expected_args.extend([
                (script.configs[distro][purpose],
                 distroseries.getSuite(pocket))
                for pocket in PackagePublishingPocket.items])
        self.assertEqual(
            expected_args, script.updateStagedFilesForSuite.extract_args())

    def test_updateStagedFiles_skips_immutable_suites(self):
        # updateStagedFiles does not update files for immutable suites.
        distro = self.makeDistroWithPublishDirectory()
        distroseries = self.factory.makeDistroSeries(
            distribution=distro, status=SeriesStatus.CURRENT)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.updateStagedFilesForSuite = FakeMethod()
        script.updateStagedFiles(distro)
        expected_args = [
            (script.configs[distro][ArchivePurpose.PRIMARY],
             distroseries.getSuite(pocket))
            for pocket in PackagePublishingPocket.items
            if pocket != PackagePublishingPocket.RELEASE]
        self.assertEqual(
            expected_args, script.updateStagedFilesForSuite.extract_args())

    def test_publish_always_returns_true_for_primary(self):
        script = self.makeScript()
        script.publishDistroUploads = FakeMethod()
        script.setUp()
        script.setUpDirs()
        result = script.publish(script.distributions[0], security_only=False)
        self.assertTrue(result)

    def test_publish_returns_true_for_non_empty_security(self):
        script = self.makeScript(extra_args=['--security-only'])
        script.setUp()
        script.setUpDirs()
        script.installDists = FakeMethod()
        script.publishSecurityUploads = FakeMethod(result=True)
        result = script.publish(script.distributions[0], security_only=True)
        self.assertTrue(result)

    def test_publish_returns_false_for_empty_security(self):
        script = self.makeScript(extra_args=['--security-only'])
        script.setUp()
        script.setUpDirs()
        script.installDists = FakeMethod()
        script.publishSecurityUploads = FakeMethod(result=False)
        result = script.publish(script.distributions[0], security_only=True)
        self.assertFalse(result)

    def test_publish_reraises_exception(self):
        # If an Exception comes up while publishing, it bubbles up out
        # of the publish method even though the method must intercept
        # it for its own purposes.
        class MoonPhaseError(Exception):
            """Simulated failure."""

        message = self.factory.getUniqueString()
        script = self.makeScript()
        script.publishDistroUploads = FakeMethod(
            failure=MoonPhaseError(message))
        script.setUp()
        self.assertRaisesWithContent(
            MoonPhaseError, message,
            script.publish, script.distributions[0])

    def test_publish_obeys_keyboard_interrupt(self):
        # Similar to an Exception, a keyboard interrupt does not get
        # swallowed.
        message = self.factory.getUniqueString()
        script = self.makeScript()
        script.publishDistroUploads = FakeMethod(
            failure=KeyboardInterrupt(message))
        script.setUp()
        self.assertRaisesWithContent(
            KeyboardInterrupt, message,
            script.publish, script.distributions[0])

    def test_publish_recovers_working_dists_on_exception(self):
        # If an Exception comes up while publishing, the publish method
        # recovers its working directory.
        class MoonPhaseError(Exception):
            """Simulated failure."""

        failure = MoonPhaseError(self.factory.getUniqueString())

        script = self.makeScript()
        script.publishDistroUploads = FakeMethod(failure=failure)
        script.recoverArchiveWorkingDir = FakeMethod()
        script.setUp()

        try:
            script.publish(script.distributions[0])
        except MoonPhaseError:
            pass

        self.assertEqual(1, script.recoverArchiveWorkingDir.call_count)

    def test_publish_recovers_working_dists_on_ctrl_C(self):
        # If the user hits ctrl-C while publishing, the publish method
        # recovers its working directory.
        failure = KeyboardInterrupt("Ctrl-C!")

        script = self.makeScript()
        script.publishDistroUploads = FakeMethod(failure=failure)
        script.recoverArchiveWorkingDir = FakeMethod()
        script.setUp()

        try:
            script.publish(script.distributions[0])
        except KeyboardInterrupt:
            pass

        self.assertEqual(1, script.recoverArchiveWorkingDir.call_count)

    def test_publish_is_not_interrupted_by_cron_control(self):
        # If cron-control switches to the disabled state in the middle of a
        # publisher run, all the subsidiary scripts are still run.
        script = self.makeScript()
        self.useFixture(MonkeyPatch(
            "lp.services.scripts.base.cronscript_enabled", FakeMethod(False)))
        process_accepted_fixture = self.useFixture(MonkeyPatch(
            "lp.archivepublisher.scripts.processaccepted.ProcessAccepted.main",
            FakeMethod()))
        publish_distro_fixture = self.useFixture(MonkeyPatch(
            "lp.archivepublisher.scripts.publishdistro.PublishDistro.main",
            FakeMethod()))
        self.assertThat(script.main, Not(Raises(MatchesException(SystemExit))))
        self.assertEqual(1, process_accepted_fixture.new_value.call_count)
        self.assertEqual(1, publish_distro_fixture.new_value.call_count)


class TestCreateDistroSeriesIndexes(TestCaseWithFactory, HelpersMixin):
    """Test initial creation of archive indexes for a `DistroSeries`."""
    layer = LaunchpadZopelessLayer

    def createIndexesMarkerDir(self, script, distroseries):
        """Create the directory for `distroseries`'s indexes marker."""
        marker = script.locateIndexesMarker(
            distroseries.distribution, get_a_suite(distroseries))
        os.makedirs(os.path.dirname(marker))

    def makeDistroSeriesNeedingIndexes(self, distribution=None):
        """Create `DistroSeries` that needs indexes created."""
        return self.factory.makeDistroSeries(
            status=SeriesStatus.FROZEN, distribution=distribution)

    def test_listSuitesNeedingIndexes_is_nonempty_for_new_frozen_series(self):
        # If a distroseries is Frozen and has not had its indexes
        # created yet, listSuitesNeedingIndexes returns a nonempty list
        # for it.
        series = self.makeDistroSeriesNeedingIndexes()
        script = self.makeScript(series.distribution)
        script.setUp()
        self.assertNotEqual([], list(script.listSuitesNeedingIndexes(series)))

    def test_listSuitesNeedingIndexes_initially_includes_entire_series(self):
        # If a series has not had any of its indexes created yet,
        # listSuitesNeedingIndexes returns all of its suites.
        series = self.makeDistroSeriesNeedingIndexes()
        script = self.makeScript(series.distribution)
        script.setUp()
        self.assertContentEqual(
            [series.getSuite(pocket) for pocket in pocketsuffix],
            script.listSuitesNeedingIndexes(series))

    def test_listSuitesNeedingIndexes_is_empty_for_nonfrozen_series(self):
        # listSuitesNeedingIndexes only returns suites for Frozen
        # distroseries.
        series = self.factory.makeDistroSeries()
        script = self.makeScript(series.distribution)
        self.assertEqual([], script.listSuitesNeedingIndexes(series))

    def test_listSuitesNeedingIndexes_is_empty_for_configless_distro(self):
        # listSuitesNeedingIndexes returns no suites for distributions
        # that have no publisher config, such as Debian.  We don't want
        # to publish such distributions.
        series = self.makeDistroSeriesNeedingIndexes()
        pub_config = get_pub_config(series.distribution)
        IMasterStore(pub_config).remove(pub_config)
        script = self.makeScript(series.distribution)
        self.assertEqual([], script.listSuitesNeedingIndexes(series))

    def test_markIndexCreationComplete_repels_listSuitesNeedingIndexes(self):
        # The effect of markIndexCreationComplete is to remove the suite
        # in question from the results of listSuitesNeedingIndexes for
        # that distroseries.
        distro = self.makeDistroWithPublishDirectory()
        series = self.makeDistroSeriesNeedingIndexes(distribution=distro)
        script = self.makeScript(distro)
        script.setUp()
        self.createIndexesMarkerDir(script, series)

        needful_suites = script.listSuitesNeedingIndexes(series)
        suite = get_a_suite(series)
        script.markIndexCreationComplete(distro, suite)
        needful_suites.remove(suite)
        self.assertContentEqual(
            needful_suites, script.listSuitesNeedingIndexes(series))

    def test_listSuitesNeedingIndexes_ignores_other_series(self):
        # listSuitesNeedingIndexes only returns suites for series that
        # need indexes created.  It ignores other distroseries.
        series = self.makeDistroSeriesNeedingIndexes()
        self.factory.makeDistroSeries(distribution=series.distribution)
        script = self.makeScript(series.distribution)
        script.setUp()
        suites = list(script.listSuitesNeedingIndexes(series))
        self.assertNotEqual([], suites)
        for suite in suites:
            self.assertThat(suite, StartsWith(series.name))

    def test_createIndexes_marks_index_creation_complete(self):
        # createIndexes calls markIndexCreationComplete for the suite.
        distro = self.makeDistroWithPublishDirectory()
        series = self.factory.makeDistroSeries(distribution=distro)
        script = self.makeScript(distro)
        script.markIndexCreationComplete = FakeMethod()
        script.runPublishDistro = FakeMethod()
        suite = get_a_suite(series)
        script.createIndexes(distro, [suite])
        self.assertEqual(
            [((distro, suite), {})], script.markIndexCreationComplete.calls)

    def test_failed_index_creation_is_not_marked_complete(self):
        # If index creation fails, it is not marked as having been
        # completed.  The next run will retry.
        class Boom(Exception):
            """Simulated failure."""

        series = self.factory.makeDistroSeries()
        script = self.makeScript(series.distribution)
        script.markIndexCreationComplete = FakeMethod()
        script.runPublishDistro = FakeMethod(failure=Boom("Sorry!"))
        try:
            script.createIndexes(series.distribution, [get_a_suite(series)])
        except Exception:
            pass
        self.assertEqual([], script.markIndexCreationComplete.calls)

    def test_locateIndexesMarker_places_file_in_archive_root(self):
        # The marker file for index creation is in the distribution's
        # archive root.
        series = self.factory.makeDistroSeries()
        script = self.makeScript(series.distribution)
        script.setUp()
        archive_root = getPubConfig(series.main_archive).archiveroot
        self.assertThat(
            script.locateIndexesMarker(
                series.distribution, get_a_suite(series)),
            StartsWith(os.path.normpath(archive_root)))

    def test_locateIndexesMarker_uses_separate_files_per_suite(self):
        # Each suite in a distroseries gets its own marker file for
        # index creation.
        distro = self.makeDistroWithPublishDirectory()
        series = self.factory.makeDistroSeries(distribution=distro)
        script = self.makeScript(distro)
        script.setUp()
        markers = get_marker_files(script, series)
        self.assertEqual(sorted(markers), sorted(list(set(markers))))

    def test_locateIndexesMarker_separates_distroseries(self):
        # Each distroseries gets its own marker files for index
        # creation.
        distro = self.makeDistroWithPublishDirectory()
        series1 = self.factory.makeDistroSeries(distribution=distro)
        series2 = self.factory.makeDistroSeries(distribution=distro)
        script = self.makeScript(distro)
        script.setUp()
        markers1 = set(get_marker_files(script, series1))
        markers2 = set(get_marker_files(script, series2))
        self.assertEqual(set(), markers1.intersection(markers2))

    def test_locateIndexMarker_uses_hidden_file(self):
        # The index-creation marker file is a "dot file," so it's not
        # visible in normal directory listings.
        series = self.factory.makeDistroSeries()
        script = self.makeScript(series.distribution)
        script.setUp()
        suite = get_a_suite(series)
        self.assertThat(
            os.path.basename(script.locateIndexesMarker(
                series.distribution, suite)),
            StartsWith("."))

    def test_script_calls_createIndexes_for_new_series(self):
        # If the script's main() finds a distroseries that needs its
        # indexes created, it calls createIndexes on that distroseries,
        # passing it all of the series' suite names.
        distro = self.makeDistroWithPublishDirectory()
        series = self.makeDistroSeriesNeedingIndexes(distribution=distro)
        script = self.makeScript(distro)
        script.createIndexes = FakeMethod()
        script.main()
        [((given_distro, given_suites), kwargs)] = script.createIndexes.calls
        self.assertEqual(distro, given_distro)
        self.assertContentEqual(
            [series.getSuite(pocket) for pocket in pocketsuffix],
            given_suites)

    def test_createIndexes_ignores_other_series(self):
        # createIndexes does not accidentally also touch other
        # distroseries than the one it's meant to.
        distro = self.makeDistroWithPublishDirectory()
        series = self.factory.makeDistroSeries(distribution=distro)
        self.factory.makeDistroSeries(distribution=distro)
        script = self.makeScript(distro)
        script.setUp()
        script.runPublishDistro = FakeMethod()
        self.createIndexesMarkerDir(script, series)
        suite = get_a_suite(series)

        script.createIndexes(distro, [suite])

        args, kwargs = script.runPublishDistro.calls[0]
        self.assertEqual([suite], kwargs['suites'])
        self.assertThat(kwargs['suites'][0], StartsWith(series.name))

    def test_prepareFreshSeries_copies_custom_uploads(self):
        distro = self.makeDistroWithPublishDirectory()
        old_series = self.factory.makeDistroSeries(
            distribution=distro, status=SeriesStatus.CURRENT)
        new_series = self.factory.makeDistroSeries(
            distribution=distro, previous_series=old_series,
            status=SeriesStatus.FROZEN)
        self.factory.makeDistroArchSeries(
            distroseries=new_series, architecturetag='i386')
        custom_upload = self.factory.makeCustomPackageUpload(
            distroseries=old_series,
            custom_type=PackageUploadCustomFormat.DEBIAN_INSTALLER,
            filename='debian-installer-images_1.0-20110805_i386.tar.gz')
        script = self.makeScript(distro)
        script.createIndexes = FakeMethod()
        script.setUp()
        have_fresh_series = script.prepareFreshSeries(distro)
        self.assertTrue(have_fresh_series)
        [copied_upload] = new_series.getPackageUploads(
            name='debian-installer-images', exact_match=False)
        [copied_custom] = copied_upload.customfiles
        self.assertEqual(
            custom_upload.customfiles[0].libraryfilealias.filename,
            copied_custom.libraryfilealias.filename)

    def test_script_creates_indexes(self):
        # End-to-end test: the script creates indexes for distroseries
        # that need them.
        test_publisher = SoyuzTestPublisher()
        series = test_publisher.setUpDefaultDistroSeries()
        series.status = SeriesStatus.FROZEN
        self.factory.makeComponentSelection(
            distroseries=series, component="main")
        self.layer.txn.commit()
        self.setUpForScriptRun(series.distribution)
        script = self.makeScript(series.distribution)
        script.main()
        self.assertEqual([], script.listSuitesNeedingIndexes(series))
        sources = os.path.join(
            getPubConfig(series.main_archive).distsroot,
            series.name, "main", "source", "Sources.gz")
        self.assertTrue(file_exists(sources))
