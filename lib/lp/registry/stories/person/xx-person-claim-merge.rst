Claiming a person while not logged in
=====================================

An anonymous user visiting an unclaimed account will be given the option
to request a merge, but the +requestmerge page will give an Unauthorized
exception that will redirect the user to the login page.

    >>> anon_browser.open("http://launchpad.test/~matsubara")
    >>> link = anon_browser.getLink("Are you Diogo Matsubara?")
    >>> print(link.url)
    http://launchpad.test/people/+requestmerge?field.dupe_person=matsubara
    >>> link.click()
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...


Claiming a person while logged in
=================================

A logged in user visiting an unclaimed account will be given the
option to request a merge.

    >>> user_browser.open("http://launchpad.test/~matsubara")
    >>> user_browser.getLink("Are you Diogo Matsubara?").click()

Clicking on that link brought them to a page where they can request to
merge the accounts, and the account name is already populated in the
field.

    >>> user_browser.url
    'http://launchpad.test/people/+requestmerge?field.dupe_person=matsubara'

    >>> user_browser.getControl(name="field.dupe_person").value
    'matsubara'

The remainder of the merging story is identical to the other
+requestmerge stories.
