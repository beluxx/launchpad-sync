     Components and Sections
     ^^^^^^^^^^^^^^^^^^^^^^^

Component refers to a group of packages within a DistroSeries that
are related by their need, shipment condition and/or licence.

Zope auxiliary test toolchain:

    >>> from zope.component import getUtility
    >>> from lp.testing import verifyObject

Importing Component content class and its interface:

    >>> from lp.services.database.interfaces import IStore
    >>> from lp.soyuz.interfaces.component import IComponent
    >>> from lp.soyuz.model.component import Component

Get an Component instance from the current sampledata:

    >>> main = IStore(Component).get(Component, 1)

Test some attributes:

    >>> print(main.id, main.name)
    1 main

Check if the instance corresponds to the declared interface:

    >>> verifyObject(IComponent, main)
    True

Now perform the tests for the Component ContentSet class, ComponentSet.

Check if it can be imported:

    >>> from lp.soyuz.interfaces.component import IComponentSet

Check we can use the set as a utility:

    >>> component_set = getUtility(IComponentSet)

Test iteration over the sampledata default components:

    >>> for c in component_set:
    ...     print(c.name)
    ...
    main
    restricted
    universe
    multiverse
    partner

by default, they are ordered by 'id'.

Test __getitem__ method, retrieving a component by name:

    >>> print(component_set["universe"].name)
    universe

Test get method, retrieving a component by its id:

    >>> print(component_set.get(2).name)
    restricted

New component creation for a given name:

    >>> new_comp = component_set.new("test")
    >>> print(new_comp.name)
    test

Ensuring a component (if not found, create it):

    >>> component_set.ensure("test").id == new_comp.id
    True

    >>> component_set.ensure("test2").id == new_comp.id
    False


Importing Section content class and its interface:

    >>> from lp.soyuz.interfaces.section import ISection
    >>> from lp.soyuz.model.section import Section

Get a Section instance from the current sampledata:

    >>> base = IStore(Section).get(Section, 1)

Test some attributes:

    >>> print(base.id, base.name)
    1 base

Check if the instance corresponds to the declared interface:

    >>> verifyObject(ISection, base)
    True

Now perform the tests for the Section ContentSet class, SectionSet.

Check if it can be imported:

    >>> from lp.soyuz.interfaces.section import ISectionSet

Check we can use the set as a utility:

    >>> section_set = getUtility(ISectionSet)

Test iteration over the sampledata default sections:

    >>> for s in section_set:
    ...     print(s.name)
    ...
    base
    web
    editors
    admin
    comm
    debian-installer
    devel
    doc
    games
    gnome
    graphics
    interpreters
    kde
    libdevel
    libs
    mail
    math
    misc
    net
    news
    oldlibs
    otherosfs
    perl
    python
    shells
    sound
    tex
    text
    translations
    utils
    x11
    electronics
    embedded
    hamradio
    science

by default they are ordered by 'id'.

Test __getitem__ method, retrieving a section by name:

    >>> print(section_set["science"].name)
    science

Test get method, retrieving a section by its id:

    >>> print(section_set.get(2).name)
    web

New section creation for a given name:

    >>> new_sec = section_set.new("test")
    >>> print(new_sec.name)
    test

Ensuring a section (if not found, create it):

    >>> section_set.ensure("test").id == new_sec.id
    True

    >>> section_set.ensure("test2").id == new_sec.id
    False
