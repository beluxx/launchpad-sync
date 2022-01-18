# Copyright 2009-2022 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for build farm job behaviours."""

__all__ = [
    'IBuildFarmJobBehaviour',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )


class IBuildFarmJobBehaviour(Interface):

    builder_type = Attribute(
        "The name of the builder type to use for this build, corresponding "
        "to a launchpad-buildd build manager tag.")

    image_types = Attribute(
        "A list of `BuildBaseImageType`s indicating which types of base "
        "images can be used for this build.")

    build = Attribute("The `IBuildFarmJob` to build.")

    archive = Attribute("The `Archive` to build against.")

    distro_arch_series = Attribute("The `DistroArchSeries` to build against.")

    pocket = Attribute("The `PackagePublishingPocket` to build against.")

    def setBuilder(builder, worker):
        """Sets the associated builder and worker for this instance."""

    def determineFilesToSend():
        """Work out which files to send to the builder.

        :return: A dict mapping filenames to dicts as follows, or a Deferred
                resulting in the same::
            'sha1': SHA-1 of file content
            'url': URL from which the builder can fetch content
            'username' (optional): username to authenticate as
            'password' (optional): password to authenticate with
        """

    def issueMacaroon():
        """Issue a macaroon to access private resources for this build.

        :raises NotImplementedError: if the build type does not support
            accessing private resources.
        :return: A Deferred that calls back with a serialized macaroon or a
            fault.
        """

    def extraBuildArgs(logger=None):
        """Return extra arguments required by the builder for this build.

        :param logger: An optional logger.
        :return: A dict of builder arguments, or a Deferred resulting in the
            same.
        """

    def composeBuildRequest(logger):
        """Compose parameters for a worker build request.

        :param logger: A logger to be used to log diagnostic information.
        :return: A tuple of (
            "builder type", `DistroArchSeries` to build against,
            `PackagePublishingPocket` to build against,
            {filename: `sendFileToWorker` arguments}, {extra build arguments}),
            or a Deferred resulting in the same.
        """

    def dispatchBuildToWorker(logger):
        """Dispatch a specific build to the worker.

        :param logger: A logger to be used to log diagnostic information.
        """

    def verifyBuildRequest(logger):
        """Carry out any pre-build checks.

        :param logger: A logger to be used to log diagnostic information.
        """

    def verifySuccessfulBuild():
        """Check that we are allowed to collect this successful build."""

    def handleStatus(bq, worker_status):
        """Update the build from a worker's status response.

        :param bq: The `BuildQueue` currently being processed.
        :param worker_status: Worker status dict from `BuilderWorker.status`.
        """
