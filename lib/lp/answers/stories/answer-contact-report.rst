Answer Contact Report
=====================

To view the answer contact report for a given person, the user chooses
the 'Answer Contact For' link from the actions portlet while viewing
the Person's page.

    >>> anon_browser.open('http://answers.launchpad.test/~no-priv')
    >>> anon_browser.getLink('Answer contact for').click()
    >>> print(anon_browser.title)
    Projects for which...

Since No Privileges Person is not an answer contact, the report states
that.

    >>> content = find_main_content(anon_browser.contents)
    >>> print(content.find('p').decode_contents())
    No Privileges Person is not an answer contact for any project.

But when the person is an answer contact, the page displays the project
they registered for.

    >>> anon_browser.open('http://answers.launchpad.test/~name16')
    >>> anon_browser.getLink('Answer contact for').click()
    >>> print(anon_browser.title)
    Projects for which...

    >>> content = find_tag_by_id(
    ...     anon_browser.contents, "direct-answer-contacts-for-list")
    >>> print(backslashreplace(extract_text(content)))
    gnomebaker
    ...mozilla-firefox... package in Ubuntu

    >>> content = find_tag_by_id(
    ...     anon_browser.contents, "team-answer-contacts-for-list")
    >>> print(extract_text(content))
    Gnome Applets
    gnomebaker

Clicking on the name of the project will show the project answers.

    >>> anon_browser.getLink('gnomebaker').click()
    >>> print(anon_browser.title)
    Questions : gnomebaker

When the user is logged in, and they are visiting this page in their
profile, they will see a link after each project to manage their
registration.

    >>> browser.addHeader('Authorization', 'Basic test@canonical.com:test')
    >>> browser.open(
    ...     'http://answers.launchpad.test/~name12')
    >>> browser.getLink('Answer contact for').click()
    >>> print(browser.title)
    Projects for which...

    >>> content = find_tag_by_id(
    ... browser.contents, "team-answer-contacts-for-list")
    >>> print(extract_text(content))
    Gnome Applets Unsubscribe team
    gnomebaker Unsubscribe team

    >>> browser.getLink(id="gnomebaker-setteamanswercontact").click()
    >>> print(browser.title)
    Answer contact for...

The Remove yourself/team links only appears in their profile. They cannot
see the link for other users.

    >>> browser.open(
    ...     'http://answers.launchpad.test/~name16')
    >>> browser.getLink('Answer contact for').click()
    >>> print(browser.title)
    Projects for which...

    >>> content = find_tag_by_id(
    ...     browser.contents, "direct-answer-contacts-for-list")
    >>> print(backslashreplace(extract_text(content)))
    gnomebaker
    ...mozilla-firefox... package in Ubuntu
