Editing a ProjectGroup
======================

The maintainer of a project can edit its details.

    >>> browser.addHeader('Authorization', 'Basic test@canonical.com:test')
    >>> browser.open('http://launchpad.test/gnome')
    >>> browser.getLink('Change details').click()
    >>> print(browser.title)
    Change project group details...

    >>> soup = find_main_content(browser.contents)
    >>> browser.getControl('Display Name').value = 'New Name'
    >>> browser.getControl('Project Group Summary').value = 'New Summary.'
    >>> browser.getControl('Description').value = 'New Description.'
    >>> browser.getControl('Homepage URL').value = 'http://new-url.com/'
    >>> browser.getControl(name='field.bugtracker').value = 'mozilla.org'
    >>> browser.getControl('Change Details').click()

    >>> print(browser.url)
    http://launchpad.test/gnome

Regular users can't access the +review page.

    >>> browser.getLink('Administer')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

But administrators can access the page:

    >>> admin_browser.open('http://launchpad.test/gnome')
    >>> admin_browser.getLink('Administer').click()

    >>> print(admin_browser.url)
    http://launchpad.test/gnome/+review

    >>> print(admin_browser.title)
    Change project group details : New Name

Mark the project as reviewed and change the name.

    >>> admin_browser.getControl('Reviewed').selected = True
    >>> admin_browser.getControl(name='field.name').value = 'new-name'
    >>> admin_browser.getControl('Change').click()

    >>> print(admin_browser.url)
    http://launchpad.test/new-name

The project summary shows the status as reviewed for admins only.

    >>> print(extract_text(find_tag_by_id(admin_browser.contents, 'status')))
    Status: Active Reviewed

Other users cannot see the Project group status in the details portlet.

    >>> anon_browser.open('http://launchpad.test/new-name')
    >>> print(extract_text(
    ...     find_tag_by_id(anon_browser.contents, 'portlet-details')))
    Project group information
    Maintainer:
    Sample Person
    Driver:
    Not yet selected
    Bug tracker:
    The Mozilla.org Bug Tracker
    Download RDF metadata

Administrators can also change the maintainer and registrant independent
of each other, as well as adding aliases to the project group.

    >>> admin_browser.open('http://launchpad.test/new-name')
    >>> admin_browser.getLink('Administer').click()
    >>> admin_browser.getControl('Maintainer').value = 'cprov'
    >>> admin_browser.getControl('Registrant').value = 'ddaa'
    >>> admin_browser.getControl('Aliases').value
    ''

    >>> admin_browser.getControl('Aliases').value = 'old-name'
    >>> admin_browser.getControl('Change').click()

    >>> admin_browser.getLink('Administer').click()
    >>> print(admin_browser.getControl('Aliases').value)
    old-name

    >>> admin_browser.goBack()

The project maintainer and registrant are now updated.

    >>> print(extract_text(
    ...     find_tag_by_id(admin_browser.contents, 'maintainer')))
    Maintainer:
    Celso Providelo
    Edit

    >>> print(extract_text(
    ...     find_tag_by_id(admin_browser.contents, 'registration')))
    Registered ... by David Allouche

The registrant really should only be a person, not a team, but that
constraint has to be relaxed to account for old data where we do have
teams as registrants.

    >>> admin_browser.open('http://launchpad.test/new-name')
    >>> admin_browser.getLink('Administer').click()
    >>> admin_browser.getControl('Registrant').value = 'registry'
    >>> admin_browser.getControl('Change').click()

    >>> print(extract_text(
    ...     find_tag_by_id(admin_browser.contents, 'registration')))
    Registered ... by Registry Administrators

Registry experts
----------------

Registry experts are not allowed access to the +edit page.

    >>> email = "expert@example.com"
    >>> registry_expert= factory.makeRegistryExpert(email=email)
    >>> logout()
    >>> expert_browser = setupBrowser(auth='Basic %s:test' % email)

    >>> expert_browser.open('http://launchpad.test/new-name')
    >>> expert_browser.getLink('Change details').click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

And going directly to the URL is not allowed.

    >>> expert_browser.open('http://launchpad.test/new-name/+edit')
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Registry experts do have access to administer project groups, though
there are fewer fields available.

    >>> expert_browser.open('http://launchpad.test/new-name')
    >>> expert_browser.getLink('Administer').click()
    >>> print(expert_browser.url)
    http://launchpad.test/new-name/+review

    >>> expert_browser.getControl('Maintainer')
    Traceback (most recent call last):
    ...
    LookupError: label ...'Maintainer'
    ...
    >>> expert_browser.getControl('Registrant')
    Traceback (most recent call last):
    ...
    LookupError: label ...'Registrant'
    ...

    >>> expert_browser.getControl('Name').value = 'newer-name'
    >>> expert_browser.getControl('Aliases').value = 'sleepy'
    >>> expert_browser.getControl('Active').selected = False
    >>> expert_browser.getControl('Reviewed').selected = False
    >>> expert_browser.getControl('Change').click()

    >>> expert_browser.open('http://launchpad.test/newer-name')
    >>> expert_browser.getLink('Administer').click()
    >>> print(expert_browser.getControl('Aliases').value)
    sleepy
