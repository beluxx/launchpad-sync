====================
Question collections
====================

The IQuestionSet utility is used to retrieve and search for questions no
matter which question target they were created for.

    >>> from lp.testing import verifyObject
    >>> from lp.answers.interfaces.questioncollection import IQuestionSet
    >>> question_set = getUtility(IQuestionSet)
    >>> verifyObject(IQuestionSet, question_set)
    True


Retrieving questions
====================

The get() method can be used to retrieve a question with a specific id.

    >>> question_one = question_set.get(1)
    >>> print(question_one.title)
    Firefox cannot render Bank Site

If no question exists, a default value is returned.

    >>> default = object()
    >>> question_nonexistant = question_set.get(123456, default=default)
    >>> question_nonexistant is default
    True

If no default value is given, None is returned.

    >>> print(question_set.get(123456))
    None


Searching questions
===================

The IQuestionSet interface defines a searchQuestions() method that is used to
search for questions defined in any question target.


Search text
-----------

The search_text parameter will return questions matching the query using the
regular full text algorithm.

    # Because not everyone uses a real editor <wink>
    >>> for question in question_set.searchQuestions(search_text=u'firefox'):
    ...     print(question.title, question.target.displayname)
    Problemas de Impressão no Firefox                Mozilla Firefox
    Firefox loses focus and gets stuck               Mozilla Firefox
    Firefox cannot render Bank Site                  Mozilla Firefox
    mailto: problem in webpage                       mozilla-firefox in Ubuntu
    Newly installed plug-in doesn't seem to be used  Mozilla Firefox
    Problem showing the SVG demo on W3C site         Mozilla Firefox
    عكس التغييرات غير المحفوظة للمستن؟               Ubuntu


Status
------

By default, expired and invalid questions are not searched for.  The status
parameter can be used to select the questions in the status you are interested
in.

    >>> from lp.answers.enums import QuestionStatus
    >>> for question in question_set.searchQuestions(
    ...         status=QuestionStatus.INVALID):
    ...     print(question.title, question.status.title,
    ...           question.target.displayname)
    Firefox is slow and consumes too ...   Invalid mozilla-firefox in Ubuntu

The status parameter can also take a list of statuses.

    >>> for question in question_set.searchQuestions(
    ...         status=[QuestionStatus.SOLVED, QuestionStatus.INVALID]):
    ...     print(question.title, question.status.title,
    ...           question.target.displayname)
    mailto: problem in webpage             Solved mozilla-firefox in Ubuntu
    Firefox is slow and consumes too ...   Invalid mozilla-firefox in Ubuntu


Language
--------

The language parameter can be used to select only questions written in a
particular language.

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> spanish = getUtility(ILanguageSet)['es']
    >>> for t in question_set.searchQuestions(language=spanish):
    ...     print(t.title)
    Problema al recompilar kernel con soporte smp (doble-núcleo)


Combinations
------------

The returned set of questions is the intersection of the sets delimited by
each criteria.

    >>> for question in question_set.searchQuestions(
    ...     search_text=u'firefox',
    ...     status=(QuestionStatus.OPEN, QuestionStatus.INVALID)):
    ...     print(question.title, question.status.title,
    ...           question.target.displayname)
    Problemas de Impressão no Firefox Open           Mozilla Firefox
    Firefox is slow and consumes too much ...        mozilla-firefox in Ubuntu
    Firefox loses focus and gets stuck Open          Mozilla Firefox
    Firefox cannot render Bank Site Open             Mozilla Firefox
    Problem showing the SVG demo on W3C site Open    Mozilla Firefox
    عكس التغييرات غير المحفوظة للمستن؟ Open          Ubuntu


Sort order
----------

When using the search_text criteria, the default is to sort the results by
relevancy.  One can use the sort parameter to change the order.  It takes one
of the constant defined in the QuestionSort enumeration.

    >>> from lp.answers.enums import QuestionSort
    >>> for question in question_set.searchQuestions(
    ...     search_text=u'firefox', sort=QuestionSort.OLDEST_FIRST):
    ...     print(question.id, question.title, question.target.displayname)
    14 عكس التغييرات غير المحفوظة للمستن؟               Ubuntu
    1 Firefox cannot render Bank Site                   Mozilla Firefox
    2 Problem showing the SVG demo on W3C site          Mozilla Firefox
    4 Firefox loses focus and gets stuck                Mozilla Firefox
    6 Newly installed plug-in doesn't seem to be used   Mozilla Firefox
    9 mailto: problem in webpage                    mozilla-firefox in Ubuntu
    13 Problemas de Impressão no Firefox                Mozilla Firefox

When no text search is done, the default sort order is by newest first.

    >>> for question in question_set.searchQuestions(
    ...         status=QuestionStatus.OPEN)[:5]:
    ...     print(question.id, question.title, question.target.displayname)
    13 Problemas de Impressão no Firefox                Mozilla Firefox
    12 Problema al recompilar kernel con soporte smp (doble-núcleo) Ubuntu
    11 Continue playing after shutdown                  Ubuntu
    5 Installation failed                               Ubuntu
    4 Firefox loses focus and gets stuck Mozilla        Firefox


Question languages
==================

The getQuestionLanguages() method returns the set of languages in which
questions are written in launchpad.

    >>> print(', '.join(
    ...     sorted(language.code
    ...            for language in question_set.getQuestionLanguages())))
    ar, en, es, pt_BR


Active projects
===============

Set Up
------

The test assume some database values have been set for usage enums, so first
we'll set those up.

    >>> import transaction
    >>> from lp.app.enums import ServiceUsage
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> inactive = factory.makeProduct()
    >>> login('admin@canonical.com')
    >>> firefox.answers_usage = ServiceUsage.LAUNCHPAD
    >>> ubuntu.answers_usage = ServiceUsage.LAUNCHPAD
    >>> inactive.answers_usage = ServiceUsage.LAUNCHPAD
    >>> inactive.active = False
    >>> transaction.commit()

This method can be used to retrieve the projects that are the most actively
using the Answer Tracker in the last 60 days.  By active, we mean that the
project is registered as officially using Answers and had some questions asked
in the period.  The projects are ordered by the number of questions asked
during the period.

Initially, no projects are returned.

    >>> list(question_set.getMostActiveProjects())
    []

Then some recent questions are created on a number of projects.

    >>> from lp.answers.testing import QuestionFactory
    >>> from lp.registry.interfaces.person import IPersonSet

    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> landscape = getUtility(IProductSet).getByName('landscape')
    >>> launchpad = getUtility(IProductSet).getByName('launchpad')
    >>> no_priv = getUtility(IPersonSet).getByName('no-priv')
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

    >>> login('no-priv@canonical.com')
    >>> QuestionFactory.createManyByProject((
    ...     ('ubuntu', 3),
    ...     ('firefox', 2),
    ...     ('landscape', 1),
    ...     (inactive.name, 5),
    ...     ))

A question is created just before the time limit on Launchpad.

    >>> from datetime import datetime, timedelta
    >>> from pytz import UTC
    >>> question = launchpad.newQuestion(
    ...     no_priv, 'Launchpad question', 'A question',
    ...     datecreated=datetime.now(UTC) - timedelta(days=61))
    >>> login(ANONYMOUS)

The method returns only projects which officially use the Answer Tracker.  The
order of the returned projects is based on the number of questions asked
during the period.

    >>> print(ubuntu.answers_usage.name)
    LAUNCHPAD
    >>> print(firefox.answers_usage.name)
    LAUNCHPAD
    >>> print(landscape.answers_usage.name)
    UNKNOWN
    >>> print(launchpad.answers_usage.name)
    LAUNCHPAD

    # Launchpad is not returned because the question was not asked in
    # the last 60 days.  Inactive projects are not returned either.
    >>> for project in question_set.getMostActiveProjects():
    ...     print(project.displayname)
    Ubuntu
    Mozilla Firefox


The method accepts an optional limit parameter limiting the number of
project returned:

    >>> for project in question_set.getMostActiveProjects(limit=1):
    ...     print(project.displayname)
    Ubuntu


Counting the open questions
===========================

getOpenQuestionCountByPackages() allow you to get the count of open questions
on a set of IDistributionSourcePackage packages.

    >>> question_set.getOpenQuestionCountByPackages([])
    {}

It returns the number of open questions for each given package.

    >>> ubuntu_evolution = ubuntu.getSourcePackage('evolution')
    >>> ubuntu_pmount = ubuntu.getSourcePackage('pmount')
    >>> debian = getUtility(IDistributionSet).getByName('debian')
    >>> debian_evolution = debian.getSourcePackage('evolution')
    >>> debian_pmount = debian.getSourcePackage('pmount')

    >>> login('foo.bar@canonical.com')
    >>> QuestionFactory.createManyByTarget(ubuntu_pmount, 4)
    [...]
    >>> QuestionFactory.createManyByTarget(debian_evolution, 3)
    [...]
    >>> open_question, closed_question = QuestionFactory.createManyByTarget(
    ...     ubuntu_evolution, 2)
    >>> closed_question.setStatus(
    ...     closed_question.owner, QuestionStatus.SOLVED, 'no comment')
    <lp.answers.model.questionmessage.QuestionMessage ...>

    >>> packages = (
    ...     ubuntu_evolution, ubuntu_pmount, debian_evolution, debian_pmount)
    >>> package_counts = question_set.getOpenQuestionCountByPackages(packages)
    >>> len(packages)
    4
    >>> for package in packages:
    ...     print("%s: %s" % (package.bugtargetname, package_counts[package]))
    evolution (Ubuntu): 1
    pmount (Ubuntu): 4
    evolution (Debian): 3
    pmount (Debian): 0
