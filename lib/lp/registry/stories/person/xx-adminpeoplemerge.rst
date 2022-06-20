Merging people or teams
=======================

Launchpad admins can merge any two people or teams, without the need of
any email address confirmation or something like that.  There's one page
for merging people and another one for merging teams, which obviously
are only accessible to LP admins.

    >>> user_browser.open('http://launchpad.test/people/+adminpeoplemerge')
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...
    >>> user_browser.open('http://launchpad.test/people/+adminteammerge')
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

When there are email addresses associated with the person/team being
merged into another one, a notification is shown to inform the user
these emails are going to be transferred.

    >>> admin_browser.open('http://launchpad.test/people/+adminpeoplemerge')
    >>> admin_browser.getControl('Duplicated Person').value = 'spiv'
    >>> admin_browser.getControl('Target Person').value = 'salgado'
    >>> admin_browser.getControl('Merge').click()

    >>> admin_browser.url
    'http://launchpad.test/people/+adminpeoplemerge'
    >>> print_feedback_messages(admin_browser.contents)
    The following email addresses are owned by Andrew Bennetts and are going
    to be transferred to Guilherme Salgado: andrew.bennetts@ubuntulinux.com

If the user confirms, spiv will be merged into salgado.

    >>> admin_browser.getControl('Reassign Emails and Merge').click()
    >>> admin_browser.url
    'http://launchpad.test/~salgado'

    >>> print_feedback_messages(admin_browser.contents)
    A merge is queued and is expected to complete in a few minutes.

