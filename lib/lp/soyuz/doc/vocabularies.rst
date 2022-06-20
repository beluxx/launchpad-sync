Vocabularies
============

Introduction
------------

Vocabularies are lists of terms. In Launchpad's Component Architecture
(CA), a vocabulary is a list of terms that a widget (normally a selection
style widget) "speaks", i.e., its allowed values.

    >>> from zope.component import getUtility
    >>> from lp.testing import login
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.services.webapp.interfaces import IOpenLaunchBag
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> person_set = getUtility(IPersonSet)
    >>> product_set = getUtility(IProductSet)
    >>> login('foo.bar@canonical.com')
    >>> launchbag = getUtility(IOpenLaunchBag)
    >>> launchbag.clear()


Values, Tokens, and Titles
..........................

In Launchpad, we generally use "tokenized vocabularies." Each term in
a vocabulary has a value, token and title. A term is rendered in a
select widget like this:

<option value="$token">$title</option>

The $token is probably the data you would store in your DB. The Token is
used to uniquely identify a Term, and the Title is the thing you display
to the user.


Launchpad Vocabularies
----------------------

There are two kinds of vocabularies in Launchpad: enumerable and
non-enumerable. Enumerable vocabularies are short enough to render in a
select widget. Non-enumerable vocabularies require a query interface to make
it easy to choose just one or a couple of options from several hundred,
several thousand, or more.

Vocabularies should not be imported - they can be retrieved from the
vocabulary registry.

    >>> from zope.schema.vocabulary import getVocabularyRegistry
    >>> from zope.security.proxy import removeSecurityProxy
    >>> vocabulary_registry = getVocabularyRegistry()
    >>> def get_naked_vocab(context, name):
    ...     return removeSecurityProxy(
    ...         vocabulary_registry.get(context, name))
    >>> product_vocabulary = vocabulary_registry.get(None, "Product")
    >>> product_vocabulary.displayname
    'Select a project'


Iterating over non-enumerable vocabularies, while possible, will
probably kill the database. Instead, these vocabularies are
search-driven.


BinaryAndSourcePackageNameVocabulary
....................................

The list of binary and source package names, ordered by name.

    >>> package_name_vocabulary = vocabulary_registry.get(
    ...     None, "BinaryAndSourcePackageName")
    >>> package_name_vocabulary.displayname
    'Select a Package'

When a package name matches both a binary package name and a source
package of the exact same name, the binary package name is
returned. This allows us, in bug reporting for example, to collect the
most specific information possible.

Let's demonstrate by searching for "mozilla-firefox", for which there is
both a source and binary package of that name.

    >>> package_name_terms = package_name_vocabulary.searchForTerms(
    ...     "mozilla-firefox")
    >>> package_name_terms.count()
    2
    >>> for term in package_name_terms:
    ...     print('%s: %s' % (term.token, term.title))
    mozilla-firefox: mozilla-firefox
    mozilla-firefox-data: mozilla-firefox-data

Searching for "mozilla" should return the binary package name above, and
the source package named "mozilla".

    >>> package_name_terms = package_name_vocabulary.searchForTerms("mozilla")
    >>> package_name_terms.count()
    3
    >>> for term in package_name_terms:
    ...     print('%s: %s' % (term.token, term.title))
    mozilla: mozilla
    mozilla-firefox: mozilla-firefox
    mozilla-firefox-data: mozilla-firefox-data

The search does a case-insensitive, substring match.

    >>> package_name_terms = package_name_vocabulary.searchForTerms("lInuX")
    >>> package_name_terms.count()
    2
    >>> for term in package_name_terms:
    ...     print('%s: %s' % (term.token, term.title))
    linux-2.6.12: linux-2.6.12
    linux-source-2.6.15: linux-source-2.6.15


SourcePackageNameVocabulary
...........................

All the source packages in Launchpad that are published in public archives
of any distribution.

    >>> spn_vocabulary = vocabulary_registry.get(None, 'SourcePackageName')
    >>> len(spn_vocabulary)
    10

    >>> spn_terms = spn_vocabulary.searchForTerms("mozilla")
    >>> len(spn_terms)
    2
    >>> for term in spn_terms:
    ...     print('%s: %s' % (term.token, term.title))
    mozilla: mozilla
    mozilla-firefox: mozilla-firefox

    >>> spn_terms = spn_vocabulary.searchForTerms("pmount")
    >>> len(spn_terms)
    1
    >>> for term in spn_terms:
    ...     print('%s: %s' % (term.token, term.title))
    pmount: pmount


Processor
.........

All processors type available in Launchpad.

    >>> vocab = vocabulary_registry.get(None, "Processor")
    >>> vocab.displayname
    'Select a processor'

    >>> [term.token for term in vocab.searchForTerms('386')]
    ['386']


PPA
...

The PPA vocabulary contains all the PPAs available in a particular
collection. It provides the IHugeVocabulary interface.

    >>> from lp.testing import verifyObject
    >>> from lp.services.webapp.vocabulary import IHugeVocabulary

    >>> vocabulary = get_naked_vocab(None, 'PPA')
    >>> verifyObject(IHugeVocabulary, vocabulary)
    True

    >>> print(vocabulary.displayname)
    Select a PPA

Iterations over the PPA vocabulary will return on PPA archives.

    >>> from operator import attrgetter
    >>> for term in sorted(vocabulary, key=attrgetter('value.owner.name')):
    ...     print(term.value.owner.name)
    cprov
    mark
    no-priv

PPA vocabulary terms contain:

 * token: the PPA owner name combined with the archive name (using '/');
 * value: the IArchive object;
 * title: the first line of the PPA description text.

    >>> cprov_term = vocabulary.getTermByToken('~cprov/ubuntu/ppa')

    >>> print(cprov_term.token)
    ~cprov/ubuntu/ppa

    >>> print(cprov_term.value)
    <... lp.soyuz.model.archive.Archive instance ...>

    >>> print(cprov_term.title)
    packages to help my friends.

Not found terms result in LookupError.

    >>> vocabulary.getTermByToken('foobar')
    Traceback (most recent call last):
    ...
    LookupError: foobar

PPA vocabulary searches consider the owner FTI and the PPA FTI.

    >>> def print_search_results(results):
    ...     for archive in results:
    ...         term = vocabulary.toTerm(archive)
    ...         print('%s: %s' % (term.token, term.title))

    >>> cprov_search = vocabulary.search(u'cprov')
    >>> print_search_results(cprov_search)
    ~cprov/ubuntu/ppa: packages to help my friends.

    >>> celso_search = vocabulary.search(u'celso')
    >>> print_search_results(celso_search)
    ~cprov/ubuntu/ppa: packages to help my friends.

    >>> friends_search = vocabulary.search(u'friends')
    >>> print_search_results(friends_search)
    ~cprov/ubuntu/ppa: packages to help my friends.

We will create an additional PPA for Celso named 'testing'

    >>> from lp.soyuz.enums import ArchivePurpose
    >>> from lp.soyuz.interfaces.archive import IArchiveSet

    >>> login('foo.bar@canonical.com')
    >>> cprov = getUtility(IPersonSet).getByName('cprov')
    >>> cprov_testing = getUtility(IArchiveSet).new(
    ...     owner=cprov, name='testing', purpose=ArchivePurpose.PPA,
    ...     description='testing packages.')

Now, a search for 'cprov' will return 2 ppas and the result is ordered
by PPA name.

    >>> cprov_search = vocabulary.search(u'cprov')
    >>> print_search_results(cprov_search)
    ~cprov/ubuntu/ppa: packages to help my friends.
    ~cprov/ubuntu/testing: testing packages.

The vocabulary search also supports specific named PPA lookups
following the same combined syntax used to build unique tokens, including
some alternate and older forms.

    >>> named_search = vocabulary.search(u'~cprov/ubuntu/testing')
    >>> print_search_results(named_search)
    ~cprov/ubuntu/testing: testing packages.

    >>> named_search = vocabulary.search(u'~cprov/testing')
    >>> print_search_results(named_search)
    ~cprov/ubuntu/testing: testing packages.

    >>> named_search = vocabulary.search(u'ppa:cprov/ubuntu/testing')
    >>> print_search_results(named_search)
    ~cprov/ubuntu/testing: testing packages.

    >>> named_search = vocabulary.search(u'ppa:cprov/testing')
    >>> print_search_results(named_search)
    ~cprov/ubuntu/testing: testing packages.

As mentioned the PPA vocabulary term title only contains the first
line of the PPA description.

    >>> cprov.archive.description = "Single line."
    >>> flush_database_updates()

    >>> cprov_term = vocabulary.getTermByToken('~cprov/ubuntu/ppa')
    >>> print(cprov_term.title)
    Single line.

    >>> cprov.archive.description = "First line\nSecond line."
    >>> flush_database_updates()

    >>> cprov_term = vocabulary.getTermByToken('~cprov/ubuntu/ppa')
    >>> print(cprov_term.title)
    First line

PPAs with empty description are identified and have a title saying so.

    >>> cprov.archive.description = None
    >>> flush_database_updates()

    >>> cprov_term = vocabulary.getTermByToken('~cprov/ubuntu/ppa')
    >>> print(cprov_term.title)
    No description available

Queries on empty strings also results in a valid SelectResults.

    >>> empty_search = vocabulary.search(u'')
    >>> empty_search.count() == 0
    True
