=============================
Finding PackageUpload records
=============================

PackageUpload records are available via a custom operation on
distroseries, getPackageUploads().

Each record exposes a number of properties.

    >>> distros = webservice.get("/distros").jsonBody()
    >>> ubuntu = distros['entries'][0]
    >>> warty = webservice.named_get(
    ...     ubuntu['self_link'], 'getSeries',
    ...     name_or_version='warty').jsonBody()

    >>> uploads = webservice.named_get(
    ...     warty['self_link'], 'getPackageUploads').jsonBody()

    >>> from lazr.restful.testing.webservice import pprint_entry
    >>> pprint_entry(uploads['entries'][0])
    archive_link: 'http://.../ubuntu/+archive/primary'
    copy_source_archive_link: None
    custom_file_urls: []
    date_created: ...
    display_arches: 'source'
    display_name: 'mozilla-firefox'
    display_version: '0.9'
    distroseries_link: 'http://.../ubuntu/warty'
    id: 11
    pocket: 'Release'
    resource_type_link: 'http://.../#package_upload'
    self_link: 'http://.../ubuntu/warty/+upload/11'
    status: 'Done'

getPackageUploads can filter on package names.

    >>> uploads = webservice.named_get(
    ...     warty['self_link'], 'getPackageUploads',
    ...     name='mozilla').jsonBody()
    >>> len(uploads['entries'])
    1
    >>> uploads = webservice.named_get(
    ...     warty['self_link'], 'getPackageUploads',
    ...     name='missing').jsonBody()
    >>> len(uploads['entries'])
    0


Retrieving Static Translation Files
===================================

Some uploads contain static translation tarballs (usually Gnome help files).
These are of particular interest to distribution developers who wish to
ship these separately from their distribution media.  The files can be
trivially retrieved using getPackageUploads and specifying a custom_type.

First, insert some data to retrieve:

    >>> login("admin@canonical.com")
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> from lp.soyuz.enums import PackageUploadCustomFormat
    >>> warty_series = getUtility(IDistributionSet)['ubuntu']['warty']
    >>> upload = warty_series.createQueueEntry(
    ...     pocket=PackagePublishingPocket.RELEASE, changesfilename="test",
    ...     changesfilecontent=b"test", archive=warty_series.main_archive)
    >>> arbitrary_file = factory.makeLibraryFileAlias(filename="custom1")
    >>> custom = upload.addCustom(
    ...     arbitrary_file, PackageUploadCustomFormat.STATIC_TRANSLATIONS)
    >>> arbitrary_file = factory.makeLibraryFileAlias(filename="custom2")
    >>> custom = upload.addCustom(
    ...     arbitrary_file, PackageUploadCustomFormat.STATIC_TRANSLATIONS)
    >>> logout()

getPackageUploads takes several optional filtering parameters, we need
to specify a custom_type of raw-translations-static to retrieve PackageUploads
that contain these file types.

    >>> uploads = webservice.named_get(
    ...     warty['self_link'], 'getPackageUploads', {},
    ...     custom_type='raw-translations-static').jsonBody()

Once we have the uploads, we can inspect the custom_file_urls property,
which is a list of URLs to librarian files:

    >>> for entry in uploads['entries']:
    ...     print(entry['display_name'])
    ...     print(pretty(entry['custom_file_urls']))
    custom1, custom2
    ['http://.../custom1', 'http://.../custom2']
