# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views for TemporaryBlobStorage."""

__all__ = [
    "TemporaryBlobStorageAddView",
    "TemporaryBlobStorageNavigation",
    "TemporaryBlobStorageURL",
]

from zope.component import getUtility
from zope.interface import implementer

from lp.app.browser.launchpadform import LaunchpadFormView, action
from lp.bugs.interfaces.apportjob import IProcessApportBlobJobSource
from lp.services.librarian.interfaces.client import UploadFailed
from lp.services.temporaryblobstorage.interfaces import (
    BlobTooLarge,
    ITemporaryBlobStorage,
    ITemporaryStorageManager,
)
from lp.services.webapp import GetitemNavigation
from lp.services.webapp.interfaces import ICanonicalUrlData


class TemporaryBlobStorageAddView(LaunchpadFormView):
    # XXX: gary 2009-09-18 bug=31358
    # This page might be able to be removed after the referenced bug is
    # fixed and apport (Ubuntu's bug reporting tool) has been changed to use
    # it.
    schema = ITemporaryBlobStorage
    label = "Store BLOB"
    page_title = "Store a BLOB temporarily in Launchpad"
    field_names = ["blob"]
    for_input = True

    def initialize(self):
        # Need this hack here to ensure Action.__get__ doesn't add the view's
        # prefix to the action's __name__.  See note below to understand why
        # we need the action's name to be FORM_SUBMIT.
        self.actions = [action for action in self.actions]
        self.actions[0].__name__ = "FORM_SUBMIT"
        super().initialize()

    # NOTE: This action is named FORM_SUBMIT because apport depends on it
    # being named like that.
    @action("Continue", name="FORM_SUBMIT")
    def continue_action(self, action, data):
        uuid = self.store_blob(data["blob"])
        if uuid is not None:
            self.request.response.setHeader("X-Launchpad-Blob-Token", uuid)
            self.request.response.addInfoNotification(
                'Your ticket is "%s"' % uuid
            )

    def store_blob(self, blob):
        """Store a blob and return its UUID."""
        try:
            uuid = getUtility(ITemporaryStorageManager).new(blob)
        except BlobTooLarge:
            self.addError("Uploaded file was too large.")
            return None
        except UploadFailed:
            self.addError("File storage unavailable - try again later.")
            return None
        else:
            # Create ProcessApportBlobJob for the BLOB.
            blob = getUtility(ITemporaryStorageManager).fetch(uuid)
            getUtility(IProcessApportBlobJobSource).create(blob)
            return uuid


@implementer(ICanonicalUrlData)
class TemporaryBlobStorageURL:
    """Bug URL creation rules."""

    inside = None
    rootsite = None

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        """Return the path component of the URL."""
        return "temporary-blobs/%s" % self.context.uuid


class TemporaryBlobStorageNavigation(GetitemNavigation):
    """Navigation for temporary blobs."""

    usedfor = ITemporaryStorageManager

    def traverse(self, name):
        return getUtility(ITemporaryStorageManager).fetch(name)
