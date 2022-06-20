QuestionWorkflowView: Handling of the subscribe_me option
=========================================================

This test makes sure that it is possible to subscribe to the question
whatever the action used.

    >>> from lp.answers.browser.question import QuestionWorkflowView
    >>> from lp.testing.deprecated import LaunchpadFormHarness
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.registry.interfaces.product import IProductSet

    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> login('test@canonical.com')
    >>> sample_person = getUtility(ILaunchBag).user
    >>> firefox_question = firefox.newQuestion(
    ...     sample_person, 'New question', 'A problem.')

Empty the subscribers list:

    >>> firefox_question.unsubscribe(sample_person, sample_person)
    >>> list(firefox_question.subscriptions)
    []

Create a view harness:

    >>> workflow_harness = LaunchpadFormHarness(
    ...     firefox_question, QuestionWorkflowView)
    >>> form_data = {'field.message': 'A message.',
    ...              'field.subscribe_me.used': 1,
    ...              'field.subscribe_me': 'on'}

Subscription is possible when requesting for more information:

    >>> login('foo.bar@canonical.com')
    >>> foo_bar = getUtility(ILaunchBag).user
    >>> workflow_harness.submit('requestinfo', form_data)
    >>> firefox_question.isSubscribed(foo_bar)
    True
    >>> firefox_question.unsubscribe(foo_bar, foo_bar)

Subscription is possible when providing more information:

    >>> login('test@canonical.com')
    >>> workflow_harness.submit('giveinfo', form_data)
    >>> firefox_question.isSubscribed(sample_person)
    True
    >>> firefox_question.unsubscribe(sample_person, sample_person)

Subscription is possible when providing an answer:

    >>> login('foo.bar@canonical.com')
    >>> workflow_harness.submit('answer', form_data)
    >>> firefox_question.isSubscribed(foo_bar)
    True
    >>> firefox_question.unsubscribe(foo_bar, foo_bar)

As when confirming an answer (altough this is probably not that common):

    >>> login('test@canonical.com')
    >>> workflow_harness.submit('confirm', dict(answer_id=-1, **form_data))
    >>> firefox_question.isSubscribed(sample_person)
    True
    >>> firefox_question.unsubscribe(sample_person, sample_person)

It is also possible when reopening the request.

    >>> workflow_harness.submit('reopen', form_data)
    >>> firefox_question.isSubscribed(sample_person)
    True
    >>> firefox_question.unsubscribe(sample_person, sample_person)

Self-Answering the request:

    >>> workflow_harness.submit('selfanswer', form_data)
    >>> firefox_question.isSubscribed(sample_person)
    True
    >>> firefox_question.unsubscribe(sample_person, sample_person)

As well as adding a comment:

    >>> workflow_harness.submit('comment', form_data)
    >>> firefox_question.isSubscribed(sample_person)
    True
    >>> firefox_question.unsubscribe(sample_person, sample_person)

Make sure that whenever the view actions is modified, this test
requires update:

    >>> print("\n".join(sorted(
    ...     action.__name__.split('.')[-1]
    ...     for action in workflow_harness.view.actions)))
    answer
    comment
    confirm
    giveinfo
    reopen
    requestinfo
    selfanswer
