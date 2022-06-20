Appointing a ProjectGroup Driver
================================

Appoint Sample Person as the driver of the GNOME Project.

    >>> browser.addHeader('Authorization', 'Basic test@canonical.com:test')
    >>> browser.open('http://launchpad.test/gnome/+driver')
    >>> print(browser.title)
    Appoint the driver for...

    >>> browser.getControl('Driver').value = 'name12'
    >>> browser.getControl('Change').click()

After changing the driver, the user is redirected to the overview page where a
message informs them of the driver change.

    >>> browser.url
    'http://launchpad.test/gnome'

    >>> for tag in find_tags_by_class(browser.contents, 'informational'):
    ...     print(tag.decode_contents())
    Successfully changed the driver to Sample Person

Sample Person is listed as the driver of the project.

    >>> print(extract_text(find_tag_by_id(browser.contents, 'driver')))
    Driver:
    Sample Person
    Edit
    ...
