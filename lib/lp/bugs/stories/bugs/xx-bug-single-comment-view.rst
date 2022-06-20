Each bug comment on the main bug page contains a link to view only that
comment.

    >>> browser.open('http://bugs.launchpad.test/bugs/2')
    >>> browser.url
    'http://bugs.launchpad.test/tomcat/+bug/2'

    >>> def print_comment_titles(page):
    ...     """Prints all the comment titles that are visible on the page."""
    ...     soup = find_main_content(browser.contents)
    ...     comment_details = soup('div', 'boardCommentDetails')
    ...     for details in comment_details:
    ...         print(details.find('strong').string)

    >>> print_comment_titles(browser.contents)
    Fantastic idea, I'd really like to see this
    Strange bug with duplicate messages.

Let's go to the last comment and make sure that there's only one
comment displayed on that page.

    >>> comment_link = browser.getLink('Strange bug with duplicate messages.')
    >>> comment_link.click()
    >>> browser.url
    'http://bugs.launchpad.test/tomcat/+bug/2/comments/2'

    >>> print_comment_titles(browser.contents)
    Strange bug with duplicate messages.
