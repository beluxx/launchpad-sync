# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.app.event.interfaces import (
    IObjectModifiedEvent, IObjectEvent, IObjectCreatedEvent)
from zope.interface import Interface, Attribute


class ISQLObjectCreatedEvent(IObjectCreatedEvent):
    """An SQLObject has been created."""
    user = Attribute("The user who created the object.")


class ISQLObjectDeletedEvent(IObjectEvent):
    """An SQLObject is being deleted."""
    user = Attribute("The user who is making this change.")


class ISQLObjectModifiedEvent(IObjectModifiedEvent):
    """An SQLObject has been modified."""

    object_before_modification = Attribute("The object before modification.")
    edited_fields = Attribute(
        "The list of fields that were edited. A field name may appear in this "
        "list if it were shown on an edit form, but not actually changed.")
    user = Attribute("The user who modified the object.")


class ISQLObjectToBeModifiedEvent(IObjectEvent):
    """An SQLObject is about to be modified."""

    new_values = Attribute("A dict of fieldname -> newvalue pairs.")
    user = Attribute("The user who will modify the object.")


class IJoinTeamEvent(Interface):
    """A user joined (or tried to join) a team."""

    user = Attribute("The user who joined the team.")
    team = Attribute("The team.")


class IKarmaAssignedEvent(IObjectEvent):
    """Karma was assigned to a person."""

    karma = Attribute("The Karma object assigned to the person.")

