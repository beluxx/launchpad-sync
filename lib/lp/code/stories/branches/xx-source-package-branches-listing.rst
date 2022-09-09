Populated source package branch listings
========================================

Going to a source package branch page shows a list of branches.

Let's demonstrate this by making a source package with some branches and then
browsing to it.

    >>> from lp.registry.model.sourcepackage import SourcePackage
    >>> def make_source_package(distro, series, name):
    ...     distro = factory.makeDistribution(name=distro, displayname=distro)
    ...     distroseries = factory.makeDistroSeries(
    ...         name=series, distribution=distro
    ...     )
    ...     sourcepackagename = factory.makeSourcePackageName(name=name)
    ...     return SourcePackage(sourcepackagename, distroseries)
    ...

    >>> login(ANONYMOUS)
    >>> source_package = make_source_package("distro", "series", "foo")
    >>> branch1 = factory.makePackageBranch(
    ...     sourcepackage=source_package,
    ...     owner=factory.makePerson(name="owner1"),
    ...     name="branch1",
    ... )
    >>> transaction.commit()
    >>> branch2 = factory.makePackageBranch(
    ...     sourcepackage=source_package,
    ...     owner=factory.makePerson(name="owner2"),
    ...     name="branch2",
    ... )
    >>> transaction.commit()
    >>> source_package_url = canonical_url(source_package, rootsite="code")
    >>> logout()

This takes us to the branch listing for that source package

    >>> browser.open(source_package_url)

Both of the branches we made appear in the listing.

    >>> def print_branches(browser):
    ...     table = find_tag_by_id(browser.contents, "branchtable")
    ...     for row in table.tbody.find_all("tr"):
    ...         print(extract_text(row))
    ...
    >>> print_branches(browser)
    lp://dev/~owner1/distro/series/foo/branch1 ...
    lp://dev/~owner2/distro/series/foo/branch2 ...

XXX: Show that the summary is beautiful.


There is also a simple branch listing for the distribution source package that
shows all branches for that source package across all series for the
distribution.

    >>> login(ANONYMOUS)
    >>> distro = branch1.distroseries.distribution
    >>> next_series = factory.makeDistroSeries(
    ...     name="next", distribution=distro
    ... )
    >>> source_package = factory.makeSourcePackage(
    ...     sourcepackagename=branch1.sourcepackagename,
    ...     distroseries=next_series,
    ... )
    >>> branch3 = factory.makePackageBranch(
    ...     sourcepackage=source_package, owner=branch1.owner, name="branch3"
    ... )
    >>> distro_source_package = factory.makeDistributionSourcePackage(
    ...     distribution=distro, sourcepackagename=branch1.sourcepackagename
    ... )
    >>> transaction.commit()
    >>> distro_source_package_listing = canonical_url(
    ...     distro_source_package, view_name="+all-branches", rootsite="code"
    ... )
    >>> logout()

    >>> browser.open(distro_source_package_listing)
    >>> print_branches(browser)
    lp://dev/~owner1/distro/next/foo/branch3 ...
    lp://dev/~owner2/distro/series/foo/branch2 ...
    lp://dev/~owner1/distro/series/foo/branch1 ...
