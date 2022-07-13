Launchpad maintenance messages
==============================

A system administrator can write an iso format timestamp to the file
"+maintenancetime.txt" in the launchpad application root directory.

This will cause a message to be displayed as part of the main template
indicating when the system is expected to go down.

First, let's check that the maintenance message is not normally displayed.

    >>> import os
    >>> os.path.exists('+maintenancetime.txt')
    False

    >>> def front_page_content():
    ...     return str(http("GET / HTTP/1.1\n"))

    >>> maintenance_text = 'Launchpad will be going offline for maintenance'
    >>> okay200 = 'HTTP/1.1 200 Ok'
    >>> content = front_page_content()
    >>> okay200 in content
    True
    >>> maintenance_text not in content
    True

Now, we can put a time in that file.  We use os.system to call the 'date'
command, because that's the easiest way to make it work in practice. We
ellipsize the number of minutes in the test output to avoid the risk of
this timebombing.

    >>> os.system(
    ... 'date --iso-8601=minutes -u -d +10mins30secs > +maintenancetime.txt')
    0
    >>> print(front_page_content())
    HTTP/1.1 200 Ok
    ...
      Launchpad will be going offline for maintenance
      in ... minutes.
    ...

When the time is more than 30 minutes away, no message is shown.

    >>> os.system(
    ...     'date --iso-8601=minutes -u -d +40mins > +maintenancetime.txt')
    0
    >>> content = front_page_content()
    >>> okay200 in content
    True
    >>> maintenance_text not in content
    True

When the time is under 30 seconds away, the time is given as "very very soon".

    >>> os.system(
    ...     'date --iso-8601=minutes -u -d +29secs > +maintenancetime.txt')
    0
    >>> content = front_page_content()
    >>> maintenance_text in content
    True
    >>> 'very very soon' in content
    True

When the time is in the past, the time is still given as "very very soon".

    >>> os.system(
    ...     'date --iso-8601=minutes -u -d -10secs > +maintenancetime.txt')
    0
    >>> content = front_page_content()
    >>> maintenance_text in content
    True
    >>> 'very very soon' in content
    True

If the time doesn't make sense, or is empty, then no message is displayed.

    >>> with open('+maintenancetime.txt', 'w') as f:
    ...     _ = f.write('xxxx')
    >>> content = front_page_content()
    >>> okay200 in content
    True
    >>> maintenance_text not in content
    True

    >>> with open('+maintenancetime.txt', 'w') as f:
    ...     _ = f.write('')
    >>> content = front_page_content()
    >>> okay200 in content
    True
    >>> maintenance_text not in content
    True


Remove +maintenancetime.txt to clean up.

    >>> os.remove('+maintenancetime.txt')


Per-page maintenance messages
-----------------------------

Alternatively, a maintenance message can be set in the
app.maintenance_message feature flag, which can be scoped to particular
pages.

    >>> from lp.services.features.testing import FeatureFixture
    >>> maintenance_text = (
    ...     'This page will be <a href="https://example.com/">broken</a> '
    ...     'for a while.')
    >>> with FeatureFixture({'app.maintenance_message': maintenance_text}):
    ...     content = front_page_content()
    >>> maintenance_text in content
    True

    >>> content = front_page_content()
    >>> maintenance_text not in content
    True
