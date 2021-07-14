# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "CharmRecipeBuildMailer",
    ]

from lp.app.browser.tales import DurationFormatterAPI
from lp.services.config import config
from lp.services.mail.basemailer import (
    BaseMailer,
    RecipientReason,
    )
from lp.services.webapp import canonical_url


class CharmRecipeBuildMailer(BaseMailer):

    app = "charms"

    @classmethod
    def forStatus(cls, build):
        """Create a mailer for notifying about charm recipe build status.

        :param build: The relevant build.
        """
        requester = build.requester
        recipients = {requester: RecipientReason.forBuildRequester(requester)}
        return cls(
            "[Charm recipe build #%(build_id)d] %(build_title)s",
            "charmrecipebuild-notification.txt", recipients,
            config.canonical.noreply_from_address, "charm-recipe-build-status",
            build)

    def __init__(self, subject, template_name, recipients, from_address,
                 notification_type, build):
        super(CharmRecipeBuildMailer, self).__init__(
            subject, template_name, recipients, from_address,
            notification_type=notification_type)
        self.build = build

    def _getHeaders(self, email, recipient):
        """See `BaseMailer`."""
        headers = super(CharmRecipeBuildMailer, self)._getHeaders(
            email, recipient)
        headers["X-Launchpad-Build-State"] = self.build.status.name
        return headers

    def _getTemplateParams(self, email, recipient):
        """See `BaseMailer`."""
        build = self.build
        params = super(CharmRecipeBuildMailer, self)._getTemplateParams(
            email, recipient)
        params.update({
            "architecturetag": build.distro_arch_series.architecturetag,
            "build_duration": "",
            "build_id": build.id,
            "build_state": build.status.title,
            "build_title": build.title,
            "build_url": canonical_url(build),
            "builder_url": "",
            "distroseries": build.distro_series,
            "log_url": "",
            "project_name": build.recipe.project.name,
            "recipe_name": build.recipe.name,
            "upload_log_url": "",
            })
        if build.duration is not None:
            duration_formatter = DurationFormatterAPI(build.duration)
            params["build_duration"] = duration_formatter.approximateduration()
        if build.log is not None:
            params["log_url"] = build.log_url
        if build.upload_log is not None:
            params["upload_log_url"] = build.upload_log_url
        if build.builder is not None:
            params["builder_url"] = canonical_url(build.builder)
        return params

    def _getFooter(self, email, recipient, params):
        """See `BaseMailer`."""
        return ("%(build_url)s\n"
                "%(reason)s\n" % params)
