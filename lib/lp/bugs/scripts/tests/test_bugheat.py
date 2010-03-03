# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from datetime import timedelta

from canonical.testing import LaunchpadZopelessLayer

from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.bugs.scripts.bugheat import BugHeatCalculator, BugHeatConstants
from lp.testing import TestCaseWithFactory

class TestBugHeatCalculator(TestCaseWithFactory):
    """Tests for the BugHeatCalculator class."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestBugHeatCalculator, self).setUp()
        self.bug = self.factory.makeBug()
        self.calculator = BugHeatCalculator(self.bug)

    def test__getHeatFromDuplicates(self):
        # BugHeatCalculator._getHeatFromDuplicates() returns the bug
        # heat generated by duplicates of a bug.
        # By default, the bug has no heat from dupes
        self.assertEqual(0, self.calculator._getHeatFromDuplicates())

        # If adding duplicates, the heat generated by them will be n *
        # BugHeatConstants.DUPLICATE, where n is the number of
        # duplicates.
        for i in range(5):
            dupe = self.factory.makeBug()
            dupe.duplicateof = self.bug

        expected_heat = BugHeatConstants.DUPLICATE * 5
        actual_heat = self.calculator._getHeatFromDuplicates()
        self.assertEqual(
            expected_heat, actual_heat,
            "Heat from duplicates does not match expected heat. "
            "Expected %s, got %s" % (expected_heat, actual_heat))

    def test__getHeatFromAffectedUsers(self):
        # BugHeatCalculator._getHeatFromAffectedUsers() returns the bug
        # heat generated by users affected by the bug and by duplicate bugs.
        # By default, the heat will be BugHeatConstants.AFFECTED_USER, since
        # there will be one affected user (the user who filed the bug).
        self.assertEqual(
            BugHeatConstants.AFFECTED_USER,
            self.calculator._getHeatFromAffectedUsers())

        # As the number of affected users increases, the heat generated
        # will be n * BugHeatConstants.AFFECTED_USER, where n is the number
        # of affected users.
        for i in range(5):
            person = self.factory.makePerson()
            self.bug.markUserAffected(person)

        expected_heat = BugHeatConstants.AFFECTED_USER * 6
        actual_heat = self.calculator._getHeatFromAffectedUsers()
        self.assertEqual(
            expected_heat, actual_heat,
            "Heat from affected users does not match expected heat. "
            "Expected %s, got %s" % (expected_heat, actual_heat))

        # When our bug has duplicates, users affected by these duplicates
        # are included in _getHeatFromAffectedUsers() of the main bug.
        for i in range(3):
            dupe = self.factory.makeBug()
            dupe.duplicateof = self.bug
        expected_heat += BugHeatConstants.AFFECTED_USER * 3

        person = self.factory.makePerson()
        dupe.markUserAffected(person)
        expected_heat += BugHeatConstants.AFFECTED_USER
        actual_heat = self.calculator._getHeatFromAffectedUsers()
        self.assertEqual(
            expected_heat, actual_heat,
            "Heat from users affected by duplicate bugs does not match "
            "expected heat. Expected %s, got %s"
            % (expected_heat, actual_heat))

    def test__getHeatFromSubscribers(self):
        # BugHeatCalculator._getHeatFromSubscribers() returns the bug
        # heat generated by users subscribed tothe bug.
        # By default, the heat will be BugHeatConstants.SUBSCRIBER,
        # since there will be one direct subscriber (the user who filed
        # the bug).
        self.assertEqual(
            BugHeatConstants.SUBSCRIBER,
            self.calculator._getHeatFromSubscribers())

        # As the number of subscribers increases, the heat generated
        # will be n * BugHeatConstants.SUBSCRIBER, where n is the number
        # of subscribers.
        for i in range(5):
            person = self.factory.makePerson()
            self.bug.subscribe(person, person)

        expected_heat = BugHeatConstants.SUBSCRIBER * 6
        actual_heat = self.calculator._getHeatFromSubscribers()
        self.assertEqual(
            expected_heat, actual_heat,
            "Heat from subscribers does not match expected heat. "
            "Expected %s, got %s" % (expected_heat, actual_heat))

        # Subscribers from duplicates are included in the heat returned
        # by _getHeatFromSubscribers()
        dupe = self.factory.makeBug()
        dupe.duplicateof = self.bug
        expected_heat = BugHeatConstants.SUBSCRIBER * 7
        actual_heat = self.calculator._getHeatFromSubscribers()
        self.assertEqual(
            expected_heat, actual_heat,
            "Heat from subscribers (including duplicate-subscribers) "
            "does not match expected heat. Expected %s, got %s" %
            (expected_heat, actual_heat))

        # Seting the bug to private will increase its heat from
        # subscribers by 1 * BugHeatConstants.SUBSCRIBER, as the project
        # owner will now be directly subscribed to it.
        self.bug.setPrivate(True, self.bug.owner)
        expected_heat = BugHeatConstants.SUBSCRIBER * 8
        actual_heat = self.calculator._getHeatFromSubscribers()
        self.assertEqual(
            expected_heat, actual_heat,
            "Heat from subscribers to private bug does not match expected "
            "heat. Expected %s, got %s" % (expected_heat, actual_heat))

    def test__getHeatFromPrivacy(self):
        # BugHeatCalculator._getHeatFromPrivacy() returns the heat
        # generated by the bug's private attribute. If the bug is
        # public, this will be 0.
        self.assertEqual(0, self.calculator._getHeatFromPrivacy())

        # However, if the bug is private, _getHeatFromPrivacy() will
        # return BugHeatConstants.PRIVACY.
        self.bug.setPrivate(True, self.bug.owner)
        self.assertEqual(
            BugHeatConstants.PRIVACY, self.calculator._getHeatFromPrivacy())

    def test__getHeatFromSecurity(self):
        # BugHeatCalculator._getHeatFromSecurity() returns the heat
        # generated by the bug's security_related attribute. If the bug
        # is not security related, _getHeatFromSecurity() will return 0.
        self.assertEqual(0, self.calculator._getHeatFromPrivacy())


        # If, on the other hand, the bug is security_related,
        # _getHeatFromSecurity() will return BugHeatConstants.SECURITY
        self.bug.security_related = True
        self.assertEqual(
            BugHeatConstants.SECURITY, self.calculator._getHeatFromSecurity())

    def test_getBugHeat(self):
        # BugHeatCalculator.getBugHeat() returns the total heat for a
        # given bug as the sum of the results of all _getHeatFrom*()
        # methods.
        # By default this will be (BugHeatConstants.AFFECTED_USER +
        # BugHeatConstants.SUBSCRIBER) since there will be one
        # subscriber and one affected user only.
        expected_heat = (
            BugHeatConstants.AFFECTED_USER + BugHeatConstants.SUBSCRIBER)
        actual_heat = self.calculator.getBugHeat()
        self.assertEqual(
            expected_heat, actual_heat,
            "Expected bug heat did not match actual bug heat. "
            "Expected %s, got %s" % (expected_heat, actual_heat))

        # Adding a duplicate and making the bug private and security
        # related will increase its heat.
        dupe = self.factory.makeBug()
        dupe.duplicateof = self.bug
        self.bug.setPrivate(True, self.bug.owner)
        self.bug.security_related = True

        expected_heat += (
            BugHeatConstants.DUPLICATE +
            BugHeatConstants.PRIVACY +
            BugHeatConstants.SECURITY +
            BugHeatConstants.AFFECTED_USER
            )

        # Adding the duplicate and making the bug private means it gets
        # two new subscribers, the project owner and the duplicate's
        # direct subscriber.
        expected_heat += BugHeatConstants.SUBSCRIBER * 2
        actual_heat = self.calculator.getBugHeat()
        self.assertEqual(
            expected_heat, actual_heat,
            "Expected bug heat did not match actual bug heat. "
            "Expected %s, got %s" % (expected_heat, actual_heat))

    def test_getBugHeat_complete_bugs(self):
        # Bug which are in a resolved status don't have heat at all.
        complete_bug = self.factory.makeBug()
        heat = BugHeatCalculator(complete_bug).getBugHeat()
        self.assertNotEqual(
            0, heat,
            "Expected bug heat did not match actual bug heat. "
            "Expected a positive value, got 0")
        complete_bug.bugtasks[0].transitionToStatus(
            BugTaskStatus.INVALID, complete_bug.owner)
        heat = BugHeatCalculator(complete_bug).getBugHeat()
        self.assertEqual(
            0, heat,
            "Expected bug heat did not match actual bug heat. "
            "Expected %s, got %s" % (0, heat))

    def test_getBugHeat_decay(self):
        # Every month, a bug that wasn't touched has its heat reduced by 10%.
        aging_bug = self.factory.makeBug()
        fresh_heat = BugHeatCalculator(aging_bug).getBugHeat()
        aging_bug.date_last_updated = (
            aging_bug.date_last_updated - timedelta(days=32))
        expected = int(fresh_heat * 0.9)
        heat = BugHeatCalculator(aging_bug).getBugHeat()
        self.assertEqual(
            expected, heat,
            "Expected bug heat did not match actual bug heat. "
            "Expected %s, got %s" % (expected, heat))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

