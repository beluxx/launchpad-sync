Script `fix_translation_credits.py`
====================================

Marks all existing translation credits as translated.

    >>> from lp.testing.script import run_script
    >>> (returncode, out, err) = run_script(
    ...     'scripts/rosetta/fix_translation_credits.py')
    >>> print(returncode)
    0
    >>> print(err)
    INFO    Creating lockfile:
        /var/lock/launchpad-fix-translation-credits.lock
    INFO    Figuring out POFiles that need fixing: this may take a while...
    INFO    Marking up a total of 3 credits as translated.
    INFO    Processed ...
    INFO    Done.

After altering the database from a separate process, we must tell the
test setup that the database is dirty in spite of appearances.

    >>> from lp.testing.layers import DatabaseLayer
    >>> DatabaseLayer.force_dirty_database()
