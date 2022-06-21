===========
translators
===========

We can get the list of translators (ordered by descending translation karma)
that did some translation in Launchpad and expressed their interest for a
concrete language.

    # Sample data is not complete for this test, so we need to note that
    # another Spanish translator expressed its interest on doing Spanish
    # translations.  That other person is Foo Bar (name16).
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> foo_bar = getUtility(IPersonSet).getByName('name16')
    >>> print(foo_bar.displayname)
    Foo Bar

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> spanish = getUtility(ILanguageSet).getLanguageByCode('es')
    >>> login('foo.bar@canonical.com')
    >>> foo_bar.addLanguage(spanish)
    >>> for translator in spanish.translators:
    ...     karma = 0
    ...     for karma_category_cache in translator.karma_category_caches:
    ...         if (karma_category_cache.category.name == 'translations'):
    ...             karma = karma_category_cache.karmavalue
    ...     print('%s: %d' % (translator.displayname, karma))
    Foo Bar: 164
    Carlos Perelló Marín: 9
