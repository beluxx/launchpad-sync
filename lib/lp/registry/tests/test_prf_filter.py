# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.registry.scripts.productreleasefinder.filter."""

import logging
import unittest

from lp.registry.scripts.productreleasefinder.filter import (
    Filter,
    FilterPattern,
)


class Filter_Logging(unittest.TestCase):
    def testCreatesDefaultLogger(self):
        """Filter creates a default logger."""
        f = Filter()
        self.assertTrue(isinstance(f.log, logging.Logger))

    def testCreatesChildLogger(self):
        """Filter creates a child logger if given a parent."""
        parent = logging.getLogger("foo")
        f = Filter(log_parent=parent)
        self.assertEqual(f.log.parent, parent)


class Filter_Init(unittest.TestCase):
    def testDefaultFiltersProperty(self):
        """Filter constructor initializes filters property to empty dict."""
        f = Filter()
        self.assertEqual(f.filters, [])

    def testFiltersPropertyGiven(self):
        """Filter constructor accepts argument to set filters property."""
        f = Filter(["wibble"])
        self.assertEqual(len(f.filters), 1)
        self.assertEqual(f.filters[0], "wibble")


class Filter_CheckUrl(unittest.TestCase):
    def testNoFilters(self):
        """Filter.check returns None if there are no filters."""
        f = Filter()
        self.assertEqual(f.check("file:///subdir/file"), None)

    def makeFilter(self, key, urlglob):
        pattern = FilterPattern(key, urlglob)
        return Filter([pattern])

    def testNotMatching(self):
        """Filter.check returns None if doesn't match a filter."""
        f = self.makeFilter("foo", "file:///subdir/w*")
        self.assertEqual(f.check("file:///subdir/file"), None)

    def testNoMatchingSlashes(self):
        """Filter.check that the glob does not match slashes."""
        f = self.makeFilter("foo", "file:///*l*")
        self.assertEqual(f.check("file:///subdir/file"), None)

    def testReturnsMatching(self):
        """Filter.check returns the matching keyword."""
        f = self.makeFilter("foo", "file:///subdir/f*e")
        self.assertEqual(f.check("file:///subdir/file"), "foo")

    def testGlobSubdir(self):
        # Filter.glob can contain slashes to match subdirs
        f = self.makeFilter("foo", "file:///sub*/f*e")
        self.assertEqual(f.check("file:///subdir/file"), "foo")

    def testReturnsNonMatchingBase(self):
        """Filter.check returns None if the base does not match."""
        f = self.makeFilter("foo", "http:f*e")
        self.assertEqual(f.check("file:///subdir/file"), None)


class Filter_IsPossibleParentUrl(unittest.TestCase):
    def makeFilter(self, key, urlglob):
        pattern = FilterPattern(key, urlglob)
        return Filter([pattern])

    def testNotContainedByMatch(self):
        # if the URL matches the pattern, then it can't contain matches.
        f = self.makeFilter("foo", "file:///subdir/foo-1.*.tar.gz")
        self.assertFalse(f.isPossibleParent("file:///subdir/foo-1.42.tar.gz"))

    def testContainedByParent(self):
        # parent directories of the match can contain the match
        f = self.makeFilter("foo", "file:///subdir/foo/bar")
        self.assertTrue(f.isPossibleParent("file:///subdir/foo/"))
        self.assertTrue(f.isPossibleParent("file:///subdir/foo"))
        self.assertTrue(f.isPossibleParent("file:///subdir"))
        self.assertTrue(f.isPossibleParent("file:///"))

    def testContainedByGlobbedParent(self):
        # test that glob matched parents can contain matches
        f = self.makeFilter("foo", "file:///subdir/1.*/foo-1.*.tar.gz")
        self.assertTrue(f.isPossibleParent("file:///subdir/1.0/"))
        self.assertTrue(f.isPossibleParent("file:///subdir/1.42"))
        self.assertTrue(f.isPossibleParent("file:///subdir/1.abc/"))
        self.assertFalse(f.isPossibleParent("file:///subdir/2.0"))
