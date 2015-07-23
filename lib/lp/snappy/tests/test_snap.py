# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap packages."""

__metaclass__ = type

from datetime import datetime

from lazr.lifecycle.event import ObjectModifiedEvent
import pytz
from storm.locals import Store
import transaction
from zope.component import getUtility
from zope.event import notify
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import (
    BuildQueueStatus,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database.constants import UTC_NOW
from lp.services.features.testing import FeatureFixture
from lp.snappy.interfaces.snap import (
    CannotDeleteSnap,
    ISnap,
    ISnapSet,
    SNAP_FEATURE_FLAG,
    SnapBuildAlreadyPending,
    SnapFeatureDisabled,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )


class TestSnapFeatureFlag(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_feature_flag_disabled(self):
        # Without a feature flag, we will not create new Snaps.
        person = self.factory.makePerson()
        self.assertRaises(
            SnapFeatureDisabled, getUtility(ISnapSet).new,
            person, person, None, None, True, None)


class TestSnap(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnap, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))

    def test_implements_interfaces(self):
        # Snap implements ISnap.
        snap = self.factory.makeSnap()
        with person_logged_in(snap.owner):
            self.assertProvides(snap, ISnap)

    def test_initial_date_last_modified(self):
        # The initial value of date_last_modified is date_created.
        snap = self.factory.makeSnap(
            date_created=datetime(2014, 04, 25, 10, 38, 0, tzinfo=pytz.UTC))
        self.assertEqual(snap.date_created, snap.date_last_modified)

    def test_modifiedevent_sets_date_last_modified(self):
        # When a Snap receives an object modified event, the last modified
        # date is set to UTC_NOW.
        snap = self.factory.makeSnap(
            date_created=datetime(2014, 04, 25, 10, 38, 0, tzinfo=pytz.UTC))
        notify(ObjectModifiedEvent(
            removeSecurityProxy(snap), snap, [ISnap["name"]]))
        self.assertSqlAttributeEqualsDate(snap, "date_last_modified", UTC_NOW)


class TestSnapSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapSet, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))

    def test_class_implements_interfaces(self):
        # The SnapSet class implements ISnapSet.
        self.assertProvides(getUtility(ISnapSet), ISnapSet)

    def makeSnapComponents(self, branch=None, git_ref=None):
        """Return a dict of values that can be used to make a Snap.

        Suggested use: provide as kwargs to ISnapSet.new.

        :param branch: An `IBranch`, or None.
        :param git_ref: An `IGitRef`, or None.
        """
        registrant = self.factory.makePerson()
        components = dict(
            registrant=registrant,
            owner=self.factory.makeTeam(owner=registrant),
            distro_series=self.factory.makeDistroSeries(),
            name=self.factory.getUniqueString(u"snap-name"))
        if branch is None and git_ref is None:
            branch = self.factory.makeAnyBranch()
        if branch is not None:
            components["branch"] = branch
        else:
            components["git_repository"] = git_ref.repository
            components["git_path"] = git_ref.path
        return components

    def test_creation_bzr(self):
        # The metadata entries supplied when a Snap is created for a Bazaar
        # branch are present on the new object.
        branch = self.factory.makeAnyBranch()
        components = self.makeSnapComponents(branch=branch)
        snap = getUtility(ISnapSet).new(**components)
        transaction.commit()
        self.assertEqual(components["registrant"], snap.registrant)
        self.assertEqual(components["owner"], snap.owner)
        self.assertEqual(components["distro_series"], snap.distro_series)
        self.assertEqual(components["name"], snap.name)
        self.assertEqual(branch, snap.branch)
        self.assertIsNone(snap.git_repository)
        self.assertIsNone(snap.git_path)
        self.assertTrue(snap.require_virtualized)

    def test_creation_git(self):
        # The metadata entries supplied when a Snap is created for a Git
        # branch are present on the new object.
        [ref] = self.factory.makeGitRefs()
        components = self.makeSnapComponents(git_ref=ref)
        snap = getUtility(ISnapSet).new(**components)
        transaction.commit()
        self.assertEqual(components["registrant"], snap.registrant)
        self.assertEqual(components["owner"], snap.owner)
        self.assertEqual(components["distro_series"], snap.distro_series)
        self.assertEqual(components["name"], snap.name)
        self.assertIsNone(snap.branch)
        self.assertEqual(ref.repository, snap.git_repository)
        self.assertEqual(ref.path, snap.git_path)
        self.assertTrue(snap.require_virtualized)

    def test_exists(self):
        # ISnapSet.exists checks for matching Snaps.
        snap = self.factory.makeSnap()
        self.assertTrue(getUtility(ISnapSet).exists(snap.owner, snap.name))
        self.assertFalse(
            getUtility(ISnapSet).exists(self.factory.makePerson(), snap.name))
        self.assertFalse(getUtility(ISnapSet).exists(snap.owner, u"different"))

    def test_getByPerson(self):
        # ISnapSet.getByPerson returns all Snaps with the given owner.
        owners = [self.factory.makePerson() for i in range(2)]
        snaps = []
        for owner in owners:
            for i in range(2):
                snaps.append(self.factory.makeSnap(
                    registrant=owner, owner=owner))
        self.assertContentEqual(
            snaps[:2], getUtility(ISnapSet).getByPerson(owners[0]))
        self.assertContentEqual(
            snaps[2:], getUtility(ISnapSet).getByPerson(owners[1]))
