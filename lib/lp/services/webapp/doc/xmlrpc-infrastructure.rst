XMLRPC infrastructure
=====================

When you write XMLRPC view classes, you should extend the base class
LaunchpadXMLRPCView.

    >>> from lp.services.webapp import LaunchpadXMLRPCView
    >>> viewobj = LaunchpadXMLRPCView('somecontext', 'somerequest')

You get access to the context and the request, as you would expect.

    >>> print(viewobj.context)
    somecontext
    >>> print(viewobj.request)
    somerequest

Like a LaunchpadView, you can get 'self.user', which is the currently
logged-in user, or None when there is no user logged in.

    >>> viewobj.user is None
    True

