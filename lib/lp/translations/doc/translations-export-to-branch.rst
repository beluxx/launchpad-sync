Exporting translations to a bzr branch
======================================

The translations-export-to-branch script visits all ProductSeries with a
translations_branch set, and for each, exports the series' translations
to that branch.

    >>> from lp.services.scripts.tests import run_script
    >>> ret_code, stdout, stderr = run_script(
    ...     "cronscripts/translations-export-to-branch.py", []
    ... )
    >>> ret_code
    0
    >>> print(stdout)
    <BLANKLINE>
    >>> print(stderr)
    INFO Creating lockfile:
    /var/lock/launchpad-translations-export-to-branch.lock
    INFO Exporting to translations branches.
    INFO Processed 0 item(s); 0 failure(s), 0 unpushed branch(es).

    >>> from lp.translations.scripts.translations_to_branch import (
    ...     ExportTranslationsToBranch,
    ... )

The script uses the DirectBranchCommit mechanism to write translation
files into the branches.  We mock it up here.

    >>> from lp.code.model.directbranchcommit import ConcurrentUpdateError

    >>> class MockDirectBranchCommit:
    ...     """Mock DirectBranchCommit.  Prints actions."""
    ...
    ...     simulate_race = False
    ...     bzrbranch = None
    ...     written_files = 0
    ...
    ...     def __init__(self, logger):
    ...         self.logger = logger
    ...
    ...     def writeFile(self, path, contents):
    ...         self.logger.info("Writing file '%s':" % path)
    ...         self.logger.info(six.ensure_text(contents))
    ...         self.written_files += 1
    ...
    ...     def lockForCommit(self):
    ...         pass
    ...
    ...     def _checkForRace(self):
    ...         if self.simulate_race:
    ...             raise ConcurrentUpdateError("Simulated race condition.")
    ...
    ...     def commit(self, message=None, txn=None):
    ...         self._checkForRace()
    ...         self.logger.info("Committed %d file(s)." % self.written_files)
    ...
    ...     def unlock(self):
    ...         self.logger.info("Unlock.")
    ...

    >>> from lp.services.log.logger import FakeLogger

    >>> class MockExportTranslationsToBranch(ExportTranslationsToBranch):
    ...     """Test version of ExportTranslationsToBranch."""
    ...
    ...     simulate_race = False
    ...     simulated_latest_commit = None
    ...     config_name = "translations_export_to_branch"
    ...
    ...     def __init__(self, *args, **kwargs):
    ...         super().__init__(*args, **kwargs)
    ...         self.logger = FakeLogger()
    ...
    ...     def _getLatestTranslationsCommit(self, branch):
    ...         return self.simulated_latest_commit
    ...
    ...     def _makeDirectBranchCommit(self, bzrbranch):
    ...         committer = MockDirectBranchCommit(self.logger)
    ...         committer.simulate_race = self.simulate_race
    ...         return committer
    ...

The Gazblachko project is set up to export its trunk translations to a
branch.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.app.enums import ServiceUsage

    >>> gazblachko = removeSecurityProxy(
    ...     factory.makeProduct(name="gazblachko", displayname="Gazblachko")
    ... )
    >>> gazblachko.translations_usage = ServiceUsage.LAUNCHPAD

    >>> branch = removeSecurityProxy(
    ...     factory.makeBranch(
    ...         name="gazpo", owner=gazblachko.owner, product=gazblachko
    ...     )
    ... )

    >>> trunk = removeSecurityProxy(gazblachko).getSeries("trunk")
    >>> trunk.translations_branch = branch

    >>> import transaction
    >>> transaction.commit()

Gazblachko trunk has two active templates, plus a deactivated one.  All
have Dutch translations.

    >>> def setup_template_and_translations(path, name, iscurrent=True):
    ...     """Set up template, Dutch translations for Gazblachko."""
    ...     template = removeSecurityProxy(
    ...         factory.makePOTemplate(
    ...             productseries=trunk,
    ...             owner=gazblachko.owner,
    ...             name=name,
    ...             path=path,
    ...         )
    ...     )
    ...
    ...     potmsgset = factory.makePOTMsgSet(
    ...         template, singular="%s msgid" % name, sequence=1
    ...     )
    ...
    ...     pofile = factory.makePOFile(
    ...         "nl", potemplate=template, owner=gazblachko.owner
    ...     )
    ...
    ...     factory.makeCurrentTranslationMessage(
    ...         pofile=pofile,
    ...         potmsgset=potmsgset,
    ...         translator=gazblachko.owner,
    ...         reviewer=gazblachko.owner,
    ...         translations=["%s msgstr" % name],
    ...     )
    ...
    ...     if not iscurrent:
    ...         removeSecurityProxy(template).iscurrent = False
    ...
    ...     return pofile
    ...

    >>> main_pofile = setup_template_and_translations(
    ...     "po/main/gazpot.pot", "maingazpot"
    ... )

    >>> module_pofile = setup_template_and_translations(
    ...     "po/module/module.pot", "gazmod"
    ... )

    >>> old_pofile = setup_template_and_translations(
    ...     "po/gazpot.pot", "oldgazpot", iscurrent=False
    ... )

When the translations-export-to-branch script runs, it feeds the
translations to the DirectBranchCommit.

    >>> transaction.commit()
    >>> script = MockExportTranslationsToBranch(
    ...     "export-to-branch", test_args=[]
    ... )
    >>> script.main()
    INFO Exporting to translations branches.
    INFO Exporting Gazblachko trunk series.
    DEBUG ...
    INFO Writing file 'po/main/nl.po':
    INFO # ...
    msgid ""
    msgstr ""
    "..."
    <BLANKLINE>
    msgid "maingazpot msgid"
    msgstr "maingazpot msgstr"
    <BLANKLINE>
    DEBUG ...
    INFO Writing file 'po/module/nl.po':
    INFO # ...
    msgid ""
    msgstr ""
    "..."
    ...
    <BLANKLINE>
    msgid "gazmod msgid"
    msgstr "gazmod msgstr"
    <BLANKLINE>
    DEBUG ...
    INFO Committed 2 file(s).
    INFO Unlock.
    INFO Processed 1 item(s); 0 failure(s), 0 unpushed branch(es).

When Gazblachko stops using Launchpad for Translations, the exports stop
also.

    >>> gazblachko.translations_usage = ServiceUsage.NOT_APPLICABLE
    >>> transaction.commit()
    >>> script.main()
    INFO Exporting to translations branches.
    INFO Processed 0 item(s); 0 failure(s), 0 unpushed branch(es).

    >>> gazblachko.translations_usage = ServiceUsage.LAUNCHPAD
    >>> transaction.commit()


Incremental exports
-------------------

If the script detects that POFiles have not been touched roughly since
the time it last exported them, it won't export them again.

    >>> from datetime import datetime, timedelta, timezone
    >>> now = datetime.now(timezone.utc)
    >>> script.simulated_latest_commit = now
    >>> main_pofile.date_changed = now - timedelta(days=3)
    >>> module_pofile.date_changed = now - timedelta(days=4)
    >>> module_pofile.potemplate.date_last_updated = now - timedelta(days=5)
    >>> transaction.commit()
    >>> old_pofile.date_changed = now - timedelta(days=5)

    >>> script.main()
    INFO Exporting to translations branches.
    INFO Exporting Gazblachko trunk series.
    DEBUG ....
    DEBUG Last commit was at ....
    INFO Unlock.
    INFO Processed 1 item(s); 0 failure(s), 0 unpushed branch(es).

If one of the files is updated, it is exported again.  Unchanged files
are not.

    >>> main_pofile.date_changed = now
    >>> script.main()
    INFO Exporting to translations branches.
    INFO Exporting Gazblachko trunk series.
    DEBUG ....
    DEBUG Last commit was at ...
    INFO Writing file 'po/main/nl.po':
    INFO ...
    INFO Committed 1 file(s).
    INFO Unlock.
    INFO Processed 1 item(s); 0 failure(s), 0 unpushed branch(es).


Unpushed branches
-----------------

The Launchpad UI allows users to register branches in the Launchpad
database without populating them in bzr.  Exporting to such a branch
won't work, so we email a notification to the branch owner.

    >>> import email
    >>> from lp.codehosting.vfs import get_rw_server
    >>> from lp.services.mail import stub
    >>> from lp.testing.factory import (
    ...     remove_security_proxy_and_shout_at_engineer,
    ... )
    >>> productseries = factory.makeProductSeries()
    >>> naked_productseries = remove_security_proxy_and_shout_at_engineer(
    ...     productseries
    ... )
    >>> naked_productseries.translations_branch = factory.makeBranch()
    >>> template = factory.makePOTemplate(productseries=productseries)
    >>> potmsgset = factory.makePOTMsgSet(template)
    >>> pofile = removeSecurityProxy(
    ...     factory.makePOFile("nl", potemplate=template)
    ... )
    >>> tm = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile, potmsgset=potmsgset, translator=template.owner
    ... )

    >>> server = get_rw_server(direct_database=True)
    >>> server.start_server()
    >>> real_script = ExportTranslationsToBranch(
    ...     "export-to-branch", test_args=[]
    ... )
    >>> real_script.logger = FakeLogger()
    >>> try:
    ...     real_script._exportToBranches([productseries])
    ... finally:
    ...     server.destroy()
    ...
    INFO Exporting ...
    INFO Processed 1 item(s); 0 failure(s), 1 unpushed branch(es).

    # Give the email a chance to arrive in the test mailbox.
    >>> transaction.commit()

    >>> sender, recipients, body = stub.test_emails.pop()
    >>> message = email.message_from_bytes(body)
    >>> print(message["Subject"])
    Launchpad: translations branch has not been set up.

    >>> print(message.get_payload())
    Hello,
    There was a problem with translations branch synchronization for
    ...
    Branch synchronization for this release series has been set up to
    commit translations snapshots to the bzr branch at lp://...

For the full message text, see emailtemplates/unpushed-branch.txt.


Race conditions
---------------

The script checks for possible race conditions.  Otherwise it might
overwrite translations committed to the branch that hadn't been
collected for import yet.


Branch races
............

Any translations coming in through a branch push are safe once they're
in the translations import queue.  So the race window spans from the
moment an update is pushed to the moment any translation import branch
jobs have completed.

If the DirectBranchCommit detects a concurrent update, the script will
refuse to commit to the branch.

    >>> script.simulate_race = True
    >>> script.simulated_latest_commit = None
    >>> script.main()
    INFO Exporting to translations branches.
    INFO Exporting Gazblachko trunk series.
    DEBUG ....
    DEBUG No previous translations commit found.
    DEBUG ....
    INFO Writing file 'po/main/nl.po':
    ...
    msgstr "gazmod msgstr"
    <BLANKLINE>
    DEBUG ...
    INFO Unlock.
    ERROR Failure in gazblachko/trunk:
    ConcurrentUpdateError(...Simulated race condition...)
    INFO Processed 1 item(s); 1 failure(s), 0 unpushed branch(es).


Pending imports from same branch
................................

Another race condition is detected by the script itself: there may be
pending translations BranchJobs on the branch.

    >>> from lp.code.model.branchjob import RosettaUploadJob
    >>> trunk.branch = branch
    >>> script.simulate_race = False
    >>> job = RosettaUploadJob.create(branch, None, True)
    >>> job is None
    False
    >>> transaction.commit()
    >>> script.main()
    INFO Exporting to translations branches.
    INFO Exporting Gazblachko trunk series.
    ERROR Failure in gazblachko/trunk:
    ConcurrentUpdateError(...Translations branch for
    Gazblachko trunk series has pending translations changes.
    Not committing...)
    INFO Processed 1 item(s); 1 failure(s), 0 unpushed branch(es).

There is one problem with detecting this race condition.  Jobs are never
cleaned up.  So if the job failed for whatever reason, an unfinished job
will stick around forever.

To avoid blocking on such a job forever, the check ignores jobs that are
old enough that they must have completed one way or another.

    >>> job.date_created -= timedelta(days=7)
    >>> transaction.commit()
    >>> script.main()
    INFO Exporting to translations branches.
    INFO Exporting Gazblachko trunk series.
    DEBUG ...
    INFO Writing file 'po/main/nl.po':
    INFO ...
    INFO Unlock.
    INFO Processed 1 item(s); 0 failure(s), 0 unpushed branch(es).
