PPA Subscriptions
=================

Note: This file contains all the pagetests for functionality that is not
part of the stories in xx-private-ppa-subscription-stories.rst.

Managing Archive subscriptions
------------------------------

Public PPAs do not have an option for managing subscriptions:

    >>> cprov_browser = setupBrowser(
    ...     auth="Basic celso.providelo@canonical.com:test"
    ... )
    >>> cprov_browser.open("http://launchpad.test/~cprov/+archive/ppa")
    >>> cprov_browser.getLink("Manage subscriptions")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

Similarly, trying to access the subscriptions page directly will simply
redirect back to the PPA page with a feedback message:

    >>> cprov_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+subscriptions"
    ... )

    >>> print(cprov_browser.url)
    http://launchpad.test/~cprov/+archive/ubuntu/ppa

    >>> print_feedback_messages(cprov_browser.contents)
    Only private archives can have subscribers.

Setup private PPAs for both Celso and Mark:

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login("admin@canonical.com")
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> cprov_private_ppa = factory.makeArchive(
    ...     owner=cprov, name="p3a", distribution=ubuntu, private=True
    ... )
    >>> mark_private_ppa = factory.makeArchive(
    ...     owner=mark, name="p3a", distribution=ubuntu, private=True
    ... )
    >>> logout()

The PPA page includes a link to manage subscriptions:

    >>> cprov_browser.open("http://launchpad.test/~cprov/+archive/p3a")
    >>> cprov_browser.getLink("Manage access").click()

Initially there are no subscriptions for a newly privatized PPA (although,
this may need to change, to add the owner/team). A heading is displayed
with a message:

    >>> main_content = find_main_content(cprov_browser.contents)
    >>> print(extract_text(main_content.find("h1")))
    Manage access to PPA named p3a for Celso Providelo

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(cprov_browser.contents, "no-subscribers")
    ...     )
    ... )
    No one has access to install software from this PPA.

Create two new users that can be subscribed to archives, and a team:

    >>> login("foo.bar@canonical.com")
    >>> joesmith = factory.makePerson(
    ...     name="joesmith", displayname="Joe Smith", email="joe@example.com"
    ... )
    >>> teamjoe = factory.makeTeam(
    ...     owner=joesmith, displayname="Team Joe", name="teamjoe"
    ... )
    >>> bradsmith = factory.makePerson(
    ...     name="bradsmith",
    ...     displayname="Brad Smith",
    ...     email="brad@example.com",
    ... )
    >>> logout()

People and teams can be subscribed by entering their details into the
displayed form:

    >>> cprov_browser.getControl(name="field.subscriber").value = "teamjoe"
    >>> cprov_browser.getControl(name="field.description").value = (
    ...     "Joes friends are my friends"
    ... )
    >>> cprov_browser.getControl(name="field.actions.add").click()
    >>> cprov_browser.getControl(name="field.subscriber").value = "bradsmith"
    >>> cprov_browser.getControl(name="field.date_expires").value = (
    ...     "2200-08-01"
    ... )
    >>> cprov_browser.getControl(name="field.description").value = (
    ...     "Brad can access for a while."
    ... )
    >>> cprov_browser.getControl(name="field.actions.add").click()

Once the subscription has been added, it will display in the table:

    >>> for row in find_tags_by_class(
    ...     cprov_browser.contents, "archive_subscriber_row"
    ... ):
    ...     print(extract_text(row))
    Name                Expires     Comment
    Brad Smith          2200-08-01  Brad can access for a while.  Edit/Cancel
    Team Joe                        Joes friends are my friends   Edit/Cancel


Managing a persons' Archive subscriptions
-----------------------------------------

The title of a persons archive subscriptions is displayed as the main
heading:

    >>> cprov_browser.open("/~cprov/+archivesubscriptions")
    >>> print(find_main_content(cprov_browser.contents))
    <div...
    <h1>Private PPA access</h1>...

A person who is not subscribed to any archives will see an appropriate
explanation if they try to view their archive subscriptions:

    >>> explanation = find_main_content(cprov_browser.contents).find("p")
    >>> print(extract_text(explanation))
    You do not have any current subscriptions to private archives...

First, create a subscription for Joe Smith's team to mark's archive
so that Joe has multiple subscriptions:

    >>> mark_browser = setupBrowser(auth="Basic mark@example.com:test")
    >>> mark_browser.open(
    ...     "http://launchpad.test/~mark/+archive/p3a/+subscriptions"
    ... )
    >>> mark_browser.getControl(name="field.subscriber").value = "joesmith"
    >>> mark_browser.getControl(name="field.description").value = (
    ...     "Joe is also my friend"
    ... )
    >>> mark_browser.getControl(name="field.actions.add").click()

A person who is subscribed to multiple archives will see all the archives
listed in the current subscriptions area:

    >>> joe_browser = setupBrowser(auth="Basic joe@example.com:test")
    >>> joe_browser.open(
    ...     "http://launchpad.test/~joesmith/+archivesubscriptions"
    ... )
    >>> for row in find_tags_by_class(
    ...     joe_browser.contents, "archive-subscription-row"
    ... ):
    ...     print(extract_text(row))
    Archive                          Owner
    PPA named... (ppa:mark/p3a)      Mark Shuttleworth       View
    PPA named... (ppa:cprov/p3a)     Celso Providelo         View

It is not possible to traverse to a team's archive subscriptions to
create tokens.

    >>> joe_browser.open(
    ...     "http://launchpad.test/~teamjoe/+archivesubscriptions"
    ... )
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...


Confirming a subscription
-------------------------

When a person clicks on the view button, the subscription is confirmed
automatically (creating a token for the user) and they are taken to a page
displaying their subscription.

    >>> joe_browser.open(
    ...     "http://launchpad.test/~joesmith/+archivesubscriptions"
    ... )
    >>> joe_browser.getControl(name="activate", index=0).click()
    >>> sources_list = find_tag_by_id(joe_browser.contents, "sources_list")
    >>> print(extract_text(sources_list))
    Custom sources.list entries
    ...
    deb http://joesmith:...@private-ppa.launchpad.test/mark/p3a/ubuntu
        hoary main #Personal access of Joe Smith (joesmith)
        to PPA named p3a for Mark Shuttleworth
    deb-src http://joesmith:...@private-ppa.launchpad.test/mark/p3a/ubuntu
        hoary main #Personal access of Joe Smith (joesmith)
        to PPA named p3a for Mark Shuttleworth

This page will include information about the signing key, if the archive
has a signing key:

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.registry.interfaces.gpg import IGPGKeySet
    >>> login("foo.bar@canonical.com")
    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> a_key = getUtility(IGPGKeySet).getByFingerprint(
    ...     "ABCDEF0123456789ABCDDCBA0000111112345678"
    ... )
    >>> removeSecurityProxy(mark_private_ppa).signing_key_fingerprint = (
    ...     a_key.fingerprint
    ... )
    >>> removeSecurityProxy(mark_private_ppa).signing_key_owner = a_key.owner
    >>> logout()

    >>> joe_browser.reload()
    >>> sources_list = find_tag_by_id(joe_browser.contents, "sources_list")
    >>> print(extract_text(sources_list))
    Custom sources.list entries
    ...
    deb http://joesmith:...@private-ppa.launchpad.test/mark/p3a/ubuntu
        hoary main #Personal access of Joe Smith (joesmith)
        to PPA named p3a for Mark Shuttleworth
    deb-src http://joesmith:...@private-ppa.launchpad.test/mark/p3a/ubuntu
        hoary main #Personal access of Joe Smith (joesmith)
        to PPA named p3a for Mark Shuttleworth
    This repository is signed ...

Once a person has activated a subscription, being subscribed again via
another team does not lead to duplicate entries on the person's
subscriptions page.

    >>> mark_browser.open("http://launchpad.test/~mark/+archive/p3a")
    >>> mark_browser.getLink("Manage access").click()
    >>> mark_browser.getControl(name="field.subscriber").value = "teamjoe"
    >>> mark_browser.getControl(name="field.description").value = (
    ...     "Joe's friends are my friends."
    ... )
    >>> mark_browser.getControl(name="field.actions.add").click()
    >>> joe_browser.open(
    ...     "http://launchpad.test/~joesmith/+archivesubscriptions"
    ... )
    >>> rows = find_tags_by_class(
    ...     joe_browser.contents, "archive-subscription-row"
    ... )
    >>> for row in rows:
    ...     print(extract_text(row))
    ...
    Archive                                            Owner
    PPA named p3a for Mark Shuttleworth (ppa:mark/p3a) Mark Shuttleworth View
    PPA named p3a for Celso Providelo (ppa:cprov/p3a)  Celso Providelo   View

Attempting to browse directly to a subscription
-----------------------------------------------

    >>> joe_browser.open(
    ...     "http://launchpad.test/~joesmith/+archivesubscriptions/foo"
    ... )
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...
