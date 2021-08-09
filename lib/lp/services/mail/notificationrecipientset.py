# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The implementation of the Notification Rec."""

__metaclass__ = type
__all__ = [
    'NotificationRecipientSet',
    'StubPerson',
]


from operator import attrgetter

import six
from zope.interface import implementer
from zope.security.proxy import (
    isinstance as zope_isinstance,
    removeSecurityProxy,
    )

from lp.registry.interfaces.person import IPerson
from lp.services.mail.interfaces import (
    INotificationRecipientSet,
    UnknownRecipientError,
    )


class StubPerson:
    """A stub recipient person.

    This can be used when sending to special email addresses that do not
    correspond to a real Person.
    """

    name = None
    displayname = None
    is_team = False
    expanded_notification_footers = False

    def __init__(self, email):
        self.preferredemail = type(
            "StubEmailAddress", (object,), {"email": email})


@implementer(INotificationRecipientSet)
class NotificationRecipientSet:
    """Set of recipients along the rationale for being in the set."""

    def __init__(self):
        """Create a new empty set."""
        # We maintain a mapping of person to rationale, as well as a
        # a mapping of all the emails to the person that hold the rationale
        # for that email. That way, adding a person and a team containing
        # that person will preserve the rationale associated when the email
        # was first added.
        self._personToRationale = {}
        self._emailToPerson = {}
        self._receiving_people = set()

    def getEmails(self):
        """See `INotificationRecipientSet`."""
        return sorted(self._emailToPerson.keys())

    def getRecipients(self):
        """See `INotificationRecipientSet`."""
        return sorted(
            self._personToRationale.keys(), key=attrgetter('displayname'))

    def getRecipientPersons(self):
        """See `INotificationRecipientSet`."""
        return self._receiving_people

    def __iter__(self):
        """See `INotificationRecipientSet`."""
        return iter(self.getRecipients())

    def __contains__(self, person_or_email):
        """See `INotificationRecipientSet`."""
        if zope_isinstance(person_or_email, six.string_types):
            return person_or_email in self._emailToPerson
        elif IPerson.providedBy(person_or_email):
            return person_or_email in self._personToRationale
        else:
            return False

    def __bool__(self):
        """See `INotificationRecipientSet`."""
        return bool(self._personToRationale)

    def getReason(self, person_or_email):
        """See `INotificationRecipientSet`."""
        if zope_isinstance(person_or_email, six.string_types):
            try:
                person = self._emailToPerson[person_or_email]
            except KeyError:
                raise UnknownRecipientError(person_or_email)
        elif IPerson.providedBy(person_or_email):
            person = person_or_email
        else:
            raise AssertionError(
                'Not an IPerson or email address: %r' % person_or_email)
        try:
            return self._personToRationale[person]
        except KeyError:
            raise UnknownRecipientError(person)

    def add(self, persons, reason, header):
        """See `INotificationRecipientSet`."""
        from lp.registry.model.person import get_recipients

        if (IPerson.providedBy(persons) or
                zope_isinstance(persons, StubPerson)):
            persons = [persons]

        for person in persons:
            assert (
                IPerson.providedBy(person) or
                zope_isinstance(person, StubPerson)), (
                'You can only add() an IPerson or a StubPerson: %r' % person)
            # If the person already has a rationale, keep the first one.
            if person in self._personToRationale:
                continue
            self._personToRationale[person] = reason, header
            if IPerson.providedBy(person):
                recipients = get_recipients(person)
            else:
                recipients = [person]
            for receiving_person in recipients:
                # Bypass zope's security because IEmailAddress.email is not
                # public.
                preferred_email = removeSecurityProxy(
                    receiving_person).preferredemail
                email = str(preferred_email.email)
                self._receiving_people.add((email, receiving_person))
                old_person = self._emailToPerson.get(email)
                # Only associate this email to the person, if there was
                # no association or if the previous one was to a team and
                # the newer one is to a person.
                if (old_person is None
                    or (old_person.is_team and not person.is_team)):
                    self._emailToPerson[email] = person

    def remove(self, persons):
        """See `INotificationRecipientSet`."""
        from lp.registry.model.person import get_recipients

        if IPerson.providedBy(persons):
            persons = [persons]
        for person in persons:
            assert IPerson.providedBy(person), (
                'You can only remove() an IPerson: %r' % person)
            if person in self._personToRationale:
                del self._personToRationale[person]
            for removed_person in get_recipients(person):
                # Bypass zope's security because IEmailAddress.email is
                # not public.
                preferred_email = removeSecurityProxy(
                    removed_person.preferredemail)
                email = str(preferred_email.email)
                self._receiving_people.discard((email, removed_person))
                del self._emailToPerson[email]

    def update(self, recipient_set):
        """See `INotificationRecipientSet`."""
        for person in recipient_set:
            if person in self._personToRationale:
                continue
            reason, header = recipient_set.getReason(person)
            self.add(person, reason, header)
