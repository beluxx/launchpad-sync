Converting people into teams
============================

There's a script which allows us to turn any person whose account_status is
NOACCOUNT (which means the person has never actually logged into Launchpad)
into a team.  The script takes the name of the person to be converted into a
team and the name of the team owner as arguments.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> matsubara = getUtility(IPersonSet).getByName('matsubara')
    >>> matsubara.is_team
    False
    >>> matsubara.account_status
    <DBItem AccountStatus.NOACCOUNT...

    >>> from subprocess import Popen, PIPE
    >>> process = Popen(
    ...     'scripts/convert-person-to-team.py -q matsubara mark',
    ...     shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE,
    ...     universal_newlines=True)
    >>> (out, err) = process.communicate()
    >>> print(out)
    <BLANKLINE>
    >>> print(err)
    <BLANKLINE>
    >>> process.returncode
    0

    # The script already committed its transaction but this test runs
    # the LaunchpadFunctionalLayer which, in turn, uses the REPEATABLE READ
    # isolation level, so we need to forcibly begin another transaction here.
    >>> import transaction; transaction.abort()

    # Flush the caches because our objects were changed in another
    # transaction.
    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> flush_database_caches()

    >>> matsubara = getUtility(IPersonSet).getByName('matsubara')
    >>> matsubara.is_team
    True

We need to force a DB reset because the changes are done from an external
script and the test system is not able to detect the database changes.

    >>> from lp.testing.layers import DatabaseLayer
    >>> DatabaseLayer.force_dirty_database()
