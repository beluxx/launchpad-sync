# Copyright 2009-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for CodeReviewComments."""

import re

import six
from soupmatchers import (
    HTMLContains,
    Tag,
    )
from testtools.matchers import (
    Equals,
    Not,
    )
from zope.component import getUtility

from lp.code.browser.codereviewcomment import (
    CodeReviewDisplayComment,
    ICodeReviewDisplayComment,
    )
from lp.code.interfaces.codereviewinlinecomment import (
    ICodeReviewInlineCommentSet,
    )
from lp.services.propertycache import clear_property_cache
from lp.services.webapp import canonical_url
from lp.testing import (
    admin_logged_in,
    BrowserTestCase,
    celebrity_logged_in,
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import HasQueryCount


class TestCodeReviewComments(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_display_comment_provides_icodereviewdisplaycomment(self):
        # The CodeReviewDisplayComment class provides IComment.
        with person_logged_in(self.factory.makePerson()):
            comment = self.factory.makeCodeReviewComment()

        display_comment = CodeReviewDisplayComment(comment)

        with person_logged_in(comment.owner):
            verifyObject(ICodeReviewDisplayComment, display_comment)

    def test_extra_css_classes_visibility(self):
        author = self.factory.makePerson()
        comment = self.factory.makeCodeReviewComment(sender=author)
        display_comment = CodeReviewDisplayComment(comment)
        self.assertEqual('', display_comment.extra_css_class)
        with person_logged_in(author):
            display_comment.message.setVisible(False)
        self.assertEqual(
            'adminHiddenComment', display_comment.extra_css_class)

    def test_show_spam_controls_permissions(self):
        # Admins, registry experts, and the author of the comment itself can
        # hide comments, but other people can't.
        author = self.factory.makePerson()
        comment = self.factory.makeCodeReviewComment(sender=author)
        display_comment = CodeReviewDisplayComment(comment)
        with person_logged_in(author):
            self.assertTrue(display_comment.show_spam_controls)
        clear_property_cache(display_comment)
        with person_logged_in(self.factory.makePerson()):
            self.assertFalse(display_comment.show_spam_controls)
        clear_property_cache(display_comment)
        with celebrity_logged_in('registry_experts'):
            self.assertTrue(display_comment.show_spam_controls)
        clear_property_cache(display_comment)
        with admin_logged_in():
            self.assertTrue(display_comment.show_spam_controls)


class TestCodeReviewCommentInlineComments(TestCaseWithFactory):
    """Test `CodeReviewDisplayComment` integration with inline-comments."""

    layer = LaunchpadFunctionalLayer

    def makeInlineComment(self, person, comment, previewdiff=None,
                          comments=None):
        # Test helper for creating inline comments.
        if previewdiff is None:
            previewdiff = self.factory.makePreviewDiff()
        if comments is None:
            comments = {'1': 'Foo'}
        getUtility(ICodeReviewInlineCommentSet).ensureDraft(
            previewdiff, person, comments)
        cric = getUtility(ICodeReviewInlineCommentSet).publishDraft(
            previewdiff, person, comment)
        return cric

    def test_display_comment_inline_comment(self):
        # The CodeReviewDisplayComment links to related inline comments
        # when they exist.
        person = self.factory.makePerson()
        with person_logged_in(person):
            comment = self.factory.makeCodeReviewComment()
        # `CodeReviewDisplayComment.previewdiff_id` is None if there
        # is no related inline-comments.
        display_comment = CodeReviewDisplayComment(comment)
        self.assertIsNone(display_comment.previewdiff_id)
        # Create a `PreviewDiff` and add inline-comments in
        # the context of this review comment.
        with person_logged_in(person):
            previewdiff = self.factory.makePreviewDiff()
            self.makeInlineComment(person, comment, previewdiff)
        # 'previewdiff_id' property is cached, so its value did not
        # change on the existing object.
        self.assertIsNone(display_comment.previewdiff_id)
        # On a new object, it successfully returns the `PreviewDiff.id`
        # containing inline-comments related with this review comment.
        display_comment = CodeReviewDisplayComment(comment)
        self.assertEqual(previewdiff.id, display_comment.previewdiff_id)

    def test_conversation_with_previewdiffs_populated(self):
        # `CodeReviewConversation` comments have 'previewdiff_id'
        # property pre-populated in view.
        person = self.factory.makePerson()
        merge_proposal = self.factory.makeBranchMergeProposal()
        with person_logged_in(person):
            for i in range(5):
                comment = self.factory.makeCodeReviewComment(
                    merge_proposal=merge_proposal)
                self.makeInlineComment(person, comment)
        from lp.testing.views import create_initialized_view
        view = create_initialized_view(merge_proposal, '+index')
        conversation = view.conversation
        with StormStatementRecorder() as recorder:
            [c.previewdiff_id for c in conversation.comments]
        self.assertThat(recorder, HasQueryCount(Equals(0)))


class TestCodeReviewCommentHtmlMixin:

    layer = DatabaseFunctionalLayer

    def test_comment_page_has_meta_description(self):
        # The CodeReviewDisplayComment class provides IComment.
        with person_logged_in(self.factory.makePerson()):
            comment = self.makeCodeReviewComment()

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
        comment = self.makeCodeReviewComment(body='x y' * 2000)
        browser = self.getViewBrowser(comment)
        body = Tag('Body text', 'p', text='x y' * 2000)
        self.assertThat(browser.contents, HTMLContains(body))

    def test_excessive_comments_redirect_to_download(self):
        """View for excessive comments redirects to download page."""
        comment = self.makeCodeReviewComment(body='x ' * 5001)
        view_url = canonical_url(comment)
        download_url = canonical_url(comment, view_name='+download')
        browser = self.getUserBrowser(view_url)
        self.assertNotEqual(view_url, browser.url)
        self.assertEqual(download_url, browser.url)
        self.assertEqual('x ' * 5001, browser.contents)

    def test_short_comment_no_download_link(self):
        """Long comments displayed by themselves are not truncated."""
        comment = self.makeCodeReviewComment(body='x ' * 5000)
        download_url = canonical_url(comment, view_name='+download')
        browser = self.getViewBrowser(comment)
        body = Tag(
            'Download', 'a', {'href': download_url},
            text='Download full text')
        self.assertThat(browser.contents, Not(HTMLContains(body)))

    def test_download_view(self):
        """The download view has the expected contents and header."""
        comment = self.makeCodeReviewComment(body='\u1234')
        browser = self.getViewBrowser(comment, view_name='+download')
        contents = '\u1234'.encode()
        self.assertEqual(contents, six.ensure_binary(browser.contents))
        self.assertEqual(
            'text/plain;charset=utf-8', browser.headers['Content-type'])
        self.assertEqual(
            '%d' % len(contents), browser.headers['Content-length'])
        disposition = 'attachment; filename="comment-%d.txt"' % comment.id
        self.assertEqual(disposition, browser.headers['Content-disposition'])

    def test_parent_comment_in_reply(self):
        """The reply view has the expected contents from the parent comment."""
        contents = 'test-comment'
        comment = self.makeCodeReviewComment(body=contents)
        browser = self.getViewBrowser(comment, view_name='+reply')
        self.assertIn(contents, browser.contents)

    def test_footer_for_mergeable_and_admin(self):
        """An admin sees Hide/Reply links for a comment on a mergeable MP."""
        comment = self.makeCodeReviewComment()
        display_comment = CodeReviewDisplayComment(comment)
        browser = self.getViewBrowser(
            display_comment, user=self.factory.makeAdministrator())
        footer = Tag('comment footer', 'div', {'class': 'boardCommentFooter'})
        hide_link = Tag('hide link', 'a', text=re.compile(r'\s*Hide\s*'))
        reply_link = Tag('reply link', 'a', text='Reply')
        self.assertThat(
            browser.contents, HTMLContains(hide_link.within(footer)))
        self.assertThat(
            browser.contents, HTMLContains(reply_link.within(footer)))

    def test_footer_for_mergeable_and_non_admin(self):
        """A mortal sees a Reply link for a comment on a mergeable MP."""
        comment = self.makeCodeReviewComment()
        display_comment = CodeReviewDisplayComment(comment)
        browser = self.getViewBrowser(display_comment)
        footer = Tag('comment footer', 'div', {'class': 'boardCommentFooter'})
        hide_link = Tag('hide link', 'a', text=re.compile(r'\s*Hide\s*'))
        reply_link = Tag('reply link', 'a', text='Reply')
        self.assertThat(browser.contents, Not(HTMLContains(hide_link)))
        self.assertThat(
            browser.contents, HTMLContains(reply_link.within(footer)))

    def test_footer_for_non_mergeable_and_admin(self):
        """An admin sees a Hide link for a comment on a non-mergeable MP."""
        comment = self.makeCodeReviewComment()
        merge_proposal = comment.branch_merge_proposal
        with person_logged_in(merge_proposal.registrant):
            merge_proposal.markAsMerged(
                merge_reporter=merge_proposal.registrant)
        display_comment = CodeReviewDisplayComment(comment)
        browser = self.getViewBrowser(
            display_comment, user=self.factory.makeAdministrator())
        footer = Tag('comment footer', 'div', {'class': 'boardCommentFooter'})
        hide_link = Tag('hide link', 'a', text=re.compile(r'\s*Hide\s*'))
        reply_link = Tag('reply link', 'a', text='Reply')
        self.assertThat(
            browser.contents, HTMLContains(hide_link.within(footer)))
        self.assertThat(browser.contents, Not(HTMLContains(reply_link)))

    def test_no_footer_for_non_mergeable_and_non_admin(self):
        """A mortal sees no footer for a comment on a non-mergeable MP."""
        comment = self.makeCodeReviewComment()
        merge_proposal = comment.branch_merge_proposal
        with person_logged_in(merge_proposal.registrant):
            merge_proposal.markAsMerged(
                merge_reporter=merge_proposal.registrant)
        display_comment = CodeReviewDisplayComment(comment)
        browser = self.getViewBrowser(display_comment)
        footer = Tag('comment footer', 'div', {'class': 'boardCommentFooter'})
        self.assertThat(browser.contents, Not(HTMLContains(footer)))


class TestCodeReviewCommentHtmlBzr(
    TestCodeReviewCommentHtmlMixin, BrowserTestCase):

    def makeCodeReviewComment(self, **kwargs):
        return self.factory.makeCodeReviewComment(**kwargs)


class TestCodeReviewCommentHtmlGit(
    TestCodeReviewCommentHtmlMixin, BrowserTestCase):

    def makeCodeReviewComment(self, **kwargs):
        return self.factory.makeCodeReviewComment(git=True, **kwargs)
