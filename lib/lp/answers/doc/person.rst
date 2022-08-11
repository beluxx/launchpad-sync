=============================
People and the answer tracker
=============================

Sometimes you want to find out what questions a person is involved with.


Searching
=========

IQuestionsPerson defines a searchQuestions() method which is used to select
all, or a subset of, the questions in which a person is involved.  This
includes questions which the person created, is assigned to, is subscribed to,
commented on, or answered.  Various subsets can be selected by using the
various search criteria.

    >>> from lp.answers.interfaces.questionsperson import IQuestionsPerson
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> personset = getUtility(IPersonSet)
    >>> foo_bar_raw = personset.getByEmail('foo.bar@canonical.com')
    >>> foo_bar = IQuestionsPerson(foo_bar_raw)


Search text
-----------

The search_text parameter will limit the questions to those matching
the query using the regular full text algorithm.

    >>> for question in foo_bar.searchQuestions(search_text=u'firefox'):
    ...     print(question.title, question.status.title)
    Firefox loses focus and gets stuck              Open
    mailto: problem in webpage                      Solved
    Newly installed plug-in doesn't seem to be used Answered


Sorting
-------

When using the search_text criteria, the default is to sort the results by
relevancy.  One can use the sort parameter to change that.  It takes one of
the constant defined in the QuestionSort enumeration.

    >>> from lp.answers.enums import QuestionSort
    >>> for question in foo_bar.searchQuestions(
    ...     search_text=u'firefox', sort=QuestionSort.OLDEST_FIRST):
    ...     print(question.id, question.title, question.status.title)
    4 Firefox loses focus and gets stuck              Open
    6 Newly installed plug-in doesn't seem to be used Answered
    9 mailto: problem in webpage                      Solved

When no text search is done, the default sort order is newest first.

    >>> for question in foo_bar.searchQuestions():
    ...     print(question.id, question.title, question.status.title)
    11 Continue playing after shutdown                      Open
    10 Play DVDs in Totem                                   Answered
     9 mailto: problem in webpage                           Solved
     8 Installation of Java Runtime Environment for Mozilla Answered
     7 Slow system                                          Needs information
     6 Newly installed plug-in doesn't seem to be used      Answered
     4 Firefox loses focus and gets stuck                   Open


Status
------

As shown above, expired and invalid questions are not returned.  The status
parameter can be used to control the list of statuses to select.

    >>> from lp.answers.enums import QuestionStatus
    >>> for question in foo_bar.searchQuestions(
    ...         status=QuestionStatus.INVALID):
    ...     print(question.title, question.status.title)
    Firefox is slow and consumes too much RAM   Invalid

The status parameter can also take a list of statuses.

    >>> for question in foo_bar.searchQuestions(
    ...         status=(QuestionStatus.SOLVED, QuestionStatus.INVALID)):
    ...     print(question.title, question.status.title)
    mailto: problem in webpage                  Solved
    Firefox is slow and consumes too much RAM   Invalid


Participation
-------------

By default, any relationship between a person and a question is considered by
searchQuestions.  This can customized through the participation parameter.  It
takes one or a list of constants from the QuestionParticipation enumeration.

To select only questions on which the person commented, the
QuestionParticipation.COMMENTER is used.

    >>> from lp.answers.enums import QuestionParticipation
    >>> for question in foo_bar.searchQuestions(
    ...         participation=QuestionParticipation.COMMENTER, status=None):
    ...     print(question.title)
    Continue playing after shutdown
    Play DVDs in Totem
    mailto: problem in webpage
    Installation of Java Runtime Environment for Mozilla
    Newly installed plug-in doesn't seem to be used

QuestionParticipation.SUBSCRIBER will only select the questions to which the
person is subscribed.

    >>> for question in foo_bar.searchQuestions(
    ...         participation=QuestionParticipation.SUBSCRIBER, status=None):
    ...     print(question.title)
    Slow system
    Firefox is slow and consumes too much RAM

QuestionParticipation.OWNER selects the questions that the person created.

    >>> for question in foo_bar.searchQuestions(
    ...         participation=QuestionParticipation.OWNER, status=None):
    ...     print(question.title)
    Slow system
    Firefox loses focus and gets stuck
    Firefox is slow and consumes too much RAM

QuestionParticipation.ANSWERER selects the questions for which the person gave
an answer.

    >>> for question in foo_bar.searchQuestions(
    ...         participation=QuestionParticipation.ANSWERER, status=None):
    ...     print(question.title)
    mailto: problem in webpage
    Firefox is slow and consumes too much RAM

QuestionParticipation.ASSIGNEE selects that questions which are assigned to
the person.

    >>> list(foo_bar.searchQuestions(
    ...         participation=QuestionParticipation.ASSIGNEE, status=None))
    []

If a list of these constants is used, all of these participation types
will be selected.

    >>> for question in foo_bar.searchQuestions(
    ...         participation=(QuestionParticipation.OWNER,
    ...                        QuestionParticipation.ANSWERER),
    ...         status=None):
    ...     print(question.title)
    mailto: problem in webpage
    Slow system
    Firefox loses focus and gets stuck
    Firefox is slow and consumes too much RAM


Language
--------

By default, questions in all languages are included in the results.  It is
possible to filter questions by the language they were written in.  One or a
sequence of ILanguage object can be passed in to specify the language filter.

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> spanish = getUtility(ILanguageSet)['es']
    >>> english = getUtility(ILanguageSet)['en']

Foo bar doesn't have any questions written in Spanish.

    >>> list(foo_bar.searchQuestions(language=spanish))
    []

But Carlos has one.

    # Because not everyone uses a real editor <wink>
    >>> carlos_raw = personset.getByName('carlos')
    >>> carlos = IQuestionsPerson(carlos_raw)
    >>> for question in carlos.searchQuestions(
    ...         language=(english, spanish)):
    ...     print(question.title, question.language.code)
    Problema al recompilar kernel con soporte smp (doble-núcleo)    es


Questions needing attention
---------------------------

You can select only the questions that needs attention from a person.  This
includes questions owned by the person in the ANSWERED or NEEDSINFO state.  It
also includes questions on which the person requested more information or gave
an answer and are back in the OPEN state.

    >>> for question in foo_bar.searchQuestions(needs_attention=True):
    ...     print(question.status.title, question.owner.displayname,
    ...           question.title)
    Open              Sample Person Continue playing after shutdown
    Needs information Foo Bar       Slow system


Search combinations
-------------------

The results are the intersection of the sets delimited by each criteria.

    >>> for question in foo_bar.searchQuestions(
    ...         search_text=u'firefox OR Java',
    ...         status=QuestionStatus.ANSWERED,
    ...         participation=QuestionParticipation.COMMENTER):
    ...     print(question.title, question.status.title)
    Installation of Java Runtime Environment for Mozilla    Answered
    Newly installed plug-in doesn't seem to be used         Answered


Question languages
==================

IQuestionsPerson also defines a getQuestionLanguages() attribute which
contains the set of languages used by all of the questions in which this
person is involved.

    >>> print(', '.join(
    ...     sorted(language.code
    ...            for language in foo_bar.getQuestionLanguages())))
    en

This includes questions which the person owns, and questions that the user is
subscribed to...

    >>> from lp.answers.interfaces.questioncollection import IQuestionSet
    >>> pt_BR_question = getUtility(IQuestionSet).get(13)
    >>> login('foo.bar@canonical.com')
    >>> pt_BR_question.subscribe(foo_bar_raw)
    <lp.answers.model.questionsubscription.QuestionSubscription...>

    >>> print(', '.join(
    ...     sorted(language.code
    ...            for language in foo_bar.getQuestionLanguages())))
    en, pt_BR

...and questions for which they're the answerer...

    >>> es_question = getUtility(IQuestionSet).get(12)
    >>> es_question.reject(foo_bar_raw, 'Reject question.')
    <lp.answers.model.questionmessage.QuestionMessage...>

    >>> print(', '.join(
    ...     sorted(language.code
    ...            for language in foo_bar.getQuestionLanguages())))
    en, es, pt_BR

...as well as questions which are assigned to the user...

    >>> pt_BR_question.assignee = carlos_raw
    >>> print(', '.join(
    ...     sorted(language.code
    ...            for language in carlos.getQuestionLanguages())))
    es, pt_BR

...and questions on which the user commented.

    >>> en_question = getUtility(IQuestionSet).get(1)
    >>> login('carlos@canonical.com')
    >>> en_question.addComment(carlos_raw, 'A simple comment.')
    <lp.answers.model.questionmessage.QuestionMessage...>

    >>> print(', '.join(
    ...     sorted(language.code
    ...            for language in carlos.getQuestionLanguages())))
    en, es, pt_BR


Direct subscriptions
====================

IQuestionsPerson defines getDirectAnswerQuestionTargets that can be used to
retrieve a list of IQuestionTargets that a person subscribed themselves to
as an answer contact.

    >>> no_priv_raw = personset.getByName('no-priv')
    >>> no_priv = IQuestionsPerson(no_priv_raw)
    >>> no_priv.getDirectAnswerQuestionTargets()
    []

    >>> from lp.registry.interfaces.product import IProductSet
    >>> firefox = getUtility(IProductSet).getByName("firefox")

    # Answer contacts must speak a language
    >>> no_priv_raw.addLanguage(english)
    >>> firefox.addAnswerContact(no_priv_raw, no_priv_raw)
    True

    >>> for target in no_priv.getDirectAnswerQuestionTargets():
    ...    print(target.name)
    firefox


Indirect subscriptions
======================

IQuestionsPerson defines getTeamAnswerQuestionTargets that retrieves a list of
IQuestionTargets that the person is subscribed to indirectly as an answer
contact through their team membership.

    >>> landscape_team = personset.getByName("landscape-developers")
    >>> ignored = landscape_team.addMember(no_priv_raw, foo_bar_raw)
    >>> no_priv_raw.inTeam(landscape_team)
    True

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> landscape_team.addLanguage(english)
    >>> ubuntu.addAnswerContact(landscape_team, landscape_team.teamowner)
    True

    >>> print(', '.join(
    ...     sorted(target.name
    ...            for target in no_priv.getTeamAnswerQuestionTargets())))
    ubuntu

Indirect team membership is also taken in consideration.  For example, when
the Landscape Team joins the Translator Team, targets for which the Translator
team is an answer contact will be included in No Privileges Person's supported
IQuestionTargets.

    >>> translator_team = personset.getByName('ubuntu-translators')
    >>> no_priv_raw.inTeam(translator_team)
    False
    >>> ignored = translator_team.addMember(landscape_team, carlos_raw)

    # We need to accept the invitation sent by the addMember() call in
    # order to make landscape_team an actual member of translator_team.
    >>> login(landscape_team.teamowner.preferredemail.email)
    >>> landscape_team.acceptInvitationToBeMemberOf(
    ...     translator_team, comment='something')

    >>> no_priv_raw.hasParticipationEntryFor(translator_team)
    True
    >>> evolution_package = ubuntu.getSourcePackage('evolution')
    >>> login('carlos@test.com')
    >>> translator_team.addLanguage(english)
    >>> evolution_package.addAnswerContact(
    ...     translator_team, translator_team.teamowner)
    True
    >>> print(', '.join(
    ...     sorted(target.name
    ...            for target in no_priv.getTeamAnswerQuestionTargets())))
    evolution, ubuntu


Deactivated pillars
===================

Only valid IQuestionTargets are returned, ensuring that no deactivated pillars
are in the results.

If the Firefox project is deactivated, it is removed from the list of
supported projects.

    >>> login('foo.bar@canonical.com')

    # Unlink the source packages so the project can be deactivated.
    >>> from lp.testing import unlink_source_packages
    >>> unlink_source_packages(firefox)
    >>> firefox.active = False
    >>> sorted(target.name
    ...        for target in no_priv.getDirectAnswerQuestionTargets())
    []

When the Firefox project is reactivated, the answer contact relationship is
visible.  These relationships are persistent for cases where we only want is
deactivated for a short period.

    >>> firefox.active = True
    >>> print(', '.join(
    ...     sorted(target.name
    ...            for target in no_priv.getDirectAnswerQuestionTargets())))
    firefox
