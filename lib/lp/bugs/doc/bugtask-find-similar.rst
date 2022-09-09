Finding Similar Bugs
====================

The normal bug search requires all the specified keywords to be present
in the found bugs. This works quite well in general, but not when you
want to find bugs similar to a given bug summary when filing a new bug;
then the search is too restrictive.

To address this use case, IBugTask.findSimilar can be used, which uses
nl_phrase_search in order to construct a suitable search string.

It doesn't make much sense to find bugs similar to an empty string, so
no results will be returned.

    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> test_product = factory.makeProduct()
    >>> test_person = factory.makePerson()
    >>> similar_bugs = getUtility(IBugTaskSet).findSimilar(
    ...     test_person, "", product=test_product
    ... )
    >>> similar_bugs.count()
    0

Also, of course, if the given summary isn't similar to any other bugs,
no results are returned.


    >>> similar_bugs = getUtility(IBugTaskSet).findSimilar(
    ...     test_person, "nosimilarbugs", product=test_product
    ... )
    >>> similar_bugs.count()
    0

Now, let's enter a real bug summary, which doesn't match any other
exactly. We can see that it still manages to find a bug.

    >>> test_bug = factory.makeBug(
    ...     target=test_product, title="SVG doesn't work"
    ... )

    >>> similar_bugs = getUtility(IBugTaskSet).findSimilar(
    ...     test_person, "Can't display SVG", product=test_product
    ... )
    >>> for bugtask in similar_bugs:
    ...     print(bugtask.bug.title)
    ...
    SVG doesn't work


Above we specified that only bugs against test_product should be
searched. If we specify a different product, no bugs will be returned,
since no similar bugs are found there.

    >>> another_product = factory.makeProduct()
    >>> similar_bugs = getUtility(IBugTaskSet).findSimilar(
    ...     test_person, "Can't display SVG", product=another_product
    ... )
    >>> similar_bugs.count()
    0

We can also search for distribution bugs:

    >>> test_distroseries = factory.makeDistroSeries()
    >>> test_distro = test_distroseries.distribution
    >>> test_package = factory.makeSourcePackage(
    ...     distroseries=test_distroseries
    ... )
    >>> distro_bug_1 = factory.makeBug(
    ...     target=test_package.distribution_sourcepackage,
    ...     series=test_distroseries,
    ...     title="Nothing to do with cheese or sandwiches",
    ... )
    >>> distro_bug_2 = factory.makeBug(
    ...     target=test_package.distribution_sourcepackage,
    ...     series=test_distroseries,
    ...     title="A bug about sandwiches",
    ... )
    >>> distro_bug_2 = factory.makeBug(
    ...     target=test_package.distribution_sourcepackage,
    ...     series=test_distroseries,
    ...     title="This cheese sandwich should show up",
    ... )

    >>> similar_bugs = getUtility(IBugTaskSet).findSimilar(
    ...     test_person, "sandwiches", distribution=test_distro
    ... )
    >>> for bugtask in similar_bugs:
    ...     print(bugtask.bug.title)
    ...
    Nothing to do with cheese or sandwiches
    A bug about sandwiches
    This cheese sandwich should show up

As well as limiting it to a specific source package:

    >>> another_package = factory.makeSourcePackage(
    ...     distroseries=test_distroseries
    ... )
    >>> similar_bugs = getUtility(IBugTaskSet).findSimilar(
    ...     test_person,
    ...     "Any cheese sandwiches?",
    ...     distribution=test_distro,
    ...     sourcepackagename=another_package.sourcepackagename,
    ... )
    >>> similar_bugs.count()
    0


Private bugs
------------

Only bugs that the user has access to view will be searched. If we set
one of our distro bugs to private, and repeat the search as a user who
isn't allowed to view it, only the public bugs will show up.

    >>> login("test@canonical.com")
    >>> distro_bug_1.setPrivate(True, distro_bug_1.owner)
    True

    >>> another_user = factory.makePerson()
    >>> similar_bugs = getUtility(IBugTaskSet).findSimilar(
    ...     another_user, "sandwiches", distribution=test_distro
    ... )
    >>> for bugtask in similar_bugs:
    ...     print(bugtask.bug.title)
    ...
    A bug about sandwiches
    This cheese sandwich should show up

    >>> distro_bug_1.setPrivate(False, distro_bug_1.owner)
    True

Ordering of search results
--------------------------

Since the search uses OR to match bugs against the entered phrase, many
bugs will be returned by a search. Since we usually want to display only
a few potential duplicates to the user, it's important that the results
are ordered in a way that the bugs matching the phrase best are first in
the list.

When searching for similar bugs, the results are ordered by ranking the
results of the fulltext search on the Bug table, so bugs that have a
summary or description that match the phrase will be displayed first.

Due to the sample data assuming a way-to-wide search facility, this test
has been narrowed - see bug 612384.

    >>> similar_bugs = getUtility(IBugTaskSet).findSimilar(
    ...     test_person, "cheese sandwiches show", distribution=test_distro
    ... )
    >>> for bugtask in similar_bugs:
    ...     print(bugtask.bug.title)
    ...
    Nothing to do with cheese or sandwiches
    This cheese sandwich should show up

    >>> similar_bugs = getUtility(IBugTaskSet).findSimilar(
    ...     test_person, "Nothing sandwich", distribution=test_distro
    ... )
    >>> for bugtask in similar_bugs:
    ...     print(bugtask.bug.title)
    ...
    Nothing to do with cheese or sandwiches
    A bug about sandwiches
    This cheese sandwich should show up


Not returning the same bug
--------------------------

findSimilarBugs() does not include the bug of the bugtask upon which
it is invoked.

    >>> orig_bug = factory.makeBug(
    ...     title="So you walk into this restaurant",
    ...     owner=test_product.owner,
    ...     target=test_product,
    ... )

    >>> dupe_bug = factory.makeBug(
    ...     title="So you walk into this restaurant",
    ...     owner=test_product.owner,
    ...     target=test_product,
    ... )
    >>> dupe_bug.markAsDuplicate(orig_bug)

    >>> similar_bugs = orig_bug.default_bugtask.findSimilarBugs(
    ...     test_product.owner
    ... )
    >>> orig_bug in similar_bugs
    False
