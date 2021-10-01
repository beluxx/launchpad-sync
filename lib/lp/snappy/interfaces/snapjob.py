# Copyright 2018-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap job interfaces."""

__all__ = [
    'ISnapJob',
    'ISnapRequestBuildsJob',
    'ISnapRequestBuildsJobSource',
    ]

from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Datetime,
    Dict,
    List,
    Set,
    TextLine,
    )

from lp import _
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )
from lp.snappy.interfaces.snap import (
    ISnap,
    ISnapBuildRequest,
    )
from lp.snappy.interfaces.snapbuild import ISnapBuild
from lp.soyuz.interfaces.archive import IArchive


class ISnapJob(Interface):
    """A job related to a snap package."""

    job = Reference(
        title=_("The common Job attributes."), schema=IJob,
        required=True, readonly=True)

    snap = Reference(
        title=_("The snap package to use for this job."),
        schema=ISnap, required=True, readonly=True)

    metadata = Attribute(_("A dict of data about the job."))


class ISnapRequestBuildsJob(IRunnableJob):
    """A Job that processes a request for builds of a snap package."""

    requester = Reference(
        title=_("The person requesting the builds."), schema=IPerson,
        required=True, readonly=True)

    archive = Reference(
        title=_("The archive to associate the builds with."), schema=IArchive,
        required=True, readonly=True)

    pocket = Choice(
        title=_("The pocket that should be targeted."),
        vocabulary=PackagePublishingPocket, required=True, readonly=True)

    channels = Dict(
        title=_("Source snap channels to use for these builds."),
        description=_(
            "A dictionary mapping snap names to channels to use for these "
            "builds.  Currently only 'core', 'core18', 'core20', 'core22', "
            "and 'snapcraft' keys are supported."),
        key_type=TextLine(), required=False, readonly=True)

    architectures = Set(
        title=_("If set, limit builds to these architecture tags."),
        value_type=TextLine(), required=False, readonly=True)

    date_created = Datetime(
        title=_("Time when this job was created."),
        required=True, readonly=True)

    date_finished = Datetime(
        title=_("Time when this job finished."),
        required=True, readonly=True)

    error_message = TextLine(
        title=_("Error message resulting from running this job."),
        required=False, readonly=True)

    build_request = Reference(
        title=_("The build request corresponding to this job."),
        schema=ISnapBuildRequest, required=True, readonly=True)

    builds = List(
        title=_("The builds created by this request."),
        value_type=Reference(schema=ISnapBuild), required=True, readonly=True)


class ISnapRequestBuildsJobSource(IJobSource):

    def create(snap, requester, archive, pocket, channels, architectures=None):
        """Request builds of a snap package.

        :param snap: The snap package to build.
        :param requester: The person requesting the builds.
        :param archive: The IArchive to associate the builds with.
        :param pocket: The pocket that should be targeted.
        :param channels: A dictionary mapping snap names to channels to use
            for these builds.
        :param architectures: If not None, limit builds to architectures
            with these architecture tags (in addition to any other
            applicable constraints).
        """

    def findBySnap(snap, statuses=None, job_ids=None):
        """Find jobs for a snap.

        :param snap: A snap package to search for.
        :param statuses: An optional iterable of `JobStatus`es to search for.
        :param job_ids: An optional iterable of job IDs to search for.
        :return: A sequence of `SnapRequestBuildsJob`s with the specified
            snap.
        """

    def getBySnapAndID(snap, job_id):
        """Get a job by snap and job ID.

        :return: The `SnapRequestBuildsJob` with the specified snap and ID.
        :raises: `NotFoundError` if there is no job with the specified snap
            and ID, or its `job_type` is not `SnapJobType.REQUEST_BUILDS`.
        """

    def findBuildsForJobs(jobs, user=None):
        """Find builds resulting from an iterable of `SnapRequestBuildJob`s.

        :param jobs: An iterable of `SnapRequestBuildJob`s to search for.
        :param user: If passed, check that the builds are for archives
            visible by this user.  (No access checks are performed on the
            snaps or on the builds.)
        :return: A dictionary mapping `SnapRequestBuildJob` IDs to lists of
            their resulting builds.
        """
