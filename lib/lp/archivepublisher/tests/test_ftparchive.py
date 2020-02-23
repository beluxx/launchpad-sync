# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for ftparchive.py"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import difflib
import gzip
import os
import re
import shutil
from textwrap import dedent
import time

from debian.deb822 import (
    Packages,
    Sources,
    )
from testtools.matchers import (
    Equals,
    LessThan,
    MatchesListwise,
    )
from zope.component import getUtility

from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.diskpool import DiskPool
from lp.archivepublisher.model.ftparchive import (
    AptFTPArchiveFailure,
    FTPArchiveHandler,
    )
from lp.archivepublisher.publishing import Publisher
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.config import config
from lp.services.log.logger import (
    BufferLogger,
    DevNullLogger,
    )
from lp.soyuz.enums import (
    BinaryPackageFormat,
    IndexCompressionType,
    PackagePublishingPriority,
    PackagePublishingStatus,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import switch_dbuser
from lp.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )


class SamplePublisher:
    """Publisher emulation test class."""

    def __init__(self, archive):
        self.archive = archive
        self.subcomponents = ['debian-installer']

    def isAllowed(self, distroseries, pocket):
        return True


class FakeSelectResult:
    """Receive a list and emulate a SelectResult object."""

    def __init__(self, result):
        self._result = result

    def __iter__(self):
        return iter(self._result)

    def count(self):
        return len(self._result)

    def __getslice__(self, i, j):
        return self._result[i:j]


class TestFTPArchive(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFTPArchive, self).setUp()
        switch_dbuser(config.archivepublisher.dbuser)

        self._distribution = getUtility(IDistributionSet)['ubuntutest']
        self._archive = self._distribution.main_archive
        self._config = getPubConfig(self._archive)
        self._config.setupArchiveDirs()
        self._sampledir = os.path.join(
            config.root, "lib", "lp", "archivepublisher", "tests",
            "apt-data")
        self._distsdir = self._config.distsroot
        self._confdir = self._config.miscroot
        self._pooldir = self._config.poolroot
        self._overdir = self._config.overrideroot
        self._listdir = self._config.overrideroot
        self._tempdir = self._config.temproot
        self._logger = BufferLogger()
        self._dp = DiskPool(self._pooldir, self._tempdir, self._logger)
        self._publisher = SamplePublisher(self._archive)

    def tearDown(self):
        super(TestFTPArchive, self).tearDown()
        shutil.rmtree(self._config.distroroot)

    def _verifyFile(self, filename, directory):
        """Compare byte-to-byte the given file and the respective sample.

        It's a poor way of testing files generated by apt-ftparchive.
        """
        result_path = os.path.join(directory, filename)
        with open(result_path) as result_file:
            result_text = result_file.read()
        sample_path = os.path.join(self._sampledir, filename)
        with open(sample_path) as sample_file:
            sample_text = sample_file.read()
        # When the comparison between the sample text and the generated text
        # differ, just printing the strings will be less than optimal.  Use
        # difflib to get a line-by-line comparison that makes it much more
        # immediately obvious what the differences are.
        diff_lines = difflib.ndiff(
            sample_text.splitlines(), result_text.splitlines())
        self.assertEqual(sample_text, result_text, '\n'.join(diff_lines))

    def _verifyDeb822(self, filename, directory, deb822_factory,
                      result_suffix="", result_open_func=open):
        """Compare the given file and the respective sample as deb822 files."""
        result_path = os.path.join(directory, filename) + result_suffix
        with result_open_func(result_path) as result_file:
            result = list(deb822_factory(result_file))
        sample_path = os.path.join(self._sampledir, filename)
        with open(sample_path) as sample_file:
            sample = list(deb822_factory(sample_file))
        self.assertThat(
            result, MatchesListwise([Equals(stanza) for stanza in sample]))

    def _verifyEmpty(self, path, open_func=open):
        """Assert that the given file is empty."""
        with open_func(path) as result_file:
            self.assertEqual("", result_file.read())

    def _addRepositoryFile(self, component, sourcename, leafname,
                           samplename=None):
        """Create a repository file."""
        fullpath = self._dp.pathFor(component, sourcename, leafname)
        dirname = os.path.dirname(fullpath)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        if samplename is None:
            samplename = leafname
        leaf = os.path.join(self._sampledir, samplename)
        with open(leaf) as leaf_file:
            leafcontent = leaf_file.read()
        with open(fullpath, "w") as f:
            f.write(leafcontent)

    def _setUpFTPArchiveHandler(self):
        return FTPArchiveHandler(
            self._logger, self._config, self._dp, self._distribution,
            self._publisher)

    def _setUpSampleDataFTPArchiveHandler(self):
        # Reconfigure FTPArchiveHandler to retrieve sampledata records.
        fa = self._setUpFTPArchiveHandler()
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        fa.distro = ubuntu
        fa.publisher.archive = hoary.main_archive
        return fa, hoary

    def _publishDefaultOverrides(self, fa, component, section='devel',
                                 phased_update_percentage=None,
                                 binpackageformat=BinaryPackageFormat.DEB):
        source_overrides = FakeSelectResult([('tiny', component, section)])
        binary_overrides = FakeSelectResult([(
            'tiny', component, section, 'i386',
            PackagePublishingPriority.EXTRA, binpackageformat,
            phased_update_percentage)])
        fa.publishOverrides('hoary-test', source_overrides, binary_overrides)

    def _publishDefaultFileLists(self, fa, component):
        source_files = FakeSelectResult([('tiny', 'tiny_0.1.dsc', component)])
        binary_files = FakeSelectResult(
            [('tiny', 'tiny_0.1_i386.deb', component, 'binary-i386')])
        fa.publishFileLists('hoary-test', source_files, binary_files)

    def test_getSourcesForOverrides(self):
        # getSourcesForOverrides returns a list of tuples containing:
        # (sourcename, component, section)
        fa, hoary = self._setUpSampleDataFTPArchiveHandler()
        published_sources = fa.getSourcesForOverrides(
            hoary, PackagePublishingPocket.RELEASE)

        # For the above query, we are depending on the sample data to
        # contain seven rows of SourcePackagePublishingHistory data.
        expectedSources = [
            ('linux-source-2.6.15', 'main', 'base'),
            ('libstdc++', 'main', 'base'),
            ('cnews', 'universe', 'base'),
            ('alsa-utils', 'main', 'base'),
            ('pmount', 'main', 'editors'),
            ('netapplet', 'main', 'web'),
            ('evolution', 'main', 'editors'),
            ]
        self.assertEqual(expectedSources, list(published_sources))

    def test_getBinariesForOverrides(self):
        # getBinariesForOverrides returns a list of tuples containing:
        # (sourcename, component, section, archtag, priority,
        # phased_update_percentage)
        fa, hoary = self._setUpSampleDataFTPArchiveHandler()
        published_binaries = fa.getBinariesForOverrides(
            hoary, PackagePublishingPocket.RELEASE)
        expectedBinaries = [
            ('pmount', 'main', 'base', 'hppa',
             PackagePublishingPriority.EXTRA, BinaryPackageFormat.DEB, None),
            ('pmount', 'universe', 'editors', 'i386',
             PackagePublishingPriority.IMPORTANT, BinaryPackageFormat.DEB,
             None),
            ]
        self.assertEqual(expectedBinaries, list(published_binaries))

    def test_getBinariesForOverrides_with_no_architectures(self):
        # getBinariesForOverrides() copes with uninitiazed distroseries
        # (no architectures), returning an empty ResultSet.
        fa = self._setUpFTPArchiveHandler()

        breezy_autotest = self._distribution.getSeries('breezy-autotest')
        self.assertEqual([], list(breezy_autotest.architectures))

        published_binaries = fa.getBinariesForOverrides(
            breezy_autotest, PackagePublishingPocket.RELEASE)
        self.assertEqual([], list(published_binaries))

    def test_publishOverrides(self):
        # publishOverrides write the expected files on disk.
        fa = self._setUpFTPArchiveHandler()
        self._publishDefaultOverrides(fa, 'main')

        # Check that the overrides lists generated by LP exist and have the
        # expected contents.
        self._verifyFile("override.hoary-test.main", self._overdir)
        self._verifyFile("override.hoary-test.main.src", self._overdir)
        self._verifyFile("override.hoary-test.extra.main", self._overdir)

    def test_publishOverrides_more_extra_components(self):
        # more-extra.override.%s.main is used regardless of component.
        fa = self._setUpFTPArchiveHandler()

        sentinel = ("hello/i386", "Task", "minimal")
        extra_overrides = os.path.join(
            self._confdir, "more-extra.override.hoary-test.main")
        with open(extra_overrides, "w") as extra_override_file:
            print("  ".join(sentinel), file=extra_override_file)
        self._publishDefaultOverrides(fa, 'universe')

        result_path = os.path.join(
            self._overdir, "override.hoary-test.extra.universe")
        with open(result_path) as result_file:
            self.assertIn("\t".join(sentinel), result_file.read().splitlines())

    def test_publishOverrides_phase(self):
        # Publications with a non-None phased update percentage produce
        # Phased-Update-Percentage extra overrides.
        fa = self._setUpFTPArchiveHandler()
        self._publishDefaultOverrides(fa, 'main', phased_update_percentage=50)

        path = os.path.join(self._overdir, "override.hoary-test.extra.main")
        with open(path) as result_file:
            self.assertIn(
                "tiny/i386\tPhased-Update-Percentage\t50",
                result_file.read().splitlines())

    def test_publishOverrides_udebs(self):
        # udeb overrides appear in a separate file.
        fa = self._setUpFTPArchiveHandler()
        self._publishDefaultOverrides(
            fa, 'main', section='debian-installer',
            binpackageformat=BinaryPackageFormat.UDEB)

        # The main override file is empty.
        stat = os.stat(os.path.join(self._overdir, "override.hoary-test.main"))
        self.assertEqual(0, stat.st_size)

        # The binary shows up in the d-i override file.
        path = os.path.join(
            self._overdir, "override.hoary-test.main.debian-installer")
        with open(path) as result_file:
            self.assertEqual(
                ["tiny\textra\tdebian-installer"],
                result_file.read().splitlines())

    def test_publishOverrides_ddebs_disabled(self):
        # ddebs aren't indexed if Archive.publish_debug_symbols is unset.
        fa = self._setUpFTPArchiveHandler()
        self._publishDefaultOverrides(
            fa, 'main', binpackageformat=BinaryPackageFormat.DDEB)

        # The main override file is empty, and there's no ddeb override
        # file.
        stat = os.stat(os.path.join(self._overdir, "override.hoary-test.main"))
        self.assertEqual(0, stat.st_size)
        self.assertFalse(
            os.path.exists(
                os.path.join(self._overdir, "override.hoary-test.main.debug")))

    def test_publishOverrides_ddebs(self):
        # ddebs are indexed in a subcomponent if
        # Archive.publish_debug_symbols is set.
        fa = self._setUpFTPArchiveHandler()
        fa.publisher.subcomponents.append('debug')
        self._publishDefaultOverrides(
            fa, 'main', binpackageformat=BinaryPackageFormat.DDEB)

        # The main override file is empty.
        stat = os.stat(os.path.join(self._overdir, "override.hoary-test.main"))
        self.assertEqual(0, stat.st_size)

        # The binary shows up in the debug override file.
        path = os.path.join(self._overdir, "override.hoary-test.main.debug")
        with open(path) as result_file:
            self.assertEqual(
                ["tiny\textra\tdevel"], result_file.read().splitlines())

    def test_generateOverrides(self):
        # generateOverrides generates all the overrides from start to finish.
        self._distribution = getUtility(IDistributionSet).getByName('ubuntu')
        self._archive = self._distribution.main_archive
        self._publisher = SamplePublisher(self._archive)
        fa = self._setUpFTPArchiveHandler()
        pubs = self._archive.getAllPublishedBinaries(
            name="pmount", status=PackagePublishingStatus.PUBLISHED,
            distroarchseries=self._distribution.getSeries("hoary")["hppa"])
        for pub in pubs:
            pub.changeOverride(new_phased_update_percentage=30).setPublished()
        fa.generateOverrides(fullpublish=True)
        result_path = os.path.join(self._overdir, "override.hoary.main")
        with open(result_path) as result_file:
            self.assertEqual("pmount\textra\tbase\n", result_file.read())
        result_path = os.path.join(self._overdir, "override.hoary.main.src")
        with open(result_path) as result_file:
            self.assertIn("pmount\teditors\n", result_file.readlines())
        result_path = os.path.join(self._overdir, "override.hoary.extra.main")
        with open(result_path) as result_file:
            self.assertEqual(dedent("""\
                pmount\tOrigin\tUbuntu
                pmount\tBugs\thttps://bugs.launchpad.net/ubuntu/+filebug
                pmount/hppa\tPhased-Update-Percentage\t30
                """), result_file.read())

    def test_getSourceFiles(self):
        # getSourceFiles returns a list of tuples containing:
        # (sourcename, filename, component)
        fa, hoary = self._setUpSampleDataFTPArchiveHandler()
        sources_files = fa.getSourceFiles(
            hoary, PackagePublishingPocket.RELEASE)
        expected_files = [
            ('alsa-utils', 'alsa-utils_1.0.9a-4ubuntu1.dsc', 'main'),
            ('evolution', 'evolution-1.0.tar.gz', 'main'),
            ('netapplet', 'netapplet_1.0.0.orig.tar.gz', 'main'),
            ]
        self.assertEqual(expected_files, list(sources_files))

    def test_getBinaryFiles(self):
        # getBinaryFiles returns a list of tuples containing:
        # (sourcename, filename, component, architecture)
        fa, hoary = self._setUpSampleDataFTPArchiveHandler()
        binary_files = fa.getBinaryFiles(
            hoary, PackagePublishingPocket.RELEASE)
        expected_files = [
            ('pmount', 'pmount_1.9-1_all.deb', 'main', 'binary-hppa'),
            ]
        self.assertEqual(expected_files, list(binary_files))

    def makeDDEBPub(self, series):
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagename='foo', sourcepackagename='foo', version='666',
            archive=series.main_archive, distroarchseries=series['hppa'],
            pocket=PackagePublishingPocket.RELEASE,
            component='main', with_debug=True, with_file=True,
            status=PackagePublishingStatus.PUBLISHED,
            architecturespecific=True)

    def test_getBinaryFiles_ddebs_disabled(self):
        # getBinaryFiles excludes ddebs unless publish_debug_symbols is
        # enabled.
        fa, hoary = self._setUpSampleDataFTPArchiveHandler()
        self.makeDDEBPub(hoary)
        binary_files = fa.getBinaryFiles(
            hoary, PackagePublishingPocket.RELEASE)
        expected_files = [
            ('foo', 'foo_666_hppa.deb', 'main', 'binary-hppa'),
            ('pmount', 'pmount_1.9-1_all.deb', 'main', 'binary-hppa'),
            ]
        self.assertEqual(expected_files, list(binary_files))

    def test_getBinaryFiles_ddebs_enabled(self):
        # getBinaryFiles includes ddebs if publish_debug_symbols is
        # enabled.
        fa, hoary = self._setUpSampleDataFTPArchiveHandler()
        fa.publisher.archive.publish_debug_symbols = True
        self.makeDDEBPub(hoary)
        binary_files = fa.getBinaryFiles(
            hoary, PackagePublishingPocket.RELEASE)
        expected_files = [
            ('foo', 'foo-dbgsym_666_hppa.ddeb', 'main', 'binary-hppa'),
            ('foo', 'foo_666_hppa.deb', 'main', 'binary-hppa'),
            ('pmount', 'pmount_1.9-1_all.deb', 'main', 'binary-hppa'),
            ]
        self.assertEqual(expected_files, list(binary_files))

    def test_publishFileLists(self):
        # publishFileLists writes the expected files on disk.
        fa = self._setUpFTPArchiveHandler()
        self._publishDefaultFileLists(fa, 'main')

        # Check that the file lists generated by LP exist and have the
        # expected contents.
        self._verifyFile("hoary-test_main_source", self._listdir)
        self._verifyFile("hoary-test_main_binary-i386", self._listdir)

    def test_generateConfig(self):
        # Generate apt-ftparchive configuration file and run it.

        # Setup FTPArchiveHandler with a real Publisher for Ubuntutest.
        publisher = Publisher(
            self._logger, self._config, self._dp, self._archive)
        fa = FTPArchiveHandler(self._logger, self._config, self._dp,
                               self._distribution, publisher)
        fa.createEmptyPocketRequests(fullpublish=True)

        # Calculate overrides and filelists.
        self._publishDefaultOverrides(fa, 'main')
        self._publishDefaultFileLists(fa, 'main')

        # Add mentioned files in the repository pool/.
        self._addRepositoryFile('main', 'tiny', 'tiny_0.1.dsc')
        self._addRepositoryFile('main', 'tiny', 'tiny_0.1.tar.gz')
        self._addRepositoryFile('main', 'tiny', 'tiny_0.1_i386.deb')

        # When include_long_descriptions is set, apt.conf has
        # LongDescription "true" for that series.
        hoary_test = self._distribution.getSeries('hoary-test')
        self.assertTrue(hoary_test.include_long_descriptions)
        breezy_autotest = self._distribution.getSeries('breezy-autotest')
        breezy_autotest.include_long_descriptions = False

        # XXX cprov 2007-03-21: Relying on byte-to-byte configuration file
        # comparing is weak. We should improve this methodology to avoid
        # wasting time on test failures due to irrelevant format changes.
        apt_conf = fa.generateConfig(fullpublish=True)
        self._verifyFile("apt.conf", self._confdir)

        # XXX cprov 2007-03-21: This is an extra problem. Running a-f on
        # developer machines is wasteful. We need to find a away to split
        # those kind of tests and avoid to run it when performing 'make
        # check'. Although they should remain active in PQM to avoid possible
        # regressions.
        fa.runApt(apt_conf)
        self._verifyDeb822(
            "Packages",
            os.path.join(self._distsdir, "hoary-test", "main", "binary-i386"),
            Packages.iter_paragraphs,
            result_suffix=".gz", result_open_func=gzip.open)
        self._verifyEmpty(
            os.path.join(
                self._distsdir, "hoary-test", "main", "debian-installer",
                "binary-i386", "Packages.gz"),
            open_func=gzip.open)
        self._verifyDeb822(
            "Sources",
            os.path.join(self._distsdir, "hoary-test", "main", "source"),
            Sources.iter_paragraphs,
            result_suffix=".gz", result_open_func=gzip.open)

        # XXX cprov 2007-03-21: see above, byte-to-byte configuration
        # comparing is weak.
        # Test that a publisher run now will generate an empty apt
        # config and nothing else.
        apt_conf = fa.generateConfig()
        with open(apt_conf) as apt_conf_file:
            self.assertEqual(22, len(apt_conf_file.readlines()))

        # XXX cprov 2007-03-21: see above, do not run a-f on dev machines.
        fa.runApt(apt_conf)

    def test_generateConfig_empty_and_careful(self):
        # Generate apt-ftparchive config for an specific empty suite.
        #
        # By passing 'careful_apt' option associated with 'allowed_suite'
        # we can publish only a specific group of the suites even if they
        # are still empty. It makes APT clients happier during development
        # cycle.
        #
        # This test should check:
        #
        #  * if apt.conf was generated correctly.
        #  * a-f runs based on this config without any errors
        #  * a-f *only* creates the wanted archive indexes.
        allowed_suites = set()
        allowed_suites.add(('hoary-test', PackagePublishingPocket.UPDATES))

        publisher = Publisher(
            self._logger, self._config, self._dp,
            allowed_suites=allowed_suites, archive=self._archive)

        fa = FTPArchiveHandler(self._logger, self._config, self._dp,
                               self._distribution, publisher)

        fa.createEmptyPocketRequests(fullpublish=True)

        # createEmptyPocketRequests creates empty override and file
        # listings.
        lists = (
            'hoary-test-updates_main_source',
            'hoary-test-updates_main_binary-i386',
            'hoary-test-updates_main_debian-installer_binary-i386',
            'override.hoary-test-updates.main',
            'override.hoary-test-updates.extra.main',
            'override.hoary-test-updates.main.src',
            )

        for listname in lists:
            path = os.path.join(self._config.overrideroot, listname)
            self._verifyEmpty(path)

        # XXX cprov 2007-03-21: see above, byte-to-byte configuration
        # comparing is weak.
        apt_conf = fa.generateConfig(fullpublish=True)
        self.assertTrue(os.path.exists(apt_conf))
        with open(apt_conf) as apt_conf_file:
            apt_conf_content = apt_conf_file.read()
        with open(os.path.join(
                self._sampledir, 'apt_conf_single_empty_suite_test')) as f:
            sample_content = f.read()
        self.assertEqual(apt_conf_content, sample_content)

        # XXX cprov 2007-03-21: see above, do not run a-f on dev machines.
        fa.runApt(apt_conf)
        self.assertTrue(os.path.exists(
            os.path.join(self._distsdir, "hoary-test-updates", "main",
                         "binary-i386", "Packages.gz")))
        self.assertTrue(os.path.exists(
            os.path.join(self._distsdir, "hoary-test-updates", "main",
                         "debian-installer", "binary-i386", "Packages.gz")))
        self.assertTrue(os.path.exists(
            os.path.join(self._distsdir, "hoary-test-updates", "main",
                         "source", "Sources.gz")))

        self.assertFalse(os.path.exists(
            os.path.join(self._distsdir, "hoary-test", "main",
                         "binary-i386", "Packages.gz")))
        self.assertFalse(os.path.exists(
            os.path.join(self._distsdir, "hoary-test", "main",
                         "debian-installer", "binary-i386", "Packages.gz")))
        self.assertFalse(os.path.exists(
            os.path.join(self._distsdir, "hoary-test", "main",
                         "source", "Sources.gz")))

    def test_generateConfig_index_compressors_changed(self):
        # If index_compressors changes between runs, then old compressed
        # files are removed.
        publisher = Publisher(
            self._logger, self._config, self._dp, self._archive)
        fa = FTPArchiveHandler(
            self._logger, self._config, self._dp, self._distribution,
            publisher)
        fa.createEmptyPocketRequests(fullpublish=True)
        self._publishDefaultOverrides(fa, "main")
        self._publishDefaultFileLists(fa, "main")
        self._addRepositoryFile("main", "tiny", "tiny_0.1.dsc")
        self._addRepositoryFile("main", "tiny", "tiny_0.1.tar.gz")
        self._addRepositoryFile("main", "tiny", "tiny_0.1_i386.deb")
        comp_dir = os.path.join(self._distsdir, "hoary-test", "main")
        os.makedirs(os.path.join(comp_dir, "signed"))
        with open(os.path.join(comp_dir, "signed", "stuff"), "w"):
            pass
        os.symlink("signed", os.path.join(comp_dir, "uefi"))
        os.makedirs(os.path.join(comp_dir, "i18n"))
        for name in ("Translation-de", "Translation-de.gz", "Translation-en",
                     "Translation-en.Z"):
            with open(os.path.join(comp_dir, "i18n", name), "w"):
                pass
        self._distribution["hoary-test"].include_long_descriptions = False

        # Run the publisher once with gzip and bzip2 compressors.
        apt_conf = fa.generateConfig(fullpublish=True)
        with open(apt_conf) as apt_conf_file:
            self.assertIn(
                'Packages::Compress "gzip bzip2";', apt_conf_file.read())
        fa.runApt(apt_conf)
        self.assertContentEqual(
            ["Packages.gz", "Packages.bz2"],
            os.listdir(os.path.join(comp_dir, "binary-i386")))
        self.assertContentEqual(
            ["Packages.gz", "Packages.bz2"],
            os.listdir(os.path.join(
                comp_dir, "debian-installer", "binary-i386")))
        self.assertContentEqual(
            ["Sources.gz", "Sources.bz2"],
            os.listdir(os.path.join(comp_dir, "source")))
        self.assertContentEqual(
            ["Translation-de", "Translation-de.gz", "Translation-en.gz",
             "Translation-en.bz2"],
            os.listdir(os.path.join(comp_dir, "i18n")))

        # Try again, this time with gzip and xz compressors.  There are no
        # bzip2 leftovers, but other files are left untouched.
        self._distribution["hoary-test"].index_compressors = [
            IndexCompressionType.GZIP, IndexCompressionType.XZ]
        apt_conf = fa.generateConfig(fullpublish=True)
        with open(apt_conf) as apt_conf_file:
            self.assertIn(
                'Packages::Compress "gzip xz";', apt_conf_file.read())
        fa.runApt(apt_conf)
        self.assertContentEqual(
            ["Packages.gz", "Packages.xz"],
            os.listdir(os.path.join(comp_dir, "binary-i386")))
        self.assertContentEqual(
            ["Packages.gz", "Packages.xz"],
            os.listdir(os.path.join(
                comp_dir, "debian-installer", "binary-i386")))
        self.assertContentEqual(
            ["Sources.gz", "Sources.xz"],
            os.listdir(os.path.join(comp_dir, "source")))
        self.assertEqual(
            ["stuff"],
            os.listdir(os.path.join(comp_dir, "signed")))
        self.assertEqual(["stuff"], os.listdir(os.path.join(comp_dir, "uefi")))
        self.assertContentEqual(
            ["Translation-de", "Translation-de.gz", "Translation-en.gz",
             "Translation-en.xz"],
            os.listdir(os.path.join(comp_dir, "i18n")))

    def test_cleanCaches_noop_if_recent(self):
        # cleanCaches does nothing if it was run recently.
        fa = self._setUpFTPArchiveHandler()
        path = os.path.join(self._config.miscroot, "apt-cleanup.conf")
        with open(path, "w"):
            pass
        timestamp = time.time() - 1
        os.utime(path, (timestamp, timestamp))
        fa.cleanCaches()
        # The filesystem may round off subsecond parts of timestamps.
        self.assertEqual(int(timestamp), int(os.stat(path).st_mtime))

    def test_cleanCaches_union_architectures(self):
        # cleanCaches operates on the union of architectures for all
        # considered series.
        for series in self._distribution.series:
            series.status = SeriesStatus.OBSOLETE
        stable = self.factory.makeDistroSeries(
            distribution=self._distribution, status=SeriesStatus.CURRENT)
        unstable = self.factory.makeDistroSeries(
            distribution=self._distribution)
        for ds, arch in (
            (stable, "i386"), (stable, "armel"),
            (unstable, "i386"), (unstable, "armhf")):
            self.factory.makeDistroArchSeries(
                distroseries=ds, architecturetag=arch)
        self._publisher = Publisher(
            self._logger, self._config, self._dp, self._archive)
        fa = self._setUpFTPArchiveHandler()
        fa.cleanCaches()
        path = os.path.join(self._config.miscroot, "apt-cleanup.conf")
        with open(path) as config_file:
            arch_lines = [
                line for line in config_file if " Architectures " in line]
        self.assertNotEqual([], arch_lines)
        for line in arch_lines:
            match = re.search(r' Architectures "(.*)"', line)
            self.assertIsNotNone(match)
            config_arches = set(match.group(1).split())
            config_arches.discard("source")
            self.assertContentEqual(["armel", "armhf", "i386"], config_arches)

    def test_cleanCaches(self):
        # cleanCaches does real work.
        self._publisher = Publisher(
            self._logger, self._config, self._dp, self._archive)
        fa = self._setUpFTPArchiveHandler()
        fa.createEmptyPocketRequests(fullpublish=True)

        # Set up an initial repository.
        source_overrides = FakeSelectResult([("tiny", "main", "devel")])
        binary_overrides = FakeSelectResult([(
            "bin%d" % i, "main", "misc", "i386",
            PackagePublishingPriority.EXTRA, BinaryPackageFormat.DEB, None)
            for i in range(50)])
        fa.publishOverrides("hoary-test", source_overrides, binary_overrides)
        source_files = FakeSelectResult([("tiny", "tiny_0.1.dsc", "main")])
        binary_files = FakeSelectResult([(
            "bin%d" % i, "bin%d_1_i386.deb" % i, "main", "binary-i386")
            for i in range(50)])
        fa.publishFileLists("hoary-test", source_files, binary_files)
        self._addRepositoryFile("main", "tiny", "tiny_0.1.dsc")
        for i in range(50):
            self._addRepositoryFile(
                "main", "bin%d" % i, "bin%d_1_i386.deb" % i,
                samplename="tiny_0.1_i386.deb")
        apt_conf = fa.generateConfig(fullpublish=True)
        fa.runApt(apt_conf)

        # Remove most of this repository's files so that cleanCaches has
        # something to do.
        for i in range(49):
            os.unlink(
                self._dp.pathFor("main", "bin%d" % i, "bin%d_1_i386.deb" % i))

        cache_path = os.path.join(self._config.cacheroot, "packages-i386.db")
        old_cache_size = os.stat(cache_path).st_size
        fa.cleanCaches()
        self.assertThat(os.stat(cache_path).st_size, LessThan(old_cache_size))


class TestFTPArchiveRunApt(TestCaseWithFactory):
    """Test `FTPArchive`'s execution of apt-ftparchive."""

    layer = ZopelessDatabaseLayer

    def test_runApt_reports_failure(self):
        # If we sabotage apt-ftparchive, runApt notices that it failed
        # and raises an exception.
        distroarchseries = self.factory.makeDistroArchSeries()
        distro = distroarchseries.distroseries.distribution
        fa = FTPArchiveHandler(DevNullLogger(), None, None, distro, None)
        self.assertRaises(AptFTPArchiveFailure, fa.runApt, "bogus-config")
