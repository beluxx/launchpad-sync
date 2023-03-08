# Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Copy Policy Classes.

The classes contain various policies about copying packages that can be
decided at runtime, such as whether to auto-accept a package or not.
"""

# All of this module's functionality can be reached through the
# ICopyPolicy adapter.
__all__ = []


from zope.interface import implementer

from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.soyuz.enums import PackageCopyPolicy
from lp.soyuz.interfaces.copypolicy import ICopyPolicy


class BasicCopyPolicy:
    """Useful standard copy policy.

    This policy auto-approves all PPA uploads.  For distribution archives it
    auto-approves only uploads to the Release pocket, and only while the
    series is not frozen.
    """

    def autoApproveNew(self, archive, distroseries=None, pocket=None):
        """See `ICopyPolicy`."""
        if archive.is_ppa:
            return True
        return False

    def autoApprove(self, archive, distroseries, pocket):
        """See `ICopyPolicy`."""
        if archive.is_ppa:
            return True

        # If the pocket is RELEASE or PROPOSED and we're not frozen then you
        # can upload to it.  Any other states mean the upload is unapproved.
        #
        # This check is orthogonal to the IArchive.canModifySuite check.
        auto_approve_pockets = (
            PackagePublishingPocket.RELEASE,
            PackagePublishingPocket.PROPOSED,
        )
        if (
            pocket in auto_approve_pockets
            and distroseries.isUnstable()
            and distroseries.status != SeriesStatus.FROZEN
        ):
            return True

        return False

    def send_email(self, archive):
        if archive.is_ppa:
            return False

        return True


@implementer(ICopyPolicy)
class InsecureCopyPolicy(BasicCopyPolicy):
    """A policy for copying from insecure sources."""

    enum_value = PackageCopyPolicy.INSECURE


@implementer(ICopyPolicy)
class MassSyncCopyPolicy(BasicCopyPolicy):
    """A policy for mass 'sync' copies.

    Exists solely so the classic job runner processes autosyncs last.
    """

    enum_value = PackageCopyPolicy.MASS_SYNC


policies = [
    InsecureCopyPolicy,
    MassSyncCopyPolicy,
]


enum_to_policy = {policy.enum_value: policy() for policy in policies}


def get_icopypolicy_for_packagecopypolicy(packagecopypolicy):
    """Look up the `ICopyPolicy` for a given `PackageCopyPolicy`."""
    return enum_to_policy[packagecopypolicy]
