Root views
==========

The launchpad front page uses the LaunchpadRootIndexView to provide the
special data needed for the layout.

    # The _get_day_of_year() method must be hacked to return a predictable day
    # to testing the view.
    >>> from lp.app.browser.root import LaunchpadRootIndexView
    >>> def day():
    ...     return 4
    >>> LaunchpadRootIndexView._get_day_of_year = staticmethod(day)

The view has a provides a list of featured projects and a top project.

    >>> from lp.services.webapp.interfaces import ILaunchpadRoot

    >>> root = getUtility(ILaunchpadRoot)
    >>> view = create_initialized_view(root, name='index.html')
    >>> for project in view.featured_projects:
    ...     print(project.name)
    applets bazaar firefox gentoo gnome-terminal mozilla thunderbird ubuntu

    >>> print(view.featured_projects_top.name)
    gnome

The featured_projects_top property is set by a helper method that pops the
project from the list of featured_projects.

    >>> featured_projects = list(view.featured_projects)
    >>> featured_projects_top = view.featured_projects_top
    >>> view._setFeaturedProjectsTop()
    >>> print(view.featured_projects_top.name)
    gnome-terminal

    >>> for project in view.featured_projects:
    ...     print(project.name)
    applets bazaar firefox gentoo mozilla thunderbird ubuntu

If there are no featured projects, the top featured project is None.

    >>> view.featured_projects = []
    >>> view.featured_projects_top = None
    >>> view._setFeaturedProjectsTop()
    >>> print(view.featured_projects_top)
    None

    # Put the projects back as they were.
    >>> view.featured_projects = featured_projects
    >>> view.featured_projects_top = featured_projects_top

The view provides the counts of branches, Git repositories, bugs,
projects, translations, blueprints, and answers registered in Launchpad.

    >>> view.branch_count
    30
    >>> view.gitrepository_count
    0
    >>> view.bug_count
    12
    >>> view.project_count
    20
    >>> view.translation_count
    155
    >>> view.blueprint_count
    12
    >>> view.answer_count
    13
