# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bug comment browser view classes."""

__metaclass__ = type
__all__ = [
    'BugComment',
    'BugCommentView',
    'BugCommentBoxView',
    'BugCommentBoxExpandedReplyView',
    'BugCommentXHTMLRepresentation',
    'build_comments_from_chunks',
    'should_display_remote_comments',
    ]

from zope.component import adapts, getMultiAdapter, getUtility
from zope.interface import implements, Interface

from lazr.restful.interfaces import IWebServiceClientRequest

from lp.bugs.interfaces.bugmessage import (
    IBugComment, IBugMessageSet)
from lp.registry.interfaces.person import IPersonSet
from canonical.launchpad.webapp import canonical_url, LaunchpadView
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.authorization import check_permission

from canonical.config import config


def should_display_remote_comments(user):
    """Return whether remote comments should be displayed for the user."""
    # comment_syncing_team can be either None or '' to indicate unset.
    if config.malone.comment_syncing_team:
        comment_syncing_team = getUtility(IPersonSet).getByName(
            config.malone.comment_syncing_team)
        assert comment_syncing_team is not None, (
            "comment_syncing_team was set to %s, which doesn't exist." % (
                config.malone.comment_syncing_team))
    else:
        comment_syncing_team = None

    if comment_syncing_team is None:
        return True
    else:
        return user is not None and user.inTeam(comment_syncing_team)


def build_comments_from_chunks(chunks, bugtask, truncate=False):
    """Build BugComments from MessageChunks."""
    display_if_from_bugwatch = should_display_remote_comments(
        getUtility(ILaunchBag).user)

    comments = {}
    index = 0
    for chunk in chunks:
        message_id = chunk.message.id
        bug_comment = comments.get(message_id)
        if bug_comment is None:
            bug_comment = BugComment(
                index, chunk.message, bugtask, display_if_from_bugwatch)
            comments[message_id] = bug_comment
            index += 1
        bug_comment.chunks.append(chunk)

    # Set up the bug watch for all the imported comments. We do it
    # outside the for loop to avoid issuing one db query per comment.
    imported_bug_messages = getUtility(IBugMessageSet).getImportedBugMessages(
        bugtask.bug)
    for bug_message in imported_bug_messages:
        message_id = bug_message.message.id
        comments[message_id].bugwatch = bug_message.bugwatch
        comments[message_id].synchronized = (
            bug_message.remote_comment_id is not None)

    for bug_message in bugtask.bug.bug_messages:
        comment = comments.get(bug_message.messageID, None)
        # XXX intellectronica 2009-04-22, bug=365092: Currently, there are
        # some bug messages for which no chunks exist in the DB, so we need to
        # make sure that we skip them, since the corresponding message wont
        # have been added to the comments dictionary in the section above.
        if comment is not None:
            comment.visible = bug_message.visible

    for comment in comments.values():
        # Once we have all the chunks related to a comment set up,
        # we get the text set up for display.
        comment.setupText(truncate=truncate)
    return comments


class BugComment:
    """Data structure that holds all data pertaining to a bug comment.

    It keeps track of which index it has in the bug comment list and
    also provides functionality to truncate the comment.

    Note that although this class is called BugComment it really takes
    as an argument a bugtask. The reason for this is to allow
    canonical_url()s of BugComments to take you to the correct
    (task-specific) location.
    """
    implements(IBugComment)

    def __init__(self, index, message, bugtask, display_if_from_bugwatch,
                 activity=None):
        self.index = index
        self.bugtask = bugtask
        self.bugwatch = None

        self.title = message.title
        self.display_title = False
        self.datecreated = message.datecreated
        self.owner = message.owner
        self.rfc822msgid = message.rfc822msgid
        self.display_if_from_bugwatch = display_if_from_bugwatch

        self.chunks = []
        self.bugattachments = []

        if activity is None:
            activity = []

        self.activity = activity

        self.synchronized = False

    @property
    def can_be_shown(self):
        """Return whether or not the BugComment can be shown."""
        if self.bugwatch and not self.display_if_from_bugwatch:
            return False
        else:
            return True

    @property
    def show_for_admin(self):
        """Show hidden comments for Launchpad admins.

        This is used in templates to add a class to hidden
        comments to enable display for admins, so the admin
        can see the comment even after it is hidden.
        """
        user = getUtility(ILaunchBag).user
        is_admin = check_permission('launchpad.Admin', user)
        if is_admin and not self.visible:
            return True
        else:
            return False

    def setupText(self, truncate=False):
        """Set the text for display and truncate it if necessary.

        Note that this method must be called before either isIdenticalTo() or
        isEmpty() are called, since to do otherwise would mean that they could
        return false positives and negatives respectively.
        """
        comment_limit = config.malone.max_comment_size

        bits = [unicode(chunk.content)
                for chunk in self.chunks
                if chunk.content is not None and len(chunk.content) > 0]
        text = self.text_contents = '\n\n'.join(bits)

        if truncate and comment_limit and len(text) > comment_limit:
            # Note here that we truncate at comment_limit, and not
            # comment_limit - 3; while it would be nice to account for
            # the ellipsis, this breaks down when the comment limit is
            # less than 3 (which can happen in a testcase) and it makes
            # counting the strings harder.
            self.text_for_display = "%s..." % text[:comment_limit]
            self.was_truncated = True
        else:
            self.text_for_display = text
            self.was_truncated = False

    def isIdenticalTo(self, other):
        """Compare this BugComment to another and return True if they are
        identical.
        """
        if self.owner != other.owner:
            return False
        if self.text_for_display != other.text_for_display:
            return False
        if self.title != other.title:
            return False
        if self.bugattachments or other.bugattachments:
            # We shouldn't collapse comments which have attachments;
            # there's really no possible identity in that case.
            return False
        return True

    def isEmpty(self):
        """Return True if text_for_display is empty."""

        return (len(self.text_for_display) == 0 and
            len(self.bugattachments) == 0)

    @property
    def add_comment_url(self):
        return canonical_url(self.bugtask, view_name='+addcomment')

    @property
    def show_footer(self):
        """Return True if the footer should be shown for this comment."""
        if len(self.activity) > 0 or self.bugwatch:
            return True
        else:
            return False


class BugCommentView(LaunchpadView):
    """View for a single bug comment."""

    def __init__(self, context, request):
        # We use the current bug task as the context in order to get the
        # menu and portlets working.
        bugtask = getUtility(ILaunchBag).bugtask
        LaunchpadView.__init__(self, bugtask, request)
        self.comment = context


class BugCommentBoxView(LaunchpadView):
    """Render a comment box with reply field collapsed."""

    expand_reply_box = False


class BugCommentBoxExpandedReplyView(LaunchpadView):
    """Render a comment box with reply field expanded."""

    expand_reply_box = True


class BugCommentXHTMLRepresentation:
    adapts(IBugComment, IWebServiceClientRequest)
    implements(Interface)

    def __init__(self, comment, request):
        self.comment = comment
        self.request = request

    def __call__(self):
        """Render `BugComment` as XHTML using the webservice."""
        comment_view = getMultiAdapter(
            (self.comment, self.request), name="+box")
        return comment_view()

