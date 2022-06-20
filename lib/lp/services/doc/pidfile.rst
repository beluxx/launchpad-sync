The `pidfile` Module
====================

The pidfile module allows multiple instances on the same machine to create
pidfiles for the same service names, by using configuration values to
differentiate between instances.  It consists of the following functions:

 * `pidfile_path`
 * `make_pidfile`
 * `get_pid`
 * `remove_pidfile`


`pidfile_path`
--------------

`pidfile_path` is the key to all four of them. Usually, you simply pass it the
name of a service. It then gets the configured name for the current instance
from `lp.services.config.config`, and returns a pidfile path that combines the
instance name with the service name.

    >>> from lp.services.pidfile import (
    ...     pidfile_path, make_pidfile, remove_pidfile, get_pid)
    >>> from lp.services.config import config

    >>> pidfile_path('nuts') == '/var/tmp/%s-nuts.pid' % config.instance_name
    True

You can pass in your own config instance to use.

    >>> class MyConfig:
    ...     class canonical:
    ...         pid_dir = '/var/tmp'
    ...     instance_name = 'blah'
    >>> print(pidfile_path('beans', MyConfig))
    /var/tmp/blah-beans.pid

This basic mechanism supports the other three functions.


`make_pidfile`
--------------

The `make_pidfile` function writes the current process id to a PID file.  For
cleanup, it also includes handlers for Python's `atexit`, signal.SIGINT or
signal.SIGTERM that remove the pidfiles.

Note that, if you install your own handlers for the two signals, you will want
to call `remove_pidfile` inside them.

As a simple demonstration, this subprocess creates a pidfile and checks that
the correct PID is stored in it.

    >>> import sys, subprocess, os, signal

    >>> cmd = '''
    ... import os.path, sys
    ... from lp.services.pidfile import make_pidfile, pidfile_path
    ... make_pidfile('nuts')
    ... sys.exit(
    ...     int(open(pidfile_path('nuts')).read().strip() == str(os.getpid()))
    ...     )
    ... '''
    >>> cmd = '%s -c "%s"' % (sys.executable, cmd)
    >>> subprocess.call(cmd, shell=True)
    1

Moreover, the pidfile has been removed.

    >>> os.path.exists(pidfile_path('nuts'))
    False

The pidfile must also be removed if the process is exited with SIGINT (Ctrl-C)
or SIGTERM, too. We'll demonstrate this with a couple of functions, because
we'll need them again later.

    >>> import errno
    >>> import time
    >>> subprocess_code = '''
    ... import time
    ... from lp.services.pidfile import make_pidfile
    ... make_pidfile('nuts')
    ... try:
    ...     time.sleep(30)
    ... except KeyboardInterrupt:
    ...     pass'''
    >>> def start_process():
    ...     real_pid = subprocess.Popen(
    ...         [sys.executable, '-c', subprocess_code]).pid
    ...     for i in range(50):
    ...         if os.path.exists(pidfile_path('nuts')):
    ...             if real_pid == int(open(pidfile_path('nuts')).read()):
    ...                 return real_pid
    ...         time.sleep(0.1)
    ...     else:
    ...         print('Error: pid file was not created')
    ...
    >>> def stop(pid, sig):
    ...     os.kill(pid, sig)
    ...     os.waitpid(pid, 0)
    ...     if not os.path.exists(pidfile_path('nuts')):
    ...         print('Stopped successfully')
    ...     else:
    ...         try:
    ...             # Is it still here at all?
    ...             os.kill(pid, 0)
    ...         except OSError as e:
    ...             if e.errno == errno.ESRCH:
    ...                 print('Error: pid file was not removed')
    ...             else:
    ...                 raise
    ...         else:
    ...             print('Error: process did not exit')
    ...

Here's our example.  We start, and then stop with SIGINT.

    >>> pid = start_process()
    >>> stop(pid, signal.SIGINT)
    Stopped successfully

We can do the same for SIGTERM.

    >>> pid = start_process()
    >>> stop(pid, signal.SIGTERM)
    Stopped successfully

It's also worth noting that trying to claim a pid that already has a file does
fail as it should. Here, we also show that the signal handlers are not
modified. (We do not check the `atexit` handlers because the module does not
provide a documented interface for doing so.)

    >>> current_SIGINT_handler = signal.getsignal(signal.SIGINT)
    >>> current_SIGTERM_handler = signal.getsignal(signal.SIGTERM)
    >>> pid = start_process()
    >>> make_pidfile('nuts')
    Traceback (most recent call last):
    ...
    RuntimeError: PID file /var/tmp/...nuts.pid already exists.
    Already running?

    >>> current_SIGINT_handler is signal.getsignal(signal.SIGINT)
    True
    >>> current_SIGTERM_handler is signal.getsignal(signal.SIGTERM)
    True
    >>> stop(pid, signal.SIGTERM)
    Stopped successfully

make_pidfile also handles stale PID files, where the owning process
terminated without removing the file, by removing the old file and
continuing as normal.

    >>> stale_pid = start_process()
    >>> make_pidfile('nuts')
    Traceback (most recent call last):
    ...
    RuntimeError: PID file /var/tmp/...nuts.pid already exists.
    Already running?
    >>> stop(stale_pid, signal.SIGKILL)
    Error: pid file was not removed
    >>> new_pid = start_process()
    >>> new_pid == stale_pid
    False
    >>> new_pid == get_pid('nuts')
    True
    >>> stop(new_pid, signal.SIGTERM)
    Stopped successfully
    >>> print(get_pid('nuts'))
    None


`get_pid`
---------

The `get_pid` function returns the PID for the given service as an integer, or
None.  It may raise a ValueError if the PID file is corrupt.

This method should only be needed by service or monitoring scripts. Currently
no checking is done to ensure that the process is actually running, is
healthy, or died horribly a while ago and its PID is being used by something
else.  What we have is probably good enough.

    >>> get_pid('nuts') is None
    True
    >>> pid = start_process()
    >>> get_pid('nuts') == pid
    True
    >>> stop(pid, signal.SIGINT)
    Stopped successfully
    >>> get_pid('nuts') is None
    True

You can also pass in your own config instance.

    >>> class MyConfig:
    ...     class canonical:
    ...         pid_dir = '/var/tmp'
    ...     instance_name = 'blah'
    >>> path = pidfile_path('beans', MyConfig)
    >>> print(path)
    /var/tmp/blah-beans.pid
    >>> file = open(path, 'w')
    >>> try:
    ...     print(72, file=file)
    ... finally:
    ...     file.close()
    >>> get_pid('beans', MyConfig)
    72
    >>> os.remove(path)


`remove_pidfile`
----------------

The `remove_pidfile` function removes the PID file. It should only be needed
if you are overriding the default SIGTERM signal handler.

    >>> path = pidfile_path('legumes')
    >>> file = open(path, 'w')
    >>> try:
    ...     print(os.getpid(), file=file)
    ... finally:
    ...     file.close()
    >>> remove_pidfile('legumes')
    >>> os.path.exists(path)
    False

If the file does not exist, the function silently ignores the request.

    >>> remove_pidfile('legumes')

You can also pass in your own config instance, in which case the pid does not
need to match the current process's pid.

    >>> class MyConfig:
    ...     class canonical:
    ...         pid_dir = '/var/tmp'
    ...     instance_name = 'blah'
    >>> path = pidfile_path('pits', MyConfig)

    >>> file = open(path, 'w')
    >>> try:
    ...     print(os.getpid() + 1, file=file)
    ... finally:
    ...     file.close()
    >>> remove_pidfile('pits', MyConfig)
    >>> os.path.exists(path)
    False
