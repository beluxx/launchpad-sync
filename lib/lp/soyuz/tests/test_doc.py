# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests and pagetests.
"""

import logging
import os
import unittest

import scandir
import transaction

from lp.services.config import config
from lp.testing import logout
from lp.testing.dbuser import switch_dbuser
from lp.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.testing.pages import (
    PageTestSuite,
    setUpGlobs,
    )
from lp.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )


here = os.path.dirname(os.path.realpath(__file__))


def lobotomize_stevea():
    """Set SteveA's email address' status to NEW.

    Call this method first in a test's setUp where needed. Tests
    using this function should be refactored to use the unaltered
    sample data and this function eventually removed.

    In the past, SteveA's account erroneously appeared in the old
    ValidPersonOrTeamCache materialized view. This materialized view
    has since been replaced and now SteveA is correctly listed as
    invalid in the sampledata. This fix broke some tests testing
    code that did not use the ValidPersonOrTeamCache to determine
    validity.
    """
    from lp.services.identity.interfaces.emailaddress import (
        EmailAddressStatus,
        )
    from lp.services.identity.model.emailaddress import EmailAddress
    stevea_emailaddress = EmailAddress.byEmail(
            'steve.alexander@ubuntulinux.com')
    stevea_emailaddress.status = EmailAddressStatus.NEW
    transaction.commit()


def uploaderSetUp(test):
    """setup the package uploader script tests."""
    setUp(test, future=True)
    switch_dbuser('uploader')


def statisticianSetUp(test):
    test_dbuser = config.statistician.dbuser
    test.globs['test_dbuser'] = test_dbuser
    switch_dbuser(test_dbuser)
    setUp(test, future=True)


def statisticianTearDown(test):
    tearDown(test)


def uploadQueueSetUp(test):
    lobotomize_stevea()
    test_dbuser = config.uploadqueue.dbuser
    switch_dbuser(test_dbuser)
    setUp(test, future=True)
    test.globs['test_dbuser'] = test_dbuser


def uploaderBugsSetUp(test):
    """Set up a test suite using the 'uploader' db user.

    Some aspects of the bug tracker are being used by the Soyuz uploader.
    In order to test that these functions work as expected from the uploader,
    we run them using the same db user used by the uploader.
    """
    lobotomize_stevea()
    test_dbuser = config.uploader.dbuser
    switch_dbuser(test_dbuser)
    setUp(test, future=True)
    test.globs['test_dbuser'] = test_dbuser


def uploaderBugsTearDown(test):
    logout()


def uploadQueueTearDown(test):
    logout()


special = {
    'package-cache.txt': LayeredDocFileSuite(
        '../doc/package-cache.txt',
        setUp=statisticianSetUp, tearDown=statisticianTearDown,
        layer=LaunchpadZopelessLayer
        ),
    'distroarchseriesbinarypackage.txt': LayeredDocFileSuite(
        '../doc/distroarchseriesbinarypackage.txt',
        setUp=lambda test: setUp(test, future=True), tearDown=tearDown,
        layer=LaunchpadZopelessLayer
        ),
    'closing-bugs-from-changelogs.txt': LayeredDocFileSuite(
        '../doc/closing-bugs-from-changelogs.txt',
        setUp=uploadQueueSetUp,
        tearDown=uploadQueueTearDown,
        layer=LaunchpadZopelessLayer
        ),
    'closing-bugs-from-changelogs.txt-uploader': LayeredDocFileSuite(
        '../doc/closing-bugs-from-changelogs.txt',
        id_extensions=['closing-bugs-from-changelogs.txt-uploader'],
        setUp=uploaderBugsSetUp,
        tearDown=uploaderBugsTearDown,
        layer=LaunchpadZopelessLayer
        ),
    'soyuz-set-of-uploads.txt': LayeredDocFileSuite(
        '../doc/soyuz-set-of-uploads.txt',
        setUp=lambda test: setUp(test, future=True),
        layer=LaunchpadZopelessLayer,
        ),
    'package-relationship.txt': LayeredDocFileSuite(
        '../doc/package-relationship.txt',
        stdout_logging=False, layer=None),
    'publishing.txt': LayeredDocFileSuite(
        '../doc/publishing.txt',
        setUp=lambda test: setUp(test, future=True),
        layer=LaunchpadZopelessLayer,
        ),
    'build-failedtoupload-workflow.txt': LayeredDocFileSuite(
        '../doc/build-failedtoupload-workflow.txt',
        setUp=lambda test: setUp(test, future=True), tearDown=tearDown,
        layer=LaunchpadZopelessLayer,
        ),
    'distroseriesqueue.txt': LayeredDocFileSuite(
        '../doc/distroseriesqueue.txt',
        setUp=lambda test: setUp(test, future=True), tearDown=tearDown,
        layer=LaunchpadZopelessLayer,
        ),
    'distroseriesqueue-notify.txt': LayeredDocFileSuite(
        '../doc/distroseriesqueue-notify.txt',
        setUp=lambda test: setUp(test, future=True), tearDown=tearDown,
        layer=LaunchpadZopelessLayer,
        ),
    'distroseriesqueue-translations.txt': LayeredDocFileSuite(
        '../doc/distroseriesqueue-translations.txt',
        setUp=lambda test: setUp(test, future=True), tearDown=tearDown,
        layer=LaunchpadZopelessLayer,
        ),
    }


def test_suite():
    suite = unittest.TestSuite()

    stories_dir = os.path.join(os.path.pardir, 'stories')
    suite.addTest(PageTestSuite(
        stories_dir, setUp=lambda test: setUpGlobs(test, future=True)))
    stories_path = os.path.join(here, stories_dir)
    for story_entry in scandir.scandir(stories_path):
        if not story_entry.is_dir():
            continue
        story_path = os.path.join(stories_dir, story_entry.name)
        suite.addTest(PageTestSuite(
            story_path, setUp=lambda test: setUpGlobs(test, future=True)))

    # Add special needs tests
    for key in sorted(special):
        special_suite = special[key]
        suite.addTest(special_suite)

    testsdir = os.path.abspath(
        os.path.normpath(os.path.join(here, os.path.pardir, 'doc')))

    # Add tests using default setup/teardown
    filenames = [filename
                 for filename in os.listdir(testsdir)
                 if filename.endswith('.txt') and filename not in special]

    # Sort the list to give a predictable order.
    filenames.sort()
    for filename in filenames:
        path = os.path.join('../doc', filename)
        one_test = LayeredDocFileSuite(
            path,
            setUp=lambda test: setUp(test, future=True), tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
            stdout_logging_level=logging.WARNING)
        suite.addTest(one_test)

    return suite
