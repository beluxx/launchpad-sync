# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for uploadprocessor.py."""

__metaclass__ = type

import os
import shutil
import unittest

from email import message_from_string

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.archiveuploader.uploadprocessor import UploadProcessor
from canonical.archiveuploader.tests.test_uploadprocessor import (
    TestUploadProcessorBase)
from canonical.config import config
from canonical.launchpad.database import Component
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory)
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.soyuz.interfaces.archive import ArchivePurpose, IArchiveSet
from lp.soyuz.interfaces.package import PackageUploadStatus
from lp.soyuz.interfaces.publishing import (
    PackagePublishingStatus, PackagePublishingPocket)
from lp.soyuz.interfaces.queue import NonBuildableSourceUploadError
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, ILibraryFileAliasSet, NotFoundError)
from canonical.launchpad.testing.fakepackager import FakePackager
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.services.mail import stub


class TestPPAUploadProcessorBase(TestUploadProcessorBase):
    """Help class for functional tests for uploadprocessor.py and PPA."""

    def setUp(self):
        """Setup infrastructure for PPA tests.

        Additionally to the TestUploadProcessorBase.setUp, set 'breezy'
        distroseries and an new uploadprocessor instance.
        """
        TestUploadProcessorBase.setUp(self)
        self.ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        # Let's make 'name16' person member of 'launchpad-beta-tester'
        # team only in the context of this test.
        beta_testers = getUtility(
            ILaunchpadCelebrities).launchpad_beta_testers
        admin = getUtility(ILaunchpadCelebrities).admin
        self.name16 = getUtility(IPersonSet).getByName("name16")
        beta_testers.addMember(self.name16, admin)
        # Pop the two messages notifying the team modification.
        unused = stub.test_emails.pop()
        unused = stub.test_emails.pop()

        # create name16 PPA
        self.name16_ppa = getUtility(IArchiveSet).new(
            owner=self.name16, distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)
        # Extra setup for breezy and allowing PPA builds on breezy/i386.
        self.setupBreezy()
        self.breezy['i386'].supports_virtualized = True
        self.layer.txn.commit()

        # Set up the uploadprocessor with appropriate options and logger
        self.options.context = 'insecure'
        self.uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

    def assertEmail(self, contents=None, recipients=None,
                    ppa_header='name16'):
        """Check email last upload notification attributes.

        :param: contents: can be a list of one or more lines, if passed
            they will be checked against the lines in Subject + Body.
        :param: recipients: can be a list of recipients lines, it defaults
            to 'Foo Bar <foo.bar@canonical.com>' (name16 account) and
            should match the email To: header content.
        :param: ppa_header: is the content of the 'X-Launchpad-PPA' header,
            it defaults to 'name16' and should be explicitly set to None for
            non-PPA or rejection notifications.
        """
        if not recipients:
            recipients = [self.name16_recipient]

        if not contents:
            contents = []

        queue_size = len(stub.test_emails)
        messages = "\n".join(m for f, t, m in stub.test_emails)
        self.assertEqual(
            queue_size, 1,'Unexpected number of emails sent: %s\n%s'
            % (queue_size, messages))

        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        msg = message_from_string(raw_msg)

        # This is now a MIMEMultipart message.
        body = msg.get_payload(0)
        body = body.get_payload(decode=True)

        clean_recipients = [r.strip() for r in to_addrs]
        for recipient in list(recipients):
            self.assertTrue(
                recipient in clean_recipients,
                "%s not in %s" % (recipient, clean_recipients))
        self.assertEqual(
            len(recipients), len(clean_recipients),
            "Email recipients do not match exactly. Expected %s, got %s" %
                (recipients, clean_recipients))

        subject = "Subject: %s\n" % msg['Subject']
        body = subject + body

        for content in list(contents):
            self.assertTrue(
                content in body,
                "Expect: '%s'\nGot:\n%s" % (content, body))

        if ppa_header is not None:
            self.assertTrue(
                'X-Launchpad-PPA' in msg.keys(), "PPA header not present.")
            self.assertEqual(
                msg['X-Launchpad-PPA'], ppa_header,
                "Mismatching PPA header: %s" % msg['X-Launchpad-PPA'])

    def checkFilesRestrictedInLibrarian(self, queue_item, condition):
        """Check the libraryfilealias restricted flag.

        For the files associated with the queue_item, check that the
        libraryfilealiases' restricted flags are the same as 'condition'.
        """
        self.assertEqual(queue_item.changesfile.restricted, condition)

        for source in queue_item.sources:
            for source_file in source.sourcepackagerelease.files:
                self.assertEqual(
                    source_file.libraryfile.restricted, condition)

        for build in queue_item.builds:
            for binarypackage in build.build.binarypackages:
                for binary_file in binarypackage.files:
                    self.assertEqual(
                        binary_file.libraryfile.restricted, condition)

        for custom in queue_item.customfiles:
            custom_file = custom.libraryfilealias
            self.assertEqual(custom_file.restricted, condition)


class TestPPAUploadProcessor(TestPPAUploadProcessorBase):
    """Functional tests for uploadprocessor.py in PPA operation."""

    def testUploadToPPA(self):
        """Upload to a PPA gets there.

        Email announcement is sent and package is on queue DONE even if
        the source is NEW (PPA Auto-Approves everything), so PPA uploads
        will immediately result in a PENDING source publishing record (
        thus visible in the UI) and a NEEDSBUILD build record ready to be
        dispatched.

        Also test IDistribution.getPendingPublicationPPAs() and check if
        it returns the just-modified archive.
        """
        #
        # Step 1: Upload the source bar_1.0-1, start a new source series
        # Ensure the 'new' source is auto-accepted, auto-published in
        # 'main' component and the PPA in question is 'pending-publication'.
        #
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.DONE, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

        [queue_item] = queue_items
        self.assertEqual(queue_item.archive, self.name16.archive)
        self.assertEqual(
            queue_item.pocket, PackagePublishingPocket.RELEASE)

        # The changes file and the source's files must all be in the non-
        # restricted librarian as this is not a private PPA.
        self.checkFilesRestrictedInLibrarian(queue_item, False)

        pending_ppas = self.breezy.distribution.getPendingPublicationPPAs()
        self.assertEqual(pending_ppas.count(), 1)
        self.assertEqual(pending_ppas[0], self.name16.archive)

        pub_sources = self.name16.archive.getPublishedSources(name='bar')
        [pub_bar] = pub_sources

        self.assertEqual(pub_bar.sourcepackagerelease.version, u'1.0-1')
        self.assertEqual(pub_bar.status, PackagePublishingStatus.PENDING)
        self.assertEqual(pub_bar.component.name, 'main')

        builds = self.name16.archive.getBuildRecords(name='bar')
        [build] = builds
        self.assertEqual(
            build.title, 'i386 build of bar 1.0-1 in ubuntu breezy RELEASE')
        self.assertEqual(build.buildstate.name, 'NEEDSBUILD')
        self.assertTrue(build.buildqueue_record.lastscore is not 0)

        #
        # Step 2: Upload a new version of bar to component universe (see
        # changesfile encoded in the upload notification). It should be
        # auto-accepted, auto-published and have its component overridden
        # to 'main' in the publishing record.
        #
        upload_dir = self.queueUpload("bar_1.0-10", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        pub_sources = self.name16.archive.getPublishedSources(name='bar')
        [pub_bar_10, pub_bar] = pub_sources

        self.assertEqual(pub_bar_10.sourcepackagerelease.version, u'1.0-10')
        self.assertEqual(pub_bar_10.status, PackagePublishingStatus.PENDING)
        self.assertEqual(pub_bar_10.component.name, 'main')

        builds = self.name16.archive.getBuildRecords(name='bar')
        [build, build_old] = builds
        self.assertEqual(
            build.title, 'i386 build of bar 1.0-10 in ubuntu breezy RELEASE')
        self.assertEqual(build.buildstate.name, 'NEEDSBUILD')
        self.assertTrue(build.buildqueue_record.lastscore is not 0)

        #
        # Step 3: Check if a lower version upload gets rejected and the
        # notification points to the right ancestry.
        #
        upload_dir = self.queueUpload("bar_1.0-2", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            u'bar_1.0-2.dsc: Version older than that in the archive. '
            u'1.0-2 <= 1.0-10')

    def testNamedPPAUploadDefault(self):
        """Test PPA uploads to the default PPA."""
        # Upload to the default PPA, using the named-ppa path syntax.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ppa/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        queue_root = self.uploadprocessor.last_processed_upload.queue_root
        self.assertEqual(queue_root.archive, self.name16.archive)
        self.assertEqual(queue_root.status, PackageUploadStatus.DONE)
        self.assertEqual(queue_root.distroseries.name, "breezy")

        # Subject and PPA emails header contain the owner name since
        # it's the default PPA.
        contents = [
            "Subject: [PPA name16] [ubuntu/breezy] bar 1.0-1 (Accepted)",
            ]
        self.assertEmail(contents, ppa_header='name16')

    def testNamedPPAUploadNonDefault(self):
        """Test PPA uploads to a named PPA."""
        # Create a PPA named 'testing' for 'name16' user.
        other_ppa = getUtility(IArchiveSet).new(
            owner=self.name16, name='testing', distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)

        # Upload to a named PPA.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/testing/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        queue_root = self.uploadprocessor.last_processed_upload.queue_root
        self.assertEqual(queue_root.archive, other_ppa)
        self.assertEqual(queue_root.status, PackageUploadStatus.DONE)
        self.assertEqual(queue_root.distroseries.name, "breezy")

        # Subject and PPA email-header are specific for this named-ppa.
        contents = [
            "Subject: [PPA name16-testing] [ubuntu/breezy] bar 1.0-1 "
                "(Accepted)",
            ]
        self.assertEmail(contents, ppa_header='name16-testing')

    def testNamedPPAUploadWithSeries(self):
        """Test PPA uploads to a named PPA location and with a distroseries.

        As per testNamedPPAUpload above, but we override the distroseries.
        """
        # The 'bar' package already targets 'breezy' as can be seen from
        # the test above, so we'll set up a new distroseries called
        # farty and override to use that.
        self.setupBreezy(name="farty")
        # Allow PPA builds.
        self.breezy['i386'].supports_virtualized = True
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ppa/ubuntu/farty")
        self.processUpload(self.uploadprocessor, upload_dir)

        queue_root = self.uploadprocessor.last_processed_upload.queue_root
        self.assertEqual(queue_root.status, PackageUploadStatus.DONE)
        self.assertEqual(queue_root.distroseries.name, "farty")

    def testNamedPPAUploadWithNonexistentName(self):
        """Test PPA uploads to a named PPA location that doesn't exist."""
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/BADNAME/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        # There's no way of knowing that the BADNAME part is a ppa_name
        # during the parallel run period, so it can only assume it's a
        # bad distribution name.
        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            "Could not find PPA named 'BADNAME' for 'name16'\n"
            "Further error processing not possible because of a "
            "critical previous error.")

    def testPPAPublisherOverrides(self):
        """Check that PPA components override to main at publishing time,

        To preserve the original upload data, PPA uploads are not overridden
        until they are published.  This means that the SourcePackageRelease
        and BinaryPackageRelease keep the uploaded data, but the publishing
        tables have the overridden data.
        """
        # bar_1.0-1_universe is targeted to universe.
        upload_dir = self.queueUpload("bar_1.0-1_universe", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)
        # Consume the test email so the assertion futher down does not fail.
        _from_addr, _to_addrs, _raw_msg = stub.test_emails.pop()

        # The SourcePackageRelease still has a component of universe:
        pub_sources = self.name16.archive.getPublishedSources(name="bar")
        [pub_foo] = pub_sources
        self.assertEqual(
            pub_foo.sourcepackagerelease.component.name, "universe")

        # But the publishing record has main:
        self.assertEqual(pub_foo.component.name, 'main')

        # Continue with a binary upload:
        builds = self.name16.archive.getBuildRecords(name="bar")
        [build] = builds
        self.options.context = 'buildd'
        self.options.buildid = build.id
        upload_dir = self.queueUpload(
            "bar_1.0-1_binary_universe", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        # No mails are sent for successful binary uploads.
        self.assertEqual(len(stub.test_emails), 0,
                         "Unexpected email generated on binary upload.")

        # Publish the binary.
        [queue_item] = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        queue_item.realiseUpload()

        for binary_package in build.binarypackages:
            self.assertEqual(binary_package.component.name, "universe")
            [binary_pub] = BinaryPackagePublishingHistory.selectBy(
                binarypackagerelease=binary_package,
                archive=self.name16.archive)
            self.assertEqual(binary_pub.component.name, "main")

    def testPPABinaryUploads(self):
        """Check the usual binary upload life-cycle for PPAs."""
        # Source upload.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        # Source publication and build record for breezy-i386
        # distroarchseries were created as expected. The source is ready
        # to receive the binary upload.
        pub_sources = self.name16.archive.getPublishedSources(name='bar')
        [pub_bar] = pub_sources
        self.assertEqual(pub_bar.sourcepackagerelease.version, u'1.0-1')
        self.assertEqual(pub_bar.status, PackagePublishingStatus.PENDING)
        self.assertEqual(pub_bar.component.name, 'main')

        builds = self.name16.archive.getBuildRecords(name='bar')
        [build] = builds
        self.assertEqual(
            build.title, 'i386 build of bar 1.0-1 in ubuntu breezy RELEASE')
        self.assertEqual(build.buildstate.name, 'NEEDSBUILD')
        self.assertTrue(build.buildqueue_record.lastscore is not 0)

        # Binary upload to the just-created build record.
        self.options.context = 'buildd'
        self.options.buildid = build.id
        upload_dir = self.queueUpload("bar_1.0-1_binary", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        # The binary upload was accepted and it's waiting in the queue.
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

        # All the files associated with this binary upload must be in the
        # non-restricted librarian as the PPA is not private.
        [queue_item] = queue_items
        self.checkFilesRestrictedInLibrarian(queue_item, False)

    def testNamedPPABinaryUploads(self):
        """Check the usual binary upload life-cycle for named PPAs."""
        # Source upload.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ppa/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        queue_root = self.uploadprocessor.last_processed_upload.queue_root
        self.assertEqual(queue_root.archive, self.name16.archive)
        self.assertEqual(queue_root.status, PackageUploadStatus.DONE)
        self.assertEqual(queue_root.distroseries.name, "breezy")

    def testPPACopiedSources(self):
        """Check PPA binary uploads for copied sources."""
        # Source upload to name16 PPA.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        # Copy source uploaded to name16 PPA to cprov's PPA.
        pub_sources = self.name16.archive.getPublishedSources(name='bar')
        [name16_pub_bar] = pub_sources
        cprov = getUtility(IPersonSet).getByName("cprov")
        cprov_pub_bar = name16_pub_bar.copyTo(
            self.breezy, PackagePublishingPocket.RELEASE, cprov.archive)
        self.assertEqual(
            cprov_pub_bar.sourcepackagerelease.upload_archive.displayname,
            'PPA for Foo Bar')

        # Create a build record for source bar for breezy-i386
        # distroarchseries in cprov PPA.
        build_bar_i386 = cprov_pub_bar.sourcepackagerelease.createBuild(
            self.breezy['i386'], PackagePublishingPocket.RELEASE,
            cprov.archive)

        # Binary upload to the just-created build record.
        self.options.context = 'buildd'
        self.options.buildid = build_bar_i386.id
        upload_dir = self.queueUpload("bar_1.0-1_binary", "~cprov/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        # The binary upload was accepted and it's waiting in the queue.
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=cprov.archive)
        self.assertEqual(queue_items.count(), 1)

    def testUploadDoesNotEmailMaintainerOrChangedBy(self):
        """PPA uploads must not email the maintainer or changed-by person.

        The package metadata must not influence the email addresses,
        it's the uploader only who gets emailed.
        """
        upload_dir = self.queueUpload(
            "bar_1.0-1_valid_maintainer", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        # name16 is Foo Bar, who signed the upload.  The package that was
        # uploaded also contains two other valid (in sampledata) email
        # addresses for maintainer and changed-by which must be ignored.
        self.assertEmail()

    def testUploadToUnknownPPA(self):
        """Upload to a unknown PPA.

        Upload gets processed as if it was targeted to the ubuntu PRIMARY
        archive, however it is rejected, since it could not find the
        specified PPA.

        A rejection notification is sent to the uploader without the PPA
        notification header, because it can't be calculated.
        """
        upload_dir = self.queueUpload("bar_1.0-1", "~spiv/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            "Could not find PPA named 'ppa' for 'spiv'\n"
            "Further error processing not "
            "possible because of a critical previous error.")

    def testUploadToDisabledPPA(self):
        """Upload to a disabled PPA.

        Upload gets processed as if it was targeted to the ubuntu PRIMARY
        archive, however it is rejected since the PPA is disabled.
        A rejection notification is sent to the uploader.
        """
        spiv = getUtility(IPersonSet).getByName("spiv")
        spiv_archive = getUtility(IArchiveSet).new(
            owner=spiv, distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)
        spiv_archive.enabled = False
        self.layer.commit()

        upload_dir = self.queueUpload("bar_1.0-1", "~spiv/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            'PPA for Andrew Bennetts is disabled\n'
            'Further error processing '
            'not possible because of a critical previous error.')
        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "PPA for Andrew Bennetts is disabled",
            "If you don't understand why your files were rejected please "
                 "send an email",
            ("to %s for help (requires membership)."
             % config.launchpad.users_address),
            ]
        self.assertEmail(contents, ppa_header=None)

    def testPPADistroSeriesOverrides(self):
        """It's possible to override target distroserieses of PPA uploads.

        Similar to usual PPA uploads:

         * Email notification is sent
         * The upload is auto-accepted in the overridden target distroseries.
         * The modified PPA is found by getPendingPublicationPPA() lookup.
        """
        hoary = self.ubuntu['hoary']
        fake_chroot = self.addMockFile('fake_chroot.tar.gz')
        hoary['i386'].addOrUpdateChroot(fake_chroot)

        upload_dir = self.queueUpload(
            "bar_1.0-1", "~name16/ubuntu/hoary")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        queue_items = hoary.getQueueItems(
            status=PackageUploadStatus.DONE, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

        [queue_item] = queue_items
        self.assertEqual(queue_item.archive, self.name16.archive)
        self.assertEqual(
            queue_item.pocket, PackagePublishingPocket.RELEASE)

        pending_ppas = self.ubuntu.getPendingPublicationPPAs()
        self.assertEqual(pending_ppas.count(), 1)
        self.assertEqual(pending_ppas[0], self.name16.archive)

    def testUploadToTeamPPA(self):
        """Upload to a team PPA also gets there.

        See testUploadToPPA.
        """
        ubuntu_team = getUtility(IPersonSet).getByName("ubuntu-team")
        getUtility(IArchiveSet).new(
            owner=ubuntu_team, distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)
        self.layer.commit()

        upload_dir = self.queueUpload("bar_1.0-1", "~ubuntu-team/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.DONE, name="bar",
            version="1.0-1", exact_match=True, archive=ubuntu_team.archive)
        self.assertEqual(queue_items.count(), 1)

        pending_ppas = self.ubuntu.getPendingPublicationPPAs()
        self.assertEqual(pending_ppas.count(), 1)
        self.assertEqual(pending_ppas[0], ubuntu_team.archive)

        builds = ubuntu_team.archive.getBuildRecords(name='bar')
        [build] = builds
        self.assertEqual(
            build.title, 'i386 build of bar 1.0-1 in ubuntu breezy RELEASE')
        self.assertEqual(build.buildstate.name, 'NEEDSBUILD')
        self.assertTrue(build.buildqueue_record.lastscore is not 0)

    def testNotMemberUploadToTeamPPA(self):
        """Upload to a team PPA is rejected when the uploader is not member.

        Also test IArchiveSet.getPendingPublicationPPAs(), no archives should
        be returned since nothing was accepted.
        """
        ubuntu_translators = getUtility(IPersonSet).getByName(
            "ubuntu-translators")
        getUtility(IArchiveSet).new(
            owner=ubuntu_translators, distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)
        self.layer.commit()

        upload_dir = self.queueUpload(
            "bar_1.0-1", "~ubuntu-translators/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        pending_ppas = self.ubuntu.getPendingPublicationPPAs()
        self.assertEqual(pending_ppas.count(), 0)

    def testUploadToSomeoneElsePPA(self):
        """Upload to a someone else's PPA gets rejected."""
        kinnison = getUtility(IPersonSet).getByName("kinnison")
        getUtility(IArchiveSet).new(
            owner=kinnison, distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)
        self.layer.commit()

        upload_dir = self.queueUpload("bar_1.0-1", "~kinnison/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            "Signer has no upload rights to this PPA.")

    def testPPAPartnerUploadFails(self):
        """Upload a partner package to a PPA and ensure it's rejected."""
        upload_dir = self.queueUpload("foocomm_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            "PPA does not support partner uploads.")

    def testUploadSignedByNonUbuntero(self):
        """Check if a non-ubuntero can upload to his PPA."""
        self.name16.activesignatures[0].active = False
        self.layer.commit()

        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            "PPA uploads must be signed by an 'ubuntero'.")
        self.assertTrue(self.name16.archive is not None)

    def testUploadSignedByBetaTesterMember(self):
        """Check if a non-member of launchpad-beta-testers can upload to PPA.

        PPA was opened for public access in 1.1.11 (22th Nov 2007), so we will
        keep this test as a simple reference to the check disabled in code
        (uploadpolicy.py).
        """
        beta_testers = getUtility(
            ILaunchpadCelebrities).launchpad_beta_testers
        self.name16.leave(beta_testers)
        # Pop the message notifying the membership modification.
        unused = stub.test_emails.pop()

        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

    def testUploadToAMismatchingDistribution(self):
        """Check if we only accept uploads to the Archive.distribution."""
        upload_dir = self.queueUpload("bar_1.0-1", "~cprov/ubuntutest")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            "Could not find PPA named 'ubuntutest' for 'cprov'\n"
            "Further error processing not possible because of a "
            "critical previous error.")

    def testUploadToUnknownDistribution(self):
        """Upload to unknown distribution gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "biscuit")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            "Could not find distribution 'biscuit'\n"
            "Further error "
            "processing not possible because of a critical previous error.")

    def testUploadWithMismatchingPPANotation(self):
        """Upload with mismatching PPA notation results in rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "biscuit/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            "Could not find distribution 'biscuit'\n"
            "Further error "
            "processing not possible because of a critical previous error.")

    def testUploadToUnknownPerson(self):
        """Upload to unknown person gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "~orange/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
             "Could not find person 'orange'\n"
             "Further error processing not "
             "possible because of a critical previous error.")

    def testUploadWithMismatchingPath(self):
        """Upload with mismating path gets proper rejection email."""
        upload_dir = self.queueUpload(
            "bar_1.0-1", "ubuntu/one/two/three/four")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            "Path mismatch 'ubuntu/one/two/three/four'. Use "
            "~<person>/<ppa_name>/<distro>[/distroseries]/[files] for PPAs "
            "and <distro>/[files] for normal uploads.\n"
            "Further error processing "
            "not possible because of a critical previous error.")

    def testUploadWithBadDistroseries(self):
        """Test uploading with a bad distroseries in the changes file.

        Uploading with a broken distroseries should not generate a message
        with a code exception in the email rejection.  It should warn about
        the bad distroseries only.
        """
        upload_dir = self.queueUpload(
            "bar_1.0-1_bad_distroseries", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            'Unable to find distroseries: flangetrousers\n'
            'Further error '
            'processing not possible because of a critical previous error.')

    def testMixedUpload(self):
        """Mixed PPA uploads are rejected with a appropriate message."""
        upload_dir = self.queueUpload(
            "bar_1.0-1-mixed", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            'Upload rejected because it contains binary packages. Ensure '
            'you are using `debuild -S`, or an equivalent command, to '
            'generate only the source package before re-uploading. See '
            'https://help.launchpad.net/Packaging/PPA for more information.')

    def testPGPSignatureNotPreserved(self):
        """PGP signatures should be removed from PPA changesfiles.

        Email notifications and the librarian file for the changesfile should
        both have the PGP signature removed.
        """
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        # Check the email.
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        msg = message_from_string(raw_msg)

        # This is now a MIMEMultipart message.
        body = msg.get_payload(0)
        body = body.get_payload(decode=True)

        self.assertTrue(
            "-----BEGIN PGP SIGNED MESSAGE-----" not in body,
            "Unexpected PGP header found")
        self.assertTrue(
            "-----BEGIN PGP SIGNATURE-----" not in body,
            "Unexpected start of PGP signature found")
        self.assertTrue(
            "-----END PGP SIGNATURE-----" not in body,
            "Unexpected end of PGP signature found")

    def doCustomUploadToPPA(self):
        """Helper method to do a custom upload to a PPA.

        :return: The queue items that were uploaded.
        """
        test_files_dir = os.path.join(config.root,
            "lib/canonical/archiveuploader/tests/data/")
        upload_dir = self.queueUpload(
            "debian-installer", "~name16/ubuntu/breezy",
            test_files_dir=test_files_dir)
        self.processUpload(self.uploadprocessor, upload_dir)

        queue_items = self.breezy.getQueueItems(
            name="debian-installer",
            status=PackagePublishingStatus.PUBLISHED,
            archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

        [queue_item] = queue_items
        return queue_item

    def testCustomUploadToPPA(self):
        """Test a custom upload to a PPA.

        For now, we just test that the right librarian is used as all
        of the existing custom upload tests use doc/distroseriesqueue-*.
        """
        queue_item = self.doCustomUploadToPPA()
        self.checkFilesRestrictedInLibrarian(queue_item, False)

    def testCustomUploadToPrivatePPA(self):
        """Test a custom upload to a private PPA.

        Make sure that the files are placed in the restricted librarian.
        """
        self.name16.archive.buildd_secret = "secret"
        self.name16.archive.private = True
        queue_item = self.doCustomUploadToPPA()
        self.checkFilesRestrictedInLibrarian(queue_item, True)

    def testUploadToPrivatePPA(self):
        """Test a source and binary upload to a private PPA.

        Make sure that the files are placed in the restricted librarian.
        """
        self.name16.archive.buildd_secret = "secret"
        self.name16.archive.private = True

        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.DONE, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

        [queue_item] = queue_items
        self.checkFilesRestrictedInLibrarian(queue_item, True)

        # Now that we have source uploaded, we can upload a build.
        builds = self.name16.archive.getBuildRecords(name='bar')
        [build] = builds
        self.options.context = 'buildd'
        self.options.buildid = build.id
        upload_dir = self.queueUpload("bar_1.0-1_binary", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        # The binary upload was accepted and it's waiting in the queue.
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

        # All the files associated with this binary upload must be in the
        # restricted librarian as the PPA is private.
        [queue_item] = queue_items
        self.checkFilesRestrictedInLibrarian(queue_item, True)

    def testPPAInvalidComponentUpload(self):
        """Upload source and binary packages with invalid components.

        Components invalid in the distroseries should be ignored since
        PPAs are always published in "main".
        """
        # The component contrib does not exist in the sample data, so
        # add it here.
        Component(name='contrib')

        # Upload a source package first.
        upload_dir = self.queueUpload(
            "bar_1.0-1_contrib_component", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.DONE, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)

        # The upload was accepted despite the fact that it does
        # not have a valid component:
        self.assertEqual(queue_items.count(), 1)
        [queue_item] = queue_items
        self.assertTrue(
            queue_item.sourcepackagerelease.component not in
            self.breezy.upload_components)

        # Binary uploads should exhibit the same behaviour:
        [build] = self.name16.archive.getBuildRecords(name="bar")
        self.options.context = 'buildd'
        self.options.buildid = build.id
        upload_dir = self.queueUpload(
            "bar_1.0-1_contrib_binary", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)

        # The binary is accepted despite the fact that it does not have
        # a valid component:
        self.assertEqual(queue_items.count(), 1)
        [queue_item] = queue_items
        [build] = queue_item.builds
        for binary in build.build.binarypackages:
            self.assertTrue(
                binary.component not in self.breezy.upload_components)

    def testPPAUploadResultingInNoBuilds(self):
        """Source uploads resulting in no builds are rejected.

        If a PPA source upload results in no builds, it will be rejected.

        It usually happens for sources targeted to architectures not
        supported in the PPA subsystem.

        This way we don't create false expectations accepting sources that
        won't be ever built.
        """
        # First upload gets in because breezy/i386 is supported in PPA.
        packager = FakePackager(
            'biscuit', '1.0', 'foo.bar@canonical.com-passwordless.sec')
        packager.buildUpstream(suite=self.breezy.name, arch="i386")
        packager.buildSource()
        biscuit_pub = packager.uploadSourceVersion(
            '1.0-1', archive=self.name16.archive)
        self.assertEqual(biscuit_pub.status, PackagePublishingStatus.PENDING)

        # Remove breezy/i386 PPA support.
        self.breezy['i386'].supports_virtualized = False
        self.layer.commit()

        # Next version can't be accepted because it can't be built.
        packager.buildVersion('1.0-2', suite=self.breezy.name, arch="i386")
        packager.buildSource()
        upload = packager.uploadSourceVersion(
            '1.0-2', archive=self.name16.archive, auto_accept=False)

        error = self.assertRaisesAndReturnError(
            NonBuildableSourceUploadError,
            upload.storeObjectsInDatabase)
        self.assertEqual(
            str(error),
            "Cannot build any of the architectures requested: i386")


class TestPPAUploadProcessorFileLookups(TestPPAUploadProcessorBase):
    """Functional test for uploadprocessor.py file-lookups in PPA."""
    # XXX cprov 20071204: the DSCFile tests are not yet implemented, this
    # issue should be addressed by bug #106084, while implementing those
    # tests we should revisit this test-suite checking if we have a
    # satisfactory coverage.

    def uploadNewBarToUbuntu(self):
        """Upload a 'bar' source containing a unseen orig.tar.gz in ubuntu.

        Accept and publish the NEW source, so it becomes available to
        the rest of the system.
        """
        upload_dir = self.queueUpload("bar_1.0-1")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.NEW)

        [queue_item] = self.breezy.getQueueItems(
            status=PackageUploadStatus.NEW, name="bar",
            version="1.0-1", exact_match=True)
        queue_item.setAccepted()
        queue_item.realiseUpload()
        self.layer.commit()

    def uploadHigherBarToUbuntu(self):
        """Upload the same higher version of 'bar' to the ubuntu.

        We expect the official orig.tar.gz to be already available in the
        system.
        """
        try:
            self.ubuntu.getFileByName(
                'bar_1.0.orig.tar.gz', source=True, binary=False)
        except NotFoundError:
            self.fail('bar_1.0.orig.tar.gz is not yet published.')

        upload_dir = self.queueUpload("bar_1.0-10")
        self.processUpload(self.uploadprocessor, upload_dir)
        # Discard the announcement email and check the acceptance message
        # content.
        announcement = stub.test_emails.pop()

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

    def testPPAReusingOrigFromUbuntu(self):
        """Official 'orig.tar.gz' can be reused for PPA uploads."""
        # Make the official bar orig.tar.gz available in the system.
        self.uploadNewBarToUbuntu()

        # Upload a higher version of 'bar' to a PPA that relies on the
        # availability of orig.tar.gz published in ubuntu.
        upload_dir = self.queueUpload("bar_1.0-10", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        # Cleanup queue directory in order to re-upload the same source.
        shutil.rmtree(
            os.path.join(self.queue_folder, 'incoming', 'bar_1.0-10'))

        # Upload a higher version of bar that relies on the official
        # orig.tar.gz availability.
        self.uploadHigherBarToUbuntu()

    def testNoPublishingOverrides(self):
        """Make sure publishing overrides are not applied for PPA uploads."""
        # Create a fake "bar" package and publish it in section "web".
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        pub_src = publisher.getPubSource(
            sourcename="bar", version="1.0-1", section="web",
            archive=self.name16_ppa, distroseries=self.breezy,
            status=PackagePublishingStatus.PUBLISHED)

        # Now upload bar 1.0-3, which has section "devel".
        # (I am using this version because it's got a .orig required for
        # the upload).
        upload_dir = self.queueUpload("bar_1.0-3_valid", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        # The published section should be "devel" and not "web".
        pub_sources = self.name16.archive.getPublishedSources(name='bar')
        [pub_bar2, pub_bar1] = pub_sources

        section = pub_bar2.section.name
        self.assertEqual(
            section, 'devel',
            "Expected a section of 'devel', actually got '%s'" % section)

    def testPPAOrigGetsPrecedence(self):
        """When available, the PPA overridden 'orig.tar.gz' gets precedence.

        This test is required to guarantee the system will continue to cope
        with possibly different 'orig.tar.gz' contents already uploaded to
        PPAs.
        """
        # Upload a initial version of 'bar' source introducing a 'orig.tar.gz'
        # different than the official one. It emulates the origs already
        # uploaded to PPAs before bug #139619 got fixed.
        # It's only possible to do such thing in the current codeline when
        # the *tainted* upload reaches the system before the 'official' orig
        # is published in the primary archive, if uploaded after the official
        # orig is published in primary archive it would fail due to different
        # file contents.
        upload_dir = self.queueUpload("bar_1.0-1-ppa-orig", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        # Make the official bar orig.tar.gz available in the system.
        self.uploadNewBarToUbuntu()

        # Upload a higher version of 'bar' to a PPA that relies on the
        # availability of orig.tar.gz published in the PPA itself.
        upload_dir = self.queueUpload("bar_1.0-10-ppa-orig", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        # Upload a higher version of bar that relies on the official
        # orig.tar.gz availability.
        self.uploadHigherBarToUbuntu()

    def testPPAConflictingOrigFiles(self):
        """When available, the official 'orig.tar.gz' restricts PPA uploads.

        This test guarantee that when not previously overridden in the
        context PPA, users will be forced to use the offical 'orig.tar.gz'
        from primary archive.
        """
        # Make the official bar orig.tar.gz available in the system.
        self.uploadNewBarToUbuntu()

        # Upload of version of 'bar' to a PPA that relies on the
        # availability of orig.tar.gz published in the PPA itself.

        # The same 'bar' version will fail due to the conflicting
        # 'orig.tar.gz' contents.
        upload_dir = self.queueUpload("bar_1.0-1-ppa-orig", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            'File bar_1.0.orig.tar.gz already exists in Primary Archive '
            'for Ubuntu Linux, but uploaded version has different '
            'contents. See more information about this error in '
            'https://help.launchpad.net/Packaging/UploadErrors.\nFiles '
            'specified in DSC are broken or missing, skipping package '
            'unpack verification.')

        self.log.lines = []
        # The same happens with higher versions of 'bar' depending on the
        # unofficial 'orig.tar.gz'.
        upload_dir = self.queueUpload("bar_1.0-10-ppa-orig", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.rejection_message,
            'File bar_1.0.orig.tar.gz already exists in Primary Archive for '
            'Ubuntu Linux, but uploaded version has different contents. See '
            'more information about this error in '
            'https://help.launchpad.net/Packaging/UploadErrors.\nFiles '
            'specified in DSC are broken or missing, skipping package unpack '
            'verification.')

        # Cleanup queue directory in order to re-upload the same source.
        shutil.rmtree(
            os.path.join(self.queue_folder, 'incoming', 'bar_1.0-1'))

        # Only versions of 'bar' matching the official 'orig.tar.gz' will
        # be accepted.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        upload_dir = self.queueUpload("bar_1.0-10", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)


class TestPPAUploadProcessorQuotaChecks(TestPPAUploadProcessorBase):
    """Functional test for uploadprocessor.py quota checks in PPA."""

    def _fillArchive(self, archive, size):
        """Create content in the given archive which the given size.

        Create a source package publication in the given archive totalizing
        the given size in bytes.

        Uses `SoyuzTestPublisher` class to create the corresponding publishing
        record, then switchDbUser as 'librariangc' and update the size of the
        source file to the given value.
        """
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        pub_src = publisher.getPubSource(
            archive=archive, distroseries=self.breezy,
            status=PackagePublishingStatus.PUBLISHED)
        alias_id = pub_src.sourcepackagerelease.files[0].libraryfile.id

        self.layer.commit()
        self.layer.switchDbUser('librariangc')
        content = getUtility(ILibraryFileAliasSet)[alias_id].content
        content = removeSecurityProxy(content)
        # Decrement the archive index parcel automatically added by
        # IArchive.estimated_size.
        content.filesize = size - 1024
        self.layer.commit()
        self.layer.switchDbUser('uploader')

        # Re-initialize uploadprocessor since it depends on the new
        # transaction reset by switchDbUser.
        self.uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

    def testPPASizeQuotaSourceRejection(self):
        """Verify the size quota check for PPA uploads.

        New source uploads are submitted to the size quota check, where
        the size of the upload plus the current PPA size must be smaller
        than the PPA.authorized_size, otherwise the upload will be rejected.
        """
        # Stuff 1024 MiB in name16 PPA, so anything will be above the
        # default quota limit, 1024 MiB.
        self._fillArchive(self.name16.archive, 1024 * (2 ** 20))

        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        upload_results = self.processUpload(self.uploadprocessor, upload_dir)

        # Upload got rejected.
        self.assertEqual(upload_results, ['rejected'])

        # An email communicating the rejection and the reason why it was
        # rejected is sent to the uploaders.
        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "Rejected:",
            "PPA exceeded its size limit (1024.00 of 1024.00 MiB). "
            "Ask a question in https://answers.launchpad.net/soyuz/ "
            "if you need more space."]
        self.assertEmail(contents)

    def testPPASizeQuotaSourceWarning(self):
        """Verify the size quota warning for PPA near size limit.

        The system start warning users for uploads exceeding 95 % of
        the current size limit.
        """
        # Stuff 973 MiB into name16 PPA, approximately 95 % of
        # the default quota limit, 1024 MiB.
        self._fillArchive(self.name16.archive, 973 * (2 ** 20))

        # Ensure the warning is sent in the acceptance notification.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: [PPA name16] [ubuntu/breezy] bar 1.0-1 (Accepted)",
            "Upload Warnings:",
            "PPA exceeded 95 % of its size limit (973.00 of 1024.00 MiB). "
            "Ask a question in https://answers.launchpad.net/soyuz/ "
            "if you need more space."]
        self.assertEmail(contents)

        # User was warned about quota limits but the source was accepted
        # as informed in the upload notification.
        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

    def testPPADoNotCheckSizeQuotaForBinary(self):
        """Verify the size quota check for internal binary PPA uploads.

        Binary uploads are not submitted to the size quota check, since
        they are automatically generated, rejecting/warning them would
        just cause unnecessary hassle.
        """
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        self.assertEqual(
            self.uploadprocessor.last_processed_upload.queue_root.status,
            PackageUploadStatus.DONE)

        # Retrieve the build record for source bar in breezy-i386
        # distroarchseries, and setup a appropriate upload policy
        # in preparation to the corresponding binary upload.
        builds = self.name16.archive.getBuildRecords(name='bar')
        [build] = builds
        self.options.context = 'buildd'
        self.options.buildid = build.id

        # Stuff 1024 MiB in name16 PPA, so anything will be above the
        # default quota limit, 1024 MiB.
        self._fillArchive(self.name16.archive, 1024 * (2 ** 20))

        upload_dir = self.queueUpload("bar_1.0-1_binary", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        # The binary upload was accepted, and it's waiting in the queue.
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

    def testArchiveBinarySize(self):
        """Test an archive's binaries_size reports correctly.

        The binary size for an archive should only take into account one
        occurrence of arch-independent files published in multiple locations.
        """
        # We need to publish an architecture-independent package
        # for a couple of distroseries in a PPA.
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()

        # Publish To Breezy:
        pub_bin1 = publisher.getPubBinaries(
            archive=self.name16.archive, distroseries=self.breezy,
            status=PackagePublishingStatus.PUBLISHED)

        # Create chroot for warty/i386, allowing binaries to build and
        # thus be published in this architecture.
        warty = self.ubuntu['warty']
        fake_chroot = self.addMockFile('fake_chroot.tar.gz')
        warty['i386'].addOrUpdateChroot(fake_chroot)

        # Publish To Warty:
        pub_bin2 = publisher.getPubBinaries(
            archive=self.name16.archive, distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)

        # The result is 54 without the bug fix (see bug 180983).
        size = self.name16.archive.binaries_size
        self.assertEqual(size, 36,
            "binaries_size returns %d, expected 36" % size)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


