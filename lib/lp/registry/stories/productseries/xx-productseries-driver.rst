Appointing a Product Series Driver (release manager)
====================================================

Sample Person is the driver of Firefox 1.0 series because they are also
the project owner. They can delegate the responsibility of release manager
by appointing someone else as the driver.

    >>> browser.addHeader('Authorization', 'Basic test@canonical.com:test')
    >>> browser.open('http://launchpad.test/firefox/1.0')
    >>> content  = find_tag_by_id(browser.contents, 'series-details')
    >>> print(extract_text(find_tag_by_id(content, 'series-drivers')))
    Project drivers: Sample Person
    >>> print(extract_text(find_tag_by_id(content, 'series-release-manager')))
    Release manager: None Appoint release manager

    >>> browser.getLink('Appoint release manager').click()

    >>> browser.url
    'http://launchpad.test/firefox/1.0/+driver'
    >>> print(browser.title)
    Appoint the release manager for...
    >>> browser.getControl('Release manager').value
    ''

    >>> browser.getControl('Release manager').value = 'salgado'
    >>> browser.getControl('Change').click()

After changing the driver, the browser shows the overview page where a
message explains that the driver changed.

    >>> browser.url
    'http://launchpad.test/firefox/1.0'

    >>> for tag in find_tags_by_class(browser.contents, 'informational'):
    ...     print(tag.decode_contents())
    Successfully changed the release manager to Guilherme Salgado

Sample Person and Guilherme Salgado are listed as the drivers of Firefox 1.0.

    >>> content  = find_tag_by_id(browser.contents, 'series-details')
    >>> print(extract_text(find_tag_by_id(content, 'series-drivers')))
    Project drivers: Guilherme Salgado, Sample Person
    >>> print(extract_text(find_tag_by_id(content, 'series-release-manager')))
    Release manager: Guilherme Salgado Appoint release manager

