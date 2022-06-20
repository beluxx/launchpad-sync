ProjectGroup views
==================

The +index view of projectgroup has a has_many_projects property. It is
used by the template to determine how to layout out the page. A project
with less than 10 projects is considered not have many projects.

    >>> projectgroup = factory.makeProject(name='mothership')
    >>> view = create_view(projectgroup, name='+index')
    >>> len(projectgroup.products)
    0

    >>> view.has_many_projects
    False

    >>> def add_daughter(projectgroup, letters):
    ...     for letter in letters:
    ...         name = '%s-%s' % (letter, projectgroup.name)
    ...         product = factory.makeProduct(
    ...             name=name, owner=projectgroup.owner)
    ...         product.projectgroup = projectgroup

    >>> owner = projectgroup.owner
    >>> ignored = login_person(owner)
    >>> add_daughter(projectgroup, 'a')
    >>> from lp.services.propertycache import clear_property_cache
    >>> clear_property_cache(projectgroup)
    >>> len(projectgroup.products)
    1

    >>> view = create_view(projectgroup, name='+index')
    >>> view.has_many_projects
    False

A projectgroup with more than 10 sub projects is considered to have many
projects (10 projects are roughly 2 portlets deep.)

    >>> add_daughter(projectgroup, 'bcdefghijk')
    >>> clear_property_cache(projectgroup)
    >>> len(projectgroup.products)
    11

    >>> view = create_view(projectgroup, name='+index')
    >>> view.has_many_projects
    True


+index portlets
---------------

The index page of a project only shows the application portlets that it
officially supports. The mothership projectgroup does not officially
support any applications.

    >>> from lp.testing.pages import find_tag_by_id

    >>> product = projectgroup.products[1]
    >>> question = factory.makeQuestion(target=product)
    >>> faq = factory.makeFAQ(target=product)
    >>> bug = factory.makeBug(target=product)
    >>> blueprint = factory.makeSpecification(product=product)

    >>> view = create_view(projectgroup, name='+index', principal=owner)
    >>> content = find_tag_by_id(view.render(), 'maincontent')
    >>> print(find_tag_by_id(content, 'portlet-latest-faqs'))
    None
    >>> print(find_tag_by_id(content, 'portlet-latest-questions'))
    None
    >>> print(find_tag_by_id(content, 'portlet-latest-bugs'))
    None
    >>> print(find_tag_by_id(content, 'portlet-blueprints'))
    None

The portlet are rendered when a child product officially uses the Launchpad
Answers, Blueprints, and Bugs applications.

    >>> from lp.app.enums import ServiceUsage
    >>> product.answers_usage = ServiceUsage.LAUNCHPAD
    >>> product.blueprints_usage = ServiceUsage.LAUNCHPAD
    >>> product.official_malone = True

    >>> view = create_view(projectgroup, name='+index', principal=owner)
    >>> content = find_tag_by_id(view.render(), 'maincontent')

    >>> print(find_tag_by_id(content, 'portlet-latest-faqs')['id'])
    portlet-latest-faqs
    >>> print(find_tag_by_id(content, 'portlet-latest-questions')['id'])
    portlet-latest-questions
    >>> print(find_tag_by_id(content, 'portlet-latest-bugs')['id'])
    portlet-latest-bugs
    >>> print(find_tag_by_id(content, 'portlet-blueprints')['id'])
    portlet-blueprints
