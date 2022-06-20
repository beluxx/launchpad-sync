Working with Launchpad Answers over the API
===========================================

Users can work with question targets and questions over the api to
search and update questions. This demonstration will use a project, it's
contact, and asker, and three questions.

    >>> from zope.component import getUtility
    >>> from lp.testing.pages import webservice_for_person
    >>> from lp.services.webapp.interfaces import OAuthPermission
    >>> from lp.app.enums import ServiceUsage
    >>> from lp.registry.interfaces.person import TeamMembershipPolicy
    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> from lp.testing.sampledata import ADMIN_EMAIL
    >>> lang_set = getUtility(ILanguageSet)

    >>> login(ADMIN_EMAIL)
    >>> _contact = factory.makePerson(name='contact')
    >>> _project = factory.makeProduct(name='my-project', owner=_contact)
    >>> _contact.addLanguage(lang_set['en'])
    >>> _project.answers_usage = ServiceUsage.LAUNCHPAD
    >>> success = _project.addAnswerContact(_contact, _contact)
    >>> _team = factory.makeTeam(
    ...     owner=_contact,
    ...     name='my-team',
    ...     membership_policy=TeamMembershipPolicy.RESTRICTED)
    >>> _team_project = factory.makeProduct(name='team-project', owner=_team)
    >>> _asker = factory.makePerson(name='asker')
    >>> _question_1 = factory.makeQuestion(
    ...     target=_project, title="Q 1 great", owner=_asker)
    >>> _question_2 = factory.makeQuestion(
    ...     target=_project, title="Q 2 greater", owner=_asker)
    >>> _question_3 = factory.makeQuestion(
    ...     target=_team_project, title="Q 3 greatest", owner=_asker)
    >>> _message = _question_1.giveAnswer(_contact, 'This is the answer')
    >>> logout()

    >>> contact_webservice = webservice_for_person(
    ...     _contact, permission=OAuthPermission.WRITE_PUBLIC)


Answer contacts
---------------

Users can add or remove themselves as an answer contact for a project using
addAnswerContact and removeAnswerContact. The user must have a preferred
language. Scripts should call the canUserAlterAnswerContact method first to
verify that the person can changed.

    >>> project = contact_webservice.get(
    ...     '/my-project', api_version='devel').jsonBody()
    >>> contact = contact_webservice.get(
    ...     '/~contact', api_version='devel').jsonBody()
    >>> contact_webservice.named_get(
    ...     project['self_link'], 'canUserAlterAnswerContact',
    ...     person=contact['self_link'], api_version='devel').jsonBody()
    True

    >>> contact_webservice.named_post(
    ...     project['self_link'], 'removeAnswerContact',
    ...     person=contact['self_link'], api_version='devel').jsonBody()
    True

    >>> contact_webservice.named_post(
    ...     project['self_link'], 'addAnswerContact',
    ...     person=contact['self_link'], api_version='devel').jsonBody()
    True

Users can also make the teams they administer answer contacts using
addAnswerContact and removeAnswerContact if the team has a preferred language.

    >>> team = contact_webservice.get(
    ...     '/~my-team', api_version='devel').jsonBody()
    >>> team_project = contact_webservice.get(
    ...     '/team-project', api_version='devel').jsonBody()
    >>> contact_webservice.named_get(
    ...     team_project['self_link'], 'canUserAlterAnswerContact',
    ...     person=team['self_link'], api_version='devel').jsonBody()
    True

    >>> contact_webservice.named_post(
    ...     team['self_link'], 'addLanguage',
    ...     language='/+languages/fr', api_version='devel').jsonBody()
    >>> contact_webservice.named_post(
    ...     team_project['self_link'], 'addAnswerContact',
    ...     person=team['self_link'], api_version='devel').jsonBody()
    True

Anyone can get the collection of languages spoken by at least one
answer contact by calling getSupportedLanguages.

    >>> languages = anon_webservice.named_get(
    ...     team_project['self_link'], 'getSupportedLanguages',
    ...     api_version='devel').jsonBody()
    >>> print_self_link_of_entries(languages)
    http://.../+languages/en
    http://.../+languages/fr

Anyone can retrieve the collection of answer contacts for a language using
getAnswerContactsForLanguage.

    >>> english = anon_webservice.get(
    ...     '/+languages/en', api_version='devel').jsonBody()

    >>> contacts = anon_webservice.named_get(
    ...     project['self_link'], 'getAnswerContactsForLanguage',
    ...     language=english['self_link'], api_version='devel').jsonBody()
    >>> print_self_link_of_entries(contacts)
    http://.../~contact

Anyone can retrieve the collection of `IQuestionTarget`s that a person
is an answer contact for using getDirectAnswerQuestionTargets.

    >>> targets = anon_webservice.named_get(
    ...     contact['self_link'], 'getDirectAnswerQuestionTargets',
    ...     api_version='devel').jsonBody()
    >>> print_self_link_of_entries(targets)
    http://api.launchpad.test/devel/my-project

Anyone can retrieve the collection of `IQuestionTarget`s that a person's
teams is an answer contact for using getTeamAnswerQuestionTargets.

    >>> targets = anon_webservice.named_get(
    ...     contact['self_link'], 'getTeamAnswerQuestionTargets',
    ...     api_version='devel').jsonBody()
    >>> print_self_link_of_entries(targets)
    http://api.launchpad.test/devel/team-project


Question collections
--------------------

Anyone can retrieve a collection of questions from an `IQuestionTarget` with
searchQuestions. The question will that match the precise search criteria
called with searchQuestions.

    >>> questions = anon_webservice.named_get(
    ...     project['self_link'], 'searchQuestions',
    ...     search_text='q great',
    ...     status=['Open', 'Needs information', 'Answered'],
    ...     language=[english['self_link']],
    ...     sort='oldest first',
    ...     api_version='devel').jsonBody()
    >>> for question in questions['entries']:
    ...     print(question['title'])
    Q 1 great

    >>> print(questions['total_size'])
    1

Anyone can retrieve a collection of questions from an `IQuestionTarget` that
are similar to a phrase using findSimilarQuestions. A phrase one or more the
words that might appear in a question's title or description.
findSimilarQuestions uses natural language techniques to match the question.

    >>> questions = anon_webservice.named_get(
    ...     project['self_link'], 'findSimilarQuestions',
    ...     phrase='q great',
    ...     api_version='devel').jsonBody()
    >>> for question in questions['entries']:
    ...     print(question['title'])
    Q 1 great
    Q 2 greater

Anyone can retrieve a specific question from an `IQuestionTarget` calling
getQuestion with the question Id.

    >>> question_1 = anon_webservice.named_get(
    ...     project['self_link'], 'getQuestion', question_id=_question_1.id,
    ...     api_version='devel').jsonBody()
    >>> print(question_1['title'])
    Q 1 great


Anyone can retrieve a collection of questions from an `IPerson` with
searchQuestions. The question will that match the precise search criteria
called with searchQuestions.

    >>> questions = anon_webservice.named_get(
    ...     contact['self_link'], 'searchQuestions',
    ...     search_text='q great',
    ...     status=['Open', 'Needs information', 'Answered'],
    ...     language=[english['self_link']],
    ...     needs_attention=False,
    ...     sort='oldest first',
    ...     api_version='devel').jsonBody()
    >>> for question in questions['entries']:
    ...     print(question['title'])
    Q 1 great


A question
----------

A question has many exported attributes about the details of the question, its
state, the people involved, and the dates of important events. There is also
a link to retrieve the question's messages.

    >>> from lazr.restful.testing.webservice import pprint_entry
    >>> pprint_entry(question_1)
    answer_link: None
    answerer_link: None
    assignee_link: None
    date_created: '20...+00:00'
    date_due: None
    date_last_query: '20...+00:00'
    date_last_response: '20...+00:00'
    date_solved: None
    description: 'description...'
    id: ...
    language_link: 'http://api.launchpad.test/devel/+languages/en'
    messages_collection_link:
        'http://api.launchpad.test/devel/my-project/+question/.../messages'
    owner_link: 'http://api.launchpad.test/devel/~asker'
    resource_type_link: 'http://api.launchpad.test/devel/#question'
    self_link: 'http://api.launchpad.test/devel/my-project/+question/...'
    status: 'Answered'
    target_link: 'http://api.launchpad.test/devel/my-project'
    title: 'Q 1 great'
    web_link: 'http://answers.launchpad.test/my-project/+question/...'


Question messages
-----------------

An `IQuestionMessage` provides the IMessage fields and additional fields
that indicate how the message changed the question.

    >>> messages = anon_webservice.get(
    ...     question_1['messages_collection_link'],
    ...     api_version='devel').jsonBody()
    >>> pprint_entry(messages['entries'][0])
    action: 'Answer'
    bug_attachments_collection_link: '...'
    content: 'This is the answer'
    date_created: '20...+00:00'
    date_deleted: None
    date_last_edited: None
    index: 1
    new_status: 'Answered'
    owner_link: 'http://api.launchpad.test/devel/~contact'
    parent_link: None
    question_link: 'http://api.launchpad.test/devel/my-project/+question/...'
    resource_type_link: 'http://api.launchpad.test/devel/#question_message'
    revisions_collection_link: 'http://...'
    self_link:
        'http://api.launchpad.test/devel/my-project/+question/.../messages/1'
    subject: 'Re: Q 1 great'
    visible: True
    web_link:
        'http://answers.launchpad.test/my-project/+question/.../messages/1'
