============
Vocabularies
============

    >>> from zope.component import getUtility
    >>> from zope.schema.vocabulary import getVocabularyRegistry
    >>> vocabulary_registry = getVocabularyRegistry()

TimezoneName
============

The TimezoneName vocabulary should only contain timezone names that
do not raise an exception when instantiated.

    >>> import pytz
    >>> timezone_vocabulary = vocabulary_registry.get(None, 'TimezoneName')
    >>> for timezone in timezone_vocabulary:
    ...     # Assign the return value of pytz.timezone() to the zone
    ...     # variable to prevent printing out the return value.
    ...     zone = pytz.timezone(timezone.value)

LanguageVocabulary
==================

All the languages known by Launchpad.

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> language_set = getUtility(ILanguageSet)

    >>> language_vocabulary = vocabulary_registry.get(
    ...     None, 'Language')
    >>> len(language_vocabulary)
    560

    >>> es = language_set['es']
    >>> term = language_vocabulary.getTerm(es)
    >>> print(term.token, term.value.displayname, term.title)
    es Spanish (es) Spanish (es)

    >>> pt_BR = language_set['pt_BR']
    >>> term = language_vocabulary.getTerm(pt_BR)
    >>> print(term.token, term.value.displayname, term.title)
    pt_BR Portuguese (Brazil) (pt_BR) Portuguese (Brazil) (pt_BR)

    >>> term = language_vocabulary.getTermByToken('es')
    >>> print(term.token, term.value.displayname, term.title)
    es Spanish (es) Spanish (es)

    >>> term = language_vocabulary.getTermByToken('pt_BR')
    >>> print(term.token, term.value.displayname, term.title)
    pt_BR Portuguese (Brazil) (pt_BR) Portuguese (Brazil) (pt_BR)

A language token/code may not be used with 'in' tests.

    >>> u'es' in language_vocabulary
    Traceback (most recent call last):
    ...
    AssertionError: 'in LanguageVocabulary' requires ILanguage
    as left operand, got <...> instead.

A LookupError is raised when a term is requested by token that does
not exist.

    >>> language_vocabulary.getTermByToken('foo')
    Traceback (most recent call last):
    ...
    LookupError:...


TranslatableLanguageVocabulary
==============================

All the translatable languages known by Launchpad. English is not
a translatable language, nor are Languages that are not visible.

The vocabulary will behave identically to LanguageVocabulary in tests
when the language is not English and is visible.

    >>> translatable_language_vocabulary = vocabulary_registry.get(
    ...     None, 'TranslatableLanguage')

    >>> es = language_set['es']
    >>> term = translatable_language_vocabulary.getTerm(es)
    >>> print(term.token, term.value.displayname, term.title)
    es Spanish (es) Spanish (es)

    >>> pt_BR = language_set['pt_BR']
    >>> term = translatable_language_vocabulary.getTerm(pt_BR)
    >>> print(term.token, term.value.displayname, term.title)
    pt_BR Portuguese (Brazil) (pt_BR) Portuguese (Brazil) (pt_BR)

    >>> term = translatable_language_vocabulary.getTermByToken('es')
    >>> print(term.token, term.value.displayname, term.title)
    es Spanish (es) Spanish (es)

    >>> term = translatable_language_vocabulary.getTermByToken('pt_BR')
    >>> print(term.token, term.value.displayname, term.title)
    pt_BR Portuguese (Brazil) (pt_BR) Portuguese (Brazil) (pt_BR)

    >>> es in translatable_language_vocabulary
    True

A language token/code may not be used with 'in' tests.

    >>> u'es' in translatable_language_vocabulary
    Traceback (most recent call last):
    ...
    AssertionError: 'in TranslatableLanguageVocabulary' requires
    ILanguage as left operand, got <...> instead.

A LookupError is raised when a term is requested by token that does
not exist.

    >>> translatable_language_vocabulary.getTermByToken('foo')
    Traceback (most recent call last):
    ...
    LookupError:...

English and non-visible languages are not in the
TranslatableLanguageVocabulary. English is the only visible language
excluded from the vocabulary.

    >>> translatable_languages = set(
    ...     t.value for t in translatable_language_vocabulary)
    >>> all_languages = set(l.value for l in language_vocabulary)
    >>> difference = list(all_languages - translatable_languages)
    >>> len(difference)
    90

    >>> hidden_languages = [lang for lang in difference if not lang.visible]
    >>> len(hidden_languages)
    89

    >>> for lang in difference:
    ...     if lang.visible:
    ...         print(lang.displayname)
    English (en)

The vocabulary will raise a LookupError if asked to return English.

    >>> english = language_set['en']
    >>> english in difference
    True
    >>> english in hidden_languages
    False
    >>> english.visible
    True

    >>> english in translatable_language_vocabulary
    False

    >>> translatable_language_vocabulary.getTerm(english)
    Traceback (most recent call last):
    ...
    LookupError:...

    >>> translatable_language_vocabulary.getTermByToken('en')
    Traceback (most recent call last):
    ...
    LookupError:...

The vocabulary will raise a LookupError if asked to return a
non-visible language. Chinese (zh) is one such language.

    >>> chinese = language_set['zh']
    >>> chinese in difference
    True
    >>> chinese in hidden_languages
    True
    >>> chinese.visible
    False

    >>> chinese in translatable_language_vocabulary
    False

    >>> translatable_language_vocabulary.getTerm(chinese)
    Traceback (most recent call last):
    ...
    LookupError:...

    >>> translatable_language_vocabulary.getTermByToken('zh')
    Traceback (most recent call last):
    ...
    LookupError:...
