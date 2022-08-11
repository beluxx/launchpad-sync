Bug editing
===========

The user should be able to look at the page title or heading and
see the bug number being edited.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/jokosher/+bug/11/+edit')
    >>> print(user_browser.title)
    Edit details for bug #11 ...
    >>> main = find_main_content(user_browser.contents)
    >>> print(extract_text(main.h1))
    Edit details for bug #11

And now we show that any logged-in user can edit public bugs.

    >>> browser = setupBrowser(auth='Basic no-priv@canonical.com:test')
    >>> browser.open(
    ...     'http://bugs.launchpad.test/debian/+source/mozilla-firefox/+bug/'
    ...     '3')
    >>> browser.getLink(url="+edit").click()
    >>> browser.url
    'http://bugs.launchpad.test/debian/+source/mozilla-firefox/+bug/3/+edit'
    >>> browser.getControl('Summary').value = 'New Summary'
    >>> browser.getControl('Description').value = 'New description.'
    >>> browser.getControl('Change').click()
    >>> browser.url
    'http://.../debian/+source/mozilla-firefox/+bug/3'
    >>> content = find_main_content(browser.contents)
    >>> print(extract_text(content.h1))
    New Summary Edit
    >>> print(extract_text(find_tag_by_id(content, 'maincontentsub')))
    Edit Bug Description New description. ...


Viewing the original description
--------------------------------

If a bug's description has not been changed since it was reported,
there is no link to the original description.

    >>> user_browser.open('http://bugs.launchpad.test/firefox/+bug/4')
    >>> user_browser.getLink('original description')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

But if the description is edited, the link appears.

    >>> user_browser.getLink(url='+edit').click()
    >>> user_browser.getControl('Description').value = 'New description.'
    >>> user_browser.getControl('Change').click()
    >>> user_browser.getLink('original description').click()
    >>> user_browser.url
    'http://.../+bug/4/comments/0'


Editing bug tags
----------------

When editing bug tags, we want to discourage people from adding new
tags.

    >>> user_browser.open('http://bugs.launchpad.test/firefox/+bug/1')
    >>> user_browser.getLink(url="+edit").click()
    >>> user_browser.url
    'http://bugs.launchpad.test/firefox/+bug/1/+edit'

    >>> user_browser.getControl('Tags').value = 'layout-test'
    >>> user_browser.getControl('Change').click()

Now we are back at the bug page, and the tag has been added.

    >>> user_browser.url
    'http://bugs.launchpad.test/firefox/+bug/1'
    >>> 'layout-test' in user_browser.contents
    True
    >>> 'new-tag' in user_browser.contents
    False

Now, let's add 'new-tag' again, and confirm it this time.

    >>> user_browser.getLink(url="+edit").click()
    >>> user_browser.getControl('Tags').value = 'new-tag'
    >>> user_browser.getControl('Change').click()

    >>> user_browser.url
    'http://bugs.launchpad.test/firefox/+bug/1'

    >>> tags_div = extract_text(
    ...       find_tag_by_id(user_browser.contents, 'bug-tags'))

    >>> 'layout-test' in tags_div
    False
    >>> 'new-tag' in tags_div
    True


Locked bugs
-----------

The metadata of a locked bug can only be edited by privileged users.

    >>> from zope.component import getUtility
    >>> from lp.bugs.enums import BugLockStatus
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.testing.pages import setupBrowserForUser

    >>> login(ANONYMOUS)
    >>> bug_1 = getUtility(IBugSet).get(1)
    >>> target_owner = bug_1.default_bugtask.target.owner
    >>> _ = login_person(target_owner)
    >>> bug_1.lock(who=target_owner, status=BugLockStatus.COMMENT_ONLY)
    >>> logout()

    >>> target_owner_browser = setupBrowserForUser(target_owner)
    >>> target_owner_browser.open('http://bugs.launchpad.test/firefox/+bug/1')
    >>> target_owner_browser.getLink(url='+edit').click()
    >>> target_owner_browser.getControl('Description').value = 'Now locked.'
    >>> target_owner_browser.getControl('Change').click()

    >>> user_browser.open('http://bugs.launchpad.test/firefox/+bug/1')
    >>> user_browser.getLink(url='+edit')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.open('http://bugs.launchpad.test/firefox/+bug/1/+edit')
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...
