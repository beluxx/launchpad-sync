Bug Lists on the Front Page
===========================

On the bugs front page there is a list of the most recently reported
and recently fixed bugs, across all products and distributions.

To demonstrate this, a few fixed bugs must be created. date_closed isn't
always set in old real data, so we create a bug without it set to
confirm it doesn't show up.

    >>> from zope.component import getUtility
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.testing import login, logout
    >>> import transaction
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.bugs.interfaces.bugtask import (
    ...     BugTaskImportance,
    ...     BugTaskStatus,
    ...     )
    >>> login('foo.bar@canonical.com')
    >>> bigfixer = factory.makeProduct(name='bigfixer')
    >>> bugs = []
    >>> for bug_x in range(1, 11):
    ...     summary = 'Summary for new bug %d' % bug_x
    ...     bug = factory.makeBug(title=summary, target=bigfixer)
    ...     bug.default_bugtask.transitionToStatus(
    ...         BugTaskStatus.FIXRELEASED, getUtility(ILaunchBag).user)
    ...     bug.default_bugtask.transitionToImportance(
    ...         BugTaskImportance.HIGH, getUtility(ILaunchBag).user)
    ...     bugs.append(bug)
    >>> removeSecurityProxy(bugs[7].default_bugtask).date_closed = None
    >>> transaction.commit()
    >>> logout()


Reported bugs
-------------

The bugs front page can be consulted now for the list of reported bugs.

    >>> anon_browser.open('http://bugs.launchpad.test/')
    >>> reported_bugs = find_tag_by_id(anon_browser.contents, 'reported-bugs')

The list of recently reported bugs contains up to the last 5 bugs reported
across Launchpad. The text for each bug contains links to the bug itself,
to the bug target and to the bug reporter's page.

    >>> def print_bugs_links(bug_row):
    ...     print("%s: %s" % (
    ...         bug_row.span.a.decode_contents().strip(),
    ...         bug_row.a.decode_contents()))
    ...     print(bug_row.a['href'])
    ...     print(bug_row.span.a['href'])
    >>> for li in reported_bugs('li'):
    ...     print_bugs_links(li)
    Bigfixer: Bug #...: Summary for new bug ...
    /bugs/...
    /bigfixer
    Bigfixer:
             Bug #...: Summary for new bug ...
    /bugs/...
    /bigfixer
    Bigfixer:
             Bug #...: Summary for new bug ...
    /bugs/...
    /bigfixer
    Bigfixer:
             Bug #...: Summary for new bug ...
    /bugs/...
    /bigfixer
    Bigfixer:
             Bug #...: Summary for new bug ...
    /bugs/...
    /bigfixer


Fixed bugs
----------

The bugs front page also can be consulted for the list of fixed bugs.

    >>> fixed_bugs = find_tag_by_id(anon_browser.contents, 'fixed-bugs')

The list of recently fixed bugs contains up to the last 5 bugs fixed
across Launchpad. The 8th new bug is not listed because it has a null
date_closed.

    >>> for li in fixed_bugs('li'):
    ...     print_bugs_links(li)
    Bigfixer:
             Bug #...: Summary for new bug 10
    /bugs/...
    /bigfixer
    Bigfixer:
             Bug #...: Summary for new bug 9
    /bugs/...
    /bigfixer
    Bigfixer:
             Bug #...: Summary for new bug 7
    /bugs/...
    /bigfixer
    Bigfixer:
             Bug #...: Summary for new bug 6
    /bugs/...
    /bigfixer
    Bigfixer:
             Bug #...: Summary for new bug 5
    /bugs/...
    /bigfixer
