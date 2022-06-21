ExternalBugTracker: Python
==========================

This covers the implementation of the ExternalBugTracker class for
Python bugwatches.

The Python bug tracker is a slight modification of the Roundup
bugtracker and the functionality for importing bugs from it is housed
within the Roundup ExternalBugTracker. As such, we only test the ways in
which it differs from standard Roundup status imports. For the tests
common to Roundup and Python instances, see
externalbugtracker-roundup.rst


Status Conversion
-----------------

The basic Python bug statuses map to Launchpad bug statuses.
Roundup.convertRemoteStatus() handles the conversion.

Because Python bugtracker statuses are entirely numeric, we use the
convert_python_status() helper function, which accepts parameters for
status and resolution, to make the test more readable.

    >>> from lp.bugs.externalbugtracker import (
    ...     Roundup)
    >>> from lp.bugs.tests.externalbugtracker import (
    ...     convert_python_status)
    >>> python_bugs = Roundup('http://bugs.python.org')

    >>> python_bugs_example_statuses = [
    ...     ('open', 'None'),
    ...     ('open', 'accepted'),
    ...     ('open', 'duplicate'),
    ...     ('open', 'fixed'),
    ...     ('open', 'invalid'),
    ...     ('open', 'later'),
    ...     ('open', 'out-of-date'),
    ...     ('open', 'postponed'),
    ...     ('open', 'rejected'),
    ...     ('open', 'remind'),
    ...     ('open', 'wontfix'),
    ...     ('open', 'worksforme'),
    ...     ('closed', 'None'),
    ...     ('closed', 'accepted'),
    ...     ('closed', 'fixed'),
    ...     ('closed', 'postponed'),
    ...     ('pending', 'None'),
    ...     ('pending', 'postponed'),
    ...     ]

    >>> for status, resolution in python_bugs_example_statuses:
    ...     status_string = convert_python_status(status, resolution)
    ...     status_converted = python_bugs.convertRemoteStatus(status_string)
    ...     print('(%s, %s) --> %s --> %s' % (
    ...         status, resolution, status_string, status_converted))
    (open, None) --> 1:None --> New
    (open, accepted) --> 1:1 --> Confirmed
    (open, duplicate) --> 1:2 --> Confirmed
    (open, fixed) --> 1:3 --> Fix Committed
    (open, invalid) --> 1:4 --> Invalid
    (open, later) --> 1:5 --> Confirmed
    (open, out-of-date) --> 1:6 --> Invalid
    (open, postponed) --> 1:7 --> Confirmed
    (open, rejected) --> 1:8 --> Won't Fix
    (open, remind) --> 1:9 --> Confirmed
    (open, wontfix) --> 1:10 --> Won't Fix
    (open, worksforme) --> 1:11 --> Invalid
    (closed, None) --> 2:None --> Won't Fix
    (closed, accepted) --> 2:1 --> Fix Committed
    (closed, fixed) --> 2:3 --> Fix Released
    (closed, postponed) --> 2:7 --> Won't Fix
    (pending, None) --> 3:None --> Incomplete
    (pending, postponed) --> 3:7 --> Won't Fix

If the status isn't something that our Python_Bugs ExternalBugTracker can
understand an UnknownRemoteStatusError will be raised.

    >>> python_bugs.convertRemoteStatus('7:13').title
    Traceback (most recent call last):
      ...
    lp.bugs.externalbugtracker.base.UnknownRemoteStatusError: 7:13
