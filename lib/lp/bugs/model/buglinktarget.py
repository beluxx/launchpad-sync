# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "BugLinkTargetMixin",
    "ObjectLinkedEvent",
    "ObjectUnlinkedEvent",
]

import lazr.lifecycle.event
from zope.event import notify
from zope.interface import implementer
from zope.security.interfaces import Unauthorized

from lp.bugs.interfaces.buglink import IObjectLinkedEvent, IObjectUnlinkedEvent


# XXX wgrant 2015-09-25: lazr.lifecycle.event.LifecyleEventBase is all
# of mispelled, private, and the sole implementer of user-fetching
# logic that we require.
@implementer(IObjectLinkedEvent)
class ObjectLinkedEvent(lazr.lifecycle.event.LifecyleEventBase):
    def __init__(self, object, other_object, user=None):
        super().__init__(object, user=user)
        self.other_object = other_object


@implementer(IObjectUnlinkedEvent)
class ObjectUnlinkedEvent(lazr.lifecycle.event.LifecyleEventBase):
    def __init__(self, object, other_object, user=None):
        super().__init__(object, user=user)
        self.other_object = other_object


class BugLinkTargetMixin:
    """Mixin class for IBugLinkTarget implementation."""

    def createBugLink(self, bug, props=None):
        """Subclass should override to create a BugLink instance."""
        raise NotImplementedError("missing createBugLink() implementation")

    def deleteBugLink(self, bug):
        """Subclass should override to delete a BugLink instance."""
        raise NotImplementedError("missing deleteBugLink() implementation")

    # IBugLinkTarget implementation
    def linkBug(self, bug, user=None, check_permissions=True, props=None):
        """See IBugLinkTarget."""
        if check_permissions and not bug.userCanView(user):
            raise Unauthorized(
                "Cannot link a private bug you don't have access to"
            )
        if bug in self.bugs:
            return False
        self.createBugLink(bug, props=props)
        notify(ObjectLinkedEvent(bug, self, user=user))
        notify(ObjectLinkedEvent(self, bug, user=user))
        return True

    def unlinkBug(self, bug, user=None, check_permissions=True):
        """See IBugLinkTarget."""
        if check_permissions and not bug.userCanView(user):
            raise Unauthorized(
                "Cannot unlink a private bug you don't have access to"
            )
        if bug not in self.bugs:
            return False
        self.deleteBugLink(bug)
        notify(ObjectUnlinkedEvent(bug, self, user=user))
        notify(ObjectUnlinkedEvent(self, bug, user=user))
        return True
