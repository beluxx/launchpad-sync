The NameBlacklist table contains a central blacklist of disallowed names.
For objects using this blacklist, it is impossible to create an object
with a blacklisted name, or rename an object to a blacklisted name.

Try creating a project with a blacklisted name:

    >>> admin_browser.open('http://launchpad.test/projectgroups/+new')
    >>> admin_browser.getControl('Name', index=0).value = 'blacklisted'
    >>> admin_browser.getControl('Display Name').value = 'Whatever'
    >>> admin_browser.getControl('Project Group Summary').value = 'Whatever'
    >>> admin_browser.getControl('Description').value = 'Whatever'
    >>> admin_browser.getControl('Add').click()
    >>> ("The name &#x27;blacklisted&#x27; has been blocked" in
    ...  admin_browser.contents)
    True

Try renaming a project to a blacklisted name:

    >>> admin_browser.open('http://launchpad.test/mozilla')
    >>> admin_browser.getLink('Administer').click()
    >>> admin_browser.getControl('Name', index=0).value = 'blacklisted'
    >>> admin_browser.getControl('Change Details').click()
    >>> ("The name &#x27;blacklisted&#x27; has been blocked" in
    ...  admin_browser.contents)
    True

Same behaviour for products:

    >>> admin_browser.open('http://launchpad.test/firefox')
    >>> admin_browser.getLink('Administer').click()
    >>> admin_browser.getControl('Name').value = 'blacklisted'
    >>> admin_browser.getControl('Change').click()
    >>> ("The name &#x27;blacklisted&#x27; has been blocked"
    ...  in admin_browser.contents)
    True

Same behaviour for people:

    >>> admin_browser.open('http://launchpad.test/~stub')
    >>> admin_browser.getLink('Change details').click()
    >>> admin_browser.getControl('Name', index=1).value = 'admin42'
    >>> admin_browser.getControl('Save').click()
    >>> ("The name &#x27;admin42&#x27; has been blocked" in
    ...  admin_browser.contents)
    True

Note that it is possible to have an object with a blacklisted name. These
objects were either created before the blacklist was implemented, or have
been created or renamed manually by the DBA. Being able to manually set
names to a blacklisted name is a desirable feature, as a use case of
the black list is to prevent social engineering attacks by pretending to
be a Launchpad Celebrity.

We can edit the details of an object with a blacklisted name quite
happily without generating

    >>> admin_browser.open('http://launchpad.test/~admins')
    >>> admin_browser.getLink('Change details').click()
    >>> admin_browser.getControl('Display Name').value = 'Different'
    >>> admin_browser.getControl('Save').click()

    >>> print_feedback_messages(admin_browser.contents)
    >>> "has been blocked" in admin_browser.contents
    False
