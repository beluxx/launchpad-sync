Answer Tracker Pages
====================

Several views are used to handle the various operations on a question.

    >>> from zope.component import getMultiAdapter
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> question_three = ubuntu.getQuestion(3)
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> firefox_question = firefox.getQuestion(2)

    # The firefox_question doesn't have any subscribers, let's subscribe
    # the owner.

    >>> login("test@canonical.com")
    >>> firefox_question.subscribe(firefox_question.owner)
    <lp.answers.model.questionsubscription.QuestionSubscription...>


QuestionSubscriptionView
------------------------

This view is used to subscribe and unsubscribe from a question.
Subscription is done when the user click on the 'Subscribe' button.

Register an event listener that will print events it receives.

    >>> from lazr.lifecycle.interfaces import IObjectModifiedEvent
    >>> from lp.answers.interfaces.question import IQuestion
    >>> from lp.testing.fixture import ZopeEventHandlerFixture

    >>> def print_modified_event(object, event):
    ...     print(
    ...         "Received ObjectModifiedEvent: %s"
    ...         % (", ".join(sorted(event.edited_fields)))
    ...     )
    ...
    >>> question_event_listener = ZopeEventHandlerFixture(
    ...     print_modified_event, (IQuestion, IObjectModifiedEvent)
    ... )
    >>> question_event_listener.setUp()

    >>> view = create_initialized_view(question_three, name="+subscribe")
    >>> print(view.label)
    Subscribe to question

    >>> print(view.page_title)
    Subscription

    >>> form = {"subscribe": "Subscribe"}
    >>> view = create_initialized_view(
    ...     question_three, name="+subscribe", form=form
    ... )
    Received ObjectModifiedEvent: subscribers
    >>> question_three.isSubscribed(getUtility(ILaunchBag).user)
    True

A notification message is displayed and the view redirect to the
question view page.

    >>> for notice in view.request.notifications:
    ...     print(notice.message)
    ...
    You have subscribed to this question.

    >>> view.request.response.getHeader("Location")
    '.../+question/3'

Unsubscription works in a similar manner.

    >>> view = create_initialized_view(question_three, name="+subscribe")
    >>> print(view.label)
    Unsubscribe from question

    >>> form = {"subscribe": "Unsubscribe"}
    >>> view = create_initialized_view(
    ...     question_three, name="+subscribe", form=form
    ... )
    Received ObjectModifiedEvent: subscribers
    >>> question_three.isSubscribed(getUtility(ILaunchBag).user)
    False

    >>> for notice in view.request.notifications:
    ...     print(notice.message)
    ...
    You have unsubscribed from this question.

    >>> view.request.response.getHeader("Location")
    '.../+question/3'

    >>> question_event_listener.cleanUp()


QuestionWorkflowView
--------------------

QuestionWorkflowView is the view used to handle the comments submitted
by users on the question. The actions available on it always depends on
the current state of the question and the identify of the user viewing
the form.

    # Setup a harness to easily test the view.

    >>> from lp.answers.browser.question import QuestionWorkflowView
    >>> from lp.testing.deprecated import LaunchpadFormHarness
    >>> workflow_harness = LaunchpadFormHarness(
    ...     firefox_question, QuestionWorkflowView
    ... )

    # Let's define a helper method that will print the names of the
    # available actions.

    >>> def printAvailableActionNames(view):
    ...     names = [
    ...         action.__name__.split(".")[-1]
    ...         for action in view.actions
    ...         if action.available()
    ...     ]
    ...     for name in sorted(names):
    ...         print(name)
    ...

Unlogged-in users cannot post any comments on the question:

    >>> login(ANONYMOUS)
    >>> workflow_harness.submit("", {})
    >>> printAvailableActionNames(workflow_harness.view)

When question is in the OPEN state, the owner can comment, answer their
own question or provide more information.

    >>> login("test@canonical.com")
    >>> workflow_harness.submit("", {})
    >>> printAvailableActionNames(workflow_harness.view)
    comment giveinfo selfanswer

But when another user sees the question, they can comment, provide an
answer or request more information.

    >>> login("no-priv@canonical.com")
    >>> workflow_harness.submit("", {})
    >>> printAvailableActionNames(workflow_harness.view)
    answer comment requestinfo

When the other user requests for more information, a confirmation is
displayed, the question status is changed to NEEDSINFO and the user is
redirected back to the question page.

    >>> workflow_harness.submit(
    ...     "requestinfo",
    ...     {
    ...         "field.message": "Can you provide an example of an URL"
    ...         "displaying the problem?"
    ...     },
    ... )
    >>> for notification in workflow_harness.request.response.notifications:
    ...     print(notification.message)
    ...
    Thanks for your information request.

    >>> print(firefox_question.status.name)
    NEEDSINFO

    >>> workflow_harness.redirectionTarget()
    '.../+question/2'

The available actions for that other user are still comment, give an
answer or request more information:

    >>> printAvailableActionNames(workflow_harness.view)
    answer comment requestinfo

And the question owner still has the same possibilities as at first:

    >>> login("test@canonical.com")
    >>> workflow_harness.submit("", {})
    >>> printAvailableActionNames(workflow_harness.view)
    comment giveinfo selfanswer

If they reply with the requested information, the question is moved back
to the OPEN state.

    >>> form = {
    ...     "field.message": "The following SVG doesn't display properly:"
    ...     "\nhttp://www.w3.org/2001/08/rdfweb/rdfweb-chaals-and-dan.svg"
    ... }
    >>> workflow_harness.submit("giveinfo", form)
    >>> for notification in workflow_harness.request.response.notifications:
    ...     print(notification.message)
    ...
    Thanks for adding more information to your question.

    >>> print(firefox_question.status.name)
    OPEN

    >>> workflow_harness.redirectionTarget()
    '.../+question/2'

The other user can come back and gives an answer:

    >>> login("no-priv@canonical.com")
    >>> workflow_harness.submit(
    ...     "answer",
    ...     {
    ...         "field.message": "New version of the firefox package are "
    ...         "available with SVG support enabled. Using apt "
    ...         "you should be able to upgrade."
    ...     },
    ... )
    >>> for notification in workflow_harness.request.response.notifications:
    ...     print(notification.message)
    ...
    Thanks for your answer.

    >>> print(firefox_question.status.name)
    ANSWERED

    >>> workflow_harness.redirectionTarget()
    '.../+question/2'

Once the question is answered, the set of possible actions for the
question owner changes. They can now either comment, confirm the answer,
answer the problem themselves, or reopen the request because that answer
isn't working.

    >>> login("test@canonical.com")
    >>> workflow_harness.submit("", {})
    >>> printAvailableActionNames(workflow_harness.view)
    comment confirm reopen selfanswer

Let's say they confirm the previous answer, in this case, the question
will move to the 'SOLVED' state. Note that the UI doesn't enable the
user to enter a confirmation message at that stage.

    >>> answer_message_number = len(firefox_question.messages) - 1
    >>> workflow_harness.submit(
    ...     "confirm",
    ...     {"answer_id": answer_message_number, "field.message": ""},
    ... )
    >>> for notification in workflow_harness.request.response.notifications:
    ...     print(notification.message)
    ...
    Thanks for your feedback.

    >>> print(firefox_question.status.name)
    SOLVED

    >>> workflow_harness.redirectionTarget()
    '.../+question/2'

Since no confirmation message was given, a default one was used.

    >>> print(firefox_question.messages[-1].text_contents)
    Thanks No Privileges Person, that solved my question.

Once in the SOLVED state, when the answerer is a person other than the
question owner, the owner can now only either add a comment or reopen
the question:

    >>> printAvailableActionNames(workflow_harness.view)
    comment reopen

Adding a comment doesn't change the status:

    >>> workflow_harness.submit(
    ...     "comment",
    ...     {
    ...         "field.message": "The example now displays "
    ...         "correctly. Thanks."
    ...     },
    ... )
    >>> for notification in workflow_harness.request.response.notifications:
    ...     print(notification.message)
    ...
    Thanks for your comment.

    >>> workflow_harness.redirectionTarget()
    '.../+question/2'

    >>> print(firefox_question.status.name)
    SOLVED

And the other user can only comment on the question:

    >>> login("no-priv@canonical.com")
    >>> workflow_harness.submit("", {})
    >>> printAvailableActionNames(workflow_harness.view)
    comment

If the question owner reopens the question, its status is changed back
to 'OPEN'.

    >>> login("test@canonical.com")
    >>> workflow_harness.submit(
    ...     "reopen",
    ...     {
    ...         "field.message": "Actually, there are still SVG "
    ...         "that do not display correctly. For example, the following "
    ...         "http://people.w3.org/maxf/ChessGML/immortal.svg doesn't "
    ...         "display correctly."
    ...     },
    ... )
    >>> for notification in workflow_harness.request.response.notifications:
    ...     print(notification.message)
    ...
    Your question was reopened.

    >>> print(firefox_question.status.name)
    OPEN

    >>> workflow_harness.redirectionTarget()
    '.../+question/2'

When the question owner answers their own question, it is moved straight
to the SOLVED state. The question owner is attributed as the answerer,
but no answer message is assigned to the answer.

    >>> workflow_harness.submit(
    ...     "selfanswer",
    ...     {
    ...         "field.message": "OK, this example requires some "
    ...         "SVG features that will only be available in Firefox 2.0."
    ...     },
    ... )
    >>> for notification in workflow_harness.request.response.notifications:
    ...     print(notification.message)
    ...
    Your question is solved. If a particular message helped you solve the
    problem, use the <em>'This solved my problem'</em> button.

    >>> print(firefox_question.status.name)
    SOLVED

    >>> print(firefox_question.answerer.displayname)
    Sample Person

    >>> firefox_question.answer is None
    True

    >>> workflow_harness.redirectionTarget()
    '.../+question/2'

When the answerer is the question owner, the owner can still confirm an
answer, in addition to adding a comment or reopening the question. This
path permits the question owner to state how the problem was solved,
then attribute an answerer as a contributor to the solution. The
answerer's message is attributed as the answer in this case.

    >>> printAvailableActionNames(workflow_harness.view)
    comment confirm reopen

    >>> workflow_harness.submit(
    ...     "confirm",
    ...     {"answer_id": answer_message_number, "field.message": ""},
    ... )
    >>> print(firefox_question.status.name)
    SOLVED

    >>> print(firefox_question.answerer.displayname)
    No Privileges Person

    >>> print(firefox_question.answer.owner.displayname)
    No Privileges Person

    >>> answer_id = firefox_question.messages[answer_message_number].id
    >>> firefox_question.answer.id == answer_id
    True

    >>> workflow_harness.redirectionTarget()
    '.../+question/2'


QuestionMakeBugView
-------------------

The QuestionMakeBugView is used to handle the creation of a bug from a
question. In addition to creating a bug, this operation will also link
the bug to the question.

    >>> login("foo.bar@canonical.com")
    >>> request = LaunchpadTestRequest(
    ...     form={
    ...         "field.actions.create": "Create",
    ...         "field.title": "Bug title",
    ...         "field.description": "Bug description.",
    ...     }
    ... )
    >>> request.method = "POST"
    >>> makebug = getMultiAdapter((question_three, request), name="+makebug")
    >>> question_three.bugs
    []

    >>> makebug.initialize()
    >>> print(question_three.bugs[0].title)
    Bug title

    >>> print(question_three.bugs[0].description)
    Bug description.

    >>> print(makebug.user.name)
    name16

    >>> question_three.bugs[0].isSubscribed(makebug.user)
    True

    >>> new_bug_id = int(question_three.bugs[0].id)
    >>> message = [n.message for n in request.notifications]
    >>> for m in message:
    ...     print(m)
    ...
    Thank you! Bug #... created.

    >>> "Bug #%s created." % new_bug_id in message[0]
    True

If the question already has bugs linked to it, no new bug can be
created.

    >>> request = LaunchpadTestRequest(
    ...     form={"field.actions.create": "create"}
    ... )
    >>> request.method = "POST"
    >>> makebug = getMultiAdapter((question_three, request), name="+makebug")
    >>> makebug.initialize()
    >>> for n in request.notifications:
    ...     print(n.message)
    ...
    You cannot create a bug report...


BugLinkView and BugsUnlinkView
------------------------------

Linking bug (+linkbug) to the question is managed through the
BugLinkView. Unlinking bugs from the question is managed through the
BugsUnlinkView. See 'buglinktarget-pages.rst' for their documentation.
The notifications sent along linking and unlinking bugs can be found in
'answer-tracker-notifications.rst'.


QuestionRejectView
------------------

That view is used by administrator and answer contacts to reject a
question.

    >>> login("foo.bar@canonical.com")
    >>> request = LaunchpadTestRequest(
    ...     form={
    ...         "field.actions.reject": "Reject",
    ...         "field.message": "Rejecting for the fun of it.",
    ...     }
    ... )
    >>> request.method = "POST"
    >>> view = getMultiAdapter((firefox_question, request), name="+reject")
    >>> view.initialize()
    >>> for notice in request.notifications:
    ...     print(notice.message)
    ...
    You have rejected this question.

    >>> print(firefox_question.status.title)
    Invalid


QuestionChangeStatusView
------------------------

QuestionChangeStatusView is used by administrator to change the status
outside of the comment workflow.

    >>> request = LaunchpadTestRequest(
    ...     form={
    ...         "field.actions.change-status": "Change Status",
    ...         "field.status": "SOLVED",
    ...         "field.message": "Previous rejection was an error.",
    ...     }
    ... )
    >>> request.method = "POST"
    >>> view = getMultiAdapter(
    ...     (firefox_question, request), name="+change-status"
    ... )
    >>> view.initialize()
    >>> for notice in request.notifications:
    ...     print(notice.message)
    ...
    Question status updated.

    >>> print(firefox_question.status.title)
    Solved


QuestionEditView
----------------

QuestionEditView available through '+edit' is used to edit most question
fields. It can be used to edit the question title and description and
also its metadata like language, assignee, distribution, source package,
product and whiteboard.

    >>> login("test@canonical.com")
    >>> request = LaunchpadTestRequest(
    ...     form={
    ...         "field.actions.change": "Continue",
    ...         "field.title": "Better Title",
    ...         "field.language": "en",
    ...         "field.description": "A better description.",
    ...         "field.target": "package",
    ...         "field.target.distribution": "ubuntu",
    ...         "field.target.package": "mozilla-firefox",
    ...         "field.assignee": "name16",
    ...         "field.whiteboard": "Some note",
    ...     }
    ... )
    >>> request.method = "POST"

    >>> view = getMultiAdapter((question_three, request), name="+edit")
    >>> view.initialize()
    >>> print(question_three.distribution.name)
    ubuntu

    >>> print(question_three.sourcepackagename.name)
    mozilla-firefox

    >>> print(question_three.product)
    None

Since a user must have launchpad.Edit (question creator or target answer
contact) to change the title or description, launchpad.Append (target
answer contact) to change the assignee and launchpad.Admin (target
owner) to change status whiteboard, the values are unchanged.

    >>> print(question_three.title)
    Firefox is slow and consumes too much RAM

    >>> print(question_three.description)
    I'm running on a 486 with 32 MB ram. And Firefox is slow! What should I
    do?

    >>> question_three.assignee is None
    True

    >>> question_three.whiteboard is None
    True

If the user has the required permission, the assignee and whiteboard
fields will be updated:

    >>> login("foo.bar@canonical.com")
    >>> request = LaunchpadTestRequest(
    ...     form={
    ...         "field.actions.change": "Continue",
    ...         "field.language": "en",
    ...         "field.title": "Better Title",
    ...         "field.description": "A better description.",
    ...         "field.target": "package",
    ...         "field.target.distribution": "ubuntu",
    ...         "field.target.package": "mozilla-firefox",
    ...         "field.assignee": "name16",
    ...         "field.whiteboard": "Some note",
    ...     }
    ... )
    >>> request.method = "POST"
    >>> view = getMultiAdapter((question_three, request), name="+edit")
    >>> view.initialize()
    >>> print(question_three.title)
    Better Title

    >>> print(question_three.description)
    A better description.

    >>> print(question_three.assignee.displayname)
    Foo Bar

    >>> print(question_three.whiteboard)
    Some note

The question language can be set to any language registered with
Launchpad--it is not restricted to the user's preferred languages.

    >>> view = create_initialized_view(question_three, name="+edit")
    >>> view.widgets["language"].vocabulary
    <lp.services.worlddata.vocabularies.LanguageVocabulary ...>

In a similar manner, the sourcepackagename field can only be updated on
a distribution question:

    >>> request = LaunchpadTestRequest(
    ...     form={
    ...         "field.actions.change": "Continue",
    ...         "field.language": "en",
    ...         "field.title": "Better Title",
    ...         "field.description": "A better description.",
    ...         "field.target": "product",
    ...         "field.target.distribution": "",
    ...         "field.target.package": "mozilla-firefox",
    ...         "field.target.product": "firefox",
    ...         "field.assignee": "",
    ...         "field.whiteboard": "",
    ...     }
    ... )
    >>> request.method = "POST"
    >>> view = getMultiAdapter((question_three, request), name="+edit")
    >>> view.initialize()
    >>> view.errors
    []

    >>> question_three.sourcepackagename is None
    True

    >>> print(question_three.distribution)
    None

    >>> print(question_three.sourcepackagename)
    None

    >>> print(question_three.product.name)
    firefox

    # Reassign back the question to ubuntu

    >>> question_three.target = ubuntu


The QuestionLanguage vocabulary
-------------------------------

The QuestionLanguageVocabularyFactory is an IContextSourceBinder which
is used in browser forms to create a vocabulary containing only the
languages that are likely to interest the user.

When the user has not configured their preferred languages, the vocabulary
will contain languages from the HTTP request, or the most likely
interesting languages based on GeoIP information.

For example, if the user doesn't log in, their browser is configured to
accept Brazilian Portuguese, and their request appears to come from a South
African IP address, the vocabulary will contain the languages spoken in
South Africa.

    >>> from operator import attrgetter

    >>> login(ANONYMOUS)
    >>> request = LaunchpadTestRequest(
    ...     HTTP_ACCEPT_LANGUAGE="pt_BR", REMOTE_ADDR="196.36.161.227"
    ... )
    >>> from lp.answers.browser.question import (
    ...     QuestionLanguageVocabularyFactory,
    ... )
    >>> view = getMultiAdapter((firefox, request), name="+addticket")
    >>> vocab = QuestionLanguageVocabularyFactory(view)(None)
    >>> languages = [term.value for term in vocab]
    >>> for lang in sorted(languages, key=attrgetter("code")):
    ...     print(lang.code)
    ...
    af
    en
    pt_BR
    st
    xh
    zu

If the user logs in but didn't configure their preferred languages, the
same logic is used to find the languages:

    >>> login("test@canonical.com")
    >>> user = getUtility(ILaunchBag).user
    >>> len(user.languages)
    0

    >>> vocab = QuestionLanguageVocabularyFactory(view)(None)
    >>> languages = [term.value for term in vocab]
    >>> for lang in sorted(languages, key=attrgetter("code")):
    ...     print(lang.code)
    ...
    af
    en
    pt_BR
    st
    xh
    zu

But if the user configured their preferred languages, only these are used:

    >>> login("carlos@canonical.com")
    >>> user = getUtility(ILaunchBag).user
    >>> for lang in sorted(user.languages, key=attrgetter("code")):
    ...     print(lang.code)
    ...
    ca
    en
    es

    >>> vocab = QuestionLanguageVocabularyFactory(view)(None)
    >>> languages = [term.value for term in vocab]
    >>> for lang in sorted(languages, key=attrgetter("code")):
    ...     print(lang.code)
    ...
    ca
    en
    es

Note that all variants of English are always excluded from the
vocabulary (since we don't want to confuse people by providing multiple
English options).

Daf has en_GB listed among his languages:

    >>> login("daf@canonical.com")
    >>> user = getUtility(ILaunchBag).user
    >>> for lang in sorted(user.languages, key=attrgetter("code")):
    ...     print(lang.code)
    ...
    cy
    en_GB
    ja

But the vocabulary made from this languages has substituted the English
variant with English:

    >>> vocab = QuestionLanguageVocabularyFactory(view)(None)
    >>> languages = [term.value for term in vocab]
    >>> for lang in sorted(languages, key=attrgetter("code")):
    ...     print(lang.code)
    ...
    cy
    en
    ja

Note also that the vocabulary will always contain the current question's
language in the vocabulary, even if this language would not be selected
by the previous rules.

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> afar = getUtility(ILanguageSet)["aa_DJ"]
    >>> question_three.language = afar
    >>> vocab = QuestionLanguageVocabularyFactory(view)(question_three)
    >>> afar in vocab
    True

    # Clean up.

    >>> question_three.language = getUtility(ILanguageSet)["en"]


UserSupportLanguagesMixin
-------------------------

The UserSupportLanguagesMixin can be used by views that needs to
retrieve the set of languages in which the user is assumed to be
interested.

    >>> from lp.answers.browser.questiontarget import (
    ...     UserSupportLanguagesMixin,
    ... )
    >>> from lp.services.webapp import LaunchpadView

    >>> class UserSupportLanguagesView(
    ...     UserSupportLanguagesMixin, LaunchpadView
    ... ):
    ...     """View to test UserSupportLanguagesMixin."""

The set of languages to use for support is defined in the
'user_support_languages' attribute.

Like all operations involving languages in the Answer Tracker, we ignore
all other English variants.

When the user is not logged in, or didn't define their preferred
languages, the set will be initialized from the request. That's the
languages configured in the browser, plus other inferred from the GeoIP
database.

    >>> request = LaunchpadTestRequest(
    ...     HTTP_ACCEPT_LANGUAGE="fr, en_CA", REMOTE_ADDR="196.36.161.227"
    ... )

    >>> login(ANONYMOUS)
    >>> view = UserSupportLanguagesView(None, request)

For this request, the set of support languages contains French (from the
request), and the languages spoken in South Africa (inferred from the
GeoIP location of the request).

    >>> for language in sorted(
    ...     view.user_support_languages, key=attrgetter("code")
    ... ):
    ...     print(language.code)
    af
    en
    fr
    st
    xh
    zu

Same thing if the logged in user didn't have any preferred languages
set:

    >>> login("test@canonical.com")
    >>> view = UserSupportLanguagesView(None, request)
    >>> for language in sorted(
    ...     view.user_support_languages, key=attrgetter("code")
    ... ):
    ...     print(language.code)
    af
    en
    fr
    st
    xh
    zu

But when the user has some preferred languages set, these will be used
instead of the ones inferred from the request:

    >>> login("carlos@canonical.com")
    >>> view = UserSupportLanguagesView(None, request)
    >>> for language in sorted(
    ...     view.user_support_languages, key=attrgetter("code")
    ... ):
    ...     print(language.code)
    ca
    en
    es

English variants included in the user's preferred languages are
excluded:

    >>> login("daf@canonical.com")
    >>> view = UserSupportLanguagesView(None, request)
    >>> for language in sorted(
    ...     view.user_support_languages, key=attrgetter("code")
    ... ):
    ...     print(language.code)
    cy
    en
    ja


SearchQuestionsView
-------------------

This view is used as a base class to search for questions. It is
intended to be easily customizable to offer more specific reports, while
keeping those searchable.

    # Define a subclass to demonstrate the customizability of the base
    # view.

    >>> from lp.answers.browser.questiontarget import SearchQuestionsView
    >>> class MyCustomSearchQuestionsView(SearchQuestionsView):
    ...     default_filter = {}
    ...
    ...     def getDefaultFilter(self):
    ...         return dict(**self.default_filter)
    ...

    >>> search_view_harness = LaunchpadFormHarness(
    ...     ubuntu, MyCustomSearchQuestionsView
    ... )

By default, that class provides widgets to search by text and by status.

    >>> search_view = search_view_harness.view
    >>> search_view.widgets.get("search_text") is not None
    True

    >>> search_view.widgets.get("language") is not None
    True

    >>> search_view.widgets.get("status") is not None
    True

It also includes a widget to select the sort order.

    >>> search_view.widgets.get("sort") is not None
    True

The questions matching the search are available by using the
searchResults() method. The returned results are batched.

    >>> questions = search_view.searchResults()
    >>> questions
    <lp.services.webapp.batching.BatchNavigator ...>

    >>> for question in questions.batch:
    ...     print(backslashreplace(question.title))
    ...
    Problema al recompilar kernel con soporte smp (doble-n\xfacleo)
    Continue playing after shutdown
    Play DVDs in Totem
    mailto: problem in webpage
    Installation of Java Runtime Environment for Mozilla

These were the default results when no search is entered. The user can
tweak the search and filter the results:

    >>> search_view_harness.submit(
    ...     "search",
    ...     {
    ...         "field.status": ["SOLVED", "OPEN"],
    ...         "field.search_text": "firefox",
    ...         "field.language": ["en"],
    ...         "field.sort": "by relevancy",
    ...     },
    ... )
    >>> search_view = search_view_harness.view
    >>> questions = search_view.searchResults()
    >>> for question in questions.batch:
    ...     print(question.title, question.status.title)
    ...
    mailto: problem in webpage Solved

Specific views can provide a default filter by returning the default
search parameters to use in the getDefaultFilter() method:

    >>> from lp.answers.enums import QuestionStatus
    >>> MyCustomSearchQuestionsView.default_filter = {
    ...     "status": [QuestionStatus.SOLVED, QuestionStatus.INVALID],
    ...     "language": search_view.user_support_languages,
    ... }
    >>> search_view_harness.submit("", {})

In this example, only the solved and invalid questions are listed by
default.

    >>> search_view = search_view_harness.view
    >>> questions = search_view.searchResults()
    >>> for question in questions.batch:
    ...     print(question.title)
    ...
    mailto: problem in webpage
    Better Title

The status widget displays the default criteria used:

    >>> for status in search_view.widgets["status"]._getFormValue():
    ...     print(status.title)
    ...
    Solved
    Invalid

The user selected search parameters will override these default
criteria.

    >>> search_view_harness.submit(
    ...     "search",
    ...     {
    ...         "field.status": ["SOLVED"],
    ...         "field.search_text": "firefox",
    ...         "field.language": ["en"],
    ...         "field.sort": "by relevancy",
    ...     },
    ... )
    >>> search_view = search_view_harness.view
    >>> questions = search_view.searchResults()
    >>> for question in questions.batch:
    ...     print(question.title)
    ...
    mailto: problem in webpage

    >>> for status in search_view.widgets["status"]._getFormValue():
    ...     print(status.title)
    ...
    Solved

The base view computes the page heading and the message displayed when
no results are found based on the selected search filter:

    >>> from zope.i18n import translate
    >>> search_view_harness.submit("", {})
    >>> print(translate(search_view_harness.view.page_title))
    Questions for Ubuntu

    >>> print(translate(search_view_harness.view.empty_listing_message))
    There are no questions for Ubuntu with the requested statuses.

    >>> MyCustomSearchQuestionsView.default_filter = dict(
    ...     status=[QuestionStatus.OPEN], search_text="Firefox"
    ... )
    >>> search_view_harness.submit("", {})
    >>> print(translate(search_view_harness.view.page_title))
    Open questions matching "Firefox" for Ubuntu

    >>> print(translate(search_view_harness.view.empty_listing_message))
    There are no open questions matching "Firefox" for Ubuntu.

It works also with user submitted values:

    >>> search_view_harness.submit(
    ...     "search",
    ...     {
    ...         "field.status": ["EXPIRED"],
    ...         "field.search_text": "",
    ...         "field.language": ["en"],
    ...         "field.sort": "by relevancy",
    ...     },
    ... )
    >>> print(translate(search_view_harness.view.page_title))
    Expired questions for Ubuntu

    >>> print(translate(search_view_harness.view.empty_listing_message))
    There are no expired questions for Ubuntu.

    >>> search_view_harness.submit(
    ...     "search",
    ...     {
    ...         "field.status": ["OPEN", "ANSWERED"],
    ...         "field.search_text": "evolution",
    ...         "field.language": ["en"],
    ...         "field.sort": "by relevancy",
    ...     },
    ... )
    >>> print(translate(search_view_harness.view.page_title))
    Questions matching "evolution" for Ubuntu

    >>> print(translate(search_view_harness.view.empty_listing_message))
    There are no questions matching "evolution" for Ubuntu with the
    requested statuses.


Question listing table
......................

The SearchQuestionsView has two attributes that control the columns of
the question listing table. Products display the default columns of
Summary, Created, Submitter, Assignee, and Status.

    >>> from lp.testing.pages import extract_text, find_tag_by_id

    >>> view = create_initialized_view(
    ...     firefox, name="+questions", principal=question_three.owner
    ... )
    >>> view.display_sourcepackage_column
    False

    >>> view.display_target_column
    False

    >>> table = find_tag_by_id(view.render(), "question-listing")
    >>> for row in table.find_all("tr"):
    ...     print(extract_text(row))
    ...
    Summary                Created     Submitter      Assignee  Status
    6 Newly installed...  2005-10-14   Sample Person  —         Answered ...

Distribution display the "Source Package" column. The name of the source
package is displayed if it exists.

    >>> view = create_initialized_view(
    ...     ubuntu, name="+questions", principal=question_three.owner
    ... )
    >>> view.display_sourcepackage_column
    True

    >>> view.display_target_column
    False

    >>> table = find_tag_by_id(view.render(), "question-listing")
    >>> for row in table.find_all("tr"):
    ...     print(extract_text(row))
    ...
    Summary  Created     Submitter      Source Package   Assignee  Status ...
    8 ...    2006-07-20  Sample Person  mozilla-firefox  —         Answered
    7 ...    2005-10-14  Foo Bar        —                —         Needs ...

ProjectGroups display the "In" column to show the product name.

    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet
    >>> mozilla = getUtility(IProjectGroupSet).getByName("mozilla")

    >>> view = create_initialized_view(
    ...     mozilla, name="+questions", principal=question_three.owner
    ... )
    >>> view.display_sourcepackage_column
    False

    >>> view.display_target_column
    True

    >>> table = find_tag_by_id(view.render(), "question-listing")
    >>> for row in table.find_all("tr"):
    ...     print(extract_text(row))
    ...
    Summary  Created     Submitter      In               Assignee  Status
    6 ...    2005-10-14  Sample Person  Mozilla Firefox  —         Answered...

The Assignee column is always displayed. It contains The person assigned
to the question, or an m-dash if there is no assignee.

    >>> question_six = firefox.getQuestion(6)
    >>> question_six.assignee = factory.makePerson(
    ...     name="bob", displayname="Bob"
    ... )
    >>> view = create_initialized_view(
    ...     firefox, name="+questions", principal=question_three.owner
    ... )
    >>> view.display_sourcepackage_column
    False

    >>> view.display_target_column
    False

    >>> table = find_tag_by_id(view.render(), "question-listing")
    >>> for row in table.find_all("tr"):
    ...     print(extract_text(row))
    ...
    Summary  Created     Submitter      Assignee  Status
    6 ...    2005-10-14  Sample Person  Bob       Answered
    4 ...    2005-09-05  Foo Bar        —         Open ...


ManageAnswerContactView
-----------------------

That view is used by a user to register themselves or any team they
administer as an answer contact for the project.

Jeff Waugh is an administrator for the Ubuntu Team. Thus he can register
himself or the Ubuntu Team as answer contact for ubuntu:

    >>> list(ubuntu.answer_contacts)
    []

    >>> login("jeff.waugh@ubuntulinux.com")
    >>> jeff_waugh = getUtility(ILaunchBag).user

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> ubuntu_team = getUtility(IPersonSet).getByName("ubuntu-team")
    >>> jeff_waugh in ubuntu_team.getDirectAdministrators()
    True

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "field.actions.update": "Continue",
    ...         "field.want_to_be_answer_contact": "on",
    ...         "field.answer_contact_teams": "ubuntu-team",
    ...     },
    ... )
    >>> view = getMultiAdapter((ubuntu, request), name="+answer-contact")
    >>> view.initialize()

    >>> for person in sorted(
    ...     ubuntu.direct_answer_contacts, key=attrgetter("displayname")
    ... ):
    ...     print(person.displayname)
    Jeff Waugh
    Ubuntu Team

The view adds notifications about the answer contacts added:

    >>> for notification in request.notifications:
    ...     print(notification.message)
    ...
    <...Your preferred languages... were updated to include ...English (en).
    You have been added as an answer contact for Ubuntu.
    English was added to Ubuntu Team's ...preferred languages...
    Ubuntu Team has been added as an answer contact for Ubuntu.

But Daniel Silverstone is only a regular member of Ubuntu Team, so he
can only subscribe himself:

    >>> login("daniel.silverstone@canonical.com")
    >>> kinnison = getUtility(ILaunchBag).user
    >>> kinnison in ubuntu_team.getDirectAdministrators()
    False

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "field.actions.update": "Continue",
    ...         "field.want_to_be_answer_contact": "on",
    ...     },
    ... )
    >>> view = getMultiAdapter((ubuntu, request), name="+answer-contact")
    >>> view.initialize()

    >>> for person in sorted(
    ...     ubuntu.direct_answer_contacts, key=attrgetter("displayname")
    ... ):
    ...     print(person.displayname)
    Daniel Silverstone
    Jeff Waugh
    Ubuntu Team

    >>> for notification in request.notifications:
    ...     print(notification.message)
    ...
    <...Your preferred languages... were updated to include ...English (en).
    You have been added as an answer contact for Ubuntu.

The same view is used to remove answer contact registrations. The user
can only remove their own registration.

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "field.actions.update": "Continue",
    ...         "field.want_to_be_answer_contact": "off",
    ...     },
    ... )
    >>> view = getMultiAdapter((ubuntu, request), name="+answer-contact")
    >>> view.initialize()

    >>> for person in sorted(
    ...     ubuntu.direct_answer_contacts, key=attrgetter("displayname")
    ... ):
    ...     print(person.displayname)
    Jeff Waugh
    Ubuntu Team

    >>> for notification in request.notifications:
    ...     print(notification.message)
    ...
    You have been removed as an answer contact for Ubuntu.

It can also be used to remove a team registration when the user is a
team administrator:

    >>> login("jeff.waugh@ubuntulinux.com")
    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={
    ...         "field.actions.update": "Continue",
    ...         "field.want_to_be_answer_contact": "on",
    ...         "field.answer_contact_teams-empty_marker": "1",
    ...     },
    ... )
    >>> view = getMultiAdapter((ubuntu, request), name="+answer-contact")
    >>> view.initialize()

    >>> for person in sorted(
    ...     ubuntu.direct_answer_contacts, key=attrgetter("displayname")
    ... ):
    ...     print(person.displayname)
    Jeff Waugh

    >>> for notification in request.notifications:
    ...     print(notification.message)
    ...
    Ubuntu Team has been removed as an answer contact for Ubuntu.
