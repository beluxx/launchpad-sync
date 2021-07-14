# Copyright 2009-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Common build interfaces."""

__metaclass__ = type

__all__ = [
    'BuildBaseImageType',
    'BuilderCleanStatus',
    'BuilderResetProtocol',
    'BuildStatus',
    'BuildQueueStatus',
    'BuildFarmJobType',
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )


class BuildStatus(DBEnumeratedType):
    """Build status type

    Builds exist in the database in a number of states such as 'complete',
    'needs build' and 'dependency wait'. We need to track these states in
    order to correctly manage the autobuilder queues in the BuildQueue table.
    """

    NEEDSBUILD = DBItem(0, """
        Needs building

        Build record is fresh and needs building. Nothing is yet known to
        block this build and it is a candidate for building on any free
        builder of the relevant architecture
        """)

    FULLYBUILT = DBItem(1, """
        Successfully built

        Build record is an historic account of the build. The build is
        complete and needs no further work to complete it. The build log etc
        are all in place if available.
        """)

    FAILEDTOBUILD = DBItem(2, """
        Failed to build

        Build record is an historic account of the build. The build failed and
        cannot be automatically retried. Either a new upload will be needed
        or the build will have to be manually reset into 'NEEDSBUILD' when
        the issue is corrected
        """)

    MANUALDEPWAIT = DBItem(3, """
        Dependency wait

        Build record represents a package whose build dependencies cannot
        currently be satisfied within the relevant DistroArchSeries. This
        build will have to be manually given back (put into 'NEEDSBUILD') when
        the dependency issue is resolved.
        """)

    CHROOTWAIT = DBItem(4, """
        Chroot problem

        Build record represents a build which needs a chroot currently known
        to be damaged or bad in some way. The buildd maintainer will have to
        reset all relevant CHROOTWAIT builds to NEEDSBUILD after the chroot
        has been fixed.
        """)

    SUPERSEDED = DBItem(5, """
        Build for superseded Source

        Build record represents a build which never got to happen because the
        source package release for the build was superseded before the job
        was scheduled to be run on a builder. Builds which reach this state
        will rarely if ever be reset to any other state.
        """)

    BUILDING = DBItem(6, """
        Currently building

        Build record represents a build which is being build by one of the
        available builders.
        """)

    FAILEDTOUPLOAD = DBItem(7, """
        Failed to upload

        Build record is an historic account of a build that could not be
        uploaded correctly. It's mainly genereated by failures in
        process-upload which quietly rejects the binary upload resulted
        by the build procedure.
        In those cases all the build historic information will be stored (
        buildlog, datebuilt, duration, builder, etc) and the buildd admins
        will be notified via process-upload about the reason of the rejection.
        """)

    UPLOADING = DBItem(8, """
        Uploading build

        The build has completed and is waiting to be processed by the
        upload processor.
        """)

    CANCELLING = DBItem(9, """
        Cancelling build

        A cancellation request was made for the build. It cannot be cancelled
        immediately because a request is made in the webapp but we need to
        wait for the buildd-manager to actually cancel it.
        """)

    CANCELLED = DBItem(10, """
        Cancelled build

        A build was cancelled. This is a terminal state.
        """)


class BuildFarmJobType(DBEnumeratedType):
    """Soyuz build farm job type.

    An enumeration with the types of jobs that may be run on the Soyuz build
    farm.
    """

    PACKAGEBUILD = DBItem(1, """
        Binary package build

        Build a source package.
        """)

    BRANCHBUILD = DBItem(2, """
        Branch build

        Build a package from a bazaar branch.
        """)

    RECIPEBRANCHBUILD = DBItem(3, """
        Recipe branch build

        Build a package from a bazaar branch and a recipe.
        """)

    TRANSLATIONTEMPLATESBUILD = DBItem(4, """
        Translation template build

        Generate translation templates from a bazaar branch.
        """)

    LIVEFSBUILD = DBItem(5, """
        Live filesystem build

        Build a live filesystem from an archive.
        """)

    SNAPBUILD = DBItem(6, """
        Snap package build

        Build a snap package from a recipe.
        """)

    OCIRECIPEBUILD = DBItem(7, """
        OCI image build

        Build an OCI image from a recipe.
        """)

    CHARMRECIPEBUILD = DBItem(8, """
        Charm recipe build

        Build a charm from a recipe.
        """)


class BuildQueueStatus(DBEnumeratedType):
    """Build queue status.

    The status of a job in the build farm queue. The queue record only
    exists while the job is running or waiting to run.

    Not to be confused with BuildStatus, which is persistent and
    includes values to represent the result of a completed job.
    """

    WAITING = DBItem(0, """
        Waiting

        The job is waiting to be run.
        """)

    RUNNING = DBItem(1, """
        Running

        The job is currently running.
        """)

    CANCELLING = DBItem(2, """
        Cancelling

        The job has been cancelled, so should be terminated.
        """)

    SUSPENDED = DBItem(3, """
        Suspended

        The job is suspended, so should not be run.
        """)


class BuilderCleanStatus(DBEnumeratedType):

    CLEAN = DBItem(0, """
        Clean

        The builder slave is ready for use.
        """)

    DIRTY = DBItem(1, """
        Dirty

        The builder slave is dirty and needs to be cleaned before use.
        """)

    CLEANING = DBItem(2, """
        Cleaning

        The builder slave is being cleaned.
        """)


class BuilderResetProtocol(DBEnumeratedType):

    PROTO_1_1 = DBItem(11, """
        1.1

        Original synchronous protocol with vm_host and buildd_name. The
        reset trigger must exit cleanly once the slave is reset and
        accepting requests.
        """)

    PROTO_2_0 = DBItem(20, """
        2.0

        Asynchronous protocol with vm_host and buildd_name. The reset
        trigger must exit cleanly once the request is accepted, and use
        the webservice to set Builder.clean_status back to 'Clean' when
        the slave is reset and accepting requests.
        """)


class BuildBaseImageType(DBEnumeratedType):
    """Build base image type

    The type of a base image that can be used for builds.
    """

    CHROOT = DBItem(0, "Chroot tarball")
    LXD = DBItem(1, "LXD image")
