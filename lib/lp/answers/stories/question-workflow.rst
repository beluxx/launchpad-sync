Question Workflow
=================

The status of a question changes based on the action done by users on
it. To demonstrate the workflow, we will use the existing question #2 on
the Firefox product which was filed by 'Sample Person'.

    # We will use one browser objects for the owner, and one for the user
    # providing support, 'No Privileges Person' here.

    >>> owner_browser = setupBrowser(auth="Basic test@canonical.com:test")

    >>> support_browser = setupBrowser(
    ...     auth="Basic no-priv@canonical.com:test"
    ... )

    # Define some utility functions to retrieve easily the last comment
    # added and the status of the question.

    >>> def find_request_status(contents):
    ...     print(extract_text(find_tag_by_id(contents, "question-status")))
    ...

    >>> def find_last_comment(contents):
    ...     soup = find_main_content(contents)
    ...     return soup.find_all("div", "boardCommentBody")[-1]
    ...

    >>> def print_last_comment(contents):
    ...     print(extract_text(find_last_comment(contents)))
    ...


Logging In
----------

To participate in a question, the user must be logged in.

    >>> anon_browser.open("http://launchpad.test/firefox/+question/2")
    >>> print(anon_browser.contents)
    <!DOCTYPE...
    ...
    To post a message you must <a href="+login">log in</a>.
    ...


Requesting for More Information
-------------------------------

It's not unusual that the original message of a question is terse and
quite vague. In these cases, to help the user, some more information
will be required.

No Privileges Person visits the question. They see the heading 'Can you
help with this problem?'. The problem is not clear, they need more
information. To request for more information from the question owner, No
Privileges Person enters their question in the 'Message' field and clicks
on the 'Add Information Request' button.

    >>> support_browser.open("http://launchpad.test/firefox/+question/2")
    >>> content = find_tag_by_id(
    ...     support_browser.contents, "can-you-help-with-this-problem"
    ... )
    >>> print(content.h2.decode_contents())
    Can you help with this problem?

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(support_browser.contents, "horizontal-menu")
    ...     )
    ... )
    Link existing bug
    Create bug report
    Link to a FAQ
    Create a new FAQ

    >>> support_browser.getControl(
    ...     "Message"
    ... ).value = (
    ...     "Can you provide an example of an URL displaying the problem?"
    ... )
    >>> support_browser.getControl("Add Information Request").click()

The message was added to the question and its status was changed to
'Needs information':

    >>> find_request_status(support_browser.contents)
    Status: Needs information

    >>> print_last_comment(support_browser.contents)
    Can you provide an example of an URL displaying the problem?

Of course, if you don't add a message, clicking on the button will give
you an error.

    >>> support_browser.getControl("Add Information Request").click()
    >>> soup = find_main_content(support_browser.contents)
    >>> print(soup.find("div", "message").decode_contents())
    Please enter a message.


Adding a Comment
----------------

A comment can be added at any point without altering the status. The
user simply enters the comment in the 'Message' box and clicks the 'Just
Add a Comment' button.

    >>> support_browser.getControl(
    ...     "Message"
    ... ).value = (
    ...     "I forgot to mention, in the meantime here is a workaround..."
    ... )
    >>> support_browser.getControl("Just Add a Comment").click()

This appends the comment to the question and it doesn't change its
status:

    >>> print(find_request_status(support_browser.contents))
    Status: Needs information ...

    >>> print_last_comment(support_browser.contents)
    I forgot to mention, in the meantime here is a workaround...


Answering with More Information
-------------------------------

When the question is in the 'Needs information' state, it means that the
question owner should come back and provide more information. They can do
so by entering the reply in the 'Message' box and clicking on the "I'm
Providing More Information" button. Note that the question owner cannot
see the 'Can you help with this problem?' heading because it is not
relevant to their tasks.

    >>> owner_browser.open("http://launchpad.test/firefox/+question/2")
    >>> content = find_tag_by_id(
    ...     owner_browser.contents, "can-you-help-with-this-problem"
    ... )
    >>> content is None
    True

    >>> owner_browser.getControl("Message").value = (
    ...     "The following SVG doesn't display properly:\n"
    ...     "http://www.w3.org/2001/08/rdfweb/rdfweb-chaals-and-dan.svg"
    ... )
    >>> owner_browser.getControl("I'm Providing More Information").click()

Once the owner replied with the, hopefully, requested information, the
status is changed to Open and their answer appended to the question
discussion.

    >>> print(find_request_status(owner_browser.contents))
    Status: Open ...

    >>> print_last_comment(owner_browser.contents)
    The following SVG doesn't display properly:
    http://www.w3.org/2001/08/rdfweb/rdfweb-chaals-and-dan.svg


Giving an Answer
----------------

Once the question is clarified, it is easier for a user to give an
answer. This is done by entering the answer in the 'Message' box and
clicking the 'Propose Answer' button.

    >>> support_browser.open("http://launchpad.test/firefox/+question/2")
    >>> support_browser.getControl("Message").value = (
    ...     "New version of the firefox package are available with SVG "
    ...     "support enabled. You can use apt to upgrade."
    ... )
    >>> support_browser.getControl("Propose Answer").click()

This moves the question to the Answered state and adds the answer to
the end of the discussion:

    >>> print(find_request_status(support_browser.contents))
    Status: Answered ...

    >>> print_last_comment(support_browser.contents)
    New version of the firefox package are available with SVG support
    enabled. You can use apt to upgrade.


Confirming an Answer
--------------------

When the owner comes back on the question page, they will now see a new
'This Solved My Problem' button near the answer.

    >>> owner_browser.open("http://launchpad.test/firefox/+question/2")
    >>> soup = find_main_content(owner_browser.contents)
    >>> soup.find_all("div", "boardComment")[-1].find("input", type="submit")
    <input name="field.actions.confirm" type="submit"
     value="This Solved My Problem"/>

(Note although we have three comments on the question, that's the only
one that has this button. Only answers have this button.)

There is also a hint below the form to the question owner about using
the 'This Solved My Problem' button.

    >>> answer_button_paragraph = find_tag_by_id(
    ...     owner_browser.contents, "answer-button-hint"
    ... )
    >>> print(extract_text(answer_button_paragraph))
    To confirm an answer, use the 'This Solved My Problem' button located at
    the bottom of the answer.

Clicking that button will confirm that the answer solved the problem.

    >>> owner_browser.getControl("This Solved My Problem").click()

This changes the status of the question to 'Solved' and mark 'No
Privileges Person' as the solver.

    >>> print(find_request_status(owner_browser.contents))
    Status: Solved ...

Since no message can be provided when that button is clicked. A default
confirmation message was appended to the question discussion:

    >>> print_last_comment(owner_browser.contents)
    Thanks No Privileges Person, that solved my question.

The confirmed answer is also highlighted.

    >>> soup = find_main_content(owner_browser.contents)
    >>> bestAnswer = soup.find_all("div", "boardComment")[-2]
    >>> print(bestAnswer.find_all("img")[1])
    <img ... src="/@@/favourite-yes" ... title="Marked as best answer"/>

    >>> print(
    ...     soup.find(
    ...         "div", "boardCommentBody highlighted editable-message-text"
    ...     ).decode_contents()
    ... )
    <p>New version of the firefox package are available with SVG support
    enabled. You can use apt to upgrade.</p>

The History link should now show up.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(support_browser.contents, "horizontal-menu")
    ...     )
    ... )
    History
    Link existing bug
    Create bug report
    Link to a FAQ
    Create a new FAQ


Adding another Comment
----------------------

When the question is Solved, it is still possible to add comments to it.
The user simply enters the comment in the 'Message' box and clicks the
'Just Add a Comment' button.

    >>> owner_browser.getControl(
    ...     "Message"
    ... ).value = "The example now displays correctly. Thanks."
    >>> owner_browser.getControl("Just Add a Comment").click()

This appends the comment to the question and it doesn't change its
status:

    >>> print(find_request_status(owner_browser.contents))
    Status: Solved ...

    >>> print_last_comment(owner_browser.contents)
    The example now displays correctly. Thanks.


Reopening
---------

It can happen that, although the owner confirmed the question was solved,
the original problem reappears. In this case, they can reopen the question
by entering a new message and clicking the "I Still Need an Answer"
button.

    >>> owner_browser.getControl("Message").value = (
    ...     "Actually, there are still SVGs that do not display correctly. "
    ...     "For example, the following\n"
    ...     "http://people.w3.org/maxf/ChessGML/immortal.svg doesn't display "
    ...     "correctly."
    ... )
    >>> owner_browser.getControl("I Still Need an Answer").click()

This appends the new information to the question discussion and changes
its status back to 'Open'.

    >>> print(find_request_status(owner_browser.contents))
    Status: Open ...

    >>> print_last_comment(owner_browser.contents)
    Actually, there are still SVGs that do not display correctly.
    For example, the following
    http://people.w3.org/maxf/ChessGML/immortal.svg doesn't display correctly.

This also removes the highlighting from the previous answer and sets the
answerer back to None.

    >>> soup = find_main_content(owner_browser.contents)
    >>> bestAnswer = soup.find_all("div", "boardComment")[-4]
    >>> bestAnswer.find("strong") is None
    True

    >>> bestAnswer.find("div", "boardCommentBody editable-message-text")
    <div class="boardCommentBody editable-message-text"
    itemprop="commentText"><p>New version of the firefox package
    are available with SVG support enabled. You can use apt to
    upgrade.</p></div>

In addition, this creates a reopening record that is displayed in the
reopening portlet.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(owner_browser.contents, "portlet-reopenings")
    ...     )
    ... )
    This question was reopened ... Sample Person


Self-Answer
-----------

The owner can also give the solution to their own question. They simply have
to enter their solution in the 'Message' box and click the 'Problem
Solved' button.

    >>> owner_browser.getControl("Message").value = (
    ...     "OK, this example requires some SVG features that will only be "
    ...     "available in Firefox 2.0."
    ... )
    >>> owner_browser.getControl("Problem Solved").click()

This appends the message to the question and sets its status to
'Solved', and the answerer as the owner. We do not however mark a
message as the "Best answer".

    >>> find_request_status(owner_browser.contents)
    Status: Solved ...

    >>> soup = find_tag_by_id(owner_browser.contents, "portlet-details")
    >>> soup = find_main_content(owner_browser.contents)
    >>> bestAnswer = soup.find("img", {"title": "Marked as best answer"})
    >>> None == bestAnswer
    True

A message is displayed to the user confirming that the question is
solved and suggesting that the user choose an answer that helped the
question owner to solve their problem.

    >>> for message in soup.find_all("div", "informational message"):
    ...     print(extract_text(message))
    ...
    Your question is solved. If a particular message helped you solve the
    problem, use the 'This solved my problem' button.

If the user chooses a best answer, the author of that answer is
attributed as the answerer.

    >>> owner_browser.getControl("This Solved My Problem").click()
    >>> find_request_status(owner_browser.contents)
    Status: Solved ...

The answer's message is also highlighted as the best answer.

    >>> soup = find_main_content(owner_browser.contents)
    >>> bestAnswer = soup.find("img", {"title": "Marked as best answer"})
    >>> print(bestAnswer)
    <img ... src="/@@/favourite-yes" ... title="Marked as best answer"/>

    >>> answerer = bestAnswer.parent.find("a")
    >>> print(extract_text(answerer))
    No Privileges Person (no-priv)

    >>> message = soup.find(
    ...     "div", "boardCommentBody highlighted editable-message-text"
    ... )
    >>> print(message)
    <div class="boardCommentBody highlighted editable-message-text"
    itemprop="commentText"><p>New version of the firefox package are
    available with SVG support enabled. You can use apt to
    upgrade.</p></div>
    >>> print(extract_text(message))
    New version of the firefox package are available with SVG support
    enabled. You can use apt to upgrade.


History
=======

The history of the question is available on the 'History' page.

    >>> anon_browser.open("http://launchpad.test/firefox/+question/2")
    >>> anon_browser.getLink("History").click()
    >>> print(anon_browser.title)
    History of question #2...

It lists all the actions performed through workflow on the question:

    >>> soup = find_main_content(anon_browser.contents)
    >>> action_listing = soup.find("table", "listing")
    >>> for header in action_listing.find_all("th"):
    ...     print(header.decode_contents())
    ...
    When
    Who
    Action
    New State

    >>> for row in action_listing.find("tbody").find_all("tr"):
    ...     cells = row.find_all("td")
    ...     who = extract_text(cells[1].find("a"))
    ...     action = cells[2].decode_contents()
    ...     new_status = cells[3].decode_contents()
    ...     print(who.lstrip("&nbsp;"), action, new_status)
    ...
    No Privileges Person Request for more information Needs information
    No Privileges Person Comment Needs information
    Sample Person        Give more information        Open
    No Privileges Person Answer                       Answered
    Sample Person        Confirm                      Solved
    Sample Person        Comment                      Solved
    Sample Person        Reopen                       Open
    Sample Person        Confirm                      Solved
    Sample Person        Confirm                      Solved


Solving a question without an answer
------------------------------------

The user that asks a questions may solve the question before another
user can submit an answer. Without any answer messages, the user does
not see a notification to choose a 'This solved my problem' button.

Carlos has an open question that no one has submitted an answer for. He
is able to solve the problem on his own, and submits the solution for
other users with similar problems. He does not see a notice about
choosing an answer that helped him solve his problem.

    >>> carlos_browser = setupBrowser(auth="Basic carlos@canonical.com:test")
    >>> carlos_browser.open("http://launchpad.test/firefox/+question/12")
    >>> print(find_request_status(carlos_browser.contents))
    Status: Open ...

    >>> answer_button_paragraph = find_tag_by_id(
    ...     carlos_browser.contents, "answer-button-hint"
    ... )
    >>> answer_button_paragraph is None
    True

    >>> carlos_browser.getControl(
    ...     "Message"
    ... ).value = (
    ...     "There is a bug in that version. SMP is fine after upgrading."
    ... )
    >>> carlos_browser.getControl("Problem Solved").click()
    >>> print(find_request_status(carlos_browser.contents))
    Status: Solved ...

    >>> content = find_main_content(carlos_browser.contents)
    >>> messages = content.find_all("div", "informational message")
    >>> messages
    []


Asking a separate question
--------------------------

A user that is new to Answers is not familiar with the workflow. They may
have a problem of their own, and has discovered an existing question. We
want them to ask their own question instead of intruding into the workflow
of existing questions.

No Privileges Person (a different user from the one above) discovers the
Firefox question. The solution does not work, but they think they have a
similar problem so they ask their own question.

    >>> user_browser.open("http://launchpad.test/firefox/+question/2")

    >>> content = find_main_content(user_browser.contents)
    >>> print(content.find(id="can-you-help-with-this-problem"))
    None

    >>> user_browser.getLink("Ask a question").click()
    >>> print(user_browser.title)
    Ask a question about...
