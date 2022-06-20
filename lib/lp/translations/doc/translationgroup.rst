Translation Groups
==================

    >>> from zope.component import getUtility

    >>> from lp.testing import login
    >>> login('daf@canonical.com')

Here are various sets of things that we'll need.

    >>> from lp.translations.interfaces.translationgroup import (
    ...     ITranslationGroupSet)
    >>> translation_group_set = getUtility(ITranslationGroupSet)

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> person_set = getUtility(IPersonSet)

    >>> from lp.registry.interfaces.product import IProductSet
    >>> product_set = getUtility(IProductSet)

    >>> from lp.translations.interfaces.translator import ITranslatorSet
    >>> translator_set = getUtility(ITranslatorSet)

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> language_set = getUtility(ILanguageSet)

    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> potemplate_set = getUtility(IPOTemplateSet)

Here are Carlos and No Privileges Person. Carlos manages the translation group
for Evolution, and No Privileges Person is a translator.

    >>> carlos = person_set.getByName('carlos')
    >>> no_priv = person_set.getByName('no-priv')

Here's our translation group.

    >>> group = translation_group_set.new(
    ...     name='foo-translators',
    ...     title='Foo Translators',
    ...     summary='Foo Translators',
    ...     translation_guide_url='https://help.launchpad.net/',
    ...     owner=carlos)

We can access all details of the new TranslationGroup.

    >>> print(group.title)
    Foo Translators
    >>> print(group.translation_guide_url)
    https://help.launchpad.net/
    >>> print(group.owner.name)
    carlos

Let's make it the translation group for Evolution.

    >>> evolution = product_set['evolution']
    >>> evolution.translationgroup = group

Let's only allow translators from that group to translate.

    >>> from lp.translations.enums import TranslationPermission
    >>> evolution.translationpermission = TranslationPermission.CLOSED

No Privileges Person isn't allowed to translate into Welsh.

    >>> series = evolution.getSeries('trunk')
    >>> subset = potemplate_set.getSubset(productseries=series)
    >>> potemplate = subset['evolution-2.2']
    >>> pofile = potemplate.newPOFile('cy')
    >>> pofile.canEditTranslations(no_priv)
    False

Let's add them to the group.

    >>> welsh = language_set['cy']

    >>> no_priv_translator = translator_set.new(
    ...     translationgroup=group,
    ...     language=welsh,
    ...     translator=no_priv)

No Privileges Person *is* allowed to translate into Welsh.

    >>> pofile.canEditTranslations(no_priv)
    True

Each group has a list of top_projects that it translates.  It is just
a shorter list of all the projects.  At the moment, it lists only
Evolution, and a number_of_remaining_projects (those not shown in the
top_projects list) is zero.

    >>> set(group.top_projects) == set([evolution])
    True
    >>> group.number_of_remaining_projects
    0

Making a distribution use the translation group puts it into top_projects.

    >>> distro = factory.makeDistribution()
    >>> distro.translationgroup = group
    >>> set(group.top_projects) == set([evolution, distro])
    True
    >>> group.number_of_remaining_projects
    0

Project groups, if they use this translation group, appear in the
top_projects too.

    >>> project = factory.makeProject()
    >>> project.translationgroup = group
    >>> set(group.top_projects) == set([evolution, distro, project])
    True
    >>> group.number_of_remaining_projects
    0

If we add 2 projects more than what the group.TOP_PROJECTS_LIMIT is,
the top_projects list is shortened and a number_of_remaining_projects tells
us how many other projects are there (2).

    >>> from zope.security.proxy import removeSecurityProxy
    >>> limit = removeSecurityProxy(group).TOP_PROJECTS_LIMIT
    >>> current = len(group.top_projects)
    >>> goal = limit + 2 - current
    >>> while goal > 0:
    ...     product = factory.makeProduct()
    ...     product.translationgroup = group
    ...     goal -= 1
    >>> len(group.top_projects) == limit
    True
    >>> group.number_of_remaining_projects
    2

We can use TranslationGroupSet to check what translation groups a person
is a part of:

    >>> for group in translation_group_set.getByPerson(carlos):
    ...     print(group.name)
    testing-translation-team

    >>> for group in translation_group_set.getByPerson(no_priv):
    ...     print(group.name)
    foo-translators

    >>> translators = getUtility(ITranslatorSet)
    >>> for trans in translators.getByTranslator(carlos):
    ...     print(trans.language.code)
    ...     print(trans.translationgroup.name)
    ...     print(trans.style_guide_url)
    es
    testing-translation-team
    None

    >>> for trans in translators.getByTranslator(no_priv):
    ...     print(trans.language.code)
    ...     print(trans.translationgroup.name)
    ...     print(trans.style_guide_url)
    cy
    foo-translators
    None


fetchTranslatorData
-------------------

Use fetchTranslator data to get all members of a translation group,
with their respective assigned languages, in one go.  This saves
repeated querying.

    >>> group = factory.makeTranslationGroup()
    >>> list(group.fetchTranslatorData())
    []

    >>> de_team = factory.makeTeam(name='de-team')
    >>> nl_team = factory.makeTeam(name='nl-team')
    >>> la_team = factory.makeTeam(name='la-team')
    >>> de_translator = factory.makeTranslator('de', group, person=de_team)
    >>> nl_translator = factory.makeTranslator('nl', group, person=nl_team)
    >>> la_translator = factory.makeTranslator('la', group, person=la_team)
    >>> transaction.commit()

The method returns tuples of respectively a Translator ("translation
group membership entry"), its language, and the actual team or person
assigned to that language.

    >>> for (translator, language, team) in group.fetchTranslatorData():
    ...     print(translator.language.code, language.code, team.name)
    nl nl nl-team
    de de de-team
    la la la-team

The members are sorted by language name in English.

    >>> for (translator, language, person) in group.fetchTranslatorData():
    ...     print(language.englishname)
    Dutch
    German
    Latin
