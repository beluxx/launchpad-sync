IFAQCollection Interface
========================

The Launchpad Answer Tracker can be used to track answers to commonly
asked questions. Regular user questions can then be answered with a
referral to the FAQ document.

Objects that represents collection of FAQs provides the IFAQCollection
interface. (The test harness is responsible for providing an object
providing this interface in the 'collection' variable of the test name
space. That way we can verify that multiple implementation provide the
interface correctly.)

    >>> from zope.interface.verify import verifyObject
    >>> from lp.answers.interfaces.faqcollection import IFAQCollection

    >>> verifyObject(IFAQCollection, collection)
    True


Population FAQs collection
--------------------------

The IFAQCollection interface is a read-only interface. The IFAQTarget
interface is used for creating FAQs (see faqtarget.rst for details).

Since not all IFAQCollections are IFAQTarget, we rely on the harness to
provide us with a newFAQ() function that can be used to add a FAQ to the
collection.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> personset = getUtility(IPersonSet)
    >>> no_priv = personset.getByName("no-priv")
    >>> foo_bar = personset.getByEmail("foo.bar@canonical.com")
    >>> sample_person = personset.getByEmail("test@canonical.com")

    >>> login("foo.bar@canonical.com")
    >>> faq_specifications = [
    ...     (
    ...         no_priv,
    ...         "How do I install Foo?",
    ...         "See http://www.foo.org/install",
    ...         "foo install",
    ...     ),
    ...     (
    ...         sample_person,
    ...         "What is The Meaning of Life?",
    ...         "A Monty Python film!",
    ...         "film monty python",
    ...     ),
    ...     (
    ...         foo_bar,
    ...         "How do I make money quickly off the Internet?",
    ...         "Install this really nice software that you can find at "
    ...         "http://www.getrichquick.com/.",
    ...         None,
    ...     ),
    ...     (
    ...         no_priv,
    ...         "How do I play the Game of Life?",
    ...         "Keep breathing!",
    ...         "install",
    ...     ),
    ...     (
    ...         sample_person,
    ...         "Who really shot JFK?",
    ...         "You decide: there were at least six conspiracies going on "
    ...         "in Dallas on Nov 22nd 1963.",
    ...         None,
    ...     ),
    ...     (
    ...         no_priv,
    ...         "What were the famous last words?",
    ...         "Who turned off the light?",
    ...         None,
    ...     ),
    ... ]

    >>> from datetime import datetime, timedelta, timezone
    >>> now = datetime.now(timezone.utc)

    >>> faq_set = []
    >>> for owner, title, content, keywords in faq_specifications:
    ...     date = now + timedelta(minutes=len(faq_set))
    ...     faq_set.append(newFAQ(owner, title, content, keywords, date))
    ...

    >>> login(ANONYMOUS)


getFAQ()
--------

It is possible to retrieve a FAQ in a collection using its id by using
the getFAQ() method.

    >>> faq = faq_set[0]
    >>> collection.getFAQ(faq.id) == faq
    True

It returns None when there is FAQ with that ID in the context:

    >>> print(collection.getFAQ(12345))
    None

It also returns None when using the ID of a FAQ that isn't in the
requested collection:

    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> ubuntu != collection
    True

    >>> login("foo.bar@canonical.com")
    >>> foo_bar = getUtility(ILaunchBag).user
    >>> ubuntu_faq = ubuntu.newFAQ(
    ...     foo_bar,
    ...     "Ubuntu Installation HowTo",
    ...     "Ubuntu installation procedure can be found at: "
    ...     "https://help.ubuntu.com/community/Installation",
    ... )

    >>> login(ANONYMOUS)
    >>> print(collection.getFAQ(ubuntu_faq.id))
    None


searchFAQs
----------

The searchFAQs() method is used to select a set of FAQs in the
collection matching various criteria.

When no criteria are given, all the FAQs in the collection are returned.
(The default sort order is most recent first.)

    >>> for faq in collection.searchFAQs():
    ...     print(faq.title)
    ...
    What were the famous last words?
    Who really shot JFK?
    How do I play the Game of Life?
    How do I make money quickly off the Internet?
    What is The Meaning of Life?
    How do I install Foo?


search_text
...........

The first criterion is search_text. It will select FAQs matching the
keywords specified. Keywords are looked for in the title, content and
keywords field of the FAQ.

    >>> for faq in collection.searchFAQs(search_text="install"):
    ...     print(faq.title)
    ...
    How do I install Foo?
    How do I play the Game of Life?
    How do I make money quickly off the Internet?

By default, the results are sorted by relevancy. In the above example,
the first result is more relevant because the keyword appear in the
title, the second because it appears in the keywords.


owner
.....

The other filtering criterion is 'owner'. It will select only FAQs that
were created by the specified user.

    >>> for faq in collection.searchFAQs(owner=no_priv):
    ...     print(faq.title)
    ...
    What were the famous last words?
    How do I play the Game of Life?
    How do I install Foo?

Again, the default sort order is most recent first.


Combination
...........

You can combine multiple criteria. Only FAQs matching all the criteria
will be returned.

    >>> for faq in collection.searchFAQs(
    ...     search_text="install", owner=no_priv
    ... ):
    ...     print(faq.title)
    How do I install Foo?
    How do I play the Game of Life?


sort
....

The sort parameter can be used to control the sort order of the results.
It takes a value from the FAQSort enumerated type. For example, the
FAQSort.NEWEST_FIRST can be used to sort the results of a text search by
date of creation (most recent first):

    >>> from lp.answers.interfaces.faqcollection import FAQSort
    >>> for faq in collection.searchFAQs(
    ...     search_text="install", sort=FAQSort.NEWEST_FIRST
    ... ):
    ...     print(faq.title)
    How do I play the Game of Life?
    How do I make money quickly off the Internet?
    How do I install Foo?

The FAQSort.OLDEST_FIRST can be used to have the oldest FAQs sorted
first:

    >>> for faq in collection.searchFAQs(sort=FAQSort.OLDEST_FIRST):
    ...     print(faq.title)
    ...
    How do I install Foo?
    What is The Meaning of Life?
    How do I make money quickly off the Internet?
    How do I play the Game of Life?
    Who really shot JFK?
    What were the famous last words?
