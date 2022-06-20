Checking messages against gettext
=================================

Before accepting a translation message, Launchpad runs it through
gettext to check for certain errors.  For example, if the message is
marked as a C format string in the template, using the c-format flag,
the set of % conversion specifiers in the translation should be
compatible with those of the original English string in the template.
Other languages such as Python have similar format string capabilities
with corresponding flags.

But sometimes it is possible for invalid messages to make it into the
database.  It may be due to a bug in Launchpad, or it could be due to a
gettext update that notices incompatibilities that earlier versions
didn't.


Test setup
----------

Here we use an instrumented version of the script that counts messages
checked instead of real time.  This gets around the indeterminate commit
points that would otherwise be in the output.

    >>> from zope.security.proxy import removeSecurityProxy

    >>> from lp.services.database.sqlbase import quote
    >>> from lp.translations.scripts.gettext_check_messages import (
    ...     GettextCheckMessages)
    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.testing.faketransaction import FakeTransaction

    >>> class InstrumentedGettextCheckMessages(GettextCheckMessages):
    ...     _commit_interval = 3
    ...     def _get_time(self):
    ...         return self._check_count

    >>> def run_checker(options, commit_interval=None):
    ...     """Create and run an instrumented `GettextCheckMessages`."""
    ...     checker = InstrumentedGettextCheckMessages(
    ...         'gettext-check-messages-test', test_args=options)
    ...     checker.logger = FakeLogger()
    ...     checker.txn = FakeTransaction(log_calls=True)
    ...     if commit_interval is not None:
    ...         checker._commit_interval = commit_interval
    ...     checker.main()

    >>> login('foo.bar@canonical.com')

    >>> pofile = factory.makePOFile()
    >>> template = pofile.potemplate

A sample translatable message is flagged as containing a C-style format
string.  This means that any "%d" sequences and such are significant.
So gettext will check those in the translations for compatibility with
those in the original message.

    >>> potmsgset = factory.makePOTMsgSet(
    ...     potemplate=template, singular=u'%d n', sequence=1)
    >>> removeSecurityProxy(potmsgset).flagscomment = 'c-format'
    >>> for flag in potmsgset.flags:
    ...     print(flag)
    c-format

The sample message has an upstream translation, and an Ubuntu
in Launchpad that differs from the upstream one.

    >>> ubuntu_message = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile, potmsgset=potmsgset, translator=template.owner,
    ...     reviewer=template.owner, translations=[u'%d c'])
    >>> ubuntu_message = removeSecurityProxy(ubuntu_message)

    >>> upstream_message = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile, potmsgset=potmsgset, translator=template.owner,
    ...     reviewer=template.owner, translations=[u'%d i'])
    >>> upstream_message = removeSecurityProxy(upstream_message)

    >>> upstream_message.is_current_ubuntu = False
    >>> ubuntu_message.is_current_upstream = False
    >>> upstream_message.is_current_upstream = True
    >>> ubuntu_message.is_current_ubuntu = True


Basic operation
---------------

The gettext_check_message script goes through a given set of messages
and re-does the gettext check.  Which messages it checks is specified as
a plain SQL WHERE clause.

    >>> run_checker(['-vv', "-w id=%s" % quote(ubuntu_message.id)])
    DEBUG Checking messages matching:  id=...
    DEBUG Checking message ...
    DEBUG Commit point.
    COMMIT
    INFO Done.
    INFO Messages checked: 1
    INFO Validation errors: 0
    INFO Messages disabled: 0
    INFO Commit points: ...


Detecting errors
----------------

If a translation fails to validate against its potmsgset, the script
detects the problem when it checks that message.

    >>> ubuntu_message.is_current_ubuntu
    True

    >>> from lp.services.propertycache import get_property_cache
    >>> get_property_cache(ubuntu_message).translations = [u'%s c']

    >>> run_checker(["-w id=%s" % quote(ubuntu_message.id)])
    DEBUG Checking messages matching:  id=...
    DEBUG Checking message ...
    INFO ... (ubuntu): format specifications ... are not the same
    DEBUG Commit point.
    COMMIT
    DEBUG Commit point.
    COMMIT
    INFO Done.
    INFO Messages checked: 1
    INFO Validation errors: 1
    INFO Messages disabled: 1
    INFO Commit points: ...

The failed message is demoted to a mere suggestion.

    >>> ubuntu_message.is_current_ubuntu
    False


Output
------

Besides Ubuntu messages, the script's output also distinguishes
upstream ones, and ones that are completely unused. The upstream message
happens to produce validation errors.

    >>> get_property_cache(upstream_message).translations = [u'%s %s i']

In this example we'd like to see a nicely predictable ordering, so we
add a sort order using the -o option.

    >>> run_checker(['-w', 'potmsgset=%s' % quote(potmsgset), '-o',  'id'])
    DEBUG Checking messages matching:  potmsgset=...
    DEBUG Checking message ...
    INFO ... (unused): format specifications ... are not the same
    DEBUG Commit point.
    COMMIT
    DEBUG Checking message ...
    INFO ... (upstream): number of format specifications ... does not match...
    DEBUG Commit point.
    COMMIT
    INFO Done.
    INFO Messages checked: 2
    INFO Validation errors: 2
    INFO Messages disabled: 1
    INFO Commit points: 2

The script also notes when a message is shared between upstream and Ubuntu.

    >>> upstream_message.is_current_ubuntu = True
    >>> upstream_message.is_current_upstream = True
    >>> run_checker(["-w id=%s" % quote(upstream_message.id)])
    DEBUG ...
    INFO ... (ubuntu, upstream): number of format specifications ...


Dry runs
--------

The --dry-run option makes the script abort all its database changes.

    >>> ubuntu_message.is_current_ubuntu = True

    >>> run_checker(["-w id=%s" % quote(ubuntu_message.id), '--dry-run'])
    INFO Dry run.  Not making any changes.
    DEBUG Checking messages matching:  id=...
    DEBUG Checking message ...
    INFO ... (ubuntu): format specifications ... are not the same
    DEBUG Commit point.
    ABORT
    DEBUG Commit point.
    ABORT
    INFO Done.
    INFO Messages checked: 1
    INFO Validation errors: 1
    INFO Messages disabled: 1
    INFO Commit points: 2


Commit points
-------------

To avoid long-running transactions and potential locks, the script
commits regularly.  Normally this happens every few seconds.  For the
purpose of this test we count messages checked.  If we set the commit
interval to 1, we get a commit after every message plus one at the end
to close things off neatly.

    >>> run_checker(["-w potmsgset=%s" % quote(potmsgset)], commit_interval=1)
    DEBUG Checking messages matching:  potmsgset=...
    DEBUG Checking message ...
    INFO ... (...): number of format specifications ...
    DEBUG Commit point.
    COMMIT
    DEBUG Checking message ...
    INFO ... (...): format specifications ... are not the same
    DEBUG Commit point.
    COMMIT
    DEBUG Commit point.
    COMMIT
    INFO Done.
    INFO Messages checked: 2
    INFO Validation errors: 2
    INFO Messages disabled: 0
    INFO Commit points: 3
