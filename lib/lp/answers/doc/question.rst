========================
Launchpad Answer Tracker
========================

Launchpad includes an Answer Tracker where users can post questions, usually
about problems they encounter with projects, and other people can answer them.
Questions are created and accessed using the IQuestionTarget interface.  This
interface is available on Products, Distributions and
DistributionSourcePackages.

    >>> login("test@canonical.com")

    >>> from lp.testing import verifyObject
    >>> from lp.answers.interfaces.questiontarget import IQuestionTarget
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet

    >>> firefox = getUtility(IProductSet)["firefox"]
    >>> verifyObject(IQuestionTarget, firefox)
    True
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> verifyObject(IQuestionTarget, ubuntu)
    True

    >>> evolution_in_ubuntu = ubuntu.getSourcePackage("evolution")
    >>> verifyObject(IQuestionTarget, evolution_in_ubuntu)
    True

Although distribution series do not implement the IQuestionTarget interface,
it is possible to adapt one to it.  The adapter is actually the distroseries's
distribution.

    >>> ubuntu_warty = ubuntu.getSeries("warty")
    >>> IQuestionTarget.providedBy(ubuntu_warty)
    False
    >>> questiontarget = IQuestionTarget(ubuntu_warty)
    >>> verifyObject(IQuestionTarget, questiontarget)
    True

SourcePackages are can be adapted to QuestionTargets.

    >>> evolution_in_hoary = ubuntu.currentseries.getSourcePackage(
    ...     "evolution"
    ... )
    >>> questiontarget = IQuestionTarget(evolution_in_hoary)
    >>> verifyObject(IQuestionTarget, questiontarget)
    True

You create a new question by calling the newQuestion() method of an
IQuestionTarget attribute.

    >>> sample_person = getUtility(IPersonSet).getByEmail(
    ...     "test@canonical.com"
    ... )
    >>> firefox_question = firefox.newQuestion(
    ...     sample_person, "Firefox question", "Unable to use Firefox"
    ... )

The complete IQuestionTarget interface is documented in questiontarget.rst.


Official usage
==============

A product or distribution may be officially supported by the community using
the Answer Tracker.  This status is set by the answers_usage attribute on
the IProduct and IDistribution.

    >>> print(ubuntu.answers_usage.name)
    LAUNCHPAD
    >>> print(firefox.answers_usage.name)
    LAUNCHPAD


IQuestion interface
===================

Questions are manipulated through the IQuestion interface.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.answers.interfaces.question import IQuestion

    # The complete interface is not necessarily available to the
    # logged in user.
    >>> verifyObject(IQuestion, removeSecurityProxy(firefox_question))
    True

The person who submitted the question is available in the owner field.

    >>> firefox_question.owner
    <Person at ... name12 (Sample Person)>

When the question is created, the owner is added to the question's
subscribers.

    >>> from operator import attrgetter
    >>> def print_subscribers(question):
    ...     people = [
    ...         subscription.person for subscription in question.subscriptions
    ...     ]
    ...     for person in sorted(people, key=attrgetter("name")):
    ...         print(person.displayname)
    ...
    >>> print_subscribers(firefox_question)
    Sample Person

The question status is 'Open'.

    >>> print(firefox_question.status.title)
    Open

The question has a creation time.

    >>> from datetime import datetime, timedelta, timezone
    >>> now = datetime.now(timezone.utc)
    >>> now - firefox_question.datecreated < timedelta(seconds=5)
    True

The target onto which the question was created is also available.

    >>> print(firefox_question.target.displayname)
    Mozilla Firefox

It is also possible to adapt a question to its IQuestionTarget.

    >>> target = IQuestionTarget(firefox_question)
    >>> verifyObject(IQuestionTarget, target)
    True

The question can be assigned to a new IQuestionTarget.

    >>> thunderbird = getUtility(IProductSet)["thunderbird"]
    >>> firefox_question.target = thunderbird
    >>> print(firefox_question.target.displayname)
    Mozilla Thunderbird

When a question is reassigned, its product, distribution and
sourcepackagename attributes are reconciled with the IQuestionTarget.

    >>> firefox_question.target = ubuntu
    >>> print(firefox_question.target.displayname)
    Ubuntu
    >>> print(firefox_question.distribution.name)
    ubuntu
    >>> print(firefox_question.sourcepackagename)
    None
    >>> print(firefox_question.product)
    None

    >>> firefox_question.target = evolution_in_ubuntu
    >>> print(firefox_question.target.displayname)
    evolution in Ubuntu
    >>> print(firefox_question.distribution.name)
    ubuntu
    >>> print(firefox_question.sourcepackagename.name)
    evolution
    >>> print(firefox_question.product)
    None

    >>> firefox_question.target = firefox
    >>> print(firefox_question.target.displayname)
    Mozilla Firefox
    >>> print(firefox_question.distribution)
    None
    >>> print(firefox_question.sourcepackagename)
    None
    >>> print(firefox_question.product.name)
    firefox


Subscriptions and notifications
===============================

Whenever a question is created or changed, email notifications will be
sent.  To receive such notification, one can subscribe to the bug using
the subscribe() method.

    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> subscription = firefox_question.subscribe(no_priv)

The subscribers include the owner and the newly subscribed person.

    >>> print_subscribers(firefox_question)
    Sample Person
    No Privileges Person

The getDirectSubscribers() method returns a sorted list of subscribers.
This method iterates like the NotificationRecipientSet returned by the
direct_recipients method.

    >>> for person in firefox_question.getDirectSubscribers():
    ...     print(person.displayname)
    ...
    No Privileges Person
    Sample Person

To remove a person from the subscriptions list, we use the unsubscribe()
method.

    >>> firefox_question.unsubscribe(no_priv, no_priv)
    >>> print_subscribers(firefox_question)
    Sample Person

The people on the subscription list are said to be directly subscribed to the
question.  They explicitly chose to get notifications about that particular
question.  This list of people is available through the direct_recipients
method.

    >>> subscribers = firefox_question.direct_recipients

That method returns an INotificationRecipientSet, containing the direct
subscribers along with the rationale for contacting them.

    >>> from lp.services.mail.interfaces import INotificationRecipientSet
    >>> verifyObject(INotificationRecipientSet, subscribers)
    True
    >>> def print_reason(subscribers):
    ...     for person in subscribers:
    ...         reason, header = subscribers.getReason(person)
    ...         text = removeSecurityProxy(reason).getReason()
    ...         print(header, person.displayname, text)
    ...
    >>> print_reason(subscribers)
    Asker Sample Person
    You received this question notification because you asked the question.

There is also a list of 'indirect' subscribers to the question.  These are
people that didn't explicitly subscribe to the question, but that will receive
notifications for other reasons.  Answer contacts for the question target are
part of the indirect subscribers list.

    # There are no answer contacts on the firefox product.
    >>> list(firefox_question.indirect_recipients)
    []

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> english = getUtility(ILanguageSet)["en"]
    >>> login("no-priv@canonical.com")
    >>> no_priv.addLanguage(english)
    >>> firefox.addAnswerContact(no_priv, no_priv)
    True

    >>> from lp.services.propertycache import get_property_cache
    >>> del get_property_cache(firefox_question).indirect_recipients
    >>> indirect_subscribers = firefox_question.indirect_recipients
    >>> verifyObject(INotificationRecipientSet, indirect_subscribers)
    True
    >>> print_reason(indirect_subscribers)
    Answer Contact (firefox) No Privileges Person
    You received this question notification because you are an answer
    contact for Mozilla Firefox.

There is a special case for when the question is associated with a source
package.  The answer contacts for both the distribution and the source package
are part of the indirect subscribers list.

    # Let's register some answer contacts for the distribution and
    # the package.
    >>> list(ubuntu.answer_contacts)
    []
    >>> list(evolution_in_ubuntu.answer_contacts)
    []
    >>> ubuntu_team = getUtility(IPersonSet).getByName("ubuntu-team")
    >>> login(ubuntu_team.teamowner.preferredemail.email)
    >>> ubuntu_team.addLanguage(english)
    >>> ubuntu.addAnswerContact(ubuntu_team, ubuntu_team.teamowner)
    True
    >>> evolution_in_ubuntu.addAnswerContact(no_priv, no_priv)
    True
    >>> package_question = evolution_in_ubuntu.newQuestion(
    ...     sample_person,
    ...     "Upgrading to Evolution 1.4 breaks plug-ins",
    ...     "The FnordsHighlighter plug-in doesn't work after upgrade.",
    ... )

    >>> print_subscribers(package_question)
    Sample Person

    >>> del get_property_cache(firefox_question).indirect_recipients
    >>> indirect_subscribers = package_question.indirect_recipients
    >>> for person in indirect_subscribers:
    ...     print(person.displayname)
    ...
    No Privileges Person
    Ubuntu Team

    >>> reason, header = indirect_subscribers.getReason(ubuntu_team)
    >>> print(header, removeSecurityProxy(reason).getReason())
    Answer Contact (ubuntu) @ubuntu-team
    You received this question notification because your team Ubuntu Team is
    an answer contact for Ubuntu.

The question's assignee is also part of the indirect subscription list:

    >>> login("admin@canonical.com")
    >>> package_question.assignee = getUtility(IPersonSet).getByName("name16")
    >>> del get_property_cache(package_question).indirect_recipients
    >>> indirect_subscribers = package_question.indirect_recipients
    >>> for person in indirect_subscribers:
    ...     print(person.displayname)
    ...
    Foo Bar
    No Privileges Person
    Ubuntu Team

    >>> reason, header = indirect_subscribers.getReason(
    ...     package_question.assignee
    ... )
    >>> print(header, removeSecurityProxy(reason).getReason())
    Assignee
    You received this question notification because you are assigned to this
    question.

The getIndirectSubscribers() method iterates like the indirect_recipients
method, but it returns a sorted list instead of a NotificationRecipientSet.
It too contains the question assignee.

    >>> indirect_subscribers = package_question.getIndirectSubscribers()
    >>> for person in indirect_subscribers:
    ...     print(person.displayname)
    ...
    Foo Bar
    No Privileges Person
    Ubuntu Team

Notifications are sent to the list of direct and indirect subscribers.  The
notification recipients list can be obtained by using the getRecipients()
method.

    >>> login("no-priv@canonical.com")
    >>> subscribers = firefox_question.getRecipients()
    >>> verifyObject(INotificationRecipientSet, subscribers)
    True
    >>> for person in subscribers:
    ...     print(person.displayname)
    ...
    No Privileges Person
    Sample Person

More documentation on the question notifications can be found in
`answer-tracker-notifications.rst`.


Workflow
========

A question status should not be manipulated directly but through the
workflow methods.

The complete question workflow is documented in
`answer-tracker-workflow.rst`.


Unsupported questions
=====================

While a Person may ask questions in their language of choice, that does not
mean that indirect subscribers (Answer Contacts) to an IQuestionTarget speak
that language.  IQuestionTarget can return a list of Questions in languages
that are not supported.

    >>> unsupported_questions = firefox.searchQuestions(unsupported=True)
    >>> for question in sorted(
    ...     unsupported_questions, key=attrgetter("title")
    ... ):
    ...     print(question.title)
    Problemas de Impressão no Firefox

    >>> unsupported_questions = evolution_in_ubuntu.searchQuestions(
    ...     unsupported=True
    ... )
    >>> sorted(question.title for question in unsupported_questions)
    []

    >>> warty_question_target = IQuestionTarget(ubuntu_warty)
    >>> unsupported_questions = warty_question_target.searchQuestions(
    ...     unsupported=True
    ... )
    >>> for question in sorted(
    ...     unsupported_questions, key=attrgetter("title")
    ... ):
    ...     print(question.title)
    Problema al recompilar kernel con soporte smp (doble-núcleo)
    عكس التغييرات غير المحفوظة للمستن؟
