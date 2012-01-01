# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Support code for using a custom test result in test.py."""

__metaclass__ = type
__all__ = [
    'filter_tests',
    'patch_find_tests',
    ]

from unittest import TestSuite

from testtools import iterate_tests
from zope.testing.testrunner import find


def patch_find_tests(hook):
    """Add a post-processing hook to zope.testing.testrunner.find_tests.

    This is useful for things like filtering tests or listing tests.

    :param hook: A callable that takes the output of the real
        `testrunner.find_tests` and returns a thing with the same type and
        structure.
    """
    real_find_tests = find.find_tests
    def find_tests(*args):
        return hook(real_find_tests(*args))
    find.find_tests = find_tests


def filter_tests(list_name):
    """Create a hook for `patch_find_tests` that filters tests based on id.

    :param list_name: A filename that contains a newline-separated list of
        test ids, as generated by `list_tests`.
    :return: A callable that takes a result of `testrunner.find_tests` and
        returns only those tests with ids in the file 'list_name'.
    """
    def do_filter(tests_by_layer_name):
        tests = sorted(set(line.strip() for line in open(list_name, 'rb')))
        result = {}
        for layer_name, suite in tests_by_layer_name.iteritems():
            new_suite = TestSuite()
            for test in iterate_tests(suite):
                if test.id() in tests:
                    new_suite.addTest(test)
            if new_suite.countTestCases():
                result[layer_name] = new_suite
        return result
    return do_filter
