Distribution Soyuz Views
========================

    >>> from lp.registry.interfaces.distribution import IDistributionSet

    >>> login("foo.bar@canonical.com")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")


DistributionArchivesView
------------------------

    >>> from lp.registry.interfaces.person import IPersonSet

The DistributionArchivesView includes an archive_list property that
returns a list of copy archives only for the given distribution (because
only copy archives are exposed through the distribution/+archives UI):

    >>> distro_archives_view = create_initialized_view(
    ...     ubuntu, name="+archives"
    ... )
    >>> archives = distro_archives_view.archive_list
    >>> archives.count()
    0

And then after creating a copy archive for Ubuntu:

    >>> copy_location = factory.makeCopyArchiveLocation(
    ...     distribution=ubuntu, name="intrepid-security-rebuild"
    ... )
    >>> archives = distro_archives_view.archive_list
    >>> archives.count()
    1

Disabled archives will be visible:

    >>> foo_bar = getUtility(IPersonSet).getByName("name16")
    >>> copy_location = factory.makeCopyArchiveLocation(
    ...     distribution=ubuntu, enabled=False, owner=foo_bar
    ... )
    >>> archives = distro_archives_view.archive_list
    >>> archives.count()
    2

DistributionPackageSearchView
-----------------------------

The DistributionPackageSearchView adds some functionality to the base
PackageSearchView class, specifically for making the results more useful.

By default the view will be initialized as a binary-package-name search,
and the search_by_binary_name property is used to determine the search
type (in templates):

Note: The substring search for binary names now uses the cached binary
names on the DistributionSourcePackageCache, which unfortunately are
not up-to-date in the test data. Hence only seeing mozilla-firefox returned
here.

    >>> distro_pkg_search_view = create_initialized_view(
    ...     ubuntu, name="+search", form={"text": "a"}, query_string="text=a"
    ... )
    >>> distro_pkg_search_view.search_by_binary_name
    True
    >>> for package in distro_pkg_search_view.search_results:
    ...     print(package.name)
    ...
    mozilla-firefox

Additionally, a helper property 'source_search_url' is included providing
easy access to the equivalent search on sources:

    >>> print(distro_pkg_search_view.source_search_url)
    http://launchpad.test/ubuntu/+search?search_type=source&text=a

Unicode form variables remain encoded as UTF-8 (as expected by the
server) when building the 'source_search_url'.

    >>> distro_pkg_search_view = create_initialized_view(
    ...     ubuntu,
    ...     name="+search",
    ...     form={"text": "\xe7"},
    ...     query_string="text=%C3%A7",
    ... )

    >>> print(distro_pkg_search_view.source_search_url)
    http://launchpad.test/ubuntu/+search?search_type=source&text=%C3%A7

But users can specify that the search should be on source-package-names
instead:

    >>> distro_pkg_search_view = create_initialized_view(
    ...     ubuntu,
    ...     name="+search",
    ...     form={"text": "a", "search_type": "source"},
    ... )
    >>> distro_pkg_search_view.search_by_binary_name
    False
    >>> for package in distro_pkg_search_view.search_results:
    ...     print(package.name)
    ...
    alsa-utils
    commercialpackage
    foobar
    mozilla-firefox
    netapplet

Unless the distribution being searched does not support binaries, in which
cases it will always be on source:

    >>> debian = factory.makeDistribution(
    ...     name="mydebian", displayname="debian-without-binaries"
    ... )

    >>> debian.has_published_binaries
    False

    >>> distro_pkg_search_view = create_initialized_view(
    ...     debian, name="+search", form={"search_type": "binary"}
    ... )
    >>> distro_pkg_search_view.search_by_binary_name
    False

Leading and trailing white-space is stripped from the search text.

    >>> distro_pkg_search_view = create_initialized_view(
    ...     ubuntu,
    ...     name="+search",
    ...     form={"text": " a "},
    ...     query_string="text=a",
    ... )
    >>> print(distro_pkg_search_view.text)
    a

If there is more than one text parameter value, the last one is used.

    >>> distro_pkg_search_view = create_initialized_view(
    ...     ubuntu,
    ...     name="+search",
    ...     form={"text": ["a", "b"]},
    ...     query_string="text=a&text=b",
    ... )
    >>> print(distro_pkg_search_view.text)
    b

Exact matches
.............

The DistributionPackageSearchView view has an exact_matches property
and a has_exact_matches property which are used to find packages that
match exactly on the binary/source name.

In the following example, there is one source package that has a binary
with the exact name 'mozilla-firefox':

    >>> distro_pkg_search_view = create_initialized_view(
    ...     ubuntu, name="+search", form={"text": "mozilla-firefox"}
    ... )
    >>> distro_pkg_search_view.has_exact_matches
    True
    >>> for package in distro_pkg_search_view.exact_matches:
    ...     print(package.name)
    ...
    mozilla-firefox

The view can also help the template know when to display exact matches.

    >>> distro_pkg_search_view.display_exact_matches
    True

Exact matches do not need to be displayed when the user views subsequent
batches.

    >>> distro_pkg_search_view = create_initialized_view(
    ...     ubuntu,
    ...     name="+search",
    ...     form={
    ...         "text": "mozilla-firefox",
    ...         "batch": "2",
    ...         "start": "2",
    ...     },
    ... )
    >>> distro_pkg_search_view.display_exact_matches
    False

But they are displayed when returning to the first batch.

    >>> distro_pkg_search_view = create_initialized_view(
    ...     ubuntu,
    ...     name="+search",
    ...     form={
    ...         "text": "mozilla-firefox",
    ...         "batch": "2",
    ...         "start": "0",
    ...     },
    ... )
    >>> distro_pkg_search_view.display_exact_matches
    True

Searches against source packages should not display exact matches either:

    >>> distro_pkg_search_view = create_initialized_view(
    ...     ubuntu,
    ...     name="+search",
    ...     form={
    ...         "text": "mozilla-firefox",
    ...         "search_type": "source",
    ...     },
    ... )
    >>> distro_pkg_search_view.display_exact_matches
    False

The DistributionPackageSearchView also has a helper property to
help templates print the list of distroseries that an exactly-matched
package is available in:

    >>> for key, value in distro_pkg_search_view.distroseries_names.items():
    ...     print("%s: %s" % (key, value))
    ...
    mozilla-firefox: warty
    >>> distro_pkg_search_view = create_initialized_view(
    ...     ubuntu, name="+search", form={"text": "mozilla-firefox"}
    ... )
    >>> for key, value in distro_pkg_search_view.distroseries_names.items():
    ...     print("%s: %s" % (key, value))
    ...
    mozilla-firefox: warty

Another helper on the DistributionPackageSearchView is the
matching_binary_names property which can be used by templates to get
a list of the binary names that matched the search term for each
package:

    >>> distro_pkg_search_view = create_initialized_view(
    ...     ubuntu, name="+search", form={"text": "moz"}
    ... )
    >>> for (
    ...     key,
    ...     value,
    ... ) in distro_pkg_search_view.matching_binary_names.items():
    ...     print("%s: %s" % (key, value))
    mozilla-firefox: mozilla-firefox, mozilla-firefox-data

The matching_binary_names property uses a protected helper method
'_listFirstFiveMatchingNames' which ensures only the first five matching
names are returned. An ellipse is used to indicate when more than five
names match:

    >>> print(
    ...     distro_pkg_search_view._listFirstFiveMatchingNames(
    ...         "moz",
    ...         "mozilla-firefox mozilla-data moziki " "limozine moza lamoz",
    ...     )
    ... )  # doctest: -ELLIPSIS
    mozilla-firefox, mozilla-data, moziki, limozine, moza, ...


Substring matches
.................

The DistributionPackageSearchView includes substring matches by default.

    >>> search_results = distro_pkg_search_view.search_results
    >>> search_results.count()
    1

    >>> for pkg in search_results:
    ...     print(pkg.name)
    ...
    mozilla-firefox
