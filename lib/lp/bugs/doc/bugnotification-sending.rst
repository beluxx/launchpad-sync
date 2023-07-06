Sending the Bug Notifications
=============================

As explained in bugnotifications.rst, a change to a bug causes a bug
notification to be added. These notifications should be assembled into
an email notification, and sent to the appropriate people.

Before we start, let's ensure that there are no pending notifications to
be sent:

    >>> from datetime import datetime, timedelta, timezone
    >>> now = datetime.now(timezone.utc)
    >>> ten_minutes_ago = now - timedelta(minutes=10)
    >>> from lp.bugs.interfaces.bugnotification import IBugNotificationSet
    >>> len(getUtility(IBugNotificationSet).getNotificationsToSend())
    0

And let's define functions to make printing out the notifications
easier.

    >>> def print_notification_headers(email_notification, extra_headers=[]):
    ...     for header in [
    ...         "To",
    ...         "From",
    ...         "Subject",
    ...         "X-Launchpad-Message-Rationale",
    ...         "X-Launchpad-Message-For",
    ...         "X-Launchpad-Subscription",
    ...     ] + extra_headers:
    ...         if email_notification[header]:
    ...             print("%s: %s" % (header, email_notification[header]))
    ...

    >>> def print_notification(email_notification, extra_headers=[]):
    ...     print_notification_headers(
    ...         email_notification, extra_headers=extra_headers
    ...     )
    ...     print()
    ...     print(email_notification.get_payload(decode=True).decode())
    ...     print("-" * 70)
    ...

We'll also import a helper function to help us with database users.

    >>> from lp.testing.dbuser import lp_dbuser

You'll note that we are printing out an X-Launchpad-Message-Rationale
header. This header is a simple string that allows people to filter
bugmail according to the reason they are getting emailed. For instance,
the person may want to specially filter mail for bugs which they are
assigned to.

Anyway, let's start our demonstration by adding a comment to a bug:

    >>> login("test@canonical.com")
    >>> from lp.services.messages.interfaces.message import IMessageSet
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> bug_one = getUtility(IBugSet).get(1)
    >>> sample_person = getUtility(ILaunchBag).user
    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "a comment.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> bug_one.addCommentNotification(comment)

    >>> notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(notifications)
    1

If we pass these notifications to get_email_notifications, we get a
list of emails to send:

    >>> from lp.bugs.scripts.bugnotification import get_email_notifications
    >>> email_notifications = get_email_notifications(notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: foo.bar@canonical.com
    From: Sample Person <1@bugs.launchpad.net>
    Subject: [Bug 1] subject
    X-Launchpad-Message-Rationale: Subscriber (mozilla-firefox in Ubuntu)
    X-Launchpad-Message-For: name16
    <BLANKLINE>
    a comment.
    <BLANKLINE>
    ...
    ----------------------------------------------------------------------
    To: mark@example.com
    From: Sample Person <1@bugs.launchpad.net>
    Subject: [Bug 1] subject
    X-Launchpad-Message-Rationale: Assignee
    X-Launchpad-Message-For: mark
    <BLANKLINE>
    a comment.
    <BLANKLINE>
    ...
    ----------------------------------------------------------------------
    To: test@canonical.com
    From: Sample Person <1@bugs.launchpad.net>
    Subject: [Bug 1] subject
    X-Launchpad-Message-Rationale: Subscriber
    X-Launchpad-Message-For: name12
    <BLANKLINE>
    a comment.
    <BLANKLINE>
    ...
    ----------------------------------------------------------------------

You can see that the message above contains the bug's initial comment's
message id as its reference, in order to make it thread properly in the
email client.

    >>> print(bug_one.initial_message.rfc822msgid)
    sdsdfsfd

The notification is still pending to be sent, since date_emailed is
still None:

    >>> notifications[0].date_emailed is None
    True
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> list(pending_notifications) == list(notifications)
    True

Setting date_emailed to some date causes it not to be pending anymore:

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> notifications[0].date_emailed = datetime.now(timezone.utc)
    >>> flush_database_updates()
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(pending_notifications)
    0

Let's define a helper function to do that for all pending notifications:

    >>> def flush_notifications():
    ...     utc_now = datetime.now(timezone.utc)
    ...     pending_notifications = getUtility(
    ...         IBugNotificationSet
    ...     ).getNotificationsToSend()
    ...     for notification in pending_notifications:
    ...         notification.date_emailed = utc_now
    ...     flush_database_updates()
    ...

To every message that gets sent out, [Bug $bugid] is prefixed to the
subject. It gets prefixed only if it's not already present in the
subject, though, which is often the case when someone replies via email.

    >>> comment = getUtility(IMessageSet).fromText(
    ...     "Re: [Bug 1] subject",
    ...     "a new comment.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> bug_one.addCommentNotification(comment)
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> email_notifications = get_email_notifications(pending_notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: foo.bar@canonical.com
    ...
    To: mark@example.com
    From: Sample Person <1@bugs.launchpad.net>
    Subject: Re: [Bug 1] subject
    X-Launchpad-Message-Rationale: Assignee
    X-Launchpad-Message-For: mark
    <BLANKLINE>
    a new comment.
    <BLANKLINE>
    ...
    ----------------------------------------------------------------------
    To: test@canonical.com
    ...

    >>> flush_notifications()

Let's add a few changes and see how it looks like:

    >>> from lp.bugs.adapters.bugchange import (
    ...     BugTitleChange,
    ...     BugInformationTypeChange,
    ... )
    >>> from lp.app.enums import InformationType

    >>> bug_one.addChange(
    ...     BugTitleChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "title",
    ...         "Old summary",
    ...         "New summary",
    ...     )
    ... )
    >>> bug_one.addChange(
    ...     BugInformationTypeChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "information_type",
    ...         InformationType.PUBLIC,
    ...         InformationType.USERDATA,
    ...     )
    ... )
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(pending_notifications)
    2

    >>> email_notifications = get_email_notifications(pending_notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: foo.bar@canonical.com
    ...
    To: mark@example.com
    From: Sample Person <1@bugs.launchpad.net>
    Subject: [Bug 1] Re: Firefox does not support SVG
    X-Launchpad-Message-Rationale: Assignee
    X-Launchpad-Message-For: mark
    <BLANKLINE>
    ** Summary changed:
    - Old summary
    + New summary
    <BLANKLINE>
    ** Information type changed from Public to Private
    <BLANKLINE>
    --
    ...
    ----------------------------------------------------------------------
    To: test@canonical.com
    ...

If we insert a comment and some more changes, they will be included in
the constructed email:

    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "a new comment.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> bug_one.addCommentNotification(comment)
    >>> bug_one.addChange(
    ...     BugTitleChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "title",
    ...         "New summary",
    ...         "Another summary",
    ...     )
    ... )
    >>> bug_one.addChange(
    ...     BugInformationTypeChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "information_type",
    ...         InformationType.USERDATA,
    ...         InformationType.PUBLIC,
    ...     )
    ... )
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(pending_notifications)
    5

Notice how the comment is in the top of the email, and the changes are
in the order they were added:

    >>> email_notifications = get_email_notifications(pending_notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: foo.bar@canonical.com
    ...
    To: mark@example.com
    From: Sample Person <1@bugs.launchpad.net>
    Subject: [Bug 1] Re: Firefox does not support SVG
    X-Launchpad-Message-Rationale: Assignee
    X-Launchpad-Message-For: mark
    <BLANKLINE>
    a new comment.
    <BLANKLINE>
    ** Summary changed:
    - Old summary
    + New summary
    <BLANKLINE>
    ** Summary changed:
    - New summary
    + Another summary
    <BLANKLINE>
    --
    ...
    ----------------------------------------------------------------------
    To: test@canonical.com
    ...

If you look carefully, there's a surprise in that output: the visibility
changes are not reported.  This is because they are done and then undone
within the same notification.  Undone changes like that are omitted.
moreover, if the email only would have reported done/undone changes, it
is not sent at all.  This is tested elsewhere (see
lp/bugs/tests/test_bugnotification.py), and not demonstrated here.

Another thing worth noting is that there's a blank line before the
signature, and the signature marker has a trailing space.

    >>> message.get_payload(decode=True).decode().splitlines()  # noqa
    [...,
     '',
     '-- ',
     'You received this bug notification because you are subscribed to the bug',
     'report.',
     'http://bugs.launchpad.test/bugs/1',
     '',
     'Title:',
     '  Firefox does not support SVG'...]

    >>> flush_notifications()

We send the notification only if the user hasn't done any other changes
for the last 5 minutes:

    >>> now = datetime.now(timezone.utc)
    >>> for minutes_ago in reversed(range(10)):
    ...     bug_one.addChange(
    ...         BugInformationTypeChange(
    ...             now - timedelta(minutes=minutes_ago),
    ...             sample_person,
    ...             "information_type",
    ...             InformationType.PUBLIC,
    ...             InformationType.USERDATA,
    ...         )
    ...     )
    ...
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(pending_notifications)
    0

    >>> flush_notifications()

If a team without a contact address is subscribed to the bug, the
notification will be sent to all members individually.

    >>> with lp_dbuser():
    ...     owner = factory.makePerson(email="owner@example.com")
    ...     addressless = factory.makeTeam(
    ...         owner=owner,
    ...         name="addressless",
    ...         displayname="Addressless Team",
    ...     )
    ...
    >>> addressless.preferredemail is None
    True
    >>> for member in addressless.activemembers:
    ...     print(member.preferredemail.email)
    ...
    owner@example.com

    >>> with lp_dbuser():
    ...     ignored = bug_one.subscribe(addressless, addressless)
    ...     comment = getUtility(IMessageSet).fromText(
    ...         "subject",
    ...         "a comment.",
    ...         sample_person,
    ...         datecreated=ten_minutes_ago,
    ...     )
    ...     bug_one.addCommentNotification(comment)
    ...

    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(pending_notifications)
    1

    >>> email_notifications = get_email_notifications(pending_notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print(message["To"])
    ...
    foo.bar@canonical.com
    mark@example.com
    owner@example.com
    test@canonical.com

    >>> flush_notifications()

Duplicates
----------

We will need a fresh new bug.

    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> description = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "a description of the bug.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> params = CreateBugParams(
    ...     msg=description, owner=sample_person, title="new bug"
    ... )

    >>> with lp_dbuser():
    ...     new_bug = ubuntu.createBug(params)
    ...

No duplicate information is included.

    >>> notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(notifications)
    1

    >>> for bug_notifications, omitted, messages in get_email_notifications(
    ...     notifications
    ... ):
    ...     for message in messages:
    ...         print_notification(
    ...             message, extra_headers=["X-Launchpad-Bug-Duplicate"]
    ...         )
    To: test@canonical.com
    From: Sample Person <...@bugs.launchpad.net>
    Subject: [Bug ...] [NEW] new bug
    X-Launchpad-Message-Rationale: Subscriber
    X-Launchpad-Message-For: name12
    <BLANKLINE>
    Public bug reported:
    ...
    ----------------------------------------------------------------------

    >>> flush_notifications()

If a bug is a duplicate of another bug, a marker gets inserted at the
top of the email:

    >>> with lp_dbuser():
    ...     new_bug.markAsDuplicate(bug_one)
    ...
    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "a comment.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> new_bug.addCommentNotification(comment)
    >>> notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(notifications)
    1

    >>> for bug_notifications, omitted, messages in get_email_notifications(
    ...     notifications
    ... ):
    ...     for message in messages:
    ...         print_notification(
    ...             message, extra_headers=["X-Launchpad-Bug-Duplicate"]
    ...         )
    To: test@canonical.com
    From: Sample Person <...@bugs.launchpad.net>
    Subject: [Bug ...] subject
    X-Launchpad-Message-Rationale: Subscriber
    X-Launchpad-Message-For: name12
    X-Launchpad-Bug-Duplicate: 1
    <BLANKLINE>
    *** This bug is a duplicate of bug 1 ***
        http://bugs.launchpad.test/bugs/1
    ...
    ----------------------------------------------------------------------

    >>> flush_notifications()


Security Vulnerabilities
------------------------

When a new security related bug is filed, a small notification is
inserted at the top of the message body.

    >>> sec_vuln_description = getUtility(IMessageSet).fromText(
    ...     "Zero-day on Frobulator",
    ...     "Woah.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )

    >>> with lp_dbuser():
    ...     sec_vuln_bug = ubuntu.createBug(
    ...         CreateBugParams(
    ...             msg=sec_vuln_description,
    ...             owner=sample_person,
    ...             title="Zero-day on Frobulator",
    ...             information_type=InformationType.PRIVATESECURITY,
    ...         )
    ...     )
    ...

    >>> notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> email_notifications = get_email_notifications(notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: test@canonical.com
    From: Sample Person <...@bugs.launchpad.net>
    Subject: [Bug ...] [NEW] Zero-day on Frobulator
    X-Launchpad-Message-Rationale: Subscriber
    X-Launchpad-Message-For: name12
    <BLANKLINE>
    *** This bug is a security vulnerability ***
    <BLANKLINE>
    ...

    >>> flush_notifications()

The message is only inserted for new bugs, not for modified bugs:

    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "a comment.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> sec_vuln_bug.addCommentNotification(comment)

    >>> notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> email_notifications = get_email_notifications(notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: test@canonical.com
    From: Sample Person <...@bugs.launchpad.net>
    Subject: [Bug ...] subject
    X-Launchpad-Message-Rationale: Subscriber
    X-Launchpad-Message-For: name12
    <BLANKLINE>
    a comment.
    <BLANKLINE>
    ...

    >>> flush_notifications()


The cronscript
--------------

There's a cronsript which does the sending of the email. Let's add a
few notifications to show that it works.

    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "a comment.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> bug_one.addCommentNotification(comment)
    >>> bug_one.addChange(
    ...     BugTitleChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "title",
    ...         "Another summary",
    ...         "New summary",
    ...     )
    ... )
    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "another comment.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> bug_one.addCommentNotification(comment)
    >>> bug_one.addChange(
    ...     BugTitleChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "title",
    ...         "Summary #431",
    ...         "Summary bleugh I'm going mad",
    ...     )
    ... )

    >>> bug_two = getUtility(IBugSet).get(2)
    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "a comment.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> bug_two.addCommentNotification(comment)
    >>> bug_two.addChange(
    ...     BugTitleChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "title",
    ...         "Old summary",
    ...         "New summary",
    ...     )
    ... )
    >>> bug_two.addChange(
    ...     BugInformationTypeChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "information_type",
    ...         InformationType.PUBLIC,
    ...         InformationType.USERDATA,
    ...     )
    ... )
    >>> bug_two.addChange(
    ...     BugInformationTypeChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "information_type",
    ...         InformationType.USERDATA,
    ...         InformationType.PUBLIC,
    ...     )
    ... )

    >>> notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(notifications)
    8

We need to commit the transaction so that the cronscript will see the
notifications.

    >>> import transaction
    >>> transaction.commit()

Now, let's run the cronscript and look at the output. Passing -v to it
makes it write out the emails it sends.

    >>> import subprocess
    >>> process = subprocess.Popen(
    ...     ["cronscripts/send-bug-notifications.py", "-v"],
    ...     stdin=subprocess.PIPE,
    ...     stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE,
    ...     universal_newlines=True,
    ... )
    >>> (out, err) = process.communicate()
    >>> process.returncode
    0
    >>> print(err)
    INFO    ...
    INFO    Notifying test@canonical.com about bug 2.
    ...
    From: Sample Person <...@bugs.launchpad.net>
    To: test@canonical.com
    Reply-To: Bug 2 <2@bugs.launchpad.net>
    ...
    References: foo@example.com-332342--1231
    ...
    X-Launchpad-Message-Rationale: Assignee
    X-Launchpad-Message-For: name12
    ...
    INFO    Notifying foo.bar@canonical.com about bug 1.
    ...
    From: Sample Person <...@bugs.launchpad.net>
    To: foo.bar@canonical.com
    Reply-To: Bug 1 <1@bugs.launchpad.net>
    ...
    References: sdsdfsfd
    ...
    X-Launchpad-Message-Rationale: Subscriber (mozilla-firefox in Ubuntu)
    X-Launchpad-Message-For: name16
    ...
    INFO    Notifying mark@example.com about bug 1.
    ...
    INFO    Notifying owner@example.com about bug 1.
    ...
    INFO    Notifying test@canonical.com about bug 1.
    ...
    INFO    Notifying foo.bar@canonical.com about bug 1.
    ...
    From: Sample Person <...@bugs.launchpad.net>
    To: foo.bar@canonical.com
    Reply-To: Bug 1 <1@bugs.launchpad.net>
    ...
    References: sdsdfsfd
    ...
    X-Launchpad-Message-Rationale: Subscriber (mozilla-firefox in Ubuntu)
    X-Launchpad-Message-For: name16
    Errors-To: bounces@canonical.com
    Return-Path: bounces@canonical.com
    Precedence: bulk
    ...
    <BLANKLINE>
    another comment.
    <BLANKLINE>
    ** Summary changed:
    <BLANKLINE>
    - Summary #431
    + Summary bleugh I'm going mad
    <BLANKLINE>
    --...
    You received this bug notification because...
    INFO    Notifying mark@example.com about bug 1.
    ...
    INFO    Notifying owner@example.com about bug 1.
    ...
    INFO    Notifying test@canonical.com about bug 1.
    ...

Note that the message omitted the undone information type change.

The cronscript has to be sure to mark all notifications, omitted and
otherwise, as sent.  It also marks the omitted notifications with a status,
so if there are any problems we can identify which notifications were omitted
during analysis.  We'll commit a transaction to synchronize the database,
and then look at the notifications available.

    >>> transaction.commit()

    >>> notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(notifications)
    0

They have all been marked as sent, including the omitted ones.  Let's look
more carefully at the notifications just to see that the status has
been set properly.

    >>> from lp.bugs.model.bugnotification import BugNotification
    >>> from lp.services.database.interfaces import IStore
    >>> for notification in list(
    ...     IStore(BugNotification)
    ...     .find(BugNotification)
    ...     .order_by(BugNotification.id)
    ... )[-8:]:
    ...     if notification.is_comment:
    ...         identifier = "comment"
    ...     else:
    ...         identifier = notification.activity.whatchanged
    ...     print(identifier, notification.status.title)
    comment Sent
    summary Sent
    comment Sent
    summary Sent
    comment Sent
    summary Sent
    information type Omitted
    information type Omitted


The X-Launchpad-Bug header
--------------------------

When a notification is sent out about a bug, the X-Launchpad-Bug header is
filled with data about that bug:

    >>> with lp_dbuser():
    ...     bug_three = getUtility(IBugSet).get(3)
    ...     subscription = bug_three.subscribe(sample_person, sample_person)
    ...

    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "a short comment.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> bug_three.addCommentNotification(comment)
    >>> notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(notifications)
    1

If we take a closer look at a notification, we can see that
X-Launchpad-Bug headers were added:

    >>> email_notifications = get_email_notifications(notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         for line in sorted(message.get_all("X-Launchpad-Bug")):
    ...             print(line)
    ...
    distribution=debian; distroseries=sarge;... milestone=3.1;...
    distribution=debian; distroseries=woody;...
    distribution=debian; sourcepackage=mozilla-firefox; component=...

The milestone field in X-Launchpad-Bug won't be filled where no milestone is
specified:

    >>> for line in sorted(message.get_all("X-Launchpad-Bug")):
    ...     "milestone" in line
    ...
    True
    False
    False


The X-Launchpad-Bug-Tags header
-------------------------------

First, a helper function that triggers notifications by adding a
comment to a given bug, another that returns a sorted list of new
email messages, and a third that combines the first two.

    >>> def trigger_notifications(bug):
    ...     comment = getUtility(IMessageSet).fromText(
    ...         "subject",
    ...         "a short comment.",
    ...         sample_person,
    ...         datecreated=ten_minutes_ago,
    ...     )
    ...     bug.addCommentNotification(comment)
    ...     return getUtility(IBugNotificationSet).getNotificationsToSend()
    ...

    >>> def get_email_messages(notifications):
    ...     messages = (
    ...         message
    ...         for bug_notifications, omitted, messages in get_email_notifications(  # noqa
    ...             notifications
    ...         )
    ...         for message in messages
    ...     )
    ...     return sorted(messages, key=lambda message: message["To"])
    ...

    >>> def trigger_and_get_email_messages(bug):
    ...     flush_notifications()
    ...     notifications = trigger_notifications(bug)
    ...     return get_email_messages(notifications)
    ...

If a bug is tagged, those tags will be included in the message in the
X-Launchpad-Bug-Tags header.

    >>> for tag in bug_three.tags:
    ...     print(tag)
    ...
    layout-test

    >>> for message in trigger_and_get_email_messages(bug_three):
    ...     for line in message.get_all("X-Launchpad-Bug-Tags"):
    ...         print(line)
    ...
    layout-test

If we add a tag to bug three that will also be included in the header.
The tags will be space-separated to allow the list to be wrapped if it
gets over-long.

    >>> with lp_dbuser():
    ...     bug_three.tags = ["layout-test", "another-tag", "yet-another"]
    ...

    >>> bug_three = getUtility(IBugSet).get(3)
    >>> for message in trigger_and_get_email_messages(bug_three):
    ...     for line in message.get_all("X-Launchpad-Bug-Tags"):
    ...         print(line)
    ...
    another-tag layout-test yet-another

If we remove the tags from the bug, the X-Launchpad-Bug-Tags header
won't be included.

    >>> with lp_dbuser():
    ...     bug_three.tags = []
    ...

    >>> bug_three = getUtility(IBugSet).get(3)
    >>> for message in trigger_and_get_email_messages(bug_three):
    ...     message.get_all("X-Launchpad-Bug-Tags")
    ...


The X-Launchpad-Bug-Information-Type header
-------------------------------------------

When a notification is sent out about a bug, the
X-Launchpad-Bug-Information-Type header shows the information type value
assigned to the bug. For backwards compatibility, the X-Launchpad-Bug-Private
and X-Launchpad-Bug-Security-Vulnerability headers are also set. These headers
can have the value "yes" or "no".

    >>> print(bug_three.information_type.title)
    Public

    >>> def print_message_header_details(message):
    ...     print(
    ...         "%s %s %s %s"
    ...         % (
    ...             message["To"],
    ...             message.get_all("X-Launchpad-Bug-Private"),
    ...             message.get_all("X-Launchpad-Bug-Security-Vulnerability"),
    ...             message.get_all("X-Launchpad-Bug-Information-Type"),
    ...         )
    ...     )
    ...

    >>> for message in trigger_and_get_email_messages(bug_three):
    ...     print_message_header_details(message)
    ...
    test@canonical.com ['no'] ['no'] ['Public']

Predictably, private bugs are sent with a slightly different header:

    >>> with lp_dbuser():
    ...     bug_three.transitionToInformationType(
    ...         InformationType.USERDATA, sample_person
    ...     )
    ...
    True
    >>> print(bug_three.information_type.title)
    Private

    >>> for message in trigger_and_get_email_messages(bug_three):
    ...     print_message_header_details(message)
    ...
    test@canonical.com ['yes'] ['no']  ['Private']

Now transition the bug to private security:

    >>> with lp_dbuser():
    ...     bug_three.transitionToInformationType(
    ...         InformationType.PRIVATESECURITY, getUtility(ILaunchBag).user
    ...     )
    ...
    True
    >>> print(bug_three.information_type.title)
    Private Security

    >>> for message in trigger_and_get_email_messages(bug_three):
    ...     print_message_header_details(message)
    ...
    test@canonical.com ['yes'] ['yes']  ['Private Security']


The X-Launchpad-Bug-Commenters header
-------------------------------------

The X-Launchpad-Bug-Recipient-Commented header lists all user IDs of
people who have ever commented on the bug. It's a space-separated
list.

    >>> message = trigger_and_get_email_messages(bug_three)[0]
    >>> print(message.get("X-Launchpad-Bug-Commenters"))
    name12

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> foo_bar = getUtility(IPersonSet).getByEmail("foo.bar@canonical.com")

    >>> from lp.bugs.interfaces.bugmessage import IBugMessageSet
    >>> with lp_dbuser():
    ...     ignored = getUtility(IBugMessageSet).createMessage(
    ...         "Hungry", bug_three, foo_bar, "Make me a sandwich."
    ...     )
    ...

    >>> message = trigger_and_get_email_messages(bug_three)[0]
    >>> print(message.get("X-Launchpad-Bug-Commenters"))
    name12 name16

It only lists each user once, no matter how many comments they've
made.

    >>> with lp_dbuser():
    ...     ignored = getUtility(IBugMessageSet).createMessage(
    ...         "Hungry", bug_three, foo_bar, "Make me a sandwich."
    ...     )
    ...

    >>> message = trigger_and_get_email_messages(bug_three)[0]
    >>> print(message.get("X-Launchpad-Bug-Commenters"))
    name12 name16


The X-Launchpad-Bug-Reporter header
-----------------------------------

The X-Launchpad-Bug-Reporter header contains information about the Launchpad
user who originally reported the bug and opened the bug's first bug task.

    >>> message = trigger_and_get_email_messages(bug_three)[0]
    >>> print(message.get("X-Launchpad-Bug-Reporter"))
    Foo Bar (name16)


Verbose bug notifications
-------------------------

It is possible for users to have all the bug notifications which they
receive include the bug description and status. This helps in those
cases where the user doesn't save bug notifications, which can make
subsequent notifications seem somewhat obscure.

To demonstrate verbose notifications, we'll create a bug, and subscribe
some very picky users to it. Verbose Person wants verbose emails, while
Concise Person does not. We'll also create teams and give them members
with different verbose_bugnotifications settings.

    >>> with lp_dbuser():
    ...     bug = factory.makeBug(
    ...         target=factory.makeProduct(displayname="Foo"),
    ...         title="In the beginning, the universe was created. This "
    ...         "has made a lot of people very angry and has been "
    ...         "widely regarded as a bad move",
    ...         description="This is a long description of the bug, which "
    ...         "will be automatically wrapped by the BugNotification "
    ...         "machinery. Ain't technology great?",
    ...     )
    ...     verbose_person = factory.makePerson(
    ...         name="verbose-person",
    ...         displayname="Verbose Person",
    ...         email="verbose@example.com",
    ...         selfgenerated_bugnotifications=True,
    ...     )
    ...     verbose_person.verbose_bugnotifications = True
    ...     ignored = bug.subscribe(verbose_person, verbose_person)
    ...     concise_person = factory.makePerson(
    ...         name="concise-person",
    ...         displayname="Concise Person",
    ...         email="concise@example.com",
    ...     )
    ...     concise_person.verbose_bugnotifications = False
    ...     ignored = bug.subscribe(concise_person, concise_person)
    ...


Concise Team doesn't want verbose notifications, while Concise Team
Person, a member, does.

    >>> with lp_dbuser():
    ...     concise_team = factory.makeTeam(
    ...         name="conciseteam", displayname="Concise Team"
    ...     )
    ...     concise_team.verbose_bugnotifications = False
    ...     concise_team_person = factory.makePerson(
    ...         name="conciseteam-person",
    ...         displayname="Concise Team Person",
    ...         email="conciseteam@example.com",
    ...     )
    ...     concise_team_person.verbose_bugnotifications = True
    ...     ignored = concise_team.addMember(
    ...         concise_team_person, concise_team_person
    ...     )
    ...     ignored = bug.subscribe(concise_team, concise_team_person)
    ...

Verbose Team wants verbose notifications, while Verbose Team Person, a
member, does not.

    >>> with lp_dbuser():
    ...     verbose_team = factory.makeTeam(
    ...         name="verboseteam", displayname="Verbose Team"
    ...     )
    ...     verbose_team.verbose_bugnotifications = True
    ...     verbose_team_person = factory.makePerson(
    ...         name="verboseteam-person",
    ...         displayname="Verbose Team Person",
    ...         email="verboseteam@example.com",
    ...     )
    ...     verbose_team_person.verbose_bugnotifications = False
    ...     ignored = verbose_team.addMember(
    ...         verbose_team_person, verbose_team_person
    ...     )
    ...     ignored = bug.subscribe(verbose_team, verbose_team_person)
    ...

We'll expire all existing notifications since we're not interested in
them:

    >>> notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(notifications)
    1

    >>> for notification in notifications:
    ...     notification.date_emailed = datetime.now(timezone.utc)
    ...


If we then add a comment to the bug, the subscribers will receive
notifications containing that comment.

    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "a really simple comment.",
    ...     verbose_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> bug.addCommentNotification(comment)

    >>> notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> len(notifications)
    1

If we pass this notification to get_email_notifications we can see that
Verbose Person and Team Person will receive notifications which contain
the bug description and the status in all of its targets. All other
subscribers will receive standard notifications that don't include the
bug description. To help with demonstrating this, we'll define a helper
function.

    >>> def collate_messages_by_recipient(messages):
    ...     messages_by_recipient = {}
    ...     for message in messages:
    ...         recipient = message["To"]
    ...         if recipient in messages_by_recipient:
    ...             messages_by_recipient[recipient].append(message)
    ...         else:
    ...             messages_by_recipient[recipient] = [message]
    ...     return messages_by_recipient
    ...

    >>> from itertools import chain
    >>> collated_messages = collate_messages_by_recipient(
    ...     chain(
    ...         *(
    ...             messages
    ...             for bug_notifications, omitted, messages in get_email_notifications(  # noqa
    ...                 notifications
    ...             )
    ...         )
    ...     )
    ... )

We can see that Concise Person doesn't receive verbose notifications:

    >>> print_notification(collated_messages["concise@example.com"][0])
    To: concise@example.com
    From: Verbose Person <...@bugs.launchpad.net>
    Subject: [Bug ...] subject
    X-Launchpad-Message-Rationale: Subscriber
    X-Launchpad-Message-For: concise-person
    <BLANKLINE>
    a really simple comment.
    <BLANKLINE>
    --
    You received this bug notification because you are subscribed to the bug
    report.
    http://bugs.launchpad.test/bugs/...
    <BLANKLINE>
    Title:
      In the beginning...
    ----------------------------------------------------------------------

However, Concise Person does get an unsubscribe link.

    >>> print_notification(collated_messages["concise@example.com"][0])
    To: concise@example.com
    ...
    To manage notifications about this bug go to:...

Verbose Team Person gets a concise email, even though they belong to a team
that gets verbose email.

    >>> print_notification(collated_messages["verboseteam@example.com"][0])
    To: verboseteam@example.com
    From: Verbose Person <...@bugs.launchpad.net>
    Subject: [Bug ...] subject
    X-Launchpad-Message-Rationale: Subscriber @verboseteam
    X-Launchpad-Message-For: verboseteam
    <BLANKLINE>
    a really simple comment.
    <BLANKLINE>
    --
    You received this bug notification because you are a member of Verbose
    Team, which is subscribed to the bug report.
    http://bugs.launchpad.test/bugs/...
    <BLANKLINE>
    Title:
      In the beginning...
    ----------------------------------------------------------------------

Whereas Verbose Person does get the description and task status:

    >>> print_notification(collated_messages["verbose@example.com"][0])
    To: verbose@example.com
    From: Verbose Person <...@bugs.launchpad.net>
    Subject: [Bug ...] subject
    X-Launchpad-Message-Rationale: Subscriber
    X-Launchpad-Message-For: verbose-person
    <BLANKLINE>
    a really simple comment.
    <BLANKLINE>
    --
    You received this bug notification because you are subscribed to the bug
    report.
    http://bugs.launchpad.test/bugs/...
    <BLANKLINE>
    Title:
      In the beginning...
    <BLANKLINE>
    Status in Foo:
      New
    <BLANKLINE>
    Bug description:
       This is a long description of the bug, which
       will be automatically wrapped by the BugNotification
       machinery. Ain't technology great?
    <BLANKLINE>
    To manage notifications about this bug go to:
    http://bugs.launchpad.test/.../+bug/.../+subscriptions
    ----------------------------------------------------------------------

And Concise Team Person does too, even though their team doesn't want them:

    >>> print_notification(collated_messages["conciseteam@example.com"][0])
    To: conciseteam@example.com
    From: Verbose Person <...@bugs.launchpad.net>
    Subject: [Bug ...] subject
    X-Launchpad-Message-Rationale: Subscriber @conciseteam
    X-Launchpad-Message-For: conciseteam
    <BLANKLINE>
    a really simple comment.
    <BLANKLINE>
    --
    You received this bug notification because you are a member of Concise
    Team, which is subscribed to the bug report.
    http://bugs.launchpad.test/bugs/...
    <BLANKLINE>
    Title:
      In the beginning...
    <BLANKLINE>
    Status in Foo:
      New
    <BLANKLINE>
    Bug description:
       This is a long description of the bug, which
       will be automatically wrapped by the BugNotification
       machinery. Ain't technology great?
    <BLANKLINE>
    To manage notifications about this bug go to:
    http://bugs.launchpad.test/.../+bug/.../+subscriptions
    ----------------------------------------------------------------------

It's important to note that the bug title and description are wrapped
and indented correctly in verbose notifications.

    >>> message = collated_messages["conciseteam@example.com"][0]
    >>> payload = message.get_payload(decode=True).decode()
    >>> print(payload.splitlines())
    [...
     'Title:',
     '  In the beginning, the universe was created. This has made a lot of',
     '  people very angry and has been widely regarded as a bad move',
     ...
     'Bug description:',
     '  This is a long description of the bug, which will be automatically',
     "  wrapped by the BugNotification machinery. Ain't technology great?"...]

The title is also wrapped and indented in normal notifications.

    >>> message = collated_messages["verboseteam@example.com"][0]
    >>> payload = message.get_payload(decode=True).decode()
    >>> print(payload.strip().splitlines())
    [...
     'Title:',
     '  In the beginning, the universe was created. This has made a lot of',
     '  people very angry and has been widely regarded as a bad move'...]

Self-Generated Bug Notifications
--------------------------------

People (not teams) will have the choice to receive notifications from actions
they generated.  For now, everyone receives these notifications whether they
want them or not.

    >>> with lp_dbuser():
    ...     person = factory.makePerson()
    ...
    >>> person.selfgenerated_bugnotifications
    False
    >>> with lp_dbuser():
    ...     person.selfgenerated_bugnotifications = True
    ...

Teams provide this attribute read-only.

    >>> with lp_dbuser():
    ...     team = factory.makeTeam()
    ...
    >>> team.selfgenerated_bugnotifications
    False
    >>> with lp_dbuser():
    ...     team.selfgenerated_bugnotifications = True
    ...
    Traceback (most recent call last):
    ...
    NotImplementedError: Teams do not support changing this attribute.

Notification Recipients
-----------------------

Bug notifications are sent to direct subscribers of a bug as well as to
structural subscribers. Structural subcribers can select the
notification level of the subscription.

    >>> flush_notifications()

    >>> from lp.bugs.enums import BugNotificationLevel
    >>> from lp.registry.interfaces.product import IProductSet
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> mr_no_privs = getUtility(IPersonSet).getByName("no-priv")
    >>> with lp_dbuser():
    ...     subscription_no_priv = firefox.addBugSubscription(
    ...         mr_no_privs, mr_no_privs
    ...     )
    ...

The notifications generated by addCommentNotification() are sent only to
structural subscribers with no filters, or with the notification level
of COMMENTS or higher. Sample Person's subscription currently does not
have any filters other than the initial catch-all one, so they receive these
notifications.

    >>> print(subscription_no_priv.bug_filters.count())
    1
    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "another comment.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> bug_one.addCommentNotification(comment)
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> email_notifications = get_email_notifications(pending_notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: foo.bar@canonical.com
    ...
    You received this bug notification because you are subscribed to
    mozilla-firefox in Ubuntu.
    ...
    ----------------------------------------------------------------------
    To: mark@example.com
    ...
    You received this bug notification because you are a bug assignee.
    ...
    ----------------------------------------------------------------------
    To: no-priv@canonical.com
    From: Sample Person <...@bugs.launchpad.net>
    Subject: [Bug 1] subject
    X-Launchpad-Message-Rationale: Subscriber (Mozilla Firefox)
    X-Launchpad-Message-For: no-priv
    <BLANKLINE>
    another comment.
    <BLANKLINE>
    --
    You received this bug notification because you are subscribed to Mozilla
    Firefox.
    ...
    ----------------------------------------------------------------------
    To: owner@example.com
    ...
    You received this bug notification because you are a member of
    Addressless Team, which is subscribed to the bug report.
    ...
    ----------------------------------------------------------------------
    To: test@canonical.com
    ...
    You received this bug notification because you are subscribed to the bug
    report.
    ...
    ----------------------------------------------------------------------

If Sample Person gets a filter with an explicit notification level of
COMMENTS, they also receive these notifications.


    >>> flush_notifications()
    >>> with lp_dbuser():
    ...     filter = subscription_no_priv.newBugFilter()
    ...     filter.bug_notification_level = BugNotificationLevel.COMMENTS
    ...     filter.description = "Allow-comments filter"
    ...

    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "another comment.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> bug_one.addCommentNotification(comment)
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> email_notifications = get_email_notifications(pending_notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: foo.bar@canonical.com
    ...
    You received this bug notification because you are subscribed to
    mozilla-firefox in Ubuntu.
    ...
    ----------------------------------------------------------------------
    To: mark@example.com
    ...
    You received this bug notification because you are a bug assignee.
    ...
    ----------------------------------------------------------------------
    To: no-priv@canonical.com
    From: Sample Person <...@bugs.launchpad.net>
    Subject: [Bug 1] subject
    X-Launchpad-Message-Rationale: Subscriber (Mozilla Firefox)
    X-Launchpad-Message-For: no-priv
    X-Launchpad-Subscription: Allow-comments filter
    <BLANKLINE>
    another comment.
    <BLANKLINE>
    --
    You received this bug notification because you are subscribed to Mozilla
    Firefox.
    Matching subscriptions: Allow-comments filter
    ...
    ----------------------------------------------------------------------
    To: owner@example.com
    ...
    You received this bug notification because you are a member of
    Addressless Team, which is subscribed to the bug report.
    ...
    ----------------------------------------------------------------------
    To: test@canonical.com
    ...
    You received this bug notification because you are subscribed to the bug
    report.
    ...
    ----------------------------------------------------------------------

If Sample Person's notification level is set to METADATA, they receive
no comment notifications.

    >>> flush_notifications()
    >>> with lp_dbuser():
    ...     filter.bug_notification_level = BugNotificationLevel.METADATA
    ...

    >>> comment = getUtility(IMessageSet).fromText(
    ...     "subject",
    ...     "no comment for no-priv.",
    ...     sample_person,
    ...     datecreated=ten_minutes_ago,
    ... )
    >>> bug_one.addCommentNotification(comment)
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> email_notifications = get_email_notifications(pending_notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: foo.bar@canonical.com
    ...
    You received this bug notification because you are subscribed to
    mozilla-firefox in Ubuntu.
    ...
    ----------------------------------------------------------------------
    To: mark@example.com
    ...
    You received this bug notification because you are a bug assignee.
    ...
    ----------------------------------------------------------------------
    To: owner@example.com
    From: Sample Person <...@bugs.launchpad.net>
    Subject: [Bug 1] subject
    X-Launchpad-Message-Rationale: Subscriber @addressless
    X-Launchpad-Message-For: addressless
    <BLANKLINE>
    no comment for no-priv.
    <BLANKLINE>
    --
    You received this bug notification because you are a member of
    Addressless Team, which is subscribed to the bug report.
    ...
    ----------------------------------------------------------------------
    To: test@canonical.com
    ...
    You received this bug notification because you are subscribed to the bug
    report.
    ...
    ----------------------------------------------------------------------

The notifications generated by addChange() are sent only to structural
subscribers with the notification level METADATA or higher. The
notification level of Sample Person is currently METADATA, hence they
receive these notifications.

    >>> bug_one.addChange(
    ...     BugTitleChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "title",
    ...         "New summary",
    ...         "Whatever",
    ...     )
    ... )
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> email_notifications = get_email_notifications(pending_notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: foo.bar@canonical.com
    ...
    You received this bug notification because you are subscribed to
    mozilla-firefox in Ubuntu.
    http://bugs.launchpad.test/bugs/1
    ...
    ----------------------------------------------------------------------
    To: mark@example.com
    ...
    You received this bug notification because you are a bug assignee.
    ...
    ----------------------------------------------------------------------
    To: no-priv@canonical.com
    From: Sample Person <...@bugs.launchpad.net>
    Subject: [Bug 1] subject
    X-Launchpad-Message-Rationale: Subscriber (Mozilla Firefox)
    X-Launchpad-Message-For: no-priv
    X-Launchpad-Subscription: Allow-comments filter
    <BLANKLINE>
    no comment for no-priv.
    <BLANKLINE>
    ** Summary changed:
    - New summary
    + Whatever
    <BLANKLINE>
    --
    You received this bug notification because you are subscribed to Mozilla
    Firefox.
    Matching subscriptions: Allow-comments filter
    ...
    ----------------------------------------------------------------------
    To: owner@example.com
    ...
    You received this bug notification because you are a member of
    Addressless Team, which is subscribed to the bug report.
    ...
    ----------------------------------------------------------------------
    To: test@canonical.com
    ...
    You received this bug notification because you are subscribed to the bug
    report.
    ...
    ----------------------------------------------------------------------

If Sample Person sets their notification level to LIFECYCLE, they receive
no notifications created by addChange().

    >>> flush_notifications()
    >>> with lp_dbuser():
    ...     filter.bug_notification_level = BugNotificationLevel.LIFECYCLE
    ...

    >>> bug_one.addChange(
    ...     BugTitleChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "title",
    ...         "Whatever",
    ...         "Whatever else",
    ...     )
    ... )
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> email_notifications = get_email_notifications(pending_notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: foo.bar@canonical.com
    ...
    You received this bug notification because you are subscribed to
    mozilla-firefox in Ubuntu.
    ...
    ----------------------------------------------------------------------
    To: mark@example.com
    ...
    You received this bug notification because you are a bug assignee.
    ...
    ----------------------------------------------------------------------
    To: owner@example.com
    From: Sample Person <...@bugs.launchpad.net>
    Subject: [Bug 1] Re: Firefox does not support SVG
    X-Launchpad-Message-Rationale: Subscriber @addressless
    X-Launchpad-Message-For: addressless
    <BLANKLINE>
    ** Summary changed:
    - Whatever
    + Whatever else
    <BLANKLINE>
    --
    You received this bug notification because you are a member of
    Addressless Team, which is subscribed to the bug report.
    http://bugs.launchpad.test/bugs/1
    ...
    ----------------------------------------------------------------------
    To: test@canonical.com
    ...
    You received this bug notification because you are subscribed to the bug
    report.
    ...
    ----------------------------------------------------------------------

Note that, if two filters exist and they both match the same bug, the
more inclusive filter wins.  Therefore, while we saw before that the
filter did not allow the change notification through, if we add another
filter that includes metadata then the notification will be sent out
after all.

    >>> flush_notifications()
    >>> with lp_dbuser():
    ...     filter2 = subscription_no_priv.newBugFilter()
    ...     filter2.bug_notification_level = BugNotificationLevel.METADATA
    ...

    >>> bug_one.addChange(
    ...     BugTitleChange(
    ...         ten_minutes_ago,
    ...         sample_person,
    ...         "title",
    ...         "I'm losing my",
    ...         "Marbles",
    ...     )
    ... )
    >>> pending_notifications = getUtility(
    ...     IBugNotificationSet
    ... ).getNotificationsToSend()
    >>> email_notifications = get_email_notifications(pending_notifications)
    >>> for bug_notifications, omitted, messages in email_notifications:
    ...     for message in messages:
    ...         print_notification(message)
    ...
    To: foo.bar@canonical.com
    ...
    You received this bug notification because you are subscribed to
    mozilla-firefox in Ubuntu.
    http://bugs.launchpad.test/bugs/1
    ...
    ----------------------------------------------------------------------
    To: mark@example.com
    ...
    You received this bug notification because you are a bug assignee.
    ...
    ----------------------------------------------------------------------
    To: no-priv@canonical.com
    From: Sample Person <...@bugs.launchpad.net>
    Subject: [Bug 1] Re: Firefox does not support SVG
    X-Launchpad-Message-Rationale: Subscriber (Mozilla Firefox)
    X-Launchpad-Message-For: no-priv
    <BLANKLINE>
    ** Summary changed:
    - I'm losing my
    + Marbles
    <BLANKLINE>
    --
    You received this bug notification because you are subscribed to Mozilla
    Firefox.
    ...
    ----------------------------------------------------------------------
    To: owner@example.com
    ...
    You received this bug notification because you are a member of
    Addressless Team, which is subscribed to the bug report.
    ...
    ----------------------------------------------------------------------
    To: test@canonical.com
    ...
    You received this bug notification because you are subscribed to the bug
    report.
    ...
    ----------------------------------------------------------------------
