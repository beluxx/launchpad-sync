# Copyright 2021-2022 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'RevisionStatusArtifact',
    'RevisionStatusArtifactSet',
    'RevisionStatusReport',
    ]

import io
import os

import pytz
from storm.expr import Desc
from storm.locals import (
    And,
    DateTime,
    Int,
    Reference,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import implementer

from lp.app.errors import NotFoundError
from lp.code.enums import (
    RevisionStatusArtifactType,
    RevisionStatusResult,
    )
from lp.code.interfaces.revisionstatus import (
    IRevisionStatusArtifact,
    IRevisionStatusArtifactSet,
    IRevisionStatusReport,
    IRevisionStatusReportSet,
    )
from lp.services.database.constants import UTC_NOW
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import convert_storm_clause_to_string
from lp.services.database.stormbase import StormBase
from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.services.librarian.model import LibraryFileAlias


@implementer(IRevisionStatusReport)
class RevisionStatusReport(StormBase):
    __storm_table__ = 'RevisionStatusReport'

    id = Int(primary=True)

    creator_id = Int(name="creator", allow_none=False)
    creator = Reference(creator_id, "Person.id")

    title = Unicode(name='name', allow_none=False)

    git_repository_id = Int(name='git_repository', allow_none=False)
    git_repository = Reference(git_repository_id, 'GitRepository.id')

    commit_sha1 = Unicode(name='commit_sha1', allow_none=False)

    url = Unicode(name='url', allow_none=True)

    result_summary = Unicode(name='description', allow_none=True)

    result = DBEnum(name='result', allow_none=True, enum=RevisionStatusResult)

    ci_build_id = Int(name="ci_build", allow_none=True)
    ci_build = Reference(ci_build_id, "CIBuild.id")

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)

    date_started = DateTime(name='date_started', tzinfo=pytz.UTC,
                            allow_none=True)
    date_finished = DateTime(name='date_finished', tzinfo=pytz.UTC,
                             allow_none=True)

    def __init__(self, git_repository, user, title, commit_sha1,
                 url, result_summary, result, ci_build=None):
        super().__init__()
        self.creator = user
        self.git_repository = git_repository
        self.title = title
        self.commit_sha1 = commit_sha1
        self.url = url
        self.result_summary = result_summary
        self.ci_build = ci_build
        self.date_created = UTC_NOW
        self.transitionToNewResult(result)

    def setLog(self, log_data):
        filename = '%s-%s.txt' % (self.title, self.commit_sha1)

        if isinstance(log_data, bytes):
            file = io.BytesIO(log_data)
            size = len(log_data)
        else:
            file = log_data
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)

        lfa = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=size,
            file=file, contentType='text/plain',
            restricted=self.git_repository.private)

        getUtility(IRevisionStatusArtifactSet).new(
            lfa, self, RevisionStatusArtifactType.LOG)

    def attach(self, name, data,
               artifact_type=RevisionStatusArtifactType.BINARY):
        """See `IRevisionStatusReport`."""

        if isinstance(data, bytes):
            file = io.BytesIO(data)
            size = len(data)
        else:
            file = data
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)

        lfa = getUtility(ILibraryFileAliasSet).create(
            name=name, size=size, file=file,
            contentType='application/octet-stream',
            restricted=self.git_repository.private)
        getUtility(IRevisionStatusArtifactSet).new(lfa, self, artifact_type)

    def transitionToNewResult(self, result):
        if self.result == RevisionStatusResult.WAITING:
            if result == RevisionStatusResult.RUNNING:
                self.date_started == UTC_NOW
        else:
            self.date_finished = UTC_NOW
        self.result = result

    def update(self, title=None, url=None,
               result_summary=None, result=None):
        if title is not None:
            self.title = title
        if url is not None:
            self.url = url
        if result_summary is not None:
            self.result_summary = result_summary
        if result is not None:
            self.transitionToNewResult(result)

    def getArtifactURLs(self, artifact_type):
        clauses = [
            RevisionStatusArtifact,
            RevisionStatusArtifact.report == self,
        ]
        if artifact_type:
            clauses.append(
                RevisionStatusArtifact.artifact_type == artifact_type)
        artifacts = IStore(RevisionStatusArtifact).find(*clauses)
        return [artifact.download_url for artifact in artifacts]

    @property
    def latest_log(self):
        log = IStore(RevisionStatusArtifact).find(
            RevisionStatusArtifact,
            RevisionStatusArtifact.report == self,
            RevisionStatusArtifact.artifact_type ==
            RevisionStatusArtifactType.LOG).order_by(
            Desc(RevisionStatusArtifact.date_created)).first()
        return log


@implementer(IRevisionStatusReportSet)
class RevisionStatusReportSet:

    def new(self, creator, title, git_repository, commit_sha1,
            url=None, result_summary=None, result=None,
            date_started=None, date_finished=None, log=None, ci_build=None):
        """See `IRevisionStatusReportSet`."""
        store = IStore(RevisionStatusReport)
        report = RevisionStatusReport(git_repository, creator, title,
                                      commit_sha1, url, result_summary,
                                      result, ci_build=ci_build)
        store.add(report)
        return report

    def getByID(self, id):
        return IStore(
            RevisionStatusReport).find(RevisionStatusReport, id=id).one()

    def findByRepository(self, repository):
        return IStore(RevisionStatusReport).find(
            RevisionStatusReport,
            RevisionStatusReport.git_repository == repository)

    def findByCommit(self, repository, commit_sha1):
        """Returns all `RevisionStatusReport` for a repository and commit."""
        return IStore(RevisionStatusReport).find(
            RevisionStatusReport,
            git_repository=repository,
            commit_sha1=commit_sha1).order_by(
                RevisionStatusReport.date_created,
                RevisionStatusReport.id)

    def getByCIBuildAndTitle(self, ci_build, title):
        """See `IRevisionStatusReportSet`."""
        return IStore(RevisionStatusReport).find(
            RevisionStatusReport, ci_build=ci_build, title=title).one()

    def deleteForRepository(self, repository):
        clauses = [
            RevisionStatusArtifact.report == RevisionStatusReport.id,
            RevisionStatusReport.git_repository == repository,
            ]
        where = convert_storm_clause_to_string(And(*clauses))
        IStore(RevisionStatusArtifact).execute("""
            DELETE FROM RevisionStatusArtifact
            USING RevisionStatusReport
            WHERE """ + where)
        self.findByRepository(repository).remove()


@implementer(IRevisionStatusArtifact)
class RevisionStatusArtifact(StormBase):
    __storm_table__ = 'RevisionStatusArtifact'

    id = Int(primary=True)

    library_file_id = Int(name='library_file', allow_none=False)
    library_file = Reference(library_file_id, 'LibraryFileAlias.id')

    report_id = Int(name='report', allow_none=False)
    report = Reference(report_id, 'RevisionStatusReport.id')

    artifact_type = DBEnum(name='type', allow_none=False,
                           enum=RevisionStatusArtifactType)

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=True)

    def __init__(self, library_file, report, artifact_type):
        super().__init__()
        self.library_file = library_file
        self.report = report
        self.artifact_type = artifact_type
        self.date_created = UTC_NOW

    @property
    def download_url(self):
        return ProxiedLibraryFileAlias(
                self.library_file, self).http_url

    def getFileByName(self, filename):
        file_object = IStore(RevisionStatusArtifact).find(
            LibraryFileAlias,
            RevisionStatusArtifact.id == self.id,
            LibraryFileAlias.id == RevisionStatusArtifact.library_file_id,
            LibraryFileAlias.filename == filename).one()
        if file_object is not None:
            return file_object
        raise NotFoundError(filename)

    @property
    def repository(self):
        return self.report.git_repository


@implementer(IRevisionStatusArtifactSet)
class RevisionStatusArtifactSet:

    def new(self, lfa, report, artifact_type):
        """See `IRevisionStatusArtifactSet`."""
        store = IStore(RevisionStatusArtifact)
        artifact = RevisionStatusArtifact(lfa, report, artifact_type)
        store.add(artifact)
        return artifact

    def getById(self, id):
        return IStore(RevisionStatusArtifact).find(
            RevisionStatusArtifact,
            RevisionStatusArtifact.id == id).one()

    def findByReport(self, report):
        return IStore(RevisionStatusArtifact).find(
            RevisionStatusArtifact,
            RevisionStatusArtifact.report == report)

    def getByRepositoryAndID(self, repository, id):
        return IStore(RevisionStatusArtifact).find(
            RevisionStatusArtifact,
            RevisionStatusArtifact.id == id,
            RevisionStatusArtifact.report == RevisionStatusReport.id,
            RevisionStatusReport.git_repository == repository).one()
