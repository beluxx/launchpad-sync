Deactivating user accounts
==========================

Users who don't want to use Launchpad anymore can easily deactivate their
accounts so they stop receiving emails from Launchpad and make it impossible
to use their accounts to log in.

Deactivating a user's account will un-assign all their bug tasks. To
demonstrate this, we'll assign a bug to the user that we're going to
deactivate.

    >>> browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> edit_bug_url = (
    ...     "http://bugs.launchpad.test/debian/sarge/+source/"
    ...     "mozilla-firefox/+bug/3/+editstatus"
    ... )
    >>> browser.open(edit_bug_url)
    >>> bugwatch_control = browser.getControl(
    ...     name="debian_sarge_mozilla-firefox.bugwatch"
    ... )
    >>> bugwatch_control.value = []
    >>> browser.getControl("Save Changes").click()

    >>> browser.open(edit_bug_url)
    >>> assignee_control = browser.getControl(
    ...     name="debian_sarge_mozilla-firefox.assignee.option"
    ... )
    >>> assignee_control.value = [
    ...     "debian_sarge_mozilla-firefox.assignee.assign_to_me"
    ... ]
    >>> browser.getControl("Save Changes").click()

There's a link to the +deactivate-account page in a person's +edit page.

    >>> browser.open("http://launchpad.test/~name12")
    >>> browser.getLink("Change details").click()
    >>> browser.url
    'http://launchpad.test/~name12/+edit'

    >>> browser.getLink("Deactivate your account").click()
    >>> browser.url
    'http://launchpad.test/~name12/+deactivate-account'

    >>> browser.getControl("Deactivate My Account").click()
    >>> browser.url
    'http://launchpad.test'
    >>> print_feedback_messages(browser.contents)
    Your account has been deactivated.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.persontransferjob import (
    ...     IPersonDeactivateJobSource,
    ... )
    >>> login("admin@canonical.com")
    >>> name12 = getUtility(IPersonSet).getByName("name12")
    >>> [job] = getUtility(IPersonDeactivateJobSource).find(name12)
    >>> job.run()
    >>> logout()

And now the Launchpad page for Sample Person person will clearly say they
do not use Launchpad.

    >>> browser.open("http://launchpad.test/~name12-deactivatedaccount")
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "not-lp-user-or-team")
    ...     )
    ... )
    Sample Person does not use Launchpad.

The bugs that were assigned to Sample Person will no longer have an
assignee.

    >>> browser.open(
    ...     "http://launchpad.test/debian/+source/" "mozilla-firefox/+bug/3"
    ... )
    >>> print(extract_text(find_main_content(browser.contents)))
    Bug Title Test
    ...
    Assigned to
    Milestone
    ...

Although teams have NOACCOUNT as their account_status, they are teams and so
it makes no sense to say they don't use Launchpad.

    >>> browser.open("http://launchpad.test/~ubuntu-team")
    >>> print(find_tag_by_id(browser.contents, "not-lp-user-or-team"))
    None

The action of deactivating an account is something that can only be done by
the user themselves --not even Launchpad admins can do that on behalf of other
people.

    >>> admin_browser.open("http://launchpad.test/~cprov/+deactivate-account")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

