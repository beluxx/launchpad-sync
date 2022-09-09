Question Subscriptions
======================

Users can subscribe to specific questions. When they are subscribed they
will receive notifications for any changes to the question.


Subscribing
-----------

To subscribe, users use the 'Subscribe' link and then confirm that
they want to subscribe by clicking on the 'Subscribe' button. The user
sees a link to their subscribed questions.

    >>> user_browser.open("http://launchpad.test/firefox/+question/2")
    >>> user_browser.getLink("Subscribe").click()
    >>> print(user_browser.title)
    Subscription : Question #2 ...

    >>> print(user_browser.getLink("your subscribed questions page"))
    <Link ...'http://answers.launchpad.test/~no-priv/+subscribedquestions'>

    >>> user_browser.getControl("Subscribe").click()

A message confirming that they were subscribed is displayed:

    >>> print_feedback_messages(user_browser.contents)
    You have subscribed to this question.


Unsubscribing
-------------

When the user is subscribed to the question, the 'Subscribe' link
becomes an 'Unsubscribe' link. To unsubscribe, the user follows that
link and then click on the 'Unsubscribe' button.

    >>> link = user_browser.getLink("Unsubscribe").click()
    >>> print(user_browser.title)
    Subscription : Question #2 ...

    >>> print(
    ...     extract_text(find_tag_by_id(user_browser.contents, "unsubscribe"))
    ... )
    Unsubscribing from this question ...

    >>> user_browser.getControl("Unsubscribe").click()

A confirmation is displayed:

    >>> print_feedback_messages(user_browser.contents)
    You have unsubscribed from this question.


Subscribing While Posting A Message
-----------------------------------

It is also possible to subscribe at the same time than posting a message
on an existing question. The user can simply check the 'Email me future
discussion about this question' checkbox:

    >>> user_browser.open("http://launchpad.test/firefox/+question/6")
    >>> user_browser.getControl("Message").value = (
    ...     "Try starting firefox from the command-line. Are there any "
    ...     "messages appearing?"
    ... )
    >>> user_browser.getControl(
    ...     "Email me future discussion about this question"
    ... ).selected = True
    >>> user_browser.getControl("Add Information Request").click()

A notification message is displayed notifying of the subscription:

    >>> print_feedback_messages(user_browser.contents)
    Thanks for your information request.
    You have subscribed to this question.
