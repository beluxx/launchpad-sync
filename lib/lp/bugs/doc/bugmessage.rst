Bug Messages
============

Bug messages are messages associated with bugs. A bug message is
described by the IBugMessage interface.

One IMessage can be associated with many IBugs, but one IBugMessage is
always associated with exactly one bug.

Retrieving bug messages
-----------------------

IBugMessageSet represents the set of all IBugMessages in the
system.

    >>> from lp.bugs.interfaces.bugmessage import IBugMessageSet
    >>> bugmessageset = getUtility(IBugMessageSet)

An individual IBugMessage can be retrieved with
IBugMessageSet.get:

    >>> bugmessage_four = bugmessageset.get(4)
    >>> print(bugmessage_four.message.subject)
    Fantastic idea, I'd really like to see this

You can get all the imported comments for a bug using
getImportedBugMessages. Imported comments are comments being linked to a
bug watch.

    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> bug_15 = getUtility(IBugSet).get(15)
    >>> bug_15.messages.count()
    7
    >>> for message in bug_15.messages:
    ...     bug_message = getUtility(IBugMessageSet).getByBugAndMessage(
    ...         bug_15, message)
    ...     print(bug_message.bugwatch)
    None
    <security proxied lp.bugs.model.bugwatch.BugWatch ...>
    ...

    >>> imported_comments = getUtility(IBugMessageSet).getImportedBugMessages(
    ...     bug_15)
    >>> imported_comments.count()
    6
    >>> for bug_message in imported_comments:
    ...     print(bug_message.bugwatch)
    <security proxied lp.bugs.model.bugwatch.BugWatch ...>
    ...


Creating bug messages
---------------------

To create a bug message, use IBugMessageSet.createMessage:

    >>> from lp.registry.interfaces.person import IPersonSet

    >>> sample_person = getUtility(IPersonSet).get(12)
    >>> bug_one = getUtility(IBugSet).get(1)
    >>> test_message = bugmessageset.createMessage(
    ...     subject="test message subject",
    ...     content="text message content",
    ...     owner=sample_person,
    ...     bug=bug_one)
    >>> print(test_message.message.subject)
    test message subject

The parent gets set to the initial message of the bug:

    >>> test_message.message.parent == bug_one.initial_message
    True

And the index of the bugmessage is set:

    >>> test_message.index
    2


Links and CVEs in bug messages
------------------------------

If a bug message contains links to an external bug report or a CVE,
bugwatches resp. CVE watches are automatically created. We add this
message as the bug_watch_updater since that Person will not be assigned
karma, which is not tested here, and since this test is run as the
checkwatches db user, which does not have permission to alter karma
scores.

    >>> bug_watch_updater = getUtility(IPersonSet).getByName(
    ...     'bug-watch-updater')
    >>> for cve in bug_one.cves:
    ...     print(cve.displayname)
    CVE-1999-8979
    >>> for bugwatch in bug_one.watches:
    ...     print(bugwatch.url)
    https://bugzilla.mozilla.org/show_bug.cgi?id=123543
    https://bugzilla.mozilla.org/show_bug.cgi?id=2000
    https://bugzilla.mozilla.org/show_bug.cgi?id=42
    http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=304014
    >>> test_message = bug_one.newMessage(
    ...     owner=bug_watch_updater,
    ...     subject="test message subject",
    ...     content="""This is a test comment. This bug is the same as the
    ...                one described here
    ...                http://some.bugzilla/show_bug.cgi?id=9876
    ...                See also CVE-1991-9911
    ...             """)
    >>> for cve in bug_one.cves:
    ...     print(cve.displayname)
    CVE-1991-9911
    CVE-1999-8979
    >>> for bugwatch in bug_one.watches:
    ...     print(bugwatch.url)
    https://bugzilla.mozilla.org/show_bug.cgi?id=123543
    https://bugzilla.mozilla.org/show_bug.cgi?id=2000
    https://bugzilla.mozilla.org/show_bug.cgi?id=42
    http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=304014
    http://some.bugzilla/show_bug.cgi?id=9876

Note that although the watch was created when the Message was added to
the bug, the message and the watch are not linked because the message
was not imported by the bug watch.

    >>> bug_message = bug_one.bug_messages.last()
    >>> print(bug_message.message == test_message)
    True
    >>> print(bug_message.bugwatch)
    None

CVE watches and bug watches are also created, when a message is imported from
an external bug tracker.

    >>> from lp.services.messages.interfaces.message import IMessageSet
    >>> message = getUtility(IMessageSet).fromText(
    ...    'subject',
    ...    """This is a comment from an external tracker. It has a link
    ...       to even another tracker
    ...        http://some.bugzilla/show_bug.cgi?id=1234 and mentions
    ...        CVE-1991-3333
    ...    """,
    ...    bug_watch_updater)
    >>> bugmsg = bug_one.linkMessage(message)
    >>> bugmsg
    <BugMessage at...
    >>> bugmsg.index
    4
    >>> for cve in bug_one.cves:
    ...     print(cve.displayname)
    CVE-1991-3333
    CVE-1991-9911
    CVE-1999-8979
    >>> for bugwatch in bug_one.watches:
    ...     print(bugwatch.url)
    https://bugzilla.mozilla.org/show_bug.cgi?id=123543
    https://bugzilla.mozilla.org/show_bug.cgi?id=2000
    https://bugzilla.mozilla.org/show_bug.cgi?id=42
    http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=304014
    http://some.bugzilla/show_bug.cgi?id=1234
    http://some.bugzilla/show_bug.cgi?id=9876


Last message date
-----------------

For each bug, we cache the date of the last message linked to it using
the attribute `date_last_message` in order to optimize searches the need
to compare this value for every bug in a large set.

    >>> test_message = bug_one.newMessage(
    ...     owner=bug_watch_updater,
    ...     subject="test message subject",
    ...     content="This is a test comment.")

    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> flush_database_caches()

    >>> bug_one.date_last_message == test_message.datecreated
    True


Retrieving IMessage.id from IBugMessage
---------------------------------------

Each IBugMessage has a message_id attribute, which allows access
to IBugMessage.IMessage.id without the additional query.

    >>> bugmessage_one = bugmessageset.get(1)
    >>> bugmessage_one.message_id == bugmessage_one.message.id
    True
