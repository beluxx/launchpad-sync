Vocabularies
============

Introduction
------------

Vocabularies are lists of terms. In Launchpad's Component Architecture
(CA), a vocabulary is a list of terms that a widget (normally a selection
style widget) "speaks", i.e., its allowed values.

    >>> from zope.component import getUtility
    >>> from lp.testing import ANONYMOUS, login
    >>> from lp.services.webapp.interfaces import IOpenLaunchBag
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet
    >>> person_set = getUtility(IPersonSet)
    >>> product_set = getUtility(IProductSet)
    >>> login("foo.bar@canonical.com")
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
    ...     return removeSecurityProxy(vocabulary_registry.get(context, name))
    ...
    >>> product_vocabulary = vocabulary_registry.get(None, "Product")
    >>> product_vocabulary.displayname
    'Select a project'


Enumerable Vocabularies
-----------------------


DistributionUsingMaloneVocabulary
.................................

All the distributions that use Malone as their main bug tracker.

    >>> using_malone_vocabulary = get_naked_vocab(
    ...     None, "DistributionUsingMalone"
    ... )
    >>> len(using_malone_vocabulary)
    2
    >>> for term in using_malone_vocabulary:
    ...     print(term.token, term.value.displayname, term.title)
    ...
    gentoo Gentoo Gentoo
    ubuntu Ubuntu Ubuntu

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    >>> ubuntu in using_malone_vocabulary
    True
    >>> debian = getUtility(ILaunchpadCelebrities).debian
    >>> debian in using_malone_vocabulary
    False

    >>> term = using_malone_vocabulary.getTerm(ubuntu)
    >>> print(term.token, term.value.displayname, term.title)
    ubuntu Ubuntu Ubuntu

    >>> term = using_malone_vocabulary.getTerm(debian)
    Traceback (most recent call last):
    ...
    LookupError:...

    >>> term = using_malone_vocabulary.getTermByToken("ubuntu")
    >>> print(term.token, term.value.displayname, term.title)
    ubuntu Ubuntu Ubuntu

    >>> term = using_malone_vocabulary.getTermByToken("debian")
    Traceback (most recent call last):
    ...
    LookupError:...


BugNominatableSeriesVocabulary
..............................

All the series that can be nominated for fixing.

This vocabulary needs either a product or distribution in the launchbag
to get the available series. It also needs a bug, since it list only
series that haven't already been nominated.

Let's start with putting a product in the launchbag.

    >>> firefox = product_set.getByName("firefox")
    >>> getUtility(IOpenLaunchBag).clear()
    >>> getUtility(IOpenLaunchBag).add(firefox)

Firefox has the following series:

    >>> for series in firefox.series:
    ...     print(series.name)
    ...
    1.0
    trunk

Now, if we look at bug one, we can see that it hasn't been targeted
for any Firefox series yet:

    >>> from lp.bugs.interfaces.bug import IBugSet

    >>> bug_one = getUtility(IBugSet).get(1)
    >>> for bugtask in bug_one.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    ...
    Mozilla Firefox
    mozilla-firefox (Ubuntu)
    mozilla-firefox (Debian)

It has however been nominated for 1.0:

    >>> for nomination in bug_one.getNominations(firefox):
    ...     print(nomination.target.name)
    ...
    1.0

This means that if we iterate through the vocabulary with bug one, only
the trunk will be nominatable:

    >>> firefox_bug_one = bug_one.bugtasks[0]
    >>> print(firefox_bug_one.target.name)
    firefox
    >>> series_vocabulary = vocabulary_registry.get(
    ...     firefox_bug_one, "BugNominatableSeries"
    ... )
    >>> for term in series_vocabulary:
    ...     print("%s: %s" % (term.token, term.title))
    ...
    trunk: Trunk

No series is targeted or nominated on bug 4:

    >>> bug_four = getUtility(IBugSet).get(4)
    >>> for bugtask in bug_four.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    ...
    Mozilla Firefox

    >>> for nomination in bug_four.getNominations(firefox):
    ...     print(nomination.target.name)
    ...

So if we give bug four to the vocabulary, all series will be returned:

    >>> firefox_bug_four = bug_four.bugtasks[0]
    >>> print(firefox_bug_four.target.name)
    firefox
    >>> series_vocabulary = vocabulary_registry.get(
    ...     firefox_bug_four, "BugNominatableSeries"
    ... )
    >>> for term in series_vocabulary:
    ...     print("%s: %s" % (term.token, term.title))
    ...
    1.0: 1.0
    trunk: Trunk

The same works for distributions:

    >>> getUtility(IOpenLaunchBag).clear()
    >>> getUtility(IOpenLaunchBag).add(ubuntu)

Bug one is nominated for Ubuntu Hoary:

    >>> bug_one = getUtility(IBugSet).get(1)
    >>> for bugtask in bug_one.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    ...
    Mozilla Firefox
    mozilla-firefox (Ubuntu)
    mozilla-firefox (Debian)

    >>> for nomination in bug_one.getNominations(ubuntu):
    ...     print(nomination.target.name)
    ...
    hoary

So Hoary isn't included in the vocabulary:

    >>> ubuntu_bug_one = bug_one.bugtasks[1]
    >>> print(ubuntu_bug_one.distribution.name)
    ubuntu
    >>> series_vocabulary = vocabulary_registry.get(
    ...     ubuntu_bug_one, "BugNominatableSeries"
    ... )
    >>> for term in series_vocabulary:
    ...     print("%s: %s" % (term.token, term.title))
    ...
    breezy-autotest: Breezy-autotest
    grumpy: Grumpy
    warty: Warty

The same is true for bug two, where the bug is targeted to Hoary.

    >>> bug_two = getUtility(IBugSet).get(2)
    >>> for bugtask in bug_two.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    ...
    Tomcat
    Ubuntu
    Ubuntu Hoary
    mozilla-firefox (Debian)
    mozilla-firefox (Debian Woody)

    >>> for nomination in bug_two.getNominations(ubuntu):
    ...     print(nomination.target.name)
    ...
    hoary

    >>> ubuntu_bug_two = bug_two.bugtasks[1]
    >>> print(ubuntu_bug_two.distribution.name)
    ubuntu
    >>> series_vocabulary = vocabulary_registry.get(
    ...     ubuntu_bug_two, "BugNominatableSeries"
    ... )
    >>> for term in series_vocabulary:
    ...     print("%s: %s" % (term.token, term.title))
    ...
    breezy-autotest: Breezy-autotest
    grumpy: Grumpy
    warty: Warty

We can get a specific term by using the release name:

    >>> term = series_vocabulary.getTermByToken("warty")
    >>> term.value == ubuntu.getSeries("warty")
    True

Trying to get a non-existent release will result in a
NoSuchDistroSeries error.

    >>> series_vocabulary.getTermByToken("non-such-release")
    Traceback (most recent call last):
    ...
    lp.registry.errors.NoSuchDistroSeries: ...


ProjectProductsVocabularyUsingMalone
....................................

All the products in a project using Malone.


    >>> mozilla_project = getUtility(IProjectGroupSet).getByName("mozilla")
    >>> for product in mozilla_project.products:
    ...     print("%s: %s" % (product.name, product.bug_tracking_usage.name))
    ...
    firefox: LAUNCHPAD
    thunderbird: UNKNOWN

    >>> mozilla_products_vocabulary = vocabulary_registry.get(
    ...     mozilla_project, "ProjectProductsUsingMalone"
    ... )
    >>> for term in mozilla_products_vocabulary:
    ...     print("%s: %s" % (term.token, term.title))
    ...
    firefox: Mozilla Firefox


Non-Enumerable Vocabularies
---------------------------

Iterating over non-enumerable vocabularies, while possible, will
probably kill the database. Instead, these vocabularies are
search-driven.


BugWatchVocabulary
..................

All bug watches associated with a bugtask's bug.

    >>> bug_one = getUtility(IBugSet).get(1)
    >>> bugtask = bug_one.bugtasks[0]
    >>> vocab = vocabulary_registry.get(bugtask, "BugWatch")
    >>> for term in vocab:
    ...     print(term.title)
    ...
    The Mozilla.org Bug Tracker <a...>#123543</a>
    The Mozilla.org Bug Tracker <a...>#2000</a>
    The Mozilla.org Bug Tracker <a...>#42</a>
    Debian Bug tracker <a...>#304014</a>

Bug watches with an email address URL (i.e. starts with "mailto:") are
treated differently.

    >>> from lp.bugs.interfaces.bugtracker import IBugTrackerSet
    >>> from lp.bugs.interfaces.bugwatch import IBugWatchSet

    >>> bug_twelve = getUtility(IBugSet).get(12)
    >>> email_bugtracker = getUtility(IBugTrackerSet).getByName("email")
    >>> email_bugwatch = getUtility(IBugWatchSet).createBugWatch(
    ...     bug_twelve, launchbag.user, email_bugtracker, ""
    ... )
    >>> print(email_bugwatch.url)
    mailto:bugs@example.com

The title is rendered differently compared to other bug watches.

    >>> bugtask = bug_twelve.bugtasks[0]
    >>> vocab = vocabulary_registry.get(bugtask, "BugWatch")
    >>> for term in vocab:
    ...     print(term.title)
    ...
    Email bugtracker &lt;<a...>bugs@example.com</a>&gt;

Additionally, if the bug tracker's title contains the bug tracker's
URL, then the title is linkified instead.

    >>> email_bugtracker.title = "Lionel Richtea (%s)" % (
    ...     email_bugtracker.baseurl,
    ... )

    >>> for term in vocab:
    ...     print(term.title)
    ...
    Lionel Richtea (<a...>mailto:bugs@example.com</a>)

When there is no logged-in user, the title is much different. The
email address is hidden, and there is no hyperlink.

    >>> current_user = launchbag.user
    >>> login(ANONYMOUS)

    >>> for term in vocab:
    ...     print(term.title)
    ...
    Lionel Richtea (mailto:&lt;email address hidden&gt;)
