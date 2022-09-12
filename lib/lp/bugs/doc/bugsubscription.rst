BugSubscription
===============

Users can get email notifications of changes to bugs by subscribing to
them.

Bug Subscriber APIs
-------------------

First, let's login:

    >>> from lp.testing import login
    >>> login("foo.bar@canonical.com")

IBug has a subscriptions attribute:

    >>> from zope.component import getUtility
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> bugset = getUtility(IBugSet)
    >>> bug = bugset.get(1)
    >>> bug.subscriptions.count()
    2

This list returns only *direct* subscribers. Bugs can also have
indirect subscribers.

Direct vs. Indirect Subscriptions
.................................

A user is directly subscribed to a bug if they or someone else has
subscribed them to the bug.

Then there are three kinds of users that are indirectly subscribed to
a bug:

    * assignees
    * structural subscribers (subscribers to the bug's target)
    * direct subscribers from dupes

Bugs may get reassigned, bug subscribers may come and go, and dupes may
be unduped or reduped to other bugs. Indirect subscriptions are looked
up at mail sending time, so the mail is automatically sent to new bug
subscribers or assignees, stops being sent to subscribers from dupes when
a bug is unduped, and so forth.

Let's create a new bug to demonstrate how direct and indirect
subscriptions work.

    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.app.enums import InformationType
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> personset = getUtility(IPersonSet)

    >>> linux_source = ubuntu.getSourcePackage("linux-source-2.6.15")
    >>> list(linux_source.bug_subscriptions)
    []
    >>> print(linux_source.distribution.bug_supervisor)
    None

    >>> foobar = getUtility(ILaunchBag).user
    >>> print(foobar.name)
    name16

    >>> params = CreateBugParams(
    ...     title="a bug to test subscriptions", comment="test", owner=foobar
    ... )
    >>> linux_source_bug = linux_source.createBug(params)

The list of direct bug subscribers is accessed via
IBug.getDirectSubscribers().

    >>> def print_displayname(subscribers):
    ...     subscriber_names = sorted(
    ...         subscriber.displayname for subscriber in subscribers
    ...     )
    ...     for name in subscriber_names:
    ...         print(name)
    ...

    >>> print_displayname(linux_source_bug.getDirectSubscribers())
    Foo Bar

    >>> mark = personset.getByName("mark")

    >>> linux_source_bug.subscribe(mark, mark)
    <lp.bugs.model.bugsubscription.BugSubscription ...>

    >>> print_displayname(linux_source_bug.getDirectSubscribers())
    Foo Bar
    Mark Shuttleworth

The list of indirect subscribers is accessed via
IBug.getIndirectSubscribers().

    >>> linux_source_bug.getIndirectSubscribers()
    []

Finer-grained access to indirect subscribers is provided by
getAlsoNotifiedSubscribers() and getSubscribersFromDuplicates().

    >>> list(linux_source_bug.getAlsoNotifiedSubscribers())
    []
    >>> list(linux_source_bug.getSubscribersFromDuplicates())
    []

It is also possible to get the list of indirect subscribers for an
individual bug task.

    >>> from lp.bugs.model.bug import get_also_notified_subscribers
    >>> res = get_also_notified_subscribers(linux_source_bug.bugtasks[0])
    >>> list(res)
    []

These are security proxied.

    >>> from zope.security.proxy import Proxy
    >>> isinstance(res, Proxy)
    True

The list of all bug subscribers can also be accessed via
IBugTask.bug_subscribers. Our event handling machinery compares a
"snapshot" of this value, before a bug was changed, to the current
value, to check if there are new bugcontacts subscribed to this bug as a
result of a product or sourcepackage reassignment. It's also an
optimization to snapshot this list only on IBugTask, because we don't
need it for changes made only to IBug.

    >>> task = linux_source_bug.bugtasks[0]
    >>> print_displayname(task.bug_subscribers)
    Foo Bar
    Mark Shuttleworth

Here are some examples of the three types of indirect subscribers:

1. Assignees

    >>> sample_person = personset.getByName("name12")

    >>> linux_source_bug.bugtasks[0].transitionToAssignee(sample_person)

    >>> print_displayname(linux_source_bug.getIndirectSubscribers())
    Sample Person

    >>> linux_source_bug.getSubscribersFromDuplicates()
    ()

    >>> print_displayname(linux_source_bug.getAlsoNotifiedSubscribers())
    Sample Person

2. Structural subscribers

    >>> mr_no_privs = personset.getByName("no-priv")

    >>> subscription_no_priv = linux_source.addBugSubscription(
    ...     mr_no_privs, mr_no_privs
    ... )

    >>> transaction.commit()
    >>> print_displayname(
    ...     sub.subscriber for sub in linux_source.bug_subscriptions
    ... )
    No Privileges Person

    >>> print_displayname(linux_source_bug.getIndirectSubscribers())
    No Privileges Person
    Sample Person

    >>> linux_source_bug.getSubscribersFromDuplicates()
    ()
    >>> print_displayname(linux_source_bug.getAlsoNotifiedSubscribers())
    No Privileges Person
    Sample Person

    >>> ubuntu_team = personset.getByName("ubuntu-team")

    >>> linux_source.distribution.bug_supervisor = ubuntu_team

    >>> print_displayname(linux_source_bug.getIndirectSubscribers())
    No Privileges Person
    Sample Person

    >>> print_displayname(linux_source_bug.getAlsoNotifiedSubscribers())
    No Privileges Person
    Sample Person

After adding a product bugtask we can see that the upstream bug
supervisor is also an indirect subscriber.

    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> firefox = getUtility(IProductSet).get(4)

    >>> getUtility(IBugTaskSet).createTask(linux_source_bug, foobar, firefox)
    <BugTask ...>

    >>> lifeless = personset.getByName("lifeless")
    >>> firefox.bug_supervisor = lifeless

    >>> print_displayname(linux_source_bug.getIndirectSubscribers())
    No Privileges Person
    Sample Person

    >>> print_displayname(linux_source_bug.getAlsoNotifiedSubscribers())
    No Privileges Person
    Sample Person

If there were no upstream product bug subscribers, the product owner
would be used instead.

    >>> firefox.bug_supervisor = None

    >>> print_displayname(linux_source_bug.getIndirectSubscribers())
    No Privileges Person
    Sample Person

    >>> print_displayname(linux_source_bug.getAlsoNotifiedSubscribers())
    No Privileges Person
    Sample Person

    >>> previous_owner = firefox.owner

    >>> firefox.owner = lifeless

    >>> print_displayname(linux_source_bug.getIndirectSubscribers())
    No Privileges Person
    Sample Person

    >>> print_displayname(linux_source_bug.getAlsoNotifiedSubscribers())
    No Privileges Person
    Sample Person

    >>> firefox.owner = previous_owner
    >>> firefox.bug_supervisor = lifeless

IBug.getAlsoNotifiedSubscribers() and IBug.getIndirectSubscribers() take
an optional parameter `level` allowing us to filter the result by
BugNotificationLevel for structural subscriptions.  Only subscribers who
have a bug notification level greater than or equal to the value passed
in the `level` parameter are returned.

Structural subscriptions control their bug notification levels via one
or more filters.  If there are no explicit filters, the default subscription
filter is interpreted to mean that the subscriber wants all notifications.
In the case of bug notification levels, that is equivalent to
BugNotificationLevel.COMMENTS.

    >>> print(subscription_no_priv.bug_filters.count())
    1

With this subscription level, No Privileges Person is returned for all
parameter values of level.

    >>> from lp.bugs.enums import BugNotificationLevel
    >>> print_displayname(
    ...     linux_source_bug.getAlsoNotifiedSubscribers(
    ...         level=BugNotificationLevel.COMMENTS
    ...     )
    ... )
    No Privileges Person
    Sample Person

    >>> print_displayname(
    ...     linux_source_bug.getIndirectSubscribers(
    ...         level=BugNotificationLevel.COMMENTS
    ...     )
    ... )
    No Privileges Person
    Sample Person

    >>> print_displayname(
    ...     linux_source_bug.getAlsoNotifiedSubscribers(
    ...         level=BugNotificationLevel.LIFECYCLE
    ...     )
    ... )
    No Privileges Person
    Sample Person

    >>> print_displayname(
    ...     linux_source_bug.getIndirectSubscribers(
    ...         level=BugNotificationLevel.LIFECYCLE
    ...     )
    ... )
    No Privileges Person
    Sample Person

If No Privileges Person created a single filter with a notification
level set to LIFECYCLE, they will not be included, if the parameter
`level` is METADATA or COMMENTS.

    >>> from lp.testing import person_logged_in
    >>> with person_logged_in(mr_no_privs):
    ...     filter_no_priv = subscription_no_priv.bug_filters.one()
    ...     filter_no_priv.bug_notification_level = (
    ...         BugNotificationLevel.LIFECYCLE
    ...     )
    ...

    >>> print_displayname(
    ...     linux_source_bug.getAlsoNotifiedSubscribers(
    ...         level=BugNotificationLevel.LIFECYCLE
    ...     )
    ... )
    No Privileges Person
    Sample Person

    >>> print_displayname(
    ...     linux_source_bug.getIndirectSubscribers(
    ...         level=BugNotificationLevel.LIFECYCLE
    ...     )
    ... )
    No Privileges Person
    Sample Person

    >>> print_displayname(
    ...     linux_source_bug.getAlsoNotifiedSubscribers(
    ...         level=BugNotificationLevel.METADATA
    ...     )
    ... )
    Sample Person

    >>> print_displayname(
    ...     linux_source_bug.getIndirectSubscribers(
    ...         level=BugNotificationLevel.METADATA
    ...     )
    ... )
    Sample Person

3. Direct subscribers of duplicate bugs.

    >>> keybuk = personset.getByName("keybuk")

    >>> params = CreateBugParams(
    ...     title="a bug to test subscriptions", comment="test", owner=keybuk
    ... )
    >>> linux_source_bug_dupe = linux_source.createBug(params)

    >>> print_displayname(linux_source_bug_dupe.getDirectSubscribers())
    Scott James Remnant

Indirect subscribers of duplicates are *not* subscribed to dupe
targets. For example, assigning stub to the dupe bug will demonstrate
how he, as an indirect subscriber of the dupe, but does not get
subscribed to the dupe target.

    >>> linux_source_bug_dupe.bugtasks[0].transitionToAssignee(
    ...     personset.getByName("stub")
    ... )

    >>> print_displayname(linux_source_bug_dupe.getIndirectSubscribers())
    No Privileges Person
    Stuart Bishop

    >>> linux_source_bug_dupe.markAsDuplicate(linux_source_bug)

    >>> print_displayname(linux_source_bug.getIndirectSubscribers())
    No Privileges Person
    Sample Person
    Scott James Remnant

    >>> print_displayname(linux_source_bug.getSubscribersFromDuplicates())
    Scott James Remnant

If Scott James Remnant makes a structural subscription to linux_source,
he will no longer appear in the list of subscribers of the duplicate
bug.

    >>> subscription_keybuk = linux_source.addBugSubscription(keybuk, keybuk)
    >>> linux_source_bug.getSubscribersFromDuplicates()
    ()

Direct subscriptions always take precedence over indirect subscriptions.

    >>> print_displayname(linux_source_bug.getDirectSubscribers())
    Foo Bar
    Mark Shuttleworth

    >>> print_displayname(linux_source_bug.getIndirectSubscribers())
    No Privileges Person
    Sample Person
    Scott James Remnant

    >>> print_displayname(linux_source_bug.getAlsoNotifiedSubscribers())
    No Privileges Person
    Sample Person
    Scott James Remnant

To find out which email addresses should receive a notification email on
a bug, and why, IBug.getBugNotificationRecipients() assembles an
INotificationRecipientSet instance for us:

    >>> recipients = linux_source_bug.getBugNotificationRecipients()

You can query for the addresses and reasons:

    >>> addresses = recipients.getEmails()
    >>> for address in addresses:
    ...     print("%s: %s" % (address, recipients.getReason(address)[1]))
    ...
    foo.bar@canonical.com: Subscriber
    mark@example.com: Subscriber
    no-priv@canonical.com: Subscriber (linux-source-2.6.15 in Ubuntu)
    test@canonical.com: Assignee

If IBug.getBugNotificationRecipients() is passed a  BugNotificationLevel
in its `level` parameter, only structural subscribers with that
notification level or higher will be returned.

    >>> recipients = linux_source_bug.getBugNotificationRecipients(
    ...     level=BugNotificationLevel.COMMENTS
    ... )
    >>> addresses = recipients.getEmails()
    >>> for address in addresses:
    ...     print("%s: %s" % (address, recipients.getReason(address)[1]))
    ...
    foo.bar@canonical.com: Subscriber
    mark@example.com: Subscriber
    test@canonical.com: Assignee

When Sample Person is unsubscribed from linux_source_bug, they are no
longer included in the result of getBugNotificationRecipients() for
the COMMENTS level...

    >>> linux_source_bug.unsubscribe(mr_no_privs, mr_no_privs)
    >>> recipients = linux_source_bug.getBugNotificationRecipients(
    ...     level=BugNotificationLevel.COMMENTS
    ... )
    >>> addresses = recipients.getEmails()
    >>> for address in addresses:
    ...     print("%s: %s" % (address, recipients.getReason(address)[1]))
    ...
    foo.bar@canonical.com: Subscriber
    mark@example.com: Subscriber
    test@canonical.com: Assignee

...but remains included for the level LIFECYCLE.

    >>> linux_source_bug.unsubscribe(mr_no_privs, mr_no_privs)
    >>> recipients = linux_source_bug.getBugNotificationRecipients(
    ...     level=BugNotificationLevel.LIFECYCLE
    ... )
    >>> addresses = recipients.getEmails()
    >>> for address in addresses:
    ...     print("%s: %s" % (address, recipients.getReason(address)[1]))
    ...
    foo.bar@canonical.com: Subscriber
    mark@example.com: Subscriber
    no-priv@canonical.com: Subscriber (linux-source-2.6.15 in Ubuntu)
    test@canonical.com: Assignee

To find out if someone is already directly subscribed to a bug, call
IBug.isSubscribed, passing in an IPerson:

    >>> linux_source_bug.isSubscribed(personset.getByName("debonzi"))
    False
    >>> name16 = personset.getByName("name16")
    >>> linux_source_bug.isSubscribed(name16)
    True

Call isSubscribedToDupes to see if a user is directly subscribed to
dupes of a bug. This is useful for, for example, figuring out how to
display the Subscribe/Unsubscribe menu option, and in TAL, for deciding
whether the user needs to be warned, while unsubscribing, that they will
be unsubscribed from dupes.

    >>> bug_five = bugset.get(5)
    >>> bug_six = bugset.get(6)

    >>> bug_six.duplicateof == bug_five
    True

    >>> bug_five.isSubscribedToDupes(sample_person)
    False

    >>> bug_six.subscribe(sample_person, sample_person)
    <lp.bugs.model.bugsubscription.BugSubscription...>

    >>> bug_five.isSubscribedToDupes(sample_person)
    True

Subscribing and Unsubscribing
-----------------------------

To subscribe people to and unsubscribe people from a bug, use
IBug.subscribe and IBug.unsubscribe:

    >>> foobar = personset.getByName("name16")

    >>> bug.isSubscribed(foobar)
    False
    >>> subscription = bug.subscribe(foobar, foobar)
    >>> bug.isSubscribed(foobar)
    True

    >>> bug.unsubscribe(foobar, foobar)
    >>> bug.isSubscribed(foobar)
    False

By default, the bug_notification_level of the new subscription will be
COMMENTS, so the user will receive all notifications about the bug.

    >>> print(subscription.bug_notification_level.name)
    COMMENTS

It's possible to subscribe to a bug at a different BugNotificationLevel
by passing a `level` parameter to subscribe().

    >>> metadata_subscriber = factory.makePerson()
    >>> metadata_subscribed_bug = factory.makeBug()
    >>> metadata_subscription = metadata_subscribed_bug.subscribe(
    ...     metadata_subscriber,
    ...     metadata_subscriber,
    ...     level=BugNotificationLevel.METADATA,
    ... )

    >>> print(metadata_subscription.bug_notification_level.name)
    METADATA

To unsubscribe from all dupes for a bug, call
IBug.unsubscribeFromDupes. This is useful because direct subscribers
from dupes are automatically subscribed to dupe targets, so we provide
them a way to unsubscribe.

For example, Sample Person can be unsubscribed from bug #6, by
unsubscribing them from the dupes of bug #5, because bug #6 is a dupe of
bug #5.

    >>> bug_six.duplicateof == bug_five
    True

    >>> bug_six.isSubscribed(sample_person)
    True

The return value of unsubscribeFromDupes() is a list of bugs from which
the user was unsubscribed.

    >>> [
    ...     bug.id
    ...     for bug in bug_five.unsubscribeFromDupes(
    ...         sample_person, sample_person
    ...     )
    ... ]
    [6]

    >>> bug_six.isSubscribed(sample_person)
    False


Determining whether a user can unsubscribe someone
..................................................

As user can't unsubscribe just anyone from a bug. To check whether
someone can be unusubscribed, the canBeUnsubscribedByUser() method on
the BugSubscription object is used.

The user can of course unsubscribe themselves, even if someone else
subscribed them.

    >>> bug = factory.makeBug()
    >>> subscriber = factory.makePerson()
    >>> subscribed_by = factory.makePerson()
    >>> subscription = bug.subscribe(subscriber, subscribed_by)
    >>> subscription.canBeUnsubscribedByUser(subscriber)
    True

The one who subscribed the subscriber does have permission to
unsubscribe them.

    >>> subscription.canBeUnsubscribedByUser(subscribed_by)
    True

Launchpad administrators can also unsubscribe them.

    >>> subscription.canBeUnsubscribedByUser(foobar)
    True

The anonymous user (represented by None) also can't unsubscribe them.

    >>> subscription.canBeUnsubscribedByUser(None)
    False

A user can unsubscribe a team they're a member of.

    >>> team = factory.makeTeam()
    >>> member = factory.makePerson()
    >>> member.join(team)
    >>> subscription = bug.subscribe(team, subscribed_by)
    >>> subscription.canBeUnsubscribedByUser(member)
    True

    >>> non_member = factory.makePerson()
    >>> subscription.canBeUnsubscribedByUser(non_member)
    False

The anonymous user (represented by None) also can't unsubscribe the team.

    >>> subscription.canBeUnsubscribedByUser(None)
    False

A bug's unsubscribe method uses canBeUnsubscribedByUser to check
that the unsubscribing user has the appropriate permissions.  unsubscribe
will raise an exception if the user does not have permission.

    >>> bug.unsubscribe(team, non_member)
    Traceback (most recent call last):
    ...
    lp.app.errors.UserCannotUnsubscribePerson: ...


Automatic Subscriptions on Bug Creation
---------------------------------------

When a new bug is opened, only the bug reporter is automatically, explicitly
subscribed to the bug:

Define a function that get subscriber email addresses back conveniently:

    >>> def getSubscribers(bug):
    ...     recipients = bug.getBugNotificationRecipients()
    ...     return recipients.getEmails()
    ...

Let's have a look at an example for a distribution bug:

    >>> ubuntu.bug_supervisor = sample_person

    >>> params = CreateBugParams(
    ...     title="a test bug", comment="a test description", owner=foobar
    ... )
    >>> new_bug = ubuntu.createBug(params)

Only the bug reporter, Foo Bar, has an explicit subscription.

    >>> for subscription in new_bug.subscriptions:
    ...     print(subscription.person.displayname)
    ...
    Foo Bar

But because Sample Person is the distribution contact for Ubuntu, they
will be implicitly added to the notification recipients.

    >>> getSubscribers(new_bug)
    ['foo.bar@canonical.com']
    >>> from lp.services.mail import stub
    >>> transaction.commit()
    >>> stub.test_emails = []

    >>> params = CreateBugParams(
    ...     title="a test bug",
    ...     comment="a test description",
    ...     owner=foobar,
    ...     information_type=InformationType.PRIVATESECURITY,
    ... )
    >>> new_bug = ubuntu.createBug(params)

    >>> getSubscribers(new_bug)
    ['foo.bar@canonical.com']

Even though support@ubuntu.com got subscribed while filing the bug, no
"You have been subscribed" notification was sent, which is normally sent
to new subscribers.

    >>> transaction.commit()
    >>> stub.test_emails
    []

Another example, this time for an upstream:

    >>> firefox.bug_supervisor = mark

    >>> params = CreateBugParams(
    ...     title="a test bug", comment="a test description", owner=foobar
    ... )
    >>> new_bug = firefox.createBug(params)

Again, only Foo Bar is explicitly subscribed:

    >>> for subscription in new_bug.subscriptions:
    ...     print(subscription.person.displayname)
    ...
    Foo Bar

But the upstream Firefox bug supervisor, mark, is implicitly added to the
recipients list.

    >>> getSubscribers(new_bug)
    ['foo.bar@canonical.com']

If we create a bug task on Ubuntu in the same bug, the Ubuntu bug
supervisor will be subscribed:

    >>> ubuntu_task = getUtility(IBugTaskSet).createTask(
    ...     new_bug, mark, ubuntu
    ... )

    >>> print("\n".join(getSubscribers(new_bug)))
    foo.bar@canonical.com

But still, only Foo Bar is explicitly subscribed.

    >>> for subscription in new_bug.subscriptions:
    ...     print(subscription.person.displayname)
    ...
    Foo Bar

When an upstream does *not* have a specific bug supervisor set, the
product.owner is used instead. So, if Firefox's bug supervisor is unset,
Sample Person, the Firefox "owner" will get subscribed instead:

    >>> firefox.bug_supervisor = None

    >>> params = CreateBugParams(
    ...     title="a test bug", comment="a test description", owner=foobar
    ... )
    >>> new_bug = firefox.createBug(params)

Foo Bar is the only explicit subscriber:

    >>> for subscription in new_bug.subscriptions:
    ...     print(subscription.person.displayname)
    ...
    Foo Bar

But the product owner, Sample Person, is implicitly added to the
recipient list:

    >>> print("\n".join(getSubscribers(new_bug)))
    foo.bar@canonical.com
    >>> params = CreateBugParams(
    ...     title="a test bug",
    ...     comment="a test description",
    ...     owner=foobar,
    ...     information_type=InformationType.PRIVATESECURITY,
    ... )
    >>> new_bug = firefox.createBug(params)

    >>> print("\n".join(getSubscribers(new_bug)))
    foo.bar@canonical.com

Now let's create a bug on a specific package, which has no package bug
contacts:

    >>> evolution = ubuntu.getSourcePackage("evolution")
    >>> list(evolution.bug_subscriptions)
    []

    >>> params = CreateBugParams(
    ...     title="another test bug",
    ...     comment="another test description",
    ...     owner=foobar,
    ... )
    >>> new_bug = evolution.createBug(params)

    >>> getSubscribers(new_bug)
    ['foo.bar@canonical.com']

Adding a package bug contact for evolution will mean that that package
bug supervisor gets implicitly subscribed to all bugs ever opened on that
package.

So, if the Ubuntu team is added as a bug supervisor to evolution:

    >>> evolution.addBugSubscription(ubuntu_team, ubuntu_team)
    <...StructuralSubscription object at ...>

The team will be implicitly subscribed to the previous bug we
created:

    >>> for subscription in new_bug.subscriptions:
    ...     print(subscription.person.displayname)
    ...
    Foo Bar

    >>> new_bug.clearBugNotificationRecipientsCache()
    >>> getSubscribers(new_bug)
    ['foo.bar@canonical.com', 'support@ubuntu.com']

And the Ubuntu team will be implicitly subscribed to future bugs:

    >>> params = CreateBugParams(
    ...     title="yet another test bug",
    ...     comment="yet another test description",
    ...     owner=foobar,
    ... )
    >>> new_bug = evolution.createBug(params)

    >>> for subscription in new_bug.subscriptions:
    ...     print(subscription.person.displayname)
    ...
    Foo Bar

    >>> getSubscribers(new_bug)
    ['foo.bar@canonical.com', 'support@ubuntu.com']
    >>> params = CreateBugParams(
    ...     title="yet another test bug",
    ...     comment="yet another test description",
    ...     owner=foobar,
    ...     information_type=InformationType.PRIVATESECURITY,
    ... )
    >>> new_bug = evolution.createBug(params)

    >>> getSubscribers(new_bug)
    ['foo.bar@canonical.com']


Subscribed by
-------------

Each `BugSubscription` records who created it, and provides a handy
utility method for formatting this information. The methods
`getDirectSubscriptions` and `getSubscriptionsFromDuplicates` provide
an equivalent to the -Subscribers methods, but returning the
subscriptions themselves, rather than the subscribers.

    >>> params = CreateBugParams(
    ...     title="one more test bug",
    ...     comment="one more test description",
    ...     owner=mark,
    ... )
    >>> ff_bug = firefox.createBug(params)
    >>> ff_bug.subscribe(lifeless, mark)
    <lp.bugs.model.bugsubscription.BugSubscription ...>
    >>> subscriptions = [
    ...     "%s: %s"
    ...     % (
    ...         subscription.person.displayname,
    ...         subscription.display_subscribed_by,
    ...     )
    ...     for subscription in ff_bug.getDirectSubscriptions()
    ... ]
    >>> for subscription in sorted(subscriptions):
    ...     print(subscription)
    ...
    Mark Shuttleworth: Self-subscribed
    Robert Collins: Subscribed by Mark Shuttleworth (mark)
    >>> params = CreateBugParams(
    ...     title="one more dupe test bug",
    ...     comment="one more dupe test description",
    ...     owner=keybuk,
    ... )
    >>> dupe_ff_bug = firefox.createBug(params)
    >>> dupe_ff_bug.markAsDuplicate(ff_bug)
    >>> dupe_ff_bug.subscribe(foobar, lifeless)
    <lp.bugs.model.bugsubscription.BugSubscription ...>
    >>> for subscription in ff_bug.getSubscriptionsFromDuplicates():
    ...     print(
    ...         "%s: %s"
    ...         % (
    ...             subscription.person.displayname,
    ...             subscription.display_duplicate_subscribed_by,
    ...         )
    ...     )
    ...
    Scott James Remnant: Self-subscribed to bug ...
    Foo Bar: Subscribed to bug ... by Robert Collins (lifeless)
