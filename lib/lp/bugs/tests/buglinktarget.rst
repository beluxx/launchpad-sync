IBugLinkTarget Interface
========================

Launchpad includes Malone, the powerful bug tracker. One of the best
features of Malone is the ability to track a bug in multiple products
and/or packages. A bug can also be linked to other non-bug tracking
objects like questions, CVEs, specifications, or merge proposals.

The IBugLinkTarget interface is used for that general purpose linking.
This file documents that interface and can be used to validate
implementation of this interface on a particular object. (This object is
made available through the 'target' variable which is defined outside of
this file, usually by a LaunchpadFunctionalTestCase. This instance
shouldn't have any bugs linked to it at the start of the test.)

    # Some parts of the IBugLinkTarget interface are only accessible
    # to a registered user.
    >>> login("no-priv@canonical.com")
    >>> from zope.interface.verify import verifyObject
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.interfaces.buglink import IBugLinkTarget

    >>> verifyObject(IBugLinkTarget, target)
    True

linkBug()
---------

    >>> bugset = getUtility(IBugSet)
    >>> bug1 = bugset.get(1)

The linkBug() method is used to link a bug to the target. It takes as
parameter the bug which should be linked. The method returns True if a
new link was created.

    >>> target.linkBug(bug1)
    True

When the bug was already linked to the target, the existing link should
be used.

    >>> target.linkBug(bug1)
    False

When a bug link is created, an IObjectLinkedEvent for each end should be
fired.

    >>> from zope.interface import Interface
    >>> from lp.bugs.interfaces.buglink import (
    ...     IObjectLinkedEvent,
    ...     IObjectUnlinkedEvent,
    ... )
    >>> from lp.testing.fixture import ZopeEventHandlerFixture
    >>> linked_events = []
    >>> linked_event_listener = ZopeEventHandlerFixture(
    ...     lambda object, event: linked_events.append(event),
    ...     (Interface, IObjectLinkedEvent),
    ... )
    >>> linked_event_listener.setUp()

    >>> bug2 = bugset.get(2)
    >>> target.linkBug(bugset.get(2))
    True
    >>> linked_events[-2].object == bug2
    True
    >>> linked_events[-2].other_object == target
    True
    >>> linked_events[-1].object == target
    True
    >>> linked_events[-1].other_object == bug2
    True

Of course, if no new link is created, no events should be fired:

    >>> linked_events = []
    >>> target.linkBug(bug2)
    False
    >>> linked_events
    []

Anonymous users cannot use linkBug():

    >>> login(ANONYMOUS)
    >>> target.linkBug(bug2)
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

A user can only link to a private bug if they are subscribed to the bug or
if they are an administrator:

    >>> login("no-priv@canonical.com")
    >>> private_bug = bugset.get(6)
    >>> private_bug.setPrivate(True, factory.makePerson())
    True
    >>> target.linkBug(private_bug, factory.makePerson())
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> admin = getUtility(IPersonSet).getByEmail("admin@canonical.com")
    >>> login("foo.bar@canonical.com")
    >>> target.linkBug(private_bug, admin)
    True

bugs
----

The list of bugs linked to the target should be available in the bugs
attributes:

    >>> [bug.id for bug in target.bugs]
    [1, 2, 6]

unlinkBug()
-----------

The unlinkBug() method is used to remove a link between a bug and
the target.

This method is only available to registered users:

    >>> login(ANONYMOUS)
    >>> target.unlinkBug(bug2, None)
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

    >>> login("no-priv@canonical.com")

The method returns whether the link existed. It should also send an
IObjectUnlinkedEvent for each of the removed link:

    >>> unlinked_events = []
    >>> unlinked_event_listener = ZopeEventHandlerFixture(
    ...     lambda object, event: unlinked_events.append(event),
    ...     (Interface, IObjectUnlinkedEvent),
    ... )
    >>> unlinked_event_listener.setUp()

    >>> target.unlinkBug(bug1, factory.makePerson())
    True
    >>> unlinked_events[-2].object == bug1
    True
    >>> unlinked_events[-2].other_object == target
    True
    >>> unlinked_events[-1].object == target
    True
    >>> unlinked_events[-1].other_object == bug1
    True

    >>> [bug.id for bug in target.bugs]
    [2, 6]

When the bug was not linked to the target, that method should return
False (and not trigger any events):

    >>> unlinked_events = []
    >>> target.unlinkBug(bug1)
    False
    >>> unlinked_events
    []

A user can only remove a link to a private bug if they are subscribed to
the bug or if they are an administrator.

    >>> target.unlinkBug(private_bug)
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

    >>> login("foo.bar@canonical.com")
    >>> target.unlinkBug(private_bug, admin)
    True

Cleanup
-------

    # Unregister event listeners.
    >>> linked_event_listener.cleanUp()
    >>> unlinked_event_listener.cleanUp()
