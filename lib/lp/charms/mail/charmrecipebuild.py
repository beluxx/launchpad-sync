# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "CharmRecipeBuildMailer",
]

from lp.app.browser.tales import DurationFormatterAPI
from lp.services.config import config
from lp.services.mail.basemailer import BaseMailer, RecipientReason
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
            "charmrecipebuild-notification.txt",
            recipients,
            config.canonical.noreply_from_address,
            "charm-recipe-build-status",
            build,
        )

    @classmethod
    def forUnauthorizedUpload(cls, build):
        """Create a mailer for notifying about unauthorized Charmhub uploads.

        :param build: The relevant build.
        """
        requester = build.requester
        recipients = {requester: RecipientReason.forBuildRequester(requester)}
        return cls(
            "Charmhub authorization failed for %(recipe_name)s",
            "charmrecipebuild-unauthorized.txt",
            recipients,
            config.canonical.noreply_from_address,
            "charm-recipe-build-upload-unauthorized",
            build,
        )

    @classmethod
    def forUploadFailure(cls, build):
        """Create a mailer for notifying about Charmhub upload failures.

        :param build: The relevant build.
        """
        requester = build.requester
        recipients = {requester: RecipientReason.forBuildRequester(requester)}
        return cls(
            "Charmhub upload failed for %(recipe_name)s",
            "charmrecipebuild-uploadfailed.txt",
            recipients,
            config.canonical.noreply_from_address,
            "charm-recipe-build-upload-failed",
            build,
        )

    @classmethod
    def forUploadReviewFailure(cls, build):
        """Create a mailer for notifying about Charmhub upload review failures.

        :param build: The relevant build.
        """
        requester = build.requester
        recipients = {requester: RecipientReason.forBuildRequester(requester)}
        return cls(
            "Charmhub upload review failed for %(recipe_name)s",
            "charmrecipebuild-reviewfailed.txt",
            recipients,
            config.canonical.noreply_from_address,
            "charm-recipe-build-upload-review-failed",
            build,
        )

    @classmethod
    def forReleaseFailure(cls, build):
        """Create a mailer for notifying about Charmhub release failures.

        :param build: The relevant build.
        """
        requester = build.requester
        recipients = {requester: RecipientReason.forBuildRequester(requester)}
        return cls(
            "Charmhub release failed for %(recipe_name)s",
            "charmrecipebuild-releasefailed.txt",
            recipients,
            config.canonical.noreply_from_address,
            "charm-recipe-build-release-failed",
            build,
        )

    def __init__(
        self,
        subject,
        template_name,
        recipients,
        from_address,
        notification_type,
        build,
    ):
        super().__init__(
            subject,
            template_name,
            recipients,
            from_address,
            notification_type=notification_type,
        )
        self.build = build

    def _getHeaders(self, email, recipient):
        """See `BaseMailer`."""
        headers = super()._getHeaders(email, recipient)
        headers["X-Launchpad-Build-State"] = self.build.status.name
        return headers

    def _getTemplateParams(self, email, recipient):
        """See `BaseMailer`."""
        build = self.build
        upload_job = build.last_store_upload_job
        if upload_job is None:
            error_message = ""
        else:
            error_message = upload_job.error_message or ""
        params = super()._getTemplateParams(email, recipient)
        params.update(
            {
                "architecturetag": build.distro_arch_series.architecturetag,
                "build_duration": "",
                "build_id": build.id,
                "build_state": build.status.title,
                "build_title": build.title,
                "build_url": canonical_url(build),
                "builder_url": "",
                "store_error_message": error_message,
                "distroseries": build.distro_series,
                "log_url": "",
                "project_name": build.recipe.project.name,
                "recipe_authorize_url": canonical_url(
                    build.recipe, view_name="+authorize"
                ),
                "recipe_name": build.recipe.name,
                "upload_log_url": "",
            }
        )
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
        return "%(build_url)s\n%(reason)s\n" % params
