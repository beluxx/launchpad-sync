Answer Tracker Email Interface
==============================

The Answer Tracker has an email interface, although it's quite limited
at the moment. The only thing you can do is post new messages on the
question. This is an important feature, though, since it ensures that if
a user decides to reply to a question notification, their email won't be
lost, it will be added to the question.

Incoming emails for the Answer Tracker are processed by the
AnswerTrackerHandler.

    # Define a time generator to ensure ordering of the messages. That is
    # necessary because the date of the messages created from an email has
    # only resolution to the second whereas the ones created by the DB API
    # have microseconds resolution. This means that it would be possible
    # for a message created using the DB API before one created by
    # the email interface to sort after.
    >>> from datetime import datetime, timedelta
    >>> from pytz import UTC
    >>> def now_generator(now_ref):
    ...     now = now_ref
    ...     while True:
    ...         yield now
    ...         now += timedelta(seconds=1)
    ...

    # We are using a date in the past because MessageSet disallows the
    # creation of email message with a future date.
    >>> now = now_generator(datetime.now(UTC) - timedelta(hours=24))

    # Define a helper function to send email to the Answer Tracker handler.
    >>> from lp.answers.mail.handler import AnswerTrackerHandler
    >>> from email.utils import formatdate, make_msgid, mktime_tz
    >>> from lp.services.mail.signedmessage import signed_message_from_bytes
    >>> handler = AnswerTrackerHandler()
    >>> def send_question_email(question_id, from_addr, subject, body):
    ...     login(from_addr)
    ...     lines = ["From: %s" % from_addr]
    ...     to_addr = "question%s@answers.launchpad.net" % question_id
    ...     lines.append("To: %s" % to_addr)
    ...     date = mktime_tz(next(now).utctimetuple() + (0,))
    ...     lines.append("Date: %s" % formatdate(date))
    ...     msgid = make_msgid()
    ...     lines.append("Message-Id: %s" % msgid)
    ...     lines.append("Subject: %s" % subject)
    ...     lines.append("")
    ...     lines.append(body)
    ...     raw_msg = "\n".join(lines)
    ...     msg = signed_message_from_bytes(raw_msg.encode("UTF-8"))
    ...     if handler.process(msg, msg["To"]):
    ...         # Ensures that the DB user has the correct permission to \
    ...         # saves the changes.
    ...         flush_database_updates()
    ...         return msgid
    ...     else:
    ...         return None
    ...

It only processes emails which are sent to an address of the form
'question<ID>@answers.launchpad.net', where <ID> is the question id. (The
domain is configured through the config.answertracker.email_domain
configuration variable.)

All other email addresses are ignored:

    >>> raw_msg = b"""From: test@canonical.com
    ... To: foo@support.launchpad.net
    ... Subject: Hello
    ...
    ... Hello there."""
    >>> msg = signed_message_from_bytes(raw_msg)
    >>> handler.process(msg, msg["To"])
    False


The message will also be ignored if no question with the addressed ID
can be found:

    >>> comment_msgid = send_question_email(
    ...     1234, "foo.bar@canonical.com", "Hey", "This is another comment."
    ... )
    >>> comment_msgid is None
    True

Incoming Email and Workflow
---------------------------

With the way the Answer Tracker workflow is modelled (see
answer-tracker-workflow.rst for the details), adding a message will
usually also change the status of the question. But currently, there is
no way to specify the exact workflow action accomplished by a given
message. (That will probably change in the near future when we add the
possibility to embed commands in the message body.) So, a default action
is chosen based on who is sending the message and the current state of
the question. There is the possibility that the default action is wrong,
but we chose the defaults based on what we assume is the common case
and by trying to minimize the impact of that error on future
possibilities for the user.

    # We will use a new question on the Ubuntu distribution in these
    # examples. We also use two actors, No Privileges Person which will
    # be the question owner and Sample Person who will play the role of
    # answer contact. Foo Bar is used to change the status of the
    # question.
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login("no-priv@canonical.com")
    >>> personset = getUtility(IPersonSet)
    >>> sample_person = personset.getByEmail("test@canonical.com")
    >>> no_priv = personset.getByEmail("no-priv@canonical.com")
    >>> foo_bar = personset.getByEmail("foo.bar@canonical.com")

    >>> import transaction
    >>> from lp.testing.dbuser import lp_dbuser

    >>> with lp_dbuser():
    ...     ubuntu = getUtility(IDistributionSet)["ubuntu"]
    ...     question = ubuntu.newQuestion(
    ...         no_priv,
    ...         "Unable to boot installer",
    ...         "I've tried installing Ubuntu on a Mac. But the installer "
    ...         "never boots.",
    ...         datecreated=next(now),
    ...     )
    ...     question_id = question.id
    ...

    # We need to refetch the question, since a new transaction was started.
    >>> from lp.answers.interfaces.questioncollection import IQuestionSet
    >>> question = getUtility(IQuestionSet).get(question_id)

    # Define an helper to change the question status easily.
    >>> def setQuestionStatus(question, new_status):
    ...     login("foo.bar@canonical.com")
    ...     question.setStatus(
    ...         foo_bar, new_status, "Status Change", datecreated=next(now)
    ...     )
    ...     login("no-priv@canonical.com")
    ...

Message From the Question Owner
-------------------------------

When the owner sends a message on the question, the message is
interpreted in three different manners based on the current question
state.

Open and Needs Information
..........................

In the Open and Needs Information states, we assume the message provides
more information on the problem.

For example, from the Open state:

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "no-priv@canonical.com",
    ...     "PowerMac 7200",
    ...     "I forgot to specify that I'm installing on a PowerMac 7200.",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Give more information
    >>> print(message.subject)
    PowerMac 7200
    >>> print(message.text_contents)
    I forgot to specify that I'm installing on a PowerMac 7200.
    >>> print(message.owner.displayname)
    No Privileges Person

And from the Needs information state:

    >>> from lp.answers.enums import QuestionStatus
    >>> setQuestionStatus(question, QuestionStatus.NEEDSINFO)

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "no-priv@canonical.com",
    ...     "Re: What model?",
    ...     "A PowerMac 7200.",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Give more information

In these states, the other possibility would be that the message is
really stating the owner solved their own problem. This is a less likely
scenario, since it would mean that the owner is replying to one of their
own messages. And if that was the case, it is easy for the owner to
correct our bad decision, since the question will stay on their
list of open questions.

Answered and Expired
....................

When the question is in the Answered or Expired states, we assume that
the email is reopening the question with more information.

    >>> setQuestionStatus(question, QuestionStatus.ANSWERED)

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "no-priv@canonical.com",
    ...     "Re: BootX",
    ...     "I installed BootX, but I must have made a mistake somewhere "
    ...     "because it still doesn't boot. I have a dialog which says "
    ...     "cannot find any kernel images.",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Reopen

From the Open state, the other possibilities for the owner email would
be that it was confirming that the provided answer work. We minimize the
chance of this happening by adding an explanation message in the footer
of the notification containing the answer. The other possibility is that
the user sent a message to explain that they solved their problem. We do
support this use case yet.

From the Expired state:

    >>> setQuestionStatus(question, QuestionStatus.EXPIRED)

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "no-priv@canonical.com",
    ...     "Need Help",
    ...     "I still cannot install on my PowerMac.",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Reopen

From the Expired state, the other possibility is the less probable
explaining that the owner solved their problem. Again, to minimize
confusion, the outoing notification contain a footer explaining what
will happen if one reply to the message.

Solved and Invalid
..................

When the question is in the Solved or Invalid state, we interpret the
message as a comment.

    >>> setQuestionStatus(question, QuestionStatus.SOLVED)

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "no-priv@canonical.com",
    ...     "Thanks",
    ...     "Thanks for helping me make BootX work.",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Comment

The other alternative is that the owner wanted to reopen the question.
But it is more likely that an email after they marked the problem as
solved would come as a reply to another comment, so it is safer to
assume it was a comment.

And from the Invalid:

    >>> setQuestionStatus(question, QuestionStatus.INVALID)

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "no-priv@canonical.com",
    ...     "Come on!",
    ...     "Trying to install on an old machine shouldn't be considered "
    ...     "an invalid question!",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Comment

That is the only possibility on an Invalid question. From the 'Invalid'
state, there is no normal transition. The only possibility is that an
admin comes to change the status of the question.

Message From Another User
.........................

It is simpler when a user other than the owner sends an email. When
the question is in the Open or Needs information state, there are only
two choices: either a question for more information or an answer. We
will assume it is an answer because it gives the opportunity for the
owner to confirm that the problem is solved. If it was really a question
for more information, the user can reply and the resulting state will be
fine. So it is the safest thing to assume.

    >>> setQuestionStatus(question, QuestionStatus.OPEN)

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "test@canonical.com",
    ...     "BootX",
    ...     "You need to install and configure BootX to boot the installer "
    ...     "CD.",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Answer
    >>> print(message.owner.displayname)
    Sample Person

Needs information example:

    >>> setQuestionStatus(question, QuestionStatus.NEEDSINFO)

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "test@canonical.com",
    ...     "What model?",
    ...     "What Mac model are you trying to install on?",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Answer

Answered example:

    >>> print(question.status.title)
    Answered

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "test@canonical.com",
    ...     "More info on BootX",
    ...     "You can find instructions on BootX installation at that URL: "
    ...     "https://help.ubuntu.com/community/Installation/OldWorldMacs",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Answer


Solved, Invalid and Expired
...........................

When another user than the owner sends a message to a question
in the Solved, Invalid or Expired states, the only possible
interpretation is that it is a comment.

    >>> setQuestionStatus(question, QuestionStatus.SOLVED)

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "test@canonical.com",
    ...     "RAM",
    ...     "You will probably need to install some RAM to make this usable "
    ...     "though.",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Comment

    >>> setQuestionStatus(question, QuestionStatus.EXPIRED)

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "test@canonical.com",
    ...     "How weird",
    ...     "Is somebody really trying to install Ubuntu on such obsolete "
    ...     "hardware?",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Comment

    >>> setQuestionStatus(question, QuestionStatus.INVALID)

    >>> msgid = send_question_email(
    ...     question.id,
    ...     "test@canonical.com",
    ...     "Error?",
    ...     "I think the rejection was an error.",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Comment
    >>> transaction.abort()


Answers linked to FAQ questions
...............................

Answers may also be linked to FAQ questions.

    >>> from zope.security.proxy import removeSecurityProxy

    >>> with lp_dbuser():
    ...     login("foo.bar@canonical.com")
    ...     faq = question.target.newFAQ(
    ...         no_priv,
    ...         "Why everyone think this is weird.",
    ...         "That's an easy one. It's because it is!",
    ...     )
    ...     removeSecurityProxy(question).faq = faq
    ...

    >>> login("no-priv@canonical.com")

    # Make sure that the database security and permissions are set up
    # correctly for answers that link to FAQs.  If they are not, then
    # this will raise an error; See bug #196661.
    >>> msgid = send_question_email(
    ...     question.id,
    ...     "test@canonical.com",
    ...     "Fnord",
    ...     "You will probably need to install some RAM to see the fnords.",
    ... )
    >>> message = question.messages[-1]
    >>> message.rfc822msgid == msgid
    True
    >>> print(message.action.title)
    Answer


AnswerTrackerHandler Integration
--------------------------------

The general mail processor delegates all emails to the
config.answertracker.email_domain to the AnswerTrackerHandler.

    >>> raw_msg = b"""From: test@canonical.com
    ... X-Launchpad-Original-To: question1@answers.launchpad.net
    ... Subject: A new comment
    ... Message-Id: <comment1@localhost>
    ... Date: Mon, 02 Jan 2006 15:42:07 -0000
    ...
    ... This is a new comment.
    ... """
    >>> from lp.services.mail import stub

    # Clear email queue of outgoing notifications.
    >>> stub.test_emails = []
    >>> stub.test_emails.append(
    ...     (
    ...         "test@canonical.com",
    ...         ["question1@answers.launchpad.net"],
    ...         raw_msg,
    ...     )
    ... )

    >>> from lp.services.mail.incoming import handleMail
    >>> handleMail()

    >>> question_one = getUtility(IQuestionSet).get(1)
    >>> "<comment1@localhost>" in [
    ...     comment.rfc822msgid for comment in question_one.messages
    ... ]
    True

For backward compatibility with notifications sent before the support
tracker was renamed to Answer Tracker, we still accept emails sent
to the old ticket<ID>@support.launchpad.net address:

    >>> raw_msg = b"""From: test@canonical.com
    ... X-Launchpad-Original-To: ticket11@support.launchpad.net
    ... Subject: Another comment
    ... Message-Id: <comment2@localhost>
    ... Date: Mon, 23 Apr 2007 16:00:00 -0000
    ...
    ... This is another comment.
    ... """
    >>> stub.test_emails.append(
    ...     (
    ...         "test@canonical.com",
    ...         ["ticket11@support.launchpad.net"],
    ...         raw_msg,
    ...     )
    ... )
    >>> handleMail()

    >>> question_11 = getUtility(IQuestionSet).get(11)
    >>> "<comment2@localhost>" in [
    ...     comment.rfc822msgid for comment in question_11.messages
    ... ]
    True
