
BugNotificationRecipients instances store email addresses mapped to the
reason for which they are being notified in a certain bug. It implements
the INotificationRecipientSet interface for bug notifications. (See
notification-recipient-set.rst for the details.)

How it's used
=============

The IBug.getBugNotificationRecipients() implementation creates and uses
BugNotificationRecipients instances. Here's an example of this in
action:

    >>> from lp.bugs.model.bug import Bug
    >>> from lp.registry.model.distribution import Distribution
    >>> from lp.registry.model.product import Product
    >>> from lp.services.database.interfaces import IStore
    >>> bug_one = IStore(Bug).get(Bug, 1)
    >>> recipients = bug_one.getBugNotificationRecipients()

The instance of BugNotificationRecipients we get back correctly
implements INotificationRecipientSet:

    >>> from lp.services.mail.interfaces import INotificationRecipientSet
    >>> from lp.testing import verifyObject
    >>> verifyObject(INotificationRecipientSet, recipients)
    True

This instance contains email addresses and rationales. Let's define a
helper function so we can format this output:

    >>> def print_rationales(rationale):
    ...     for address in rationale.getEmails():
    ...         text, header = rationale.getReason(address)
    ...         print(address)
    ...         print("    %s" % header)
    ...         print("    %s" % text)
    ...

And print them out. The first line is the email address; second is the
text appropriate to be used in an X- header, and the last is the text
appropriate for an email footer.

    >>> print_rationales(recipients)
    foo.bar@canonical.com
        Subscriber (mozilla-firefox in Ubuntu)
        You received this bug notification because you are subscribed
        to mozilla-firefox in Ubuntu.
    mark@example.com
        Assignee
        You received this bug notification because you are a bug assignee.
    test@canonical.com
        Subscriber
        You received this bug notification because you are subscribed
        to the bug report.

The Bug-BugNotificationRecipients API
=====================================

Most of the API of BugNotificationRecipients is actually kept private
between the Bug class and itself. Let's now demonstrate the API that Bug
and BugNotificationRecipients use to set up the rationales; this is
essentially what happens under the wraps when you call
IBug.getBugNotificationRecipients().

Let's up some data for our test:

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.bugs.mail.bugnotificationrecipients import (
    ...     BugNotificationRecipients,
    ... )
    >>> debian = IStore(Distribution).find(Distribution, name="debian").one()
    >>> pmount = debian.getSourcePackage("pmount")
    >>> alsa_utils = IStore(Product).find(Product, name="alsa-utils").one()
    >>> gnomebaker = IStore(Product).find(Product, name="gnomebaker").one()
    >>> personset = getUtility(IPersonSet)

Here's where getBugNotificationRecipients() starts off. First, a
BugNotificationRecipients instance is created:

    >>> recipients = BugNotificationRecipients()

Then, subscribers of various types are added:

    >>> foo_bar = personset.getByEmail("foo.bar@canonical.com")
    >>> recipients.addDupeSubscriber(foo_bar)

    >>> test = personset.getByEmail("test@canonical.com")
    >>> recipients.addDirectSubscriber(test)

    >>> no_priv = personset.getByEmail("no-priv@canonical.com")
    >>> recipients.addAssignee(no_priv)

    >>> carlos = personset.getByEmail("carlos@canonical.com")
    >>> recipients.addStructuralSubscriber(carlos, pmount)

If we print out the recipients and rationales, here's what we get:

    >>> print_rationales(recipients)
    carlos@canonical.com
        Subscriber (pmount in Debian)
        You received this bug notification because you are subscribed
        to pmount in Debian.
    foo.bar@canonical.com
        Subscriber of Duplicate
        You received this bug notification because you are subscribed
        to a duplicate bug report.
    no-priv@canonical.com
        Assignee
        You received this bug notification because you are a bug
        assignee.
    test@canonical.com
        Subscriber
        You received this bug notification because you are subscribed
        to the bug report.

Note how we account for every important variation in bug subscriptions
here: bug supervisors, subscribers, dupe subscribers and more.

A duplicate bug modification notifies its main bug
==================================================

If the bug we are changing is actually a duplicate of another bug, an
additional step is involved. A BugNotificationRecipients instance is
created, annotating that it represents a master bug (of which we are a
duplicate of).

    >>> bug_two = IStore(Bug).get(Bug, 2)
    >>> recipients = BugNotificationRecipients(duplicateof=bug_two)

    >>> foo_bar = personset.getByEmail("foo.bar@canonical.com")
    >>> recipients.addDupeSubscriber(foo_bar)

    >>> test = personset.getByEmail("test@canonical.com")
    >>> recipients.addDirectSubscriber(test)

    >>> no_priv = personset.getByEmail("no-priv@canonical.com")
    >>> recipients.addAssignee(no_priv)

    >>> carlos = personset.getByEmail("carlos@canonical.com")
    >>> recipients.addStructuralSubscriber(carlos, pmount)

If you print out rationales in this situation, you'll see that the
message says "via Bug 2". The reason for this is that the people being
notified here are actually subscribed to bug 2, and they may be asking
themselves why the hell they are getting email for bug 1.

    >>> print_rationales(recipients)
    carlos@canonical.com
        Subscriber (pmount in Debian) via Bug 2
        You received this bug notification because you are subscribed
        to pmount in Debian (via bug 2).
    foo.bar@canonical.com
        Subscriber of Duplicate via Bug 2
        You received this bug notification because you are subscribed
        to a duplicate bug report (via bug 2).
    no-priv@canonical.com
        Assignee via Bug 2
        You received this bug notification because you are a bug
        assignee (via bug 2).
    test@canonical.com
        Subscriber via Bug 2
        You received this bug notification because you are subscribed
        to the bug report (via bug 2).

Team subscribers are special
============================

In the case where the teams are subscribers, things vary according to
whether the team has a contact email address or not. When there is no
contact email address, all team members (cascaded down) get emailed
directly, and the person getting the notification may not know of this
immediately.

Here's an example of this situation:

    >>> recipients = BugNotificationRecipients()
    >>> testing_spanish_team = personset.getByName("testing-spanish-team")
    >>> recipients.addDupeSubscriber(testing_spanish_team)

    >>> guadamen = personset.getByName("guadamen")
    >>> recipients.addAssignee(guadamen)

    >>> name20 = personset.getByName("name20")
    >>> recipients.addStructuralSubscriber(name20, pmount)

    >>> commercial_admins = personset.getByName("commercial-admins")
    >>> recipients.addDirectSubscriber(commercial_admins)

You'll notice that the rationales this time state clearly which team
membership is causing us to send mail.

    >>> print_rationales(recipients)
      carlos@canonical.com
          Subscriber of Duplicate @testing-spanish-team
          You received this bug notification because you are a member
          of testing Spanish team, which is subscribed to a
          duplicate bug report.
      commercial-member@canonical.com
          Subscriber @commercial-admins
          You received this bug notification because you are a member
          of Commercial Subscription Admins, which is subscribed to the
          bug report.
      foo.bar@canonical.com
          Subscriber of Duplicate @testing-spanish-team
          You received this bug notification because you are a member
          of testing Spanish team, which is subscribed to a
          duplicate bug report.
      kurem@debian.cz
          Subscriber of Duplicate @testing-spanish-team
          You received this bug notification because you are a member
          of testing Spanish team, which is subscribed to a
          duplicate bug report.
      mark@example.com
          Subscriber of Duplicate @testing-spanish-team
          You received this bug notification because you are a member
          of testing Spanish team, which is subscribed to a
          duplicate bug report.
      support@ubuntu.com
          Assignee @guadamen
          You received this bug notification because you are a member
          of GuadaMen, which is a bug assignee.
      test@canonical.com
          Subscriber (pmount in Debian) @name20
          You received this bug notification because you are a member
          of Warty Security Team, which is subscribed to pmount in
          Debian.
      tsukimi@quaqua.net
          Subscriber of Duplicate @testing-spanish-team
          You received this bug notification because you are a member
          of testing Spanish team, which is subscribed to a
          duplicate bug report.

This doesn't help the end-user too much if they're a member of this team
indirectly (for instance, if they're a member of a team which is in turn a
member of another team); however, in that case, the user can still visit
the team page and see the membership graph directly. This may be worth
fixing in the future.

First impressions stick
=======================

Another important property of BugNotificationRecipients is that the
first rationale presented to it is the one that is presented -- even if
the recipient has multiple reasons for which they might be emailed. Here's
a pathological example:

    >>> recipients = BugNotificationRecipients()
    >>> recipients.addDirectSubscriber(test)
    >>> recipients.addAssignee(test)
    >>> recipients.addDirectSubscriber(foo_bar)

This guy is emailed because they're a direct subscriber, an assignee and an
upstream registrant. However, if we ask the rationales instance:

    >>> print_rationales(recipients)
    foo.bar@canonical.com
        Subscriber
        You received this bug notification because you are subscribed
        to the bug report.
    test@canonical.com
        Subscriber
        You received this bug notification because you are subscribed
        to the bug report.

Only the first rationale is presented. This is the case even if we
update this set of recipients with another one:

    >>> recipients2 = BugNotificationRecipients()
    >>> recipients2.addDupeSubscriber(test)
    >>> recipients2.update(recipients)

The rationales for test@canonical.com in the 'recipients' instance just
don't matter:

    >>> print_rationales(recipients2)
    foo.bar@canonical.com
        Subscriber
        You received this bug notification because you are subscribed
        to the bug report.
    test@canonical.com
        Subscriber of Duplicate
        You received this bug notification because you are subscribed
        to a duplicate bug report.

This may be seen as a limitation, but you don't want a 10-line rationale
footer for people who are central to Launchpad, so for now it's the way
it is.
