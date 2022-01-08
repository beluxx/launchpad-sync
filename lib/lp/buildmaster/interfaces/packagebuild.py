# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for package-specific builds."""

__all__ = [
    'IPackageBuild',
    'IPackageBuildView',
    ]


from lazr.restful.declarations import exported
from lazr.restful.fields import Reference
from zope.interface import Attribute
from zope.schema import (
    Choice,
    Object,
    TextLine,
    )

from lp import _
from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob,
    IBuildFarmJobView,
    )
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.librarian.interfaces import ILibraryFileAlias
from lp.soyuz.interfaces.archive import IArchive


class IPackageBuildView(IBuildFarmJobView):
    """`IPackageBuild` methods that require launchpad.View."""

    archive = exported(
        Reference(
            title=_('Archive'), schema=IArchive,
            required=True, readonly=True,
            description=_('The Archive context for this build.')))

    pocket = exported(
        Choice(
            title=_('Pocket'), required=True,
            vocabulary=PackagePublishingPocket,
            description=_('The build targeted pocket.')))

    upload_log = Object(
        schema=ILibraryFileAlias, required=False,
        title=_('The LibraryFileAlias containing the upload log for a'
                'build resulting in an upload that could not be processed '
                'successfully. Otherwise it will be None.'))

    upload_log_url = exported(
        TextLine(
            title=_("Upload Log URL"), required=False,
            description=_("A URL for failed upload logs."
                          "Will be None if there was no failure.")))

    current_component = Attribute(
        'Component where the source related to this build was last '
        'published.')

    distribution = exported(
        Reference(
            schema=IDistribution,
            title=_("Distribution"), required=True,
            description=_("Shortcut for its distribution.")))

    distro_series = exported(
        Reference(
            schema=IDistroSeries,
            title=_("Distribution series"), required=True,
            description=_("Shortcut for its distribution series.")))

    def verifySuccessfulUpload():
        """Verify that the upload of this build completed successfully."""

    def storeUploadLog(content):
        """Store the given content as the build upload_log.

        :param content: string containing the upload-processor log output for
            the binaries created in this build.
        """

    def notify(extra_info=None):
        """Notify current build state to related people via email.

        :param extra_info: Optional extra information that will be included
            in the notification email. If the notification is for a
            failed-to-upload error then this must be the content of the
            upload log.
        """

    def getUploader(changes):
        """Return the person responsible for the upload.

        This is used to when checking permissions.

        :param changes: Changes file from the upload.
        """


class IPackageBuild(IPackageBuildView, IBuildFarmJob):
    """Attributes and operations specific to package build jobs."""
