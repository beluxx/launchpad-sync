====================================
ProjectGroups and the answer tracker
====================================

Although question cannot be filed directly against project groups,
IProjectGroup in Launchpad also provides the IQuestionCollection and
ISearchableByQuestionOwner interfaces.

    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet
    >>> from lp.answers.interfaces.questioncollection import (
    ...     ISearchableByQuestionOwner,
    ...     IQuestionCollection,
    ... )

    >>> mozilla_project = getUtility(IProjectGroupSet).getByName("mozilla")
    >>> verifyObject(IQuestionCollection, mozilla_project)
    True
    >>> verifyObject(ISearchableByQuestionOwner, mozilla_project)
    True


Questions filed against project in a project group
==================================================

You can search for all questions filed against projects in a project using the
project group's searchQuestions() method.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet

    >>> login("test@canonical.com")
    >>> thunderbird = getUtility(IProductSet).getByName("thunderbird")
    >>> sample_person = getUtility(IPersonSet).getByName("name12")
    >>> question = thunderbird.newQuestion(
    ...     sample_person,
    ...     "SVG attachments aren't displayed ",
    ...     "It would be a nice feature if SVG attachments could be displayed"
    ...     " inlined.",
    ... )

    >>> for question in mozilla_project.searchQuestions(search_text="svg"):
    ...     print(question.title, question.target.displayname)
    ...
    SVG attachments aren't displayed            Mozilla Thunderbird
    Problem showing the SVG demo on W3C site    Mozilla Firefox

In the case where a project group has no projects, there are no results.

    >>> aaa_project = getUtility(IProjectGroupSet).getByName("aaa")
    >>> list(aaa_project.searchQuestions())
    []

Questions can be searched by all the standard searchQuestions() parameters.
See questiontarget.rst for the full details.

    >>> from lp.answers.enums import QuestionSort, QuestionStatus
    >>> for question in mozilla_project.searchQuestions(
    ...     owner=sample_person,
    ...     status=QuestionStatus.OPEN,
    ...     sort=QuestionSort.OLDEST_FIRST,
    ... ):
    ...     print(question.title, question.target.displayname)
    Problem showing the SVG demo on W3C site    Mozilla Firefox
    SVG attachments aren't displayed            Mozilla Thunderbird


Languages
=========

getQuestionLanguages() returns the set of languages that is used by all the
questions in the project group's projects.

    # The Firefox project group has one question created in Brazilian
    # Portuguese.
    >>> print(
    ...     ", ".join(
    ...         sorted(
    ...             language.code
    ...             for language in mozilla_project.getQuestionLanguages()
    ...         )
    ...     )
    ... )
    en, pt_BR

In the case where a project group has no projects, there are no results.

    >>> list(aaa_project.getQuestionLanguages())
    []
