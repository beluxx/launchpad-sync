Presenting Lengths of Time
==========================

First, let's bring in some dependencies:

    >>> from lp.testing import test_tales
    >>> from datetime import timedelta

Exact Duration
--------------

To display the precise length of a duraction, use fmt:exactduration:

    >>> td = timedelta(days=1, hours=2, minutes=3, seconds=4.567)
    >>> test_tales("td/fmt:exactduration", td=td)
    '1 day, 2 hours, 3 minutes, 4.6 seconds'
    >>> td = timedelta(days=1, minutes=3, seconds=4.567)
    >>> test_tales("td/fmt:exactduration", td=td)
    '1 day, 0 hours, 3 minutes, 4.6 seconds'
    >>> td = timedelta(minutes=3, seconds=4.567)
    >>> test_tales("td/fmt:exactduration", td=td)
    '3 minutes, 4.6 seconds'

    >>> td = timedelta(days=1, hours=1, minutes=1, seconds=1)
    >>> test_tales("td/fmt:exactduration", td=td)
    '1 day, 1 hour, 1 minute, 1.0 seconds'
    >>> td = timedelta(days=2, hours=2, minutes=2, seconds=2)
    >>> test_tales("td/fmt:exactduration", td=td)
    '2 days, 2 hours, 2 minutes, 2.0 seconds'

Approximate Duration
--------------------

To get more friendly-to-display duration output, use
fmt:approximateduration:

    >>> td = timedelta(seconds=0)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '1 second'

    >>> td = timedelta(seconds=-1)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '1 second'

    >>> td = timedelta(seconds=1.1)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '1 second'
    >>> td = timedelta(seconds=2.4)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '2 seconds'
    >>> td = timedelta(seconds=3.0)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '3 seconds'
    >>> td = timedelta(seconds=3.5)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '4 seconds'

    >>> td = timedelta(seconds=4.5)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '5 seconds'
    >>> td = timedelta(seconds=6)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '5 seconds'

    >>> td = timedelta(seconds=8)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '10 seconds'
    >>> td = timedelta(seconds=12.4)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '10 seconds'

    >>> td = timedelta(seconds=12.5)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '15 seconds'
    >>> td = timedelta(seconds=16.9)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '15 seconds'

    >>> td = timedelta(seconds=17.5)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '20 seconds'
    >>> td = timedelta(seconds=22)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '20 seconds'

    >>> td = timedelta(seconds=22.5)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '25 seconds'
    >>> td = timedelta(seconds=27.4)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '25 seconds'

    >>> td = timedelta(seconds=28)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '30 seconds'
    >>> td = timedelta(seconds=31.2)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '30 seconds'

    >>> td = timedelta(seconds=35)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '40 seconds'
    >>> td = timedelta(seconds=44.999)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '40 seconds'

    >>> td = timedelta(seconds=45)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '50 seconds'
    >>> td = timedelta(seconds=54.11)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '50 seconds'

    >>> td = timedelta(seconds=55)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '1 minute'
    >>> td = timedelta(seconds=88.123)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '1 minute'

    >>> td = timedelta(seconds=90)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '2 minutes'
    >>> td = timedelta(seconds=149.9181)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '2 minutes'

    >>> td = timedelta(seconds=150)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '3 minutes'
    >>> td = timedelta(seconds=199)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '3 minutes'

    >>> td = timedelta(seconds=330)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '6 minutes'
    >>> td = timedelta(seconds=375.1)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '6 minutes'

    >>> td = timedelta(seconds=645)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '11 minutes'
    >>> td = timedelta(seconds=689.9999)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '11 minutes'

    >>> td = timedelta(seconds=3500)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '58 minutes'

    >>> td = timedelta(seconds=3569)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '59 minutes'

    >>> td = timedelta(seconds=3570)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '1 hour'

    >>> td = timedelta(seconds=3899.99999)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '1 hour'

    >>> td = timedelta(seconds=5100.181)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '1 hour 30 minutes'

    >>> td = timedelta(seconds=5655.119)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '1 hour 30 minutes'

    >>> td = timedelta(seconds=35200.1234)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '9 hours 50 minutes'

    >>> td = timedelta(seconds=35850.2828)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '10 hours'

    >>> td = timedelta(seconds=38000)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '11 hours'

    >>> td = timedelta(seconds=170000)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '47 hours'

    >>> td = timedelta(seconds=171000)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '2 days'

    >>> td = timedelta(seconds=900000)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '10 days'

    >>> td = timedelta(seconds=1160000)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '13 days'

    >>> td = timedelta(seconds=1500000)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '2 weeks'

    >>> td = timedelta(seconds=6000000)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '10 weeks'

    >>> td = timedelta(seconds=6350400)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '11 weeks'

    >>> td = timedelta(seconds=7560000)
    >>> test_tales("td/fmt:approximateduration", td=td)
    '13 weeks'

    >>> td = timedelta(days=(365 * 99))
    >>> test_tales("td/fmt:approximateduration", td=td)
    '5162 weeks'
