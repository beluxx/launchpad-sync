Permission checking
===================

The check_permission() helper is a wrapper around Zope's security API
that makes it easy to check if a user has the requested permission on a
given object.  This is the same check available in TALES as
something/required:permission.Name.

    >>> from zope.component import getUtility
    >>> from lp.services.webapp.authorization import check_permission
    >>> from lp.registry.interfaces.person import IPersonSet

    >>> personset = getUtility(IPersonSet)
    >>> sample_person = personset.get(12)

    >>> login('test@canonical.com')
    >>> check_permission('launchpad.Edit', sample_person)
    True
    >>> mark = personset.getByEmail('mark@example.com')
    >>> check_permission('launchpad.Edit', mark)
    False

If the permission doesn't exist, it raises an error:

    >>> check_permission('mushroom.Badger', sample_person)
    Traceback (most recent call last):
    ...
    ValueError: ('Undefined permission ID', ...'mushroom.Badger')
    >>> logout()


WebService-related restrictions
-------------------------------

The webservice is supposed to be consumed by third party applications
rather than human beings, so users must have finer grained control on
what applications are allowed to do.


Access level
............

This specifies what level of access is allowed for the principal whose
credentials were given in the request.  A principal with READ_PRIVATE
access level will be able to read, but not change, anything.

    >>> from lp.services.webapp.interaction import (
    ...     Participation, setupInteraction)
    >>> from lp.services.webapp.interfaces import (
    ...     AccessLevel, IPlacelessAuthUtility)
    >>> login('test@canonical.com')
    >>> principal = getUtility(IPlacelessAuthUtility).getPrincipalByLogin(
    ...     'test@canonical.com')
    >>> logout()
    >>> principal.access_level = AccessLevel.READ_PRIVATE
    >>> setupInteraction(principal)
    >>> check_permission('launchpad.View', sample_person)
    True
    >>> check_permission('launchpad.Edit', sample_person)
    False

The access level of a principal also specifies whether or not it has
access to private objects.  For instance, the above principal has
permission to read private and non-private objects (READ_PRIVATE).

    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> login('test@canonical.com')
    >>> bug_4 = getUtility(IBugSet).get(4)
    >>> bug_4.setPrivate(True, sample_person)
    True
    >>> check_permission('launchpad.View', bug_4)
    True

A principal with permission to read only non-private objects won't have
access to that bug, though.

    >>> logout()
    >>> principal.access_level = AccessLevel.READ_PUBLIC
    >>> setupInteraction(principal)
    >>> check_permission('launchpad.View', bug_4)
    False

A token used for desktop integration has a level of permission
equivalent to WRITE_PUBLIC.

    >>> principal.access_level = AccessLevel.DESKTOP_INTEGRATION
    >>> setupInteraction(principal)
    >>> check_permission('launchpad.View', bug_4)
    True

    >>> check_permission('launchpad.Edit', sample_person)
    True

Users logged in through the web application have full access, which
means they can read/change any object they have access to.

    >>> mock_participation = Participation()
    >>> login('test@canonical.com', mock_participation)
    >>> mock_participation.principal.access_level
    <DBItem AccessLevel.WRITE_PRIVATE...
    >>> check_permission('launchpad.View', sample_person)
    True
    >>> check_permission('launchpad.Edit', sample_person)
    True


Scope of access
...............

When users allow applications to access Launchpad on their behalf, they
are also able to limit that access to a certain scope (ProjectGroup, Product,
Distribution or DistributionSourcePackage).  If that is used, then the
access level specified will be valid only for things in that scope.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet
    >>> login('foo.bar@canonical.com')
    >>> principal = getUtility(IPlacelessAuthUtility).getPrincipalByLogin(
    ...     'foo.bar@canonical.com')
    >>> firefox = getUtility(IProductSet)['firefox']
    >>> mozilla = getUtility(IProjectGroupSet)['mozilla']
    >>> private_bug = getUtility(IBugSet).get(14)
    >>> logout()
    >>> principal.access_level = AccessLevel.WRITE_PRIVATE
    >>> principal.scope_url = '/firefox'
    >>> setupInteraction(principal)
    >>> check_permission('launchpad.Edit', firefox)
    True
    >>> check_permission('launchpad.Edit', mozilla)
    False

The application will still have READ_PUBLIC access to things outside
that scope, though.

    >>> check_permission('launchpad.View', mozilla)
    True

But it won't be able to view private stuff that is not within its scope
(firefox).

    >>> private_bug.private
    True
    >>> check_permission('launchpad.View', private_bug)
    False

If the scope is a ProjectGroup or Distribution, then the access level will
be used for anything which is part of that ProjectGroup/Distribution.

    >>> principal.scope_url = '/mozilla'
    >>> setupInteraction(principal)
    >>> check_permission('launchpad.Edit', mozilla)
    True
    >>> check_permission('launchpad.Edit', firefox)
    True

    >>> from lp.registry.interfaces.distribution import (
    ...     IDistributionSet)
    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> warty = ubuntu.getSeries('warty')
    >>> principal.scope_url = '/ubuntu'
    >>> setupInteraction(principal)
    >>> check_permission('launchpad.Edit', ubuntu)
    True
    >>> check_permission('launchpad.Edit', warty)
    True

But having access restricted to a given distribution won't warrant any
special access on anything not related to the distribution, just like
with Products/ProjectGroups.

    >>> check_permission('launchpad.Edit', firefox)
    False

A bug task whose target is Firefox is said to be within firefox (which
in turn is within Mozilla), so the user's access level will apply to
that bug task as well.

    >>> principal.scope_url = '/mozilla'
    >>> setupInteraction(principal)
    >>> from lp.bugs.interfaces.bugtasksearch import BugTaskSearchParams
    >>> bug_task = firefox.searchTasks(
    ...     BugTaskSearchParams(user=personset.getByName('name16')))[0]
    >>> check_permission('launchpad.Edit', bug_task)
    True

If no scope is specified, the access level will be used for everything.

    >>> principal.scope_url = None
    >>> setupInteraction(principal)
    >>> check_permission('launchpad.Edit', ubuntu)
    True
    >>> check_permission('launchpad.Edit', warty)
    True
    >>> check_permission('launchpad.Edit', firefox)
    True
    >>> check_permission('launchpad.Edit', mozilla)
    True
