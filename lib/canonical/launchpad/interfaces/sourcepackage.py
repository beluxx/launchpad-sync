# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class IPackages(Interface):
    """Root object for web app."""
    binary = Attribute("Binary packages")
    source = Attribute("Source packages")

    def __getitem__(name):
        """Retrieve a package set by name."""

class IPackageSet(Interface):
    """A set of packages"""
    def __getitem__(name):
        """Retrieve a package by name."""
    def __iter__():
        """Iterate over names"""

class ISourcePackageSet(IPackageSet):
    """A set of source packages"""

#
# Interface we expect a SourcePackage to provide.
#
class ISourcePackage(Interface):
    """A SourcePackage"""
    id = Int(title=_("ID"), required=True)
    maintainer = Int(title=_("Maintainer"), required=True)
    name = TextLine(title=_("Name"), required=True)
    title = TextLine(title=_("Title"), required=True)
    shortdesc = Text(title=_("Description"), required=True)
    description = Text(title=_("Description"), required=True)
    manifest = Int(title=_("Manifest"), required=False)
    distro = Int(title=_("Distribution"), required=False)
    sourcepackagename = Int(title=_("SourcePackage Name"), required=True)
    bugs = Attribute("bugs")
    ##XXX: (interface+attr) cprov 20041010
    ## I'm confused about how to declare new (abstract) attributes as
    ## following.
    product = Attribute("Product, or None")
    proposed = Attribute("A source package release with upload status of "
                         "PROPOSED, else None")

#
# Interface provied by a SourcePackageName. This is a tiny
# table that allows multiple SourcePackage entities to share
# a single name.
#
class ISourcePackageName(Interface):
    """Name of a SourcePackage"""
    id = Int(title=_("ID"), required=True)
    name = TextLine(title=_("Name"), required=True)



class ISourcePackageContainer(Interface):
    """A container for ISourcePackage objects."""

    def __getitem__(key):
        """Get an ISourcePackage by name"""

    def __iter__():
        """Iterate through SourcePackages."""

    def withBugs(self):
        """Return a sequence of SourcePackage, that have bugs assigned to
        them. In future, we might pass qualifiers to further limit the list
        that is returned, such as a name filter, or a bug assignment status
        filter."""


class ISourcePackageRelease(Interface):
    """A source package release, e.g. apache-utils 2.0.48-3"""
    # See the SourcePackageRelease table

    sourcepackage = Attribute("The source package this is a release for")
    creator = Attribute("Person that created this release")
    version = Attribute("A version string")
    dateuploaded = Attribute("Date of Upload")
    urgency = Attribute("Source Package Urgency")
    dscsigningkey = Attribute("DSC Signing Key")
    component = Attribute("Source Package Component")
    changelog = Attribute("Source Package Change Log")
    pkgurgency = Attribute("Source Package Urgency Translated using dbschema")

    binaries = Attribute("Binary Packages generated by this SourcePackageRelease")
    section = Attribute("Section this Source package Release belongs to")

    def branches():
        """Return the list of branches in a source package release"""


#
# SourcePackage related Applications Interfaces
#

class IDistroSourcesApp(Interface):
    """A Distribution Source Tag """
    distribution = Attribute("Distribution")

    def __getitem__(name):
        """retrieve sourcepackges by release"""

    def __iter__():
        """retrieve an iterator"""
     

class IDistroReleaseSourcesApp(Interface):
    """A Release Sources Proxy """
    release = Attribute("Release")
    
    def __getitem__(name):
        """Retrieve a package by name."""

    def __iter__():
        """Iterate over names"""

    def findPackagesByName():
        """Find packages by name."""

    def sourcePackagesBatch():
        """Return a batch of source packages."""

    
class IDistroReleaseSourceApp(Interface):
    """A SourcePackage Proxy """
    sourcepackage = Attribute("SourcePackage")
    releases = Attribute("SourcePackageReleases")
    proposed = Attribute("Proposed source package release")
    lastversions = Attribute("Last Release Versions")
    currentversions = Attribute("Current Release Versions")
    bugsCounter = Attribute("A tuple of bug counters")
    archs = Attribute("A tuple of architectures")
    
    def __getitem__(name):
        """Retrieve a package release by version."""

class IDistroReleaseSourceReleaseApp(Interface):
    """A SourcePackageRelease Proxy """
    sourcepackagerelease = Attribute("SourcePackageRelease")
    archs = Attribute("Builded archs")
    builddepends = Attribute("Builddepends for this sourcepackagerelease")
    builddependsindep = Attribute("BuilddependsIndep for this sourcepackagerelease")
    distroreleasename = Attribute("The Distro Release name need to make links to bin packages")

    def __getitem__(name):
        """Retrieve a package release build by arch."""

class IDistroReleaseSourceReleaseBuildApp(Interface):
        sourcepackagerelease = Attribute("SourcePackageRelease")
        arch = Attribute("Builded arch")
        build = Attribute("The SourcePackageRelease Build Table")


class IbuilddepsContainer(Interface):
    name = Attribute("Package name for a builddepends/builddependsindep")
    signal = Attribute("Dependence Signal e.g = >= <= <")
    version = Attribute("Package version for a builddepends/builddependsindep")

class ICurrentVersion(Interface):
    release = Attribute("The binary or source release object")
    currentversion = Attribute("Current version of A binary or source package")
    currentbuilds = Attribute("The current builds for binary or source package")


