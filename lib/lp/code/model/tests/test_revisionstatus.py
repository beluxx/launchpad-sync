# Copyright 2021-2022 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for revision status reports and artifacts."""

import hashlib
from hashlib import sha1
import io
import os

from fixtures import (
    FakeLogger,
    TempDir,
    )
import requests
from storm.store import Store
from testtools.matchers import (
    AnyMatch,
    Equals,
    GreaterThan,
    Is,
    MatchesSetwise,
    MatchesStructure,
    )
from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from lp.app.enums import InformationType
from lp.code.enums import (
    RevisionStatusArtifactType,
    RevisionStatusResult,
    )
from lp.code.interfaces.revisionstatus import (
    IRevisionStatusArtifactSet,
    IRevisionStatusReportSet,
    )
from lp.services.auth.enums import AccessTokenScope
from lp.services.osutils import write_file
from lp.services.webapp.authorization import check_permission
from lp.testing import (
    anonymous_logged_in,
    api_url,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import switch_dbuser
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.pages import webservice_for_person


class TestRevisionStatusReport(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def makeRevisionStatusArtifact(self, report, artifact_type=None):
        # We don't need to upload files to the librarian in this test suite.
        lfa = self.factory.makeLibraryFileAlias(db_only=True)
        return self.factory.makeRevisionStatusArtifact(
            lfa=lfa, report=report, artifact_type=artifact_type)

    def test_owner_public(self):
        # The owner of a public repository can view and edit its reports and
        # artifacts.
        report = self.factory.makeRevisionStatusReport()
        artifact = self.makeRevisionStatusArtifact(report=report)
        with person_logged_in(report.git_repository.owner):
            self.assertTrue(check_permission("launchpad.View", report))
            self.assertTrue(check_permission("launchpad.View", artifact))
            self.assertTrue(check_permission("launchpad.Edit", report))
            self.assertTrue(check_permission("launchpad.Edit", artifact))

    def test_owner_private(self):
        # The owner of a private repository can view and edit its reports
        # and artifacts.
        with person_logged_in(self.factory.makePerson()) as owner:
            report = self.factory.makeRevisionStatusReport(
                git_repository=self.factory.makeGitRepository(
                    owner=owner, information_type=InformationType.USERDATA))
            artifact = self.makeRevisionStatusArtifact(report=report)
            self.assertTrue(check_permission("launchpad.View", report))
            self.assertTrue(check_permission("launchpad.View", artifact))
            self.assertTrue(check_permission("launchpad.Edit", report))
            self.assertTrue(check_permission("launchpad.Edit", artifact))

    def test_random_public(self):
        # An unrelated user can view but not edit reports and artifacts in
        # public repositories.
        report = self.factory.makeRevisionStatusReport()
        artifact = self.makeRevisionStatusArtifact(report=report)
        with person_logged_in(self.factory.makePerson()):
            self.assertTrue(check_permission("launchpad.View", report))
            self.assertTrue(check_permission("launchpad.View", artifact))
            self.assertFalse(check_permission("launchpad.Edit", report))
            self.assertFalse(check_permission("launchpad.Edit", artifact))

    def test_random_private(self):
        # An unrelated user can neither view nor edit reports and artifacts
        # in private repositories.
        with person_logged_in(self.factory.makePerson()) as owner:
            report = self.factory.makeRevisionStatusReport(
                git_repository=self.factory.makeGitRepository(
                    owner=owner, information_type=InformationType.USERDATA))
            artifact = self.makeRevisionStatusArtifact(report=report)
        with person_logged_in(self.factory.makePerson()):
            self.assertFalse(check_permission("launchpad.View", report))
            self.assertFalse(check_permission("launchpad.View", artifact))
            self.assertFalse(check_permission("launchpad.Edit", report))
            self.assertFalse(check_permission("launchpad.Edit", artifact))

    def test_anonymous_public(self):
        # Anonymous users can view but not edit reports and artifacts in
        # public repositories.
        report = self.factory.makeRevisionStatusReport()
        artifact = self.makeRevisionStatusArtifact(report=report)
        with anonymous_logged_in():
            self.assertTrue(check_permission("launchpad.View", report))
            self.assertTrue(check_permission("launchpad.View", artifact))
            self.assertFalse(check_permission("launchpad.Edit", report))
            self.assertFalse(check_permission("launchpad.Edit", artifact))

    def test_anonymous_private(self):
        # Anonymous users can neither view nor edit reports and artifacts in
        # private repositories.
        with person_logged_in(self.factory.makePerson()) as owner:
            report = self.factory.makeRevisionStatusReport(
                git_repository=self.factory.makeGitRepository(
                    owner=owner, information_type=InformationType.USERDATA))
            artifact = self.makeRevisionStatusArtifact(report=report)
        with anonymous_logged_in():
            self.assertFalse(check_permission("launchpad.View", report))
            self.assertFalse(check_permission("launchpad.View", artifact))
            self.assertFalse(check_permission("launchpad.Edit", report))
            self.assertFalse(check_permission("launchpad.Edit", artifact))

    def test_getByCIBuildAndTitle(self):
        build = self.factory.makeCIBuild()

        report = getUtility(
            IRevisionStatusReportSet).getByCIBuildAndTitle(build, "test")
        self.assertEqual(None, report)

        revision_status_report = self.factory.makeRevisionStatusReport(
            title="test",
            ci_build=build,
        )
        Store.of(revision_status_report).flush()
        report = getUtility(
            IRevisionStatusReportSet).getByCIBuildAndTitle(build, "test")
        self.assertEqual("test", report.title)

    def test_latest_log(self):
        report = self.factory.makeRevisionStatusReport()
        self.makeRevisionStatusArtifact(report=report)
        self.makeRevisionStatusArtifact(report=report)
        artifact3 = self.makeRevisionStatusArtifact(report=report)
        with person_logged_in(report.git_repository.owner):
            self.assertEqual(artifact3, report.latest_log)


class TestRevisionStatusReportWebservice(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def getWebservice(self, person, repository):
        with person_logged_in(person):
            secret, _ = self.factory.makeAccessToken(
                owner=person, target=repository,
                scopes=[AccessTokenScope.REPOSITORY_BUILD_STATUS])
        return webservice_for_person(
            person, default_api_version="devel", access_token_secret=secret)

    def _test_setLog(self, private):
        requester = self.factory.makePerson()
        with person_logged_in(requester):
            kwargs = {"owner": requester}
            if private:
                kwargs["information_type"] = InformationType.USERDATA
            repository = self.factory.makeGitRepository(**kwargs)
            report = self.factory.makeRevisionStatusReport(
                git_repository=repository)
            report_url = api_url(report)
        webservice = self.getWebservice(requester, repository)
        content = b'log_content_data'
        response = webservice.named_post(
            report_url, "setLog", log_data=io.BytesIO(content))
        self.assertEqual(200, response.status)

        # A report may have multiple artifacts.
        # We verify that the content we just submitted via API now
        # matches one of the artifacts in the DB for the report.
        with person_logged_in(requester):
            artifacts = list(getUtility(
                IRevisionStatusArtifactSet).findByReport(report))
            self.assertThat(artifacts, AnyMatch(
                MatchesStructure(
                    report=Equals(report),
                    library_file=MatchesStructure(
                        content=MatchesStructure.byEquality(
                            sha256=hashlib.sha256(content).hexdigest()),
                        filename=Equals(
                            "%s-%s.txt" % (report.title, report.commit_sha1)),
                        mimetype=Equals("text/plain"),
                        restricted=Is(private)),
                    artifact_type=Equals(RevisionStatusArtifactType.LOG))))

    def test_setLog(self):
        self._test_setLog(private=False)

    def test_setLog_private(self):
        self._test_setLog(private=True)

    def test_setLog_with_file_object(self):
        switch_dbuser("launchpad_main")

        # create log file
        path = os.path.join(
            self.useFixture(TempDir()).path, "test", "build:0.log"
        )
        content = "some log content"
        write_file(path, content.encode("utf-8"))

        report = self.factory.makeRevisionStatusReport(
            title="build:0",
            ci_build=self.factory.makeCIBuild(),
        )

        with person_logged_in(report.creator):
            with open(path, "rb") as f:
                report.setLog(f)

        artifacts = list(getUtility(
            IRevisionStatusArtifactSet).findByReport(report))
        self.assertEqual(
            artifacts[0].library_file.content.sha1,
            sha1(content.encode()).hexdigest()
        )

    def _test_attach(self, private):
        requester = self.factory.makePerson()
        with person_logged_in(requester):
            kwargs = {"owner": requester}
            if private:
                kwargs["information_type"] = InformationType.USERDATA
            repository = self.factory.makeGitRepository(**kwargs)
            report = self.factory.makeRevisionStatusReport(
                git_repository=repository)
            report_url = api_url(report)
        webservice = self.getWebservice(requester, repository)
        filenames = ["artifact-1", "artifact-2"]
        contents = [b"artifact 1", b"artifact 2"]
        for filename, content in zip(filenames, contents):
            response = webservice.named_post(
                report_url, "attach", name=filename, data=io.BytesIO(content))
            self.assertEqual(200, response.status)

        with person_logged_in(requester):
            artifacts = list(getUtility(
                IRevisionStatusArtifactSet).findByReport(report))
            self.assertThat(artifacts, MatchesSetwise(*(
                MatchesStructure(
                    report=Equals(report),
                    library_file=MatchesStructure(
                        content=MatchesStructure.byEquality(
                            sha256=hashlib.sha256(content).hexdigest()),
                        filename=Equals(filename),
                        mimetype=Equals("application/octet-stream"),
                        restricted=Is(private)),
                    artifact_type=Equals(RevisionStatusArtifactType.BINARY))
                for filename, content in zip(filenames, contents))))

    def test_attach(self):
        self._test_attach(private=False)

    def test_attach_private(self):
        self._test_attach(private=True)

    def test_attach_with_file_object(self):
        switch_dbuser("launchpad_main")

        # create text file
        path = os.path.join(
            self.useFixture(TempDir()).path, "test.md"
        )
        content = "some content"
        write_file(path, content.encode("utf-8"))

        report = self.factory.makeRevisionStatusReport(
            title="build:0",
            ci_build=self.factory.makeCIBuild(),
        )

        with person_logged_in(report.creator):
            with open(path, "rb") as f:
                report.attach("text", f)

        artifacts = list(getUtility(
            IRevisionStatusArtifactSet).findByReport(report))
        self.assertEqual(
            artifacts[0].library_file.content.sha1,
            sha1(content.encode()).hexdigest()
        )

    def test_update(self):
        report = self.factory.makeRevisionStatusReport(
            result=RevisionStatusResult.FAILED)
        requester = report.creator
        repository = report.git_repository
        initial_commit_sha1 = report.commit_sha1
        initial_result_summary = report.result_summary
        report_url = api_url(report)
        webservice = self.getWebservice(requester, repository)
        response = webservice.named_post(
            report_url, "update", title="updated-report-title")
        self.assertEqual(200, response.status)
        with person_logged_in(requester):
            self.assertThat(report, MatchesStructure.byEquality(
                title="updated-report-title",
                commit_sha1=initial_commit_sha1,
                result_summary=initial_result_summary,
                result=RevisionStatusResult.FAILED))
            date_finished_before_update = report.date_finished
        response = webservice.named_post(
            report_url, "update", result="Succeeded")
        self.assertEqual(200, response.status)
        with person_logged_in(requester):
            self.assertThat(report, MatchesStructure(
                title=Equals("updated-report-title"),
                commit_sha1=Equals(initial_commit_sha1),
                result_summary=Equals(initial_result_summary),
                result=Equals(RevisionStatusResult.SUCCEEDED),
                date_finished=GreaterThan(date_finished_before_update)))

    def test_getArtifactURLs(self):
        report = self.factory.makeRevisionStatusReport()
        artifact_log = self.factory.makeRevisionStatusArtifact(
            report=report, artifact_type=RevisionStatusArtifactType.LOG,
            content=b'log_data')
        artifact_binary = self.factory.makeRevisionStatusArtifact(
            report=report, artifact_type=RevisionStatusArtifactType.BINARY,
            content=b'binary_data')
        requester = report.creator
        repository = report.git_repository
        report_url = api_url(report)
        log_url = 'http://code.launchpad.test/%s/+artifact/%s/+files/%s' % (
            repository.unique_name, artifact_log.id,
            artifact_log.library_file.filename)
        binary_url = 'http://code.launchpad.test/%s/+artifact/%s/+files/%s' % (
            repository.unique_name, artifact_binary.id,
            artifact_binary.library_file.filename)
        webservice = self.getWebservice(requester, repository)

        response = webservice.named_get(
            report_url, "getArtifactURLs", artifact_type="Log")

        self.assertEqual(200, response.status)
        with person_logged_in(requester):
            self.assertIn(log_url, response.jsonBody())
            self.assertNotIn(binary_url, response.jsonBody())
            # ensure the url works
            browser = self.getNonRedirectingBrowser()
            browser.open(log_url)
            self.assertEqual(
                303,
                int(browser.headers["Status"].split(" ", 1)[0]))
            self.assertEqual(
                b"log_data",
                requests.get(browser.headers["Location"]).content)

        response = webservice.named_get(
            report_url, "getArtifactURLs", artifact_type="Binary")

        self.assertEqual(200, response.status)
        with person_logged_in(requester):
            self.assertNotIn(log_url, response.jsonBody())
            self.assertIn(binary_url, response.jsonBody())

        response = webservice.named_get(
            report_url, "getArtifactURLs")

        self.assertEqual(200, response.status)
        with person_logged_in(requester):
            self.assertIn(log_url, response.jsonBody())
            self.assertIn(binary_url, response.jsonBody())

    def test_getArtifactURLs_restricted(self):
        self.useFixture(FakeLogger())
        requester = self.factory.makePerson()
        with person_logged_in(requester):
            kwargs = {"owner": requester}
            kwargs["information_type"] = InformationType.USERDATA
            repository = self.factory.makeGitRepository(**kwargs)
            report = self.factory.makeRevisionStatusReport(
                git_repository=repository)
            report_url = api_url(report)
            artifact = self.factory.makeRevisionStatusArtifact(
                report=report, artifact_type=RevisionStatusArtifactType.LOG,
                content=b'log_data', restricted=True)
            log_url = ('http://code.launchpad.test/%s/'
                       '+artifact/%s/+files/%s' % (
                repository.unique_name, artifact.id,
                artifact.library_file.filename))
        webservice = self.getWebservice(requester, repository)

        response = webservice.named_get(
            report_url, "getArtifactURLs", artifact_type="Log")

        self.assertEqual(200, response.status)
        with person_logged_in(requester):
            self.assertIn(log_url, response.jsonBody())
            # ensure the url works - we see failure here without authentication
            browser = self.getNonRedirectingBrowser()
            self.assertRaises(Unauthorized, browser.open, log_url)

            # we should be redirected to librarian with authentication
            browser = self.getNonRedirectingBrowser(user=requester)
            browser.open(log_url)
            self.assertEqual(
                303,
                int(browser.headers["Status"].split(" ", 1)[0]))
            # Actually requesting files from the restricted librarian is
            # cumbersome, but at least test that we're redirected to the
            # restricted librarian with a suitable token.
            self.assertRegex(
                browser.headers["Location"],
                r"^https://.*\.restricted\..*?token=.*")
