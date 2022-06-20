Validation
==========

LaunchpadValidationError
------------------------

LaunchpadValidationError is the standard exception used for custom
validators upon a validation error. Rendering one is done by getting
an IWidgetInputErrorView:

    >>> from lp.app.validators import LaunchpadValidationError
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from zope.component import getMultiAdapter
    >>> from zope.formlib.interfaces import IWidgetInputErrorView

    >>> error = LaunchpadValidationError('lp validation error')
    >>> request = LaunchpadTestRequest()
    >>> view = getMultiAdapter((error, request),
    ...     IWidgetInputErrorView)

    >>> IWidgetInputErrorView.providedBy(view)
    True
    >>> print(view.snippet())
    lp validation error
