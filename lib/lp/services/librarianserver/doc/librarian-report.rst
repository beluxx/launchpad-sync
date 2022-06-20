We have a report that we run as necessary to see what is using the Librarian
storage.

    >>> from lp.testing.script import run_script
    >>> script = 'scripts/librarian-report.py'

    >>> rv, out, err = run_script(script)
    >>> print(rv)
    0
    >>> print(err)
    >>> print('\n' + out)
    <BLANKLINE>
    ...
    45 kB         languagepack in 4 files
    ...


We can filter on date to produce deltas.

    >>> rv, out, err = run_script(
    ...     script, ['--from=2005/01/01', '--until=2005/12/31'])
    >>> print(rv)
    0
    >>> print(err)
    >>> print('\n' + out)
    <BLANKLINE>
    ...
    0 bytes      languagepack in 0 files
    ...
