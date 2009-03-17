# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations for bug changes."""

__metaclass__ = type
__all__ = [
    'BugDescriptionChange',
    'BugTitleChange',
    'BugVisibilityChange',
    'get_bug_change_class',
]

from textwrap import dedent

from zope.interface import implements

from canonical.launchpad.interfaces.bugchange import (
    IBugChange)


def get_bug_change_class(obj, field_name):
    """Return a suitable IBugChange to describe obj and field_name."""
    try:
        return BUG_CHANGE_LOOKUP[field_name]
    except KeyError:
        return BugChangeBase


def get_unified_diff(old_value, new_value, line_length):
    """Return a unified diff of old_value and new_value."""
    # We've created this local version to avoid circular import
    # problems.
    from canonical.launchpad.mailnotification import get_unified_diff
    return get_unified_diff(old_value, new_value, line_length)


class BugChangeBase:
    """An abstract base class for Bug[Task]Changes."""

    implements(IBugChange)

    def __init__(self, when, person, what_changed, old_value, new_value,
                 recipients=None):
        self.new_value = new_value
        self.old_value = old_value
        self.person = person
        self.what_changed = what_changed
        self.when = when
        self.recipients = recipients

    def getBugActivity(self):
        """Return the `BugActivity` entry for this change."""
        raise NotImplementedError(self.getBugActivity)

    def getBugNotification(self):
        """Return the `BugNotification` for this event."""
        raise NotImplementedError(self.getBugNotification)

    def getBugNotificationRecipients(self):
        """Return the recipients for this event."""
        raise NotImplementedError(self.getBugNotificationRecipients)


class SimpleBugChangeMixin:
    """A mixin class that provides basic functionality for `IBugChange`s."""

    def getBugActivity(self):
        """Return the BugActivity data for the textual change."""
        return {
            'newvalue': self.new_value,
            'oldvalue': self.old_value,
            'whatchanged': self.what_changed,
            }

    def getBugNotificationRecipients(self):
        return self.recipients


class BugDescriptionChange(SimpleBugChangeMixin, BugChangeBase):
    """Describes a change to a bug's description."""

    def getBugNotification(self):
        description_diff = get_unified_diff(
            self.old_value, self.new_value, 72)
        notification_text = (
            u"** Description changed:\n\n%s" % description_diff)
        return {'text': notification_text}


class BugTitleChange(SimpleBugChangeMixin, BugChangeBase):
    """Describes a change to a bug's title, aka summary."""

    def getBugActivity(self):
        activity = super(BugTitleChange, self).getBugActivity()

        # We return 'summary' instead of 'title' for title changes
        # because the bug's title is referred to as its summary in the
        # UI.
        activity['whatchanged'] = 'summary'
        return activity

    def getBugNotification(self):
        notification_text = dedent("""\
            ** Summary changed:

            - %s
            + %s""" % (self.old_value, self.new_value))
        return {'text': notification_text}


class BugVisibilityChange(BugChangeBase):
    """Describes a change to a bug's visibility."""

    def _getVisibilityString(self, private):
        """Return a string representation of `private`.

        :return: 'Public' if private is False, 'Private' if
            private is True.
        """
        if private:
            return 'Private'
        else:
            return 'Public'

    def getBugActivity(self):
        # Use _getVisibilityString() to set old and new values
        # correctly. We lowercase them for UI consistency in the
        # activity log.
        old_value = self._getVisibilityString(self.old_value)
        new_value = self._getVisibilityString(self.new_value)
        return {
           'oldvalue': old_value.lower(),
           'newvalue': new_value.lower(),
           'whatchanged': 'visibility',
           }

    def getBugNotification(self):
        visibility_string = self._getVisibilityString(self.new_value)
        return {'text': "** Visibility changed to: %s" % visibility_string}


BUG_CHANGE_LOOKUP = {
    'description': BugDescriptionChange,
    'private': BugVisibilityChange,
    'title': BugTitleChange,
    }
