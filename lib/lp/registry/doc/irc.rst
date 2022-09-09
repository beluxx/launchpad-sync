IRC IDs
=======

IRC IDs are associated with a person and must be created through the
IIrcIDSet utility.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.role import IHasOwner
    >>> from lp.registry.interfaces.irc import IIrcID, IIrcIDSet

The new() method of IIrcIDSet takes the person who will be associated
with the IRC ID, the IRC network and nickname.

    >>> salgado = getUtility(IPersonSet).getByName("salgado")
    >>> irc_id = getUtility(IIrcIDSet).new(
    ...     salgado, "chat.freenode.net", "salgado"
    ... )

The returned IrcID object provides both IIrcID and IHasOwner.

    >>> from lp.testing import verifyObject
    >>> verifyObject(IIrcID, irc_id)
    True
    >>> verifyObject(IHasOwner, irc_id)
    True
