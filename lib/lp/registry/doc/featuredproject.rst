Featured Projects
=================

We show a few key projects on the Launchpad home page. These are
projects that are either topical, or high profile, or making very good
use of Launchpad, so we want to draw attention to them. The list of
projects is stored in the FeaturedProject table, and managed through the
PillarNameSet.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.pillar import IPillarNameSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet
    >>> pillar_set = getUtility(IPillarNameSet)
    >>> def isFeatured(project):
    ...     return project in getUtility(IPillarNameSet).featured_projects
    ...

We can get a list of featured projects from the pillar name set:

    >>> for project in pillar_set.featured_projects:
    ...     print(project.name)
    ...
    applets
    bazaar
    firefox
    gentoo
    gnome
    gnome-terminal
    mozilla
    thunderbird
    ubuntu

We'll make sure our isFeatured() test is working:

    >>> isFeatured(getUtility(IProductSet).getByName("bazaar"))
    True
    >>> isFeatured(getUtility(IProjectGroupSet).getByName("gnome"))
    True
    >>> isFeatured(getUtility(IDistributionSet).getByName("ubuntu"))
    True
    >>> isFeatured(getUtility(IDistributionSet).getByName("kubuntu"))
    False

We can add a project, product or distro to the list of featured
projects:

    >>> guadalinex = getUtility(IDistributionSet).getByName("guadalinex")
    >>> isFeatured(guadalinex)
    False
    >>> added = pillar_set.add_featured_project(guadalinex)
    >>> isFeatured(guadalinex)
    True

    >>> evolution = getUtility(IProductSet).getByName("evolution")
    >>> isFeatured(evolution)
    False
    >>> added = pillar_set.add_featured_project(evolution)
    >>> isFeatured(evolution)
    True

    >>> apache = getUtility(IProjectGroupSet).getByName("apache")
    >>> isFeatured(apache)
    False
    >>> added = pillar_set.add_featured_project(apache)
    >>> isFeatured(apache)
    True

And we can remove them, too:

    >>> pillar_set.remove_featured_project(apache)
    >>> isFeatured(apache)
    False
    >>> pillar_set.remove_featured_project(evolution)
    >>> isFeatured(evolution)
    False
    >>> pillar_set.remove_featured_project(guadalinex)
    >>> isFeatured(guadalinex)
    False

