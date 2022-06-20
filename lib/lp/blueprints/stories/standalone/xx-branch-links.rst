Creating Specification Branch Links
===================================

Blueprints (aka Specifications) and branches can be linked to show
intention of the branch to implement the blueprint.

Blueprints and branches can be linked together from either the
default blueprint page or the default branch page.

From the branch page
--------------------

There is a "Link to a blueprint" item in the actions menu that is visible
to everybody but which links to a page restricted with the
launchpad.AnyPerson permission.

If the user is not logged in, they will be asked to log in.

    >>> anon_browser.open(
    ...     'http://code.launchpad.test/~name12/firefox/main')
    >>> anon_browser.getLink('Link to a blueprint').click()
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: (...launchpad.AnyPerson')

    >>> def printSpecBranchLinks(browser):
    ...     tags = find_tags_by_class(browser.contents, 'spec-branch-summary')
    ...     if len(tags) == 0:
    ...         print('No spec branch links')
    ...     else:
    ...         for tag in tags:
    ...             print(extract_text(tag))

When linking from a branch to a spec, a select widget is used as a
method for selecting values.  This widget is populated with the
product's blueprints.

    >>> browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> browser.open(
    ...     'http://code.launchpad.test/~name12/firefox/main')
    >>> printSpecBranchLinks(browser)
    No spec branch links

    >>> browser.getLink('Link to a blueprint').click()

    >>> browser.getControl('Blueprint').value = ['2']
    >>> browser.getControl('Continue').click()
    >>> printSpecBranchLinks(browser)
    Support &lt;canvas&gt; Objects
    (Medium)
    Edit


From the blueprint page
-----------------------

The main blueprint page has an action 'Link a related branch'.  This allows
the user to specify a branch to link to the blueprint.

    >>> browser.open(
    ...     'http://blueprints.launchpad.test/firefox/+spec/svg-support')
    >>> browser.getLink('Link a related branch').click()

There is a link back to the blueprint page, in case you change your mind.

    >>> back_link = browser.getLink('Support Native SVG Objects')
    >>> back_link.url
    'http://blueprints.launchpad.test/firefox/+spec/svg-support'

    >>> browser.getControl('Branch').value = '~mark/firefox/release-0.8'
    >>> browser.getControl('Continue').click()

The blueprint page shows the linked branches in a portlet.

    >>> user_browser.open(
    ...     'http://blueprints.launchpad.test/firefox/+spec/svg-support')
    >>> print(extract_text(find_tag_by_id(user_browser.contents,
    ...     'linked_branches')))
    Related branches
    lp://dev/~mark/firefox/release-0.8
    Link to another branch

Again, attempting to link to the same branch gives an error.

    >>> browser.getLink('Link to another branch').click()
    >>> browser.getControl('Branch').value = '~mark/firefox/release-0.8'
    >>> browser.getControl('Continue').click()
    >>> print_feedback_messages(browser.contents)
    There is 1 error.
    This branch has already been linked to the blueprint

    >>> browser.getLink('Cancel').click()


Deleting a Branch Link
----------------------

Users can delete the branch link from the branch link page:

    >>> browser.getLink(url='+branch/mark/firefox/release-0.8').click()
    >>> back_link = browser.getLink('Support Native SVG Objects')
    >>> back_link.url
    'http://blueprints.launchpad.test/firefox/+spec/svg-support'
    >>> browser.getControl('Delete').click()

The branch is now no longer listed in the portlet:

    >>> user_browser.open(
    ...     'http://blueprints.launchpad.test/firefox/+spec/svg-support')
    >>> print(extract_text(find_tag_by_id(user_browser.contents,
    ...     'linked_branches')))
    Related branches
    Link a related branch
