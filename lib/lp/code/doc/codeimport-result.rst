Code Import Results
===================

A CodeImportResult is a record of a completed code import job.  They
are accessed via a utility registered for the ICodeImportResultSet
interface.

    >>> from lp.code.interfaces.codeimportresult import (
    ...     ICodeImportResult, ICodeImportResultSet)
    >>> result_set = getUtility(ICodeImportResultSet)
    >>> from lp.testing import verifyObject
    >>> verifyObject(ICodeImportResultSet, result_set)
    True

The ICodeImportResultSet interface defines methods for creating and
retrieving CodeImportResult objects.

CodeImports are hidden from regular users currently. David Allouche is a
member of the vcs-imports team and can access the objects freely.

    >>> login('david.allouche@canonical.com')

Creating CodeImportResults
--------------------------

Creating CodeImportResult objects is usually done by the finishJob()
method of the CodeImportWorkflow utility, but here we use the object
factory.

    >>> log_data = 'several\nlines\nof\nlog data'
    >>> log_excerpt = log_data.splitlines()[-1]
    >>> log_alias = factory.makeLibraryFileAlias(content=log_data)
    >>> log_alias_id = log_alias.id

Then commit the transaction, so the external librarian process can see
it.

    >>> from transaction import commit
    >>> commit()
    >>> from lp.services.librarian.interfaces import (
    ...     ILibraryFileAliasSet)
    >>> log_alias = getUtility(ILibraryFileAliasSet)[log_alias_id]

    >>> sample_import = factory.makeCodeImport()

Then create a result object.

    >>> from lp.testing import time_counter
    >>> from pytz import UTC
    >>> from datetime import datetime, timedelta
    >>> time_source = time_counter(
    ...     datetime(2008, 1, 1, tzinfo=UTC),
    ...     timedelta(days=1))
    >>> odin = factory.makeCodeImportMachine(hostname="odin")
    >>> from lp.code.enums import CodeImportResultStatus
    >>> new_result = factory.makeCodeImportResult(
    ...     sample_import, result_status=CodeImportResultStatus.SUCCESS,
    ...     date_started=next(time_source), log_excerpt=log_excerpt,
    ...     log_alias=log_alias, machine=odin)
    >>> verifyObject(ICodeImportResult, new_result)
    True

CodeImportResult objects themselves have no behaviour, they are just
read-only records of what happened.

    >>> print(new_result.machine.hostname)
    odin
    >>> print(new_result.requesting_user)
    None
    >>> print(new_result.log_excerpt)
    log data

In order to read the actual log file, the transaction needs to be committed
for the Librarian to save the file.

    >>> print(new_result.log_file.read().decode('UTF-8'))
    several
    lines
    of
    log data
    >>> print(new_result.status.name)
    SUCCESS

A helper property exists to give the duration of the job run.

    >>> print(new_result.job_duration)
    4:00:00


Retrieving CodeImportResults
----------------------------

The CodeImportResult objects for a given import can be retrieved in
reverse chronological order with the results attribute on a code import.

We need to create a few result objects before we can test that this
method works as expected.

    >>> oldest_result = new_result
    >>> middle_result = factory.makeCodeImportResult(
    ...     sample_import, date_started = next(time_source))
    >>> newest_result = factory.makeCodeImportResult(
    ...     sample_import, date_started = next(time_source))

Results for other imports of course should not be present in the
results, so we should create one of those just to be sure that it's
not present.

    >>> result_for_other_import = factory.makeCodeImportResult()

Then we can test that the results are in the order expected.

    >>> results = list(sample_import.results)
    >>> len(results)
    3
    >>> results.index(newest_result)
    0
    >>> results.index(middle_result)
    1
    >>> results.index(oldest_result)
    2

