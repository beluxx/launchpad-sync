# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the merge_translations script."""


import transaction

from lp.services.scripts.tests import run_script
from lp.testing import TestCaseWithFactory, person_logged_in
from lp.testing.layers import ZopelessAppServerLayer
from lp.translations.tests.test_translationpackagingjob import (
    count_translations,
    make_translation_merge_job,
)
from lp.translations.utilities.translationmerger import TranslationMerger


class TestMergeExistingPackagings(TestCaseWithFactory):
    layer = ZopelessAppServerLayer

    def test_merge_translations(self):
        """Running the script performs a translation merge."""
        # Import here to avoid autodetection by test runner.
        for packaging in set(TranslationMerger.findMergeablePackagings()):
            with person_logged_in(packaging.owner):
                packaging.destroySelf()
        job = make_translation_merge_job(self.factory)
        self.assertEqual(2, count_translations(job))
        transaction.commit()
        retcode, stdout, stderr = run_script(
            "scripts/rosetta/merge-existing-packagings.py",
            [],
            expect_returncode=0,
        )
        merge_message = "INFO    Merging %s/%s and %s/%s.\n" % (
            job.productseries.product.name,
            job.productseries.name,
            job.sourcepackagename.name,
            job.distroseries.name,
        )
        self.assertEqual(
            merge_message
            + "INFO    Deleted POTMsgSets: 1.  TranslationMessages: 1.\n"
            "INFO    Merging template 1/2.\n"
            "INFO    Merging template 2/2.\n",
            stderr,
        )
        self.assertEqual("", stdout)
        self.assertEqual(1, count_translations(job))
