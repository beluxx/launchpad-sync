# Copyright 2009, 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for CodeReviewComments."""

__metaclass__ = type

from soupmatchers import (
    HTMLContains,
    Tag,
    )

from lp.code.browser.codereviewcomment import (
    CodeReviewDisplayComment,
    ICodeReviewDisplayComment,
    )
from lp.services.webapp.interfaces import IPrimaryContext
from lp.services.webapp.testing import verifyObject
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestCodeReviewComments(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def testPrimaryContext(self):
        # Tests the adaptation of a code review comment into a primary
        # context.
        # We need a person to make a comment.
        with person_logged_in(self.factory.makePerson()):
            # The primary context of a code review comment is the same
            # as the primary context for the branch merge proposal that
            # the comment is for.
            comment = self.factory.makeCodeReviewComment()

        self.assertEqual(
            IPrimaryContext(comment).context,
            IPrimaryContext(comment.branch_merge_proposal).context)

    def test_display_comment_provides_icodereviewdisplaycomment(self):
        # The CodeReviewDisplayComment class provides IComment.
        with person_logged_in(self.factory.makePerson()):
            comment = self.factory.makeCodeReviewComment()

        display_comment = CodeReviewDisplayComment(comment)

        verifyObject(ICodeReviewDisplayComment, display_comment)


class TestCodeReviewCommentHtml(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_comment_page_has_meta_description(self):
        # The CodeReviewDisplayComment class provides IComment.
        with person_logged_in(self.factory.makePerson()):
            comment = self.factory.makeCodeReviewComment()

        display_comment = CodeReviewDisplayComment(comment)
        browser = self.getViewBrowser(display_comment)
        self.assertThat(
            browser.contents,
            HTMLContains(Tag(
                'meta description', 'meta',
                dict(
                    name='description',
                    content=comment.message_body))))

    def test_long_comments_not_truncated(self):
        """Long comments displayed by themselves are not truncated."""
        comment = self.factory.makeCodeReviewComment(body='x y' * 2000)
        browser = self.getViewBrowser(comment)
        body = Tag('Body text', 'p', text='x y' * 2000)
        self.assertThat(browser.contents, HTMLContains(body))
