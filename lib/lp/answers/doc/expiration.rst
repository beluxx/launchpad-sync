Questions Expiration
====================

It is not productive to have questions lying around forever in
the Answer Tracker. That's why we have a script which runs daily to
expire old questions on which there was no activity for the past two
weeks.

The expiration period is set using the
config.answertracker.days_before_expiration configuration variable. It
defaults to 15 days.

    >>> from lp.services.config import config
    >>> config.answertracker.days_before_expiration
    15

Only questions in the OPEN or NEEDSINFO state which aren't assigned to
somebody are subject to expiration.

    # Sanity check in case somebody modifies the question sampledata and
    # forget to update this script.
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.answers.enums import QuestionStatus
    >>> from lp.answers.model.question import Question
    >>> IStore(Question).find(
    ...     Question, Question.status.is_in(
    ...         (QuestionStatus.OPEN, QuestionStatus.NEEDSINFO))).count()
    9

    # By default, all open and needs info question should expire. Make
    # sure that no new questions were recently added and will make this
    # test fails in the future.
    >>> from datetime import datetime, timedelta
    >>> import pytz
    >>> from storm.locals import Or
    >>> interval = datetime.now(pytz.UTC) - timedelta(days=15)
    >>> IStore(Question).find(
    ...     Question,
    ...     Or(
    ...         Question.datelastresponse >= interval,
    ...         Question.datelastquery >= interval)).count()
    0

    # We need to massage sample data a little. Since all expiration
    # candidates in sample data would expire, do a little activity on
    # some of these.
    >>> from datetime import datetime, timedelta
    >>> from pytz import UTC
    >>> now = datetime.now(UTC)
    >>> two_weeks_ago = now - timedelta(days=14)
    >>> a_month_ago = now - timedelta(days=31)
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.answers.interfaces.questioncollection import IQuestionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login('no-priv@canonical.com')
    >>> no_priv = getUtility(ILaunchBag).user

    >>> questionset = getUtility(IQuestionSet)

    # An old question in NEEDSINFO the state.
    >>> old_needs_info_question = questionset.get(7)
    >>> print(old_needs_info_question.status.title)
    Needs information

    # An open question assigned to somebody.
    >>> login('foo.bar@canonical.com')
    >>> old_assigned_open_question = questionset.get(1)
    >>> old_assigned_open_question.assignee = getUtility(ILaunchBag).user

    # This one got an update from its owner recently.
    >>> login('test@canonical.com')
    >>> recent_open_question = questionset.get(2)
    >>> recent_open_question.giveInfo(
    ...     'SVG works better now, but is still broken')
    <lp.answers.model.questionmessage.QuestionMessage...>

    # This one was put in the NEEDSINFO state recently.
    >>> recent_needsinfo_question = questionset.get(4)
    >>> recent_needsinfo_question.requestInfo(
    ...     no_priv, 'What URL were you visiting?')
    <lp.answers.model.questionmessage.QuestionMessage...>

    # Old open questions.
    >>> old_open_question = questionset.get(5)

    # Subscribe a team to that question, and a answer contact,
    # to make sure that DB permissions are correct.
    >>> admin_team = getUtility(IPersonSet).getByName('admins')
    >>> old_open_question.subscribe(admin_team)
    <lp.answers.model.questionsubscription.QuestionSubscription...>
    >>> salgado = getUtility(IPersonSet).getByName('salgado')
    >>> old_open_question.target.addAnswerContact(salgado, salgado)
    True

    # Link it to a FAQ item for the same reason. We are setting the
    # attribute directly, because using the linkFAQ API would update
    # the last updates date of the question and remove it from the expiration
    # set.
    >>> from zope.security.proxy import removeSecurityProxy
    >>> login('foo.bar@canonical.com')
    >>> faq = old_open_question.target.newFAQ(
    ...     salgado, 'Why everyone think this is weird.',
    ...     "That's an easy one. It's because it is!")
    >>> removeSecurityProxy(old_open_question).faq = faq

    # A question linked to an non-Invalid bug is not expirable.
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> fixed_bug = getUtility(IBugSet).get(9)
    >>> bugtasks = fixed_bug.bugtasks
    >>> bugtasks[1].transitionToStatus(BugTaskStatus.INVALID, no_priv)
    >>> [bugtask.status.title for bugtask in bugtasks]
    ['Unknown', 'Invalid']
    >>> bug_link_question = questionset.get(11)
    >>> bug_link_question.linkBug(fixed_bug)
    True

    # A question linked to an Invalid bug; it is expirable.
    >>> invalid_bug = getUtility(IBugSet).get(10)
    >>> bugtask = invalid_bug.bugtasks[0]
    >>> bugtask.transitionToStatus(BugTaskStatus.INVALID, no_priv)
    >>> bugtask.status.title
    'Invalid'
    >>> invalid_bug_question = questionset.get(12)
    >>> invalid_bug_question.linkBug(invalid_bug)
    True

    # Commit the current transaction because the script will run in
    # another transaction and thus it won't see the changes done on this
    # test unless we commit.
    # XXX flacoste 2006-10-03 bug=3989: Unecessary flush_database_updates
    # required.
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> flush_database_updates()
    >>> import transaction
    >>> transaction.commit()

    # Run the script.
    >>> import subprocess
    >>> process = subprocess.Popen(
    ...     'cronscripts/expire-questions.py', shell=True,
    ...     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE, universal_newlines=True)
    >>> (out, err) = process.communicate()
    >>> print(err)
    INFO    Creating lockfile: /var/lock/launchpad-expire-questions.lock
    INFO    Expiring OPEN and NEEDSINFO questions without activity for the
            last 15 days.
    INFO    Found 5 questions to expire.
    INFO    Expired 5 questions.
    INFO    Finished expiration run.
    <BLANKLINE>
    >>> print(out)
    <BLANKLINE>
    >>> process.returncode
    0

    # Now we flush the caches, so that the above defined objects gets
    # their content from the modified DB.
    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> flush_database_caches()

The status of the OPEN and NEEDSINFO questions that had recent activity
wasn't modified by the script:

    >>> print(recent_open_question.status.title)
    Open
    >>> print(recent_needsinfo_question.status.title)
    Needs information

Neither the old one which was assigned to Foo Bar:

    >>> print(old_assigned_open_question.status.title)
    Open

The old question with non-Invalid bug link is still Open status:

    >>> print(bug_link_question.status.title)
    Open

But the other ones status was changed to 'Expired':

    >>> print(old_needs_info_question.status.title)
    Expired
    >>> print(old_open_question.status.title)
    Expired
    >>> print(invalid_bug_question.status.title)
    Expired

The message explaining the reason for the expiration was posted by the
Launchpad Janitor celebrity:

    >>> expiration_message = old_needs_info_question.messages[-1]
    >>> print(expiration_message.action.name)
    EXPIRE
    >>> print(expiration_message.new_status.title)
    Expired
    >>> print(expiration_message.owner.name)
    janitor

    >>> print(expiration_message.text_contents)
    This question was expired because it remained in the
    'Needs information' state without activity for the last 15 days.
