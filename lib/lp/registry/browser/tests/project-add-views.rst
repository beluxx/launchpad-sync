Project add views
=================

New projects are registered in Launchpad using a two step multi-view widget.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> login("foo.bar@canonical.com")
    >>> product_set = getUtility(IProductSet)

    >>> view = create_initialized_view(product_set, name="+new")
    >>> view.first_step
    <class 'lp.registry.browser.product.ProjectAddStepOne'>

The first step requires all of name, summary, display_name to be given.  These
are forwarded in the form data to the second step.  The title is also
forwarded, but is only required by the Zope machinery, not the view.

    >>> from lp.registry.browser.product import ProjectAddStepOne
    >>> form = {
    ...     "field.actions.continue": "Continue",
    ...     "field.__visited_steps__": ProjectAddStepOne.step_name,
    ...     "field.display_name": "",
    ...     "field.name": "",
    ...     "field.summary": "",
    ... }

    >>> view = create_initialized_view(product_set, name="+new", form=form)
    >>> for error in view.view.errors:
    ...     print(pretty(error.args))
    ...
    ('display_name', 'Name', RequiredMissing('display_name'))
    ('name', 'URL', RequiredMissing('name'))
    ('summary', 'Summary', RequiredMissing('summary'))

    >>> form["field.display_name"] = "Snowdog"
    >>> form["field.name"] = "snowdog"
    >>> form["field.summary"] = "By-tor and the Snowdog"
    >>> view = create_initialized_view(product_set, name="+new", form=form)

Each step in the process has a label, a description, and a search results
count.  The first step has no search results.

    # Because of the way the multistep view works, we need to test the
    # steps individually.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest

    >>> form["field.__visited_steps__"] = ProjectAddStepOne.step_name
    >>> request = LaunchpadTestRequest(form=form, method="POST")
    >>> view = ProjectAddStepOne(product_set, request)
    >>> view.initialize()

    >>> print(view.label)
    Register a project in Launchpad
    >>> print(view.step_description)
    Project basics
    >>> view.search_results_count
    0

The second step has the same attributes, but it provides a little more
information in the label.

    >>> from lp.registry.browser.product import ProjectAddStepTwo
    >>> form = {
    ...     "field.actions.continue": "Continue",
    ...     "field.__visited_steps__": ProjectAddStepTwo.step_name,
    ...     "field.display_name": "Snowdog",
    ...     "field.name": "snowdog",
    ...     "field.title": "The Snowdog",
    ...     "field.summary": "By-tor and the Snowdog",
    ... }

    >>> request = LaunchpadTestRequest(form=form, method="POST")
    >>> view = ProjectAddStepTwo(product_set, request)
    >>> view.initialize()

    >>> print(view.label)
    Register Snowdog (snowdog) in Launchpad
    >>> print(view.step_description)
    Registration details
    >>> view.search_results_count
    0

The second step also has a iterator over all the search results, of which
there are currently none.

    >>> list(view.search_results)
    []

The prospective project's name, display_name and summary are used to search
existing projects for possible matches.  By tweaking the project summary, we
can see that there are search results available.

    >>> form["field.summary"] = "My Snowdog ate your Firefox"

    >>> request = LaunchpadTestRequest(form=form, method="POST")
    >>> view = ProjectAddStepTwo(product_set, request)
    >>> view.initialize()

    >>> print(view.label)
    Register Snowdog (snowdog) in Launchpad

Because there are search results, the description used on the page is
different.

    >>> print(view.step_description)
    Check for duplicate projects

The search results are displayed on the page.

    >>> view.search_results_count
    2
    >>> for project in view.search_results:
    ...     print(project.name)
    ...
    firefox
    mozilla

The project's licence has not yet been selected, so posting this form will
result in an error, since the licence is required.

    >>> form.update(
    ...     {
    ...         "field.__visited_steps__": "%s|%s"
    ...         % (ProjectAddStepOne.step_name, ProjectAddStepTwo.step_name),
    ...         "field.actions.continue": "Continue",
    ...     }
    ... )

    >>> request = LaunchpadTestRequest(form=form, method="POST")
    >>> view = ProjectAddStepTwo(product_set, request)
    >>> view.initialize()
    >>> for error in view.errors:
    ...     print(error)
    ...
    You must select at least one licence.  If you select Other/Proprietary
    or Other/OpenSource you must include a description of the licence.
    ...

When an open source licence is selected, the project is created.

    # The form keys have the 'field.' prefix here because the form data will
    # be processed.
    >>> registrant = factory.makePerson()
    >>> form = {
    ...     "field.display_name": "Snowdog",
    ...     "field.name": "snowdog",
    ...     "field.title": "The Snowdog",
    ...     "field.summary": "By-tor and the Snowdog",
    ...     "field.licenses": ["PYTHON"],
    ...     "field.license_info": "",
    ...     "field.owner": registrant.name,
    ...     "field.driver": registrant.name,
    ...     "field.bug_supervisor": registrant.name,
    ...     "field.__visited_steps__": "%s|%s"
    ...     % (ProjectAddStepOne.step_name, ProjectAddStepTwo.step_name),
    ...     "field.actions.continue": "Continue",
    ... }
    >>> request = LaunchpadTestRequest(form=form, method="POST")
    >>> view = ProjectAddStepTwo(product_set, request)
    >>> view.initialize()
    >>> view.errors
    []

    >>> print(product_set.getByName("snowdog").display_name)
    Snowdog


Duplicate projects
------------------

A project that already exists cannot be registered again.  The only field
that's checked for duplicates is the 'name' field.

    >>> form = {
    ...     "field.display_name": "Cougar",
    ...     "field.name": "snowdog",
    ...     "field.title": "The Cougar",
    ...     "field.summary": "There's the Cougar!",
    ...     "field.__visited_steps__": ProjectAddStepOne.step_name,
    ...     "field.actions.continue": "Continue",
    ... }
    >>> request = LaunchpadTestRequest(form=form, method="POST")
    >>> view = ProjectAddStepOne(product_set, request)
    >>> view.initialize()

    >>> for error in view.errors:
    ...     print(error)
    ...
    ('name', 'URL',
     LaunchpadValidationError('snowdog is already used by another project'))
