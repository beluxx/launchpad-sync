FAQ Vocabulary
==============

The FAQ vocabulary contains all the FAQs available in a particular
collection. It provides the IHugeVocabulary interface.

    >>> from zope.component import getUtility
    >>> from zope.schema.vocabulary import getVocabularyRegistry
    >>> from lp.testing import verifyObject
    >>> from lp.services.webapp.vocabulary import IHugeVocabulary
    >>> from lp.registry.interfaces.product import IProductSet

    >>> vocabulary_registry = getVocabularyRegistry()
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> vocabulary = vocabulary_registry.get(firefox, 'FAQ')
    >>> verifyObject(IHugeVocabulary, vocabulary)
    True

    >>> print(vocabulary.displayname)
    Select a FAQ

It contains all the FAQs of the collection, but not those from other
collections:

    >>> firefox_faqs = set(firefox.searchFAQs())
    >>> vocabulary_faqs = set(term.value for term in vocabulary)
    >>> for item in firefox_faqs.symmetric_difference(vocabulary_faqs):
    ...     print(item)

And it only contains FAQs:

    >>> u'10' in vocabulary
    False

The term's token is the FAQ's id and its title is the FAQ's title:

    >>> firefox_faq = firefox.getFAQ(10)
    >>> term = vocabulary.getTerm(firefox_faq)
    >>> term.token
    '10'
    >>> print(term.title)
    How do I install plugins (Shockwave, QuickTime, etc.)?

Asking for something which isn't a FAQ of the target raises LookupError:

    >>> from lp.registry.interfaces.distribution import (
    ...     IDistributionSet)
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> ubuntu_faq = ubuntu.getFAQ(1)
    >>> vocabulary.getTerm(ubuntu_faq)
    Traceback (most recent call last):
      ...
    LookupError:...

Since IHugeVocabulary extends IVocabularyTokenized, the term can also
be retrieved by token:

    >>> term = vocabulary.getTermByToken(u'10')
    >>> print(term.title)
    How do I install plugins (Shockwave, QuickTime, etc.)?

Trying to retrieve an invalid or non-existent token raises LookupError:

    >>> vocabulary.getTermByToken('not a good token')
    Traceback (most recent call last):
      ...
    LookupError:...

    >>> vocabulary.getTermByToken('1001')
    Traceback (most recent call last):
      ...
    LookupError:...

The searchForTerms() method returns a CountableIterator of terms that
are similar to the query:

    >>> from zope.security import proxy
    >>> from lp.services.webapp.vocabulary import CountableIterator
    >>> terms = vocabulary.searchForTerms('extensions')
    >>> proxy.isinstance(terms, CountableIterator)
    True
    >>> terms.count()
    2
    >>> for term in terms:
    ...     print(term.title)
    How do I install Extensions?
    How do I troubleshoot problems with extensions/themes?
