Demonstrate that SQLObject works with security proxies
------------------------------------------------------

Do some imports.

    >>> from zope.component import getUtility
    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> from lp.registry.interfaces.person import IPersonSet

Login as Mark.

    >>> login('mark@example.com')

Get Mark's person and another person, wrapped in security proxies.

    >>> mark = getUtility(IPersonSet).getByName('mark')
    >>> spiv = getUtility(IPersonSet).getByName('spiv')
    >>> print(type(mark))
    <... 'zope.security._proxy._Proxy'>

Get a bug task assigned to Mark.  The bug task is also security-proxied.

    >>> bugtask = getUtility(IBugTaskSet).get(2)
    >>> print(bugtask.assignee.name)
    mark
    >>> print(type(mark))
    <... 'zope.security._proxy._Proxy'>

Assign a different person as the assignee, and check that it worked by reading
it back, despite the security proxies.

    >>> bugtask.transitionToAssignee(spiv)
    >>> print(bugtask.assignee.name)
    spiv

