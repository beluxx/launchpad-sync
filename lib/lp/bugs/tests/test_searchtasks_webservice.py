# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad Bugs."""

__metaclass__ = type

from unittest import TestLoader

from canonical.launchpad.ftests import login
from lp.testing import TestCaseWithFactory
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing import DatabaseFunctionalLayer


class TestOmitTargetedParameter(TestCaseWithFactory):
    """Test all values for the omit_targeted search parameter."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login('foo.bar@canonical.com')
        self.distro = self.factory.makeDistribution(name='mebuntu')
        self.release = self.factory.makeDistroRelease(name='inkanyamba',
            distribution=self.distro)
        self.bug = self.factory.makeBugTask(target=self.release)

        self.webservice = LaunchpadWebServiceCaller('launchpad-library',
            'salgado-change-anything')

    def test_omit_targeted_default(self):
        response = self.webservice.named_get(
            self.webservice.getAbsoluteUrl('/mebuntu/inkanyamba'),
            'searchTasks').jsonBody()
        self.assertEqual(response['total_size'], 1)

    def test_omit_targeted_true(self):
        response = self.webservice.named_get(
            self.webservice.getAbsoluteUrl('/mebuntu/inkanyamba'),
            'searchTasks', omit_targeted=True).jsonBody()
        self.assertEqual(response['total_size'], 0)

    def test_omit_targeted_false(self):
        response = self.webservice.named_get(
            self.webservice.getAbsoluteUrl('/mebuntu/inkanyamba'),
            'searchTasks', omit_targeted=False).jsonBody()
        self.assertEqual(response['total_size'], 1)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
