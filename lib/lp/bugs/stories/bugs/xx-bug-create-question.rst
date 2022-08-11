Convert bug to question
=======================

Some bugs that are filed, aren't really bugs, they are questions. When
the bug target's pillar uses Launchpad to track bugs, the bug can be
converted to a question. The process creates a new question using the
bug's owner, title, and description. The bug's status is set to Invalid
in every location that it affects.

A user with permission to edit a bug may create a question from a bug.
An anonymous user cannot create a question.

    >>> anon_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/ubuntu/+source/linux-source-2.6.15/+bug/10')
    >>> anon_browser.title
    'Bug #10 ... : Bugs : linux-source-2.6.15 package : Ubuntu'

    >>> anon_browser.getLink('Convert to a question')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> anon_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/ubuntu/+source/linux-source-2.6.15/+bug/10/+create-question')
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

No Privileges Person is doing triage for Ubuntu. They recognize bug 10 is
really a question. They choose to make a question from it.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/ubuntu/+source/linux-source-2.6.15/+bug/10')
    >>> user_browser.title
    'Bug #10 ... : Bugs : linux-source-2.6.15 package : Ubuntu'

    >>> user_browser.getLink('Convert to a question').click()
    >>> user_browser.title
    'Convert this bug to a question...

The 'Convert this to a question' page explains what will happen if No
Privileges Person chooses to make the bug into a question. There is a
field for a comment. They decide to create the question using the
'Convert this bug to a question' button.

    >>> print(find_main_content(user_browser.contents).p)
    <p>... the bug's status is set to Invalid. The new question
    will be linked to the bug. ...

    >>> user_browser.getControl('Comment').value = 'This bug is a question.'
    >>> user_browser.getControl('Convert this Bug into a Question').click()

No Privileges Person is shown the bug page again. There is a permanent
informational message stating that a question was created from the bug.

    >>> user_browser.title
    'Bug #10 ... : Bugs : linux-source-2.6.15 package : Ubuntu'

    >>> content = find_main_content(user_browser.contents)
    >>> print(content.find(id="bug-is-question"))
    <p...This bug report was converted into a question:
     question #...: <a ...>another test bug</a>. </p>

The bug status is Invalid for 'linux-source-2.6.15 (Ubuntu)'--It cannot
be edited.

    >>> print(extract_text(content(['table'], {'class' : 'listing'})[0]))
    Affects                        Status   Importance  Assigned to  Milestone
    linux-source-2.6.15 (Ubuntu) ... Invalid  Medium      Unassigned ...

Nor can the bugtask be edited if No Privileges Person accesses the
bugtask directly.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/ubuntu/+source/linux-source-2.6.15/+bug/10/+editstatus')
    >>> print_feedback_messages(user_browser.contents)
    This bug was converted into a question. It cannot be edited.

    >>> user_browser.getControl('Save Changes')
    Traceback (most recent call last):
    ...
    LookupError: ...

    >>> user_browser.goBack(1)

They see their comment was appended to the bug report's messages.

    >>> print(extract_text(
    ...     find_tags_by_class(str(content), 'editable-message-text')[-1]))
    This bug is a question.

No Privileges Person looks at the page heading and sees that Foo Bar is
the bug owner. They see the link to the question in the 'Related
questions' portlet, and uses it to go to the question page.

    >>> print(user_browser.url)
    http://bugs.launchpad.test/ubuntu/.../+bug/10

    >>> portlet = find_portlet(user_browser.contents, 'Related questions')
    >>> question_anchor = portlet.a
    >>> question_anchor
    <a href=".../ubuntu/+source/linux-source-2.6.15/+question/...">another
    test bug</a>

    >>> user_browser.getLink('another test bug').click()

No Privileges Person case see that the question was created from a bug.
They use the link to Related bug to return to the bug.

    >>> print(user_browser.title)
    Question #... : Questions : linux-source-2.6.15 package : Ubuntu

    >>> print(extract_text(
    ...     find_tag_by_id(user_browser.contents, 'original-bug')))
    This question was originally filed as bug #10.

    >>> user_browser.getLink('#10: another test bug').click()
    >>> user_browser.title
    'Bug #10 ... : Bugs : linux-source-2.6.15 package : Ubuntu'


When a question cannot be created from a bug
---------------------------------------------

Thunderbird does not use Launchpad to track bugs. Questions cannot be
made from its bugs. When No Privileges Person uses the link in the Bug
Actions menu, the page explains why they cannot make the bug into a
question.

    >>> user_browser.open('http://bugs.launchpad.test/thunderbird/+bug/9')
    >>> user_browser.title
    'Bug #9 ...'

    >>> user_browser.getLink('Convert to a question').click()
    >>> print(user_browser.title)
    Convert this bug to a question...

    >>> print(find_main_content(user_browser.contents).p)
    <p>
    This bug cannot be converted into a question.
    Mozilla Thunderbird does not use Launchpad to track bugs.
    Mozilla Thunderbird does not use Launchpad for support questions. ...

The page is present, but without a comment field or a button to create
the question.

    >>> user_browser.getControl('Comment')
    Traceback (most recent call last):
    ...
    LookupError: ...

    >>> user_browser.getControl('Convert to a question').click()
    Traceback (most recent call last):
    ...
    LookupError: ...

If No Privileges Person were to create a question from a bug, then
return to the create a question from a bug page using their back button or
a bookmark, they see that they cannot create the question again.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test'
    ...     '/ubuntu/+source/linux-source-2.6.15/+bug/10/+create-question')
    >>> user_browser.title
    'Convert this bug to a question...

    >>> print(find_main_content(user_browser.contents).p)
    <p>
    This bug cannot be converted into a question.
    A question was already created from this bug. ...

    >>> user_browser.getControl('Convert this Bug into a Question').click()
    Traceback (most recent call last):
    ...
    LookupError: ...

Most browsers cache pages. When No Privileges Person uses their
browser's back button, after creating a question, they are re-shown the
form as it was. They resubmit the form, and are notified that a question
could not be created.

Jokosher must enable answers to access questions.

    >>> from zope.component import getUtility
    >>> from lp.app.enums import ServiceUsage
    >>> from lp.registry.interfaces.product import IProductSet

    >>> login('admin@canonical.com')
    >>> getUtility(IProductSet)['jokosher'].answers_usage = (
    ...     ServiceUsage.LAUNCHPAD)
    >>> transaction.commit()
    >>> logout()

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/jokosher/+bug/12')
    >>> user_browser.title
    'Bug #12 ...'

    >>> user_browser.getLink('Convert to a question').click()
    >>> user_browser.getControl('Comment').value = 'This will succeed.'
    >>> user_browser.getControl('Convert this Bug into a Question').click()
    >>> user_browser.title
    'Bug #12 ...'

    >>> message = find_tag_by_id(user_browser.contents, 'bug-is-question')
    >>> print(extract_text(message))
    This bug report was converted into a question:...question #...


Remove the question
-------------------

After a question is created from a bug, the bug's Action menu displays
the 'Convert back to a bug' link. No Privileges Person decides to
reactivate a bug report.

    >>> user_browser.title
    'Bug #12 ... : Bugs : Jokosher'

    >>> user_browser.getLink('Convert back to a bug').click()
    >>> print(user_browser.title)
    Bug #12 - Convert this...

The 'Convert back to a bug' page explains what will happen if No
Privileges Person chooses to reactivate the bug. There is an optional
field for a comment. No other input is needed. No Privileges Person uses
the 'Convert back to a bug' button.

    >>> print(find_main_content(user_browser.contents).p)
    <p>... Reactivate this bug report by removing the question created
    from the bug. ...

    >>> user_browser.getControl('Comment').value = 'I misunderstood.'
    >>> user_browser.getControl('Convert Back to Bug').click()

No Privileges Person is shown the bug page again. There is a notice
stating that a question was removed from the bug. The Related Questions
portlet is gone too. They view the question and sees that it is still in
the Open status.

    >>> user_browser.title
    'Bug #12 ... : Bugs : Jokosher'

    >>> print_feedback_messages(user_browser.contents)
    Removed Question #...:
    Copy, Cut and Delete operations should work...

    >>> portlet = find_portlet(user_browser.contents, 'Related questions')
    >>> print(portlet)
    None

    >>> user_browser.getLink(
    ...     'Copy, Cut and Delete operations should work on '
    ...     'selections').click()
    >>> print(user_browser.title)
    Question #... : Questions : Jokosher

    >>> print(extract_text(
    ...     find_tag_by_id(user_browser.contents, 'question-status')))
    Status: Open

No Privileges Person uses their browser's back button to view the bug
again. The bug status is sill Invalid for Jokosher, but they can edit it.

    >>> user_browser.goBack(count=1)
    >>> content = find_main_content(user_browser.contents)
    >>> print(extract_text(content(['table'], {'class' : 'listing'})[0]))
    Affects                       Status   Importance  Assigned to  Milestone
    ... Jokosher ...              Invalid  Critical    Unassigned ...
    Affecting: Jokosher
    Filed here by: Foo Bar...

They read their comment that was appended to the bug report's messages.

    >>> print(extract_text(
    ...     find_tags_by_class(str(content), 'boardComment')[-1]))
    Revision history for this message
    No Privileges Person (no-priv)
    wrote
    ...
    I misunderstood.
    ...

When the remove question page is visited, and there is no question, the
form is not displayed. This can happened if the URL is hacked or the
question was removed, and the user used their back button to return to the
page. No Privileges Person sees a message that there is no question to
remove.

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/jokosher/+bug/12/+remove-question')
    >>> print(user_browser.title)
    Bug #12 - Convert this...

    >>> print(find_main_content(user_browser.contents).p)
    <p>
    The bug was not converted to a question. There is nothing to change. ...

    >>> user_browser.getControl('Comment')
    Traceback (most recent call last):
    ...
    LookupError: ...

    >>> user_browser.getControl('Convert Back to Bug').click()
    Traceback (most recent call last):
    ...
    LookupError: ...


