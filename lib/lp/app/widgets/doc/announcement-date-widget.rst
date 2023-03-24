AnnouncementDateWidget
======================

This widget combines radio buttons and a DateTimeWidget. It allows you to
choose to publish an announcement immediately, at a predetermined date in the
future, or to manually publish it later.

    >>> from zope.schema import Field
    >>> from lp.testing.pages import extract_text
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.app.widgets.announcementdate import AnnouncementDateWidget
    >>> field = Field(__name__="foo", title="Foo")
    >>> widget = AnnouncementDateWidget(field, LaunchpadTestRequest())
    >>> print(extract_text(widget()))
    Publish this announcement:
    Immediately
    At some time in the future when I come back to authorize it
    At this specific date and time:
    in time zone: UTC

When you choose to publish at a specific date in the future, the widget will
return the date you specified.

    >>> action_widget = widget.action_widget
    >>> action_widget.request.form[action_widget.name] = "specific"
    >>> date_widget = widget.announcement_date_widget
    >>> date_widget.request.form[date_widget.name] = "2005-07-23"
    >>> print(widget.getInputValue())
    2005-07-23 00:00:00+00:00

When you choose to publish immediately, the widget will return the current
date and time.

    >>> from datetime import datetime, timedelta, timezone
    >>> action_widget.request.form[action_widget.name] = "immediately"
    >>> date_widget.request.form[date_widget.name] = ""
    >>> now = datetime.now(timezone.utc)
    >>> before = now - timedelta(1)  # 1 day
    >>> after = now + timedelta(1)  # 1 day
    >>> immediate_date = widget.getInputValue()
    >>> print(repr(immediate_date))
    datetime.datetime(...)
    >>> before < immediate_date < after
    True

When you choose to publish manually at some time in the future, the widget
won't return a date.

    >>> action_widget.request.form[action_widget.name] = "sometime"
    >>> date_widget.request.form[date_widget.name] = "2005-07-23"
    >>> print(widget.getInputValue())
    None

If you choose to publish immediately, the date field must be empty.

    >>> action_widget.request.form[action_widget.name] = "immediately"
    >>> date_widget.request.form[date_widget.name] = "2005-07-23"
    >>> print(widget.getInputValue())
    Traceback (most recent call last):
    ...
    zope.formlib.interfaces.WidgetInputError:
    ('field.foo', 'Foo',
     LaunchpadValidationError('Please do not provide a date if you want to
                               publish immediately.'))

If you choose to publish at a specific date in the future, the date field
must be filled.

    >>> action_widget.request.form[action_widget.name] = "specific"
    >>> date_widget.request.form[date_widget.name] = ""
    >>> print(widget.getInputValue())
    Traceback (most recent call last):
    ...
    zope.formlib.interfaces.WidgetInputError:
    ('field.foo', 'Foo',
     LaunchpadValidationError('Please provide a publication date.'))
