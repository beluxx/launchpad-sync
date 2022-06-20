Renewing a member's subscription
================================

Mark decides to renew his subscription to the 'Ubuntu Gnome Team', which
is expired. He select Never from the expiration options and chooses
the 'Renew' button.

    >>> browser = setupBrowser(auth='Basic mark@example.com:test')
    >>> browser.open('http://launchpad.test/~name18/+member/mark')
    >>> print(browser.title)
    Mark Shuttleworth's membership : ...Ubuntu Gnome Team... team
    >>> content = find_main_content(browser.contents)
    >>> print(extract_text(content.p))
    Mark Shuttleworth (mark) is an Expired Member of Ubuntu Gnome Team.

    >>> browser.getControl(name='expires').value = ['never']
    >>> browser.getControl('Renew').click()

He is redirected to the team page. He can see that his subscription
is approved because he is in the active members table.

    >>> from lp.services.helpers import backslashreplace
    >>> print(backslashreplace(browser.title))
    Members : \u201cUbuntu Gnome Team\u201d team
    >>> content = find_tag_by_id(browser.contents, 'activemembers')
    >>> print(extract_text(content, formatter='html'))
    Name               Member since  Expires  Status
    ...
    Mark Shuttleworth  2005-03-03    &ndash;  Approved
    ...
