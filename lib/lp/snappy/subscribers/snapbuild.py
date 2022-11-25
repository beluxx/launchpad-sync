# Copyright 2016-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Event subscribers for snap builds."""

from zope.component import getUtility

from lp.buildmaster.enums import BuildStatus
from lp.services.scripts import log
from lp.services.webapp.publisher import canonical_url
from lp.services.webhooks.interfaces import IWebhookSet
from lp.services.webhooks.payload import compose_webhook_payload
from lp.snappy.interfaces.snapbuild import ISnapBuild
from lp.snappy.interfaces.snapbuildjob import ISnapStoreUploadJobSource


def _trigger_snap_build_webhook(snapbuild, action):
    payload = {
        "snap_build": canonical_url(snapbuild, force_local_path=True),
        "action": action,
    }
    payload.update(
        compose_webhook_payload(
            ISnapBuild,
            snapbuild,
            ["snap", "build_request", "status", "store_upload_status"],
        )
    )
    getUtility(IWebhookSet).trigger(snapbuild.snap, "snap:build:0.1", payload)


def snap_build_created(snapbuild, event):
    """Trigger events when a new snap package build is created."""
    _trigger_snap_build_webhook(snapbuild, "created")


def snap_build_status_changed(snapbuild, event):
    """Trigger events when snap package build statuses change."""
    _trigger_snap_build_webhook(snapbuild, "status-changed")

    if snapbuild.status == BuildStatus.FULLYBUILT:
        if snapbuild.snap.can_upload_to_store and snapbuild.snap.store_upload:
            log.info("Scheduling upload of %r to the store." % snapbuild)
            getUtility(ISnapStoreUploadJobSource).create(snapbuild)
        else:
            log.info(
                "%r is not configured for upload to the store."
                % snapbuild.snap
            )


def snap_build_store_upload_status_changed(snapbuild, event):
    """Trigger events when snap package build store upload statuses change."""
    _trigger_snap_build_webhook(snapbuild, "status-changed")
