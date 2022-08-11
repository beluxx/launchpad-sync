Sample data setup
=================

# XXX: StevenK 2010-07-13 bug=617164: Calling utility scripts is bad

In order to run Soyuz locally on a development system, the sample data
must be cleaned up and customized a bit.  This is done by a the script
utilities/soyuz-sampledata-setup.py.

We only need this script for the playground sample data, so there's
little point in inspecting what it does to the test database in detail.

    >>> from lp.testing.script import run_script

    >>> return_code, output, error = run_script(
    ...     'utilities/soyuz-sampledata-setup.py')

    >>> print(return_code)
    0

    >>> print(error)
    INFO ...
    INFO Done.

    >>> from lp.testing.layers import DatabaseLayer
    >>> DatabaseLayer.force_dirty_database()
