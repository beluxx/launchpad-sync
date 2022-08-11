IBugLinkTarget Views
====================

The +linkbug and +unlinkbug views operates on IBugLinkTarget.

    >>> from zope.component import getMultiAdapter
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lazr.lifecycle.event import ObjectModifiedEvent
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.interfaces.buglink import IBugLinkTarget
    >>> from lp.bugs.interfaces.cve import ICveSet

    >>> bugset = getUtility(IBugSet)
    >>> cve = getUtility(ICveSet)['2005-2730']

    (Setup an event listener.)
    >>> from lp.testing.fixture import ZopeEventHandlerFixture
    >>> collected_events = []
    >>> modified_listener = ZopeEventHandlerFixture(
    ...     lambda object, event: collected_events.append(event),
    ...     (IBugLinkTarget, ObjectModifiedEvent))
    >>> modified_listener.setUp()

    (Login because bug link management is only available to registered users.)
    >>> login('no-priv@canonical.com')


Link Bug View
-------------

The +linkbug view is used to link bugs to IBugLinkTarget.

    >>> view = create_view(cve, name='+linkbug')
    >>> print(view.label)
    Link a bug report

    >>> print(view.cancel_url)
    http://bugs.launchpad.test/bugs/cve/2005-2730

It has a simple widget to enter the bug number or nickname of the bug to link
to. After it links the bug, it sends a ObjectModifiedEvent.

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={'field.actions.link':'Link', 'field.bug' : '1'})
    >>> linkView = getMultiAdapter((cve, request), name='+linkbug')
    >>> linkView.initialize()

One notification should have been added to the response.

    >>> len(request.response.notifications)
    1

Bug #1 was added to the object:

    >>> print([bug.id for bug in cve.bugs])
    [1]

A ObjectModifiedEvent was sent:

    >>> len(collected_events)
    1
    >>> event = collected_events[0]
    >>> event
    <...ObjectModifiedEvent...>
    >>> event.object == cve
    True
    >>> event.edited_fields
    ['bugs']
    >>> event.object_before_modification.bugs
    []

    (Cleanup)
    >>> collected_events = []


Unlink Bugs View
----------------

    (Link some other bugs first.)
    >>> link = cve.linkBug(bugset.get(2))
    >>> link = cve.linkBug(bugset.get(3))


The +unlinkbug view is used to unlink a selection of bugs from an
IBugLinkTarget.

    >>> view = create_view(cve, name='+unlinkbug')
    >>> print(view.label)
    Remove links to bug reports

    >>> print(view.cancel_url)
    http://bugs.launchpad.test/bugs/cve/2005-2730

After removing the bugs, it sends a SQLObjectModified event.

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={'field.actions.remove':'Remove', 'field.bugs' : ['1', '2']})
    >>> unlinkView = getMultiAdapter((cve, request), name='+unlinkbug')
    >>> unlinkView.initialize()

One notification by removed bugs should have been added to the response.

    >>> len(request.response.notifications)
    2

The two bugs were removed and only bug #3 should still be present:

    >>> print([bug.id for bug in cve.bugs])
    [3]

A ObjectModifiedEvent was sent:

    >>> len(collected_events)
    1
    >>> event = collected_events[0]
    >>> event
    <...ObjectModifiedEvent...>
    >>> event.object == cve
    True
    >>> event.edited_fields
    ['bugs']
    >>> print([bug.id for bug in event.object_before_modification.bugs])
    [1, 2, 3]


Bug titles are escaped in notifications
---------------------------------------

Bug titles may legitimately contain HTML markup, such as reporting that
there is "Too much space between <h1> and <h2>". Notifications, like the
the bug link notification, may also contain HTML markup. To prevent a
XSS vulnerability, the bug title is escaped before it is interpolated
with the notification message. (see bug 183277).

We will give bug #2 a very bad title, then link the cve to the bug.

    >>> bug = bugset.get(2)
    >>> bug.title = '<script>window.alert("Hello!")</script>'

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={'field.actions.link':'Link', 'field.bug' : '2'})
    >>> linkView = getMultiAdapter((cve, request), name='+linkbug')
    >>> linkView.initialize()

The notification contains the escaped bug title.

    >>> for notification in request.response.notifications:
    ...     print(notification.message)
    Added link to bug #2:
    ...&lt;script&gt;window.alert(&quot;Hello!&quot;)&lt;/script&gt;....


Cleanup
-------

    (Deactivate the event listener.)
    >>> modified_listener.cleanUp()
