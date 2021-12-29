# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the milestone vocabularies."""

from zope.component import getUtility

from lp.app.enums import InformationType
from lp.blueprints.interfaces.specification import ISpecificationSet
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.projectgroup import IProjectGroupSet
from lp.registry.vocabularies import (
    MilestoneVocabulary,
    MilestoneWithDateExpectedVocabulary,
    )
from lp.testing import (
    admin_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestMilestoneVocabulary(TestCaseWithFactory):
    """Test that the MilestoneVocabulary behaves as expected."""

    layer = DatabaseFunctionalLayer

    def test_project_group_does_not_show_nonpublic_products(self):
        # Milestones for a projectgroup should not include those on an
        # associated private product.
        owner = self.factory.makePerson()
        group = self.factory.makeProject(owner=owner)
        public = self.factory.makeProduct(projectgroup=group, owner=owner)
        private = self.factory.makeProduct(projectgroup=group, owner=owner,
            information_type=InformationType.PROPRIETARY)
        with person_logged_in(owner):
            m1 = self.factory.makeMilestone(name='public', product=public)
            m2 = self.factory.makeMilestone(name='private', product=private)
        vocabulary = MilestoneVocabulary(group)
        expected = [m1.title]
        listing = [term.title for term in vocabulary]
        self.assertEqual(expected, listing)

        with person_logged_in(owner):
            vocabulary = MilestoneVocabulary(group)
            expected = [m1.title, m2.title]
            listing = [term.title for term in vocabulary]
            self.assertEqual(expected, listing)

    def testProductMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a product."""
        firefox = getUtility(IProductSet).getByName('firefox')
        vocabulary = MilestoneVocabulary(firefox)
        self.assertEqual(
            [term.title for term in vocabulary], ['Mozilla Firefox 1.0'])

    def testProductSeriesMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a product series."""
        firefox = getUtility(IProductSet).getByName('firefox')
        trunk = firefox.getSeries('trunk')
        vocabulary = MilestoneVocabulary(trunk)
        self.assertEqual(
            [term.title for term in vocabulary], ['Mozilla Firefox 1.0'])

    def testProjectGroupMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a project group."""
        mozilla = getUtility(IProjectGroupSet).getByName('mozilla')
        vocabulary = MilestoneVocabulary(mozilla)
        self.assertEqual(
            [term.title for term in vocabulary], ['Mozilla Firefox 1.0'])

    def testDistributionMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a distribution."""
        debian = getUtility(IDistributionSet).getByName('debian')
        vocabulary = MilestoneVocabulary(debian)
        self.assertEqual(
            [term.title for term in vocabulary],
            ['Debian 3.1', 'Debian 3.1-rc1'])

    def testDistroseriesMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a distroseries."""
        debian = getUtility(IDistributionSet).getByName('debian')
        woody = debian.getSeries('woody')
        vocabulary = MilestoneVocabulary(woody)
        self.assertEqual(
            [term.title for term in vocabulary],
            ['Debian 3.1', 'Debian 3.1-rc1'])

    def testSpecificationMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a specification."""
        spec = getUtility(ISpecificationSet).get(1)
        firefox = getUtility(IProductSet).getByName('firefox')
        self.assertEqual(spec.target, firefox)
        vocabulary = MilestoneVocabulary(spec)
        self.assertEqual(
            [term.title for term in vocabulary], ['Mozilla Firefox 1.0'])

    def testPersonMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a person."""
        sample_person = getUtility(IPersonSet).getByEmail(
            'test@canonical.com')
        vocabulary = MilestoneVocabulary(sample_person)
        # A person is not a milestone target; the vocabulary consists
        # in such a case of all known visible milestones.
        self.assertEqual(
            [term.title for term in vocabulary],
            ['Debian 3.1', 'Debian 3.1-rc1', 'Mozilla Firefox 1.0'])


class TestMilestoneWithDateExpectedVocabulary(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_milestone_with_date_expected(self):
        firefox = getUtility(IProductSet).getByName('firefox')
        vocabulary = MilestoneWithDateExpectedVocabulary(firefox)
        self.assertEqual(
            [term.title for term in vocabulary],
            ['Mozilla Firefox 1.0 (2056-10-16)'])

    def test_milestone_without_date_expected(self):
        evolution = getUtility(IProductSet).getByName('evolution')
        series = evolution.getSeries('trunk')
        with admin_logged_in():
            series.newMilestone(name='3.0', dateexpected=None)
        vocabulary = MilestoneWithDateExpectedVocabulary(evolution)
        self.assertEqual(
            [term.title for term in vocabulary], ['Evolution 3.0'])
