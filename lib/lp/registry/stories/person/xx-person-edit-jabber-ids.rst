==========
Jabber IDs
==========


In their Launchpad profile, users can register their Jabber IDs.

Adding and editing an ID
------------------------

To register a Jabber ID with their account, the user visits their
profile page and uses the 'Update Jabber IDs' link.

    >>> user_browser.open('http://launchpad.test/~no-priv')
    >>> user_browser.getLink('Update Jabber IDs').click()
    >>> print(user_browser.title)
    No Privileges Person's Jabber IDs...

The user enters the Jabber ID in the text field and clicks on the
'Save Changes' button.

    >>> user_browser.getControl(name='field.jabberid').value = (
    ...     'jeff@jabber.org')
    >>> user_browser.getControl('Save Changes').click()

In this case, the user tried registering a jabber ID that was already
registered by someone else. Since only one person can use a Jabber ID,
an error is displayed and the user can enter another one:

    >>> def show_errors(browser):
    ...     for error in find_tags_by_class(browser.contents, 'error'):
    ...         print(extract_text(error))
    >>> show_errors(user_browser)
    There is 1 error.
    New Jabber user ID:
    The Jabber ID jeff@jabber.org is already registered by Jeff Waugh.

However, if the user enters a Jabber ID which isn't already registered,
it will be associated with their account.

    >>> user_browser.getControl(name='field.jabberid').value = (
    ...     'no-priv@jabber.org')
    >>> user_browser.getControl('Save Changes').click()
    >>> show_errors(user_browser)

    >>> def show_jabberids(browser):
    ...     tags = find_tag_by_id(browser.contents, 'jabber-ids')
    ...     for dd in tags.find_all('dd'):
    ...         print(extract_text(dd))

    >>> show_jabberids(user_browser)
    no-priv@jabber.org

Removing an ID
--------------

To remove an existing Jabber ID, the user simply checks the 'Remove'
checkbox besides the ID:
    >>> user_browser.getLink('Update Jabber IDs').click()
    >>> user_browser.getControl('Remove', index=0).click()
    >>> user_browser.getControl('Save Changes').click()

    >>> show_jabberids(user_browser)
    No Jabber IDs registered.
