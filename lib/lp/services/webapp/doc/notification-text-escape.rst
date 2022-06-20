Notification Text Escaping
==========================

There are a number of user actions that may generate on-screen
notifications, such as moving a bug or deleting a branch.  Some of
these notifications display potentially unsafe text that is obtained
from the user.  In order to prevent a cross-site-scripting attack,
HTML characters in notifications must be escaped.  However, there are
special cases where notifications from known safe sources must be
allowed to pass HTML through.  This document exercises these
mechanisms.

    >>> from lp.services.webapp.notifications import (
    ...	     NotificationResponse, NotificationRequest)
    >>> def new_response():
    ...     response = NotificationResponse()
    ...     request  = NotificationRequest()
    ...     request.response = response
    ...     response._request = request
    ...	    return response
    >>>

Plain text passed into the object's addNotification() method is
unchanged:

    >>> response = new_response()
    >>> response.addNotification('clean')
    >>> for notification in response.notifications:
    ...   print(notification.message)
    clean

But text containing markup is CGI-escaped:

    >>> response = new_response()
    >>> response.addNotification(u'<br/>dirty')
    >>> for notification in response.notifications:
    ...     print(notification.message)
    &lt;br/&gt;dirty


If the object passed to addNotification() publishes the
IStructuredString interface, then a string will be returned with the
appropriate sections escaped and unescaped.

    >>> from lp.services.webapp.interfaces import IStructuredString
    >>> from lp.services.webapp.escaping import structured
    >>> msg = u'<b>%(escaped)s</b>'
    >>> structured_text = structured(msg, escaped=u'<br/>foo')
    >>> IStructuredString.providedBy(structured_text)
    True
    >>> print(structured_text.escapedtext)
    <b>&lt;br/&gt;foo</b>

    >>> response = new_response()
    >>> response.addNotification(structured_text)
    >>> for notification in response.notifications:
    ...     print(notification.message)
    <b>&lt;br/&gt;foo</b>

Passing an object to addNotification() that is an instance of
zope.i18n.Message will be escaped in the same
manner as raw text.

    >>> import zope.i18n
    >>> msgtxt   = zope.i18n.Message(u'<br/>foo')
    >>> response = new_response()
    >>> response.addNotification(msgtxt)
    >>> for notification in response.notifications:
    ...     print(notification.message)
    &lt;br/&gt;foo

To pass internationalized text that contains markup, one may call
structured() directly with an internationalized object.  structured()
performs the translation and substitution, and the resulting object
may then be passed to addNotification().

    >>> from lp import _
    >>> msgid   = _(u'<good/>%(evil)s')
    >>> escapee = '<evil/>'
    >>> text    = structured(msgid, evil=escapee)
    >>> print(text.escapedtext)
    <good/>&lt;evil/&gt;

    >>> response = new_response()
    >>> response.addNotification(text)
    >>> for notification in response.notifications:
    ...     print(notification.message)
    <good/>&lt;evil/&gt;
