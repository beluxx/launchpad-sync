=====
Karma
=====

Launchpad assigns a person karma for performing actions beneficial to
the community.  A person's current total karma is available on their
profile page.

    >>> anon_browser.open('http://launchpad.test/~name12')
    >>> print(anon_browser.title)
    Sample Person in Launchpad

    >>> content = find_main_content(anon_browser.contents)
    >>> karma = find_tag_by_id(content, 'karma-total')
    >>> print(karma.decode_contents())
    138

The total karma points is also a link to the person's karma summary page.

    >>> anon_browser.getLink('138').click()
    >>> print(anon_browser.title)
    Karma : Sample Person

Any user can see the categories that a user has earned karma in.

    >>> content = find_main_content(anon_browser.contents)
    >>> for row in find_tag_by_id(content, 'karmapoints').find_all('tr'):
    ...     print(extract_text(row))
    Bug Management           94
    Specification Tracking   44

Any user can see that a user has latest actions.

    >>> for row in find_tag_by_id(content, 'karmaactions').find_all('tr'):
    ...     print(extract_text(row))
    Date        Action
    2001-11-02  Registered Specification
    2001-11-02  Registered Specification
    2001-10-28  New Bug Filed
    ...

The karma page can also show any user that a user has never earned karma.

    >>> anon_browser.open('http://launchpad.test/~salgado/+karma')
    >>> content = find_main_content(anon_browser.contents)
    >>> print(extract_text(find_tag_by_id(content, 'no-karma')))
    No karma has yet been assigned to Guilherme Salgado. Karma is updated
    daily.

The karma page will explain that a user's karma has expired, and show
a that user's last karma actions

    >>> anon_browser.open('http://launchpad.test/~karl/+karma')
    >>> content = find_main_content(anon_browser.contents)
    >>> print(extract_text(find_tag_by_id(content, 'no-karma')))
    Karl Tilbury's karma has expired.

    >>> for row in find_tag_by_id(content, 'karmaactions').find_all('tr'):
    ...     print(extract_text(row))
    Date        Action
    2001-08-09  New Bug Filed
