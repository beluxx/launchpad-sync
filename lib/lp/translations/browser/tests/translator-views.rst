Translator views
================

Translator views provide ways to administrate, edit and remove
per-language translation teams in a `TranslationGroup`.

    >>> group = factory.makeTranslationGroup(
    ...     name='test-translators', title=u'Test translators')
    >>> team = factory.makeTeam(name='bad-translators',
    ...                         displayname='Bad translators')

Serbian translators in 'Test translators' group is the `team`.

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> from lp.translations.interfaces.translator import ITranslatorSet
    >>> serbian = getUtility(ILanguageSet).getLanguageByCode('sr')
    >>> translator = getUtility(ITranslatorSet).new(
    ...     group, serbian, team, None)


TranslatorAdminView
-------------------

Translator +admin view provides a nice page title and a form label.

    >>> view = create_initialized_view(translator, '+admin')
    >>> print(view.label)
    Edit Serbian translation team in Test translators

    >>> print(view.page_title)
    Edit Serbian translation team

Canceling changes to the Translator takes one back to the group
page.

    >>> print(view.cancel_url)
    http://translations.launchpad.test/+groups/test-translators

TranslatorEditView
------------------

Translator +edit view allows one to only set translation guidelines
for a language in a TranslationGroup, and page title and form label
describe that appropriately.

    >>> view = create_initialized_view(translator, '+edit')
    >>> print(view.label)
    Set Serbian guidelines for Test translators

    >>> print(view.page_title)
    Set Serbian guidelines

Canceling changes to the guidelines takes one back to the team page.

    >>> print(view.cancel_url)
    http://translations.launchpad.test/~bad-translators


TranslatorRemoveView
------------------

Translator +edit view allows one to only set translation guidelines
for a language in a TranslationGroup.

    >>> view = create_initialized_view(translator, '+remove')
    >>> print(view.label)
    Unset 'Bad translators' as the Serbian translator in Test translators

    >>> print(view.page_title)
    Remove translation team

Canceling removal of a translation team takes one back to the group page.

    >>> print(view.cancel_url)
    http://translations.launchpad.test/+groups/test-translators
