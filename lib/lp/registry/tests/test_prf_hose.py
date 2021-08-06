# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.registry.scripts.productreleasefinder.hose."""

import logging
import os
import shutil
import tempfile
import unittest

from lp.registry.scripts.productreleasefinder.filter import (
    Filter,
    FilterPattern,
    )
from lp.registry.scripts.productreleasefinder.hose import Hose
from lp.testing import reset_logging


def instrument_method(observer, obj, name):
    """Wrap the named method of obj in an InstrumentedMethod object.

    The InstrumentedMethod object will send events to the provided observer.
    """
    func = getattr(obj, name)
    instrumented_func = _InstrumentedMethod(observer, name, func)
    setattr(obj, name, instrumented_func)


class _InstrumentedMethod:
    """Wrapper for a callable, that sends event to an observer."""

    def __init__(self, observer, name, func):
        self.observer = observer
        self.name = name
        self.callable = func

    def __call__(self, *args, **kwargs):
        self.observer.called(self.name, args, kwargs)
        try:
            value = self.callable(*args, **kwargs)
        except Exception as exc:
            self.observer.raised(self.name, exc)
            raise
        else:
            self.observer.returned(self.name, value)
            return value


class InstrumentedMethodObserver:
    """Observer for InstrumentedMethod."""

    def __init__(self, called=None, returned=None, raised=None):
        if called is not None:
            self.called = called
        if returned is not None:
            self.returned = returned
        if raised is not None:
            self.raised = raised

    def called(self, name, args, kwargs):
        """Called before an instrumented method."""
        pass

    def returned(self, name, value):
        """Called after an instrumented method returned."""
        pass

    def raised(self, name, exc):
        """Called when an instrumented method raises."""
        pass


class Hose_Logging(unittest.TestCase):
    def testCreatesDefaultLogger(self):
        """Hose creates a default logger."""
        h = Hose()
        self.assertTrue(isinstance(h.log, logging.Logger))

    def testCreatesChildLogger(self):
        """Hose creates a child logger if given a parent."""
        parent = logging.getLogger("foo")
        h = Hose(log_parent=parent)
        self.assertEqual(h.log.parent, parent)


class Hose_Filter(unittest.TestCase):
    def testCreatesFilterObject(self):
        """Hose creates a Filter object."""
        h = Hose()
        self.assertTrue(isinstance(h.filter, Filter))

    def testDefaultsFiltersToEmptyDict(self):
        """Hose creates Filter object with empty dictionary."""
        h = Hose()
        self.assertEqual(h.filter.filters, [])

    def testCreatesFiltersWithGiven(self):
        """Hose creates Filter object with dictionary given."""
        pattern = FilterPattern("foo", "http:e*")
        h = Hose([pattern])
        self.assertEqual(len(h.filter.filters), 1)
        self.assertEqual(h.filter.filters[0], pattern)


class Hose_Urls(unittest.TestCase):
    def testCallsReduceWork(self):
        """Hose constructor calls reduceWork function."""
        h = Hose.__new__(Hose)

        class Observer(InstrumentedMethodObserver):
            def __init__(self):
                self.called_it = False

            def called(self, name, args, kw):
                self.called_it = True

        obs = Observer()
        instrument_method(obs, h, "reduceWork")
        h.__init__()
        self.assertTrue(obs.called_it)

    def testPassesUrlList(self):
        """Hose constructor passes url list to reduceWork."""
        pattern = FilterPattern("foo", "http://archive.ubuntu.com/e*")
        h = Hose.__new__(Hose)

        class Observer(InstrumentedMethodObserver):
            def __init__(self):
                self.args = []

            def called(self, name, args, kw):
                self.args.append(args)

        obs = Observer()
        instrument_method(obs, h, "reduceWork")
        h.__init__([pattern])
        self.assertEqual(obs.args[0][0], ["http://archive.ubuntu.com/"])

    def testSetsUrlProperty(self):
        """Hose constructor sets urls property to reduceWork return value."""
        class TestHose(Hose):
            def reduceWork(self, url_list):
                return "wibble"

        h = TestHose()
        self.assertEqual(h.urls, "wibble")


class Hose_ReduceWork(unittest.TestCase):
    def testEmptyList(self):
        """Hose.reduceWork returns empty list when given one."""
        h = Hose()
        self.assertEqual(h.reduceWork([]), [])

    def testReducedList(self):
        """Hose.reduceWork returns same list when nothing to do."""
        h = Hose()
        self.assertEqual(h.reduceWork(["http://localhost/", "file:///usr/"]),
                         ["http://localhost/", "file:///usr/"])

    def testReducesList(self):
        """Hose.reduceWork removes children elements from list."""
        h = Hose()
        self.assertEqual(h.reduceWork(["http://localhost/",
                                       "http://localhost/foo/bar/",
                                       "http://localhost/wibble/",
                                       "file:///usr/"]),
                         ["http://localhost/", "file:///usr/"])


class Hose_LimitWalk(unittest.TestCase):

    def setUp(self):
        self.release_root = tempfile.mkdtemp()
        self.release_url = 'file://' + self.release_root

    def tearDown(self):
        shutil.rmtree(self.release_root, ignore_errors=True)
        reset_logging()

    def testHoseLimitsWalk(self):
        # Test that the hose limits the directory walk to places that
        # could contain a match.

        # Set up the releases tree:
        for directory in ['bar',
                          'foo',
                          'foo/1.0',
                          'foo/1.0/source',
                          'foo/1.0/x64',
                          'foo/1.5',
                          'foo/1.5/source',
                          'foo/2.0',
                          'foo/2.0/source']:
            os.mkdir(os.path.join(self.release_root, directory))
        for releasefile in ['foo/1.0/foo-1.0.tar.gz',
                            'foo/1.0/source/foo-1.0.tar.gz',
                            'foo/1.0/source/foo-2.0.tar.gz',
                            'foo/1.0/x64/foo-1.0.tar.gz',
                            'foo/1.5/source/foo-1.5.tar.gz',
                            'foo/2.0/source/foo-2.0.tar.gz']:
            fp = open(os.path.join(self.release_root, releasefile), 'wb')
            fp.write(b'data')
            fp.close()

        # Run the hose over the test data
        pattern = FilterPattern("key", self.release_url +
                                "/foo/1.*/source/foo-1.*.tar.gz")
        hose = Hose([pattern])

        prefix_len = len(self.release_url)
        matched = []
        unmatched = []
        for key, url in hose:
            if key is None:
                unmatched.append(url[prefix_len:])
            else:
                matched.append(url[prefix_len:])

        # Make sure that the correct releases got found.
        self.assertEqual(sorted(matched),
                         ['/foo/1.0/source/foo-1.0.tar.gz',
                          '/foo/1.5/source/foo-1.5.tar.gz'])

        # The only unmatched files that get checked exist in
        # directories that are parents of potential matches.
        self.assertEqual(sorted(unmatched),
                         ['/foo/1.0/foo-1.0.tar.gz',
                          '/foo/1.0/source/foo-2.0.tar.gz'])
