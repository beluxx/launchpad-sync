# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite
import unittest

from zope.interface import implementer
from zope.publisher.interfaces.browser import IBrowserRequest

from lp.registry.interfaces.person import IPerson
from lp.services.webapp.interfaces import ILaunchBag
from lp.services.worlddata.interfaces.language import ILanguageSet


class DummyLanguage:

    def __init__(self, code, pluralforms):
        self.code = code
        self.pluralforms = pluralforms
        self.alt_suggestion_language = None


@implementer(ILanguageSet)
class DummyLanguageSet:

    _languages = {
        'ja': DummyLanguage('ja', 1),
        'es': DummyLanguage('es', 2),
        'fr': DummyLanguage('fr', 3),
        'cy': DummyLanguage('cy', None),
        }

    def __getitem__(self, key):
        return self._languages[key]


@implementer(IPerson)
class DummyPerson:

    def __init__(self, codes):
        self.codes = codes
        all_languages = DummyLanguageSet()

        self.languages = [all_languages[code] for code in self.codes]


dummyPerson = DummyPerson(('es',))
dummyNoLanguagePerson = DummyPerson(())


class DummyResponse:

    def redirect(self, url):
        pass


@implementer(IBrowserRequest)
class DummyRequest:

    def __init__(self, **form_data):
        self.form = form_data
        self.URL = "http://this.is.a/fake/url"
        self.response = DummyResponse()

    def get(self, key, default):
        raise key


def adaptRequestToLanguages(request):
    return DummyRequestLanguages()


class DummyRequestLanguages:

    def getPreferredLanguages(self):
        return [DummyLanguage('ja', 1),
            DummyLanguage('es', 2),
            DummyLanguage('fr', 3),
            ]

    def getLocalLanguages(self):
        return [DummyLanguage('da', 4),
            DummyLanguage('as', 5),
            DummyLanguage('sr', 6),
            ]


@implementer(ILaunchBag)
class DummyLaunchBag:

    def __init__(self, login=None, user=None):
        self.login = login
        self.user = user


def test_preferred_or_request_languages():
    '''
    >>> from zope.component import provideAdapter, provideUtility
    >>> from zope.container.testing import setUp, tearDown
    >>> from zope.i18n.interfaces import IUserPreferredLanguages
    >>> from lp.services.geoip.interfaces import IRequestPreferredLanguages
    >>> from lp.services.geoip.interfaces import IRequestLocalLanguages
    >>> from lp.services.worlddata.helpers import (
    ...     preferred_or_request_languages)

    First, test with a person who has a single preferred language.

    >>> setUp()
    >>> provideUtility(DummyLanguageSet(), ILanguageSet)
    >>> provideUtility(
    ...     DummyLaunchBag('foo.bar@canonical.com', dummyPerson), ILaunchBag)
    >>> provideAdapter(
    ...     adaptRequestToLanguages, (IBrowserRequest,),
    ...     IRequestPreferredLanguages)
    >>> provideAdapter(
    ...     adaptRequestToLanguages, (IBrowserRequest,),
    ...     IRequestLocalLanguages)

    >>> languages = preferred_or_request_languages(DummyRequest())
    >>> len(languages)
    1
    >>> print(languages[0].code)
    es

    >>> tearDown()

    Then test with a person who has no preferred language.

    >>> setUp()
    >>> provideUtility(DummyLanguageSet(), ILanguageSet)
    >>> provideUtility(
    ...     DummyLaunchBag('foo.bar@canonical.com', dummyNoLanguagePerson),
    ...     ILaunchBag)
    >>> provideAdapter(
    ...     adaptRequestToLanguages, (IBrowserRequest,),
    ...     IRequestPreferredLanguages)
    >>> provideAdapter(
    ...     adaptRequestToLanguages, (IBrowserRequest,),
    ...     IRequestLocalLanguages)

    >>> languages = preferred_or_request_languages(DummyRequest())
    >>> len(languages)
    6
    >>> print(languages[0].code)
    ja

    >>> tearDown()
    '''


def test_is_english_variant():
    """
    >>> from lp.services.worlddata.helpers import is_english_variant
    >>> class Language:
    ...     def __init__(self, code):
    ...         self.code = code
    >>> is_english_variant(Language('fr'))
    False
    >>> is_english_variant(Language('en'))
    False
    >>> is_english_variant(Language('en_CA'))
    True
    >>> is_english_variant(Language('enm'))
    False
    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite())
    return suite
