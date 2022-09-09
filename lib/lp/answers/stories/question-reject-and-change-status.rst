Rejecting Questions
===================

Answer contacts and administrators can reject a question.
This should be done when the question isn't an actual pertinent question
for the product. For example, if the question is a duplicate or spam.

No Privileges Person isn't an answer contact or administrator, so they
don't have access to that feature.

    >>> user_browser.open("http://launchpad.test/firefox/+question/2")
    >>> user_browser.getLink("Reject question")
    Traceback (most recent call last):
      ...
    zope.testbrowser.browser.LinkNotFoundError

Even when trying to access the page directly, they will get an unauthorized
error.

    >>> user_browser.open("http://launchpad.test/firefox/+question/2/+reject")
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

To reject the question, the user clicks on the 'Reject Question' link.

    >>> admin_browser.open(
    ...     "http://answers.launchpad.test/firefox/+question/2"
    ... )
    >>> admin_browser.getLink("Reject question").click()
    >>> admin_browser.getControl("Reject").click()

They need to enter a message explaining the rejection:

    >>> for message in find_tags_by_class(admin_browser.contents, "message"):
    ...     print(message.decode_contents())
    ...
    There is 1 error.
    You must provide an explanation message.

At this point the user might decide this is a bad idea, so there is a
cancel link to take them back to the question:

    >>> print(admin_browser.getLink("Cancel").url)
    http://answers.launchpad.test/firefox/+question/2

Entering an explanation message and clicking the 'Reject' button,
will reject the question.

    >>> admin_browser.getControl(
    ...     "Message"
    ... ).value = """Rejecting because it's a duplicate of bug #1."""
    >>> admin_browser.getControl("Reject").click()

Once the question is rejected, a confirmation message is shown;

    >>> for message in find_tags_by_class(admin_browser.contents, "message"):
    ...     print(message.decode_contents())
    ...
    You have rejected this question.

its status is changed to 'Invalid';

    >>> def print_question_status(browser):
    ...     print(
    ...         extract_text(
    ...             find_tag_by_id(browser.contents, "question-status")
    ...         )
    ...     )
    ...

    >>> print_question_status(admin_browser)
    Status: Invalid ...

and the rejection message is added to the question board.

    >>> content = find_main_content(admin_browser.contents)
    >>> print(
    ...     content.find_all("div", "boardCommentBody")[-1].decode_contents()
    ... )
    <p>Rejecting because it's a duplicate of <a...>bug #1</a>.</p>

The call to help with this problem is not displayed.

    >>> print(content.find(id="can-you-help-with-this-problem"))
    None

Selecting the 'Reject' action again, will simply display a message
stating that the question is already rejected:

    >>> admin_browser.getLink("Reject question").click()
    >>> print(admin_browser.url)
    http://answers.launchpad.test/firefox/+question/2
    >>> for message in find_tags_by_class(admin_browser.contents, "message"):
    ...     print(message.decode_contents())
    ...
    The question is already rejected.

Changing the Question Status
============================

In the previous example, that rejection was clearly a mistake: you
shouldn't reject a question because it is related to a bug, for these
case, you should link the question to the bug!

Users who have administrative privileges on the question (product or
distribution registrant and Launchpad admins) can correct errors like
these by using the 'Change status' action. This page enables a user to
set the question status to an arbitrary value without workflow constraint.

That action isn't available to a non-privileged user:

    >>> browser.open("http://launchpad.test/firefox/+question/2")
    >>> browser.getLink("Change status")
    Traceback (most recent call last):
      ...
    zope.testbrowser.browser.LinkNotFoundError

The change status form is available to an administrator through the
'Change status' link.

    >>> admin_browser.open("http://launchpad.test/firefox/+question/2")
    >>> admin_browser.getLink("Change status").click()

The form has a select widget displaying the current status.

    >>> admin_browser.getControl("Status", index=0).displayValue
    ['Invalid']

There is also a cancel link should the user decide otherwise:

    >>> print(admin_browser.getLink("Cancel").url)
    http://answers.launchpad.test/firefox/+question/2

The user needs to select a status and enter a message explaining the
status change:

    >>> admin_browser.getControl("Change Status").click()
    >>> for error in find_tags_by_class(admin_browser.contents, "message"):
    ...     print(error.decode_contents())
    ...
    There are 2 errors.
    You didn't change the status.
    You must provide an explanation message.

To correct the mistake of the previous example, the administrator would
select back the 'Open' status and provide an appropriate message:

    >>> admin_browser.getControl("Status", index=0).displayValue = ["Open"]
    >>> admin_browser.getControl("Message").value = (
    ...     "Setting status back to 'Open'. Questions similar to a bug "
    ...     "report should be linked to it, not rejected."
    ... )
    >>> admin_browser.getControl("Change Status").click()

Once the operation is completed, a confirmation message is displayed;

    >>> for message in find_tags_by_class(admin_browser.contents, "message"):
    ...     print(message.decode_contents())
    ...
    Question status updated.

its status is updated;

    >>> print_question_status(admin_browser)
    Status: Open ...

and the explanation message is added to the question discussion:

    >>> content = find_main_content(admin_browser.contents)
    >>> print(
    ...     content.find_all("div", "boardCommentBody")[-1].decode_contents()
    ... )
    <p>Setting status back to 'Open'. Questions similar to a
    bug report should be linked to it, not rejected.</p>
