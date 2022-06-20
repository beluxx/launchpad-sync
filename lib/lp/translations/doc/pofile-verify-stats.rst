POFile statistics
=================

We frequently display statistics about POFiles: how many of its messages
remain untranslated, how many have been changed in Ubuntu, how many have
had suggested translations submitted that need to be reviewed?

It takes too long to gather these statistics on demand, so we cache them in
POFile fields.  When translations are changed, these statistics can be either
updated incrementally or recomputed altogether.

Incremental updates carry a risk of errors creeping in and being preserved
even during some updates.  That's why a cron job trawls the POFile table,
recomputing translation statistics and noting any divergence between the
cached values and the ones it recomputes from scratch.


Direct invocation
-----------------

The statistics verifier is invoked by the cron job, but we can also call
it directly.

    >>> import transaction
    >>> from lp.services.mail.stub import test_emails
    >>> from lp.translations.scripts.verify_pofile_stats import (
    ...     VerifyPOFileStatsProcess)
    >>> from lp.services.log.logger import FakeLogger
    >>> logger = FakeLogger()
    >>> VerifyPOFileStatsProcess(transaction, logger).run()
    INFO Starting verification of POFile stats at id 0
    ...
    INFO Done.
    >>> old_email = test_emails.pop()

All POFile statistics in our database are now correct, and we can test in
more detail.


Limited runs
------------

Old data will probably change less, either because it's superseded by later
distro/product series or because it has reached maturity and stabilized.  To
optimize for this principle, the verifier supports partial runs, skipping
POFiles whose id is lower than some given value.  This gives us room to
schedule more frequent runs on newer data, or we can choose to do a quick
manual run on part of the data if we believe some recent POFile(s) to have
incorrect statistics data.

As an example we verify just the POFiles with id 30 and up (something the
cron script does not allow us to do, but the underlying machinery supports).

    >>> verifier = VerifyPOFileStatsProcess(transaction, logger, 30)
    >>> verifier.run()
    INFO Starting verification of POFile stats at id 30
    INFO Done.

Again we find no errors.  The next section shows what happens when we do.


Reports and correction
----------------------

If for any reason any POFiles' statistics are found to be wrong, the script
reports this giving both the wrong and the corrected statistics.

    >>> from lp.translations.model.pofile import POFile
    >>> pofile = POFile.get(34)
    >>> pofile.getStatistics()
    (0, 0, 3, 0)

We have a POFile with zero current, updated, and unreviewed translations, and
3 translations changed in Ubuntu (compared to upstream).

A software bug incorrectly sets the number of changed translations to 999.

    >>> pofile.rosettacount = 999

We run the verifier on the incorrect POFile (and all POFile's with
higher ids).  It detects and reports the problem, finding a count of 999
changed translations where it expected to find 3.

Incorrect statistics are reported but do not affect the successful
completion of the verifier.

    >>> verifier = VerifyPOFileStatsProcess(transaction, logger, 34)
    >>> verifier.run()
    INFO Starting verification of POFile stats at id 34
    INFO POFile 34:
    cached stats were (0, 0, 999, 0), recomputed as (0, 0, 3, 0)
    INFO Done.

The verifier also corrects the corrupted statistics it finds, so the numbers
are once again what they were.

    >>> pofile.getStatistics()
    (0, 0, 3, 0)

The Translations administrators also receive an email about the error.

    >>> from_addr, to_addrs, body = test_emails.pop()
    >>> len(test_emails)
    0
    >>> to_addrs
    ['launchpad-error-reports@lists.canonical.com']
    >>> in_header = True
    >>> for line in body.decode('UTF-8').splitlines():
    ...     if in_header:
    ...         in_header = (line != '')
    ...     else:
    ...         print(line)
    The POFile statistics verifier encountered errors while checking cached
    statistics in the database:
    <BLANKLINE>
    Exceptions: 0
    POFiles with incorrect statistics: 1
    Total POFiles checked: ...
    <BLANKLINE>
    See the log file for detailed information.

Cron job
--------

The rosetta-pofile-stats cron script invokes the verifier code.  It
completes without finding any errors: the one we introduced earlier was
fixed by running the verifier directly.

    >>> from lp.testing.script import run_script
    >>> (returncode, out, err) = run_script(
    ...     'cronscripts/rosetta-pofile-stats.py', ['--start-id=99'])
    >>> print(returncode)
    0
    >>> print(err)
    INFO    Creating lockfile: /var/lock/launchpad-pofile-stats.lock
    INFO    Starting verification of POFile stats at id 99
    INFO    Done.
