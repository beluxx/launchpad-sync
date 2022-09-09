LowerCaseTextWidget
===================

This custom widget is used to convert strings to lower case.

Some fields accept only lower case strings. Instead of displaying an
error message when the user inputs an upper case string, a
LowerCaseTextWidget can be used to automatically convert the input to
lower case:

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.app.widgets.textwidgets import LowerCaseTextWidget
    >>> from lp.bugs.interfaces.bug import IBug
    >>> field = IBug["description"]
    >>> request = LaunchpadTestRequest(form={"field.description": "Foo"})
    >>> widget = LowerCaseTextWidget(field, request)
    >>> print(widget.getInputValue())
    foo

However, strings without lower case characters are left unchanged:

    >>> field = IBug["description"]
    >>> request = LaunchpadTestRequest(form={"field.description": "foo1"})
    >>> widget = LowerCaseTextWidget(field, request)
    >>> print(widget.getInputValue())
    foo1

In addition, the widget also renders itself with a CSS style that causes
characters to be rendered in lower case as they are typed in by the
user:

    >>> widget.cssClass
    'lowerCaseText'

This style is defined by "lib/canonical/launchpad/icing/style.css". Note
that the style only causes text to be rendered in lower case, and does
not convert the underlying string to lower case.
