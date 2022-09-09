BugTarget-QuestionTarget compatibility
======================================

Bugs can be converted into questions when a person ascertains that that
is the nature of the issue. The bug's target must be adaptable to
IQuestionTarget.


BugTargets can be adapted to QuestionTargets
--------------------------------------------

Valid BugTargets except for Projects can be adapted to QuestionTargets.
The test fixture (test_bugtarget.py) provides bugtarget that is used in
this interface test for creating the bug. The target may be a: Product,
Distribution, ProductSeries, DistributionSeries, SourcePackage, or
DistributionSourcePackages.

    >>> from lp.answers.interfaces.questiontarget import IQuestionTarget
    >>> from lp.bugs.interfaces.bugtarget import IBugTarget

    >>> login("foo.bar@canonical.com")
    >>> IBugTarget.providedBy(bugtarget)
    True

    >>> IQuestionTarget.providedBy(IQuestionTarget(bugtarget))
    True


Create a question from a bug
----------------------------

The primary use case for converting a bug into a question is when a bug
contact recognises a bug is really a question. No Privileges Person
create a a new bug on the bugtarget. It will be converted to a question.

    >>> login("no-priv@canonical.com")
    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> bug = filebug(bugtarget, "Print is broken", status=BugTaskStatus.NEW)


canBeAQuestion()
----------------

The canBeAQuestion() method can be used to check if a question can be
created from a bug (but it will not state why). The most important
prerequisite for a bug to become a question is that the bugtarget's
pillar must use Launchpad to track bugs.

    >>> bug.affected_pillars[0].bug_tracking_usage
    <DBItem ServiceUsage.LAUNCHPAD, (20) Launchpad>

    >>> bug.canBeAQuestion()
    True


convertToQuestion()
-------------------

Sample Person recognises that this bug is a question while reviewing the
bugtarget's bugs, and choose to make it into a question. The UI would
pass Sample Person as the Person changing the status. They may provide a
message about why the report is a question.

    >>> from lp.registry.interfaces.person import IPersonSet

    >>> login("test@canonical.com")
    >>> sample_person = getUtility(IPersonSet).getByName("name12")
    >>> bug_subscription = bug.subscribe(sample_person, sample_person)

    >>> question = bug.convertToQuestion(sample_person, "This is a question.")

The bug and the question share identical attributes.

    >>> question.target == question_target
    True

    >>> question.owner == bug.owner
    True

    >>> question.title == bug.title
    True

    >>> question.description == bug.description
    True

    >>> question.datecreated == bug.datecreated
    True

    >>> print(question.owner.displayname)
    No Privileges Person

    >>> print(question.title)
    Print is broken

    >>> print(question.description)
    Print is broken

The bug's messages are copied to the question. The comment parameter for
convertToQuestion is optional. When it is provided, it is added to the
bug.

    # Bugs save the Bug.description as the first message;
    # questions do not.

    >>> len(question.messages) == bug.messages.count() - 1
    True

    >>> question.messages[-1].text_contents == bug.messages[-1].text_contents
    True

    >>> print(question.messages[-1].text_contents)
    This is a question.

Once converted to a question, the bugtask status is Invalid.

    >>> bug.bugtasks[-1].status.title
    'Invalid'

Subscribers to the bug are notified that the bug was made into a
question and that the bugtasks are Invalid.

    >>> bug.clearBugNotificationRecipientsCache()
    >>> recipients = bug.getBugNotificationRecipients()
    >>> "no-priv@canonical.com" in recipients.getEmails()
    True

    >>> "test@canonical.com" in recipients.getEmails()
    True

    >>> from storm.locals import Desc
    >>> from lp.bugs.model.bugnotification import BugNotification
    >>> from lp.services.database.interfaces import IStore
    >>> bug_notifications = (
    ...     IStore(BugNotification)
    ...     .find(BugNotification)
    ...     .order_by(Desc(BugNotification.id))
    ... )
    >>> for notification in bug_notifications:
    ...     print(notification.message.text_contents)
    ...
    ** Converted to question:
       http://answers.launchpad.test/.../+question/...
    ** Changed in: ...
       Status: New => Invalid
    This is a question.
    Print is broken

A bug can only be converted to a question once.

    >>> question = bug.convertToQuestion(sample_person, "Fail.")
    Traceback (most recent call last):
    ...
    AssertionError: This bug was already converted to question #...


getQuestionCreatedFromBug()
---------------------------

The question created from the bug is automatically linked to the
original bug. A bug can also retrieve all the questions that link to it
to, and vice versa. The getQuestionCreatedFromBug() method will return
just the question created from the bug.

    >>> question == bug.getQuestionCreatedFromBug()
    True

    >>> question in bug.questions
    True

    >>> print(bug.title)
    Print is broken

    >>> for bug in question.bugs:
    ...     print(bug.title)
    ...
    Print is broken

    >>> for question in bug.questions:
    ...     print(question.title)
    ...
    Print is broken


Only one bugtask must be valid
------------------------------

In the rare instance where a bug has more than one bugtask, there must
be exactly one bugtask having a non-Invalid status. The question's
target come from the bugtask's target.

    >>> login("no-priv@canonical.com")
    >>> big_bug = filebug(
    ...     bugtarget, "Print is borked", status=BugTaskStatus.NEW
    ... )

    >>> evo_project = factory.makeProduct()
    >>> evo_bugtask = factory.makeBugTask(bug=big_bug, target=evo_project)
    >>> bugtasks = big_bug.bugtasks
    >>> len(bugtasks) > 1
    True

    >>> len([bt for bt in bugtasks if bt.status.title != "Invalid"]) > 1
    True

    >>> big_bug.canBeAQuestion()
    False

The user can choose to Invalidate one or more bugtasks so that only one
bugtask can provide the QuestionTarget. Note that the comment is not
provided

    >>> evo_bugtask.transitionToStatus(BugTaskStatus.INVALID, sample_person)
    >>> len(
    ...     [
    ...         bt
    ...         for bt in bugtasks
    ...         if bt.status.title == "New" and bt.conjoined_primary is None
    ...     ]
    ... )
    1

    >>> big_bug.canBeAQuestion()
    True

    >>> question = big_bug.convertToQuestion(sample_person)
    >>> print(question.title)
    Print is borked

    >>> len(bugtasks) == len(
    ...     [bt for bt in bugtasks if bt.status.title == "Invalid"]
    ... )
    True


