Linked Bug Status Changed Notification (Private)
================================================

See `answer-tracker-notifications-linked-bug.rst` for public bug behaviour.

Question subscribers are not sent notifications about private bugs, because
they are indirect subscribers.

    >>> from lp.answers.tests.test_question_notifications import (
    ...     pop_questionemailjobs,
    ... )
    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.services.webapp.snapshot import notify_modified

    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> bugtask = get_bugtask_linked_to_question()

    >>> bugtask.bug.setPrivate(True, bugtask.bug.owner)
    True
    >>> with notify_modified(bugtask, ["status"], user=no_priv):
    ...     bugtask.transitionToStatus(BugTaskStatus.FIXCOMMITTED, no_priv)
    ...     ignore = pop_questionemailjobs()
    ...
    >>> notifications = pop_questionemailjobs()
    >>> len(notifications)
    0
