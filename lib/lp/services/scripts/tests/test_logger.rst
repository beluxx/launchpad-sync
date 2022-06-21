Our scripts all use logger_options for common command line verbosity
settings. These command line options change what log levels are output
by our logging handler.

    >>> def test(*args, **kw):
    ...     import os
    ...     import sys
    ...     import subprocess
    ...     from lp.services.config import config
    ...     test_script_path = os.path.join(
    ...         config.root, 'lib', 'lp', 'services',
    ...         'scripts', 'tests', 'loglevels.py')
    ...     cmd = [sys.executable, test_script_path] + list(args)
    ...     proc = subprocess.Popen(
    ...         cmd, stdin=subprocess.PIPE,
    ...         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ...         universal_newlines=True, **kw)
    ...     out, err = proc.communicate()
    ...     assert out == "", "Output to stdout"
    ...     print(err)


The default is to output INFO messages and above.

When run from the test runner, there are no timestamps.

    >>> test()
    ERROR   This is an error
    WARNING This is a warning
    INFO    This is info

When run in other contexts, timestamps are displayed. They
take up a lot of screen space, but we find them critical when
diagnosing problems as we can tell when a script was blocked or
taking too long, and can reference other timestamped log files
such as Apache, Librarian or PostgreSQL logs.

    >>> test(env={'LPCONFIG': 'development'})
    1985-12-21 13:45:55 ERROR   This is an error
    1985-12-21 13:45:55 WARNING This is a warning
    1985-12-21 13:45:55 INFO    This is info

The -q or --quiet argument reduces verbosity.

    >>> test("--quiet")
    ERROR   This is an error
    WARNING This is a warning

    >>> test("--quiet", "-q")
    ERROR   This is an error


The -v argument increases verbosity.

    >>> test("-v")
    ERROR   This is an error
    WARNING This is a warning
    INFO    This is info
    DEBUG   This is debug


More -v arguments increase verbosity more.

    >>> test("-vv", "--verbose", "--verbose")
    ERROR   This is an error
    WARNING This is a warning
    INFO    This is info
    DEBUG   This is debug
    DEBUG2  This is debug2
    DEBUG3  This is debug3
    DEBUG4  This is debug4


Combining -q and -v arguments is handled as you would expect.

    >>> args = ["-q"] * 5 + ["-v"] * 10 + ["--quiet"] * 3 + ["-v"]
    >>> test(*args)
    ERROR   This is an error
    WARNING This is a warning
    INFO    This is info
    DEBUG   This is debug
    DEBUG2  This is debug2
    DEBUG3  This is debug3


We have 10 debug levels. DEBUG2 to DEBUG9 are custom, defined in
lp.services.log.loglevels. All available loglevels are exported from
this module, including the stadard Python ones. You can see that
FATAL is an alias for CRITICAL, and DEBUG1 is an alias for DEBUG.

    >>> from lp.services.log import loglevels
    >>> levels = [
    ...     loglevels.FATAL, loglevels.CRITICAL, loglevels.ERROR,
    ...     loglevels.WARNING, loglevels.INFO, loglevels.DEBUG,
    ...     loglevels.DEBUG1, loglevels.DEBUG2, loglevels.DEBUG3,
    ...     loglevels.DEBUG4, loglevels.DEBUG5, loglevels.DEBUG6,
    ...     loglevels.DEBUG7, loglevels.DEBUG8, loglevels.DEBUG9]
    >>> import logging
    >>> for level in levels:
    ...     print("%2d %s" % (level, logging.getLevelName(level)))
    50 CRITICAL
    50 CRITICAL
    40 ERROR
    30 WARNING
    20 INFO
    10 DEBUG
    10 DEBUG
     9 DEBUG2
     8 DEBUG3
     7 DEBUG4
     6 DEBUG5
     5 DEBUG6
     4 DEBUG7
     3 DEBUG8
     2 DEBUG9

    >>> test(*["-v"] * 20)
    ERROR   This is an error
    WARNING This is a warning
    INFO    This is info
    DEBUG   This is debug
    DEBUG2  This is debug2
    DEBUG3  This is debug3
    DEBUG4  This is debug4
    DEBUG5  This is debug5
    DEBUG6  This is debug6
    DEBUG7  This is debug7
    DEBUG8  This is debug8
    DEBUG9  This is debug9

