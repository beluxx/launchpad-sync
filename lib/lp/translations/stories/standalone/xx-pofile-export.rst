Exporting Single PO Files through the Web
=========================================

Not logged in users can't access the +export page.

    >>> anon_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary'
    ...     '/+source/evolution/+pots/evolution-2.2/es/')
    >>> anon_browser.getLink('Download').click()
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Logged in as a regular user, the +export page is accessible.

    >>> user_browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary'
    ...     '/+source/evolution/+pots/evolution-2.2/es')
    >>> user_browser.getLink('Download').click()

    >>> print(user_browser.title)
    Download translation : Spanish (es)... : Hoary (5.04) :
    Translations : evolution package : Ubuntu

    >>> print(find_main_content(user_browser.contents))
    <...
    ...Download Spanish translation...
    Once the file is ready for download, Launchpad will email
    <code>no-priv@canonical.com</code>
    with a link to the file...

If we POST the page, it should add the request to the queue.

    >>> user_browser.getControl(name='format').value = ['PO']
    >>> user_browser.getControl('Request Download').click()
    >>> print(user_browser.url)
    http://translatio.../ubuntu/hoary/+source/evolution/+pots/evolution-2.2/es

    >>> for tag in find_tags_by_class(user_browser.contents, 'informational'):
    ...     print(tag.decode_contents())
    Your request has been received. Expect to receive an email shortly.

Let's be sure that we can request po files without translations as the
No Privileges Person.

    >>> user_browser.open(
    ...    'http://translations.launchpad.test/evolution/trunk/+pots/'
    ...    'evolution-2.2/cy/+details')
    >>> user_browser.getLink('Download').click()

    >>> user_browser.getControl(name='format').value = ['PO']
    >>> user_browser.getControl('Request Download').click()
    >>> print(user_browser.url)
    http://translations.launchpad.test/evolution/trunk/+pots/evolution-2.2/cy

    >>> for tag in find_tags_by_class(
    ...     user_browser.contents, 'informational'):
    ...     print(tag.decode_contents())
    Your request has been received. Expect to receive an email shortly.

If the POFile first has to be created, the requester becomes its owner.
This implies no special privileges.

We test using the Swedish (sv) language which doesn't have a pofile for
evolution yet; it will be created at the moment the export is requested.

    >>> browser = setupBrowser(auth='Basic carlos@canonical.com:test')
    >>> browser.open(
    ...     'http://translations.launchpad.test/evolution/trunk/+pots/'
    ...     'evolution-2.2/sv/+details')
    >>> browser.getLink('Download').click()

    >>> browser.getControl(name='format').value = ['PO']
    >>> browser.getControl('Request Download').click()
    >>> print(browser.url)
    http://translations.launchpad.test/evolution/trunk/+pots/evolution-2.2/sv

    >>> for tag in find_tags_by_class(browser.contents, 'informational'):
    ...     print(tag.decode_contents())
    Your request has been received. Expect to receive an email shortly.

    >>> browser.open(
    ...     'http://translations.launchpad.test/evolution/trunk/+pots/'
    ...     'evolution-2.2/sv/+details')
    >>> translation_portlet = find_portlet(
    ...     browser.contents, 'Translation file details')
    >>> carlos = u'Carlos Perell\xf3 Mar\xedn'
    >>> creator = extract_text(
    ...     translation_portlet.find(text='Creator:').find_next('a'))
    >>> carlos in creator
    True

Request the same pofile again won't crash. (See bug
https://launchpad.net/rosetta/+bug/1558).

    >>> browser.getLink('Download').click()

    >>> browser.getControl(name='format').value = ['PO']
    >>> browser.getControl('Request Download').click()
    >>> print(browser.url)
    http://translations.launchpad.test/evolution/trunk/+pots/evolution-2.2/sv

    >>> for tag in find_tags_by_class(browser.contents, 'informational'):
    ...     print(tag.decode_contents())
    Your request has been received. Expect to receive an email shortly.
