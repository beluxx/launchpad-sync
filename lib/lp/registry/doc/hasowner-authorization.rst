IHasOwner
=========

Objects which provide that interface can only be changed by the owner
itself or a Launchpad admin.

    # First we define a class which only provides IHasOwner.
    >>> from zope.interface import implementer
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.role import (
    ...     IHasOwner,
    ...     IPersonRoles,
    ... )
    >>> salgado = getUtility(IPersonSet).getByName("salgado")
    >>> @implementer(IHasOwner)
    ... class FooObject:
    ...     owner = salgado
    ...

Salgado is the owner of any FooObject we create, so he can edit it.

    >>> foo = FooObject()
    >>> from zope.component import queryAdapter
    >>> from lp.app.interfaces.security import IAuthorization
    >>> authorization = queryAdapter(foo, IAuthorization, "launchpad.Edit")
    >>> print(authorization.checkAuthenticated(IPersonRoles(salgado)))
    True

So can a member of the Launchpad admins team.

    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> admins = getUtility(IPersonSet).getByName("admins")
    >>> print(mark.inTeam(admins))
    True
    >>> print(authorization.checkAuthenticated(IPersonRoles(mark)))
    True

But someone who's not salgado nor a member of the admins team won't be
able to.

    >>> sample_person = getUtility(IPersonSet).getByName("name12")
    >>> print(sample_person.inTeam(admins))
    False
    >>> print(authorization.checkAuthenticated(IPersonRoles(sample_person)))
    False
