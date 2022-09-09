Code Import Jobs
================

A CodeImportJob is a record of a pending or running code import job.

CodeImports are hidden from regular users currently. David Allouche is a
member of the vcs-imports team and can access the objects freely.

    >>> login("david.allouche@canonical.com")

They can be accessed via a utility registered for the ICodeImportJobSet
interface.

    >>> from lp.testing import verifyObject
    >>> from lp.code.interfaces.codeimportjob import ICodeImportJobSet
    >>> job_set = getUtility(ICodeImportJobSet)
    >>> verifyObject(ICodeImportJobSet, job_set)
    True

The code-import-worker scripts are attached to specific job objects and
retrieve jobs by database id using the CodeImportJobSet.getById method.

    >>> from lp.code.interfaces.codeimportjob import ICodeImportJob
    >>> verifyObject(ICodeImportJob, job_set.getById(1))
    True

The webapp gets the current job for display using the
CodeImport.import_job property.

CodeImportJob objects can also be retrieved using the import_job
property of a CodeImport object. It is useful for the webapp to display
the current job of a given CodeImport.

    >>> from lp.code.interfaces.codeimport import ICodeImportSet
    >>> code_import = getUtility(ICodeImportSet).get(1)
    >>> verifyObject(ICodeImportJob, code_import.import_job)
    True

The life cycle of a CodeImportJob involves the creation of other objects
at various points. To enforce this, CodeImportJob objects are only
modified using the CodeImportJobWorkflow utility.

    >>> from lp.code.interfaces.codeimportjob import ICodeImportJobWorkflow
    >>> workflow = getUtility(ICodeImportJobWorkflow)
    >>> verifyObject(ICodeImportJobWorkflow, workflow)
    True


Sample data of interest
-----------------------

There are two CodeImport objects of interest in the sample data.

    >>> from lp.code.interfaces.branchlookup import IBranchLookup
    >>> from lp.code.interfaces.codeimport import ICodeImportSet
    >>> branch_lookup = getUtility(IBranchLookup)
    >>> code_import_set = getUtility(ICodeImportSet)

One has review_status set to NEW.

    >>> new_import_branch = branch_lookup.getByUniqueName(
    ...     "~vcs-imports/evolution/import"
    ... )
    >>> new_import = code_import_set.getByBranch(new_import_branch)
    >>> print(new_import.review_status.name)
    NEW

The other one has review_status set to REVIEWED.

    >>> reviewed_import_branch = branch_lookup.getByUniqueName(
    ...     "~vcs-imports/gnome-terminal/import"
    ... )
    >>> reviewed_import = code_import_set.getByBranch(reviewed_import_branch)
    >>> print(reviewed_import.review_status.name)
    REVIEWED

Some workflow methods expect the user that is requesting the action. We
use the No Privileges Person, regardless of what privileges may be
required to initiate the action.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> person_set = getUtility(IPersonSet)
    >>> nopriv = person_set.getByName("no-priv")


Test helpers
------------

The NewEvents class helps testing the creation of CodeImportEvent
objects.

    >>> from lp.code.model.tests.test_codeimportjob import NewEvents


Testing whether a job is overdue
--------------------------------

CodeImportJob objects have a date_due attribute that specifies when the
job should ideally be started. If the date_due is in the past, the job
is said to be overdue, and will be run as soon as possible.

The CodeImportJob.isOverdue() method tells whether a job is overdue.

    >>> from datetime import datetime
    >>> from pytz import UTC
    >>> import_job = reviewed_import.import_job

    >>> from zope.security.proxy import removeSecurityProxy
    >>> def set_date_due(import_job, date):
    ...     # ICodeImportJob does not allow setting date_due, so we must use
    ...     # removeSecurityProxy to set it.
    ...     removeSecurityProxy(import_job).date_due = date
    ...

If date_due is in the future, then the job is not overdue.

    >>> future_date = datetime(2100, 1, 1, tzinfo=UTC)
    >>> set_date_due(import_job, future_date)
    >>> import_job.isOverdue()
    False

If date_due is in the past, then the job is overdue.

    >>> past_date = datetime(1900, 1, 1, tzinfo=UTC)
    >>> set_date_due(import_job, past_date)
    >>> import_job.isOverdue()
    True

Owing to the fleeting nature of time, if date_due is the time of the
current transaction, then the job is overdue.

    >>> from lp.services.database.constants import UTC_NOW
    >>> set_date_due(import_job, UTC_NOW)
    >>> import_job.isOverdue()
    True


Creating a new job
------------------

CodeImportJob objects are created using the CodeImportJobWorkflow.newJob
method.

In normal use, the only case where a job object is created explicitly is
when the review status of a code import is modified. This case is
handled by the CodeImport.updateFromData method.

When the review status an import changes to REVIEWED, an associated job
is created.

    >>> from lp.code.enums import CodeImportReviewStatus
    >>> unproxied_new_import = removeSecurityProxy(new_import)
    >>> unproxied_new_import.review_status = CodeImportReviewStatus.REVIEWED
    >>> new_job = workflow.newJob(new_import)
    >>> print(new_import.import_job)
    <security proxied ...CodeImportJob instance at 0x...>

Jobs are always created in PENDING state.

    >>> print(new_job.state.name)
    PENDING

When the code import is associated to existing CodeImportResult objects,
the date due may be UTC_NOW or a timestamp in the future. This is
covered in detail in the test_codeimportjob.py file.


Deleting a pending job
----------------------

In normal use, the only case where a job object is deleted explicitly is
when the review status of a code import is modified. This case is
handled by the CodeImport.updateFromData method.

When the review status of an import changes from REVIEWED, and the
associated job is not running, the job is deleted.

    >>> unproxied_new_import.review_status = CodeImportReviewStatus.INVALID
    >>> workflow.deletePendingJob(new_import)
    >>> print(new_import.import_job)
    None


Requesting a job run
--------------------

When a job is pending, users can request that it be run as soon as
possible.

    >>> from datetime import datetime
    >>> from pytz import UTC
    >>> pending_job = reviewed_import.import_job
    >>> future_date = datetime(2100, 1, 1, tzinfo=UTC)

ICodeImportJob does not expose date_due, so we must use removeSecurityProxy.

    >>> removeSecurityProxy(pending_job).date_due = future_date
    >>> new_events = NewEvents()

    >>> workflow.requestJob(pending_job, nopriv)

This records the requesting user in the job object and sets its date due
for running as soon as possible.

    >>> print(pending_job.requesting_user.name)
    no-priv

The job request is also recorded in the CodeImportEvent audit trail.

    >>> print(new_events.summary())
    REQUEST ~vcs-imports/gnome-terminal/import no-priv

Once a job has been requested by a user, it cannot be requested a
second time until the job runs and terminates.  This means that any
Launchpad web application code that is going to call requestJob must
first check the status and if the job has already been requested by
another user, present a message explaining that this has happened.

    >>> workflow.requestJob(pending_job, nopriv)
    Traceback (most recent call last):
    ...
    AssertionError: The CodeImportJob associated with
    ~vcs-imports/gnome-terminal/import was already requested by no-priv.


Starting a job
--------------

When a job is about to performed by a code import worker, the startJob
workflow method updates the job's fields to indicate that it is now
running and which machine it is running on.

    >>> from lp.code.interfaces.codeimportmachine import ICodeImportMachineSet
    >>> machine_set = getUtility(ICodeImportMachineSet)
    >>> machine = machine_set.getByHostname("bazaar-importer")
    >>> new_events = NewEvents()

Run the job:

    >>> workflow.startJob(pending_job, machine)
    >>> running_job = pending_job

The event is also recorded in the CodeImportEvent audit trail.

    >>> print(new_events.summary())
    START ~vcs-imports/gnome-terminal/import bazaar-importer


Recording progress on a job
---------------------------

As the code import worker progresses, it calls the updateHeartbeat
method at least every minute to indicate that it is still progressing.
This allows the situations where a machine falls off the network,
becomes starved of RAM and starts thrashing badly or similar to be
detected.

As updateHeartbeat updates the 'heartbeat' field of the job to the
current transaction time, we force a date in the a past into this
field now so that we can check that updateHeartbeat has an effect.

    >>> removeSecurityProxy(running_job).heartbeat = datetime(
    ...     2007, 1, 1, 0, 0, 0, tzinfo=UTC
    ... )
    >>> new_events = NewEvents()

    >>> workflow.updateHeartbeat(running_job, "some interesting log output")

No code import events are generated by this method.

    >>> print(new_events.summary())
    <BLANKLINE>
