# Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the BugSummary class and underlying database triggers."""

__metaclass__ = type

from datetime import datetime

from pytz import utc
from zope.security.proxy import removeSecurityProxy

from lp.bugs.interfaces.bugsummary import IBugSummary
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.bugs.model.bug import BugTag
from lp.bugs.model.bugsummary import BugSummary
from lp.bugs.model.bugtask import BugTask
from lp.registry.enums import InformationType
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database.lpstorm import IMasterStore
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import switch_dbuser
from lp.testing.layers import LaunchpadZopelessLayer


class TestBugSummary(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestBugSummary, self).setUp()

        # Some things we are testing are impossible as mere mortals,
        # but might happen from the SQL command line.
        switch_dbuser('testadmin')

        self.store = IMasterStore(BugSummary)

    def getPublicCount(self, **kw_find_expr):
        return self.getCount(None, **kw_find_expr)

    def getCount(self, person, **kw_find_expr):
        self._maybe_rollup()

        public_summaries = self.store.find(
            BugSummary,
            BugSummary.viewed_by == None,
            **kw_find_expr)
        private_summaries = self.store.find(
            BugSummary,
            BugSummary.viewed_by_id == TeamParticipation.teamID,
            TeamParticipation.person == person,
            **kw_find_expr)
        all_summaries = public_summaries.union(private_summaries, all=True)

        # Note that if there a 0 records found, sum() returns None, but
        # we prefer to return 0 here.
        return all_summaries.sum(BugSummary.count) or 0

    def assertCount(self, count, user=None, **kw_find_expr):
        self.assertEqual(count, self.getCount(user, **kw_find_expr))

    def _maybe_rollup(self):
        """Rollup the journal if the class is testing the rollup case."""
        # The base class does not rollup the journal, see
        # TestBugSummaryRolledUp which does.
        pass

    def test_providesInterface(self):
        bug_summary = self.store.find(BugSummary)[0]
        self.assertTrue(IBugSummary.providedBy(bug_summary))

    def test_addTag(self):
        tag = u'pustular'

        # Ensure nothing using our tag yet.
        self.assertCount(0, tag=tag)

        product = self.factory.makeProduct()

        for count in range(3):
            bug = self.factory.makeBug(product=product)
            bug_tag = BugTag()
            bug_tag.bug = bug
            bug_tag.tag = tag
            self.store.add(bug_tag)

        # Number of tagged tasks for a particular product
        self.assertCount(3, product=product, tag=tag)

        # There should be no other BugSummary rows.
        self.assertCount(3, tag=tag)

    def test_changeTag(self):
        old_tag = u'pustular'
        new_tag = u'flatulent'

        # Ensure nothing using our tags yet.
        self.assertCount(0, tag=old_tag)
        self.assertCount(0, tag=new_tag)

        product = self.factory.makeProduct()

        for count in range(3):
            bug = self.factory.makeBug(product=product)
            bug_tag = BugTag()
            bug_tag.bug = bug
            bug_tag.tag = old_tag
            self.store.add(bug_tag)

        # Number of tagged tasks for a particular product
        self.assertCount(3, product=product, tag=old_tag)

        for count in reversed(range(3)):
            bug_tag = self.store.find(BugTag, tag=old_tag).any()
            bug_tag.tag = new_tag

            self.assertEqual(
                self.getPublicCount(product=product, tag=old_tag), count)
            self.assertEqual(
                self.getPublicCount(product=product, tag=new_tag), 3 - count)

        # There should be no other BugSummary rows.
        self.assertCount(0, tag=old_tag)
        self.assertCount(3, tag=new_tag)

    def test_removeTag(self):
        tag = u'pustular'

        # Ensure nothing using our tags yet.
        self.assertCount(0, tag=tag)

        product = self.factory.makeProduct()

        for count in range(3):
            bug = self.factory.makeBug(product=product)
            bug_tag = BugTag()
            bug_tag.bug = bug
            bug_tag.tag = tag
            self.store.add(bug_tag)

        # Number of tagged tasks for a particular product
        self.assertCount(3, product=product, tag=tag)

        for count in reversed(range(3)):
            bug_tag = self.store.find(BugTag, tag=tag).any()
            self.store.remove(bug_tag)
            self.assertEqual(
                self.getPublicCount(product=product, tag=tag), count)

        # There should be no other BugSummary rows.
        self.assertCount(0, tag=tag)

    def test_changeStatus(self):
        org_status = BugTaskStatus.NEW
        new_status = BugTaskStatus.INVALID

        product = self.factory.makeProduct()

        for count in range(3):
            bug = self.factory.makeBug(product=product)
            bug_task = self.store.find(BugTask, bug=bug).one()
            bug_task._status = org_status

            self.assertEqual(
                self.getPublicCount(product=product, status=org_status),
                count + 1)

        for count in reversed(range(3)):
            bug_task = self.store.find(
                BugTask, product=product, _status=org_status).any()
            bug_task._status = new_status
            self.assertEqual(
                self.getPublicCount(product=product, status=org_status),
                count)
            self.assertEqual(
                self.getPublicCount(product=product, status=new_status),
                3 - count)

    def test_changeImportance(self):
        org_importance = BugTaskImportance.UNDECIDED
        new_importance = BugTaskImportance.CRITICAL

        product = self.factory.makeProduct()

        for count in range(3):
            bug = self.factory.makeBug(product=product)
            bug_task = self.store.find(BugTask, bug=bug).one()
            bug_task.importance = org_importance

            self.assertEqual(
                self.getPublicCount(
                    product=product, importance=org_importance),
                count + 1)

        for count in reversed(range(3)):
            bug_task = self.store.find(
                BugTask, product=product, importance=org_importance).any()
            bug_task.importance = new_importance
            self.assertEqual(
                self.getPublicCount(
                    product=product, importance=org_importance),
                count)
            self.assertEqual(
                self.getPublicCount(
                    product=product, importance=new_importance),
                3 - count)

    def test_makePrivate(self):
        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product, owner=person_b)

        bug.subscribe(person=person_a, subscribed_by=person_a)

        # Make the bug private. We have to use the Python API to ensure
        # BugSubscription records get created for implicit
        # subscriptions.
        bug.setPrivate(True, bug.owner)

        # Confirm counts.
        self.assertCount(0, product=product)
        self.assertEqual(self.getCount(person_a, product=product), 1)
        self.assertEqual(self.getCount(person_b, product=product), 1)
        # Confirm implicit subscriptions work too.
        self.assertEqual(self.getCount(bug.owner, product=product), 1)

    def test_makePublic(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(
            product=product, information_type=InformationType.USERDATA)

        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        bug.subscribe(person=person_a, subscribed_by=person_a)

        # Make the bug public. We have to use the Python API to ensure
        # BugSubscription records get created for implicit
        # subscriptions.
        bug.setPrivate(False, bug.owner)

        self.assertCount(1, product=product)
        self.assertEqual(self.getCount(person_a, product=product), 1)
        self.assertEqual(self.getCount(person_b, product=product), 1)

    def test_subscribePrivate(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(
            product=product, information_type=InformationType.USERDATA)

        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        bug.subscribe(person=person_a, subscribed_by=person_a)

        self.assertCount(0, product=product)
        self.assertEqual(self.getCount(person_a, product=product), 1)
        self.assertEqual(self.getCount(person_b, product=product), 0)

    def test_unsubscribePrivate(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(
            product=product, information_type=InformationType.USERDATA)

        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        bug.subscribe(person=person_a, subscribed_by=person_a)
        bug.subscribe(person=person_b, subscribed_by=person_b)
        bug.unsubscribe(person=person_b, unsubscribed_by=person_b)

        self.assertCount(0, product=product)
        self.assertEqual(self.getCount(person_a, product=product), 1)
        self.assertEqual(self.getCount(person_b, product=product), 0)

    def test_subscribePublic(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)

        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        bug.subscribe(person=person_a, subscribed_by=person_a)

        self.assertCount(1, product=product)
        self.assertEqual(self.getCount(person_a, product=product), 1)
        self.assertEqual(self.getCount(person_b, product=product), 1)

    def test_unsubscribePublic(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)

        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        bug.subscribe(person=person_a, subscribed_by=person_a)
        bug.subscribe(person=person_b, subscribed_by=person_b)
        bug.unsubscribe(person=person_b, unsubscribed_by=person_b)

        self.assertCount(1, product=product)
        self.assertEqual(self.getCount(person_a, product=product), 1)
        self.assertEqual(self.getCount(person_b, product=product), 1)

    def test_addProduct(self):
        distribution = self.factory.makeDistribution()
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(distribution=distribution)

        self.assertCount(1, distribution=distribution)
        self.assertCount(0, product=product)

        self.factory.makeBugTask(bug=bug, target=product)

        self.assertCount(1, distribution=distribution)
        self.assertCount(1, product=product)

    def test_changeProduct(self):
        product_a = self.factory.makeProduct()
        product_b = self.factory.makeProduct()
        bug_task = self.factory.makeBugTask(target=product_a)

        self.assertCount(1, product=product_a)
        self.assertCount(0, product=product_b)

        removeSecurityProxy(bug_task).product = product_b

        self.assertCount(0, product=product_a)
        self.assertCount(1, product=product_b)

    def test_removeProduct(self):
        distribution = self.factory.makeDistribution()
        product = self.factory.makeProduct()

        product_bug_task = self.factory.makeBugTask(target=product)
        self.factory.makeBugTask(
            bug=product_bug_task.bug, target=distribution)

        self.assertCount(1, distribution=distribution)
        self.assertCount(1, product=product)

        self.store.remove(product_bug_task)

        self.assertCount(1, distribution=distribution)
        self.assertCount(0, product=product)

    def test_addProductSeries(self):
        bug = self.factory.makeBug()
        productseries = self.factory.makeProductSeries()
        product = productseries.product

        bug_task = self.factory.makeBugTask(bug=bug, target=productseries)

        self.assertTrue(bug_task.product is None)

        self.assertCount(1, product=product)
        self.assertCount(1, productseries=productseries)

    def test_changeProductSeries(self):
        product = self.factory.makeProduct()
        productseries_a = self.factory.makeProductSeries(product=product)
        productseries_b = self.factory.makeProductSeries(product=product)

        # You can't have a BugTask targetted to a productseries without
        # already having a BugTask targetted to the product. Create
        # this task explicitly.
        product_task = self.factory.makeBugTask(target=product)

        series_task = self.factory.makeBugTask(
            bug=product_task.bug, target=productseries_a)

        self.assertCount(1, product=product)
        self.assertEqual(
            self.getPublicCount(productseries=productseries_a), 1)

        removeSecurityProxy(series_task).productseries = productseries_b

        self.assertCount(1, product=product)
        self.assertEqual(
            self.getPublicCount(productseries=productseries_a), 0)
        self.assertEqual(
            self.getPublicCount(productseries=productseries_b), 1)

    def test_removeProductSeries(self):
        series = self.factory.makeProductSeries()
        product = series.product
        bug_task = self.factory.makeBugTask(target=series)

        self.assertCount(1, product=product)
        self.assertCount(1, productseries=series)

        self.store.remove(bug_task)

        self.assertCount(1, product=product)
        self.assertCount(0, productseries=series)

    def test_addDistribution(self):
        distribution = self.factory.makeDistribution()
        self.factory.makeBugTask(target=distribution)

        self.assertCount(1, distribution=distribution)

    def test_changeDistribution(self):
        distribution_a = self.factory.makeDistribution()
        distribution_b = self.factory.makeDistribution()
        bug_task = self.factory.makeBugTask(target=distribution_a)

        self.assertCount(1, distribution=distribution_a)

        removeSecurityProxy(bug_task).distribution = distribution_b

        self.assertCount(0, distribution=distribution_a)
        self.assertCount(1, distribution=distribution_b)

    def test_removeDistribution(self):
        distribution_a = self.factory.makeDistribution()
        distribution_b = self.factory.makeDistribution()
        bug_task_a = self.factory.makeBugTask(target=distribution_a)
        bug = bug_task_a.bug
        bug_task_b = self.factory.makeBugTask(bug=bug, target=distribution_b)

        self.assertCount(1, distribution=distribution_a)
        self.assertCount(1, distribution=distribution_b)

        self.store.remove(bug_task_b)

        self.assertCount(1, distribution=distribution_a)
        self.assertCount(0, distribution=distribution_b)

    def test_addDistroSeries(self):
        series = self.factory.makeDistroSeries()
        distribution = series.distribution

        # This first creates a BugTask on the distribution. We can't
        # have a distroseries BugTask without a distribution BugTask.
        self.factory.makeBugTask(target=series)

        self.assertCount(1, distribution=distribution)
        self.assertCount(1, distroseries=series)

    def test_changeDistroSeries(self):
        distribution = self.factory.makeDistribution()
        series_a = self.factory.makeDistroSeries(distribution=distribution)
        series_b = self.factory.makeDistroSeries(distribution=distribution)

        bug_task = self.factory.makeBugTask(target=series_a)

        self.assertCount(1, distribution=distribution)
        self.assertCount(1, distroseries=series_a)
        self.assertCount(0, distroseries=series_b)

        removeSecurityProxy(bug_task).distroseries = series_b

        self.assertCount(1, distribution=distribution)
        self.assertCount(0, distroseries=series_a)
        self.assertCount(1, distroseries=series_b)

    def test_removeDistroSeries(self):
        series = self.factory.makeDistroSeries()
        distribution = series.distribution
        bug_task = self.factory.makeBugTask(target=series)

        self.assertCount(1, distribution=distribution)
        self.assertCount(1, distroseries=series)

        self.store.remove(bug_task)

        self.assertCount(1, distribution=distribution)
        self.assertCount(0, distroseries=series)

    def test_addDistributionSourcePackage(self):
        distribution = self.factory.makeDistribution()
        sourcepackage = self.factory.makeDistributionSourcePackage(
            distribution=distribution)

        bug = self.factory.makeBug()
        self.factory.makeBugTask(bug=bug, target=sourcepackage)

        self.assertCount(1, distribution=distribution, sourcepackagename=None)
        self.assertCount(
            1, distribution=distribution,
            sourcepackagename=sourcepackage.sourcepackagename)

    def test_changeDistributionSourcePackage(self):
        distribution = self.factory.makeDistribution()
        sourcepackage_a = self.factory.makeDistributionSourcePackage(
            distribution=distribution)
        sourcepackage_b = self.factory.makeDistributionSourcePackage(
            distribution=distribution)

        bug_task = self.factory.makeBugTask(target=sourcepackage_a)

        self.assertCount(1, distribution=distribution, sourcepackagename=None)
        self.assertCount(
            1, distribution=distribution,
            sourcepackagename=sourcepackage_a.sourcepackagename)
        self.assertCount(
            0, distribution=distribution,
            sourcepackagename=sourcepackage_b.sourcepackagename)

        removeSecurityProxy(bug_task).sourcepackagename = (
            sourcepackage_b.sourcepackagename)

        self.assertCount(1, distribution=distribution, sourcepackagename=None)
        self.assertCount(
            0, distribution=distribution,
            sourcepackagename=sourcepackage_a.sourcepackagename)
        self.assertCount(
            1, distribution=distribution,
            sourcepackagename=sourcepackage_b.sourcepackagename)

    def test_removeDistributionSourcePackage(self):
        distribution = self.factory.makeDistribution()
        sourcepackage = self.factory.makeDistributionSourcePackage(
            distribution=distribution)

        bug_task = self.factory.makeBugTask(target=sourcepackage)

        self.assertCount(1, distribution=distribution, sourcepackagename=None)
        self.assertCount(
            1, distribution=distribution,
            sourcepackagename=sourcepackage.sourcepackagename)

        removeSecurityProxy(bug_task).sourcepackagename = None

        self.assertCount(1, distribution=distribution, sourcepackagename=None)
        self.assertCount(
            0, distribution=distribution,
            sourcepackagename=sourcepackage.sourcepackagename)

    def test_addDistroSeriesSourcePackage(self):
        distribution = self.factory.makeDistribution()
        series = self.factory.makeDistroSeries(distribution=distribution)
        package = self.factory.makeSourcePackage(distroseries=series)
        sourcepackagename = package.sourcepackagename
        self.factory.makeBugTask(target=package)

        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, sourcepackagename=None),
            1)
        self.assertEqual(
            self.getPublicCount(
                distribution=distribution,
                sourcepackagename=sourcepackagename),
            1)
        self.assertEqual(
            self.getPublicCount(distroseries=series, sourcepackagename=None),
            1)
        self.assertEqual(
            self.getPublicCount(
                distroseries=series, sourcepackagename=sourcepackagename),
            1)

    def test_changeDistroSeriesSourcePackage(self):
        distribution = self.factory.makeDistribution()
        series = self.factory.makeDistroSeries(distribution=distribution)
        package_a = self.factory.makeSourcePackage(
            distroseries=series, publish=True)
        package_b = self.factory.makeSourcePackage(
            distroseries=series, publish=True)
        spn_a = package_a.sourcepackagename
        spn_b = package_b.sourcepackagename
        bug_task = self.factory.makeBugTask(target=package_a)

        self.assertCount(1, distribution=distribution, sourcepackagename=None)
        self.assertCount(1, distribution=distribution, sourcepackagename=spn_a)
        self.assertCount(0, distribution=distribution, sourcepackagename=spn_b)
        self.assertCount(1, distroseries=series, sourcepackagename=None)
        self.assertCount(1, distroseries=series, sourcepackagename=spn_a)
        self.assertCount(0, distroseries=series, sourcepackagename=spn_b)

        bug_task.transitionToTarget(series.getSourcePackage(spn_b))

        self.assertCount(1, distribution=distribution, sourcepackagename=None)
        self.assertCount(0, distribution=distribution, sourcepackagename=spn_a)
        self.assertCount(1, distribution=distribution, sourcepackagename=spn_b)
        self.assertCount(1, distroseries=series, sourcepackagename=None)
        self.assertCount(0, distroseries=series, sourcepackagename=spn_a)
        self.assertCount(1, distroseries=series, sourcepackagename=spn_b)

    def test_removeDistroSeriesSourcePackage(self):
        distribution = self.factory.makeDistribution()
        series = self.factory.makeDistroSeries(distribution=distribution)
        package = self.factory.makeSourcePackage(distroseries=series)
        sourcepackagename = package.sourcepackagename
        bug_task = self.factory.makeBugTask(target=package)

        self.assertEqual(
            self.getPublicCount(
                distribution=distribution,
                sourcepackagename=None),
            1)
        self.assertEqual(
            self.getPublicCount(
                distribution=distribution,
                sourcepackagename=sourcepackagename),
            1)
        self.assertEqual(
            self.getPublicCount(
                distroseries=series,
                sourcepackagename=None),
            1)
        self.assertEqual(
            self.getPublicCount(
                distroseries=series,
                sourcepackagename=sourcepackagename),
            1)

        bug_task.transitionToTarget(series)

        self.assertEqual(
            self.getPublicCount(
                distribution=distribution,
                sourcepackagename=None),
            1)
        self.assertEqual(
            self.getPublicCount(
                distribution=distribution,
                sourcepackagename=sourcepackagename),
            0)
        self.assertEqual(
            self.getPublicCount(
                distroseries=series,
                sourcepackagename=None),
            1)
        self.assertEqual(
            self.getPublicCount(
                distroseries=series,
                sourcepackagename=sourcepackagename),
            0)

    def test_addMilestone(self):
        distribution = self.factory.makeDistribution()
        milestone = self.factory.makeMilestone(distribution=distribution)
        bug_task = self.factory.makeBugTask(target=distribution)

        self.assertEqual(
            self.getPublicCount(distribution=distribution, milestone=None),
            1)

        bug_task.milestone = milestone

        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, milestone=None),
            0)
        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, milestone=milestone),
            1)

    def test_changeMilestone(self):
        distribution = self.factory.makeDistribution()
        milestone_a = self.factory.makeMilestone(distribution=distribution)
        milestone_b = self.factory.makeMilestone(distribution=distribution)
        bug_task = self.factory.makeBugTask(target=distribution)
        bug_task.milestone = milestone_a

        self.assertEqual(
            self.getPublicCount(
                distribution=distribution,
                milestone=None),
            0)
        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, milestone=milestone_a),
            1)
        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, milestone=milestone_b),
            0)

        bug_task.milestone = milestone_b

        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, milestone=None),
            0)
        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, milestone=milestone_a),
            0)
        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, milestone=milestone_b),
            1)

    def test_removeMilestone(self):
        distribution = self.factory.makeDistribution()
        milestone = self.factory.makeMilestone(distribution=distribution)
        bug_task = self.factory.makeBugTask(target=distribution)
        bug_task.milestone = milestone

        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, milestone=None),
            0)
        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, milestone=milestone),
            1)

        bug_task.milestone = None

        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, milestone=None),
            1)
        self.assertEqual(
            self.getPublicCount(
                distribution=distribution, milestone=milestone),
            0)

    def test_addPatch(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)

        self.assertEqual(
            self.getPublicCount(product=product, has_patch=True), 0)

        removeSecurityProxy(bug).latest_patch_uploaded = datetime.now(tz=utc)

        self.assertEqual(
            self.getPublicCount(product=product, has_patch=True), 1)

    def test_removePatch(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        removeSecurityProxy(bug).latest_patch_uploaded = datetime.now(tz=utc)

        self.assertEqual(
            self.getPublicCount(product=product, has_patch=True), 1)
        self.assertEqual(
            self.getPublicCount(product=product, has_patch=False), 0)

        removeSecurityProxy(bug).latest_patch_uploaded = None

        self.assertEqual(
            self.getPublicCount(product=product, has_patch=True), 0)
        self.assertEqual(
            self.getPublicCount(product=product, has_patch=False), 1)


class TestBugSummaryRolledUp(TestBugSummary):

    def _maybe_rollup(self):
        # Rollup the BugSummaryJournal into BugSummary
        # so all the records are in one place - this checks the journal
        # flushing logic is correct.
        self.store.execute("SELECT bugsummary_rollup_journal()")
