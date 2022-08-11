Subscriptions View
------------------

XXX: bdmurray 2010-09-24 bug=628411 This story is complete until we publish
the link that leads to the +subscriptions page.

Any user can view the direct subscriptions that a person or team has to
blueprints, branches, bugs, merge proposals and questions.

    >>> anon_browser.open('http://launchpad.test/~ubuntu-team/+subscriptions')
    >>> print(anon_browser.title)
    Subscriptions : Bugs : “Ubuntu Team” team

The user can see that the Ubuntu Team does not have any direct bug
subscriptions.

    >>> page_text = extract_text(find_main_content(anon_browser.contents))
    >>> "does not have any direct bug subscriptions" in page_text
    True

To test bug subscriptions we are going to create two products, Affluenza and
Scofflaw, and a user Webster who will be subscribed to bugs about both of
those.

    >>> login('foo.bar@canonical.com')
    >>> scofflaw = factory.makeProduct(name='scofflaw')
    >>> subscriber = factory.makePerson(name='webster')
    >>> bugA = factory.makeBug(target=scofflaw,
    ...     title='Word needs more popularity')
    >>> affluenza = factory.makeProduct(name='affluenza')
    >>> subscriptionA = bugA.subscribe(subscriber, subscriber)
    >>> transaction.commit()
    >>> bugB = factory.makeBug(target=affluenza,
    ...     title='A terrible affliction')
    >>> subscriptionB = bugB.subscribe(subscriber, subscriber)
    >>> logout()

Any user can see Webster's bug subscriptions.  The bug subscriptions table
includes the bug number, title and location.

    >>> anon_browser.open('http://launchpad.test/~webster/+subscriptions')
    >>> print(extract_text(find_tag_by_id(
    ...     anon_browser.contents, 'bug_subscriptions')))
    Summary
    In
    ...
    A terrible affliction
    Affluenza
    ...
    Word needs more popularity
    Scofflaw

The bug subscriptions table also includes an unsubscribe link, if the user has
permission to remove the subscription, for bugs to which the person or team is
subscribed.

Webster can see and manage their direct bug subscriptions using the page too.
They choose to view the bug about Scofflaw.

    >>> login('foo.bar@canonical.com')
    >>> subscriber_browser = setupBrowser(
    ...     auth='Basic %s:test' % subscriber.preferredemail.email)
    >>> logout()
    >>> subscriber_browser.open(
    ...     'http://bugs.launchpad.test/~webster/+subscriptions')
    >>> unsub_link = subscriber_browser.getLink(
    ...     id='unsubscribe-subscriber-%s' % subscriber.id)
    >>> unsub_link.click()
    >>> page_text = extract_text(find_tag_by_id(
    ...     subscriber_browser.contents, 'nonportlets'))
    >>> "unsubscribe me from this bug" in page_text
    True

After viewing the +subscribe page Webster decides that they still want to be
subscribed to the bug.  They click cancel which takes them back to their
+subscription page.

    >>> cancel_link = subscriber_browser.getLink('Cancel')
    >>> cancel_link.click()
    >>> print(subscriber_browser.title)
    Subscriptions : Bugs : Webster

They choose to unsubscribe from the bug about Affluenza.

    >>> subscriber_browser.getLink(url='/affluenza/+bug/%s/+subscribe'
    ...     % bugB.id).click()
    >>> subscriber_browser.getControl(
    ...     "unsubscribe me from this bug").selected = True
    >>> subscriber_browser.getControl("Continue").click()
    >>> print(subscriber_browser.title)
    Subscriptions : Bugs : Webster

Webster can see that the bug about Affluenza is no longer listed in their
direct bug subscriptions.

    >>> subscriber_browser.open(
    ...     'http://bugs.launchpad.test/~webster/+subscriptions')
    >>> print(extract_text(find_tag_by_id(
    ...     subscriber_browser.contents, 'bug_subscriptions')))
    Summary
    In
    ...
    Word needs more popularity
    Scofflaw

Webster adds a bug subscription for a team, team America, of which they are
a member.

    >>> login('foo.bar@canonical.com')
    >>> team = factory.makeTeam(name='america')
    >>> bugC = factory.makeBug(target=scofflaw,
    ...     title="Word came from a contest")
    >>> membership = team.addMember(subscriber, subscriber)
    >>> subscriptionC = bugC.subscribe(team, subscriber)
    >>> logout()

Webster chooses to review the subscriptions for their team America.

    >>> subscriber_browser.open(
    ...     'http://bugs.launchpad.test/~america/+subscriptions')
    >>> print(subscriber_browser.title)
    Subscriptions : Bugs ...

    >>> print(extract_text(find_tag_by_id(
    ...     subscriber_browser.contents, 'bug_subscriptions')))
    Summary
    In
    ...
    Word came from a contest
    Scofflaw

Webster now chooses to unsubscribe team America from the bug about Scofflaw.

    >>> subscriber_browser.getLink(id='unsubscribe-subscriber-%s' %
    ...     team.id).click()
    >>> print(extract_text(find_tags_by_class(
    ...     subscriber_browser.contents, 'value')[0]))
    subscribe me to this bug, or
    unsubscribe America from this bug.

    >>> subscriber_browser.getControl(
    ...     'unsubscribe America from this bug').selected = True
    >>> subscriber_browser.getControl('Continue').click()

    >>> subscriber_browser.open(
    ...     'http://launchpad.test/~america/+subscriptions')
    >>> page_text = extract_text(
    ...     find_main_content(subscriber_browser.contents))
    >>> "does not have any direct bug subscriptions" in page_text
    True


Structural subscriptions
========================

Leading from the subscriptions view is an overview page of all
structural subscriptions.

    >>> admin_browser.open("http://launchpad.test/people/+me/+subscriptions")
    >>> admin_browser.getLink("Structural subscriptions").click()
    >>> admin_browser.url
    'http://launchpad.test/~name16/+structural-subscriptions'
    >>> admin_browser.title
    'Structural subscriptions : Bugs : Foo Bar'

The structures to which the user is subscribed are displayed in a
list. The title of the structure links to the structure itself, and is
followed by a link to edit the subscription.

    >>> subscriptions = find_tag_by_id(
    ...     admin_browser.contents, 'structural-subscriptions')
    >>> for subscription in subscriptions.find_all("li"):
    ...     structure_link, modify_link = subscription.find_all("a")[:2]
    ...     print("%s <%s>" % (
    ...         extract_text(structure_link), structure_link.get("href")))
    ...     print("--> %s" % modify_link.get("href"))
    mozilla-firefox in Ubuntu </ubuntu/+source/mozilla-firefox>
    --> /ubuntu/+source/mozilla-firefox/+subscribe
    pmount in Ubuntu </ubuntu/+source/pmount>
    --> /ubuntu/+source/pmount/+subscribe

The links to modify subscriptions are only shown when the user has
permission to modify those subscriptions.

    >>> subscriber_browser.open(
    ...     "http://launchpad.test/~name16/+structural-subscriptions")
    >>> subscriptions = find_tag_by_id(
    ...     subscriber_browser.contents, 'structural-subscriptions')
    >>> for subscription in subscriptions.find_all("li"):
    ...     structure_link = subscription.find("a")
    ...     print("%s <%s>" % (
    ...         extract_text(structure_link), structure_link.get("href")))
    mozilla-firefox in Ubuntu </ubuntu/+source/mozilla-firefox>
    pmount in Ubuntu </ubuntu/+source/pmount>

The structural subscriptions page links back to the direct
subscriptions page.

    >>> admin_browser.getLink("Direct subscriptions").url
    'http://launchpad.test/~name16/+subscriptions'

A simple explanatory message is shown when the user doesn't have any
structural subscriptions.

    >>> subscriber_browser.open(
    ...     "http://launchpad.test/people/+me/+structural-subscriptions")
    >>> print(extract_text(find_tag_by_id(
    ...     subscriber_browser.contents, "structural-subscriptions")))
    Webster does not have any structural subscriptions.


Creating Bug Filters
~~~~~~~~~~~~~~~~~~~~

Every structural subscription also has a link to create a new bug
subscription filter.

    >>> import re

    >>> def show_create_links(browser):
    ...     subscriptions = find_tag_by_id(
    ...         browser.contents, 'structural-subscriptions')
    ...     for subscription in subscriptions.find_all("li"):
    ...         structure_link = subscription.find("a")
    ...         print(extract_text(structure_link))
    ...         create_text = subscription.find(text=re.compile("Create"))
    ...         if create_text is None:
    ...             print("* No create link.")
    ...         else:
    ...             print("* %s --> %s" % (
    ...                 create_text.strip(),
    ...                 create_text.parent.get("href")))

    >>> admin_browser.open(
    ...     "http://launchpad.test/people/+me/+structural-subscriptions")
    >>> show_create_links(admin_browser)
    mozilla-firefox in Ubuntu
    * Create a new filter --> /ubuntu/.../name16/+new-filter
    pmount in Ubuntu
    * Create a new filter --> /ubuntu/.../name16/+new-filter

If the user does not have the necessary rights to create new bug
filters the "Create" link is not shown.

    >>> subscriber_browser.open(
    ...     "http://launchpad.test/~name16/+structural-subscriptions")
    >>> show_create_links(subscriber_browser)
    mozilla-firefox in Ubuntu
    * No create link.
    pmount in Ubuntu
    * No create link.


Subscriptions with Bug Filters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Products for which a subscription exists bug for which there are no
filters are shown with a message stating that there is no filtering.

    >>> from lp.testing import celebrity_logged_in, person_logged_in

    >>> with celebrity_logged_in("admin"):
    ...     nigel = factory.makePerson(name="nigel", displayname="Nigel")
    >>> with person_logged_in(nigel):
    ...     nigel_subscription = scofflaw.addBugSubscription(nigel, nigel)
    ...     nigel_browser = setupBrowser(
    ...         auth='Basic %s:test' % nigel.preferredemail.email)

    >>> def show_nigels_subscriptions():
    ...     nigel_browser.open(
    ...         "http://launchpad.test/people/"
    ...         "+me/+structural-subscriptions")
    ...     subscriptions = find_tag_by_id(
    ...         nigel_browser.contents, 'structural-subscriptions')
    ...     for subscription in subscriptions.find_all("li"):
    ...         print(extract_text(subscription.p))
    ...         if subscription.dl is not None:
    ...             print(extract_text(subscription.dl))

    >>> show_nigels_subscriptions()
    Bug mail for Nigel about Scofflaw is filtered;
    ...
    This filter allows all mail through.
    There are no filter conditions!
    (edit)

If a bug mail filter exists for a structural subscription it is
displayed immediately after the subscription.

    >>> with person_logged_in(nigel):
    ...     nigel_bug_filter1 = nigel_subscription.bug_filters.one()
    ...     nigel_bug_filter1.description = u"First"
    ...     nigel_bug_filter1.tags = [u"foo"]

    >>> show_nigels_subscriptions()
    Bug mail for Nigel about Scofflaw is filtered; it will be sent
    only if it matches the following filter:
    “First” allows mail through when:
    the bug is tagged with foo
    (edit)

Multiple filters will be shown if they exist, with a slightly modified
message.

    >>> with person_logged_in(nigel):
    ...     nigel_bug_filter2 = nigel_subscription.newBugFilter()
    ...     nigel_bug_filter2.description = u"Second"
    ...     nigel_bug_filter2.tags = [u"bar"]

    >>> show_nigels_subscriptions()
    Bug mail for Nigel about Scofflaw is filtered; it will be sent
    only if it matches one or more of the following filters:
    “First” allows mail through when:
    the bug is tagged with foo
    (edit)
    “Second” allows mail through when:
    the bug is tagged with bar
    (edit)
