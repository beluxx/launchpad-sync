We have a custom IUserPreferredCharsets which always returns
utf-8 as the preferred charset.

    >>> from zope.publisher.browser import TestRequest
    >>> from lp.services.webapp import Utf8PreferredCharsets
    >>> user_preferred = Utf8PreferredCharsets(TestRequest())

    >>> from zope.i18n.interfaces import IUserPreferredCharsets
    >>> from zope.interface.verify import verifyObject
    >>> verifyObject(IUserPreferredCharsets, user_preferred)
    True

    >>> user_preferred.getPreferredCharsets()
    ['utf-8']

Even if the user specifies that they don't want utf-8:

    >>> no_utf8_request = TestRequest(
    ...     environ={'HTTP_ACCEPT_CHARSET': 'iso8859-1'})
    >>> user_preferred = Utf8PreferredCharsets(no_utf8_request)
    >>> user_preferred.getPreferredCharsets()
    ['utf-8']
