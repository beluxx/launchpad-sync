# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for objects that can be linked to bugs."""

__all__ = [
    "IBugLinkForm",
    "IBugLinkTarget",
    "IObjectLinkedEvent",
    "IObjectUnlinkedEvent",
    "IUnlinkBugsForm",
]

from lazr.restful.declarations import exported, exported_as_webservice_entry
from lazr.restful.fields import CollectionField, Reference
from zope.interface import Attribute, Interface, implementer
from zope.interface.interfaces import IObjectEvent
from zope.schema import Choice, Set
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from zope.security.interfaces import Unauthorized

from lp import _
from lp.bugs.interfaces.bug import IBug
from lp.services.fields import BugField


class IObjectLinkedEvent(IObjectEvent):
    """An object that has been linked to another."""

    other_object = Attribute("The object that is now linked.")
    user = Attribute("The user who linked the object.")


class IObjectUnlinkedEvent(IObjectEvent):
    """An object that has been unlinked from another."""

    other_object = Attribute("The object that is no longer linked.")
    user = Attribute("The user who unlinked the object.")


@exported_as_webservice_entry(as_of="beta")
class IBugLinkTarget(Interface):
    """An entity which can be linked to bugs.

    Examples include an ISpecification.
    """

    bugs = exported(
        CollectionField(
            title=_("Bugs related to this object."),
            value_type=Reference(schema=IBug),
            readonly=True,
        ),
        as_of="devel",
    )

    def linkBug(bug, user=None, check_permissions=True, props=None):
        """Link the object with this bug.

        If a new link is created by this method, an ObjectLinkedEvent is
        sent for each end.

        :return: True if a new link was created, False if it already existed.
        """

    def unlinkBug(bug, user=None, check_permissions=True):
        """Remove any link between this object and the bug.

        If a link is removed by this method, an ObjectUnlinkedEvent is
        sent for each end.

        :return: True if a link was deleted, False if it didn't exist.
        """


# These schemas are only used by browser/buglinktarget.py and should really
# live there. See Bug #66950.
class IBugLinkForm(Interface):
    """Schema for the unlink bugs form."""

    bug = BugField(title=_("Bug ID"), required=True)


# XXX flacoste 2006-08-29: To remain consistent with the existing source
# code layout policy, this should really be in vocabularies.buglinks but this
# is not possible because of dependencies on interfaces in some vocabularies
# modules.
@implementer(IContextSourceBinder)
class BugLinksVocabularyFactory:
    """IContextSourceBinder that creates a vocabulary of the linked bugs on
    the IBugLinkTarget.
    """

    def __call__(self, context):
        """See IContextSourceBinder."""
        terms = []
        for bug in context.bugs:
            try:
                title = _(
                    "#${bugid}: ${title}",
                    mapping={"bugid": bug.id, "title": bug.title},
                )
                terms.append(SimpleTerm(bug, bug.id, title))
            except Unauthorized:
                pass
        return SimpleVocabulary(terms)


class IUnlinkBugsForm(Interface):
    """Schema for the unlink bugs form."""

    bugs = Set(
        title=_("Bug Links"),
        required=True,
        value_type=Choice(source=BugLinksVocabularyFactory()),
        description=_("Select the bug links that you want to remove."),
    )
