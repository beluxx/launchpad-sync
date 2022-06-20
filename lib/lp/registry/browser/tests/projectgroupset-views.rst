Project Group Set views
========================

Project groups cannot be administered by end-users.  Only members of the
admins and registry admins teams can list, create, or review them.

    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.services.webapp.authorization import check_permission
    >>> login('no-priv@canonical.com')
    >>> project_set = getUtility(IProjectGroupSet)


Accessing the +index view
-------------------------

A Launchpad admin has permission to access the +index view.

    >>> view = create_view(project_set, name='+index')

    >>> login('foo.bar@canonical.com')
    >>> check_permission('launchpad.Moderate', view)
    True

The view provides a page_title.

    >>> print(view.page_title)
    Project groups registered in Launchpad

A regular user cannot access the view.

    >>> user = factory.makePerson()
    >>> ignored = login_person(user)
    >>> celebs = getUtility(ILaunchpadCelebrities)
    >>> registry = celebs.registry_experts
    >>> user.inTeam(registry)
    False

    >>> check_permission('launchpad.Moderate', view)
    False

A member of the registry team has permission.

    >>> registry_member = factory.makePerson()
    >>> login('foo.bar@canonical.com')
    >>> ignored = registry.addMember(registry_member, registry.teamowner)
    >>> registry_member.inTeam(registry)
    True

    >>> ignored = login_person(registry_member)
    >>> check_permission('launchpad.Moderate', view)
    True


Accessing the +all view
-----------------------

A Launchpad admin has permission to access the +all view.

    >>> view = create_view(project_set, name='+all')
    >>> login('foo.bar@canonical.com')
    >>> check_permission('launchpad.Moderate', view)
    True

The view provides a page_title.

    >>> print(view.page_title)
    Project groups registered in Launchpad

A regular user cannot access the view.

    >>> ignored = login_person(user)
    >>> check_permission('launchpad.Moderate', view)
    False

A member of the registry team has permission.

    >>> ignored = login_person(registry_member)
    >>> check_permission('launchpad.Moderate', view)
    True


Accessing the +new view
-----------------------

A Launchpad admin has permission to access the +new view.

    >>> view = create_view(project_set, name='+new')
    >>> login('foo.bar@canonical.com')
    >>> check_permission('launchpad.Moderate', view)
    True

    >>> print(view.page_title)
    Register a project group with Launchpad

A regular user cannot access the view.

    >>> ignored = login_person(user)
    >>> check_permission('launchpad.Moderate', view)
    False

A member of the registry team has permission.

    >>> ignored = login_person(registry_member)
    >>> check_permission('launchpad.Moderate', view)
    True
