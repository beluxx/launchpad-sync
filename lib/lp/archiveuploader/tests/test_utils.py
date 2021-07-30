#!/usr/bin/python3
#
# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

import os

import six

from lp.archiveuploader.tests import datadir
from lp.archiveuploader.utils import (
    determine_binary_file_type,
    determine_source_file_type,
    DpkgSourceError,
    extract_dpkg_source,
    ParseMaintError,
    re_isadeb,
    re_issource,
    )
from lp.registry.interfaces.sourcepackage import SourcePackageFileType
from lp.soyuz.enums import BinaryPackageFileType
from lp.testing import TestCase


class TestUtilities(TestCase):

    def test_determine_source_file_type(self):
        """lp.archiveuploader.utils.determine_source_file_type should work."""

        # .dsc -> DSC
        self.assertEqual(
            determine_source_file_type('foo_1.0-1.dsc'),
            SourcePackageFileType.DSC)

        # .diff.gz -> DIFF
        self.assertEqual(
            determine_source_file_type('foo_1.0-1.diff.gz'),
            SourcePackageFileType.DIFF)

        # DIFFs can only be gzipped.
        self.assertEqual(
            determine_source_file_type('foo_1.0.diff.bz2'), None)

        # Plain original tarballs can be gzipped or bzip2ed.
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig.tar.gz'),
            SourcePackageFileType.ORIG_TARBALL)
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig.tar.bz2'),
            SourcePackageFileType.ORIG_TARBALL)
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig.tar.xz'),
            SourcePackageFileType.ORIG_TARBALL)

        # Component original tarballs too.
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig-foo.tar.gz'),
            SourcePackageFileType.COMPONENT_ORIG_TARBALL)
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig-bar.tar.bz2'),
            SourcePackageFileType.COMPONENT_ORIG_TARBALL)
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig-bar.tar.xz'),
            SourcePackageFileType.COMPONENT_ORIG_TARBALL)

        # And Debian tarballs...
        self.assertEqual(
            determine_source_file_type('foo_1.0-1.debian.tar.gz'),
            SourcePackageFileType.DEBIAN_TARBALL)
        self.assertEqual(
            determine_source_file_type('foo_1.0-2.debian.tar.bz2'),
            SourcePackageFileType.DEBIAN_TARBALL)
        self.assertEqual(
            determine_source_file_type('foo_1.0-2.debian.tar.xz'),
            SourcePackageFileType.DEBIAN_TARBALL)

        # And even native tarballs!
        self.assertEqual(
            determine_source_file_type('foo_1.0.tar.gz'),
            SourcePackageFileType.NATIVE_TARBALL)
        self.assertEqual(
            determine_source_file_type('foo_1.0.tar.bz2'),
            SourcePackageFileType.NATIVE_TARBALL)
        self.assertEqual(
            determine_source_file_type('foo_1.0.tar.xz'),
            SourcePackageFileType.NATIVE_TARBALL)

        # (Component) original tarball signatures are detected for any
        # supported compression method.
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig.tar.gz.asc'),
            SourcePackageFileType.ORIG_TARBALL_SIGNATURE)
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig.tar.bz2.asc'),
            SourcePackageFileType.ORIG_TARBALL_SIGNATURE)
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig.tar.xz.asc'),
            SourcePackageFileType.ORIG_TARBALL_SIGNATURE)
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig-foo.tar.gz.asc'),
            SourcePackageFileType.COMPONENT_ORIG_TARBALL_SIGNATURE)
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig-bar.tar.bz2.asc'),
            SourcePackageFileType.COMPONENT_ORIG_TARBALL_SIGNATURE)
        self.assertEqual(
            determine_source_file_type('foo_1.0.orig-bar.tar.xz.asc'),
            SourcePackageFileType.COMPONENT_ORIG_TARBALL_SIGNATURE)

        self.assertIsNone(determine_source_file_type('foo_1.0'))
        self.assertIsNone(determine_source_file_type('foo_1.0.blah.gz'))

    def test_determine_binary_file_type(self):
        """lp.archiveuploader.utils.determine_binary_file_type should work."""
        # .deb -> DEB
        self.assertEqual(
            determine_binary_file_type('foo_1.0-1_all.deb'),
            BinaryPackageFileType.DEB)

        # .ddeb -> DDEB
        self.assertEqual(
            determine_binary_file_type('foo_1.0-1_all.ddeb'),
            BinaryPackageFileType.DDEB)

        # .udeb -> UDEB
        self.assertEqual(
            determine_binary_file_type('foo_1.0-1_all.udeb'),
            BinaryPackageFileType.UDEB)

        self.assertEqual(determine_binary_file_type('foo_1.0'), None)
        self.assertEqual(determine_binary_file_type('foo_1.0.notdeb'), None)

    def testPrefixMultilineString(self):
        """lp.archiveuploader.utils.prefix_multi_line_string should work"""
        from lp.archiveuploader.utils import prefix_multi_line_string
        self.assertEqual("A:foo\nA:bar",
                         prefix_multi_line_string("foo\nbar", "A:"))
        self.assertEqual("A:foo\nA:bar",
                         prefix_multi_line_string("foo\n\nbar", "A:"))
        self.assertEqual("A:foo\nA:\nA:bar",
                         prefix_multi_line_string("foo\n\nbar", "A:", 1))

    def testExtractComponent(self):
        """lp.archiveuploader.utils.extract_component_from_section should work
        """
        from lp.archiveuploader.utils import extract_component_from_section

        (sect, comp) = extract_component_from_section("libs")
        self.assertEqual(sect, "libs")
        self.assertEqual(comp, "main")

        (sect, comp) = extract_component_from_section("restricted/libs")
        self.assertEqual(sect, "libs")
        self.assertEqual(comp, "restricted")

        (sect, comp) = extract_component_from_section("libs", "multiverse")
        self.assertEqual(sect, "libs")
        self.assertEqual(comp, "multiverse")

        (sect, comp) = extract_component_from_section("restricted/libs",
                                                      "multiverse")
        self.assertEqual(sect, "libs")
        self.assertEqual(comp, "restricted")

    def testParseMaintainerOkay(self):
        """lp.archiveuploader.utils.parse_maintainer should parse correctly
        """
        from lp.archiveuploader.utils import (
            parse_maintainer_bytes,
            rfc822_encode_address,
            )
        cases = (
            (b"No\xc3\xa8l K\xc3\xb6the <noel@debian.org>",
             u"No\xe8l K\xf6the <noel@debian.org>",
             u"No\xe8l K\xf6the",
             u"noel@debian.org"),

            (b"No\xe8l K\xf6the <noel@debian.org>",
             u"No\xe8l K\xf6the <noel@debian.org>",
             u"No\xe8l K\xf6the",
             u"noel@debian.org"),

            ("James Troup <james@nocrew.org>",
             u"James Troup <james@nocrew.org>",
             u"James Troup",
             u"james@nocrew.org"),

            ("James J. Troup <james@nocrew.org>",
             u"james@nocrew.org (James J. Troup)",
             u"James J. Troup",
             u"james@nocrew.org"),

            ("James J, Troup <james@nocrew.org>",
             u"james@nocrew.org (James J, Troup)",
             u"James J, Troup",
             u"james@nocrew.org"),

            ("james@nocrew.org",
             u" <james@nocrew.org>",
             u"",
             u"james@nocrew.org"),

            ("<james@nocrew.org>",
             u" <james@nocrew.org>",
             u"",
             u"james@nocrew.org"),

            ("Cris van Pelt <\"Cris van Pelt\"@tribe.eu.org>",
             u"Cris van Pelt <\"Cris van Pelt\"@tribe.eu.org>",
             u"Cris van Pelt",
             u"\"Cris van Pelt\"@tribe.eu.org"),

            ("Zak B. Elep <zakame@ubuntu.com>",
             u"zakame@ubuntu.com (Zak B. Elep)",
             u"Zak B. Elep",
             u"zakame@ubuntu.com"),

            ("zakame@ubuntu.com (Zak B. Elep)",
             u" <zakame@ubuntu.com (Zak B. Elep)>",
             u"",
             u"zakame@ubuntu.com (Zak B. Elep)"),
             )

        for case in cases:
            (name, email) = parse_maintainer_bytes(case[0], 'Maintainer')
            self.assertEqual(case[2], name)
            self.assertEqual(case[3], email)
            self.assertEqual(case[1], rfc822_encode_address(name, email))

    def testParseMaintainerRaises(self):
        """lp.archiveuploader.utils.parse_maintainer should raise on incorrect
           values
        """
        from lp.archiveuploader.utils import (
            parse_maintainer_bytes,
            )

        cases = (
            ("James Troup",
             'James Troup: no @ found in email address part.'),

            ("James Troup <james>",
             'James Troup <james>: no @ found in email address part.'),

            ("James Troup <james@nocrew.org",
             ("James Troup <james@nocrew.org: "
              "doesn't parse as a valid Maintainer field.")),

            (b"No\xc3\xa8l K\xc3\xb6the",
             (b'No\xc3\xa8l K\xc3\xb6the: '
              b'no @ found in email address '
              b'part.').decode('utf-8')),
        )

        for case in cases:
            try:
                parse_maintainer_bytes(case[0], 'Maintainer')
            except ParseMaintError as e:
                self.assertEqual(case[1], six.text_type(e))
            else:
                self.fail('ParseMaintError not raised')


class TestFilenameRegularExpressions(TestCase):

    def test_re_isadeb(self):
        # Verify that the three binary extensions match the regexp.
        for extension in ('deb', 'ddeb', 'udeb'):
            self.assertEqual(
                ('foo-bar', '1.0', 'i386', extension),
                re_isadeb.match('foo-bar_1.0_i386.%s' % extension).groups())

        # Some other extension doesn't match.
        self.assertIs(None, re_isadeb.match('foo-bar_1.0_i386.notdeb'))

        # A missing architecture also doesn't match.
        self.assertIs(None, re_isadeb.match('foo-bar_1.0.deb'))

    def test_re_issource(self):
        # Verify that various source extensions match the regexp.
        extensions = (
            'dsc', 'tar.gz', 'tar.bz2', 'tar.xz', 'diff.gz',
            'orig.tar.gz', 'orig.tar.bz2', 'orig.tar.xz',
            'orig-bar.tar.gz', 'orig-bar.tar.bz2', 'orig-bar.tar.xz',
            'orig-foo_bar.tar.gz',
            'debian.tar.gz', 'debian.tar.bz2', 'debian.tar.xz')
        for extension in extensions:
            self.assertEqual(
                ('foo-bar', '1.0', extension),
                re_issource.match('foo-bar_1.0.%s' % extension).groups())

        # While orig-*.tar.gz is all interpreted as extension, *orig-*.tar.gz
        # is taken to have an extension of just 'tar.gz'.
        self.assertEqual(
            ('foo-bar', '1.0.porig-bar', 'tar.gz'),
            re_issource.match('foo-bar_1.0.porig-bar.tar.gz').groups())

        # Some other extension doesn't match.
        self.assertIs(None, re_issource.match('foo-bar_1.0.notdsc'))

        # A badly formatted name also doesn't match.
        self.assertIs(None, re_issource.match('foo-bar.dsc'))

        # bzip2/xz compression for files which must be gzipped is invalid.
        self.assertIs(None, re_issource.match('foo-bar_1.0.diff.bz2'))
        self.assertIs(None, re_issource.match('foo-bar_1.0.diff.xz'))


class TestExtractDpkgSource(TestCase):
    """Tests for extract_dpkg_source."""

    def test_simple(self):
        # unpack_source unpacks in a temporary directory and returns the
        # path.
        temp_dir = self.makeTemporaryDirectory()
        extract_dpkg_source(
            datadir(os.path.join('suite', 'bar_1.0-1', 'bar_1.0-1.dsc')),
            temp_dir)
        self.assertEqual(["bar-1.0"], os.listdir(temp_dir))
        self.assertContentEqual(
            ["THIS_IS_BAR", "debian"],
            os.listdir(os.path.join(temp_dir, "bar-1.0")))

    def test_nonexistent(self):
        temp_dir = self.makeTemporaryDirectory()
        err = self.assertRaises(
            DpkgSourceError, extract_dpkg_source,
            "thispathdoesntexist", temp_dir)
        self.assertNotEqual(0, err.result)
        self.assertEqual("", err.output)
