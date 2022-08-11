Launchpad Comments
##################

The comments service module provides some interfaces to handle consistent
rendering of comments within Launchpad.


How does it work?
=================

In pages where a conversation is to be rendered, the view should provide an
attribute that provides the IConversation interface.  This is then rendered
using the +render view on the interface.

   <tal:conversation replace="structure view/conversation/@@+render"/>

The comment in the conversation needs to provide the IComment interface.  A
simple way to do this is to have a view class that implements IComment and
delegates to the underlying interface object, like this:

@implementer(IComment)
@delegate_to(ICodeReviewComment, context='comment')
class CodeReviewDisplayComment:
    """A code review comment or activity or both."""

    ...


Each comment in the conversation's comment list is then rendered using the
standard Launchpad style.  This is defined in the templates directory as
comment.pt.  This page template delegates the rendering of the parts to views
on the comment:

 * +comment-header - the top part of the comment
     normally something like "Bob wrote 4 seconds ago"
 * +comment-body - the main content
     Only rendered if IComment.has_body is true.  By default, is the same as
     +comment-body-text
 * +comment-body-text - the main content
     The textual portion of the message body, suitably escaped and linkified.
 * +comment-footer - associated activity or other footer info, like
     bug activity or code reviews.
     Only rendered if IComment.has_footer is true

