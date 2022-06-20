Request time out
================

Launchpad request shouldn't take more than a fix number of seconds to
complete. The database adapter issues RequestExpired errors when the
database takes too long to respond (see
lib/lp/services/webapp/doc/test_adapter.rst)

The app server is also configured with a default timeout function (for
functions wrapped with the @with_timeout decorator) that computes the
time remaining before the request should time out.

    >>> from lp.services.timeout import get_default_timeout_function
    >>> from lp.services.webapp.adapter import (
    ...     set_launchpad_default_timeout)
    >>> old_func = get_default_timeout_function()

    >>> from zope.processlifetime import ProcessStarting

    # We don't use notify here, because we don't want to invoke the
    # other subscribers.
    >>> set_launchpad_default_timeout(ProcessStarting())

    >>> get_default_timeout_function()
    <function get_request_remaining_seconds...>

The timeout to use is the number of seconds remaining before
db_statement_timeout is expired.

    >>> from lp.services.config import config
    >>> from textwrap import dedent
    >>> config.push('timeout', dedent('''\
    ... [database]
    ... db_statement_timeout = 10000'''))

    >>> timeout_func = get_default_timeout_function()

(Set the request to have started a few seconds in the past.)

    >>> import time
    >>> from lp.services.webapp import adapter
    >>> adapter.set_request_started(time.time()-5)

So the computed timeout should be more or less 5 seconds (10-5).

    >>> timeout_func() <= 5
    True

If the timeout is already expired, a RequestExpired error is raised:

    >>> from lp.services.webapp.adapter import clear_request_started
    >>> clear_request_started()
    >>> adapter.set_request_started(time.time()-12)
    >>> timeout_func()
    Traceback (most recent call last):
      ...
    lp.services.webapp.adapter.RequestExpired: request expired.

Same thing if a function decorated using @with_timeout is called.

    >>> from lp.services.timeout import with_timeout
    >>> @with_timeout()
    ... def wait_a_little():
    ...     time.sleep(1)
    >>> wait_a_little()
    Traceback (most recent call last):
      ...
    lp.services.webapp.adapter.RequestExpired: request expired.

@with_timeout allows the actual timeout value to be specified, either as a
numeric argument or a function argument returning the required value. Here we
specify a timeout of 2 seconds to allow the called function to complete
successfully.

    >>> @with_timeout(timeout=2)
    ... def wait_a_little_more():
    ...     time.sleep(1)
    >>> wait_a_little_more()

    >>> def _timeout():
    ...     return 2
    >>> @with_timeout(timeout=_timeout)
    ... def wait_a_little_again():
    ...     time.sleep(1)
    >>> wait_a_little_again()

    >>> class Foo:
    ...     @property
    ...     def _timeout(self):
    ...         return 2
    ...     @with_timeout(timeout=lambda self: self._timeout)
    ...     def wait_a_little(self):
    ...         time.sleep(1)
    >>> Foo().wait_a_little()

If there is no db_statement_timeout, then the default timeout is None
and a TimeoutError is never raised.

    >>> config.push('no-timeout', dedent('''\
    ... [database]
    ... db_statement_timeout = None'''))

    >>> print(timeout_func())
    None

    >>> wait_a_little()

Overriding hard timeouts via FeatureFlags
=========================================

It's possible to use FeatureFlags to control the hard timeout. This is used to
deal with pages that suddenly start performing badly, which are being
optimised but should not hold back the overall timeout decrease, or for which
there are only a few specific users and we are willing to have them run for
longer periods. For more information on feature flags see
lp.services.features.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.services.features.model import FeatureFlag, getFeatureStore
    >>> from lp.services.features import install_feature_controller
    >>> from lp.services.features.flags import FeatureController
    >>> from lp.services.features.webapp import ScopesFromRequest

Install the feature flag to increase the timeout value.

    >>> config.push('flagstimeout', dedent('''\
    ... [database]
    ... db_statement_timeout = 10000'''))

    >>> empty_request = LaunchpadTestRequest()
    >>> install_feature_controller(FeatureController(
    ...     ScopesFromRequest(empty_request).lookup))
    >>> ignore = getFeatureStore().add(FeatureFlag(
    ...     scope=u'default', flag=u'hard_timeout', value=u'20000',
    ...     priority=1))

Now the request can take 20 seconds to complete.

    >>> clear_request_started()
    >>> adapter.set_request_started(time.time())
    >>> adapter.set_permit_timeout_from_features(True)
    >>> abs(adapter._get_request_timeout()-20000) < 0.001
    True

Clean up
========

    >>> ignored = config.pop('timeout')

    >>> from lp.services.timeout import set_default_timeout_function
    >>> set_default_timeout_function(old_func)

    >>> clear_request_started()

