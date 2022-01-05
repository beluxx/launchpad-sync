# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Account interfaces."""

__all__ = [
    'AccountDeceasedError',
    'AccountStatus',
    'AccountStatusError',
    'AccountSuspendedError',
    'AccountCreationRationale',
    'IAccount',
    'IAccountModerateRestricted',
    'IAccountPublic',
    'IAccountSet',
    'IAccountViewRestricted',
    'INACTIVE_ACCOUNT_STATUSES',
    ]

import http.client

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from lazr.restful.declarations import error_status
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Datetime,
    Int,
    Text,
    )
from zope.security.proxy import removeSecurityProxy

from lp import _
from lp.app.validators import LaunchpadValidationError
from lp.services.fields import StrippedTextLine


@error_status(http.client.BAD_REQUEST)
class AccountSuspendedError(Exception):
    """The account being accessed has been suspended."""


@error_status(http.client.BAD_REQUEST)
class AccountDeceasedError(Exception):
    """The account being accessed belongs to a deceased user."""


class AccountStatus(DBEnumeratedType):
    """The status of an account."""

    PLACEHOLDER = DBItem(5, """
        Placeholder

        The account was created automatically by SSO and exists solely
        to hold a username. It is visible only to staff.

        XXX wgrant 2016-03-03: This is a hack until usernames are moved
            into SSO properly.
        """)

    NOACCOUNT = DBItem(10, """
        Unactivated

        The account has not yet been activated.
        """)

    ACTIVE = DBItem(20, """
        Active

        The account is active.
        """)

    DEACTIVATED = DBItem(30, """
        Deactivated

        The account has been deactivated by the account's owner.
        """)

    SUSPENDED = DBItem(40, """
        Suspended

        The account has been suspended by a Launchpad admin.
        """)

    CLOSED = DBItem(50, """
        Closed

        The account has been permanently closed, removing as much personal
        information as possible.
        """)

    DECEASED = DBItem(60, """
        Deceased

        The account belonged to somebody who is now deceased, and has been
        permanently archived.
        """)


INACTIVE_ACCOUNT_STATUSES = [
    AccountStatus.PLACEHOLDER, AccountStatus.DEACTIVATED,
    AccountStatus.SUSPENDED, AccountStatus.CLOSED, AccountStatus.DECEASED]


class AccountCreationRationale(DBEnumeratedType):
    """The rationale for the creation of a given account.

    These statuses are seeded from PersonCreationRationale, as our
    initial accounts where split from the Person table. A number of the
    creation rationales only make sense in this historical context (eg.
    importing bugs into Launchpad no longer needs to create Account records).
    """

    UNKNOWN = DBItem(1, """
        Unknown

        The reason for the creation of this account is unknown.
        """)

    BUGIMPORT = DBItem(2, """
        Existing user in another bugtracker from which we imported bugs.

        A bugzilla import or sf.net import, for instance. The bugtracker from
        which we were importing should be described in
        Person.creation_comment.
        """)

    SOURCEPACKAGEIMPORT = DBItem(3, """
        This person was mentioned in a source package we imported.

        When gina imports source packages, it has to create Person entries for
        the email addresses that are listed as maintainer and/or uploader of
        the package, in case they don't exist in Launchpad.
        """)

    POFILEIMPORT = DBItem(4, """
        This person was mentioned in a POFile imported into Rosetta.

        When importing POFiles into Rosetta, we need to give credit for the
        translations on that POFile to its last translator, which may not
        exist in Launchpad, so we'd need to create it.
        """)

    KEYRINGTRUSTANALYZER = DBItem(5, """
        Created by the keyring trust analyzer.

        The keyring trust analyzer is responsible for scanning GPG keys
        belonging to the strongly connected set and assign all email addresses
        registered on those keys to the people representing their owners in
        Launchpad. If any of these people doesn't exist, it creates them.
        """)

    FROMEMAILMESSAGE = DBItem(6, """
        Created when parsing an email message.

        Sometimes we parse email messages and want to associate them with the
        sender, which may not have a Launchpad account. In that case we need
        to create a Person entry to associate with the email.
        """)

    SOURCEPACKAGEUPLOAD = DBItem(7, """
        This person was mentioned in a source package uploaded.

        Some uploaded packages may be uploaded with a maintainer that is not
        registered in Launchpad, and in these cases, soyuz may decide to
        create the new Person instead of complaining.
        """)

    OWNER_CREATED_LAUNCHPAD = DBItem(8, """
        Created by the owner themselves, coming from Launchpad.

        Somebody was navigating through Launchpad and at some point decided to
        create an account.
        """)

    OWNER_CREATED_SHIPIT = DBItem(9, """
        Created by the owner themselves, coming from Shipit.

        Somebody went to one of the shipit sites to request Ubuntu CDs and was
        directed to Launchpad to create an account.
        """)

    OWNER_CREATED_UBUNTU_WIKI = DBItem(10, """
        Created by the owner themselves, coming from the Ubuntu wiki.

        Somebody went to the Ubuntu wiki and was directed to Launchpad to
        create an account.
        """)

    USER_CREATED = DBItem(11, """
        Created by a user to represent a person which does not use Launchpad.

        A user wanted to reference a person which is not a Launchpad user, so
        they created this "placeholder" profile.
        """)

    OWNER_CREATED_UBUNTU_SHOP = DBItem(12, """
        Created by the owner themselves, coming from the Ubuntu Shop.

        Somebody went to the Ubuntu Shop and was directed to Launchpad to
        create an account.
        """)

    OWNER_CREATED_UNKNOWN_TRUSTROOT = DBItem(13, """
        Created by the owner themselves, coming from unknown OpenID consumer.

        Somebody went to an OpenID consumer we don't know about and was
        directed to Launchpad to create an account.
        """)

    OWNER_SUBMITTED_HARDWARE_TEST = DBItem(14, """
        Created by a submission to the hardware database.

        Somebody without a Launchpad account made a submission to the
        hardware database.
        """)

    BUGWATCH = DBItem(15, """
        Created by the updating of a bug watch.

        A watch was made against a remote bug that the user submitted or
        commented on.
        """)

    SOFTWARE_CENTER_PURCHASE = DBItem(16, """
        Created by purchasing commercial software through Software Center.

        A purchase of commercial software (ie. subscriptions to a private
        and commercial archive) was made via Software Center.
        """)

    USERNAME_PLACEHOLDER = DBItem(17, """
        Created by setting a username in SSO.

        Somebody without a Launchpad account set their username in SSO.
        Since SSO doesn't store usernames directly, an invisible
        placeholder Launchpad account is required.
        """)


class AccountStatusError(LaunchpadValidationError):
    """The account status cannot change to the proposed status."""


class AccountStatusChoice(Choice):
    """A valid status and transition."""

    transitions = {
        AccountStatus.PLACEHOLDER: [
            AccountStatus.NOACCOUNT, AccountStatus.ACTIVE,
            AccountStatus.DECEASED],
        AccountStatus.NOACCOUNT: [
            AccountStatus.ACTIVE, AccountStatus.CLOSED,
            AccountStatus.DECEASED],
        AccountStatus.ACTIVE: [
            AccountStatus.DEACTIVATED, AccountStatus.SUSPENDED,
            AccountStatus.CLOSED, AccountStatus.DECEASED],
        AccountStatus.DEACTIVATED: [
            AccountStatus.ACTIVE, AccountStatus.CLOSED,
            AccountStatus.DECEASED],
        AccountStatus.SUSPENDED: [
            AccountStatus.DEACTIVATED, AccountStatus.CLOSED,
            AccountStatus.DECEASED],
        AccountStatus.CLOSED: [],
        AccountStatus.DECEASED: [
            AccountStatus.DEACTIVATED, AccountStatus.CLOSED],
        }

    def constraint(self, value):
        """See `IField`."""
        if not IAccount.providedBy(self.context):
            # Not an account, eg. validating Person.setAccountStatus.
            return True
        if removeSecurityProxy(self.context)._SO_creating:
            # This object is initializing.
            return True
        if self.context.status == value:
            return True
        return value in self.transitions[self.context.status]

    def _validate(self, value):
        """See `IField`.

        Ensure the value is a valid transition for current AccountStatus.

        :raises AccountStatusError: When self.constraint() returns False.
        """
        if not self.constraint(value):
            raise AccountStatusError(
                "The status cannot change from %s to %s" %
                (removeSecurityProxy(self.context).status, value))
        super()._validate(value)


class IAccountPublic(Interface):
    """Public information on an `IAccount`."""

    id = Int(title=_('ID'), required=True, readonly=True)

    displayname = StrippedTextLine(
        title=_('Display Name'), required=True, readonly=False,
        description=_("Your name as you would like it displayed."))

    status = AccountStatusChoice(
        title=_("The status of this account"), required=True,
        readonly=True, vocabulary=AccountStatus)


class IAccountViewRestricted(Interface):
    """Private information on an `IAccount`."""

    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)

    creation_rationale = Choice(
        title=_("Rationale for this account's creation."), required=True,
        readonly=True, values=AccountCreationRationale.items)

    openid_identifiers = Attribute(_("Linked OpenId Identifiers"))

    date_status_set = Datetime(
        title=_('Date status last modified.'), required=True, readonly=True)

    def reactivate(comment):
        """Activate this account.

        Set the account status to ACTIVE.

        :param comment: An explanation of why the account status changed.
        """


class IAccountModerateRestricted(Interface):

    status_history = Text(
        title=_("Account status comments"), required=False, readonly=True)

    def setStatus(status, user, comment):
        """Change the status of this account.

        :param user: The user performing the action or None.
        :param comment: An explanation of the change to be logged in
            status_history.
        """


class IAccount(IAccountPublic, IAccountViewRestricted,
               IAccountModerateRestricted):
    """Interface describing an `Account`."""


class IAccountSet(Interface):
    """Creation of and access to `IAccount` providers."""

    def new(rationale, displayname):
        """Create a new `IAccount`.

        :param rationale: An `AccountCreationRationale` value.
        :param displayname: The user's display name.

        :return: The newly created `IAccount` provider.
        """

    def get(id):
        """Return the `IAccount` with the given id.

        :raises LookupError: If the account is not found.
        """

    def getByOpenIDIdentifier(openid_identity):
        """Return the `IAccount` with the given OpenID identifier.

         :param open_identifier: An ascii compatible string that is either
             the old or new openid_identifier that belongs to an account.
         :return: An `IAccount`
         :raises LookupError: If the account is not found.
         """
