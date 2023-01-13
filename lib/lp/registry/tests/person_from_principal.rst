person_from_principal
=====================

person_from_principal is used to adapt an ILaunchpadPrincipal to an
IPerson. If some other object is passed in, a ComponentLookupError is
raised.

    >>> from lp.registry.adapters import person_from_principal
    >>> class NoLaunchpadPrincipal:
    ...     id = 42
    ...     person = None
    ...
    >>> person_from_principal(NoLaunchpadPrincipal())
    Traceback (most recent call last):
    ...
    zope.interface.interfaces.ComponentLookupError

If an ILaunchpadPrincipal is passed in, the principal's .person
attribute is returned. The .person attribute was set when the principal
got created, so that we don't have to look up the Person record every
time we adapt.

    >>> from zope.interface import implementer
    >>> from lp.services.webapp.interfaces import ILaunchpadPrincipal
    >>> cached_person = object()
    >>> @implementer(ILaunchpadPrincipal)
    ... class LaunchpadPrincipal:
    ...
    ...     person = cached_person
    ...

    >>> person_from_principal(LaunchpadPrincipal()) is cached_person
    True

