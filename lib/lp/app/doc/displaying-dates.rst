Date Display
============

We aim for "friendly" display of dates. That means we prefer to express the
date "relative to the present" when it is close to now. Instead of saying
"2007-12-15 06:15 EST" we say "3 minutes ago" or "in 18 seconds".

There are two TALES formatters:

  o fmt:approximatedate does the hard work of turning a timestamp into an
    relative time description. It should be used for tabular data. For
    example:

        Product           Registered               Registrant
        =======           ==========               ==========
        foobar            *3 minutes ago*          James Wilson
        bzrness           *2005-11-07*             Richard Downes

  o fmt:displaydate is similar but is better in paragraphs or sentences. So,
    for example: "FooBar was registered *on 2005-11-06* and last updated
    *4 minutes ago*."

The difference between them is TINY: fmt:displaydate prepends "on " to the
result of fmt:approximatedate IF the time delta is greater than 1 day, and
hence if the display will be the date.

First, let's bring in some dependencies:

    >>> from datetime import datetime, timedelta
    >>> from lp.testing import test_tales
    >>> import pytz
    >>> UTC = pytz.timezone('UTC')

fmt:approximatedate and fmt:displaydate display the difference between
the formatted timestamp and the present.  This is a really bad idea
for tests, so we register an alternate formatter that use the same
formatting code, but always display the difference from a known
timestamp.

    >>> fixed_time_utc = datetime(2005, 12, 25, 12, 0, 0, tzinfo=UTC)
    >>> fixed_time = datetime(2005, 12, 25, 12, 0, 0)
    >>> from lp.app.browser.tales import DateTimeFormatterAPI
    >>> class TestDateTimeFormatterAPI(DateTimeFormatterAPI):
    ...     def _now(self):
    ...         if self._datetime.tzinfo:
    ...             return fixed_time_utc
    ...         else:
    ...             return fixed_time
    >>> from zope.component import provideAdapter
    >>> from zope.traversing.interfaces import IPathAdapter
    >>> provideAdapter(
    ...     TestDateTimeFormatterAPI, (datetime,), IPathAdapter, 'testfmt')

A time that is ten seconds or less will be displayed as an approximate:

    >>> t = fixed_time + timedelta(0, 5, 0)
    >>> test_tales('t/testfmt:approximatedate', t=t)
    'in a moment'
    >>> t = fixed_time + timedelta(0, 9, 0)
    >>> test_tales('t/testfmt:approximatedate', t=t)
    'in a moment'
    >>> print(test_tales('t/testfmt:approximatedate', t=t) ==
    ...       test_tales('t/testfmt:displaydate', t=t))
    True
    >>> t = fixed_time_utc - timedelta(0, 10, 0)
    >>> test_tales('t/testfmt:approximatedate', t=t)
    'a moment ago'
    >>> print(test_tales('t/testfmt:approximatedate', t=t) ==
    ...       test_tales('t/testfmt:displaydate', t=t))
    True

A time that is very close to the present will be displayed in seconds:

    >>> t = fixed_time + timedelta(0, 11, 0)
    >>> test_tales('t/testfmt:approximatedate', t=t)
    'in 11 seconds'
    >>> print(test_tales('t/testfmt:approximatedate', t=t) ==
    ...       test_tales('t/testfmt:displaydate', t=t))
    True
    >>> t = fixed_time_utc - timedelta(0, 25, 0)
    >>> test_tales('t/testfmt:approximatedate', t=t)
    '25 seconds ago'
    >>> print(test_tales('t/testfmt:approximatedate', t=t) ==
    ...       test_tales('t/testfmt:displaydate', t=t))
    True

Further out we expect minutes.  Note that for singular units (e.g. "1
minute"), we present the singular unit:

    >>> t = fixed_time_utc + timedelta(0, 185, 0)
    >>> test_tales('t/testfmt:approximatedate', t=t)
    'in 3 minutes'
    >>> print(test_tales('t/testfmt:approximatedate', t=t) ==
    ...       test_tales('t/testfmt:displaydate', t=t))
    True
    >>> t = fixed_time_utc - timedelta(0, 75, 0)
    >>> test_tales('t/testfmt:approximatedate', t=t)
    '1 minute ago'
    >>> print(test_tales('t/testfmt:approximatedate', t=t) ==
    ...       test_tales('t/testfmt:displaydate', t=t))
    True

Further out we expect hours:

    >>> t = fixed_time_utc + timedelta(0, 3635, 0)
    >>> test_tales('t/testfmt:approximatedate', t=t)
    'in 1 hour'
    >>> print(test_tales('t/testfmt:approximatedate', t=t) ==
    ...       test_tales('t/testfmt:displaydate', t=t))
    True
    >>> t = fixed_time_utc - timedelta(0, 3635, 0)
    >>> test_tales('t/testfmt:approximatedate', t=t)
    '1 hour ago'
    >>> print(test_tales('t/testfmt:approximatedate', t=t) ==
    ...       test_tales('t/testfmt:displaydate', t=t))
    True

And if the approximate date is more than a day away, we expect the date. We
also expect the fmt:displaydate to change form, and become "on yyyy-mm-dd".

    >>> t = datetime(2004, 1, 13, 15, 35)
    >>> test_tales('t/testfmt:approximatedate', t=t)
    '2004-01-13'
    >>> print(test_tales('t/testfmt:approximatedate', t=t) ==
    ...       test_tales('t/testfmt:displaydate', t=t))
    False
    >>> test_tales('t/testfmt:displaydate', t=t)
    'on 2004-01-13'
    >>> t = datetime(2015, 1, 13, 15, 35)
    >>> test_tales('t/testfmt:approximatedate', t=t)
    '2015-01-13'
    >>> print(test_tales('t/testfmt:approximatedate', t=t) ==
    ...       test_tales('t/testfmt:displaydate', t=t))
    False
    >>> test_tales('t/testfmt:displaydate', t=t)
    'on 2015-01-13'

We have two more related TALES formatters, fmt:approximatedatetitle and
fmt:displaydatetitle.  These act similarly to their siblings without
"title", but they wrap the time description in an HTML element with "title"
and "datetime" attributes in order that browsers show the timestamp as hover
text.

    >>> print(test_tales('t/testfmt:approximatedatetitle', t=t))
    <time title="2015-01-13 15:35:00"
          datetime="2015-01-13T15:35:00">2015-01-13</time>
    >>> print(test_tales('t/testfmt:displaydatetitle', t=t))
    <time title="2015-01-13 15:35:00"
          datetime="2015-01-13T15:35:00">on 2015-01-13</time>
