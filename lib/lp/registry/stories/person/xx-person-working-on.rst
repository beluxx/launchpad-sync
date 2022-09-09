Things a person is working on
=============================

Any person page contains the bugs/blueprints a person is working on.

Sample Person is not working on any bugs/blueprints right now, so the section
won't be displayed.

    >>> anon_browser.open("http://launchpad.test/~name12/")
    >>> text = extract_text(
    ...     find_tag_by_id(anon_browser.contents, "working-on")
    ... )
    >>> len(text)
    0

For a person who's working on some bugs/blueprints, though, they'd be
displayed there.

    # Go behind the scenes and create a bug and a blueprint, both assigned to
    # a single person.
    >>> login("foo.bar@canonical.com")
    >>> from lp.services.webapp import canonical_url
    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> from lp.blueprints.enums import SpecificationImplementationStatus
    >>> spec = factory.makeSpecification()
    >>> spec.assignee = spec.owner
    >>> spec.implementation_status = SpecificationImplementationStatus.STARTED
    >>> status = spec.updateLifecycleStatus(spec.owner)
    >>> task = factory.makeBugTask(owner=spec.owner)
    >>> task.transitionToAssignee(task.owner)
    >>> task.transitionToStatus(BugTaskStatus.INPROGRESS, task.owner)
    >>> new_person_url = canonical_url(task.owner)
    >>> logout()

    >>> anon_browser.open(new_person_url)
    >>> print(
    ...     extract_text(find_tag_by_id(anon_browser.contents, "working-on"))
    ... )
    All bugs in progress
    Assigned bugs
    ...
    All assigned blueprints
    ...

The links below the bugs/blueprints sections point to the other
bugs/blueprints that the person is working on.

    >>> anon_browser.getLink("All bugs in progress")
    <Link...+assignedbugs?...status=In+Progress...
    >>> anon_browser.getLink("All assigned blueprints")
    <Link...+specs?role=assignee...
