The IHasBuildRecords interface
==============================

The `IHasBuildRecords` interface provides functionality via inheritance
for working with builds.


Getting the build records for the object
----------------------------------------

Each class that implements `IHasBuildRecords` provides a getBuildRecords()
for accessing the builds related to the instance.

The method can be called without any arguments.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> hoary = ubuntu['hoary']
    >>> hoary.getBuildRecords().count()
    5

The method has a number of filtering options, such as filtering by build
status,

    >>> from lp.buildmaster.enums import BuildStatus
    >>> hoary.getBuildRecords(build_state=BuildStatus.FULLYBUILT).count()
    2

filtering by source package name,

    >>> hoary.getBuildRecords(name=u'pm').count()
    2

filtering by the pocket to which the build was published,

    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> hoary.getBuildRecords(
    ...     pocket=PackagePublishingPocket.RELEASE).count()
    5

and filtering by the build architecture tag.

    >>> builds = ubuntu['warty'].getBuildRecords(name=u'firefox',
    ...                                          arch_tag='i386')
    >>> for build in builds:
    ...     print(build.title)
    i386 build of mozilla-firefox 0.9 in ubuntu warty RELEASE


