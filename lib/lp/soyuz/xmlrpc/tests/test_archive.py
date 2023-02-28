# Copyright 2017-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the internal Soyuz archive API."""

from datetime import timedelta

from fixtures import FakeLogger
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import BuildStatus
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import get_transaction_timestamp
from lp.services.features.testing import FeatureFixture
from lp.services.macaroons.interfaces import IMacaroonIssuer
from lp.soyuz.enums import ArchiveRepositoryFormat, PackagePublishingStatus
from lp.soyuz.interfaces.archive import NAMED_AUTH_TOKEN_FEATURE_FLAG
from lp.soyuz.xmlrpc.archive import ArchiveAPI
from lp.testing import TestCaseWithFactory, person_logged_in
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.xmlrpc import faults


class TestArchiveAPI(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super().setUp()
        self.useFixture(FeatureFixture({NAMED_AUTH_TOKEN_FEATURE_FLAG: "on"}))
        self.archive_api = ArchiveAPI(None, None)
        self.pushConfig(
            "launchpad", internal_macaroon_secret_key="some-secret"
        )
        self.logger = self.useFixture(FakeLogger())

    def assertLogs(self, message):
        self.assertEqual([message], self.logger.output.splitlines())

    def assertNotFound(self, func_name, message, log_message, *args, **kwargs):
        """Assert that a call returns NotFound."""
        fault = getattr(self.archive_api, func_name)(*args, **kwargs)
        self.assertEqual(faults.NotFound(message), fault)
        self.assertLogs(log_message)

    def assertUnauthorized(self, func_name, log_message, *args, **kwargs):
        """Assert that a call returns Unauthorized."""
        fault = getattr(self.archive_api, func_name)(*args, **kwargs)
        self.assertEqual(faults.Unauthorized("Authorisation required."), fault)
        self.assertLogs(log_message)

    def test_checkArchiveAuthToken_unknown_archive(self):
        self.assertNotFound(
            "checkArchiveAuthToken",
            "No archive found for '~nonexistent/unknown/bad'.",
            "user@~nonexistent/unknown/bad: No archive found",
            "~nonexistent/unknown/bad",
            "user",
            "",
        )

    def test_checkArchiveAuthToken_anonymous_private(self):
        archive = self.factory.makeArchive(private=True)
        self.assertUnauthorized(
            "checkArchiveAuthToken",
            "<anonymous>@%s: Private archive requires authorization"
            % archive.reference,
            archive.reference,
            None,
            None,
        )

    def test_checkArchiveAuthToken_anonymous_public(self):
        archive = self.factory.makeArchive()
        self.assertIsNone(
            self.archive_api.checkArchiveAuthToken(
                archive.reference, None, None
            )
        )
        self.assertLogs("%s: Authorized (public)" % archive.reference)

    def test_checkArchiveAuthToken_no_tokens(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        self.assertNotFound(
            "checkArchiveAuthToken",
            "No valid tokens for 'nobody' in '%s'." % archive.reference,
            "nobody@%s: No valid tokens" % archive.reference,
            archive.reference,
            "nobody",
            "",
        )

    def test_checkArchiveAuthToken_no_named_tokens(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        self.assertNotFound(
            "checkArchiveAuthToken",
            "No valid tokens for '+missing' in '%s'." % archive.reference,
            "+missing@%s: No valid tokens" % archive.reference,
            archive.reference,
            "+missing",
            "",
        )

    def test_checkArchiveAuthToken_buildd_macaroon_wrong_archive(self):
        archive = self.factory.makeArchive(private=True)
        build = self.factory.makeBinaryPackageBuild(archive=archive)
        other_archive = self.factory.makeArchive(
            distribution=archive.distribution, private=True
        )
        removeSecurityProxy(build).updateStatus(BuildStatus.BUILDING)
        issuer = removeSecurityProxy(
            getUtility(IMacaroonIssuer, "binary-package-build")
        )
        macaroon = issuer.issueMacaroon(build)
        self.assertUnauthorized(
            "checkArchiveAuthToken",
            "buildd@%s: Macaroon verification failed"
            % other_archive.reference,
            other_archive.reference,
            "buildd",
            macaroon.serialize(),
        )

    def test_checkArchiveAuthToken_buildd_macaroon_not_building(self):
        archive = self.factory.makeArchive(private=True)
        build = self.factory.makeBinaryPackageBuild(archive=archive)
        issuer = removeSecurityProxy(
            getUtility(IMacaroonIssuer, "binary-package-build")
        )
        macaroon = issuer.issueMacaroon(build)
        self.assertUnauthorized(
            "checkArchiveAuthToken",
            "buildd@%s: Macaroon verification failed" % archive.reference,
            archive.reference,
            "buildd",
            macaroon.serialize(),
        )

    def test_checkArchiveAuthToken_buildd_macaroon_wrong_user(self):
        archive = self.factory.makeArchive(private=True)
        build = self.factory.makeBinaryPackageBuild(archive=archive)
        removeSecurityProxy(build).updateStatus(BuildStatus.BUILDING)
        issuer = removeSecurityProxy(
            getUtility(IMacaroonIssuer, "binary-package-build")
        )
        macaroon = issuer.issueMacaroon(build)
        self.assertNotFound(
            "checkArchiveAuthToken",
            "No valid tokens for 'another-user' in '%s'." % archive.reference,
            "another-user@%s: No valid tokens" % archive.reference,
            archive.reference,
            "another-user",
            macaroon.serialize(),
        )

    def test_checkArchiveAuthToken_buildd_macaroon_correct(self):
        archive = self.factory.makeArchive(private=True)
        build = self.factory.makeBinaryPackageBuild(archive=archive)
        removeSecurityProxy(build).updateStatus(BuildStatus.BUILDING)
        issuer = removeSecurityProxy(
            getUtility(IMacaroonIssuer, "binary-package-build")
        )
        macaroon = issuer.issueMacaroon(build)
        self.assertIsNone(
            self.archive_api.checkArchiveAuthToken(
                archive.reference, "buildd", macaroon.serialize()
            )
        )
        self.assertLogs("buildd@%s: Authorized" % archive.reference)

    def test_checkArchiveAuthToken_named_token_wrong_password(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        token = archive.newNamedAuthToken("special")
        self.assertUnauthorized(
            "checkArchiveAuthToken",
            "+special@%s: Password does not match" % archive.reference,
            archive.reference,
            "+special",
            token.token + "-bad",
        )

    def test_checkArchiveAuthToken_named_token_deactivated(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        token = archive.newNamedAuthToken("special")
        removeSecurityProxy(token).deactivate()
        self.assertNotFound(
            "checkArchiveAuthToken",
            "No valid tokens for '+special' in '%s'." % archive.reference,
            "+special@%s: No valid tokens" % archive.reference,
            archive.reference,
            "+special",
            token.token,
        )

    def test_checkArchiveAuthToken_named_token_correct_password(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        token = archive.newNamedAuthToken("special")
        self.assertIsNone(
            self.archive_api.checkArchiveAuthToken(
                archive.reference, "+special", token.token
            )
        )
        self.assertLogs("+special@%s: Authorized" % archive.reference)

    def test_checkArchiveAuthToken_personal_token_wrong_password(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        subscriber = self.factory.makePerson()
        archive.newSubscription(subscriber, archive.owner)
        token = archive.newAuthToken(subscriber)
        self.assertUnauthorized(
            "checkArchiveAuthToken",
            "%s@%s: Password does not match"
            % (subscriber.name, archive.reference),
            archive.reference,
            subscriber.name,
            token.token + "-bad",
        )

    def test_checkArchiveAuthToken_personal_token_deactivated(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        subscriber = self.factory.makePerson()
        archive.newSubscription(subscriber, archive.owner)
        token = archive.newAuthToken(subscriber)
        removeSecurityProxy(token).deactivate()
        self.assertNotFound(
            "checkArchiveAuthToken",
            "No valid tokens for '%s' in '%s'."
            % (subscriber.name, archive.reference),
            "%s@%s: No valid tokens" % (subscriber.name, archive.reference),
            archive.reference,
            subscriber.name,
            token.token,
        )

    def test_checkArchiveAuthToken_personal_token_cancelled(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        subscriber = self.factory.makePerson()
        subscription = archive.newSubscription(subscriber, archive.owner)
        token = archive.newAuthToken(subscriber)
        removeSecurityProxy(subscription).cancel(archive.owner)
        self.assertNotFound(
            "checkArchiveAuthToken",
            "No valid tokens for '%s' in '%s'."
            % (subscriber.name, archive.reference),
            "%s@%s: No valid tokens" % (subscriber.name, archive.reference),
            archive.reference,
            subscriber.name,
            token.token,
        )

    def test_checkArchiveAuthToken_personal_token_correct_password(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        subscriber = self.factory.makePerson()
        archive.newSubscription(subscriber, archive.owner)
        token = archive.newAuthToken(subscriber)
        self.assertIsNone(
            self.archive_api.checkArchiveAuthToken(
                archive.reference, subscriber.name, token.token
            )
        )
        self.assertLogs(
            "%s@%s: Authorized" % (subscriber.name, archive.reference)
        )

    def test_translatePath_unknown_archive(self):
        self.assertNotFound(
            "translatePath",
            "No archive found for '~nonexistent/unknown/bad'.",
            "~nonexistent/unknown/bad: No archive found",
            "~nonexistent/unknown/bad",
            "dists/jammy/InRelease",
        )

    def test_translatePath_non_debian_archive(self):
        archive = removeSecurityProxy(
            self.factory.makeArchive(
                repository_format=ArchiveRepositoryFormat.PYTHON
            )
        )
        self.assertNotFound(
            "translatePath",
            "Can't translate paths in '%s' with format Python."
            % archive.reference,
            "%s: Repository format is Python" % archive.reference,
            archive.reference,
            "dists/jammy/InRelease",
        )

    def test_translatePath_by_hash_unsupported_checksum(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        archive_file = self.factory.makeArchiveFile(
            archive=archive,
            container="release:jammy",
            path="dists/jammy/InRelease",
        )
        path = (
            "dists/jammy/by-hash/SHA1/%s"
            % archive_file.library_file.content.sha1
        )
        self.assertNotFound(
            "translatePath",
            "'%s' not found in '%s'." % (path, archive.reference),
            "%s: %s not found" % (archive.reference, path),
            archive.reference,
            path,
        )

    def test_translatePath_by_hash_checksum_not_found(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        self.factory.makeArchiveFile(
            archive=archive,
            container="release:jammy",
            path="dists/jammy/InRelease",
        )
        path = "dists/jammy/by-hash/SHA256/nonexistent"
        self.assertNotFound(
            "translatePath",
            "'%s' not found in '%s'." % (path, archive.reference),
            "%s: %s not found" % (archive.reference, path),
            archive.reference,
            path,
        )

    def test_translatePath_by_hash_checksum_expired(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        archive_file = self.factory.makeArchiveFile(
            archive=archive,
            container="release:jammy",
            path="dists/jammy/InRelease",
        )
        path = (
            "dists/jammy/by-hash/SHA256/%s"
            % archive_file.library_file.content.sha256
        )
        removeSecurityProxy(archive_file.library_file).content = None
        self.assertNotFound(
            "translatePath",
            "'%s' not found in '%s'." % (path, archive.reference),
            "%s: %s not found" % (archive.reference, path),
            archive.reference,
            path,
        )

    def test_translatePath_by_hash_checksum_found(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        now = get_transaction_timestamp(IStore(archive))
        self.factory.makeArchiveFile(
            archive=archive,
            container="release:jammy",
            path="dists/jammy/InRelease",
            date_superseded=now,
            scheduled_deletion_date=now + timedelta(days=1),
        )
        archive_file = self.factory.makeArchiveFile(
            archive=archive,
            container="release:jammy",
            path="dists/jammy/InRelease",
        )
        path = (
            "dists/jammy/by-hash/SHA256/%s"
            % archive_file.library_file.content.sha256
        )
        self.assertEqual(
            archive_file.library_file.getURL(),
            self.archive_api.translatePath(archive.reference, path),
        )
        self.assertLogs(
            "%s: %s (by-hash) -> LFA %d"
            % (archive.reference, path, archive_file.library_file.id)
        )

    def test_translatePath_by_hash_checksum_found_private(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        now = get_transaction_timestamp(IStore(archive))
        self.factory.makeArchiveFile(
            archive=archive,
            container="release:jammy",
            path="dists/jammy/InRelease",
            date_superseded=now,
            scheduled_deletion_date=now + timedelta(days=1),
        )
        archive_file = self.factory.makeArchiveFile(
            archive=archive,
            container="release:jammy",
            path="dists/jammy/InRelease",
        )
        path = (
            "dists/jammy/by-hash/SHA256/%s"
            % archive_file.library_file.content.sha256
        )
        self.assertStartsWith(
            archive_file.library_file.getURL() + "?token=",
            self.archive_api.translatePath(archive.reference, path),
        )
        self.assertLogs(
            "%s: %s (by-hash) -> LFA %d"
            % (archive.reference, path, archive_file.library_file.id)
        )

    def test_translatePath_non_pool_not_found(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        self.factory.makeArchiveFile(archive=archive)
        self.assertNotFound(
            "translatePath",
            "'nonexistent/path' not found in '%s'." % archive.reference,
            "%s: nonexistent/path not found" % archive.reference,
            archive.reference,
            "nonexistent/path",
        )

    def test_translatePath_non_pool_expired(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        path = "dists/focal/InRelease"
        archive_file = self.factory.makeArchiveFile(archive=archive, path=path)
        removeSecurityProxy(archive_file.library_file).content = None
        self.assertNotFound(
            "translatePath",
            "'%s' not found in '%s'." % (path, archive.reference),
            "%s: %s not found" % (archive.reference, path),
            archive.reference,
            path,
        )

    def test_translatePath_non_pool_found(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        now = get_transaction_timestamp(IStore(archive))
        self.factory.makeArchiveFile(archive=archive)
        path = "dists/focal/InRelease"
        archive_files = [
            self.factory.makeArchiveFile(
                archive=archive,
                path=path,
                date_superseded=now,
                scheduled_deletion_date=now + timedelta(days=1),
            ),
            self.factory.makeArchiveFile(archive=archive, path=path),
        ]
        self.assertEqual(
            archive_files[1].library_file.getURL(),
            self.archive_api.translatePath(archive.reference, path),
        )
        self.assertLogs(
            "%s: %s (non-pool) -> LFA %d"
            % (
                archive.reference,
                path,
                archive_files[1].library_file.id,
            )
        )

    def test_translatePath_non_pool_found_private(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        now = get_transaction_timestamp(IStore(archive))
        self.factory.makeArchiveFile(archive=archive)
        path = "dists/focal/InRelease"
        archive_files = [
            self.factory.makeArchiveFile(
                archive=archive,
                path=path,
                date_superseded=now,
                scheduled_deletion_date=now + timedelta(days=1),
            ),
            self.factory.makeArchiveFile(archive=archive, path=path),
        ]
        self.assertStartsWith(
            archive_files[1].library_file.getURL() + "?token=",
            self.archive_api.translatePath(archive.reference, path),
        )
        self.assertLogs(
            "%s: %s (non-pool) -> LFA %d"
            % (
                archive.reference,
                path,
                archive_files[1].library_file.id,
            )
        )

    def test_translatePath_pool_bad_file_name(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        path = "pool/nonexistent"
        self.assertNotFound(
            "translatePath",
            "'%s' not found in '%s'." % (path, archive.reference),
            "%s: %s not found" % (archive.reference, path),
            archive.reference,
            path,
        )

    def test_translatePath_pool_source_not_found(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        self.factory.makeSourcePackagePublishingHistory(
            archive=archive,
            status=PackagePublishingStatus.PUBLISHED,
            sourcepackagename="test-package",
            component="main",
        )
        path = "pool/main/t/test-package/test-package_1.dsc"
        self.assertNotFound(
            "translatePath",
            "'%s' not found in '%s'." % (path, archive.reference),
            "%s: %s not found" % (archive.reference, path),
            archive.reference,
            path,
        )

    def test_translatePath_pool_source_expired(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        spph = self.factory.makeSourcePackagePublishingHistory(
            archive=archive,
            status=PackagePublishingStatus.PUBLISHED,
            sourcepackagename="test-package",
            component="main",
        )
        sprf = self.factory.makeSourcePackageReleaseFile(
            sourcepackagerelease=spph.sourcepackagerelease,
            library_file=self.factory.makeLibraryFileAlias(
                filename="test-package_1.dsc", db_only=True
            ),
        )
        self.factory.makeSourcePackageReleaseFile(
            sourcepackagerelease=spph.sourcepackagerelease,
            library_file=self.factory.makeLibraryFileAlias(
                filename="test-package_1.tar.xz", db_only=True
            ),
        )
        removeSecurityProxy(sprf.libraryfile).content = None
        path = "pool/main/t/test-package/test-package_1.dsc"
        self.assertNotFound(
            "translatePath",
            "'%s' not found in '%s'." % (path, archive.reference),
            "%s: %s not found" % (archive.reference, path),
            archive.reference,
            path,
        )

    def test_translatePath_pool_source_found(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        spph = self.factory.makeSourcePackagePublishingHistory(
            archive=archive,
            status=PackagePublishingStatus.PUBLISHED,
            sourcepackagename="test-package",
            component="main",
        )
        sprf = self.factory.makeSourcePackageReleaseFile(
            sourcepackagerelease=spph.sourcepackagerelease,
            library_file=self.factory.makeLibraryFileAlias(
                filename="test-package_1.dsc", db_only=True
            ),
        )
        self.factory.makeSourcePackageReleaseFile(
            sourcepackagerelease=spph.sourcepackagerelease,
            library_file=self.factory.makeLibraryFileAlias(
                filename="test-package_1.tar.xz", db_only=True
            ),
        )
        IStore(sprf).flush()
        path = "pool/main/t/test-package/test-package_1.dsc"
        self.assertEqual(
            sprf.libraryfile.getURL(),
            self.archive_api.translatePath(archive.reference, path),
        )
        self.assertLogs(
            "%s: %s (pool) -> LFA %d"
            % (archive.reference, path, sprf.libraryfile.id)
        )

    def test_translatePath_pool_source_found_private(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        with person_logged_in(archive.owner):
            spph = self.factory.makeSourcePackagePublishingHistory(
                archive=archive,
                status=PackagePublishingStatus.PUBLISHED,
                sourcepackagename="test-package",
                component="main",
            )
            sprf = self.factory.makeSourcePackageReleaseFile(
                sourcepackagerelease=spph.sourcepackagerelease,
                library_file=self.factory.makeLibraryFileAlias(
                    filename="test-package_1.dsc", db_only=True
                ),
            )
            self.factory.makeSourcePackageReleaseFile(
                sourcepackagerelease=spph.sourcepackagerelease,
                library_file=self.factory.makeLibraryFileAlias(
                    filename="test-package_1.tar.xz", db_only=True
                ),
            )
            IStore(sprf).flush()
        path = "pool/main/t/test-package/test-package_1.dsc"
        self.assertStartsWith(
            sprf.libraryfile.getURL() + "?token=",
            self.archive_api.translatePath(archive.reference, path),
        )
        self.assertLogs(
            "%s: %s (pool) -> LFA %d"
            % (archive.reference, path, sprf.libraryfile.id)
        )

    def test_translatePath_pool_binary_not_found(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        self.factory.makeBinaryPackagePublishingHistory(
            archive=archive,
            status=PackagePublishingStatus.PUBLISHED,
            sourcepackagename="test-package",
            component="main",
        )
        path = "pool/main/t/test-package/test-package_1_amd64.deb"
        self.assertNotFound(
            "translatePath",
            "'%s' not found in '%s'." % (path, archive.reference),
            "%s: %s not found" % (archive.reference, path),
            archive.reference,
            path,
        )

    def test_translatePath_pool_binary_expired(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            archive=archive,
            status=PackagePublishingStatus.PUBLISHED,
            sourcepackagename="test-package",
            component="main",
        )
        bpf = self.factory.makeBinaryPackageFile(
            binarypackagerelease=bpph.binarypackagerelease,
            library_file=self.factory.makeLibraryFileAlias(
                filename="test-package_1_amd64.deb", db_only=True
            ),
        )
        removeSecurityProxy(bpf.libraryfile).content = None
        path = "pool/main/t/test-package/test-package_1_amd64.deb"
        self.assertNotFound(
            "translatePath",
            "'%s' not found in '%s'." % (path, archive.reference),
            "%s: %s not found" % (archive.reference, path),
            archive.reference,
            path,
        )

    def test_translatePath_pool_binary_found(self):
        archive = removeSecurityProxy(self.factory.makeArchive())
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            archive=archive,
            status=PackagePublishingStatus.PUBLISHED,
            sourcepackagename="test-package",
            component="main",
        )
        bpf = self.factory.makeBinaryPackageFile(
            binarypackagerelease=bpph.binarypackagerelease,
            library_file=self.factory.makeLibraryFileAlias(
                filename="test-package_1_amd64.deb", db_only=True
            ),
        )
        bpph2 = self.factory.makeBinaryPackagePublishingHistory(
            archive=archive,
            status=PackagePublishingStatus.PUBLISHED,
            sourcepackagename="test-package",
            component="main",
        )
        self.factory.makeBinaryPackageFile(
            binarypackagerelease=bpph2.binarypackagerelease,
            library_file=self.factory.makeLibraryFileAlias(
                filename="test-package_1_i386.deb", db_only=True
            ),
        )
        IStore(bpf).flush()
        path = "pool/main/t/test-package/test-package_1_amd64.deb"
        self.assertEqual(
            bpf.libraryfile.getURL(),
            self.archive_api.translatePath(archive.reference, path),
        )
        self.assertLogs(
            "%s: %s (pool) -> LFA %d"
            % (archive.reference, path, bpf.libraryfile.id)
        )

    def test_translatePath_pool_binary_found_private(self):
        archive = removeSecurityProxy(self.factory.makeArchive(private=True))
        with person_logged_in(archive.owner):
            bpph = self.factory.makeBinaryPackagePublishingHistory(
                archive=archive,
                status=PackagePublishingStatus.PUBLISHED,
                sourcepackagename="test-package",
                component="main",
            )
            bpf = self.factory.makeBinaryPackageFile(
                binarypackagerelease=bpph.binarypackagerelease,
                library_file=self.factory.makeLibraryFileAlias(
                    filename="test-package_1_amd64.deb", db_only=True
                ),
            )
            bpph2 = self.factory.makeBinaryPackagePublishingHistory(
                archive=archive,
                status=PackagePublishingStatus.PUBLISHED,
                sourcepackagename="test-package",
                component="main",
            )
            self.factory.makeBinaryPackageFile(
                binarypackagerelease=bpph2.binarypackagerelease,
                library_file=self.factory.makeLibraryFileAlias(
                    filename="test-package_1_i386.deb", db_only=True
                ),
            )
            IStore(bpf).flush()
        path = "pool/main/t/test-package/test-package_1_amd64.deb"
        self.assertStartsWith(
            bpf.libraryfile.getURL() + "?token=",
            self.archive_api.translatePath(archive.reference, path),
        )
        self.assertLogs(
            "%s: %s (pool) -> LFA %d"
            % (archive.reference, path, bpf.libraryfile.id)
        )
