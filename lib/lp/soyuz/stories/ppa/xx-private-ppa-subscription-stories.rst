PPA Subscription Stories
========================

The owner or admin of a private PPA can add subscribers - people
or teams - to the private archive. This will enable subscribers to obtain
a custom sources.list entry and access the repository.

The owner or admin of a private archive can also edit or cancel
subscribers related to the archive.

Setup Helpers
-------------

Just so the definition of these helpers doesn't get in the way of the
story text, define them here.

First create a helper function for printing the archive subscriptions
of a person:

    >>> def print_subscriptions_for_person(contents):
    ...     subscriptions = find_tags_by_class(
    ...         contents, "archive-subscription-row"
    ...     )
    ...     for subscription in subscriptions:
    ...         print(extract_text(subscription))
    ...

Story: An archive owner can add a subscription for a private archive
--------------------------------------------------------------------

 * As a software developer who plans to release some private software
 * I want to add certain users or teams as subscribers of my PPA
 * So that they can download my software.

Scenario 1: A user is added as a subscriber
...........................................

Given a private PPA for Celso,

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login("admin@canonical.com")
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> private_ppa = factory.makeArchive(
    ...     owner=cprov, name="p3a", distribution=ubuntu, private=True
    ... )
    >>> logout()

and a browser for Celso currently navigated to the Manage Subscriptions page,

    >>> cprov_browser = setupBrowser(
    ...     auth="Basic celso.providelo@canonical.com:test"
    ... )
    >>> cprov_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/p3a/+subscriptions"
    ... )

and a client of Celso's who has a launchpad name of 'joesmith'

    >>> login("foo.bar@canonical.com")
    >>> client = factory.makePerson(
    ...     name="joesmith", displayname="Joe Smith", email="joe@example.com"
    ... )
    >>> logout()

When Celso fills in the form with 'joesmith' as the subscriber, a blank
subscription expiry, a description of "Joe is my friend" and clicks on the
"Add subscriber" button,

    >>> cprov_browser.getControl(name="field.subscriber").value = "joesmith"
    >>> cprov_browser.getControl(
    ...     name="field.description"
    ... ).value = "Joe is my friend"
    >>> cprov_browser.getControl(name="field.actions.add").click()

then he is redirected to the subscribers page and the new subscription
is displayed with a notification about the new subscriber.

Create a helper function to print subscriptions:
    >>> def print_archive_subscriptions(contents):
    ...     subscriptions = find_tags_by_class(
    ...         contents, "archive_subscriber_row"
    ...     )
    ...     for subscription in subscriptions:
    ...         print(extract_text(subscription))
    ...

    >>> print_archive_subscriptions(cprov_browser.contents)
    Name                Expires     Comment
    Joe Smith                       Joe is my friend    Edit/Cancel

    >>> print_feedback_messages(cprov_browser.contents)
    You have granted access for Joe Smith to install software from
    PPA named p3a for Celso Providelo. Joe Smith will be notified of the
    access via email.


Scenario 2: A team is added as a subscriber
...........................................

Given a private PPA for Celso and a browser for Celso currently navigated
to the Manage Subscriptions page, when Celso fills in the form with the
'launchpad' team as the subscriber, an expiry date of '2200-08-01',
a description of "Launchpad developer access." and clicks on the
"Add subscriber" button,

    >>> cprov_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/p3a/+subscriptions"
    ... )
    >>> cprov_browser.getControl(name="field.subscriber").value = "launchpad"
    >>> cprov_browser.getControl(
    ...     name="field.date_expires"
    ... ).value = "2200-08-01"
    >>> cprov_browser.getControl(
    ...     name="field.description"
    ... ).value = "Launchpad developer access."
    >>> cprov_browser.getControl(name="field.actions.add").click()

then Celso is redirected to the subscribers page, the new subscription
for the launchpad team is displayed as well as a notification about the
new subscriber.

    >>> print_archive_subscriptions(cprov_browser.contents)
    Name                    Expires       Comment
    Joe Smith                             Joe is my friend    ...
    Launchpad Developers    2200-08-01    Launchpad developer access.
    ...

    >>> print_feedback_messages(cprov_browser.contents)
    You have granted access for Launchpad Developers to install software
    from PPA named p3a for Celso Providelo. Members of Launchpad Developers
    will be notified of the access via email.

Story 2: An owner edits a subscription for their private archive
----------------------------------------------------------------

 * As a software developer who has released some private software
 * I want to edit subscriptions to my private PPA
 * So that I can adjust who can download my software.

Scenario 1: Adjusting the details of a subscription
...................................................

Given a private PPA for Celso, a subscription to Celso's private PPA
for the Launchpad Developers team and a browser for Celso currently
navigated to the Manage Subscriptions page,

    >>> cprov_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/p3a/+subscriptions"
    ... )

when Celso clicks 'Edit/Cancel' for the Launchpad Developers subscription,
modifies the description field and clicks Update,

    >>> cprov_browser.getLink(
    ...     url="/~cprov/+archive/ubuntu/p3a/+subscriptions/launchpad/+edit",
    ... ).click()
    >>> cprov_browser.getControl(
    ...     name="field.description"
    ... ).value = "a different description"
    >>> cprov_browser.getControl(name="field.actions.update").click()

then the browser is redirected back to the subscriptions page, the updated
subscription for the launchpad team is displayed as well as a notification
about the update.

    >>> print(cprov_browser.url)
    http://launchpad.test/~cprov/+archive/ubuntu/p3a/+subscriptions
    >>> print_archive_subscriptions(cprov_browser.contents)
    Name                    Expires       Comment
    Joe Smith                             Joe is my friend    ...
    Launchpad Developers    2200-08-01    a different description
    ...
    >>> print_feedback_messages(cprov_browser.contents)
    The access for Launchpad Developers has been updated.

Scenario 2: Canceling a subscription
....................................

Given a private PPA for Celso, a subscription to Celso's private PPA for
the Launchpad Developers team and a browser for Celso currently navigated
to the Manage Subscriptions page,

    >>> cprov_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/p3a/+subscriptions"
    ... )

when Celso clicks 'Edit/Cancel' for the Launchpad Developers subscription
and clicks Cancel,

    >>> cprov_browser.getLink(
    ...     url="/~cprov/+archive/ubuntu/p3a/+subscriptions/launchpad/+edit",
    ... ).click()
    >>> cprov_browser.getControl(name="field.actions.cancel").click()

then the browser is redirected back to the subscriptions page, the canceled
subscription is no longer displayed and a notification about the
cancellation is displayed.

    >>> print(cprov_browser.url)
    http://launchpad.test/~cprov/+archive/ubuntu/p3a/+subscriptions
    >>> print_archive_subscriptions(cprov_browser.contents)
    Name                    Expires       Comment
    Joe Smith                             Joe is my friend    Edit/Cancel

    >>> print_feedback_messages(cprov_browser.contents)
    You have revoked Launchpad Developers's access to PPA
    named p3a for Celso Providelo.


Story 3: A subscriber activates a subscription
----------------------------------------------

 * As a user of Celso's software,
 * I want to obtain a private sources.list entry
 * So that I can download and get updates for the software in
   Celso's private PPA.

Scenario 1: A user activates a personal subscription
....................................................

Given a subscription for Celso's private PPA for Joe Smith, when
Joe visits his profile and clicks 'View your private PPA subscriptions'
then he'll see a list of his current subscriptions.

    >>> joe_browser = setupBrowser(auth="Basic joe@example.com:test")
    >>> joe_browser.open("http://launchpad.test/~joesmith")
    >>> joe_browser.getLink("View your private PPA subscriptions").click()
    >>> print_subscriptions_for_person(joe_browser.contents)
    Archive        Owner
    PPA named ...  Celso Providelo  View

When Joe clicks on the View button for Celso's PPA then the
details of the subscription are displayed with the newly created
access details.

    >>> joe_browser.getControl(name="activate").click()
    >>> sources_list = find_tag_by_id(joe_browser.contents, "sources_list")
    >>> print(extract_text(sources_list))
    Custom sources.list entries
    ...
    deb http://joesmith:...@private-ppa.launchpad.test/cprov/p3a/ubuntu
        hoary main #Personal access of Joe Smith (joesmith)
        to PPA named p3a for Celso Providelo
    deb-src http://joesmith:...@private-ppa.launchpad.test/cprov/p3a/ubuntu
        hoary main #Personal access of Joe Smith (joesmith)
        to PPA named p3a for Celso Providelo

When Joe navigates back to his current archive subscriptions then the list of
subscriptions reflects the confirmed subscription, providing a normal
link to view the details.

    >>> joe_browser.open(
    ...     "http://launchpad.test/~joesmith/+archivesubscriptions"
    ... )
    >>> print_subscriptions_for_person(joe_browser.contents)
    Archive        Owner
    PPA named ...  Celso Providelo  View

    >>> joe_browser.getLink("View").click()
    >>> print(extract_text(joe_browser.contents))
    Access to PPA named p3a for Celso Providelo...

Scenario 2: A user re-generates the token for a subscription
............................................................

Given an activated subscription to Celso's private PPA, when Joe visits
his private archive subscriptions page and clicks on the 'view' link to view
a subscription then information regarding the generation of a new personal
subscription is displayed.

    >>> joe_browser.open(
    ...     "http://launchpad.test/~joesmith/+archivesubscriptions"
    ... )
    >>> joe_browser.getLink("View").click()
    >>> regeneration_info = find_tag_by_id(
    ...     joe_browser.contents, "regenerate_token"
    ... )
    >>> print(extract_text(regeneration_info))
    Reset password
    If you believe...

When Joe clicks on the 'Generate new personal subscription' link then
the page is redisplayed with new sources.list entries and a notification.

    >>> joe_browser.getControl(name="regenerate_btn").click()
    >>> print_feedback_messages(joe_browser.contents)
    Launchpad has generated the new password you requested for your
    access to the archive PPA named p3a for Celso Providelo. Please
    follow the instructions below to update your custom "sources.list".


Scenario 3: A user activates a team subscription
................................................

Given a subscription for Celso's private PPA for the Launchpad Team and
a user Mark who is a member of the Launchpad team,

    >>> login("celso.providelo@canonical.com")
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> launchpad = getUtility(IPersonSet).getByName("launchpad")
    >>> ignore = private_ppa.newSubscription(launchpad, cprov)
    >>> login("foo.bar@canonical.com")
    >>> foobar = getUtility(IPersonSet).getByName("name16")
    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> ignored = launchpad.addMember(mark, foobar)
    >>> import transaction
    >>> transaction.commit()
    >>> logout()

When Mark, a member of the Launchpad team, visits his profile and clicks
'View your private PPA subscriptions', then he'll see a list of his current
subscriptions.

    >>> mark_browser = setupBrowser(auth="Basic mark@example.com:test")
    >>> mark_browser.open("http://launchpad.test/~mark")

    >>> mark_browser.getLink("View your private PPA subscriptions").click()
    >>> print_subscriptions_for_person(mark_browser.contents)
    Archive        Owner
    PPA named ...  Celso Providelo  View

When Mark clicks on the view button, then he is taken to the page for
his personal subscription for Celso's private PPA and the newly-created
access details are displayed.

    >>> mark_browser.getControl(name="activate").click()
    >>> sources_list = find_tag_by_id(mark_browser.contents, "sources_list")
    >>> print(extract_text(sources_list))
    Custom sources.list entries
    ...
    deb http://mark:...@private-ppa.launchpad.test/cprov/p3a/ubuntu
        hoary main #Personal access of
        Mark Shuttleworth (mark) to PPA named p3a for Celso Providelo
    deb-src http://mark:...@private-ppa.launchpad.test/cprov/p3a/ubuntu
        hoary main #Personal access of
        Mark Shuttleworth (mark) to PPA named p3a for Celso Providelo

When Mark navigates back to his current archive subscriptions then the list of
subscriptions reflects the confirmed subscription, providing a normal
link to view the details.

    >>> mark_browser.open("http://launchpad.test/~mark/+archivesubscriptions")
    >>> print_subscriptions_for_person(mark_browser.contents)
    Archive        Owner
    PPA named ...  Celso Providelo  View

    >>> mark_browser.getLink("View").click()
    >>> print(extract_text(mark_browser.contents))
    Access to PPA named p3a for Celso Providelo...


Story 4: A user's subscription expires or is cancelled
------------------------------------------------------

 * As a user of Celso's software
 * I want to know (eventually, be notified) when my subscription expires
 * So that I understand why I can no longer download Celso's software

Scenario 1: Accessing details for an expired subscription
.........................................................

Given an expired subscription for Celso's private PPA

When Andrew visits his subscriptions
Then the page clearly identifies the subscription as no longer valid
And there is no entry in the sources.list for the expired subscription.

Scenario 2: Accessing details for a cancelled subscription
..........................................................

Given a cancelled subscription for Celso's private PPA

When Andrew visits his subscriptions
Then the page clearly identifies the subscription as no longer valid
And there is no entry in the sources.list for the expired subscription.
