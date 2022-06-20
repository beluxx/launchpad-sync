Branch listings for distroseries
================================

All source package branches are associated with a distribution series and a
source package name.

    >>> login('admin@canonical.com')
    >>> mint = factory.makeDistribution(name='mint')
    >>> stable = factory.makeDistroSeries(mint, name='stable')
    >>> eric = factory.makePerson(name='eric')
    >>> twisted = factory.makeSourcePackageName('twisted')
    >>> branch = factory.makePackageBranch(
    ...     distroseries=stable, sourcepackagename=twisted, owner=eric,
    ...     name='old')
    >>> zope = factory.makeSourcePackageName('zope')
    >>> branch = factory.makePackageBranch(
    ...     distroseries=stable, sourcepackagename=zope, owner=eric,
    ...     name='new')
    >>> logout()

    >>> browser.open('http://launchpad.test/mint/stable')

Going to this page shows us a listing of all branches associated with that
distribution series ordered by most recently changed first.

    >>> browser.open('http://code.launchpad.test/mint/stable')
    >>> contents = browser.contents
    >>> print_tag_with_id(contents, 'branchtable')
    Name   Status   Last Modified  Last Commit
    lp://dev/~eric/mint/stable/twisted/old      Development ...
    lp://dev/~eric/mint/stable/zope/new         Development ...
    ...
    >>> ordering_control = browser.getControl(name='field.sort_by')
    >>> print(ordering_control.displayValue)
    ['most recently changed first']
