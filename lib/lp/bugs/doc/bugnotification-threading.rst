Bug Notification Threading
==========================

In order to make the notifications more usable, all notifications
related to a specific bug have their headers set so that they will be
grouped together by an email client that handles threading correctly.
Comments added by the web UI won't be correctly threaded, though, since
you can't know to which comment the new comment was a reply to.

Let's add add change notification and see how it works:

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.services.messages.model.message import MessageSet

    >>> login('test@canonical.com')

    >>> import pytz
    >>> from datetime import datetime, timedelta
    >>> from lp.services.messages.interfaces.message import IMessageSet
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.adapters.bugchange import BugInformationTypeChange
    >>> from lp.app.enums import InformationType

    >>> ten_minutes_ago = (
    ...     datetime.now(pytz.timezone('UTC')) - timedelta(minutes=10))
    >>> sample_person = getUtility(ILaunchBag).user
    >>> bug_one = getUtility(IBugSet).get(1)
    >>> bug_one.addChange(
    ...     BugInformationTypeChange(
    ...         ten_minutes_ago, sample_person, "information_type",
    ...         InformationType.PUBLIC, InformationType.USERDATA))

    >>> from lp.bugs.interfaces.bugnotification import IBugNotificationSet
    >>> from lp.bugs.scripts.bugnotification import (
    ...     get_email_notifications)
    >>> notifications = getUtility(
    ...     IBugNotificationSet).getNotificationsToSend()

    >>> messages = [emails for notifications, omitted, emails in
    ...     get_email_notifications(notifications)]
    >>> len(messages)
    1

There are three recipients for this message, so we get:

    >>> emails = messages[0]
    >>> len(emails)
    3

The three emails have identical headers for our purposes, so:

    >>> notification = emails[0]

The email has the message id of the change notification, and it
references the bug's initial message, so that it will be threaded in
an email client.

    >>> notification['Message-Id'] == notifications[0].message.rfc822msgid
    True
    >>> notification['References'] == bug_one.initial_message.rfc822msgid
    True

If we add a comment, the notification will have the comment's message
id:

    >>> comment = getUtility(IMessageSet).fromText(
    ...     'subject', 'comment', sample_person, datecreated=ten_minutes_ago)
    >>> bug_one.addCommentNotification(comment)
    >>> bug_one.linkMessage(comment)
    <...>
    >>> bug_one.addChange(
    ...     BugInformationTypeChange(
    ...         ten_minutes_ago, sample_person, "information_type",
    ...         InformationType.USERDATA, InformationType.PUBLIC))
    >>> notifications = getUtility(
    ...     IBugNotificationSet).getNotificationsToSend()
    >>> messages = [emails for notifications, omitted, emails in
    ...     get_email_notifications(notifications)]
    >>> len(messages)
    1
    >>> emails = messages[0]
    >>> len(emails)
    3
    >>> notification = emails[0]

    >>> notification['Message-Id'] == comment.rfc822msgid
    True
    >>> notification['References'] == bug_one.initial_message.rfc822msgid
    True

Refresh the dates, and create a new reply to ensure that the references
are chained together properly:

    >>> for notification in notifications:
    ...     notification.date_emailed = datetime.now(pytz.timezone('UTC'))
    >>> flush_database_updates()

    >>> reply = MessageSet().fromText(
    ...     'Re: subject', 'reply', sample_person,
    ...     datecreated=ten_minutes_ago)
    >>> reply.parent = comment
    >>> bug_one.addCommentNotification(reply)
    >>> bug_one.linkMessage(reply)
    <...>

Grab the notifications:

    >>> notifications = getUtility(
    ...     IBugNotificationSet).getNotificationsToSend()
    >>> messages = [emails for notifications, omitted, emails in
    ...     get_email_notifications(notifications)]
    >>> len(messages)
    1
    >>> emails = messages[0]
    >>> len(emails)
    3
    >>> notification = emails[0]
    >>> notification['Message-Id'] == reply.rfc822msgid
    True
    >>> references = notification['References'].split()
    >>> bug_one.initial_message.rfc822msgid in references
    True
    >>> comment.rfc822msgid in references
    True

Create a new bug, fetching the notification manually since it will not yet
be ready to send.  The notification sent for this should not have any
References header.

    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.bugs.model.bugnotification import BugNotification
    >>> from lp.services.database.interfaces import IStore

    >>> for notification in notifications:
    ...     notification.date_emailed = datetime.now(pytz.timezone('UTC'))
    >>> flush_database_updates()

    >>> params = CreateBugParams(
    ...     owner=sample_person, title="New bug", comment="New bug.",
    ...     target=bug_one.default_bugtask.target)
    >>> bug = getUtility(IBugSet).createBug(params)
    >>> notifications = IStore(BugNotification).find(BugNotification, bug=bug)
    >>> messages = [emails for notifications, omitted, emails in
    ...     get_email_notifications(notifications)]
    >>> len(messages)
    1
    >>> emails = messages[0]
    >>> len(emails)
    1
    >>> notification = emails[0]
    >>> notification['Message-Id'] == bug.initial_message.rfc822msgid
    True
    >>> 'References' in notification
    False
