# Copyright 2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `OCIRecipeUpload`."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import json
import os

from storm.store import Store

from lp.archiveuploader.tests.test_uploadprocessor import (
    TestUploadProcessorBase,
    )
from lp.archiveuploader.uploadprocessor import (
    UploadHandler,
    UploadStatusEnum,
    )
from lp.buildmaster.enums import BuildStatus
from lp.oci.interfaces.ocirecipe import OCI_RECIPE_ALLOW_CREATE
from lp.services.features.testing import FeatureFixture
from lp.services.osutils import write_file
from lp.services.propertycache import get_property_cache


class TestOCIRecipeUploads(TestUploadProcessorBase):

    def setUp(self):
        super(TestOCIRecipeUploads, self).setUp()
        self.useFixture(FeatureFixture({OCI_RECIPE_ALLOW_CREATE: 'on'}))

        self.setupBreezy()

        self.switchToAdmin()
        self.build = self.factory.makeOCIRecipeBuild()
        Store.of(self.build).flush()
        self.switchToUploader()
        self.options.context = "buildd"

        self.uploadprocessor = self.getUploadProcessor(
            self.layer.txn, builds=True)

        self.digests = [{
            "diff_id_1": {
                "digest": "digest_1",
                "source": "test/base_1",
                "layer_id": "layer_1"
            },
            "diff_id_2": {
                "digest": "digest_2",
                "source": "",
                "layer_id": "layer_2"
            }
        }]

    def test_sets_build_and_state(self):
        # The upload processor uploads files and sets the correct status.
        self.assertFalse(self.build.verifySuccessfulUpload())
        del get_property_cache(self.build).manifest
        del get_property_cache(self.build).digests
        upload_dir = os.path.join(
            self.incoming_folder, "test", str(self.build.id), "ubuntu")
        write_file(os.path.join(upload_dir, "layer_1.tar.gz"), b"layer_1")
        write_file(os.path.join(upload_dir, "layer_2.tar.gz"), b"layer_2")
        write_file(
            os.path.join(upload_dir, "digests.json"), json.dumps(self.digests))
        write_file(os.path.join(upload_dir, "manifest.json"), b"manifest")
        handler = UploadHandler.forProcessor(
            self.uploadprocessor, self.incoming_folder, "test", self.build)
        result = handler.processOCIRecipe(self.log)
        self.assertEqual(
            UploadStatusEnum.ACCEPTED, result,
            "OCI upload failed\nGot: %s" % self.log.getLogBuffer())
        self.assertEqual(BuildStatus.FULLYBUILT, self.build.status)
        self.assertTrue(self.build.verifySuccessfulUpload())

    def test_requires_digests(self):
        # The upload processor fails if the upload does not contain the
        # digests file
        self.assertFalse(self.build.verifySuccessfulUpload())
        del get_property_cache(self.build).manifest
        del get_property_cache(self.build).digests
        upload_dir = os.path.join(
            self.incoming_folder, "test", str(self.build.id), "ubuntu")
        write_file(os.path.join(upload_dir, "layer_1.tar.gz"), b"layer_1")
        handler = UploadHandler.forProcessor(
            self.uploadprocessor, self.incoming_folder, "test", self.build)
        result = handler.processOCIRecipe(self.log)
        self.assertEqual(UploadStatusEnum.REJECTED, result)
        self.assertIn(
            "ERROR Build did not produce a digests.json.",
            self.log.getLogBuffer())
        self.assertFalse(self.build.verifySuccessfulUpload())

    def test_missing_layer_file(self):
        # The digests.json specifies a layer file that is missing
        self.assertFalse(self.build.verifySuccessfulUpload())
        del get_property_cache(self.build).manifest
        del get_property_cache(self.build).digests
        upload_dir = os.path.join(
            self.incoming_folder, "test", str(self.build.id), "ubuntu")
        write_file(os.path.join(upload_dir, "layer_1.tar.gz"), b"layer_1")
        write_file(
            os.path.join(upload_dir, "digests.json"), json.dumps(self.digests))
        handler = UploadHandler.forProcessor(
            self.uploadprocessor, self.incoming_folder, "test", self.build)
        result = handler.processOCIRecipe(self.log)
        self.assertEqual(UploadStatusEnum.REJECTED, result)
        self.assertIn(
            "ERROR Missing layer file: layer_2.",
            self.log.getLogBuffer())
        self.assertFalse(self.build.verifySuccessfulUpload())

    def test_reuse_existing_file(self):
        # The digests.json specifies a file that already exists in the
        # librarian, but not on disk
        self.assertFalse(self.build.verifySuccessfulUpload())
        del get_property_cache(self.build).manifest
        del get_property_cache(self.build).digests
        upload_dir = os.path.join(
            self.incoming_folder, "test", str(self.build.id), "ubuntu")
        write_file(os.path.join(upload_dir, "layer_1.tar.gz"), b"layer_1")
        write_file(os.path.join(upload_dir, "manifest.json"), b"manifest")
        write_file(
            os.path.join(upload_dir, "digests.json"), json.dumps(self.digests))

        # create the existing file
        self.switchToAdmin()
        layer_2 = self.factory.makeOCIFile(layer_file_digest="digest_2")
        Store.of(layer_2.build).flush()
        self.switchToUploader()

        handler = UploadHandler.forProcessor(
            self.uploadprocessor, self.incoming_folder, "test", self.build)
        result = handler.processOCIRecipe(self.log)
        self.assertEqual(
            UploadStatusEnum.ACCEPTED, result,
            "OCI upload failed\nGot: %s" % self.log.getLogBuffer())
        self.assertEqual(BuildStatus.FULLYBUILT, self.build.status)
        self.assertTrue(self.build.verifySuccessfulUpload())
