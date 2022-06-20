Person notifications
====================

The PersonNotification table stores notifications that should be sent
(or already sent) to a given person.  It stores the person who should
receive the notification as well as the email message's body and
subject.  A cronscript is then responsible for picking up these
notifications and sending them.

    >>> from lp.registry.interfaces.personnotification import (
    ...     IPersonNotification, IPersonNotificationSet)
    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> notification_set = getUtility(IPersonNotificationSet)
    >>> mark = getUtility(IPersonSet).getByName('mark')

To add a new notification we need the recipient, the email body and its
subject.

    >>> notification = notification_set.addNotification(
    ...     mark, u'subject', u'body')
    >>> verifyObject(IPersonNotification, notification)
    True
    >>> print(notification.person.name)
    mark
    >>> notification.date_created
    datetime.datetime(...
    >>> print(notification.date_emailed)
    None

The notifications that need to be sent can be retrieved with
getNotificationsToSend().

    >>> for n in notification_set.getNotificationsToSend():
    ...     print(n.subject)
    subject

We can also retrieve notifications that are older than a certain date.

    >>> import pytz
    >>> from datetime import datetime, timedelta
    >>> now = datetime.now(pytz.timezone('UTC'))
    >>> for n in notification_set.getNotificationsOlderThan(now):
    ...     print(n.subject)
    subject

    >>> yesterday = now - timedelta(days=1)
    >>> [n.subject
    ...  for n in notification_set.getNotificationsOlderThan(yesterday)]
    []

A notification has a send() method which creates an email message and
sends it to the recipient.

    >>> from lp.services.log.logger import FakeLogger
    >>> notification.send(logger=FakeLogger())
    INFO Sending notification to ['Mark Shuttleworth <mark@example.com>'].
    >>> from lp.testing.mail_helpers import print_emails
    >>> print_emails()
    From: bounces@canonical.com
    To: Mark Shuttleworth <mark@example.com>
    Subject: subject
    body
    ----------------------------------------

The send-person-notifications script will send all pending
notifications.

    >>> notification = notification_set.addNotification(
    ...     mark, u'subject2', u'body2')

This includes notifications to teams owned by other teams.

    >>> owning_team = factory.makeTeam()
    >>> team = factory.makeTeam(owner=owning_team)
    >>> team_notification = notification_set.addNotification(
    ...     team, u'subject3', u'body3')
    >>> for n in notification_set.getNotificationsToSend():
    ...     print(n.subject)
    subject2
    subject3
    >>> transaction.commit()

    >>> import subprocess
    >>> process = subprocess.Popen(
    ...     'cronscripts/send-person-notifications.py -q', shell=True,
    ...     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE, universal_newlines=True)
    >>> (out, err) = process.communicate()
    >>> print(out)
    <BLANKLINE>
    >>> print(err)
    <BLANKLINE>
    >>> process.returncode
    0

    >>> [n.subject for n in notification_set.getNotificationsToSend()]
    []
