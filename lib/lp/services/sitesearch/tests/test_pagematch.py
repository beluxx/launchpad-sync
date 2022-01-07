# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the search result PageMatch class."""

from testtools.matchers import MatchesStructure

from lp.services.sitesearch import (
    PageMatch,
    PageMatches,
    )
from lp.testing import TestCase


class TestPageMatchURLHandling(TestCase):

    def test_attributes(self):
        p = PageMatch(
            'Unicode Titles in Launchpad',
            'http://example.com/unicode-titles',
            'Unicode Titles is a modest project using Unicode.')
        self.assertThat(p, MatchesStructure.byEquality(
            title='Unicode Titles in Launchpad',
            summary='Unicode Titles is a modest project using Unicode.',
            url='http://example.com/unicode-titles',
            ))

    def test_rewrite_url(self):
        """The URL scheme used in the rewritten URL is configured via
        config.vhosts.use_https. The hostname is set in the shared
        key config.vhost.mainsite.hostname.
        """
        p = PageMatch(
            'Bug #456 in Unicode title: "testrunner hates Unicode"',
            'https://bugs.launchpad.net/unicode-titles/+bug/456',
            'The Zope testrunner likes ASCII more than Unicode.')
        self.assertEqual(
            'http://bugs.launchpad.test/unicode-titles/+bug/456', p.url)

    def test_rewrite_url_with_trailing_slash(self):
        """A URL's trailing slash is removed; Launchpad does not use trailing
        slashes.
        """
        p = PageMatch(
            'Ubuntu in Launchpad',
            'https://launchpad.net/ubuntu/',
            'Ubuntu also includes more software than any other operating')
        self.assertEqual('http://launchpad.test/ubuntu', p.url)

    def test_rewrite_url_exceptions(self):
        """There is a list of URLs that are not rewritten configured in
        config.sitesearch.url_rewrite_exceptions. For example,
        help.launchpad.net is only run in one environment, so links to
        that site will be preserved.
        """
        p = PageMatch(
            'OpenID',
            'https://help.launchpad.net/OpenID',
            'Launchpad uses OpenID.')
        self.assertEqual('https://help.launchpad.net/OpenID', p.url)

    def test_rewrite_url_handles_invalid_data(self):
        # Given a bad url, pagematch can get a valid one.
        bad_url = ("http://launchpad.test/+search?"
                   "field.text=WUSB54GC+ karmic&"
                   "field.actions.search=Search")
        p = PageMatch('Bad,', bad_url, 'Bad data')
        expected = ("http://launchpad.test/+search?"
                   "field.text=WUSB54GC++karmic&"
                   "field.actions.search=Search")
        self.assertEqual(expected, p.url)

    def test_rewrite_url_handles_invalid_data_partial_escaped(self):
        # Given a url with partial escaped values, pagematch does not error.
        partial_encoded_url = (
           "http://launchpad.test/+search?"
           "field.text=WUSB54GC+%2Bkarmic&"
           "field.actions.search=Search")
        p = PageMatch('Weird.', partial_encoded_url, 'Weird data')
        expected = (
            "http://launchpad.test/+search?"
            "field.text=WUSB54GC+%2Bkarmic&"
            "field.actions.search=Search")
        self.assertEqual(expected, p.url)


class TestPageMatches(TestCase):

    def test_initialisation(self):
        matches = PageMatches(['match1', 'match2', 'match3'], 12, 15)
        self.assertEqual(12, matches.start)
        self.assertEqual(15, matches.total)

    def test_len(self):
        matches = PageMatches(['match1', 'match2', 'match3'], 12, 15)
        self.assertEqual(3, len(matches))

    def test_getitem(self):
        matches = PageMatches(['match1', 'match2', 'match3'], 12, 15)
        self.assertEqual('match2', matches[1])

    def test_iter(self):
        matches = PageMatches(['match1', 'match2', 'match3'], 12, 15)
        self.assertEqual(
            ['match1', 'match2', 'match3'], [match for match in matches])
