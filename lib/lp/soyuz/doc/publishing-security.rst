===================
Publishing Security
===================

The publication records, SourcePackagePublishingHistory and
BinaryPackagePublishingHistory have a security adapter that prevents viewing
by unauthorised people.  For publications attached to a public archive, there
are no restrictions.  For those attached to a private archive, only those able
to view the archive, or admins, can see the publication.

We create two PPAs, one public and one private. Both PPAs are populated
with some source and binary publishings.

    >>> login("admin@canonical.com")
    >>> public_ppa = factory.makeArchive(private=False)
    >>> private_ppa = factory.makeArchive(private=True)
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> test_publisher = SoyuzTestPublisher()
    >>> test_publisher.prepareBreezyAutotest()
    >>> ignore = test_publisher.getPubBinaries(archive=public_ppa)
    >>> ignore = test_publisher.getPubBinaries(archive=private_ppa)


As an anonymous user we can get the first published source and binary out
the public PPA:

    >>> login(ANONYMOUS)
    >>> print(public_ppa.getPublishedSources().first().displayname)
    foo 666 in breezy-autotest

    >>> binary_pub = public_ppa.getAllPublishedBinaries()[0]
    >>> print(binary_pub.displayname)
    foo-bin 666 in breezy-autotest i386

A regular user can see them too:

    >>> login("no-priv@canonical.com")
    >>> print(public_ppa.getPublishedSources().first().displayname)
    foo 666 in breezy-autotest

    >>> binary_pub = public_ppa.getAllPublishedBinaries()[0]
    >>> print(binary_pub.displayname)
    foo-bin 666 in breezy-autotest i386

But when querying the private PPA, anonymous access will be refused:

    >>> login(ANONYMOUS)
    >>> source_pub = private_ppa.getPublishedSources().first()
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> binary_pub = private_ppa.getAllPublishedBinaries()[0]
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

As is for a regular user.

    >>> login("no-priv@canonical.com")
    >>> source_pub = private_ppa.getPublishedSources().first()
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> binary_pub = private_ppa.getAllPublishedBinaries()[0]
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

But the owner can see them.

    >>> ignored = login_person(private_ppa.owner)
    >>> print(public_ppa.getPublishedSources().first().displayname)
    foo 666 in breezy-autotest

    >>> binary_pub = private_ppa.getAllPublishedBinaries()[0]
    >>> print(binary_pub.displayname)
    foo-bin 666 in breezy-autotest i386

As can an administrator.

    >>> login("admin@canonical.com")
    >>> print(public_ppa.getPublishedSources().first().displayname)
    foo 666 in breezy-autotest

    >>> binary_pub = private_ppa.getAllPublishedBinaries()[0]
    >>> print(binary_pub.displayname)
    foo-bin 666 in breezy-autotest i386

