ProjectGroup Branches Overview
==============================

    >>> from lp.code.tests.branch_helper import (
    ...     reset_all_branch_last_modified)
    >>> reset_all_branch_last_modified()


ProjectGroups link their branch listing page.

    >>> browser.open('http://launchpad.test/mozilla')
    >>> browser.getLink('Code').click()
    >>> print(browser.title)
    Code : The Mozilla Project


Default page for code site
==========================

When going directly to a project on the code rootsite for launchpad,
the branch listing is the default page shown.

If there are branches, then they are displayed.

    >>> browser.open('http://code.launchpad.test/mozilla')
    >>> table = find_tag_by_id(browser.contents, 'branchtable')
    >>> for row in table.tbody.find_all('tr'):
    ...     print(extract_text(row))
    lp://dev/~mark/firefox/release--0.9.1  Development   firefox ...
    lp://dev/~mark/firefox/release-0.8     Development   firefox ...
    lp://dev/~mark/firefox/release-0.9     Development   firefox ...
    lp://dev/~mark/firefox/release-0.9.2   Development   firefox ...
    lp://dev/~name12/firefox/main            Development   firefox ...
    lp://dev/~stevea/thunderbird/main        Development   thunderbird ...

If there are not any branches, a relevant message is shown.

    >>> browser.open('http://code.launchpad.test/aaa')
    >>> print(browser.title)
    Code : the Test Project
    >>> message = find_tag_by_id(browser.contents, 'no-branchtable')
    >>> print(extract_text(message))
    Launchpad does not know where any of
    the Test Project's
    projects host their code.
