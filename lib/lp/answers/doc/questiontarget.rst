=========================
IQuestionTarget interface
=========================

Launchpad includes an answer tracker.  Questions are associated to objects
implementing IQuestionTarget.

    # An IQuestionTarget object is made available to this test via the
    # 'target' variable by the test framework.  It won't have any questions
    # associated with it at the start of the test.  This is done because the
    # exact same test applies to all types of question targets: products,
    # distributions, and distribution source packages.
    #
    # Some parts of the IQuestionTarget interface are only accessible
    # to a registered user.
    >>> login('no-priv@canonical.com')

    >>> from zope.component import getUtility
    >>> from zope.interface.verify import verifyObject
    >>> from lp.answers.interfaces.questiontarget import IQuestionTarget

    >>> verifyObject(IQuestionTarget, target)
    True


New questions
=============

Questions are always owned by a registered user.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> sample_person = getUtility(IPersonSet).getByEmail(
    ...     'test@canonical.com')

The newQuestion() method is used to create a question that will be associated
with the target.  It takes as parameters the question's owner, title and
description.  It also takes an optional parameter 'datecreated' which defaults
to UTC_NOW.

    # Initialize 'now' to a known value.
    >>> from datetime import datetime, timedelta
    >>> from pytz import UTC
    >>> now = datetime.now(UTC)

    >>> question = target.newQuestion(sample_person, 'New question',
    ...     'Question description', datecreated=now)
    >>> print(question.title)
    New question
    >>> print(question.description)
    Question description
    >>> print(question.owner.displayname)
    Sample Person
    >>> question.datecreated == now
    True
    >>> question.datelastquery == now
    True

The created question starts in the 'Open' status and should have the owner
subscribed to the question.

    >>> print(question.status.title)
    Open

    >>> for subscription in question.subscriptions:
    ...     print(subscription.person.displayname)
    Sample Person

Questions can be written in any languages supported in Launchpad.  The
language of the request is available in the 'language' attribute.  By default,
requests are assumed to be written in English.

    >>> print(question.language.code)
    en

It is possible to create questions in another language than English, by
passing in the language that the question is written in.

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> french = getUtility(ILanguageSet)['fr']
    >>> question = target.newQuestion(
    ...     sample_person, "De l'aide S.V.P.",
    ...     "Pouvez-vous m'aider?", language=french,
    ...     datecreated=now + timedelta(seconds=30))
    >>> print(question.language.code)
    fr

Anonymous users cannot use newQuestion().

    >>> login(ANONYMOUS)
    >>> question = target.newQuestion(
    ...     sample_person, 'This will fail', 'Failed?')
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...


Retrieving questions
====================

The getQuestion() method is used to retrieve a question by id for a
particular target.

    >>> target.getQuestion(question.id) == question
    True

If you pass in a non-existent id or a question for a different target, the
method returns None.

    >>> print(target.getQuestion(2))
    None
    >>> print(target.getQuestion(12345))
    None


Searching for questions
=======================

    # Create new questions for the following tests.  Odd questions will be
    # owned by Foo Bar and even questions will be owned by Sample Person.
    >>> login('no-priv@canonical.com')
    >>> foo_bar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
    >>> questions = []
    >>> for num in range(5):
    ...     if num % 2:
    ...         owner = foo_bar
    ...     else:
    ...         owner = sample_person
    ...     description = ('Support request description%d.\n'
    ...         'This request index is %d.') % (num, num)
    ...     questions.append(target.newQuestion(
    ...         owner, 'Question title%d' % num, description,
    ...         datecreated=now+timedelta(minutes=num+1)))

    # For more variety, we will set the status of the last to INVALID and the
    # fourth one to ANSWERED.
    >>> login('foo.bar@canonical.com')
    >>> foo_bar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
    >>> message = questions[-1].reject(
    ...     foo_bar, 'Invalid question.', datecreated=now+timedelta(hours=1))
    >>> message = questions[3].giveAnswer(
    ...     sample_person, 'This is your answer.',
    ...     datecreated=now+timedelta(hours=1))

    # Also add a reply from the owner on the first of these.
    >>> login('test@canonical.com')
    >>> message = questions[0].giveInfo(
    ...     'I think I forgot something.', datecreated=now+timedelta(hours=4))

    # Create another one that will also have the word 'new' in its
    # description.
    >>> question = target.newQuestion(sample_person, 'Another question',
    ...     'Another new question that is actually very new.',
    ...     datecreated=now+timedelta(hours=1))
    >>> login(ANONYMOUS)

The searchQuestions() method is used to search for questions.


Search text
-----------

The search_text parameter will select the questions that contain the
passed in text.  The standard text searching algorithm is used; see
lib/lp/services/database/doc/textsearching.rst.

    >>> for t in target.searchQuestions(search_text=u'new'):
    ...     print(t.title)
    New question
    Another question

The results are sorted by relevancy.  In the last questions, 'New' appeared in
the description which makes it less relevant than when the word appears in the
title.


Status
------

The searchQuestions() method can also filter questions by status.

    >>> from lp.answers.enums import QuestionStatus
    >>> for t in target.searchQuestions(status=QuestionStatus.OPEN):
    ...     print(t.title)
    Another question
    Question title2
    Question title1
    Question title0
    De l'aide S.V.P.
    New question

In this previous example, because there is no sort text, the
default sort order is from newest to oldest.

    >>> for t in target.searchQuestions(status=QuestionStatus.INVALID):
    ...     print(t.title)
    Question title4

You can pass in a list of statuses, and you can also use the search_text and
status parameters at the same time.  This will search OPEN and INVALID
questions with the word 'index'.

    >>> for t in target.searchQuestions(
    ...     search_text=u'request index',
    ...     status=(QuestionStatus.OPEN, QuestionStatus.INVALID)):
    ...     print(t.title)
    Question title4
    Question title2
    Question title1
    Question title0


Sorting
-------

You can control the sort order by passing one of the constants defined in
QuestionSort.  Previously, we saw the NEWEST_FIRST and RELEVANCY sort order.

You can sort also from oldest to newest using the OLDEST_FIRST constant.

    >>> from lp.answers.enums import QuestionSort
    >>> for t in target.searchQuestions(search_text='new',
    ...                                 sort=QuestionSort.OLDEST_FIRST):
    ...     print(t.title)
    New question
    Another question

You can sort by status (the status order is OPEN, NEEDSINFO, ANSWERED, SOLVED,
EXPIRED, INVALID).  This also sorts from newest to oldest as a secondary key.
Here we use status=None to search for all statuses; by default INVALID and
EXPIRED questions are excluded.

    >>> for t in target.searchQuestions(search_text='request index',
    ...                                 status=None,
    ...                                 sort=QuestionSort.STATUS):
    ...     print(t.status.title, t.title)
    Open Question title2
    Open Question title1
    Open Question title0
    Answered Question title3
    Invalid Question title4

If there is no search_text and the requested sort order is RELEVANCY,
the questions will be sorted NEWEST_FIRST.

    # 'Question title4' is not shown in this case because it has INVALID as
    # its status.
    >>> for t in target.searchQuestions(sort=QuestionSort.RELEVANCY):
    ...     print(t.title)
    Another question
    Question title3
    Question title2
    Question title1
    Question title0
    De l'aide S.V.P.
    New question

The RECENT_OWNER_ACTIVITY sort order sorts first questions which recently
received a new message by their owner.  It effectively sorts descending on the
datelastquery attribute.

    # Question title0 sorts first because it has a message from its owner
    # after the others were created.
    >>> for t in target.searchQuestions(
    ...                             sort=QuestionSort.RECENT_OWNER_ACTIVITY):
    ...     print(t.title)
    Question title0
    Another question
    Question title3
    Question title2
    Question title1
    De l'aide S.V.P.
    New question


Owner
-----

You can find question owned by a particular user by using the owner parameter.

    >>> for t in target.searchQuestions(owner=foo_bar):
    ...     print(t.title)
    Question title3
    Question title1


Language
---------

The language criteria can be used to select only questions written in a
particular language.

    >>> english = getUtility(ILanguageSet)['en']
    >>> for t in target.searchQuestions(language=french):
    ...     print(t.title)
    De l'aide S.V.P.

    >>> for t in target.searchQuestions(language=(english, french)):
    ...     print(t.title)
    Another question
    Question title3
    Question title2
    Question title1
    Question title0
    De l'aide S.V.P.
    New question


Questions needing attention
---------------------------

You can search among the questions that need attention.  A question needs the
attention of a user if they own it and if it is in the NEEDSINFO or ANSWERED
state.  Questions on which the user gave an answer or requested for more
information, and that are back in the OPEN state, are also included.

    # One of Sample Person's question gets to need attention from Foo Bar.
    >>> login('foo.bar@canonical.com')
    >>> message = questions[0].requestInfo(
    ...     foo_bar, 'Do you have a clue?',
    ...     datecreated=now+timedelta(hours=1))

    >>> login('test@canonical.com')
    >>> message = questions[0].giveInfo(
    ...     'I do, now please help me.', datecreated=now+timedelta(hours=2))

    # Another one of Foo Bar's questions needs attention.
    >>> message = questions[1].requestInfo(
    ...     sample_person, 'And you, do you have a clue?',
    ...     datecreated=now+timedelta(hours=1))

    >>> login(ANONYMOUS)
    >>> for t in target.searchQuestions(needs_attention_from=foo_bar):
    ...     print(t.status.title, t.title, t.owner.displayname)
    Answered Question title3 Foo Bar
    Needs information Question title1 Foo Bar
    Open Question title0 Sample Person


Unsupported language
--------------------

The 'unsupported' criteria is used to select questions that are in a
language that is not spoken by any of the Support Contacts.

    >>> for t in target.searchQuestions(unsupported=True):
    ...     print(t.title)
    De l'aide S.V.P.


Finding similar questions
=========================

The method findSimilarQuestions() can be use to find questions similar to some
target text.  The questions don't have to contain all the words of the text.

    # This returns the same results as with the search 'new' because
    # all other words in the text are either common ('question', 'title') or
    # stop words ('with', 'a').
    >>> for t in target.findSimilarQuestions('new questions with a title'):
    ...     print(t.title)
    New question
    Another question



Answer contacts
===============

Targets can have answer contacts.  The list of answer contacts for a
target is available through the answer_contacts attribute.

    >>> list(target.answer_contacts)
    []

There is also a direct_answer_contacts which includes only the answer contacts
registered explicitly on the question target.  In general, this will be the
same as the answer_contacts attribute, but some IQuestionTarget
implementations may inherit answer contacts from other contexts.  In these
cases, the direct_answer_contacts attribute would only contain the answer
contacts defined in the current IQuestionTarget context.

    >>> list(target.direct_answer_contacts)
    []

You add an answer contact by using the addAnswerContact() method.  This
is only available to registered users.

    >>> name18 = getUtility(IPersonSet).getByName('name18')
    >>> target.addAnswerContact(name18, name18)
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

This method returns True when the contact was added the list and False when it
was already on the list.

    >>> login('no-priv@canonical.com')
    >>> target.addAnswerContact(name18, name18)
    True
    >>> people = [p.name for p in target.answer_contacts]
    >>> len(people)
    1
    >>> print(people[0])
    name18
    >>> people = [p.name for p in target.direct_answer_contacts]
    >>> len(people)
    1
    >>> print(people[0])
    name18
    >>> target.addAnswerContact(name18, name18)
    False

An answer contact must have at least one language among their preferred
languages.

    >>> sample_person = getUtility(IPersonSet).getByName('name12')
    >>> len(sample_person.languages)
    0
    >>> target.addAnswerContact(sample_person, sample_person)
    Traceback (most recent call last):
      ...
    lp.answers.errors.AddAnswerContactError: An answer contact must speak a
    language...

Answer contacts can be removed by using the removeAnswerContact() method.
Like its counterpart, it returns True when the answer contact was removed and
False when the person wasn't on the answer contact list.

    >>> target.removeAnswerContact(name18, name18)
    True
    >>> list(target.answer_contacts)
    []
    >>> list(target.direct_answer_contacts)
    []
    >>> target.removeAnswerContact(name18, name18)
    False

Only registered users can remove an answer contact.

    >>> login(ANONYMOUS)
    >>> target.removeAnswerContact(name18, name18)
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...


Supported languages
===================

The supported languages for a given IQuestionTarget are given by
getSupportedLanguages().  The supported languages of a question target include
all languages spoken by at least one of its answer contacts, with the
exception of all English variations since English is the assumed language for
support when there are no answer contacts.

    >>> codes = [lang.code for lang in target.getSupportedLanguages()]
    >>> len(codes)
    1
    >>> print(codes[0])
    en

    # Let's add some answer contacts which speak different languages.
    >>> login('carlos@canonical.com')
    >>> carlos = getUtility(IPersonSet).getByName('carlos')
    >>> for language in carlos.languages:
    ...     print(language.code)
    ca
    en
    es
    >>> target.addAnswerContact(carlos, carlos)
    True

While daf has en_GB as one of his preferred languages...

    >>> login('daf@canonical.com')
    >>> daf = getUtility(IPersonSet).getByName('daf')
    >>> for language in daf.languages:
    ...     print(language.code)
    en_GB
    ja
    cy
    >>> target.addAnswerContact(daf, daf)
    True

...en_GB is not included in the target's supported languages, because all
English variants are converted to English.

    >>> from operator import attrgetter
    >>> print(', '.join(
    ...     language.code
    ...     for language in sorted(target.getSupportedLanguages(),
    ...                            key=attrgetter('code'))))
    ca, cy, en, es, ja


Answer contacts for languages
=============================

getAnswerContactsForLanguage() method returns a list of answer contacts who
support the specified language in their preferred languages.  Daf is in the
list because he speaks an English variant, which is treated as English.

    >>> spanish = getUtility(ILanguageSet)['es']
    >>> answer_contacts = target.getAnswerContactsForLanguage(spanish)
    >>> for person in answer_contacts:
    ...     print(person.name)
    carlos

    >>> answer_contacts = target.getAnswerContactsForLanguage(english)
    >>> for person in sorted(answer_contacts, key=lambda person: person.name):
    ...     print(person.name)
    carlos
    daf


A question's languages
======================

The getQuestionLanguages() method returns the set of languages used by all
of the target's questions.

    >>> print(', '.join(
    ...     sorted(language.code
    ...            for language in target.getQuestionLanguages())))
    en, fr


Creating questions from bugs
============================

The target can create a question from a bug, and link that bug to the new
question.  The question's owner is the same as the bug's owner.  The question
title and description are taken from the bug.  The comments on the bug are
copied to the question.

    >>> from datetime import datetime
    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from pytz import UTC

    >>> now = datetime.now(UTC)
    >>> target = getUtility(IProductSet)['jokosher']
    >>> bug_params = CreateBugParams(
    ...     title="Print is broken", comment="blah blah blah",
    ...     owner=sample_person)
    >>> target_bug = target.createBug(bug_params)
    >>> bug_message = target_bug.newMessage(
    ...     owner=sample_person, subject="Opps, my mistake",
    ...     content="This is really a question.")

    >>> target_question = target.createQuestionFromBug(target_bug)

    >>> print(target_question.owner.displayname)
    Sample Person
    >>> print(target_question.title)
    Print is broken
    >>> print(target_question.description)
    blah blah blah
    >>> question_message = target_question.messages[-1]
    >>> print(question_message.text_contents)
    This is really a question.

    >>> for bug in target_question.bugs:
    ...     print(bug.title)
    Print is broken
    >>> print(target_question.messages[-1].text_contents)
    This is really a question.

The question's creation date is the same as the bug's creation date.  The
question's last response date has a current datetime stamp to indicate the
question is active.  The question janitor would otherwise mistake the
questions made from old bugs as old questions and would expire them.

    >>> target_question.datecreated == target_bug.datecreated
    True
    >>> target_question.datelastresponse > now
    True

The question language is always English because all bugs in Launchpad are
written in English.

    >>> print(target_question.language.code)
    en
