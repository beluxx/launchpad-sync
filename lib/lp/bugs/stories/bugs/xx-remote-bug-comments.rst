Remote bug comments
===================

Comments imported into Launchpad from external bug trackers are
formatted for display in a way that distinguishes them from comments
entered within Launchpad itself.

    >>> user_browser.open("http://bugs.launchpad.test/redfish/+bug/15")
    >>> remote_bug_comment = find_tags_by_class(
    ...     user_browser.contents, "remoteBugComment", only_first=True
    ... )
    >>> details = remote_bug_comment.find(
    ...     attrs={"class": "boardCommentDetails"}
    ... )
    >>> print(extract_text(details))
    Revision history for this message
    In
    Debian Bug tracker #308994,
    josh (jbuhl-nospam)
    wrote
    ...
    gnome-volume-manager: dvd+rw unreadable when automounted ...

Remote comments are decorated with the bug watch icon, to distinguish
them from comments posted directly by Launchpad users.

    >>> print(details.find_all("img")[1]["src"])
    /@@/bug-remote

Since it's possible to reply to imported comments and have them
synchronized with the remote bug tracker, we display a simple reply form
inlined, to make it clear that the comment will end up on the remote
bug tracker.

    >>> activity = remote_bug_comment.find(
    ...     attrs={"class": "boardCommentActivity"}
    ... )
    >>> print(extract_text(activity))
    Reply on Debian Bug tracker...

When javascript is not available, the link simply takes us to the
individual comment page, where the inline form is displayed.

    >>> user_browser.getLink("Reply on Debian Bug tracker").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/redfish/+bug/15/comments/1

We enter a comment, and submit the form.

    >>> user_browser.getControl(name="field.comment").value = (
    ...     "A reply comment."
    ... )
    >>> user_browser.getControl(name="field.actions.save").click()

The new comment appears, formatted as a remote bug comment.

    >>> new_bug_comment = find_tags_by_class(
    ...     user_browser.contents, "remoteBugComment"
    ... )[-1]
    >>> print(extract_text(new_bug_comment))
    Revision history for this message
    In
    Debian Bug tracker #308994,
    ...
    #7
      A reply comment.
    ...

The comment isn't synchronized immediately. To make that clear, we
mark the comment as 'awaiting synchronization' until it makes its way
to the remote bug tracker.

    >>> activity = new_bug_comment.find(
    ...     attrs={"class": "boardCommentActivity"}
    ... )
    >>> print(extract_text(activity.find_all("td")[1]))
    Awaiting synchronization

When the comment is synchronized, it receives a remote comment id, and
the 'awaiting synchronization' mark goes away.

    >>> from zope.component import getUtility
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.interfaces.bugmessage import IBugMessageSet
    >>> login("foo.bar@canonical.com")
    >>> bug_15 = getUtility(IBugSet).get(15)
    >>> message = bug_15.messages.last()
    >>> print(message.text_contents)
    A reply comment.
    >>> bug_message = getUtility(IBugMessageSet).getByBugAndMessage(
    ...     bug_15, message
    ... )
    >>> removeSecurityProxy(bug_message).remote_comment_id = (
    ...     "test-remote-comment-id"
    ... )
    >>> flush_database_updates()
    >>> logout()

    >>> user_browser.open("http://bugs.launchpad.test/redfish/+bug/15")
    >>> last_bug_comment = find_tags_by_class(
    ...     user_browser.contents, "remoteBugComment"
    ... )[-1]
    >>> print(extract_text(last_bug_comment))
    Revision history for this message
    In
    Debian Bug tracker #308994,
    ...
    #7
      A reply comment.
    ...
    >>> footer = last_bug_comment.find(attrs={"class": "boardCommentFooter"})
    >>> "Awaiting synchronization" in extract_text(footer)
    False

When an anonymous user views a remote comment, the reply links are
hidden, since they can't be used anonymously anyway.

    >>> anon_browser.open("http://bugs.launchpad.test/redfish/+bug/15")
    >>> remote_bug_comment = find_tags_by_class(
    ...     anon_browser.contents, "remoteBugComment", only_first=True
    ... )
    >>> activity = remote_bug_comment.find(
    ...     attrs={"class": "boardCommentActivity"}
    ... )
    >>> "Reply" in extract_text(activity)
    False
