Fake Packager Utility
=====================

FakePackager allows us to easily create minimal debian packages to be
used in tests.

    >>> import os
    >>> from lp.soyuz.tests.fakepackager import FakePackager


Setup and reset
---------------

When FakePackager is initialized it automatically creates a temporary
directory we call 'sandbox'. It's where the packages will get created.

    >>> packager = FakePackager("biscuit", "1.0")

    >>> print(packager.sandbox_path)
    /tmp/fakepackager-...

    >>> os.path.exists(packager.sandbox_path)
    True

Source 'name' and 'version' and 'gpg_key_fingerprint' are set according to
the arguments passed in the initialization.

    >>> print(packager.name)
    biscuit

    >>> print(packager.version)
    1.0

    >>> print(packager.gpg_key_fingerprint)
    None

The upstream directory is known but not yet created.

    >>> print(packager.upstream_directory)
    /tmp/fakepackager-.../biscuit-1.0

    >>> os.path.exists(packager.upstream_directory)
    False


Creating Packages
-----------------

Then we create it on disk based on the FakePackager templates.

    >>> packager.buildUpstream(build_orig=False)

It results in a buildable source package with the suffix '-1' appended
to the upstream version in the upstream_directory path.

    >>> os.path.exists(packager.upstream_directory)
    True

    >>> for name in sorted(os.listdir(packager.sandbox_path)):
    ...     print(name)
    ...
    biscuit-1.0

    >>> for name in sorted(os.listdir(packager.debian_path)):
    ...     print(name)
    ...
    changelog
    control
    copyright
    rules

We will instantiate a new packager so we can generate a new upstream
directory with a corresponding original tarball.

    >>> packager = FakePackager("biscuit", "1.0")
    >>> packager.buildUpstream()

    >>> for name in sorted(os.listdir(packager.sandbox_path)):
    ...     print(name)
    ...
    biscuit-1.0
    biscuit_1.0.orig.tar.gz

    >>> for name in sorted(os.listdir(packager.debian_path)):
    ...     print(name)
    ...
    changelog
    control
    copyright
    rules

Now we can build the source package using the generated tarball.

    >>> packager.buildSource(signed=False)

    >>> for changesfile in packager.listAvailableUploads():
    ...     print(changesfile)
    ...
    /tmp/fakepackager-.../biscuit_1.0-1_source.changes

    >>> changesfile_path = packager.listAvailableUploads()[0]
    >>> with open(changesfile_path) as changesfile:
    ...     print(changesfile.read())
    ...
    Format: ...
    Date: ...
    Source: biscuit...
    Architecture: source
    Version: 1.0-1
    Distribution: hoary
    Urgency: low
    Maintainer: Launchpad team <launchpad@lists.canonical.com>
    Changed-By: Foo Bar <foo.bar@canonical.com>...
    Changes:
     biscuit (1.0-1) hoary; urgency=low
     .
       * Initial Upstream package
    ...
     ... devel optional biscuit_1.0-1.dsc
     ... devel optional biscuit_1.0.orig.tar.gz
     ... devel optional biscuit_1.0-1.diff.gz...
    <BLANKLINE>

When we try to build an incompatible package version an error will be
raised indicating it could not created.

    >>> packager.buildVersion("2.0-2", changelog_text="version on crack.")
    Traceback (most recent call last):
    ...
    AssertionError: New versions should start with the upstream version: 1.0

Using a proper version, let's build a new source package version, but
now signing the DSC and the changesfile.

    >>> packager.buildVersion(
    ...     "1.0-2", changelog_text="Waar ligt de sleutel ?"
    ... )
    >>> packager.buildSource(include_orig=True)
    Traceback (most recent call last):
    ...
    AssertionError: Cannot build signed packages because the key is not set.

The error was raised because no signing key was set.

    >>> print(packager.gpg_key_fingerprint)
    None

A GPG key can only be set on initialization so we will have to create a
new packager passing a filename available in our test_keys directory.

    >>> packager = FakePackager(
    ...     "biscuit", "1.0", "foo.bar@canonical.com-passwordless.sec"
    ... )
    >>> packager.buildUpstream()
    >>> packager.buildSource()

GPG key set, now we are able to build a signed version.

    >>> print(packager.gpg_key_fingerprint)
    0xFD311613D941C6DE55737D310E3498675D147547

FakePackager also allows us to include as many versions it needs
before building the package. It helps when the content of the
changelog matters in the test context.

    >>> packager.buildVersion("1.0-2", changelog_text="cookies")
    >>> packager.buildVersion("1.0-3", changelog_text="butter cookies")
    >>> packager.buildSource(include_orig=False)

The generated changesfile contains a valid signature done by the
preset GPG key. All the job is done by `debuild` here, we are
basically checking we pass the right arguments to it.

    >>> changesfile_path = packager.listAvailableUploads()[1]
    >>> print(os.path.basename(changesfile_path))
    biscuit_1.0-3_source.changes

    >>> with open(changesfile_path, "rb") as changesfile:
    ...     content = changesfile.read()
    ...

    >>> from zope.component import getUtility
    >>> from lp.services.gpg.interfaces import IGPGHandler
    >>> gpghandler = getUtility(IGPGHandler)
    >>> sig = gpghandler.getVerifiedSignature(content)

    >>> sig.fingerprint == packager.gpg_key_fingerprint[2:]
    True

Continuing in the same 'sandbox', we can generate subsequent packages
for the same upstream source.

    >>> packager.buildVersion("1.0-4", changelog_text="uhmmm, leker")
    >>> packager.buildSource(include_orig=False)

Or, at any time, we can create another packager.

    >>> zeca_packager = FakePackager(
    ...     "zeca", "1.0", "foo.bar@canonical.com-passwordless.sec"
    ... )
    >>> zeca_packager.buildUpstream()
    >>> zeca_packager.buildSource()

    >>> zeca_packager.buildVersion("1.0-2", changelog_text="cookies")
    >>> zeca_packager.buildSource(include_orig=False)

And get back to the previous source.

    >>> packager.buildVersion("1.0-5", changelog_text="we, together, again.")
    >>> packager.buildSource(include_orig=False)

All generated changesfiles and related files are available in their
corresponding sandbox directory.

    >>> for changesfile in packager.listAvailableUploads():
    ...     print(changesfile)
    ...
    /tmp/fakepackager-.../biscuit_1.0-1_source.changes
    /tmp/fakepackager-.../biscuit_1.0-3_source.changes
    /tmp/fakepackager-.../biscuit_1.0-4_source.changes
    /tmp/fakepackager-.../biscuit_1.0-5_source.changes

    >>> for changesfile in zeca_packager.listAvailableUploads():
    ...     print(changesfile)
    ...
    /tmp/fakepackager-.../zeca_1.0-1_source.changes
    /tmp/fakepackager-.../zeca_1.0-2_source.changes

Finally, an error is raised if we try to build a source package before
creating the upstream directory.

    >>> canjica_packager = FakePackager("canjica", "1.0")
    >>> canjica_packager.buildSource()
    Traceback (most recent call last):
    ...
    AssertionError: Selected upstream directory does not exist: canjica-1.0


Uploading generated packages
----------------------------

FakePackage also allow the user to upload available packages using a
simplified upload-processor.

In order to upload packages we have to be logged in as an administrator.

    >>> login("foo.bar@canonical.com")

It also requires the public test gpg keys to be imported in the
database.

    >>> from lp.testing.gpgkeys import import_public_test_keys
    >>> import_public_test_keys()

The default upload target is ubuntu/hoary and since we will deal with
NEW packages, which defaults to 'universe' component, we have to
enable uploads for it.

    >>> from lp.soyuz.model.component import ComponentSelection
    >>> from lp.services.librarian.interfaces import ILibraryFileAliasSet
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.soyuz.interfaces.component import IComponentSet

    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> hoary = ubuntu.getSeries("hoary")
    >>> universe = getUtility(IComponentSet)["universe"]
    >>> selection = ComponentSelection(distroseries=hoary, component=universe)
    >>> fake_chroot = getUtility(ILibraryFileAliasSet)[1]
    >>> unused = hoary["i386"].addOrUpdateChroot(fake_chroot)
    >>> unused = hoary["hppa"].addOrUpdateChroot(fake_chroot)

Uploading a generated package is deadly simple: just call
`FakePackager.uploadSourceVersion()` passing the desired upload
version.

It raises an error if the version has not been generated.

    >>> upload = zeca_packager.uploadSourceVersion("6.6.6")
    Traceback (most recent call last):
    ...
    AssertionError: Could not find a source upload for version 6.6.6.

If the version is available, the package is uploaded, NEW packages are
automatically accepted, builds are created, the upload is published and
the source publishing record created are returned.

    >>> print(ubuntu.getSourcePackage("zeca"))
    None

    >>> zeca_pub = zeca_packager.uploadSourceVersion("1.0-1")

    >>> print(zeca_pub.displayname, zeca_pub.status.name)
    zeca 1.0-1 in hoary PENDING

    >>> len(zeca_pub.getBuilds())
    2

    >>> print(ubuntu.getSourcePackage("zeca").currentrelease.version)
    1.0-1

New uploaded versions will immediately show up as the current
version in ubuntu.

    >>> zeca_pub = zeca_packager.uploadSourceVersion("1.0-2")

    >>> len(zeca_pub.getBuilds())
    2

    >>> print(ubuntu.getSourcePackage("zeca").currentrelease.version)
    1.0-2

We can change the upload policy for a specific upload, for instance to
allow unsigned uploads.

    >>> biscuit_pub = packager.uploadSourceVersion("1.0-1", policy="sync")

    >>> len(biscuit_pub.getBuilds())
    2

    >>> print(ubuntu.getSourcePackage("biscuit").currentrelease.version)
    1.0-1

Since we are using Foo Bar's GPG key to sign packages, in order to test
PPA uploads we will create a PPA for it.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> foobar = getUtility(IPersonSet).getByName("name16")
    >>> print(foobar.archive)
    None

    >>> from lp.soyuz.enums import ArchivePurpose
    >>> from lp.soyuz.interfaces.archive import IArchiveSet
    >>> ppa = getUtility(IArchiveSet).new(
    ...     owner=foobar, distribution=ubuntu, purpose=ArchivePurpose.PPA
    ... )

So, uploading to a PPA only requires us to specify the target archive.

    >>> ppa_pub = packager.uploadSourceVersion(
    ...     "1.0-5", archive=foobar.archive
    ... )

    >>> print(ppa_pub.archive.displayname)
    PPA for Foo Bar

    >>> print(ppa_pub.displayname, ppa_pub.status.name)
    biscuit 1.0-5 in hoary PENDING

    >>> len(ppa_pub.getBuilds())
    1

Upload errors are raised when they happen. In this case, packages
signed by Foo Bar can't be uploaded to Celso's PPA.

    >>> cprov = getUtility(IPersonSet).getByName("cprov")

    >>> cprov_pub = packager.uploadSourceVersion(
    ...     "1.0-5", archive=cprov.archive
    ... )
    Traceback (most recent call last):
    ...
    AssertionError: Upload was rejected: Signer has no upload rights
    to this PPA.
