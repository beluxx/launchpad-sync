Web service configuration
=========================

Every web service needs a configuration object that provides
information about policy. Some of the Launchpad web service's
configuration options are controlled by code. This test demonstrates
how that code works.

    >>> from zope.component import provideUtility
    >>> from lazr.restful.interfaces import IWebServiceConfiguration
    >>> from lp.services.webservice.configuration import (
    ...     LaunchpadWebServiceConfiguration,
    ... )
    >>> webservice_config = LaunchpadWebServiceConfiguration()

    >>> provideUtility(webservice_config, IWebServiceConfiguration)


show_tracebacks
---------------

The show_tracebacks variable controls whether the client is shown
tracebacks of errors. The show_tracebacks behaviour itself is tested in
lazr.restful's "webservice-error" test. This test only shows how
changes within Launchpad affect the value of show_tracebacks. The
Launchpad web service shows or hides information about exceptions
based on the site configuration and whether the requesting user is a
developer.

    >>> from lp.services.config import config
    >>> from textwrap import dedent

    >>> from zope.interface import implementer
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> @implementer(ILaunchBag)
    ... class FakeLaunchBag:
    ...     developer = False
    >>> the_launchbag = FakeLaunchBag()
    >>> provideUtility(the_launchbag, ILaunchBag)

Here's how a value for the web service's 'show_tracebacks' variable is
determined from the user's developer status plus Launchpad's
'show_tracebacks' configuration variable:

Launchpad show_tracebacks | User is developer | Web service show_tracebacks
--------------------------+-------------------+----------------------------
False                     | False             | False
False                     | True              | True
True                      | False             | True
True                      | True              | True

When the Launchpad configuration variable 'show_tracebacks' is True,
the web service configuration's 'show_tracebacks' value will always be
True.

    >>> the_launchbag.developer = False
    >>> config.push(
    ...     "traceback_on",
    ...     dedent(
    ...         """
    ...     [canonical]
    ...     show_tracebacks: True"""
    ...     ),
    ... )
    >>> webservice_config.show_tracebacks
    True

    >>> the_launchbag.developer = True
    >>> webservice_config.show_tracebacks
    True

    >>> ignored = config.pop("traceback_on")

When the Launchpad configuration variable 'show_tracebacks' is False,
the web service configuration's 'show_tracebacks' is only True if the
current user is a developer.

    >>> the_launchbag.developer = False
    >>> config.push(
    ...     "traceback_off",
    ...     dedent(
    ...         """
    ...     [canonical]
    ...     show_tracebacks: False"""
    ...     ),
    ... )
    >>> webservice_config.show_tracebacks
    False

    >>> the_launchbag.developer = True
    >>> webservice_config.show_tracebacks
    True

    >>> ignored = config.pop("traceback_off")
