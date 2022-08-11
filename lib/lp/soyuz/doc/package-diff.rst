Package Diff
============

The 'package-diff' subsystem allows users to request a diff between
two SourcePackageReleases.

The diff can be requested by any user with permission to view both
packages and will be performed frequently by our infrastructure.


Requesting a Diff
-----------------

First we have to retrieve a SourcePackageRelease from the sampledata,
let's use 'pmount' sources.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet

    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> pmount = ubuntu.getSourcePackage('pmount')

    >>> pmount_from = pmount.getVersion('0.1-1').sourcepackagerelease
    >>> pmount_to = pmount.getVersion('0.1-2').sourcepackagerelease

A packageDiff can be created from the two packages by calling
requestDiffTo(). It takes two arguments: the user requesting the
packageDiff, and the sourcepackagerelease to that has the changes.

Requesting a diff from pmount_0.1-1 to pmount_0.1-2.

    >>> cprov = getUtility(IPersonSet).getByName('cprov')
    >>> package_diff = pmount_from.requestDiffTo(
    ...     requester=cprov, to_sourcepackagerelease=pmount_to)

Let's inspect the PackageDiff record created.

    >>> from lp.testing import verifyObject
    >>> from lp.soyuz.interfaces.packagediff import IPackageDiff

    >>> verifyObject(IPackageDiff, package_diff)
    True

Its main attributes are:

 * 'requester', which maps to a `IPerson`, the user who made the diff
   request.

    >>> from lp.registry.interfaces.person import IPerson
    >>> verifyObject(IPerson, package_diff.requester)
    True

    >>> print(package_diff.requester.displayname)
    Celso Providelo

 * 'from_source', which maps to a `ISourcePackageRelease`, the base
   source used in the diff.

    >>> from lp.soyuz.interfaces.sourcepackagerelease import (
    ...     ISourcePackageRelease)
    >>> verifyObject(ISourcePackageRelease, package_diff.from_source)
    True

    >>> print(package_diff.from_source.title)
    pmount - 0.1-1

 * 'to_source', which maps to a `ISourcePackageRelease`, the result
   source used in the diff.

    >>> verifyObject(ISourcePackageRelease, package_diff.to_source)
    True

    >>> print(package_diff.to_source.title)
    pmount - 0.1-2

The PackageDiff record is not yet 'performed', so 'status' is PENDING
and both 'date_fulfilled' and 'diff_content' fields are empty.

    >>> print(package_diff.date_fulfilled)
    None

    >>> print(package_diff.diff_content)
    None

    >>> print(package_diff.status.name)
    PENDING

IPackageDiff offers a property that return the 'title' of the diff
request.

    >>> print(package_diff.title)
    diff from 0.1-1 to 0.1-2

IPackageDiff has a property which indicates whether a diff content
should be private or not. See section 'PackageDiff privacy' below.

    >>> print(package_diff.private)
    False

An attempt to record an already recorded DiffRequest will result in an
error:

    >>> dup_diff = pmount_from.requestDiffTo(
    ...     requester=cprov, to_sourcepackagerelease=pmount_to)
    Traceback (most recent call last):
    ...
    lp.soyuz.interfaces.packagediff.PackageDiffAlreadyRequested:
    diff from 0.1-1 to 0.1-2 has already been requested


Diff request for source uploads
-------------------------------

When a source package upload is processed, the upload-processor
already requests a package diff against the immediate ancestry.

Before starting let's enable the universe component and add the i386
chroot in hoary in order to be able to accept the NEW packages.

    >>> from lp.soyuz.model.component import ComponentSelection
    >>> from lp.services.librarian.model import LibraryFileAlias
    >>> from lp.soyuz.interfaces.component import IComponentSet

    >>> hoary = ubuntu.getSeries('hoary')
    >>> breezy_autotest = ubuntu.getSeries('breezy-autotest')

    >>> universe = getUtility(IComponentSet)['universe']
    >>> selection = ComponentSelection(
    ...     distroseries=hoary, component=universe)

    >>> fake_chroot = LibraryFileAlias.get(1)
    >>> hoary_i386 = hoary['i386']
    >>> unused = hoary_i386.addOrUpdateChroot(fake_chroot)
    >>> breezy_autotest_i386 = breezy_autotest['i386']
    >>> unused = breezy_autotest_i386.addOrUpdateChroot(fake_chroot)

`FakePackager` (see fakepackager.rst) handles the packaging and upload
of a new source series for us. We can use this to avoid messing with
sampledata to create valid packages.

    >>> from lp.soyuz.tests.fakepackager import FakePackager
    >>> login('foo.bar@canonical.com')
    >>> packager = FakePackager(
    ...     'biscuit', '1.0', 'foo.bar@canonical.com-passwordless.sec')

And setup the test_keys in order to build and upload signed packages.

    >>> from lp.testing.gpgkeys import import_public_test_keys
    >>> import_public_test_keys()

When the first version of 'biscuit' is uploaded, since there is no
suitable ancentry, no diff is requested.

    >>> packager.buildUpstream()
    >>> packager.buildSource(signed=False)
    >>> biscuit_one_pub = packager.uploadSourceVersion('1.0-1', policy='sync')

    >>> len(biscuit_one_pub.sourcepackagerelease.package_diffs)
    0

When 1.0-8 is uploaded and 1.0-1 is published, the upload-processor
requests a diff, since there is a suitable ancestry.

    >>> packager.buildVersion('1.0-8', changelog_text="cookies")
    >>> packager.buildSource(signed=False)
    >>> biscuit_eight_pub = packager.uploadSourceVersion(
    ...     '1.0-8', policy='sync')

    >>> [diff] = biscuit_eight_pub.sourcepackagerelease.package_diffs
    >>> print(diff.title)
    diff from 1.0-1 to 1.0-8

We will release ubuntu/hoary so we can upload to post-RELEASE pockets
and ubuntu/breezy-autotest.

    >>> from lp.registry.interfaces.series import SeriesStatus
    >>> hoary.status = SeriesStatus.CURRENT

We upload version '1.0-9' to hoary-updates and get the diff against
the last published version in the RELEASE pocket.

    >>> packager.buildVersion('1.0-9', changelog_text="cookies")
    >>> packager.buildSource(signed=False)
    >>> biscuit_nine_pub = packager.uploadSourceVersion(
    ...     '1.0-9', policy='sync', suite='hoary-updates')

    >>> [diff] = biscuit_nine_pub.sourcepackagerelease.package_diffs
    >>> print(diff.title)
    diff from 1.0-8 to 1.0-9

Now version 1.0-12 gets uploaded to the just opened distroseries. It
gets diffed against the last version present in the RELEASE pocket of
the previous distroseries and *not* the highest previous version
present in ubuntu distribution, the hoary-updates one.

    >>> packager.buildVersion('1.0-12', changelog_text="chips")
    >>> packager.buildSource(signed=False)
    >>> biscuit_twelve_pub = packager.uploadSourceVersion(
    ...     '1.0-12', policy='sync', suite='breezy-autotest')

    >>> [diff] = biscuit_twelve_pub.sourcepackagerelease.package_diffs
    >>> print(diff.title)
    diff from 1.0-8 to 1.0-12

The subsequent version uploaded to hoary-updates will get a diff
against 1.0-9.

    >>> packager.buildVersion('1.0-10', changelog_text="cookies")
    >>> packager.buildSource(signed=False)
    >>> biscuit_ten_pub = packager.uploadSourceVersion(
    ...     '1.0-10', policy='sync', suite='hoary-updates')

    >>> [diff] = biscuit_ten_pub.sourcepackagerelease.package_diffs
    >>> print(diff.title)
    diff from 1.0-9 to 1.0-10

An upload to other pocket, in this case hoary-proposed, will get a diff
against the last version in the RELEASE pocket.

    >>> packager.buildVersion('1.0-11', changelog_text="cookies")
    >>> packager.buildSource(signed=False)
    >>> biscuit_eleven_pub = packager.uploadSourceVersion(
    ...     '1.0-11', policy='sync', suite='hoary-proposed')

    >>> [diff] = biscuit_eleven_pub.sourcepackagerelease.package_diffs
    >>> print(diff.title)
    diff from 1.0-8 to 1.0-11

For testing diffs in the PPA context we need to activate the PPA for
Foo Bar.

    >>> from lp.soyuz.enums import ArchivePurpose
    >>> from lp.soyuz.interfaces.archive import IArchiveSet
    >>> foobar = getUtility(IPersonSet).getByName('name16')
    >>> ppa = getUtility(IArchiveSet).new(
    ...     owner=foobar, distribution=ubuntu, purpose=ArchivePurpose.PPA)

We will upload version 1.0-2 to Foo Bar's PPA and since it was never
published in the PPA context it will get a diff against the last
version in the PRIMARY archive in the RELEASE pocket.

    >>> packager.buildVersion('1.0-2', changelog_text="unterzeichnet")
    >>> packager.buildSource()
    >>> biscuit_two_pub = packager.uploadSourceVersion(
    ...     '1.0-2', archive=foobar.archive)

    >>> [diff] = biscuit_two_pub.sourcepackagerelease.package_diffs
    >>> print(diff.title)
    diff from 1.0-8 (in Ubuntu) to 1.0-2

A subsequent upload in the PPA context will get a diff against 1.0-2,
the version found in its context.

    >>> packager.buildVersion('1.0-3', changelog_text="unterzeichnet")
    >>> packager.buildSource()
    >>> biscuit_three_pub = packager.uploadSourceVersion(
    ...     '1.0-3', archive=foobar.archive)

    >>> [diff] = biscuit_three_pub.sourcepackagerelease.package_diffs
    >>> print(diff.title)
    diff from 1.0-2 to 1.0-3


Performing a Diff
-----------------

Now we will actually perform a package diff and look at the results.

In order for the uploaded files to be flushed to the librarian we need
to commit the transaction here.

    >>> import transaction
    >>> transaction.commit()

The auxiliary function below will facilitate the viewing of diff results.

    >>> import os
    >>> import re
    >>> import shutil
    >>> import subprocess
    >>> import tempfile

    >>> from lp.services.librarian.utils import copy_and_close

    >>> def get_diff_results(diff):
    ...     lfa = diff.diff_content
    ...     if lfa is None:
    ...         return None
    ...     lfa.open()
    ...     jail = tempfile.mkdtemp()
    ...     local = os.path.abspath('')
    ...     jail = tempfile.mkdtemp()
    ...     fhandle = open(os.path.join(jail, "the.diff.gz"), 'wb')
    ...     copy_and_close(lfa, fhandle)
    ...     os.chdir(jail)
    ...     p = subprocess.Popen(
    ...          ['gunzip', "the.diff.gz"], stdout=subprocess.PIPE)
    ...     p.communicate()
    ...     p = subprocess.Popen(
    ...          ['splitdiff', "-a", "-d", "-p1", "the.diff"],
    ...          stdout=subprocess.PIPE)
    ...     p.communicate()
    ...     diffs = [filename for filename in sorted(os.listdir('.'))
    ...              if filename != 'the.diff']
    ...     ordered_diff_contents = [
    ...         re.sub(r'^diff .*\n', '', open(diff).read(), flags=re.M)
    ...         for diff in diffs]
    ...     os.chdir(local)
    ...     shutil.rmtree(jail)
    ...     return "".join(ordered_diff_contents)

Let's obtain the diff that was created when package "biscuit - 1.0-8"
was uploaded.

    >>> [diff] = biscuit_eight_pub.sourcepackagerelease.package_diffs

The PackageDiff record is not yet 'performed', so both,
'date_fulfilled' and 'diff_content' fields, are empty and 'status' is
PENDING.

    >>> print(diff.status.name)
    PENDING

    >>> print(diff.date_fulfilled)
    None

    >>> print(diff.diff_content)
    None

Performing the diff.

    >>> diff.performDiff()

The record is immediatelly updated, now the record contains a
'date_fulfilled', its status is COMPLETED and 'diff_content' points
to a LibraryFileAlias with a proper mimetype.

    >>> diff.date_fulfilled is not None
    True

    >>> print(diff.status.name)
    COMPLETED

    >>> print(diff.diff_content.filename)
    biscuit_1.0-1_1.0-8.diff.gz

    >>> print(diff.diff_content.mimetype)
    application/gzipped-patch

    >>> print(diff.diff_content.restricted)
    False

Since it stores the diff results in the librarian we need to commit the
transaction before we can access the file.

    >>> transaction.commit()

Now we can compare the package diff outcome to the debdiff output
(obtained manually on the shell) for the packages in question.

    >>> print(get_diff_results(diff))
    --- biscuit-1.0/contents
    +++ biscuit-1.0/contents
    @@ -2,0 +3 @@
    +1.0-8
    --- biscuit-1.0/debian/changelog
    +++ biscuit-1.0/debian/changelog
    @@ -1,3 +1,9 @@
    +biscuit (1.0-8) hoary; urgency=low
    +
    +  * cookies
    +
    + -- Foo Bar <foo.bar@canonical.com>  ...
    +
     biscuit (1.0-1) hoary; urgency=low
    <BLANKLINE>
       * Initial Upstream package
    <BLANKLINE>

The Librarian serves package-diff files with 'gzip' content-encoding
and 'text/plain' content-type. This combination instructs the browser
to decompress the file and display it inline, which makes it easier
for users to view it.

    >>> from lp.services.webapp.url import urlparse
    >>> parsed_url = urlparse(diff.diff_content.http_url)
    >>> netloc, path = parsed_url[1:3]

    >>> import http.client
    >>> con = http.client.HTTPConnection(netloc)
    >>> con.request("HEAD", path)
    >>> resp = con.getresponse()

    >>> print(resp.getheader('content-encoding'))
    gzip

    >>> print(resp.getheader('content-type'))
    text/plain


Dealing with all PackageDiff objects
------------------------------------

The PackageDiffSet utility implements simple auxiliary methods to deal
directly with PackageDiffs objects.

Let's flush all the updates done.

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> flush_database_updates()

Those methods are useful when the callsites are not interested only in
PackageDiffs attached to specific SourcePackageReleases.

Using the utility it's possible to iterate over all PackageDiff
stored.

    >>> from lp.soyuz.interfaces.packagediff import IPackageDiffSet
    >>> packagediff_set = getUtility(IPackageDiffSet)

    >>> def print_diffs(diff_set):
    ...     diffs = list(diff_set)
    ...     diff_first_id = diffs[0].id
    ...     for diff in diff_set:
    ...         id_diff = diff.id - diff_first_id
    ...         print(diff.from_source.name, diff.title,
    ...               diff.date_fulfilled is not None, id_diff)

    >>> print_diffs(packagediff_set)
    biscuit diff from 1.0-2 to 1.0-3               False   0
    biscuit diff from 1.0-8 (in Ubuntu) to 1.0-2   False  -1
    biscuit diff from 1.0-8 to 1.0-11              False  -2
    biscuit diff from 1.0-9 to 1.0-10              False  -3
    biscuit diff from 1.0-8 to 1.0-12              False  -4
    biscuit diff from 1.0-8 to 1.0-9               False  -5
    biscuit diff from 1.0-1 to 1.0-8               True   -6
    pmount diff from 0.1-1 to 0.1-2                False  -7

All package diffs targeting a set of source package releases can also
be requested.  The results are ordered by the source package release
ID:

    >>> sprs = [biscuit_eight_pub.sourcepackagerelease,
    ...         biscuit_nine_pub.sourcepackagerelease]
    >>> print_diffs(packagediff_set.getDiffsToReleases(sprs))
    biscuit diff from 1.0-1 to 1.0-8 True 0
    biscuit diff from 1.0-8 to 1.0-9 False 1

The method will return an empty result if no source package releases
are passed to it:

    >>> packagediff_set.getDiffsToReleases([]).count()
    0

A arbitrary PackageDiff object can be easily retrieved by database ID
if necessary.

    >>> [diff] = biscuit_eight_pub.sourcepackagerelease.package_diffs
    >>> candidate_diff = packagediff_set.get(diff.id)
    >>> candidate_diff == diff
    True


Special circumstances
---------------------

There is only one way a PackageDiff request will result in an empty
diff, when the same source package is re-uploaded.

To emulate this situation we will upload a new package called
'staging' first to the ubuntu primary archive, which will result in no
diff since the package is NEW, and then we will upload the same
version to the Foo Bar's PPA.

Note that this is a legitimate use-case, let's say Foo Bar user
suspects 'staging' will be affected by their new toolchain, already
hosted in the PPA. Since they cannot copy the primary archive sources,
they simply re-upload the source as it is in ubuntu to their PPA and check
if it builds correctly.

    >>> packager = FakePackager(
    ...     'staging', '1.0', 'foo.bar@canonical.com-passwordless.sec')

    >>> packager.buildUpstream(suite='breezy-autotest')
    >>> packager.buildSource()
    >>> staging_ubuntu_pub = packager.uploadSourceVersion(
    ...     '1.0-1', policy='sync')
    >>> len(staging_ubuntu_pub.sourcepackagerelease.package_diffs)
    0

    >>> staging_ppa_pub = packager.uploadSourceVersion(
    ...     '1.0-1', archive=foobar.archive)
    >>> [diff] = staging_ppa_pub.sourcepackagerelease.package_diffs
    >>> print(diff.title)
    diff from 1.0-1 (in Ubuntu) to 1.0-1

Commit the transaction for make the uploaded files available in
librarian:

    >>> transaction.commit()

Perform the pending diff request and commit the transaction again, so
the diff file can be retrieved.

    >>> diff.performDiff()
    >>> transaction.commit()

The PackageDiff request was correctly performed and the result is a
empty library file, which is what the user expects.

    >>> print(diff.status.name)
    COMPLETED

    >>> diff.date_fulfilled is not None
    True

    >>> print(diff.diff_content.filename)
    staging_1.0-1_1.0-1.diff.gz

    >>> print(get_diff_results(diff))
    <BLANKLINE>

Now we will simulate a version collision when generating the diff.

First we upload a version of 'collision' source package to the ubuntu
primary archive.

    >>> packager = FakePackager(
    ...     'collision', '1.0', 'foo.bar@canonical.com-passwordless.sec')

    >>> packager.buildUpstream(suite='breezy-autotest')
    >>> packager.buildSource()
    >>> collision_ubuntu_pub = packager.uploadSourceVersion(
    ...     '1.0-1', policy='sync')
    >>> len(collision_ubuntu_pub.sourcepackagerelease.package_diffs)
    0

Then we taint the package content and rebuild the same source package
version before uploading it again to Foo Bar's PPA.

    >>> packager._appendContents('I am evil.')
    >>> packager.buildSource()

    >>> collision_ppa_pub = packager.uploadSourceVersion(
    ...     '1.0-1', archive=foobar.archive)
    >>> [diff] = collision_ppa_pub.sourcepackagerelease.package_diffs
    >>> print(diff.title)
    diff from 1.0-1 (in Ubuntu) to 1.0-1

Note that, despite of having the same name and version, the diff.gz
and dsc files have different contents.

    >>> file_set = set()

    >>> for file in diff.from_source.files:
    ...     lfa = file.libraryfile
    ...     file_set.add((lfa.filename, lfa.content.md5))

    >>> for file in diff.to_source.files:
    ...     lfa = file.libraryfile
    ...     file_set.add((lfa.filename, lfa.content.md5))

    >>> distinct_files = [filename for filename, md5 in file_set]
    >>> for filename in sorted(distinct_files):
    ...     print(filename)
    collision_1.0-1.diff.gz
    collision_1.0-1.diff.gz
    collision_1.0-1.dsc
    collision_1.0-1.dsc
    collision_1.0.orig.tar.gz

Such situation can happen due to the lack of consistency checks
between versions in ubuntu primary archive and versions in PPAs. From
the Soyuz code point of view the packages are consistent in their own
context and the fact that 'apt' might get in trouble when installing
packages from the PPA is considered an PPA maintainer issue, at
moment.

Let's do the commit dance again and generate the diff.

    >>> transaction.commit()
    >>> diff.performDiff()
    >>> transaction.commit()

The package-diff subsystem has dealt with the filename conflicts and
the diff was properly generated.

    >>> print(diff.status.name)
    COMPLETED

    >>> diff.date_fulfilled is not None
    True

    >>> print(diff.diff_content.filename)
    collision_1.0-1_1.0-1.diff.gz

    >>> print(get_diff_results(diff))
    --- collision-1.0/contents
    +++ collision-1.0/contents
    @@ -2,0 +3 @@
    +I am evil.
    <BLANKLINE>

The 'debdiff' application may fail to process the given pair of
sources, usually due to hardlink within the source package or other
very rare (thus unknown yet) conditions.

Anyway, the package-diff request infrastructure copes fine with
'debdiff' failures. When it happens the request is simply marked as
FAILED, this way it will not block the pending-diff processor neither
be processed again, unless it gets reset.

In order to cause a 'debdiff' failure we will taint the DSC file of an
uploaded source.

    >>> packager = FakePackager(
    ...     'broken-source', '1.0', 'foo.bar@canonical.com-passwordless.sec')

    >>> packager.buildUpstream(suite='breezy-autotest')
    >>> packager.buildSource()
    >>> ignore = packager.uploadSourceVersion('1.0-1', policy='sync')

    >>> packager.buildVersion('1.0-2', changelog_text="I am broken.")
    >>> packager.buildSource()
    >>> pub = packager.uploadSourceVersion(
    ...     '1.0-2', archive=foobar.archive)
    >>> transaction.commit()

    >>> from lp.services.librarianserver.testing.server import (
    ...     fillLibrarianFile)
    >>> [orig, upload_diff, dsc] = pub.sourcepackagerelease.files
    >>> fillLibrarianFile(dsc.libraryfile.id)

    >>> [broken_diff] = pub.sourcepackagerelease.package_diffs
    >>> print(broken_diff.title)
    diff from 1.0-1 (in Ubuntu) to 1.0-2

With a tainted DSC 'debdiff' cannot do much and fails, resulting in a
FAILED request (empty 'diff_content' and 'date_fulfilled').

    >>> broken_diff.performDiff()
    >>> transaction.commit()

    >>> print(broken_diff.status.name)
    FAILED

    >>> broken_diff.date_fulfilled is None
    True

    >>> print(broken_diff.diff_content)
    None


PackageDiff privacy
-------------------

Packagediff decides whether the 'diff_content' file should be
in the restricted librarian or not according to the privacy of the
archive where the targeted SourcePackageRelease ('to_source') were
originally uploaded to.

Let's use one of the diffs already requested in this test setup to
explain how this mechanism works.

    >>> [diff] = biscuit_two_pub.sourcepackagerelease.package_diffs
    >>> print(diff.title)
    diff from 1.0-8 (in Ubuntu) to 1.0-2

The chosen diff is for a source uploaded to a public PPA.

    >>> print(diff.to_source.upload_archive.displayname)
    PPA for Foo Bar

    >>> print(diff.to_source.upload_archive.private)
    False

Thus it's also considered public and the generated 'diff_content' is
stored in the public librarian.

    >>> print(diff.private)
    False

    >>> diff.performDiff()
    >>> transaction.commit()

    >>> print(diff.diff_content.restricted)
    False

If the diff is attached to a private PPA, the diff becomes 'private' and
the new 'diff_content' is stored in the restricted librarian instance.

    >>> private_ppa = factory.makeArchive(private=True)
    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(diff.to_source).upload_archive = private_ppa
    >>> removeSecurityProxy(biscuit_two_pub).archive = private_ppa

    >>> print(diff.private)
    True

    >>> diff.performDiff()
    >>> transaction.commit()

    >>> print(diff.diff_content.restricted)
    True
