Uploading DDEBs
===============

DDEBs ('.ddeb' extension) are essentially a Debian binary packages,
they only use a different extension as a convenience to identify their
contents easily. They contain debug symbols stripped from one or more
packages during their build process.

On a client system, DDEB installation is optional, it's only necessary
for obtaining extra information about crashes in the corresponding
feature.

    >>> import transaction
    >>> from lp.services.config import config
    >>> from lp.testing.dbuser import switch_dbuser

    >>> from lp.soyuz.tests.test_publishing import (
    ...     SoyuzTestPublisher)

    >>> test_publisher = SoyuzTestPublisher()

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> hoary = ubuntu.getSeries('hoary')

    >>> unused = test_publisher.setUpDefaultDistroSeries(hoary)

We first upload a new source, 'debug - 1.0-1'. Because this is NEW,
it is in the queue awaiting overrides and acceptance.

    >>> src = getUploadForSource(
    ...     'suite/debug_1.0-1/debug_1.0-1_source.changes')
    >>> src.process()
    >>> result = src.do_accept()
    >>> print(src.queue_root.status.name)
    NEW
    >>> transaction.commit()

We don't really care where the source ends up, so we just accept the
default overrides. It is now pending publication.

    >>> src.queue_root.acceptFromQueue()
    >>> print(src.queue_root.status.name)
    DONE

    >>> src_pub = src.queue_root.archive.getPublishedSources(
    ...     name='debug', version='1.0-1', exact_match=True).one()

    >>> print(src_pub.displayname, src_pub.status.name)
    debug 1.0-1 in hoary PENDING

At this point a deb and a ddeb, produced during a normal build
process, are uploaded. This is exactly the same procedure used for
binary uploads with only ordinary debs.

    >>> bin = getUploadForBinary(
    ...     'suite/debug_1.0-1/debug_1.0-1_i386.changes')

Because the DEB is new, the binary upload is held in NEW.

    >>> bin.process()
    >>> result = bin.do_accept()
    >>> print(bin.queue_root.status.name)
    NEW

This upload has one build with two binaries: a DEB and its corresponding
DDEB.

    >>> build = bin.queue_root.builds[0].build
    >>> build.binarypackages.count()
    2
    >>> print(build.binarypackages[0].binpackageformat.name)
    DEB
    >>> print(build.binarypackages[1].binpackageformat.name)
    DDEB
    >>> build.binarypackages[0].debug_package == build.binarypackages[1]
    True
    >>> build.binarypackages[1].debug_package is None
    True

We override the binary to main/devel, and accept it into the archive.

    >>> from operator import attrgetter
    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> from lp.soyuz.interfaces.section import ISectionSet
    >>> main = getUtility(IComponentSet)['main']
    >>> universe = getUtility(IComponentSet)['universe']
    >>> devel = getUtility(ISectionSet)['devel']

    >>> switch_dbuser('launchpad')

    >>> bin.queue_root.overrideBinaries(
    ...     [{"component": main, "section": devel}], [main, universe])
    True
    >>> bin.queue_root.acceptFromQueue()

    >>> print(bin.queue_root.status.name)
    ACCEPTED

    >>> switch_dbuser(config.uploadqueue.dbuser)

    >>> bin_pubs = sorted(
    ...     bin.queue_root.realiseUpload(), key=attrgetter('displayname'))

    >>> switch_dbuser('uploader')

Now, both, binary and debug-symbol packages are pending publication.

    >>> for bin_pub in bin_pubs:
    ...     print('%s %s %s %s' % (
    ...         bin_pub.displayname, bin_pub.status.name,
    ...         bin_pub.component.name, bin_pub.section.name))
    debug-bin 1.0-1 in hoary i386 PENDING main devel
    debug-bin-dbgsym 1.0-1 in hoary i386 PENDING main devel

DEBs and DDEBs are uploaded to separate archives, because the size
impact of uploading them to a single archive on mirrors would be
unacceptable.

The DDEB is stored appropriately in the database.

    >>> [deb_pub, ddeb_pub] = bin_pubs
    >>> ddeb = ddeb_pub.binarypackagerelease

    >>> print(ddeb.title)
    debug-bin-dbgsym-1.0-1

The corresponding `BinaryPackageRelease` is recorded with DDEB format.

    >>> print(ddeb.binpackageformat.name)
    DDEB

And its corresponding file is also stored as DDEB filetype.

    >>> for bin_file in ddeb.files:
    ...     print(bin_file.libraryfile.filename, bin_file.filetype.name)
    debug-bin-dbgsym_1.0-1_i386.ddeb DDEB


Mismatched DDEBs
----------------

Each uploaded DDEB must be associated with a normal DEB. Any duplicated
DDEBs or DDEBs without matching DEBs will cause the upload to be
rejected.

    >>> bin = getUploadForBinary(
    ...     'suite/debug_1.0-1_broken/debug_1.0-1_i386.changes')
    >>> bin.process()
    >>> bin.is_rejected
    True
    >>> print(bin.rejection_message)
    Orphaned debug packages: not-debug-bin-dbgsym 1.0-1 (i386)
