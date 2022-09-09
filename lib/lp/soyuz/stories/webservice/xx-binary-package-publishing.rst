=========================
Binary Package Publishing
=========================

Binary package publishing details are available via a custom operation on
archives, getPublishedBinaries().

    >>> cprov_archive = webservice.get(
    ...     "/~cprov/+archive/ubuntu/ppa"
    ... ).jsonBody()
    >>> pubs = webservice.named_get(
    ...     cprov_archive["self_link"], "getPublishedBinaries"
    ... ).jsonBody()

    >>> def print_publications(pubs):
    ...     for display_name in sorted(
    ...         entry["display_name"] for entry in pubs["entries"]
    ...     ):
    ...         print(display_name)
    ...

    >>> print_publications(pubs)
    mozilla-firefox 1.0 in warty hppa
    mozilla-firefox 1.0 in warty i386
    pmount 0.1-1 in warty hppa
    pmount 0.1-1 in warty i386

getPublishedBinaries() can accept some optional filtering parameters to reduce
the number of returned publications.

Search by name and version using an exact match:

    >>> pubs = webservice.named_get(
    ...     cprov_archive["self_link"],
    ...     "getPublishedBinaries",
    ...     binary_name="pmount",
    ...     version="0.1-1",
    ...     exact_match=True,
    ... ).jsonBody()
    >>> print_publications(pubs)
    pmount 0.1-1 in warty hppa
    pmount 0.1-1 in warty i386

Search by publishing status:

    >>> pubs = webservice.named_get(
    ...     cprov_archive["self_link"],
    ...     "getPublishedBinaries",
    ...     status="Published",
    ... ).jsonBody()
    >>> print_publications(pubs)
    mozilla-firefox 1.0 in warty hppa
    mozilla-firefox 1.0 in warty i386
    pmount 0.1-1 in warty hppa
    pmount 0.1-1 in warty i386

Search by distroseries and pocket:

    >>> distros = webservice.get("/distros").jsonBody()
    >>> ubuntu = distros["entries"][0]
    >>> warty = webservice.named_get(
    ...     ubuntu["self_link"], "getSeries", name_or_version="warty"
    ... ).jsonBody()

    >>> pubs = webservice.named_get(
    ...     cprov_archive["self_link"],
    ...     "getPublishedBinaries",
    ...     distro_series=warty["self_link"],
    ...     pocket="Release",
    ... ).jsonBody()
    >>> print_publications(pubs)
    mozilla-firefox 1.0 in warty hppa
    mozilla-firefox 1.0 in warty i386
    pmount 0.1-1 in warty hppa
    pmount 0.1-1 in warty i386

Each binary publication exposes a number of properties:

    >>> from lazr.restful.testing.webservice import pprint_entry
    >>> pprint_entry(pubs["entries"][0])
    architecture_specific: True
    archive_link: 'http://.../~cprov/+archive/ubuntu/ppa'
    binary_package_name: 'mozilla-firefox'
    binary_package_version: '1.0'
    build_link: 'http://.../~cprov/+archive/ubuntu/ppa/+build/28'
    component_name: 'main'
    copied_from_archive_link: None
    creator_link: None
    date_created: '2007-08-10T13:00:00+00:00'
    date_made_pending: None
    date_published: '2007-08-10T13:00:01+00:00'
    date_removed: None
    date_superseded: None
    display_name: 'mozilla-firefox 1.0 in warty hppa'
    distro_arch_series_link: 'http://.../ubuntu/warty/hppa'
    phased_update_percentage: None
    pocket: 'Release'
    priority_name: 'IMPORTANT'
    removal_comment: None
    removed_by_link: None
    resource_type_link: 'http://.../#binary_package_publishing_history'
    scheduled_deletion_date: None
    section_name: 'base'
    self_link: 'http://.../~cprov/+archive/ubuntu/ppa/+binarypub/30'
    source_package_name: 'mozilla-firefox'
    source_package_version: '0.9'
    status: 'Published'


Security
========

Create a private PPA for Celso with some binaries.

    >>> login("foo.bar@canonical.com")
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> from lp.soyuz.enums import PackagePublishingStatus
    >>> cprov_db = getUtility(IPersonSet).getByName("cprov")
    >>> ubuntu_db = getUtility(IDistributionSet).getByName("ubuntu")
    >>> cprov_private_ppa_db = factory.makeArchive(
    ...     private=True, owner=cprov_db, name="p3a", distribution=ubuntu_db
    ... )
    >>> test_publisher = SoyuzTestPublisher()
    >>> test_publisher.prepareBreezyAutotest()
    >>> private_source_pub = test_publisher.getPubBinaries(
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     binaryname="privacy-test-bin",
    ...     archive=cprov_private_ppa_db,
    ... )
    >>> logout()

Only Celso (or anyone who participates on the PPA owner team) has
access to the PPA publications.

    >>> cprov_private_ppa = webservice.get(
    ...     "/~cprov/+archive/ubuntu/p3a"
    ... ).jsonBody()
    >>> cprov_bins_response = webservice.named_get(
    ...     cprov_private_ppa["self_link"], "getPublishedBinaries"
    ... )
    >>> print(cprov_bins_response)
    HTTP/1.1 200 Ok
    ...

Any other user attempt would result in a 401 error.

    >>> response = user_webservice.named_get(
    ...     cprov_private_ppa["self_link"], "getPublishedBinaries"
    ... )
    >>> print(response)
    HTTP/1.1 401 Unauthorized
    ...

If the user attempts to access the publication URL directly they will
also fail in their quest.

    >>> pubs = cprov_bins_response.jsonBody()
    >>> private_publication_url = pubs["entries"][0]["self_link"]
    >>> response = user_webservice.get(private_publication_url)
    >>> print(response)
    HTTP/1.1 401 Unauthorized
    ...


Download counts
===============

We can retrieve the total download count for a binary in this archive.

    >>> webservice.named_get(
    ...     pubs["entries"][0]["self_link"], "getDownloadCount"
    ... ).jsonBody()
    0

    >>> login("foo.bar@canonical.com")

    >>> from datetime import date
    >>> from lp.services.worlddata.interfaces.country import ICountrySet
    >>> australia = getUtility(ICountrySet)["AU"]

    >>> firefox_db = cprov_db.archive.getAllPublishedBinaries(
    ...     name="mozilla-firefox"
    ... )[0]
    >>> firefox_db.archive.updatePackageDownloadCount(
    ...     firefox_db.binarypackagerelease, date(2010, 2, 21), australia, 10
    ... )
    >>> firefox_db.archive.updatePackageDownloadCount(
    ...     firefox_db.binarypackagerelease, date(2010, 2, 23), None, 8
    ... )

    >>> logout()

    >>> firefox = webservice.named_get(
    ...     cprov_archive["self_link"],
    ...     "getPublishedBinaries",
    ...     binary_name="mozilla-firefox",
    ... ).jsonBody()["entries"][0]
    >>> webservice.named_get(
    ...     firefox["self_link"], "getDownloadCount"
    ... ).jsonBody()
    18

Detailed download counts are also available from the getDownloadCounts method.

    >>> counts = webservice.named_get(
    ...     firefox["self_link"], "getDownloadCounts"
    ... ).jsonBody()["entries"]
    >>> len(counts)
    2

A detailed count object can be retrieved by its URL.

    >>> pprint_entry(webservice.get(counts[1]["self_link"]).jsonBody())
    ... # noqa
    archive_link: 'http://.../~cprov/+archive/ubuntu/ppa'
    binary_package_name: 'mozilla-firefox'
    binary_package_version: '1.0'
    count: 10
    country_link: 'http://.../+countries/AU'
    day: '2010-02-21'
    resource_type_link: 'http://.../#binary_package_release_download_count'
    self_link: 'http://.../~cprov/+archive/ubuntu/ppa/+binaryhits/mozilla-firefox/1.0/hppa/2010-02-21/AU'

We can also filter by date.

    >>> counts = webservice.named_get(
    ...     firefox["self_link"], "getDownloadCounts", start_date="2010-02-22"
    ... ).jsonBody()["entries"]
    >>> len(counts)
    1

    >>> pprint_entry(webservice.get(counts[0]["self_link"]).jsonBody())
    ... # noqa
    archive_link: 'http://.../~cprov/+archive/ubuntu/ppa'
    binary_package_name: 'mozilla-firefox'
    binary_package_version: '1.0'
    count: 8
    country_link: None
    day: '2010-02-23'
    resource_type_link: 'http://.../#binary_package_release_download_count'
    self_link: 'http://.../~cprov/+archive/ubuntu/ppa/+binaryhits/mozilla-firefox/1.0/hppa/2010-02-23/unknown'

But other URLs result in a 404.

    >>> print(webservice.get("/~cprov/+archive/ubuntu/ppa/+binaryhits/moz"))
    HTTP/1.1 404 Not Found
    ...

    >>> print(
    ...     webservice.get(
    ...         "/~cprov/+archive/ubuntu/ppa/+binaryhits/phoenix/1.0/"
    ...         "hppa/2010-02-23/unknown"
    ...     )
    ... )
    HTTP/1.1 404 Not Found
    ...

    >>> print(
    ...     webservice.get(
    ...         "/~cprov/+archive/ubuntu/ppa/+binaryhits/mozilla-firefox/1.1/"
    ...         "hppa/2010-02-23/unknown"
    ...     )
    ... )
    HTTP/1.1 404 Not Found
    ...

    >>> print(
    ...     webservice.get(
    ...         "/~cprov/+archive/ubuntu/ppa/+binaryhits/mozilla-firefox/1.0/"
    ...         "foo/2010-02-23/unknown"
    ...     )
    ... )
    HTTP/1.1 404 Not Found
    ...

    >>> print(
    ...     webservice.get(
    ...         "/~cprov/+archive/ubuntu/ppa/+binaryhits/mozilla-firefox/1.0/"
    ...         "hppa/2010-02-25/unknown"
    ...     )
    ... )
    HTTP/1.1 404 Not Found
    ...

    >>> print(
    ...     webservice.get(
    ...         "/~cprov/+archive/ubuntu/ppa/+binaryhits/mozilla-firefox/1.0/"
    ...         "hppa/2010-02-23/XX"
    ...     )
    ... )
    HTTP/1.1 404 Not Found
    ...

getDailyDownloadTotals returns a dict mapping dates to total counts.

    >>> for key, value in sorted(
    ...     webservice.named_get(
    ...         firefox["self_link"], "getDailyDownloadTotals"
    ...     )
    ...     .jsonBody()
    ...     .items()
    ... ):
    ...     print("%s: %d" % (key, value))
    2010-02-21: 10
    2010-02-23: 8


Overrides
=========

    >>> from lp.services.webapp.interfaces import OAuthPermission
    >>> from lp.testing.pages import webservice_for_person
    >>> login("foo.bar@canonical.com")
    >>> override_source = test_publisher.getPubSource(
    ...     archive=cprov_db.archive, sourcename="testoverrides"
    ... )
    >>> override_binaries = test_publisher.getPubBinaries(
    ...     binaryname="testoverrides",
    ...     pub_source=override_source,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )
    >>> logout()
    >>> cprov_webservice = webservice_for_person(
    ...     cprov_db, permission=OAuthPermission.WRITE_PUBLIC
    ... )

    >>> cprov_archive_devel = webservice.get(
    ...     "/~cprov/+archive/ubuntu/ppa", api_version="devel"
    ... ).jsonBody()
    >>> pubs = webservice.named_get(
    ...     cprov_archive_devel["self_link"],
    ...     "getPublishedBinaries",
    ...     api_version="devel",
    ...     binary_name="testoverrides",
    ... ).jsonBody()
    >>> print(pubs["entries"][0]["section_name"])
    base
    >>> print(pubs["entries"][0]["priority_name"])
    STANDARD
    >>> package = pubs["entries"][0]["self_link"]

Anonymous users can't change overrides.

    >>> response = webservice.named_post(
    ...     package,
    ...     "changeOverride",
    ...     api_version="devel",
    ...     new_section="admin",
    ...     new_priority="optional",
    ... )
    >>> print(response)
    HTTP/1.1 401 Unauthorized
    ...

The owner of a PPA can change overrides.

    >>> response = cprov_webservice.named_post(
    ...     package,
    ...     "changeOverride",
    ...     api_version="devel",
    ...     new_section="admin",
    ...     new_priority="optional",
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

The override change takes effect:

    >>> pubs = webservice.named_get(
    ...     cprov_archive["self_link"],
    ...     "getPublishedBinaries",
    ...     binary_name="testoverrides",
    ... ).jsonBody()
    >>> print(pubs["entries"][0]["section_name"])
    admin
    >>> print(pubs["entries"][0]["priority_name"])
    OPTIONAL
