# Copyright10 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version (see the file LICENSE).

"""Unit tests for bug supervisor views."""

__metaclass__ = type

import unittest

from zope.app.form.interfaces import ConversionError

from lp.bugs.browser.bugsupervisor import BugSupervisorEditSchema
from lp.testing import login, login_person, TestCaseWithFactory
from lp.testing.views import create_initialized_view
from canonical.testing import DatabaseFunctionalLayer


class TestBugSupervisorEditView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSupervisorEditView, self).setUp()
        self.owner = self.factory.makePerson(
            name='splat', displayname='<splat />')
        self.product = self.factory.makeProduct(
            name="boing", displayname='<boing />', owner=self.owner)
        self.team = self.factory.makeTeam(name='thud', owner=self.owner)
        login_person(self.owner)

    def _makeForm(self, person):
        if person is None:
            name = ''
        else:
            name = person.name
        return {
            'field.bug_supervisor': name,
            'field.actions.change': 'Change',
            }

    def test_view_attributes(self):
        self.product.displayname = 'Boing'
        view = create_initialized_view(
            self.product, name='+bugsupervisor')
        label = 'Edit bug supervisor for Boing'
        self.assertEqual(label, view.label)
        self.assertEqual(label, view.page_title)
        fields = ['bug_supervisor']
        self.assertEqual(fields, view.field_names)
        adapter, context = view.adapters.popitem()
        self.assertEqual(BugSupervisorEditSchema, adapter)
        self.assertEqual(self.product, context)
        self.assertEqual('http://launchpad.dev/boing', view.next_url)
        self.assertEqual('http://launchpad.dev/boing', view.cancel_url)

    def test_owner_appoint_self_from_none(self):
        # This also verifies that displaynames are escaped.
        form = self._makeForm(self.owner)
        view = create_initialized_view(
            self.product, name='+bugsupervisor', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(self.product.bug_supervisor, self.owner)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = (
            'Successfully changed the bug supervisor to '
            '<a href="http://launchpad.dev/~splat">&lt;splat /&gt;</a>.'
            '<br /><a href="http://launchpad.dev/~splat">&lt;splat /&gt;</a> '
            'has also been subscribed to bug notifications for '
            '&lt;boing /&gt;.<br />You can '
            '<a href="http://launchpad.dev/boing/+subscribe">change '
            'the subscriptions</a> for &lt;boing /&gt; at any time.')
        self.assertEqual(expected, notifications.pop().message)

    def test_owner_appoint_self_from_another(self):
        self.product.setBugSupervisor(self.team, self.owner)
        form = self._makeForm(self.owner)
        view = create_initialized_view(
            self.product, name='+bugsupervisor', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(self.product.bug_supervisor, self.owner)

    def test_owner_appoint_none(self):
        self.product.setBugSupervisor(self.owner, self.owner)
        form = self._makeForm(None)
        view = create_initialized_view(
            self.product, name='+bugsupervisor', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(self.product.bug_supervisor, None)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = (
            'Successfully cleared the bug supervisor. '
            'You can set the bug supervisor again at any time.')
        self.assertEqual(expected, notifications.pop().message)

    def test_owner_appoint_his_team(self):
        form = self._makeForm(self.team)
        view = create_initialized_view(
            self.product, name='+bugsupervisor', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(self.product.bug_supervisor, self.team)

    def test_owner_cannot_appoint_another_team(self):
        team = self.factory.makeTeam(name='smack', displayname='<smack />')
        form = self._makeForm(team)
        view = create_initialized_view(
            self.product, name='+bugsupervisor', form=form)
        self.assertEqual(1, len(view.errors))
        expected = (
            'You cannot set &lt;smack /&gt; as the bug supervisor for '
            '&lt;boing /&gt; because you are not an administrator of that '
            'team.<br />If you believe that &lt;smack /&gt; should be the '
            'bug supervisor for &lt;boing /&gt;, notify one of the '
            '<a href="http://launchpad.dev/~smack/+members">&lt;smack /&gt; '
            'administrators</a>. See '
            '<a href="https://help.launchpad.net/BugSupervisors">the '
            'help wiki</a> for information about setting a bug supervisor.')
        self.assertEqual(expected, view.errors.pop())

    def test_owner_cannot_appoint_a_nonvalid_user(self):
        form = self._makeForm(None)
        form['field.bug_supervisor'] = 'fnord'
        view = create_initialized_view(
            self.product, name='+bugsupervisor', form=form)
        self.assertEqual(2, len(view.errors))
        expected = (
            'You must choose a valid person or team to be the bug supervisor '
            'for &lt;boing /&gt;.')
        self.assertEqual(expected, view.errors.pop())
        self.assertTrue(isinstance(view.errors.pop(), ConversionError))

    def test_owner_cannot_appoint_another_user(self):
        another_user = self.factory.makePerson(name='smack')
        form = self._makeForm(another_user)
        view = create_initialized_view(
            self.product, name='+bugsupervisor', form=form)
        self.assertEqual(1, len(view.errors))
        expected = (
            'You cannot set another person as the bug supervisor for '
            '&lt;boing /&gt;.<br />See '
            '<a href="https://help.launchpad.net/BugSupervisors">the help '
            'wiki</a> for information about setting a bug supervisor.')
        self.assertEqual(expected, view.errors.pop())

    def test_admin_appoint_another_user(self):
        another_user = self.factory.makePerson(name='smack')
        login('admin@canonical.com')
        form = self._makeForm(another_user)
        view = create_initialized_view(
            self.product, name='+bugsupervisor', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(self.product.bug_supervisor, another_user)

    def test_admin_appoint_another_team(self):
        another_team = self.factory.makeTeam(name='smack')
        login('admin@canonical.com')
        form = self._makeForm(another_team)
        view = create_initialized_view(
            self.product, name='+bugsupervisor', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(self.product.bug_supervisor, another_team)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
