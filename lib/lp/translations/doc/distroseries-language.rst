DistroSeriesLanguage
====================

This is a special class which encapsulates the information associated with a
particular language and distroseries.

First we need to know which distroserieslanguage we are working with. We
will work with spanish in Hoary first.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.distroseries import IDistroSeriesSet
    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> from lp.translations.interfaces.distroserieslanguage import (
    ...     IDistroSeriesLanguage)
    >>> distroseriesset = getUtility(IDistroSeriesSet)
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> hoary = distroseriesset.queryByName(ubuntu, "hoary")
    >>> print(hoary.name)
    hoary
    >>> spanish = getUtility(ILanguageSet)['es']
    >>> hoary_spanish = hoary.getDistroSeriesLanguage(spanish)

DistroSeriesLanguage provides basic `title` describing what is it about.

    >>> print(hoary_spanish.title)
    Spanish translations of Ubuntu Hoary

In DistroSeriesLanguage.pofiles we find real POFiles for the given
DistroSeries in the given language.  That is, translations that actually
contain messages.

    >>> for po in hoary_spanish.pofiles:
    ...     print(po.potemplate.name)
    evolution-2.2
    pmount
    pkgconf-mozilla
    man

There are however more templates than the ones that have messages:

    >>> hoary_templates = list(hoary.getCurrentTranslationTemplates())
    >>> for template in hoary_templates:
    ...     print(template.name)
    evolution-2.2
    man
    man
    pkgconf-mozilla
    pmount

We can ask the DistroSeriesLanguage to fetch existing POFiles for these
templates where they exist, or create matching DummyPOFiles where they
don't.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> def print_augmented_pofiles(distroserieslanguage, templates):
    ...     """Print `POFile`s for each of `templates`.
    ...
    ...     Creates `DummyPOFile`s where needed.  Prints types.
    ...     """
    ...     for pofile in distroserieslanguage.getPOFilesFor(templates):
    ...         print("%s (%s) %s" % (
    ...             pofile.potemplate.name, pofile.language.code,
    ...             removeSecurityProxy(pofile).__class__))

    >>> print_augmented_pofiles(hoary_spanish, hoary_templates)
    evolution-2.2     (es)   <class '...pofile.POFile'>
    man               (es)   <class '...pofile.POFile'>
    man               (es)   <class '...pofile.DummyPOFile'>
    pkgconf-mozilla   (es)   <class '...pofile.POFile'>
    pmount            (es)   <class '...pofile.POFile'>

Note that the sorting is by template name, and there are two 'man'
templates of which one has a real translation and the other uses a
DummyPOFile.

When we ask for the whole list of templates, including non-current ones,
we see one extra template that was not shown in the DistroSeriesLanguage
listing.

    >>> for potemplate in hoary.getTranslationTemplates():
    ...     print(potemplate.name)
    evolution-2.2
    disabled-template
    man
    man
    pkgconf-mozilla
    pmount

This is the one obsolete template.

    >>> potemplate = hoary.getTranslationTemplateByName('disabled-template')
    >>> print(potemplate.iscurrent)
    False

Also, we can see that the template has an Spanish translation that
hoary_spanish.pofiles is hiding as expected.

    >>> print(potemplate.getPOFileByLang('es').title)
    Spanish (es) translation of disabled-template in Ubuntu Hoary package
    "evolution"

We also have DummyDistroSeriesLanguages.

    >>> amharic = getUtility(ILanguageSet)['am']
    >>> hoary_amharic = hoary.getDistroSeriesLanguageOrDummy(amharic)
    >>> print(hoary_amharic.__class__)
    <class '...DummyDistroSeriesLanguage'>

English is not a translatable language because we store the source messages
as English. Thus English cannot be a DummyDistroSeriesLanguage.

    >>> english = getUtility(ILanguageSet)['en']
    >>> hoary_english = hoary.getDistroSeriesLanguageOrDummy(english)
    Traceback (most recent call last):
    ...
    AssertionError: English is not a translatable language.

A DummyDistroSeriesLanguage gives you the same set of templates to
translate as a regular DistroSeriesLanguage would.

    >>> print_augmented_pofiles(hoary_amharic, hoary_templates)
    evolution-2.2    (am)  <class '...pofile.DummyPOFile'>
    man              (am)  <class '...pofile.DummyPOFile'>
    man              (am)  <class '...pofile.DummyPOFile'>
    pkgconf-mozilla  (am)  <class '...pofile.DummyPOFile'>
    pmount           (am)  <class '...pofile.DummyPOFile'>

Now, we should test that a DummyDistroSeriesLanguage implements the full
interface of a normal DistroSeriesLanguage.

NB IF THIS FAILS then it means that the DistroSeriesLanguage object has
been extended, and the DummyDistroSeriesLanguage has not been similarly
extended.

    >>> print(IDistroSeriesLanguage.providedBy(hoary_amharic))
    True


POTemplate Sorting
------------------

In general, potemplates should be sorted by priority (descending) then name.
The sample data all has priority 0. So it's all sorted by name (the above
tests show that).

Now we will show that the priority can dominate the sort order.

    >>> potemplates = list(hoary.getCurrentTranslationTemplates())
    >>> evo = potemplates[0]
    >>> print(evo.name)
    evolution-2.2
    >>> man1 = potemplates[1]
    >>> print(man1.name)
    man
    >>> man2 = potemplates[2]
    >>> print(man2.name)
    man
    >>> mozconf = potemplates[3]
    >>> print(mozconf.name)
    pkgconf-mozilla
    >>> pm = potemplates[4]
    >>> print(pm.name)
    pmount

OK, so we have the five templates. Let's set their priorities and see if
that changes the default sort order.

We need to login so we can poke at the potemplates.

    >>> from lp.testing import login
    >>> login('foo.bar@canonical.com')

We set their priorities so that the lowest alpha-sort one has the highest
priority.

    >>> evo.priority = 5
    >>> man1.priority = 6
    >>> man2.priority = 7
    >>> mozconf.priority = 8
    >>> pm.priority = 9
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> flush_database_updates()

And now we can confirm that priority does in fact dominate:

    >>> for pot in hoary.getCurrentTranslationTemplates():
    ...     print(pot.priority, pot.name)
    9 pmount
    8 pkgconf-mozilla
    7 man
    6 man
    5 evolution-2.2

And now this priority should also dominate the distroseries language
pofile sort order:

    >>> print_augmented_pofiles(
    ...     hoary_amharic, hoary.getCurrentTranslationTemplates())
    pmount           (am)  <class '...pofile.DummyPOFile'>
    pkgconf-mozilla  (am)  <class '...pofile.DummyPOFile'>
    man              (am)  <class '...pofile.DummyPOFile'>
    man              (am)  <class '...pofile.DummyPOFile'>
    evolution-2.2    (am)  <class '...pofile.DummyPOFile'>
