Package copy requests
=====================

Populating a copy archive from some other source archive is a potentially
long-lasting operation. Thus the population parameters are specified using
package copy requests and these requests are carried out in asynchronous
fashion.

Let's prepare a few things we'll need for the subsequent tests.

    >>> from lp.soyuz.adapters.packagelocation import build_package_location
    >>> from lp.soyuz.interfaces.packagecopyrequest import (
    ...     IPackageCopyRequest,
    ...     IPackageCopyRequestSet,
    ... )
    >>> from lp.soyuz.enums import ArchivePurpose, PackageCopyStatus
    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.soyuz.interfaces.archive import IArchiveSet

In order to instantiate a package copy request we require a source and
target package location.

    >>> source = build_package_location("ubuntutest", suite="breezy-autotest")
    >>> target = build_package_location("ubuntutest", suite="breezy-autotest")

We'll be using Celso's identity along with the 'ubuntutest' distribution
and a copy archive for rebuilds.

    >>> ubuntutest = getUtility(IDistributionSet)["ubuntutest"]
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> rebuild_archive = getUtility(IArchiveSet).new(
    ...     owner=cprov,
    ...     purpose=ArchivePurpose.COPY,
    ...     distribution=ubuntutest,
    ...     name="our-sample-copy-archive",
    ... )
    >>> target.archive = rebuild_archive

As well as Mark's identity and the 'ubuntu' distribution..

    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> snapshot_archive = getUtility(IArchiveSet).new(
    ...     owner=mark,
    ...     purpose=ArchivePurpose.COPY,
    ...     distribution=ubuntu,
    ...     name="our-sample-sbapshot-archive",
    ... )

.. and a package location targeting ubuntu/warty and a different copy
archive (for snapshots).

    >>> snapshot_target = build_package_location("ubuntu", "warty")
    >>> snapshot_target.archive = snapshot_archive

Finally, we have all that's needed to instantiate the package copy request.

    >>> pcr_set = getUtility(IPackageCopyRequestSet)
    >>> new_pcr = pcr_set.new(
    ...     source, target, cprov, reason="We need to test this stuff!"
    ... )

Let's have a look at it. Please note that the source and the target
components are not set by default. Also, the date started and completed are
not set either since this is a new package copy request.

    >>> print(new_pcr)
    Package copy request
    source = primary/breezy-autotest/-/RELEASE
    target = our-sample-copy-archive/breezy-autotest/-/RELEASE
    copy binaries: False
    requester: cprov
    status: NEW
    date created: ...
    date started: -
    date completed: -

    >>> verifyObject(IPackageCopyRequest, new_pcr)
    True

    >>> new_pcr.date_started is None
    True

    >>> new_pcr.date_completed is None
    True

Now let's instantiate more package copy requests in order to check some
of the filtering capabilities of the IPackageCopyRequestSet component.

    >>> inprogress_pcr = pcr_set.new(source, snapshot_target, mark)
    >>> inprogress_pcr.markAsInprogress()

Make sure the 'in progress' package copy request has its 'date_started'
property set.

    >>> inprogress_pcr.status == PackageCopyStatus.INPROGRESS
    True
    >>> inprogress_pcr.date_started is not None
    True

It should not have a "date completed" yet.

    >>> inprogress_pcr.date_completed is not None
    False

The completed package copy request will have a "date completed" set.

    >>> completed_pcr = pcr_set.new(source, target, cprov)
    >>> completed_pcr.markAsInprogress()
    >>> completed_pcr.markAsCompleted()

    >>> completed_pcr.status == PackageCopyStatus.COMPLETE
    True
    >>> completed_pcr.date_completed is not None
    True

The cancelled package copy request will have a "date completed" set as
well.

    >>> cancelled_pcr = pcr_set.new(source, snapshot_target, mark)
    >>> cancelled_pcr.markAsCancelled()

    >>> cancelled_pcr.status == PackageCopyStatus.CANCELLED
    True
    >>> cancelled_pcr.date_completed is not None
    True

Now let's query for Celso's package copy requests regardless of their
status.

    >>> cprov_pcrs = pcr_set.getByPersonAndStatus(cprov)
    >>> cprov_pcrs.count() == 2
    True

Make sure that the returned package copy requests do belong to Celso.

    >>> len([pcr for pcr in cprov_pcrs if pcr.requester != cprov]) == 0
    True

A package copy request in state "canceling" is somewhat similar to one in
state "in progress" i.e. it has a 'date_started' set but its status is
'CANCELING'.

    >>> canceling_pcr = pcr_set.new(source, snapshot_target, mark)

The package copy request has just been instantiated, has status "new" and
no 'date_started' value yet.

    >>> canceling_pcr.status == PackageCopyStatus.NEW
    True
    >>> canceling_pcr.date_started is None
    True

Now we change its status to 'canceling'.

    >>> canceling_pcr.markAsCanceling()

    >>> canceling_pcr.status == PackageCopyStatus.CANCELING
    True

Please note that marking a package copy requests as 'canceling' does not
affect its 'date_started' value.

    >>> canceling_pcr.date_started is None
    True

Now let's query for package copy requests belonging to a particular person
and being in a certain state.

    >>> cancelled_pcrs = pcr_set.getByPersonAndStatus(
    ...     mark, PackageCopyStatus.CANCELLED
    ... )
    >>> cancelled_pcrs.count() == 1
    True
    >>> cancelled_pcrs[0].status == PackageCopyStatus.CANCELLED
    True

Make sure that the returned package copy requests do belong to Mark.

    >>> len([pcr for pcr in cancelled_pcrs if pcr.requester != mark]) == 0
    True

Now let's exercise some of the other package copy request filtering
methods.

First we select all package copy requests with a matching source
distroseries.

    >>> breezy = ubuntutest["breezy-autotest"]
    >>> breezy_source_pcrs = pcr_set.getBySourceDistroSeries(breezy)

All five package copy requests have 'breezy-autotest' as their source
distroseries.

    >>> breezy_source_pcrs.count() == 5
    True

Make sure that the returned package copy requests do have the proper source
distroseries.

    >>> len(
    ...     [
    ...         pcr
    ...         for pcr in breezy_source_pcrs
    ...         if pcr.source_distroseries != breezy
    ...     ]
    ... ) == 0
    True

Now for the target distroseries, we are interested in package copy requests
that target 'warty'.

    >>> warty = ubuntu["warty"]
    >>> warty_target_pcrs = pcr_set.getByTargetDistroSeries(warty)

Three out of five package copy requests have 'warty' as their target
distroseries.

    >>> warty_target_pcrs.count() == 3
    True

Make sure that the returned package copy requests do have the proper target
distroseries.

    >>> len(
    ...     [
    ...         pcr
    ...         for pcr in warty_target_pcrs
    ...         if pcr.target_distroseries != warty
    ...     ]
    ... ) == 0
    True

Last but not least we want to see the package copy requests that target
the rebuild archive.

    >>> rebuild_pcrs = pcr_set.getByTargetArchive(rebuild_archive)
    >>> rebuild_pcrs.count() == 2
    True

    >>> len(
    ...     [
    ...         pcr
    ...         for pcr in rebuild_pcrs
    ...         if pcr.target_archive != rebuild_archive
    ...     ]
    ... ) == 0
    True

The archive must be set in both the source and the target location. Otherwise
the instantiation of the package copy request will fail.

    >>> target.archive = None
    >>> will_fail = pcr_set.new(source, target, cprov)
    Traceback (most recent call last):
    ...
    AssertionError: target archive must be set in package location

    >>> source.archive = None
    >>> will_fail_as_well = pcr_set.new(source, snapshot_target, mark)
    Traceback (most recent call last):
    ...
    AssertionError: source archive must be set in package location
