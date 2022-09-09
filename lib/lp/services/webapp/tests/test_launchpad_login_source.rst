LaunchpadLoginSource
====================

LaunchpadLoginSource is used to create principals, from login
information, passing the email address to getPrincipalByLogin. If no
person is found with the given email address, None is returned

    >>> from lp.services.webapp.authentication import LaunchpadLoginSource
    >>> login_source = LaunchpadLoginSource()
    >>> print(login_source.getPrincipalByLogin("no-such-email@example.com"))
    None

Giving getPrincipalByLogin() an existing email address, returns a
ILaunchpadPrincipal with the same id as the corresponding Account record's
account id.

    >>> person = factory.makePerson(email="existing@example.com")
    >>> account = person.account
    >>> principal = login_source.getPrincipalByLogin("existing@example.com")

    >>> from lp.services.webapp.interfaces import ILaunchpadPrincipal
    >>> ILaunchpadPrincipal.providedBy(principal)
    True
    >>> principal.id == str(account.id)
    True

The corresponding Account and Person records are also in the
principal, to make it easier for the security machinery to get at
it. It needs to get it quite often, so having the Person record
directly on the Principal improves performance quite a lot, even
compared to getting it from storm's cache. We also store the person's name
so that OOPS handlers can use it without needing to make another database
query (which may be impossible due to a timeout).

    >>> principal.account == account
    True
    >>> principal.person == person
    True
    >>> principal.person_name == person.name
    True

The principal's account and person are security proxied.

    >>> from zope.security.proxy import getChecker
    >>> getChecker(principal.account) is not None
    True
    >>> getChecker(principal.person) is not None
    True
