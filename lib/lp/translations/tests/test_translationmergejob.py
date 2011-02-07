# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for merging translations."""

__metaclass__ = type


from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    )
from lp.services.job.interfaces.job import IRunnableJob
from lp.services.job.model.job import Job
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.side import TranslationSide
from lp.translations.model.potemplate import POTemplateSubset
from lp.translations.model.translationmergejob import TranslationMergeJob


class TestTranslationMergeJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def makeTranslationMergeJob(self):
        singular = self.factory.getUniqueString()
        upstream_pofile = self.factory.makePOFile(
            side=TranslationSide.UPSTREAM)
        upstream_potmsgset = self.factory.makePOTMsgSet(
            upstream_pofile.potemplate, singular, sequence=1)
        upstream = self.factory.makeCurrentTranslationMessage(
            pofile=upstream_pofile, potmsgset=upstream_potmsgset)
        ubuntu_potemplate = self.factory.makePOTemplate(
            side=TranslationSide.UBUNTU, name=upstream_pofile.potemplate.name)
        ubuntu_pofile = self.factory.makePOFile(
            potemplate=ubuntu_potemplate)
        ubuntu_potmsgset = self.factory.makePOTMsgSet(
            ubuntu_pofile.potemplate, singular, sequence=1)
        ubuntu = self.factory.makeCurrentTranslationMessage(
            pofile=ubuntu_pofile, potmsgset=ubuntu_potmsgset,
            translations=upstream.translations)
        productseries = upstream_pofile.potemplate.productseries
        distroseries = ubuntu_pofile.potemplate.distroseries
        sourcepackagename = ubuntu_pofile.potemplate.sourcepackagename
        return TranslationMergeJob(
            Job(), productseries, distroseries, sourcepackagename)

    def test_interface(self):
        """TranslationMergeJob must implement IRunnableJob."""
        job = self.makeTranslationMergeJob()
        verifyObject(IRunnableJob, job)

    def test_run(self):
        job = self.makeTranslationMergeJob()
        self.becomeDbUser('rosettaadmin')
        job.run()
        msg_sets = []
        for template in POTemplateSubset(productseries=job.productseries):
            msg_sets.extend(template.getPOTMsgSets())
        (package_template,) = list(POTemplateSubset(
            sourcepackagename=job.sourcepackagename,
            distroseries=job.distroseries))
        (package_msg_set,) = list(package_template.getPOTMsgSets())
        self.assertEqual([package_msg_set], msg_sets)
