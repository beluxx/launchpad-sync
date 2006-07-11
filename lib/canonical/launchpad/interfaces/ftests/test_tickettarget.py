# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Module defining a base test class for ITicketTarget implementation."""

__metaclass__ = type

__all__ = [
    'BaseTicketTargetTest',
    ]

import unittest
from datetime import datetime, timedelta
from pytz import UTC

from zope.component import getUtility
from zope.interface.verify import verifyObject

from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.launchpad.interfaces import (
    IDistributionSet, ILaunchBag, IPersonSet, IProductSet, ITicketTarget)


class BaseTicketTargetTest(LaunchpadFunctionalTestCase):
    """Base tests for implementation of ITicketTarget.

    Derived classes need to override the getTarget() method.
    """

    def getTarget(self):
        """Return the ITicketTarget object which should be tested. The
        target returned should not have any tickets associated with it."""
        raise NotImplementedError

    def setUp(self):
        LaunchpadFunctionalTestCase.setUp(self)
        self.login('test@canonical.com')
        self.sample_person = getUtility(ILaunchBag).user

    def test_interface(self):
        """Target should implement ITicketTarget."""
        self.failUnless(verifyObject(ITicketTarget, self.getTarget()))

    def test_newTicket(self):
        target = self.getTarget()
        ticket = target.newTicket(self.sample_person, 'New ticket',
                                  'Ticket description')
        self.assertEquals('New ticket', ticket.title)
        self.assertEquals('Ticket description', ticket.description)
        self.assertEquals([self.sample_person],
                          [s.person for s in ticket.subscriptions])
        self.assertEquals(target, ticket.target)

    def test_getTicket(self):
        target = self.getTarget()
        # Ticket for other target should return None
        self.assertEquals(None, target.getTicket(2))
        # Non-existant ticket should also return None
        self.assertEquals(None, target.getTicket(12345))

        ticket = target.newTicket(self.sample_person, 'New ticket',
                                  'Ticket description')
        self.assertEquals(ticket, target.getTicket(ticket.id))

    def test_tickets(self):
        target = self.getTarget()
        self.assertEquals([], list(target.tickets()))
        tickets = []
        now = datetime.now(UTC)
        for num in range(10):
            # XXX the when parameter is not part of the newTicket interface
            # it is only present in our implementation for testing purpose.
            ticket = target.newTicket(self.sample_person, 'Ticket %d' % num,
                                      'Ticket description %d' % num,
                                      when=now+timedelta(seconds=num))
            tickets.append(ticket)
        # Tickets are returned from last to first.
        tickets.reverse()
        self.assertEquals(tickets, list(target.tickets()))
        self.assertEquals(tickets[:5], list(target.tickets(5)))
        self.assertEquals(tickets, list(target.tickets(15)))

    def test_addSupportContact(self):
        target = self.getTarget()
        self.assertEquals([], target.support_contacts)

        # addSupportContact returns True if the contact was added
        self.failUnless(target.addSupportContact(self.sample_person))
        self.assertEquals([self.sample_person], target.support_contacts)

        # False otherwise
        self.failIf(target.addSupportContact(self.sample_person))
        self.assertEquals([self.sample_person], target.support_contacts)

    def test_removeSupportContact(self):
        target = self.getTarget()
        persons = []
        personset = getUtility(IPersonSet)
        for name in ['name18', 'name19', 'name20']:
            person = personset.getByName(name)
            persons.append(person)
            target.addSupportContact(person)
        self.assertEquals(persons, target.support_contacts)

        # removeSupportContact returns True when it removed the person
        self.failUnless(target.removeSupportContact(persons[-1]))
        self.assertEquals(persons[0:2], target.support_contacts)
        # False otherwise
        self.failIf(target.removeSupportContact(persons[-1]))

    def test_newTicket_with_support_contact(self):
        # Support contacts are subscribed on ticket notification.
        target = self.getTarget()
        target.addSupportContact(self.sample_person)
        name18 = getUtility(IPersonSet).getByName('name18')
        target.addSupportContact(name18)
        ticket = target.newTicket(self.sample_person, title='New ticket',
                                  description='New description')
        self.assertEquals([self.sample_person, name18],
                          [s.person for s in ticket.subscriptions])


class DistributionTicketTargetTest(BaseTicketTargetTest):
    """Tests for implementation of ITicketTarget in Distribution."""

    def getTarget(self):
        """Return the kubuntu distribution as an ITicketTarget."""
        return getUtility(IDistributionSet).getByName('kubuntu')


class ProductTicketTargetTest(BaseTicketTargetTest):
    """Tests for implementation of ITicketTarget in Product."""

    def getTarget(self):
        """Return the thunderbird product as an ITicketTarget."""
        return getUtility(IProductSet).getByName('thunderbird')


class SourcePackageTicketTargetTest(BaseTicketTargetTest):
    """Tests for implementation of ITicketTarget in SourcePackage."""

    def getTarget(self):
        """Return the evolution sourcepackage in current ubuntu
        as an ITicketTarget.
        """
        distro = getUtility(IDistributionSet).getByName('ubuntu')
        return distro.currentrelease.getSourcePackage('evolution')

    def test_newTicket(self):
        target = self.getTarget()
        ticket = target.newTicket(self.sample_person, 'New ticket',
                                  'Ticket description')
        self.assertEquals('New ticket', ticket.title)
        self.assertEquals('Ticket description', ticket.description)
        self.assertEquals([self.sample_person],
                          [s.person for s in ticket.subscriptions])
        # SourcePackage has a special case: the actual target of
        # the created ticket is the distribution
        self.assertEquals(target.distribution, ticket.target)

    def test_newTicket_with_support_contact(self):
        BaseTicketTargetTest.test_newTicket_with_support_contact(self)
        # Check that the distro support contact is also subscribed
        target = self.getTarget()
        name20 = getUtility(IPersonSet).getByName('name20')
        target.distribution.addSupportContact(name20)
        ticket = target.newTicket(self.sample_person, title='New ticket',
                                  description='New description')
        self.failUnless(ticket.isSubscribed(name20))

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DistributionTicketTargetTest))
    suite.addTest(unittest.makeSuite(ProductTicketTargetTest))
    suite.addTest(unittest.makeSuite(SourcePackageTicketTargetTest))
    return suite


if __name__ == '__main__':
    unittest.main()