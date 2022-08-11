KarmaAction views
=================

    >>> from lp.registry.interfaces.karma import IKarmaActionSet

    >>> karmaactionset = getUtility(IKarmaActionSet)


Karma action set
----------------

The karma action set +index view lists all the karma actions.

    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.testing.pages import (
    ...     extract_text, find_tag_by_id)

    >>> user = getUtility(ILaunchBag).user
    >>> view = create_view(karmaactionset, '+index', principal=user,
    ...     path_info='/karmaaction')
    >>> print(extract_text(find_tag_by_id(view(), 'karmas')))
    Category        Action          Points
    bugs            Bug Accepted    5
    ...


Karma action
------------

The karma action +edit view allow an admin to edit a karma action. The
view provides a label, page_title and a cancel_url

    >>> action = karmaactionset.getByName('branchcreated')
    >>> view = create_initialized_view(action, '+index')
    >>> print(view.label)
    Edit New branch registered karma action

    >>> print(view.page_title)
    Edit New branch registered karma action

    >>> print(view.cancel_url)
    http://launchpad.test/karmaaction

The admin can edit the karma action's fields.

    >>> view.field_names
    ['name', 'category', 'points', 'title', 'summary']

    >>> action.points
    1

    >>> login('admin@canonical.com')
    >>> form = {
    ...     'field.points': '2',
    ...     'field.actions.change': 'Change',
    ...     }
    >>> view = create_initialized_view(action, '+index', form=form)
    >>> view.errors
    []

    >>> print(view.next_url)
    http://launchpad.test/karmaaction

    >>> action.points
    2

Only admins can access the view.

    >>> from lp.services.webapp.authorization import check_permission

    >>> check_permission('launchpad.Admin', view)
    True

    >>> login('test@canonical.com')
    >>> check_permission('launchpad.Admin', view)
    False
