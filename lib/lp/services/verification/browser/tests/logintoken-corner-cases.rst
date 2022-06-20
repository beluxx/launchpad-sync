LoginToken Corner Cases
=======================

Once a LoginToken is consumed, it cannot be used again. Since the
LoginToken is used mainly for workflow purposes, we have to guard
against multiple corner cases, for example where the user posts the
form again.


Double Post on the NewAccountView
---------------------------------

Using the +validateemail view on a token that was already consumed should
redirect to the default token view. This would happen if for example the
user tried to re-post the form after validating one of their email addresses.

    >>> from lp.testing import login_person
    >>> from lp.services.verification.browser.logintoken import (
    ...     ValidateEmailView)
    >>> from lp.services.verification.interfaces.authtoken import (
    ...     LoginTokenType)
    >>> from lp.services.verification.interfaces.logintoken import (
    ...     ILoginTokenSet)
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.registry.interfaces.person import IPersonSet

    >>> foo_bar = getUtility(IPersonSet).getByName('name16')
    >>> ignored = login_person(foo_bar)
    >>> token = getUtility(ILoginTokenSet).new(
    ...     requester=foo_bar, requesteremail='foo.bar@canonical.com',
    ...     email='foo@barino.com', tokentype=LoginTokenType.VALIDATEEMAIL)
    >>> token.consume()
    >>> form = {'field.actions.continue': 'Continue'}
    >>> view = ValidateEmailView(
    ...     token, LaunchpadTestRequest(form=form, method='POST'))
    >>> view.initialize()

    >>> response = view.request.response
    >>> response.getStatus()
    302
    >>> response.getHeader('Location')
    'http://launchpad.test/token/...'

