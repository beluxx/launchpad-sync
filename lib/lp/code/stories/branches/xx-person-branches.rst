Person Views of Branch Lists
============================

There are several views of the branches related to a person.

First, check that the condensed branch listing page works:

    >>> browser = setupBrowser(auth='Basic test@canonical.com:test')
    >>> browser.open('http://code.launchpad.test/~name12')
    >>> print(browser.title)
    Code : Sample Person


Default view for a person on code root site
-------------------------------------------

The default view for a person on the code root site is the normal branch
listing view for that person.

If a person does not have any related branches, we print an informative
message.

    >>> browser.open('http://code.launchpad.test/~kinnison')
    >>> print(extract_text(
    ...     find_tag_by_id(browser.contents, 'no-branch-message')))
    There are no branches related to Daniel Silverstone in Launchpad today.


Junk branches
-------------

On the user's own code page, they will see directions on pushing a branch.

    >>> browser.open('http://code.launchpad.test/~name12')
    >>> print(extract_text(
    ...     find_tag_by_id(browser.contents, 'junk-branch-directions')))
    You can push (upload) personal branches
    (those not related to a project) with the following command:
    bzr push lp:~name12/+junk/BRANCHNAME


Owned Branches
--------------

A person's owned branches are shown on their code application overview page.

    >>> browser.open('http://code.launchpad.test/~name12')
    >>> table = find_tag_by_id(browser.contents, 'branchtable')
    >>> for row in table.tbody.find_all('tr'):
    ...     print(extract_text(row))
    lp://dev/~name12/landscape/feature-x      Development
    ...


Registered Branches
-------------------

There is also a filter for registered branches.

    >>> browser.open('http://code.launchpad.test/~name12')
    >>> browser.getControl(name='field.category').displayValue = [
    ...     'Registered']
    >>> browser.getControl('Filter').click()
    >>> print(browser.title)
    Code : Sample Person
    >>> table = find_tag_by_id(browser.contents, 'branchtable')
    >>> for row in table.tbody.find_all('tr'):
    ...     print(extract_text(row))
    lp://dev/~name12/landscape/feature-x      Development
    ...


Subscribed branches
-------------------

From the persons main listing page, there is also a filter for
subscribed branches.

    >>> browser.open('http://code.launchpad.test/~name12')
    >>> browser.getControl(name='field.category').displayValue = [
    ...     'Subscribed']
    >>> browser.getControl('Filter').click()
    >>> print(browser.title)
    Code : Sample Person
    >>> table = find_tag_by_id(browser.contents, 'branchtable')
    >>> for row in table.tbody.find_all('tr'):
    ...     print(extract_text(row))
    lp://dev/~launchpad/gnome-terminal/launchpad  Development           ...
    lp://dev/~name12/+junk/junk.dev               Experimental  ...


Person branch summary
---------------------

Each of the person branch listing pages has a brief summary at the
top of the page with some branch counts.  These also contain the links
to the registered, owned and subscribed listing pages for a person.

Firstly lets set up a new person with no branches.

    >>> login(ANONYMOUS)
    >>> eric = factory.makePerson(
    ...     name="eric", email="eric@example.com",
    ...     displayname="Eric the Viking")
    >>> b1 = factory.makeAnyBranch(owner=eric)
    >>> logout()

The summary is shown.

    >>> eric_browser = setupBrowser(auth="Basic eric@example.com:test")
    >>> eric_browser.open('http://code.launchpad.test/~eric')
    >>> print_tag_with_id(eric_browser.contents, 'portlet-person-codesummary')
    Branches
    Active reviews
    Source package recipes
    Snap packages

Now we'll create another branch, and unsubscribe the owner from it.

    >>> login(ANONYMOUS)
    >>> b2 = factory.makeAnyBranch(owner=eric)
    >>> ignored = b2.unsubscribe(eric, eric)
    >>> logout()

    >>> eric_browser.open('http://code.launchpad.test/~eric')
    >>> print_tag_with_id(
    ...     eric_browser.contents, 'portlet-person-codesummary')
    Branches
    Active reviews
    Source package recipes
    Snap packages
