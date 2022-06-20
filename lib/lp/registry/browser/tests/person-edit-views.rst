Person edit pages
=================

There are many views to edit aspects of a user.


Edit IRC
--------

The +editircnickname provides a label and a title.

    >>> person = factory.makePerson(name='basil', displayname='Basil')
    >>> ignored = login_person(person)
    >>> view = create_initialized_view(
    ...     person, name='+editircnicknames', form={}, principal=person)
    >>> print(view.label)
    Basil's IRC nicknames

    >>> print(view.page_title)
    Basil's IRC nicknames

    >>> print(view.cancel_url)
    http://launchpad.test/~basil

The IRC form requires a nickname.

    >>> form = {
    ...     'newnetwork': 'chat.freenode.net',
    ...     'newnick': '',
    ...     'field.actions.save': 'Save Changes',
    ...     }
    >>> view = create_initialized_view(
    ...     person, name='+editircnicknames', form=form, principal=person)

    # This form does not use schema or LaunchpadFormView validation.
    >>> view.errors
    []

    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    Neither Nickname nor Network can be empty...

    >>> [irc for irc in person.ircnicknames]
    []

The IRC form requires a network.

    >>> form = {
    ...     'newnetwork': '',
    ...     'newnick': 'basil',
    ...     'field.actions.save': 'Save Changes',
    ...     }
    >>> view = create_initialized_view(
    ...     person, name='+editircnicknames', form=form, principal=person)

    # This form does not use schema or LaunchpadFormView validation.
    >>> view.errors
    []

    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    Neither Nickname nor Network can be empty.

    >>> [irc for irc in person.ircnicknames]
    []

The IRC nickname is added when both the nickname and network are submitted.

    >>> form = {
    ...     'newnetwork': 'chat.freenode.net',
    ...     'newnick': 'basil',
    ...     'field.actions.save': 'Save Changes',
    ...     }
    >>> view = create_initialized_view(
    ...     person, name='+editircnicknames', form=form, principal=person)

    # This form does not use schema or LaunchpadFormView validation.
    >>> view.errors
    []

    >>> print(view.request.response.notifications)
    []

    # We need to clear ircnicknames from the property cache so the new data
    # is read.
    >>> from lp.services.propertycache import get_property_cache
    >>> del get_property_cache(person).ircnicknames
    >>> [ircnickname] = [irc for irc in person.ircnicknames]
    >>> print(ircnickname.nickname)
    basil

An IRC nickname can be removed.

    >>> id = ircnickname.id
    >>> form = {
    ...     'newnetwork_%s' % ircnickname.id: 'chat.freenode.net',
    ...     'newnick_%s' % ircnickname.id: 'basil',
    ...     'remove_%s' % ircnickname.id: 'Remove',
    ...     'field.actions.save': 'Save Changes',
    ...     }
    >>> view = create_initialized_view(
    ...     person, name='+editircnicknames', form=form, principal=person)

    # This form does not use schema or LaunchpadFormView validation.
    >>> view.errors
    []

    >>> print(view.request.response.notifications)
    []

    # Clear the cache first.
    >>> del get_property_cache(person).ircnicknames
    >>> [irc.nickname for irc in person.ircnicknames]
    []
