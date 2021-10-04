# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Notifications related to linking bugs and questions."""

__all__ = []

from lazr.lifecycle.interfaces import IObjectModifiedEvent

from lp.answers.karma import assignKarmaUsingQuestionContext
from lp.answers.notification import QuestionNotification
from lp.bugs.interfaces.bug import IBug
from lp.bugs.interfaces.bugtask import IBugTask
from lp.registry.interfaces.person import IPerson
from lp.services.database.sqlbase import block_implicit_flushes
from lp.services.mail.helpers import get_email_template
from lp.services.webapp.publisher import canonical_url


@block_implicit_flushes
def assign_question_bug_link_karma(question, event):
    """Assign karma to the user which added <questionbug>."""
    if IBug.providedBy(event.other_object):
        assignKarmaUsingQuestionContext(
            IPerson(event.user), event.object, 'questionlinkedtobug')


def subscribe_owner_to_bug(question, event):
    """Subscribe a question's owner when it's linked to a bug."""
    if IBug.providedBy(event.other_object):
        if not event.other_object.isSubscribed(question.owner):
            event.other_object.subscribe(question.owner, question.owner)


def unsubscribe_owner_from_bug(question, event):
    """Unsubscribe a question's owner when it's unlinked from a bug."""
    if IBug.providedBy(event.other_object):
        if event.other_object.isSubscribed(question.owner):
            event.other_object.unsubscribe(question.owner, question.owner)


def dispatch_linked_question_notifications(bugtask, event):
    """Send notifications to linked question subscribers when the bugtask
    status change.
    """
    for question in bugtask.bug.questions:
        QuestionLinkedBugStatusChangeNotification(question, event)


class QuestionLinkedBugStatusChangeNotification(QuestionNotification):
    """Notification sent when a linked bug status is changed."""

    def initialize(self):
        """Create a notifcation for a linked bug status change."""
        assert IObjectModifiedEvent.providedBy(self.event), (
            "Should only be subscribed for IObjectModifiedEvent.")
        assert IBugTask.providedBy(self.event.object), (
            "Should only be subscribed for IBugTask modification.")
        self.bugtask = self.event.object
        self.old_bugtask = self.event.object_before_modification

    def shouldNotify(self):
        """Only send notification when the status changed."""
        return (self.bugtask.status != self.old_bugtask.status
                and self.bugtask.bug.private == False)

    def getSubject(self):
        """See QuestionNotification."""
        return "[Question #%s]: Status of bug #%s changed to '%s' in %s" % (
            self.question.id, self.bugtask.bug.id, self.bugtask.status.title,
            self.bugtask.target.displayname)

    def getBody(self):
        """See QuestionNotification."""
        template = get_email_template(
            'question-linked-bug-status-updated.txt', app='coop/answersbugs')
        return template % {
            'bugtask_target_name': self.bugtask.target.displayname,
            'question_id': self.question.id,
            'question_title': self.question.title,
            'question_url': canonical_url(self.question),
            'bugtask_url': canonical_url(self.bugtask),
            'bug_id': self.bugtask.bug.id,
            'bugtask_title': self.bugtask.bug.title,
            'old_status': self.old_bugtask.status.title,
            'new_status': self.bugtask.status.title}
