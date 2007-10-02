# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = ['CodeImportJobState', 'ICodeImportJob', 'ICodeImportJobSet']

from canonical.launchpad import _
from canonical.launchpad.interfaces.codeimport import ICodeImport
from canonical.launchpad.interfaces.codeimportmachine import ICodeImportMachine
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.interfaces.person import IPerson
from canonical.lazr import (
    DBEnumeratedType, DBItem)

from zope.interface import Interface
from zope.schema import Choice, Datetime, Int, Object, Text


class CodeImportJobState(DBEnumeratedType):
    """Values that ICodeImportJob.state can take."""

    PENDING = DBItem(10, """
        Pending

        The job has a time when it is due to run, and will wait until
        that time or an explicit update request is made.
        """)

    SCHEDULED = DBItem(20, """
        Scheduled

        The job is due to be run.
        """)

    RUNNING = DBItem(30, """
        Running

        The job is running.
        """)


class ICodeImportJob(Interface):
    """A pending or active code import job.

    There is always such a row for any active import, but it will not
    run until date_due is in the past."""

    id = Int(required=True, readonly=True)

    date_created = Datetime(required=True, readonly=True)

    code_import = Object(
        schema=ICodeImport, required=True, readonly=True,
        description=_("The code import that is being worked upon."))

    machine = Object(
        schema=ICodeImportMachine, required=False, readonly=False,
        description=_("The machine job is currently scheduled to run on, or "
                      "where the job is currently running."))

    date_due = Datetime(
        required=True, readonly=False,
        description=_("When the import should happen."))

    state = Choice(
        vocabulary=CodeImportJobState, required=True, readonly=False,
        description=_("The current state of the job."))

    requesting_user = Object(
        schema=IPerson, required=False, readonly=False,
        description=_("The user who requested the import, if any."))

    ordering = Int(
        required=True, readonly=False,
        description=_("A measure of how urgent the job is -- queue entries "
                      "with lower 'ordering' should be processed first, or "
                      "in other words 'ORDER BY ordering' returns the most "
                      "import jobs first."))

    heartbeat = Datetime(
        required=False, readonly=False,
        description=_("While the job is running, this field should be "
                      "updated frequently to indicate that the import job "
                      "hasn't crashed."))

    logtail = Text(
        required=False, readonly=False,
        description=_("The last few lines of output produced by the running "
                      "job. It should be updated at the same time as the "
                      "heartbeat."))

    date_started = Datetime(
        required=False, readonly=False,
        description=_("When the import began to be processed."))


class ICodeImportJobSet(Interface):
    """XXX."""

    def new(code_import):
        """XXX."""
