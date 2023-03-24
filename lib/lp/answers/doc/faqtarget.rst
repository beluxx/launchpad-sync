IFAQTarget Interface
====================

The Launchpad Answer Tracker can be used to track answers to commonly
asked questions. Regular user questions can then be answered with a
referral to the FAQ document.

Pillars that can host a FAQ provides the IFAQTarget.

    >>> from zope.interface.verify import verifyObject
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.answers.interfaces.faqtarget import IFAQTarget

    # NB: this test is called multiple times with different values for
    # 'target', which is setup by the testing framework.  It can be a
    # product or a distribution.

    # removeSecurityProxy() is needed because some attributes are
    # protected.

    >>> verifyObject(IFAQTarget, removeSecurityProxy(target))
    True


newFAQ()
--------

The newFAQ() method is used to create a new IFAQ object on the target.

That method is only available to a user who has 'launchpad.Append' on
the target.

    >>> login("no-priv@canonical.com")
    >>> from lp.services.webapp.authorization import check_permission
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> check_permission("launchpad.Append", target)
    False

    >>> no_priv = getUtility(ILaunchBag).user
    >>> target.newFAQ(no_priv, "Title", "Summary", content="Content")
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

In practice, this means that only the project's owner (aka maintainer)
or one of its answer contacts is authorized to create a new FAQ.

    >>> old_owner = target.owner

    >>> removeSecurityProxy(target).owner = no_priv
    >>> from lp.services.webapp.authorization import clear_cache
    >>> clear_cache()  # Clear authorization cache for check_permission.
    >>> check_permission("launchpad.Append", target)
    True

    >>> removeSecurityProxy(target).owner = old_owner

    # An answer contact must have a preferred language registered.

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> no_priv.addLanguage(getUtility(ILanguageSet)["en"])
    >>> target.addAnswerContact(no_priv, no_priv)
    True

    >>> clear_cache()  # Clear authorization cache for check_permission.
    >>> check_permission("launchpad.Append", target)
    True

    >>> faq = target.newFAQ(no_priv, "Title", "Content")

The returned object provides the IFAQ interface:

    >>> from lp.answers.interfaces.faq import IFAQ
    >>> from lp.testing import admin_logged_in
    >>> with admin_logged_in():
    ...     verifyObject(IFAQ, faq)
    ...
    True

The newFAQ() requires an owner, title, and content parameter. It also
accepts an optional date_created attribute (which defaults to the
current time), and an optional keywords parameter used to initialize the
FAQ's keywords.

    >>> from datetime import datetime, timezone
    >>> now = datetime.now(timezone.utc)

    >>> faq = target.newFAQ(
    ...     no_priv,
    ...     "How to do something",
    ...     "Explain how to do something.",
    ...     keywords="documentation howto",
    ...     date_created=now,
    ... )

    >>> print(faq.owner.displayname)
    No Privileges Person

    >>> print(faq.title)
    How to do something

    >>> print(faq.content)
    Explain how to do something.

    >>> print(faq.keywords)
    documentation howto

    >>> faq.date_created == now
    True

The project where the FAQ was created is available through the target
attribute:

    >>> faq.target == target
    True


getFAQ()
--------

It is possible to retrieve the FAQ from its container when you know the
id of the FAQ by using the get() method.

    >>> target.getFAQ(faq.id) == faq
    True

It returns None when there is FAQ with that ID in the context:

    >>> print(target.getFAQ(12345))
    None

It also returns None when asking an ID for a FAQ that isn't in the
requested target:

    # Create a FAQ on Ubuntu.

    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> ubuntu != target
    True

    >>> login("foo.bar@canonical.com")
    >>> foo_bar = getUtility(ILaunchBag).user
    >>> ubuntu_faq = ubuntu.newFAQ(
    ...     foo_bar,
    ...     "Ubuntu Installation HowTo",
    ...     "Ubuntu installation procedure can be found at: "
    ...     "https://help.ubuntu.com/community/Installation",
    ... )

    >>> login("no-priv@canonical.com")
    >>> print(target.getFAQ(ubuntu_faq.id))
    None


findSimilarFAQs()
-----------------

The method findSimilarFAQs() can be use to find FAQ document that are
likely to answer a particular question. The question's summary or a
sentence describing the issue should be given in parameter. The FAQ's
title, summary, keywords and content can be the source of the match.

This method uses a "natural language" search algorithm (see
lib/lp/services/database/doc/textsearching.rst for the details) which ignore
common words and stop words.

    # Create more FAQs.

    >>> faq = target.newFAQ(
    ...     no_priv,
    ...     "How to answer a question",
    ...     "Description on how to use the Answer Tracker can be found at: "
    ...     "https://help.launchpad.net/AnswerTrackerDocumentation",
    ... )
    >>> faq = target.newFAQ(
    ...     no_priv,
    ...     "How to become a Launchpad king",
    ...     "The secret to achieve uber-karma is to answer questions using "
    ...     "the Launchpad Answer Tracker",
    ... )
    >>> faq = target.newFAQ(
    ...     no_priv,
    ...     "How to use bug mail",
    ...     "The syntax of bug mail commands is described at: "
    ...     "https://help.launchpad.net/BugTrackerEmailInterface",
    ... )

    >>> for faq in target.findSimilarFAQs("How do I use the Answer Tracker"):
    ...     print(faq.title)
    ...
    How to answer a question
    How to become a Launchpad king

The results are ordered by relevancy. The first document is considered
more relevant because 'Answer Tracker' appeared in the summary (they
appear in the content in the other document).

If there are no similar FAQ, no result should be returned:

    >>> for faq in target.findSimilarFAQs("How do I do this?"):
    ...     print(faq.title)
    ...

Since only common and stop words are in that summary, no similar FAQ
could be found.
