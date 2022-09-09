Jabber IDs
==========

Jabber IDs are associated with a person and must be created through the
IJabberIDSet utility.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.role import IHasOwner
    >>> from lp.registry.interfaces.jabber import IJabberID, IJabberIDSet

The new() method of IJabberIDSet takes the person who will be associated
with the Jabber ID and the Jabber ID itself.

    >>> salgado = getUtility(IPersonSet).getByName("salgado")
    >>> jabber_id = getUtility(IJabberIDSet).new(
    ...     salgado, "salgado@jabber.net"
    ... )

The returned JabberID object provides both IJabberID and IHasOwner.

    >>> from lp.testing import verifyObject
    >>> verifyObject(IJabberID, jabber_id)
    True
    >>> verifyObject(IHasOwner, jabber_id)
    True
