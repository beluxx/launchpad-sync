Tokens TextLine Widget
======================

This custom widget is used to normalise the space between words,
strip punctuation, and strip leading and trailing whitespace.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.app.widgets.textwidgets import TokensTextWidget
    >>> from lp.answers.interfaces.faq import IFAQ

The IFAQ keywords field requires a space separated list of terms. In the
spirit of Postel's Law, the TokensTextWidget permits users to enter
a list of terms as they like, while ensuring that the schema's field is
satisfied.

    >>> field = IFAQ["keywords"]
    >>> request = LaunchpadTestRequest(
    ...     form={"field.keywords": " news feeds   HTTP, RSS; UTF-8. "}
    ... )
    >>> widget = TokensTextWidget(field, request)

The widget removed the extra whitespace and punctuation.

    >>> print(widget.getInputValue())
    news feeds HTTP RSS UTF-8


