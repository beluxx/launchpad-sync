Helper Functions
================

A quick helper function to list the subscribed people.

    >>> def print_subscribers(contents):
    ...     subscriptions = find_tags_by_class(
    ...         contents, 'branch-subscribers')[0]
    ...     if subscriptions == None:
    ...         print(subscriptions)
    ...         return
    ...     for subscriber in subscriptions.find_all('div'):
    ...         print(extract_text(subscriber.decode_contents()))

Another to print the informational message.

    >>> def print_informational_message(contents):
    ...     message = find_tags_by_class(contents, 'informational message')
    ...     if message:
    ...         print(extract_text(message[0]))


Subscribing to Branches
=======================

In order to subscribe to a branch, the user must be logged in.

    >>> anon_browser.open(
    ...     'http://code.launchpad.test/~name12/gnome-terminal/main')
    >>> anon_browser.getLink('Subscribe')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

Let us subscribe to one of the branches. First, let's make sure we can see the
link "Subscribe" from a branch's page.

    >>> browser = setupBrowser(auth='Basic no-priv@canonical.com:test')
    >>> browser.open('http://code.launchpad.test/~name12/gnome-terminal/main')

Initially there should be no subscribers.

    >>> print_subscribers(browser.contents)
    No subscribers.
    >>> browser.getLink('Subscribe').click()

At this stage the defaults that are set for subscriptions
are fairly arbitrary, so we'll explicitly choose the values.

    >>> browser.getControl('Notification Level').displayValue = [
    ...     'Branch attribute notifications only']
    >>> browser.getControl('Generated Diff Size Limit').displayValue = [
    ...     '1000 lines']

Now, post the subscription form. We should see a message that we have
just subscribed.

    >>> browser.getControl('Subscribe').click()
    >>> print_informational_message(browser.contents)
    You have subscribed to this branch with:
    Only send notifications for branch attribute changes such
    as name, description and whiteboard.
    Send email about any code review activity for this branch.

There should be only one person subscribed to the branch now.

    >>> print_subscribers(browser.contents)
    No Privileges Person

Now, press the back button, and post the subscription form again. We
should see a message that we are already subscribed.

    >>> browser.goBack(count=1)
    >>> browser.getControl('Subscribe').click()
    >>> print_informational_message(browser.contents)
    You are already subscribed to this branch.

Now the subscription link should say "Edit subscription" in the actions
menu.

    >>> browser.getLink('Edit your subscription').click()

Let's change our subscription to getting emails for modifications, and diffs,
and limit our diffs to 5000 lines.

    >>> browser.getControl('Notification Level').displayValue = [
    ...     'Branch attribute and revision notifications']
    >>> browser.getControl('Generated Diff Size Limit').displayValue = [
    ...     '5000 lines']
    >>> browser.getControl('Change').click()

Now we should be taken back to the main branch page, with a nice
informational message for us to see.

    >>> print_informational_message(browser.contents)
    Subscription updated to:
    Send notifications for both branch attribute updates
    and new revisions added to the branch.
    Limit the generated diff to 5000 lines.
    Send email about any code review activity for this branch.

    >>> print_subscribers(browser.contents)
    No Privileges Person

The page to edit a person's subscription also allows the user to
unsubscribe.

    >>> browser.getLink('Edit your subscription').click()
    >>> form_url = browser.url
    >>> browser.getControl('Unsubscribe').click()

The user is taken back to the branch details page, and a message is
shown to the user.

    >>> print_informational_message(browser.contents)
    You have unsubscribed from this branch.
    >>> print_subscribers(browser.contents)
    No subscribers.

Clicking the back button and then clicking on either Change or
Unsubscribe will give a message that we are not subscribed.

    >>> from urllib.parse import urlencode
    >>> browser.addHeader('Referer', 'https://launchpad.test/')
    >>> browser.open(
    ...     form_url,
    ...     data=urlencode({'field.actions.change': 'Change'}))
    >>> print_informational_message(browser.contents)
    You are not subscribed to this branch.
    >>> browser.open(
    ...     form_url,
    ...     data=urlencode({'field.actions.unsubscribe': 'Unsubscribe'}))
    >>> print_informational_message(browser.contents)
    You are not subscribed to this branch.


Subscribing someone else
========================

The 'Subscribe' action listed for branches is for subscribing the logged
in user.  In order to be able to subscribe teams to branches there needs
to be an different way to do this.  The 'Subscribe someone else' action
can be used to subscribe individuals or teams.

You need to be logged in to see the link.

    >>> anon_browser.open(
    ...     'http://code.launchpad.test/~name12/gnome-terminal/main')
    >>> anon_browser.getLink('Subscribe someone else')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

Any logged in user is able to subscribe others to a branch.

    >>> browser.open('http://code.launchpad.test/~name12/gnome-terminal/main')
    >>> browser.getLink('Subscribe someone else').click()

The process of subscribing others is the same as subscribing the
currently logged in user with the addition of the user needing to
specify the person to subscribe.  The person field is required.

    >>> browser.getControl('Notification Level').displayValue = [
    ...     'Branch attribute and revision notifications']
    >>> browser.getControl('Generated Diff Size Limit').displayValue = [
    ...     '5000 lines']
    >>> browser.getControl('Subscribe').click()

    >>> print_feedback_messages(browser.contents)
    There is 1 error.
    Required input is missing.

    >>> browser.getControl('Person').value = 'mark'
    >>> browser.getControl('Subscribe').click()

    >>> print_informational_message(browser.contents)
    Mark Shuttleworth has been subscribed to this branch with:
    Send notifications for both branch attribute updates
    and new revisions added to the branch.
    Limit the generated diff to 5000 lines.
    Send email about any code review activity for this branch.

    >>> print_subscribers(browser.contents)
    Mark Shuttleworth

Subscribing a team is as simple as putting in the team name.

    >>> browser.getLink('Subscribe someone else').click()
    >>> browser.getControl('Notification Level').displayValue = [
    ...     'Branch attribute and revision notifications']
    >>> browser.getControl('Generated Diff Size Limit').displayValue = [
    ...     '1000 lines']
    >>> browser.getControl('Person').value = 'landscape-developers'
    >>> browser.getControl('Subscribe').click()

The user does not have to be in the team to subscribe them.

    >>> print_informational_message(browser.contents)
    Landscape Developers has been subscribed to this branch with:
    Send notifications for both branch attribute updates
    and new revisions added to the branch.
    Limit the generated diff to 1000 lines.
    Send email about any code review activity for this branch.

    >>> anon_browser.open(
    ...     'http://code.launchpad.test/~name12/gnome-terminal/main')
    >>> print_subscribers(anon_browser.contents)
    Landscape Developers
    Mark Shuttleworth

Launchpad administrators can edit anyones branch subsription.

    >>> admin_browser.open(
    ...     'http://code.launchpad.test/~name12/gnome-terminal/main')
    >>> print_subscribers(admin_browser.contents)
    Landscape Developers
    Mark Shuttleworth


Editing a team subscription
===========================

In order to edit a team subscription the logged in user needs to be a member
of the team that is subscribed, or must the person who subscribed the team
to the branch.  There is a link shown in the subscriptions portlet to edit the
subscription of a team that the logged in user is a member of.

XXX: thumper 2007-06-11, bug 110953
There should be a central user subscriptions page.  This could then
be used to traverse to the branch subscriptions instead of through
the branch itself.

    >>> browser.open(
    ...     'http://code.launchpad.test/~name12/gnome-terminal/main')
    >>> print_subscribers(browser.contents)
    Landscape Developers
    Mark Shuttleworth

    >>> browser.getLink(url='+subscription/landscape').click()
    >>> main_content = find_main_content(browser.contents)
    >>> print(extract_text(main_content.h1))
    Edit subscription to branch for Landscape Developers

From this page the branch subscription can be altered...

    >>> browser.getControl('Notification Level').displayValue = [
    ...     'No email']
    >>> browser.getControl('Change').click()

... or unsubscribed from.

    >>> browser.getLink(url='+subscription/landscape').click()
    >>> browser.getControl('Unsubscribe').click()
    >>> print_informational_message(browser.contents)
    Landscape Developers has been unsubscribed from this branch.
    >>> print_subscribers(browser.contents)
    Mark Shuttleworth


Private teams in public subscriptions
=====================================

If a private team is subscribed to a public branch, it is visible
to everyone.

    >>> from lp.testing import login, logout
    >>> from lp.registry.interfaces.person import PersonVisibility
    >>> from lp.code.enums import (
    ...     BranchSubscriptionNotificationLevel,
    ...     CodeReviewNotificationLevel)

    >>> login('admin@canonical.com')
    >>> private_team = factory.makeTeam(
    ...     name='shh', displayname='Shh',
    ...     visibility=PersonVisibility.PRIVATE)
    >>> member = factory.makePerson(email='shh@example.com')
    >>> ignored = private_team.addMember(member, private_team.teamowner)
    >>> owner = factory.makePerson(name='branch-owner')
    >>> branch = factory.makeAnyBranch(owner=owner)
    >>> ignored = branch.subscribe(
    ...     private_team, BranchSubscriptionNotificationLevel.NOEMAIL, None,
    ...     CodeReviewNotificationLevel.NOEMAIL, private_team.teamowner)
    >>> url = canonical_url(branch)
    >>> logout()

No-priv is not a member of the private team, but they can see the team's
display name in the subscriber list.

    >>> browser.open(url)
    >>> print_subscribers(browser.contents)
    Branch-owner
    Shh
