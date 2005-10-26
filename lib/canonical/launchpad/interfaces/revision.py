# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Revision interfaces."""

__metaclass__ = type
__all__ = ['IRevision', 'IRevisionAuthor', 'IRevisionParent', 'IRevisionNumber']

from zope.i18nmessageid import MessageIDFactory
from zope.interface import Interface, Attribute
from zope.schema import Datetime, Int, Choice, Text, TextLine, Float

from canonical.launchpad.interfaces import IHasOwner


_ = MessageIDFactory('launchpad')


class IRevision(IHasOwner):
    """Bazaar revision."""

    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    date_created = Datetime(
        title=_("Date Created"), required=True, readonly=True)
    log_body = Attribute("The revision log message.")
    revision_author = Attribute("The revision author identifier.")
    gpgkey = Attribute("The GPG key used to sign the revision.")
    revision_id = Attribute("The unique revision identifier.")
    revision_date = Datetime(
        title=_("The date the revision was committed."),
        required=True, readonly=True)


class IRevisionAuthor(Interface):
    """Committer of a Bazaar revision."""

    # id = Int(title=_("RevisionAuthor ID"), required=True, readonly=True)
    name = TextLine(title=_("Revision Author Name"), required=True)


class IRevisionParent(Interface):
    """The association between a revision and its parent revisions."""

    revision = Attribute("The descendant revision.")
    sequence = Attribute("The order of the parent of that revision.")
    parent = Attribute("The revision_id of the parent revision.")


class IRevisionNumber(Interface):
    """The association between a revision and a branch."""

    sequence = Int(
        title=_("Revision Number"), required=True,
        description=_("The index of a revision within a branch's history."))
    branch = Attribute("The branch this revision number belongs to.")
    revision = Attribute("The revision with that index in this branch.")
