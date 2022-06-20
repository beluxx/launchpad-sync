=================
Person karma view
=================

The ~person/+karma page is controlled by the PersonKarmaView.

    >>> geddy = factory.makePerson(name='geddy', displayname='Geddy Lee')
    >>> ignored = login_person(geddy)
    >>> view = create_initialized_view(geddy, '+karma')

The view's label shows the person who's karma we're looking at...

    >>> print(view.label)
    Your Launchpad Karma

...even when the logged in user is looking at someone else's karma.

    >>> neil = factory.makePerson(name='neil', displayname='Neil Peart')
    >>> view = create_initialized_view(neil, '+karma')
    >>> print(view.label)
    Launchpad Karma
