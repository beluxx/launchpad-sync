NewLineToSpaces Widget
======================

This custom widget is used to replace new line characters to spaces.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.bugs.browser.widgets.bugtask import NewLineToSpacesWidget
    >>> from lp.bugs.interfaces.bugtasksearch import IBugTaskSearch

We pass a string with some new line characters to the widget

    >>> field = IBugTaskSearch['searchtext']
    >>> request = LaunchpadTestRequest(
    ...     form={'field.searchtext':'some text\rwith\nnew\r\nlines removed'})
    >>> widget = NewLineToSpacesWidget(field, request)

And check that the new lines were replaced by spaces.

    >>> print(widget.getInputValue())
    some text with new lines removed

Since the widget inherits from StrippedTextWidget, trailing whitespaces are
also removed.

    >>> request = LaunchpadTestRequest(
    ...     form={'field.searchtext':
    ...     'text\rwith\nnew\r\nlines and trailing whitespace removed  '})
    >>> widget = NewLineToSpacesWidget(field, request)
    >>> print(widget.getInputValue())
    text with new lines and trailing whitespace removed
