Soyuz Files
===========

Soyuz keeps a collection of source and binary packages classified as
SourcePackageRelease and BinaryPackageRelease respectively, each of
those records may contain one or more files according its type.

Those files are stored in the Librarian and related to their parent
object via a BinaryPackageFile or SourcePackageReleaseFile.

SourcePackageReleaseFile or BinaryPackageFile are available via the
'files' attribute on its parent.

    >>> from zope.component import getUtility
    >>> from lp.testing import verifyObject

    >>> from lp.services.librarian.interfaces import ILibraryFileAlias
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.soyuz.interfaces.files import (
    ...     IBinaryPackageFile,
    ...     ISourcePackageReleaseFile,
    ...     )

    >>> warty = getUtility(IDistributionSet)['ubuntu']['warty']


Source Files
------------

An ISourcePackageRelease contains the file that make up the source
package for that release:

   * An '.orig.tar.gz' file containing the upstream source distribution.
   * A '.diff.tar.gz' file containing the patches applied to the
     upstream source.
   * A '.dsc' package description file.

    >>> warty_firefox_srcpkg = warty.getSourcePackage(
    ...     'mozilla-firefox').currentrelease

    >>> srcfile = warty_firefox_srcpkg.files[0]

    >>> verifyObject(ISourcePackageReleaseFile, srcfile)
    True

    >>> verifyObject(ILibraryFileAlias, srcfile.libraryfile)
    True

    >>> print(srcfile.libraryfile.filename)
    firefox_0.9.2.orig.tar.gz

    >>> srcfile.libraryfile.http_url
    'http://.../3/firefox_0.9.2.orig.tar.gz'


Binary Files
------------

An IBinaryPackageRelease contains only one file which is the
instalable debian-format file:

   * An '.deb'

    >>> warty_i386_pmount_binpkg = warty['i386'].getBinaryPackage(
    ...    'pmount')['2:1.9-1']

    >>> print(warty_i386_pmount_binpkg.name)
    pmount

    >>> debfile = warty_i386_pmount_binpkg.files[0]

    >>> verifyObject(IBinaryPackageFile, debfile)
    True

    >>> verifyObject(ILibraryFileAlias, debfile.libraryfile)
    True

    >>> print(debfile.libraryfile.filename)
    pmount_1.9-1_all.deb

    >>> debfile.libraryfile.http_url
    'http://.../37/pmount_1.9-1_all.deb'
