ArchiveSubscriber
=================

This content class represents a subscription by a person to an IArchive.
The subscription represents that person's ability to download items from
the archive's repository.  The subscription is granted by a person who
has upload permission to the archive.  Once created the subscription is only
viewable by other uploaders and the person in the subscription.

See also archiveauthtoken.rst.

First, create a person 'joesmith' and a team 'team_cprov':

    >>> login('foo.bar@canonical.com')
    >>> joesmith = factory.makePerson(name="joesmith",
    ...                               displayname="Joe Smith",
    ...                               email="joe@example.com")
    >>> johnsmith = factory.makePerson(name="johnsmith",
    ...                               displayname="John Smith",
    ...                               email="john@example.com")
    >>> fredsmith = factory.makePerson(name="fredsmith",
    ...                               displayname="Fred Smith",
    ...                               email="fred@example.com")
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> team_cprov = factory.makeTeam(cprov, "Team Cprov")
    >>> johnsmith.join(team_cprov)
    >>> from lp.testing.mail_helpers import print_emails


Creating new subscriptions
--------------------------

New subscriptions are created using IArchive.newSubscription()

Operations with subscriptions are security protected, so to start with we'll
log in as an unprivileged user.

    >>> login("no-priv@canonical.com")

We can create a new subscription for joesmith to access cprov's PPA like this:

    >>> new_sub = cprov.archive.newSubscription(joesmith, cprov)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

That failed because only people who have launchpad.Append (basically, upload
access) on the context archive are allowed to create subscriptions.

Users cannot create their own subscriptions either.  Log in as joesmith:

    >>> login("joe@example.com")
    >>> new_token = cprov.archive.newSubscription(joesmith, cprov)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

If we log in as cprov it will still not work because his archive is
public:

    >>> login("celso.providelo@canonical.com")
    >>> new_sub = cprov.archive.newSubscription(
    ...     joesmith, cprov, description=u"subscription for joesmith")
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.ArchiveNotPrivate:
    Only private archives can have subscriptions.

If we create a private ppa for Celso, then he can create a
subscription for joesmith:

    >>> login('foo.bar@canonical.com')
    >>> cprov_private_ppa = factory.makeArchive(
    ...     owner=cprov, distribution=cprov.archive.distribution,
    ...     private=True, name='p3a',
    ...     description="packages to help my friends.")
    >>> login("celso.providelo@canonical.com")
    >>> new_sub = cprov_private_ppa.newSubscription(
    ...     joesmith, cprov, description=u"subscription for joesmith")

The new subscription is returned and reflects the data:

    >>> print(new_sub.displayname)
    Joe Smith's access to PPA named p3a for Celso Providelo

    >>> print(new_sub.registrant.name)
    cprov

    >>> print(new_sub.description)
    subscription for joesmith

    >>> print(new_sub.status.name)
    CURRENT

Subscriptions also contain some date information:

    >>> new_sub.date_created is not None
    True

    >>> print(new_sub.date_expires)
    None

An email is sent to the subscribed person when the ArchiveSubscriber
entry is created:

    >>> print_emails(include_reply_to=True) #doctest: -NORMALIZE_WHITESPACE
    From: Celso Providelo <noreply@launchpad.net>
    To: joe@example.com
    Reply-To: Celso Providelo <celso.providelo@canonical.com>
    Subject: PPA access granted for PPA named p3a for Celso Providelo
    Hello Joe Smith,
    <BLANKLINE>
    Launchpad: access to a private archive
    --------------------------------------
    <BLANKLINE>
    Celso Providelo has granted you access to a private software archive
    "PPA named p3a for Celso Providelo" (ppa:cprov/p3a), which is hosted by
    Launchpad and has the following description:
    <BLANKLINE>
    packages to help my friends.
    <BLANKLINE>
    To start downloading and using software from this archive you need to
    view your access details by visiting this link:
    <BLANKLINE>
    <http://launchpad.test/~/+archivesubscriptions>
    <BLANKLINE>
    You can find out more about Celso Providelo here:
    <BLANKLINE>
    <http://launchpad.test/~cprov>
    <BLANKLINE>
    If you'd prefer not to use software from this archive, you can safely
    ignore this email. However, if you have any concerns you can contact the
    Launchpad team by emailing feedback@launchpad.net
    <BLANKLINE>
    Regards,
    The Launchpad team
    ----------------------------------------

If the description of the P3A is changed to None, and a new user subscribed
the email does not contain the description.

    >>> cprov_private_ppa.description = None
    >>> unused = cprov_private_ppa.newSubscription(fredsmith, cprov)
    >>> print_emails(include_reply_to=True) #doctest: -NORMALIZE_WHITESPACE
    From: Celso Providelo <noreply@launchpad.net>
    To: fred@example.com
    Reply-To: Celso Providelo <celso.providelo@canonical.com>
    Subject: PPA access granted for PPA named p3a for Celso Providelo
    Hello Fred Smith,
    <BLANKLINE>
    Launchpad: access to a private archive
    --------------------------------------
    <BLANKLINE>
    Celso Providelo has granted you access to a private software archive
    "PPA named p3a for Celso Providelo" (ppa:cprov/p3a), which is hosted by
    Launchpad.
    <BLANKLINE>
    To start downloading and using software from this archive you need to
    view your access details by visiting this link:
    <BLANKLINE>
    <http://launchpad.test/~/+archivesubscriptions>
    <BLANKLINE>
    You can find out more about Celso Providelo here:
    <BLANKLINE>
    <http://launchpad.test/~cprov>
    <BLANKLINE>
    If you'd prefer not to use software from this archive, you can safely
    ignore this email. However, if you have any concerns you can contact the
    Launchpad team by emailing feedback@launchpad.net
    <BLANKLINE>
    Regards,
    The Launchpad team
    ----------------------------------------

A subscription for a subscriber who already has a current subscription
cannot be created:

    >>> new_sub = cprov_private_ppa.newSubscription(
    ...     joesmith, cprov, description=u"subscription for joesmith")
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.archive.AlreadySubscribed: Joe Smith already has a
    current subscription for 'PPA named p3a for Celso Providelo'.


Add another subscription for the test user, this time to mark's ppa:

    >>> login("mark@example.com")
    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> mark_private_ppa = factory.makeArchive(
    ...     owner=mark, distribution=mark.archive.distribution,
    ...     private=True, name='p3a')
    >>> new_sub_to_mark_ppa = mark_private_ppa.newSubscription(
    ...     joesmith, mark, description=u"subscription for joesmith")

    >>> print_emails()
    From: Mark Shuttleworth <noreply@launchpad.net>
    To: joe@example.com
    ...

And also a subscription for a Team:

    >>> new_team_sub_to_mark_ppa = mark_private_ppa.newSubscription(
    ...     team_cprov, mark, description=u"Access for cprov team")

    >>> print_emails()
    From: Mark Shuttleworth <noreply@launchpad.net>
    To: celso.providelo@canonical.com
    ...


Explicitly set the date_created for testing purposes:

    >>> from datetime import datetime
    >>> import pytz
    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(new_sub).date_created = datetime(
    ...     2009, 2, 26, tzinfo=pytz.UTC)
    >>> removeSecurityProxy(new_sub_to_mark_ppa).date_created = datetime(
    ...     2009, 2, 22, tzinfo=pytz.UTC)
    >>> removeSecurityProxy(new_team_sub_to_mark_ppa).date_created = (
    ...     datetime(2009, 2, 24, tzinfo=pytz.UTC))

Commit the new subscriptions to the database.

    >>> from storm.store import Store
    >>> Store.of(new_sub).commit()

Retrieving existing subscriptions
---------------------------------

The ArchiveSubscriberSet utility allows you to retrieve subscriptions by
subscriber and archive.  To access subscriptions you need launchpad.View
privilege which applies to the person in the subscriptions and launchpad
admins.

    >>> from lp.soyuz.enums import ArchiveSubscriberStatus
    >>> from lp.soyuz.interfaces.archivesubscriber import (
    ...     IArchiveSubscriberSet)
    >>> sub_set = getUtility(IArchiveSubscriberSet)

    >>> login("no-priv@canonical.com")

    >>> sub = sub_set.getBySubscriber(new_sub.subscriber)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Log in as joesmith, who is the person in the subscription.

    >>> login("joe@example.com")

And retrieve the subscription by subscriber and archive:

    >>> print(sub_set.getBySubscriber(
    ...     new_sub.subscriber)[0].archive.displayname)
    PPA named p3a for Celso Providelo

    >>> print(sub_set.getByArchive(new_sub.archive)[1].subscriber.name)
    joesmith

The getBySubscriber() method takes an optional archive parameter for
finding a subscription for a particular user in a particular archive:

    >>> print(sub_set.getBySubscriber(
    ...     new_sub.subscriber, new_sub.archive)[0].archive.displayname)
    PPA named p3a for Celso Providelo

By default the getBySubscriber() and getByArchive() methods return
all current subscriptions, most recently created first:

    >>> login('mark@example.com')
    >>> for subscription in sub_set.getBySubscriber(new_sub.subscriber):
    ...     print(subscription.archive.displayname)
    ...     print(subscription.date_created.date())
    PPA named p3a for Celso Providelo      2009-02-26
    PPA named p3a for Mark Shuttleworth    2009-02-22

getByArchive() sorts by subscriber name.

    >>> for subscription in sub_set.getByArchive(mark_private_ppa):
    ...     print(subscription.subscriber.name)
    ...     print(subscription.subscriber.displayname)
    ...     print(subscription.date_created.date())
    joesmith            Joe Smith       2009-02-22
    team-name-...       Team Cprov      2009-02-24

If we cancel one of the subscriptions:

    >>> login("mark@example.com")
    >>> new_sub_to_mark_ppa.status = ArchiveSubscriberStatus.CANCELLED
    >>> login("joe@example.com")

then the cancelled subscription no longer appears in the results
of getBySubscriber() and getByArchive():

    >>> sub_set.getBySubscriber(new_sub.subscriber).count()
    1
    >>> sub_set.getByArchive(mark_private_ppa).count()
    1

Unless we explicitly ask for all subscriptions - not just the current ones:

    >>> sub_set.getBySubscriber(
    ...     new_sub.subscriber, current_only=False).count()
    2
    >>> sub_set.getByArchive(mark_private_ppa, current_only=False).count()
    2

The getBySubscriber() method includes by default subscriptions for teams
to which the provided subscriber belongs:

    >>> joesmith.join(team_cprov)
    >>> for subscription in sub_set.getBySubscriber(joesmith):
    ...     print(subscription.archive.displayname)
    ...     print(subscription.description)
    PPA named p3a for Celso Providelo        subscription for joesmith
    PPA named p3a for Mark Shuttleworth      Access for cprov team

Finally, many callsites of getBySubscriber() will be interested not only
in each subscription of the subscriber, but also the generated
ArchiveAuthToken for each subscription of the subscriber. These can
be returned as well using the getBySubscriberWithActiveToken():

First create a token for joesmith's subscription for cprov's archive:

    >>> joesmith_token = cprov_private_ppa.newAuthToken(
    ...     joesmith, u"test_token")

Now print out all subscriptions with their tokens for joesmith:

    >>> def print_subscriptions_with_tokens(subs_with_tokens):
    ...     for subscription, token in subs_with_tokens:
    ...         if token:
    ...             token_text = token.token
    ...         else:
    ...             token_text = "None"
    ...         print(subscription.archive.displayname)
    ...         print(token_text)
    >>> print_subscriptions_with_tokens(
    ...     sub_set.getBySubscriberWithActiveToken(joesmith))
    PPA named p3a for Celso Providelo            test_token
    PPA named p3a for Mark Shuttleworth          None

There's a also related method on IPerson that will return the archive URLs
for the activated tokens.

    >>> for url in joesmith.getArchiveSubscriptionURLs(joesmith):
    ...     print(url)
    http://joesmith:test_token@private-ppa.launchpad.test/cprov/p3a/ubuntu

This method can only be used by someone with launchpad.Edit on the context
IPerson:

    >>> login("no-priv@canonical.com")
    >>> urls = joesmith.getArchiveSubscriptionURLs(no_priv)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized

Deactivated tokens are not included with the returned token for a
subscription:

    >>> login("celso.providelo@canonical.com")
    >>> joesmith_token.deactivate()
    >>> login("joe@example.com")

    >>> print_subscriptions_with_tokens(
    ... sub_set.getBySubscriberWithActiveToken(joesmith))
    PPA named p3a for Celso Providelo            None
    PPA named p3a for Mark Shuttleworth          None


Amending Subscriptions
----------------------

Some of the properties of subscriptions can change after they are created.
To do this, the changer needs to have launchpad.Edit on the subscription,
or be an admin.

Trying to set the properties as the subscribed person will fail:

    >>> from lp.services.database.constants import UTC_NOW
    >>> new_sub.date_expires = UTC_NOW
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Log in as someone with launchpad.Edit and it will work:

    >>> login("celso.providelo@canonical.com")
    >>> new_sub.date_expires = UTC_NOW

Other properties that might get modified later are status and description.
We can also do this as an admin.

    >>> login("admin@canonical.com")
    >>> new_sub.description = u"changed by admin"
    >>> new_sub.status = ArchiveSubscriberStatus.EXPIRED

The subscriber and registrant properties are not editable.

    >>> new_sub.subscriber = cprov
    Traceback (most recent call last):
    ...
    zope.security.interfaces.ForbiddenAttribute: ...

    >>> new_sub.registrant = joesmith
    Traceback (most recent call last):
    ...
    zope.security.interfaces.ForbiddenAttribute: ...


Cancelling subscriptions
------------------------

Subscriptions can only be cancelled after they are created.  The calling user
also needs launchpad.Edit on the subscription, which means either someone with
IArchive launchpad.Append (as for creating new tokens) or an admin.

    >>> login("no-priv@canonical.com")
    >>> new_sub.cancel()
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> login("celso.providelo@canonical.com")
    >>> new_sub.cancel(cprov)

Cancelling sets the date_cancelled value to the current date/time
and cancelled_by to the supplied person.  The status also changes to
CANCELLED.

    >>> new_sub.date_cancelled is not None
    True

    >>> print(new_sub.cancelled_by.name)
    cprov

    >>> print(new_sub.status.name)
    CANCELLED

We can do this as an admin too:

    >>> login("admin@canonical.com")
    >>> new_sub.cancel(cprov)

We can cancel subscriptions in bulk:

    >>> login("celso.providelo@canonical.com")
    >>> subs = [
    ...     cprov_private_ppa.newSubscription(factory.makePerson(), cprov)
    ...     for _ in range(3)]
    >>> sub_set.cancel([subs[0].id, subs[1].id], cprov)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> login("admin@canonical.com")
    >>> sub_set.cancel([subs[0].id, subs[1].id], cprov)
    >>> print(subs[0].status.name)
    CANCELLED
    >>> print(subs[1].status.name)
    CANCELLED
    >>> print(subs[2].status.name)
    CURRENT


Finding all non-active subscribers
----------------------------------

The method getNonActiveSubscribers() facilitates contacting all the people
included in this subscription who do not yet have an active token for the
corresponding archive.

For example, Joe already has an (unactivated) subscription to Mark's PPA
via the cprov_team:

    >>> for subscription in sub_set.getBySubscriber(joesmith):
    ...     print(subscription.archive.displayname)
    ...     print(subscription.description)
    PPA named p3a for Mark Shuttleworth      Access for cprov team

    >>> subscription = sub_set.getBySubscriber(joesmith).first()

So the getNonActiveSubscribers() method for this team subscription will
currently include Joe:

    >>> for person, email in subscription.getNonActiveSubscribers():
    ...     print(person.displayname, email.email)
    Celso Providelo   celso.providelo@canonical.com
    Joe Smith         joe@example.com
    John Smith        john@example.com

But if we create an auth token for joe to the archive (this could be via
a separate subscription), then he will no longer be listed as a non-active
subscriber for this subscription:

    >>> joesmith_token = mark_private_ppa.newAuthToken(joesmith)
    >>> for person, email in subscription.getNonActiveSubscribers():
    ...     print(person.displayname)
    Celso Providelo
    John Smith

If the subscription is just for an individual, getNonActiveSubscribers()
will return a list with the single subscriber as expected:

    >>> login("mark@example.com")
    >>> harrysmith = factory.makePerson(name="harrysmith",
    ...                                 displayname="Harry Smith",
    ...                                 email="harry@example.com")
    >>> subscription = mark_private_ppa.newSubscription(
    ...     harrysmith, mark, description=u"subscription for joesmith")
    >>> for person, email in subscription.getNonActiveSubscribers():
    ...     print(person.displayname)
    Harry Smith

If Harry activates a token for his new subscription then
getNonActiveSubscribers will return an empty result set as he is now
"active".

    >>> harry_token = mark_private_ppa.newAuthToken(harrysmith)
    >>> print(subscription.getNonActiveSubscribers().count())
    0

If the subscription is for a group which itself contains a group, all
indirect members that are not themselves groups are included:

    >>> launchpad_devs = getUtility(IPersonSet).getByName('launchpad')
    >>> ignored = launchpad_devs.addMember(
    ...     team_cprov, mark, force_team_add=True)
    >>> subscription = mark_private_ppa.newSubscription(
    ...     launchpad_devs, mark, description=u"LP team too")
    >>> for person, email in subscription.getNonActiveSubscribers():
    ...     print(person.displayname)
    Celso Providelo
    John Smith
    Foo Bar
