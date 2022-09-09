Bug Comments
############

The BugComment class is a content class assembled by browser code; it
abstracts a single bug comment, has an index, and can be rendered
independently.

    >>> from zope.component import getMultiAdapter
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.bugs.interfaces.bug import IBugSet


Handling of the bug's first comment
===================================

The bug's description starts out identical to its first comment. In the course
of a bug's life, the description may be updated, but the first comment stays
intact. To improve readability, we never display the first comment in the bug
page, and this is why the event stream elides it doesn't include it:

    >>> bug_ten = getUtility(IBugSet).get(10)
    >>> bug_ten_bugtask = bug_ten.bugtasks[0]

    >>> bug_view = getMultiAdapter(
    ...     (bug_ten_bugtask, LaunchpadTestRequest()), name="+index"
    ... )
    >>> bug_view.initialize()
    >>> def bug_comments(bug_view):
    ...     return [
    ...         event.get("comment")
    ...         for event in bug_view.activity_and_comments
    ...         if event.get("comment")
    ...     ]
    ...
    >>> [bug_comment.index for bug_comment in bug_comments(bug_view)]
    [1]

In the case of bug 10, the first comment is identical to the bug's
description:

    >>> bug_view.wasDescriptionModified()
    False

And in this case we don't say anything special in the UI. If the description
was updated, the UI includes a note on this matter and a link to the original
comment.

The first comment may have bug attachments. While it is not possible
to add an attachment via the web interface to the first comment, bugs
submitted via the email interface can have file attachments, which are
stored as bug attachments of the first comment. Similarly, the first
comment of bugs imported from other bug trackers may have attachments.
We display these attachments in the comment section of the Web UI,
hence the activity stream contains the first comment, if it has attachments.

Currently, the first comment of bug 11 has no attachments, hence
BugTaskView.activity_and_comments does not return the
first comment.

    >>> bug_11 = getUtility(IBugSet).get(11)
    >>> bug_11_bugtask = bug_11.bugtasks[0]
    >>> bug_11_view = getMultiAdapter(
    ...     (bug_11_bugtask, LaunchpadTestRequest()), name="+index"
    ... )
    >>> bug_11_view.initialize()
    >>> rendered_comments = bug_comments(bug_11_view)
    >>> [bug_comment.index for bug_comment in rendered_comments]
    [1, 2, 3, 4, 5, 6]

If we add an attachment to the first comment, this comment is included
in activity_and_comments...

    >>> from io import BytesIO
    >>> login("test@canonical.com")
    >>> attachment = bug_11.addAttachment(
    ...     owner=None,
    ...     data=BytesIO(b"whatever"),
    ...     comment=bug_11.initial_message,
    ...     filename="test.txt",
    ...     is_patch=False,
    ...     content_type="text/plain",
    ...     description="sample data",
    ... )
    >>> bug_11_view = getMultiAdapter(
    ...     (bug_11_bugtask, LaunchpadTestRequest()), name="+index"
    ... )
    >>> bug_11_view.initialize()
    >>> rendered_comments = bug_comments(bug_11_view)
    >>> [bug_comment.index for bug_comment in rendered_comments]
    [0, 1, 2, 3, 4, 5, 6]
    >>>

...but the attribute text_for_display of the first comment is empty.
This allows us to display the attachments of the initial message
as the first comment, without repeating the text of the bug report.

    >>> rendered_comments[0].text_for_display
    ''
    >>> print(rendered_comments[0].text_contents)
    I've had problems when switching from Jokosher...


Comment truncation
==================

If a comment is too long, we truncate it before we display it and
display a link to view the full comment. Let's change the default
threshold so that all comments truncate.

    >>> from lp.services.config import config
    >>> max_comment_size = """
    ...     [malone]
    ...     max_comment_size: 20
    ...     """
    >>> config.push("max_comment_size", max_comment_size)

(For bug comments the context isn't too important, so we get the page using
just any of the bug's bugtask.)

    >>> bug_two = getUtility(IBugSet).get(2)
    >>> bug_two_bugtask = bug_two.bugtasks[0]
    >>> bug_view = getMultiAdapter(
    ...     (bug_two_bugtask, LaunchpadTestRequest()), name="+index"
    ... )
    >>> bug_view.initialize()

If we get the bug comments from the view we can see that the two additional
comments have been truncated:

    >>> [
    ...     (bug_comment.index, bug_comment.too_long)
    ...     for bug_comment in bug_comments(bug_view)
    ... ]
    [(1, True), (2, True)]

Let's take a closer look at one of the truncated comments. We can
display the truncated text using text_for_display:

    >>> comment_one = bug_comments(bug_view)[0]
    >>> print(comment_one.text_for_display)  # doctest: -ELLIPSIS
    This would be a real...

The UI will display information about the comment being truncated and
provide a link to view the full comment.


Comments with multiple chunks
=============================

Bug 10 has two comments: one which is the initial description, and one
which is a multi-chunk comment added through the email interface. To grab
/all/ BugComments related to it, we use the browser function
get_comments_for_bugtask:

    >>> from lp.bugs.browser.bugtask import get_comments_for_bugtask
    >>> all_comments = get_comments_for_bugtask(bug_ten_bugtask)

    >>> [bug_comment.index for bug_comment in all_comments]
    [0, 1]
    >>> print(all_comments[0].text_for_display)
    test bug
    >>> print(all_comments[1].text_for_display)
    Welcome to Canada!
    <BLANKLINE>
    Unicode™ text

Note that multi-chunk comments are only created by the email interface
itself; adding comments through the web UI always places them in the
same chunk.


Comment titles
==============

This function also eliminates redundant message titles. We have a policy of
only displaying message titles when these are "new" to the bug. That means
they are different to the bug title, and different to the previous message.

The function sets a comment.display_title to True if the title should be
displayed.

    >>> bug_11 = getUtility(IBugSet).get(11)
    >>> all_comments = get_comments_for_bugtask(bug_11.bugtasks[0])
    >>> for comment in all_comments:
    ...     print(comment.display_title, comment.title)
    ...
    False Make Jokosher use autoaudiosink
    False Re: Make Jokosher use autoaudiosink
    False Re: Make Jokosher use autoaudiosink
    True Autoaudiosink is no longer under development
    False Re: Autoaudiosink is no longer under development
    True This is a really new title
    False Re: Make Jokosher use autoaudiosink
    >>> bug_12 = getUtility(IBugSet).get(12)
    >>> all_comments = get_comments_for_bugtask(bug_12.bugtasks[0])
    >>> for comment in all_comments:
    ...     print(comment.display_title, comment.title)
    ...
    False Copy, Cut and Delete operations should work on selections
    False Re: Copy, Cut and Delete operations should work on selections
    False Re: Copy, Cut and Delete operations should work on selections
    False Re: Copy, Cut and Delete operations should work on selections
    False Re: Copy, Cut and Delete operations should work on selections


Comment omission
================

If a comment made by the same user is strictly identical to its previous
comment in sequence, it will be omitted. Let's add some comments and
attachments to a bug to see this in action:

    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> user = getUtility(ILaunchBag).user
    >>> different_user = getUtility(IPersonSet).getByName("name16")

    >>> login("test@canonical.com")
    >>> bug_three = getUtility(IBugSet).get(3)
    >>> m1 = bug_three.newMessage(
    ...     owner=user, subject="Hi", content="Hello there"
    ... )
    >>> m2 = bug_three.newMessage(
    ...     owner=user, subject="Hi", content="Hello there"
    ... )
    >>> m3 = bug_three.newMessage(
    ...     owner=user, subject="Ho", content="Hello there"
    ... )
    >>> m4 = bug_three.newMessage(
    ...     owner=user, subject="Ho", content="Hello there"
    ... )
    >>> file_ = BytesIO(b"Bogus content makes the world go round")
    >>> a1 = bug_three.addAttachment(
    ...     owner=user,
    ...     data=file_,
    ...     description="Ho",
    ...     filename="munchy",
    ...     comment="Hello there",
    ... )
    >>> m6 = bug_three.newMessage(
    ...     owner=user, subject="Ho", content="Hello there"
    ... )
    >>> m7 = bug_three.newMessage(
    ...     owner=different_user, subject="Ho", content="Hello there"
    ... )
    >>> bug_three.messages.count()
    8

Now checking what gets displayed. m2 and m4 should be omitted, as they are
identical to the comment that precedes them in order; Although m7 is identical
to its preceding comment, it was made by a different user so it shouldn't be
hidden.

    >>> bug_three_bugtask = bug_three.bugtasks[0]
    >>> bug_view = getMultiAdapter(
    ...     (bug_three_bugtask, LaunchpadTestRequest()), name="+index"
    ... )
    >>> bug_view.initialize()
    >>> for c in bug_comments(bug_view):
    ...     print("%d: '%s', '%s'" % (c.index, c.title, c.text_for_display))
    ...
    1: 'Hi', 'Hello there'
    3: 'Ho', 'Hello there'
    5: 'Ho', 'Hello there'
    6: 'Ho', 'Hello there'
    7: 'Ho', 'Hello there'


Bugs with lots of comments
==========================

BugTaskView has another property for helping render bugs with lots of
comments: visible_comments_truncated_for_display.

This is normally false, but for bugs with lots of comments, the
visible_comments_truncated_for_display property becomes True and the activity
stream has the middle comments elided.

The configuration keys comments_list_max_length,
comments_list_truncate_oldest_to, and comments_list_truncate_newest_to
control the thresholds. If there are more comments than
comments_list_max_length, the list is truncated to show the oldest and
newest bugs, with a visual break in between.

    >>> from lp.services.config import config
    >>> config.push(
    ...     "malone",
    ...     """
    ... [malone]
    ... comments_list_max_length: 10
    ... comments_list_truncate_oldest_to: 3
    ... comments_list_truncate_newest_to: 5
    ... """,
    ... )

We'll create an example bug with 9 comments.

    >>> import itertools
    >>> from lp.bugs.interfaces.bugmessage import IBugMessageSet

    >>> comment_counter = itertools.count(1)
    >>> def add_comments(bug, how_many):
    ...     bug_message_set = getUtility(IBugMessageSet)
    ...     for i in range(how_many):
    ...         num = next(comment_counter)
    ...         bug_message_set.createMessage(
    ...             "Comment %d" % num,
    ...             bug,
    ...             bug.owner,
    ...             "Something or other #%d" % num,
    ...         )
    ...

    >>> bug = factory.makeBug()
    >>> add_comments(bug, 9)

If we create a view for this, we can see that truncation is disabled.

    >>> bug_view = getMultiAdapter(
    ...     (bug.default_bugtask, LaunchpadTestRequest()), name="+index"
    ... )
    >>> bug_view.initialize()
    >>> bug_view.visible_comments_truncated_for_display
    False

Add two more comments, and the list will be truncated to only 8 total.

    >>> add_comments(bug, 2)

    >>> bug_view = getMultiAdapter(
    ...     (bug.default_bugtask, LaunchpadTestRequest()), name="+index"
    ... )
    >>> bug_view.initialize()

    >>> bug_view.visible_comments_truncated_for_display
    True
    >>> bug_view.visible_initial_comments
    3
    >>> bug_view.visible_recent_comments
    5

The display of all comments can be requested with a form parameter.

    >>> request = LaunchpadTestRequest(form={"comments": "all"})
    >>> bug_view = getMultiAdapter(
    ...     (bug.default_bugtask, request), name="+index"
    ... )
    >>> bug_view.initialize()

    >>> bug_view.visible_comments_truncated_for_display
    False

Restore the configuration to its previous setting.

    >>> config.pop("malone")
    (...)


Wrapping up
===========

Be nice and restore the comment size to what it was originally.

    >>> config_data = config.pop("max_comment_size")


Displaying BugComments with activity
====================================

Comments are often made when a user makes a change to a bug, for example
setting the bug's status. The BugComment class has a property, activity,
which can hold a list of BugActivityItems associated with a comment (see
doc/bugactivity.rst for details of the BugActivityItem class).

    >>> from lp.bugs.browser.bugcomment import BugComment
    >>> from lp.bugs.browser.bugtask import BugActivityItem
    >>> from lp.bugs.interfaces.bugactivity import IBugActivitySet

    >>> user = factory.makePerson(displayname="Arthur Dent")
    >>> message = factory.makeMessage(content="Comment content", owner=user)
    >>> bug_task = factory.makeBugTask(owner=user)
    >>> activity = getUtility(IBugActivitySet).new(
    ...     bug=bug_task.bug,
    ...     whatchanged="malone: status",
    ...     oldvalue="New",
    ...     newvalue="Confirmed",
    ...     person=user,
    ...     datechanged=message.datecreated,
    ... )
    >>> activity_item = BugActivityItem(activity)

    >>> bug_comment = BugComment(
    ...     index=0,
    ...     message=message,
    ...     bugtask=bug_task,
    ...     activity=[activity_item],
    ... )

    >>> for activity in bug_comment.activity:
    ...     print(
    ...         "%s: %s" % (activity.change_summary, activity.change_details)
    ...     )
    ...
    status: New &#8594; Confirmed

The activity will be inserted into the footer of the comment. If a
BugComment has some activity associated with it, it's show_activity
property will be True.

    >>> bug_comment.show_activity
    True

    >>> bug_comment.activity = []
    >>> bug_comment.show_activity
    False

BugComment.show_activity will also be True if a BugWatch is associated
with the comment.

    >>> bug_comment.bugwatch = factory.makeBugWatch()
    >>> bug_comment.show_activity
    True


Comment attachments
===================

Attachments are provided in the properties BugComment.patches and
BugComment.attachments. The latter provides only those attachments
not included in BugComment.patches.

    >>> bug_task = factory.makeBugTask(owner=user)
    >>> bug = bug_task.bug
    >>> attachment_1 = bug.addAttachment(
    ...     owner=None,
    ...     data=BytesIO(b"whatever"),
    ...     comment=bug.initial_message,
    ...     filename="file1",
    ...     is_patch=False,
    ...     content_type="text/plain",
    ...     description="sample data 1",
    ... )
    >>> attachment_2 = bug.addAttachment(
    ...     owner=None,
    ...     data=BytesIO(b"whatever"),
    ...     comment=bug.initial_message,
    ...     filename="file2",
    ...     is_patch=False,
    ...     content_type="text/plain",
    ...     description="sample data 2",
    ... )
    >>> patch_1 = bug.addAttachment(
    ...     owner=None,
    ...     data=BytesIO(b"whatever"),
    ...     comment=bug.initial_message,
    ...     filename="patch1",
    ...     is_patch=True,
    ...     content_type="text/plain",
    ...     description="patch 1",
    ... )
    >>> patch_2 = bug.addAttachment(
    ...     owner=None,
    ...     data=BytesIO(b"whatever"),
    ...     comment=bug.initial_message,
    ...     filename="patch2",
    ...     is_patch=True,
    ...     content_type="text/plain",
    ...     description="patch 2",
    ... )
    >>> bug_view = getMultiAdapter(
    ...     (bug_task, LaunchpadTestRequest()), name="+index"
    ... )
    >>> bug_view.initialize()

    >>> bug_comment = bug_view.comments[0]
    >>> for attachment in bug_comment.bugattachments:
    ...     print(attachment.title, attachment.type.title)
    ...
    sample data 1 Unspecified
    sample data 2 Unspecified
    >>> for patch in bug_comment.patches:
    ...     print(patch.title, patch.type.title)
    ...
    patch 1 Patch
    patch 2 Patch
