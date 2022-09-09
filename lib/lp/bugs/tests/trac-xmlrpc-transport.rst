TestTracXMLRPCTransport
=======================

TestTracXMLRPCTransport is an XML-RPC transport which simulates the LP
Trac plugin. It can be used to avoid network traffic while testing, and
it implements the same API that Trac instances having the LP plugin
installed implement.

    >>> import xmlrpc.client
    >>> from lp.bugs.tests.externalbugtracker import TestTracXMLRPCTransport
    >>> trac_transport = TestTracXMLRPCTransport("http://example.com/xmlrpc")
    >>> server = xmlrpc.client.ServerProxy(
    ...     "http://example.com/xmlrpc", transport=trac_transport
    ... )

All the methods need an authentication cookie to be sent.

    >>> server.launchpad.bugtracker_version()
    Traceback (most recent call last):
    ...
    xmlrpc.client.ProtocolError: <... 403 Forbidden>

This test transport doesn't validate the cookie, it just ensures that
some cookie is set.

    >>> trac_transport.setCookie("trac_auth=auth_cookie")


launchpad.bugtracker_version()
------------------------------

bugtracker_version() returns a list of
[Trac version, plugin version, dupe knowledge]. The version numbers are
returned as strings. `dupe_knowledge` indicates whether the Trac
instance knows how to track duplicate bugs.

    >>> server.launchpad.bugtracker_version()
    ['0.11.0', '1.0', False]


launchpad.time_snapshot()
-------------------------

time_snapshot returns information about what the Trac instance thinks
the current time is. It returns the local time zone, the local time, and
the UTC time. The times are returned as seconds since epoch.

    >>> print(*server.launchpad.time_snapshot())
    UTC ... ...

It's possible to set which values will be returned, if the current time
isn't suitable.

    >>> trac_transport.seconds_since_epoch = 1206328061
    >>> trac_transport.local_timezone = "US/Eastern"
    >>> trac_transport.utc_offset = -4 * 60 * 60

    >>> print(*server.launchpad.time_snapshot())
    US/Eastern 1206328061 1206342461


launchpad.bug_info()
--------------------

bug_info() returns, as the name suggests, info about a given bug or set
of bugs. It takes two parameters: level, an integer indicating how much
data to return, and criteria, which specifies criteria by which to
select the bugs to return.

We'll add some bugs to our trac transport to demonstrate this.

    >>> from datetime import datetime
    >>> from lp.bugs.tests.externalbugtracker import MockTracRemoteBug

    >>> remote_bugs = {
    ...     "1": MockTracRemoteBug(
    ...         id="1",
    ...         last_modified=datetime(2008, 4, 1, 0, 0, 0),
    ...         status="open",
    ...     ),
    ...     "2": MockTracRemoteBug(
    ...         id="2",
    ...         last_modified=datetime(2007, 1, 1, 1, 1, 1),
    ...         status="closed",
    ...     ),
    ...     "3": MockTracRemoteBug(
    ...         id="3",
    ...         last_modified=datetime(2008, 1, 1, 1, 2, 3),
    ...         status="fixed",
    ...     ),
    ... }

    >>> trac_transport.remote_bugs = remote_bugs

Specifying a level of 0 and no criteria will return the IDs of all the
bugs, along with a time snapshot as returned by time_snapshot().

    >>> time_snapshot, bugs = trac_transport.bug_info(level=0)
    >>> print(pretty(bugs))
    [{'id': '1'}, {'id': '2'}, {'id': '3'}]

Specifying a level of 1 will return each bug's metadata, not including
its last modified time.

    >>> def print_bugs(bug_list):
    ...     for bug in bug_list:
    ...         print("%(id)s: %(status)s." % bug)
    ...

    >>> time_snapshot, bugs = trac_transport.bug_info(level=1)
    >>> print_bugs(bugs)
    1: open.
    2: closed.
    3: fixed.

Specifying a level of 2 will return each bug's metadata and a list of
comment IDs for each bug.

We'll add some sample comments to demonstrate this.

    >>> import time
    >>> comment_datetime = datetime(2008, 4, 18, 16, 0, 0)
    >>> comment_timestamp = int(time.mktime(comment_datetime.timetuple()))

    >>> trac_transport.remote_bugs["1"].comments = [
    ...     {
    ...         "id": "1-1",
    ...         "type": "comment",
    ...         "user": "test@canonical.com",
    ...         "comment": "Hello, world!",
    ...         "timestamp": comment_timestamp,
    ...     }
    ... ]
    >>> trac_transport.remote_bugs["2"].comments = [
    ...     {
    ...         "id": "2-1",
    ...         "type": "comment",
    ...         "user": "test@canonical.com",
    ...         "comment": "Hello again, world!",
    ...         "timestamp": comment_timestamp,
    ...     },
    ...     {
    ...         "id": "2-2",
    ...         "type": "comment",
    ...         "user": "foo.bar@canonical.com",
    ...         "comment": "More commentary.",
    ...         "timestamp": comment_timestamp,
    ...     },
    ... ]

    >>> time_snapshot, bugs = trac_transport.bug_info(level=2)
    >>> for bug in bugs:
    ...     print("%s: %s" % (bug["id"], pretty(bug["comments"])))
    ...
    1: ['1-1']
    2: ['2-1', '2-2']
    3: []

We'll also define a helper function to print comments out.

    >>> def print_bug_comment(comment):
    ...     for key in sorted(comment.keys()):
    ...         print("%s: %s" % (key, comment[key]))
    ...     print("")
    ...

At level 3 the full list of comment dicts is returned along with the bug
metadata, but not including comment authors.

    >>> time_snapshot, bugs = trac_transport.bug_info(level=3)
    >>> for bug in bugs:
    ...     print("Comments for bug %s:" % bug["id"])
    ...     for comment in bug["comments"]:
    ...         print_bug_comment(comment)
    ...
    Comments for bug 1:
    comment: Hello, world!
    id: 1-1
    timestamp: 1208514600
    type: comment
    <BLANKLINE>
    Comments for bug 2:
    comment: Hello again, world!
    id: 2-1
    timestamp: 1208514600
    type: comment
    <BLANKLINE>
    comment: More commentary.
    id: 2-2
    timestamp: 1208514600
    type: comment
    <BLANKLINE>
    Comments for bug 3:

The criteria dict has two possible keys: modified_since and bugs.
Specifying a value for modified_since will cause only the bugs modified
since that time to be returned. modified_since is an integer timestamp,
so we'll convert a datetime into one for the purposes of this test.

    >>> import time
    >>> last_checked = datetime(2008, 1, 1, 0, 0, 0)
    >>> last_checked_timestamp = int(time.mktime(last_checked.timetuple()))

    >>> criteria = {"modified_since": last_checked_timestamp}
    >>> time_snapshot, bugs = trac_transport.bug_info(
    ...     level=0, criteria=criteria
    ... )

    >>> print(pretty(bugs))
    [{'id': '1'}, {'id': '3'}]

The bugs key in the criteria dict allows us to specify a list of bug IDs
to return.

    >>> criteria = {"bugs": ["1", "2"]}
    >>> time_snapshot, bugs = trac_transport.bug_info(
    ...     level=0, criteria=criteria
    ... )

    >>> print(pretty(bugs))
    [{'id': '1'}, {'id': '2'}]

If a bug doesn't exist, it will be returned with a status of
'missing'.

    >>> criteria = {"bugs": ["11", "12"]}
    >>> time_snapshot, bugs = trac_transport.bug_info(
    ...     level=0, criteria=criteria
    ... )

    >>> print(pretty(bugs))
    [{'id': '11', 'status': 'missing'}, {'id': '12', 'status': 'missing'}]

Combining the bugs and modified_since fields in the criteria dict will
result in only the bugs modified since the modified_since time whose IDs
are in the bugs list being returned.

    >>> criteria = {
    ...     "bugs": ["1", "2"],
    ...     "modified_since": last_checked_timestamp,
    ... }
    >>> time_snapshot, bugs = trac_transport.bug_info(
    ...     level=0, criteria=criteria
    ... )

    >>> print(pretty(bugs))
    [{'id': '1'}]


launchpad.get_comments()
------------------------

get_comments() returns a list of comment dicts. The comment dicts
returned correspond to the comment IDs passed in the comments parameter.

    >>> comments_to_retrieve = ["1-1", "2-1", "2-2"]
    >>> time_snapshot, comments = trac_transport.get_comments(
    ...     comments_to_retrieve
    ... )
    >>> for comment in comments:
    ...     print_bug_comment(comment)
    ...
    comment: Hello, world!
    id: 1-1
    timestamp: 1208514600
    type: comment
    user: test@canonical.com
    <BLANKLINE>
    comment: Hello again, world!
    id: 2-1
    timestamp: 1208514600
    type: comment
    user: test@canonical.com
    <BLANKLINE>
    comment: More commentary.
    id: 2-2
    timestamp: 1208514600
    type: comment
    user: foo.bar@canonical.com



launchpad.add_comment()
-----------------------

The Trac XML-RPC API allows us to push comments to remote bug trackers
via the launchpad.add_comment() method.

Remote bug 3 doesn't have any comments:

    >>> trac_transport.remote_bugs["3"].comments
    []

We can add one by using the add_comment() method. We'll force the UTC
value of the remote bugtracker for demonstration purposes.

    >>> trac_transport.seconds_since_epoch = 1209399273
    >>> trac_transport.local_timezone = "UTC"
    >>> trac_transport.utc_offset = 0
    >>> (time_snapshot, comment_id) = trac_transport.add_comment(
    ...     3, "This is a test comment being pushed."
    ... )

add_comment() will return a new comment ID.

    >>> print(comment_id)
    3-1

The comment will be included in the remote bug's comments.

    >>> for comment in trac_transport.remote_bugs["3"].comments:
    ...     for key in sorted(comment.keys()):
    ...         print("%s: %s" % (key, comment[key]))
    ...
    comment: This is a test comment being pushed.
    id: 3-1
    time: 1209399273
    type: comment
    user: launchpad


Getting and setting the Launchpad bug ID
----------------------------------------

The Trac XML-RPC API allows us to tell the remote tracker which
Launchpad bug links to a particular one of its bugs and also allows us
to retrieve that information from the remote tracker. We'll add a
Launchpad bug ID to our example Trac transport to demonstrate this.

    >>> trac_transport.launchpad_bugs["1"] = 42

The XML-RPC method `launchpad.get_launchpad_bug()` is used to retrieve
the Launchpad bug for a given remote bug.

    >>> timestamp, launchpad_bug = trac_transport.get_launchpad_bug("1")
    >>> print(launchpad_bug)
    42

If the remote bug isn't currently linked to by a Launchpad bug,
`launchpad.get_launchpad_bug()` will return 0 for the bug ID.

    >>> timestamp, launchpad_bug = trac_transport.get_launchpad_bug("2")
    >>> print(launchpad_bug)
    0

Calling `launchpad.get_launchpad_bug()` on a remote bug that doesn't
exist will result in a Fault being raised.

    >>> trac_transport.get_launchpad_bug("12345")
    Traceback (most recent call last):
      ...
    xmlrpc.client.Fault: <Fault 1001: 'Ticket does not exist'>

Setting the Launchpad bug for a remote bug is done by calling
`launchpad.set_launchpad_bug()`. This takes two parameters: the remote
bug ID and the ID of the Launchpad bug that links to it.

    >>> timestamp = trac_transport.set_launchpad_bug("2", 1)
    >>> timestamp, launchpad_bug = trac_transport.get_launchpad_bug("2")
    >>> print(launchpad_bug)
    1

Calling `launchpad.set_launchpad_bug()` will overwrite the existing
Launchpad bug ID stored for the given remote bug.

    >>> timestamp = trac_transport.set_launchpad_bug("2", 42)
    >>> timestamp, launchpad_bug = trac_transport.get_launchpad_bug("2")
    >>> print(launchpad_bug)
    42

Trying to call `launchpad.set_launchpad_bug()` on a remote bug that
doesn't exist will result in a Fault.

    >>> trac_transport.set_launchpad_bug("12345", 1)
    Traceback (most recent call last):
      ...
    xmlrpc.client.Fault: <Fault 1001: 'Ticket does not exist'>

