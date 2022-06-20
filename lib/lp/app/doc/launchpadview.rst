LaunchpadView
=============

This is the base-class we should use for all View classes in Launchpad.

    >>> from lp.services.webapp import LaunchpadView
    >>> from lp.services.webapp.servers import LaunchpadTestRequest

    >>> class MyView(LaunchpadView):
    ...
    ...     def initialize(self):
    ...         print("Initalizing...")
    ...
    ...     def render(self):
    ...         return "rendered content"

    >>> context = object()
    >>> request = LaunchpadTestRequest()

Note that constructing a view does not initialize().

    >>> view = MyView(context, request)

Anonymous logged in, so view.account and view.user are None.

    >>> print(view.account)
    None
    >>> print(view.user)
    None

    >>> result = view()
    Initalizing...

    >>> print(result)
    rendered content

Now, we log in a user and see what happens to the 'user' attribute.  The
existing view should have the same user, 'None', because it was cached.

    >>> login('foo.bar@canonical.com')
    >>> print(view.user)
    None

A new view should have the new user.

    >>> view = MyView(context, request)
    >>> print(view.account)
    <...lp.services.identity.model.account.Account instance ...>
    >>> print(view.user)
    <...lp.registry.model.person.Person instance ...>
    >>> print(view.user.name)
    name16

A view can have `error_message` or `info_message` set for display in
the template (each template is responsible for including the messages,
using a `structure` directive). The supplied value must be None or
an IStructuredString implementation.

    >>> view = MyView(context, request)
    >>> print(view.error_message)
    None
    >>> print(view.info_message)
    None

    >>> view.error_message = 'A simple string.'
    Traceback (most recent call last):
    ...
    ValueError: <... 'str'> is not a valid value for error_message,
    only None and IStructuredString are allowed.
    >>> print(view.error_message)
    None

    >>> view.info_message = 'A simple string.'
    Traceback (most recent call last):
    ...
    ValueError: <... 'str'> is not a valid value for info_message,
    only None and IStructuredString are allowed.
    >>> print(view.info_message)
    None

    >>> from lp.services.webapp.escaping import structured
    >>> view.error_message = structured(
    ...    'A structure is just "%s".', 'smoke & mirrors')
    >>> print(view.error_message.escapedtext)
    A structure is just "smoke &amp; mirrors".
    >>> view.error_message = structured('Information overload.')
    >>> print(view.error_message.escapedtext)
    Information overload.
