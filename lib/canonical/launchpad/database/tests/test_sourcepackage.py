# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Unit tests for ISourcePackage implementations."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.interfaces.publishing import PackagePublishingPocket
from canonical.launchpad.interfaces.seriessourcepackagebranch import (
    ISeriesSourcePackageBranchSet)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.testing.layers import DatabaseFunctionalLayer


class TestSourcePackage(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_path(self):
        sourcepackage = self.factory.makeSourcePackage()
        self.assertEqual(
            '%s/%s/%s' % (
                sourcepackage.distribution.name,
                sourcepackage.distroseries.name,
                sourcepackage.sourcepackagename.name),
            sourcepackage.path)

    def test_getBranch_no_branch(self):
        # If there's no official branch for that pocket of a source package,
        # getBranch returns None.
        sourcepackage = self.factory.makeSourcePackage()
        branch = sourcepackage.getBranch(PackagePublishingPocket.RELEASE)
        self.assertIs(None, branch)

    def test_getBranch_exists(self):
        # If there is a SeriesSourcePackageBranch entry for that source
        # package and pocket, then return the branch.
        sourcepackage = self.factory.makeSourcePackage()
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        getUtility(ISeriesSourcePackageBranchSet).new(
            sourcepackage.distroseries, PackagePublishingPocket.RELEASE,
            sourcepackage.sourcepackagename, branch, registrant)
        official_branch = sourcepackage.getBranch(
            PackagePublishingPocket.RELEASE)
        self.assertEqual(branch, official_branch)

    def test_getBranchLink(self):
        # getBranchLink returns the `ISeriesSourcePackageBranch` object
        # associated with the branch link.
        sourcepackage = self.factory.makeSourcePackage()
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        pocket = PackagePublishingPocket.RELEASE
        sspb = getUtility(ISeriesSourcePackageBranchSet).new(
            sourcepackage.distroseries, pocket,
            sourcepackage.sourcepackagename, branch, registrant)
        self.assertEqual(sspb, sourcepackage.getBranchLink(pocket))

    def test_setBranch(self):
        # We can set the official branch for a pocket of a source package.
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        registrant = self.factory.makePerson()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        sourcepackage.setBranch(pocket, branch, registrant)
        self.assertEqual(branch, sourcepackage.getBranch(pocket))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
