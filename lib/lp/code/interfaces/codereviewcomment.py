# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""CodeReviewComment interfaces."""

__all__ = [
    "ICodeReviewComment",
    "ICodeReviewCommentDeletion",
]

from lazr.restful.declarations import exported, exported_as_webservice_entry
from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import Bool, Choice, Datetime, Int, Object, TextLine

from lp import _
from lp.code.enums import CodeReviewVote
from lp.code.interfaces.branchmergeproposal import IBranchMergeProposal
from lp.registry.interfaces.person import IPerson
from lp.services.messages.interfaces.message import (
    IMessage,
    IMessageCommon,
    IMessageEdit,
)


class ICodeReviewCommentView(IMessageCommon):
    """Globally visible attributes of ICodeReviewComment."""

    id = exported(
        Int(
            title=_("DB ID"),
            required=True,
            readonly=True,
            description=_("The tracking number for this comment."),
        )
    )

    branch_merge_proposal = exported(
        Reference(
            title=_("The branch merge proposal"),
            schema=IBranchMergeProposal,
            required=True,
            readonly=True,
        )
    )

    message = Object(schema=IMessage, title=_("The message."))

    author = exported(
        Reference(
            title=_("Comment Author"),
            schema=IPerson,
            required=True,
            readonly=True,
        )
    )

    date_created = exported(
        Datetime(title=_("Date Created"), required=True, readonly=True)
    )

    vote = exported(
        Choice(title=_("Review"), required=False, vocabulary=CodeReviewVote)
    )

    vote_tag = exported(TextLine(title=_("Vote tag"), required=False))

    title = exported(TextLine(title=_("The title of the comment")))

    message_body = exported(
        TextLine(
            title=_('Deprecated. Use "content" attribute instead.'),
            readonly=True,
        )
    )

    def getAttachments():
        """Get the attachments from the original message.

        :return: two lists, the first being attachments that we would display
            (being plain text or diffs), and a second list being any other
            attachments.
        """

    def getOriginalEmail():
        """An email object of the original raw email if there was one."""

    as_quoted_email = exported(
        TextLine(title=_("The message as quoted in email."), readonly=True)
    )

    visible = Bool(title=_("Whether this comment is visible."))

    def userCanSetCommentVisibility(user):
        """Can `user` set the visibility of this comment?

        Admins and registry experts can set the visibility of any code
        review comment.  Comment authors can set the visibility of their own
        comments.
        """


@exported_as_webservice_entry(as_of="beta")
class ICodeReviewComment(ICodeReviewCommentView, IMessageEdit):
    """A link between a merge proposal and a message."""


class ICodeReviewCommentDeletion(Interface):
    """This interface provides deletion of CodeReviewComments.

    This is the only mutation of CodeReviewCommentss that is permitted.
    """

    def destroySelf():
        """Delete this message."""
