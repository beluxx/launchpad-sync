Build files
===========

Create a test build.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher

    >>> login("foo.bar@canonical.com")

    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> test_publisher = SoyuzTestPublisher()
    >>> test_publisher.prepareBreezyAutotest()
    >>> test_publisher.addFakeChroots()
    >>> test_source = test_publisher.getPubSource(
    ...     archive=cprov.archive, sourcename="test-pkg", version="1.0"
    ... )
    >>> binary_pubs = test_publisher.getPubBinaries(
    ...     binaryname="test", pub_source=test_source
    ... )
    >>> deb = binary_pubs[0].binarypackagerelease.files[0].libraryfile
    >>> [build] = test_source.getBuilds()


IBuild provide a getFileByName() method, which returns one of the
following file type in its context.

 * Binary changesfile: '.changes';
 * Build logs: '.txt.gz';
 * Build upload logs: '_log.txt';
 * Built files: '*deb';

    >>> print(build.title)
    i386 build of test-pkg 1.0 in ubuntutest breezy-autotest RELEASE

Unsupported filename lookups also result in a `NotFoundError`.

    >>> build.getFileByName("biscuit.cookie")
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...'biscuit.cookie'

And unreachable files in `NotFoundError`.

    >>> build.getFileByName("boing.changes")
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...'boing.changes'

Retrieving a binary changesfile.  "test_1.0_i386.changes" is created when
SoyuzTestPublisher creates the "test" binary publication.

    >>> print(build.upload_changesfile.filename)
    test_1.0_i386.changes

    >>> build.upload_changesfile == build.getFileByName(
    ...     build.upload_changesfile.filename
    ... )
    True

Adding and retrieving a buildlog.

    >>> build.log == build.getFileByName(build.log.filename)
    True

Adding and retrieving a upload_log.

    >>> upload_log_name = "upload_%d_log.txt" % build.id
    >>> build.storeUploadLog("i am an upload log")
    >>> build.upload_log == build.getFileByName(upload_log_name)
    True

Retrieve a built file:

    >>> deb == build.getFileByName("test_1.0_all.deb")
    True

We can also retrieve the corresponding BinaryPackageFile:

    >>> bpf = build.getBinaryPackageFileByName("test_1.0_all.deb")
    >>> bpf
    <...BinaryPackageFile object ...>
    >>> bpf.libraryfile == deb
    True
