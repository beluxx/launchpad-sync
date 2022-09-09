Hide bug comments
=================

Bug comments can be hidden by setting visible to False.  There is
a corresponding API method to do this.  Call the method with the
number of the comment in the bug's message list along with a
boolean parameter for visible.

The number of the comment in the bug's message list is zero
indexed.  To hide the third comment in the list of comments
for bug 11:

    >>> print(
    ...     webservice.named_post(
    ...         "/bugs/11",
    ...         "setCommentVisibility",
    ...         comment_number=2,
    ...         visible=False,
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...

Accessing the message again, visible is set to False.  Notice,
too, that even with visible set False, the order of the messages
is preserved.  setCommentVisibility only affects page display
not access in the Bug.messages array.

    >>> from zope.component import getUtility
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.interfaces.bugmessage import IBugMessageSet
    >>> login("foo.bar@canonical.com")
    >>> bug_11 = getUtility(IBugSet).get(11)
    >>> bug_message = getUtility(IBugMessageSet).getByBugAndMessage(
    ...     bug_11, bug_11.messages[2]
    ... )
    >>> bug_message.message.visible
    False
    >>> logout()

Since the array order is the same, the message can be marked
visible again.

    >>> print(
    ...     webservice.named_post(
    ...         "/bugs/11",
    ...         "setCommentVisibility",
    ...         comment_number=2,
    ...         visible=True,
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...

And indeed, the comment is visible again.

    >>> login("foo.bar@canonical.com")
    >>> bug_11 = getUtility(IBugSet).get(11)
    >>> bug_message = getUtility(IBugMessageSet).getByBugAndMessage(
    ...     bug_11, bug_11.messages[2]
    ... )
    >>> bug_message.message.visible
    True
    >>> logout()

This method can only be accessed by Launchpad admins.  (In the example
above, the default "webservice" uses an admin account.)

    >>> print(
    ...     user_webservice.named_post(
    ...         "/bugs/11",
    ...         "setCommentVisibility",
    ...         comment_number=1,
    ...         visible=False,
    ...     )
    ... )
    HTTP/1.1 401 Unauthorized
    ...
