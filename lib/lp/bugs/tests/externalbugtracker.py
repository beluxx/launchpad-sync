# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper classes for testing ExternalSystem."""

from contextlib import contextmanager
from copy import deepcopy
from datetime import (
    datetime,
    timedelta,
    )
from operator import itemgetter
import os
import random
import re
import time
import xmlrpc.client

import responses
from six.moves.urllib_parse import (
    parse_qs,
    urljoin,
    urlsplit,
    )
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.bugs.externalbugtracker import (
    BATCH_SIZE_UNLIMITED,
    BugNotFound,
    BugTrackerConnectError,
    Bugzilla,
    DebBugs,
    ExternalBugTracker,
    Mantis,
    RequestTracker,
    Roundup,
    SourceForge,
    Trac,
    )
from lp.bugs.externalbugtracker.trac import (
    FAULT_TICKET_NOT_FOUND,
    LP_PLUGIN_BUG_IDS_ONLY,
    LP_PLUGIN_FULL,
    LP_PLUGIN_METADATA_AND_COMMENTS,
    LP_PLUGIN_METADATA_ONLY,
    )
from lp.bugs.externalbugtracker.xmlrpc import RequestsTransport
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.bugs.interfaces.bugtracker import IBugTrackerSet
from lp.bugs.interfaces.externalbugtracker import (
    UNKNOWN_REMOTE_IMPORTANCE,
    UNKNOWN_REMOTE_STATUS,
    )
from lp.bugs.model.bugtracker import BugTracker
from lp.bugs.scripts import debbugs
from lp.bugs.xmlrpc.bug import ExternalBugTrackerTokenAPI
from lp.registry.interfaces.person import IPersonSet
from lp.services.verification.interfaces.logintoken import ILoginTokenSet
from lp.testing import admin_logged_in
from lp.testing.dbuser import lp_dbuser
from lp.testing.systemdocs import ordered_dict_as_string


def new_bugtracker(bugtracker_type, base_url='http://bugs.some.where'):
    """Create a new bug tracker using the 'launchpad db user.

    Before calling this function, the current transaction should be
    commited, since the current connection to the database will be
    closed. After returning from this function, a new connection using
    the checkwatches db user is created.
    """
    with lp_dbuser():
        owner = getUtility(IPersonSet).getByEmail('no-priv@canonical.com')
        bugtracker_set = getUtility(IBugTrackerSet)
        index = 1
        name = '%s-checkwatches' % (bugtracker_type.name.lower())
        while bugtracker_set.getByName("%s-%d" % (name, index)) is not None:
            index += 1
        name += '-%d' % index
        BugTracker(
            name=name,
            title='%s *TESTING*' % (bugtracker_type.title),
            bugtrackertype=bugtracker_type,
            baseurl=base_url,
            summary='-', contactdetails='-',
            owner=owner)
    return getUtility(IBugTrackerSet).getByName(name)


def read_test_file(name):
    """Return the contents of the test file named :name:"""
    file_path = os.path.join(os.path.dirname(__file__), 'testfiles', name)

    with open(file_path) as test_file:
        return test_file.read()


def print_bugwatches(bug_watches, convert_remote_status=None):
    """Print the bug watches for a BugTracker, ordered by remote bug id.

    :bug_watches: A set of BugWatches to print.

    :convert_remote_status: A convertRemoteStatus method from an
        ExternalBugTracker instance, which will convert a bug's remote
        status into a Launchpad BugTaskStatus. See
        `ExternalBugTracker.convertRemoteStatus()`.

    Bug watches will be printed in the form: Remote bug <id>:
    <remote_status>. If convert_remote_status is callable it will be
    used to convert the watches' remote statuses to Launchpad
    BugTaskStatuses and these will be output instead.
    """
    watches = {int(bug_watch.remotebug): bug_watch
        for bug_watch in bug_watches}

    for remote_bug_id in sorted(watches.keys()):
        status = watches[remote_bug_id].remotestatus
        if callable(convert_remote_status):
            status = convert_remote_status(status)

        print('Remote bug %d: %s' % (remote_bug_id, status))


def convert_python_status(status, resolution):
    """Convert a human readable status and resolution into a Python
    bugtracker status and resolution string.
    """
    status_map = {'open': 1, 'closed': 2, 'pending': 3}
    resolution_map = {
        'None': 'None',
        'accepted': 1,
        'duplicate': 2,
        'fixed': 3,
        'invalid': 4,
        'later': 5,
        'out-of-date': 6,
        'postponed': 7,
        'rejected': 8,
        'remind': 9,
        'wontfix': 10,
        'worksforme': 11,
        }

    return "%s:%s" % (status_map[status], resolution_map[resolution])


def set_bugwatch_error_type(bug_watch, error_type):
    """Set the last_error_type field of a bug watch to a given error type."""
    naked = removeSecurityProxy(bug_watch)
    naked.remotestatus = None
    naked.last_error_type = error_type
    with admin_logged_in():
        naked.updateStatus(UNKNOWN_REMOTE_STATUS, BugTaskStatus.UNKNOWN)


class BugTrackerResponsesMixin:
    """A responses-based test mixin for bug trackers.

    The simplest way to use this is as a context manager:

        with bug_tracker.responses():
            ...

    Classes using this mixin should implement `addResponses`.
    """

    def addResponses(self, requests_mock, **kwargs):
        """Add test responses."""

    @contextmanager
    def responses(self, trace_calls=False, **kwargs):
        with responses.RequestsMock() as requests_mock:
            self.addResponses(requests_mock, **kwargs)
            yield requests_mock
            if trace_calls:
                for call in requests_mock.calls:
                    print(call.request.method, call.request.url)


class TestExternalBugTracker(ExternalBugTracker):
    """A test version of `ExternalBugTracker`.

    Implements all the methods required of an `IExternalBugTracker`
    implementation, though it doesn't actually do anything.
    """

    batch_size = BATCH_SIZE_UNLIMITED

    def __init__(self, baseurl='http://example.com/'):
        super().__init__(baseurl)

    def getRemoteBug(self, remote_bug):
        """Return the tuple (None, None) as a representation of a remote bug.

        We add this method here to prevent tests which need to call it,
        but which make no use of the output, from failing.
        """
        return None, None

    def convertRemoteStatus(self, remote_status):
        """Always return UNKNOWN_REMOTE_STATUS.

        This method exists to satisfy the implementation requirements of
        `IExternalBugTracker`.
        """
        return BugTaskStatus.UNKNOWN

    def getRemoteImportance(self, bug_id):
        """Stub implementation."""
        return UNKNOWN_REMOTE_IMPORTANCE

    def convertRemoteImportance(self, remote_importance):
        """Stub implementation."""
        return BugTaskImportance.UNKNOWN

    def getRemoteStatus(self, bug_id):
        """Stub implementation."""
        return UNKNOWN_REMOTE_STATUS


class TestBrokenExternalBugTracker(TestExternalBugTracker):
    """A test version of ExternalBugTracker, designed to break."""

    initialize_remote_bugdb_error = None
    get_remote_status_error = None

    def initializeRemoteBugDB(self, bug_ids):
        """Raise the error specified in initialize_remote_bugdb_error.

        If initialize_remote_bugdb_error is None, None will be returned.
        See `ExternalBugTracker`.
        """
        if self.initialize_remote_bugdb_error:
            # We have to special case BugTrackerConnectError as it takes
            # two non-optional arguments.
            if self.initialize_remote_bugdb_error is BugTrackerConnectError:
                raise self.initialize_remote_bugdb_error(
                    "http://example.com", "Testing")
            else:
                raise self.initialize_remote_bugdb_error("Testing")

    def getRemoteStatus(self, bug_id):
        """Raise the error specified in get_remote_status_error.

        If get_remote_status_error is None, None will be returned.
        See `ExternalBugTracker`.
        """
        if self.get_remote_status_error:
            raise self.get_remote_status_error("Testing")


class TestBugzilla(BugTrackerResponsesMixin, Bugzilla):
    """Bugzilla ExternalSystem for use in tests."""
    # We set the batch_query_threshold to zero so that only
    # getRemoteBugBatch() is used to retrieve bugs, since getRemoteBug()
    # calls getRemoteBugBatch() anyway.
    batch_query_threshold = 0
    trace_calls = False

    version_file = 'gnome_bugzilla_version.xml'
    buglist_file = 'gnome_buglist.xml'
    bug_item_file = 'gnome_bug_li_item.xml'

    buglist_page = 'buglist.cgi'
    bug_id_form_element = 'bug_id'

    def __init__(self, baseurl='http://bugzilla.example.com/', version=None):
        Bugzilla.__init__(self, baseurl, version=version)
        self.bugzilla_bugs = self._getBugsToTest()

    def getExternalBugTrackerToUse(self):
        # Always return self here since we test this separately.
        return self

    def _getBugsToTest(self):
        """Return a dict with bugs in the form
           bug_id: (status, resolution, priority, severity)"""
        return {3224: ('RESOLVED', 'FIXED', 'MINOR', 'URGENT'),
                328430: ('UNCONFIRMED', '', 'MEDIUM', 'NORMAL')}

    def _readBugItemFile(self):
        """Reads in the file for an individual bug item.

        This method exists really only to allow us to check that the
        file is being used. So what?
        """
        return read_test_file(self.bug_item_file)

    def _getCallback(self, request):
        """Handle a test GET request.

        Only handles xml.cgi?id=1 so far.
        """
        url = urlsplit(request.url)
        if (url.path == urlsplit(self.baseurl).path + '/xml.cgi' and
                parse_qs(url.query).get('id') == ['1']):
            body = read_test_file(self.version_file).encode('UTF-8')
            # Add some latin1 to test bug 61129
            return 200, {}, body % {b'non_ascii_latin1': b'\xe9'}
        else:
            raise AssertionError('Unknown URL: %s' % request.url)

    def _postCallback(self, request):
        """Handle a test POST request.

        Only handles buglist.cgi so far.
        """
        url = urlsplit(request.url)
        if url.path == urlsplit(self.baseurl).path + '/' + self.buglist_page:
            buglist_xml = read_test_file(self.buglist_file)
            form = parse_qs(request.body)
            bug_ids = str(form[self.bug_id_form_element][0]).split(',')
            bug_li_items = []
            for bug_id in bug_ids:
                bug_id = int(bug_id)
                if bug_id not in self.bugzilla_bugs:
                    # Unknown bugs aren't included in the resulting xml.
                    continue
                bug_status, bug_resolution, bug_priority, bug_severity = (
                    self.bugzilla_bugs[int(bug_id)])
                bug_item = self._readBugItemFile() % {
                    'bug_id': bug_id,
                    'status': bug_status,
                    'resolution': bug_resolution,
                    'priority': bug_priority,
                    'severity': bug_severity,
                    }
                bug_li_items.append(bug_item)
            body = buglist_xml % {
                'bug_li_items': '\n'.join(bug_li_items),
                'page': url.path.lstrip('/'),
                }
            return 200, {}, body
        else:
            raise AssertionError('Unknown URL: %s' % request.url)

    def addResponses(self, requests_mock, get=True, post=True):
        """Add test responses."""
        if get:
            requests_mock.add_callback(
                'GET', re.compile(r'.*'), self._getCallback)
        if post:
            requests_mock.add_callback(
                'POST', re.compile(r'.*'), self._postCallback)


class TestWeirdBugzilla(TestBugzilla):
    """Test support for a few corner cases in Bugzilla.

        - UTF8 data in the files being parsed.
        - bz:status instead of bz:bug_status
    """
    bug_item_file = 'weird_non_ascii_bug_li_item.xml'

    def _getBugsToTest(self):
        return {2000: ('ASSIGNED', '', 'HIGH', 'BLOCKER'),
                123543: ('RESOLVED', 'FIXED', 'HIGH', 'BLOCKER')}


class TestBrokenBugzilla(TestBugzilla):
    """Test parsing of a Bugzilla which returns broken XML."""
    bug_item_file = 'broken_bug_li_item.xml'

    def _getBugsToTest(self):
        return {42: ('ASSIGNED', '', 'HIGH', 'BLOCKER'),
                2000: ('RESOLVED', 'FIXED', 'LOW', 'BLOCKER')}


class AnotherBrokenBugzilla(TestBrokenBugzilla):
    """Test parsing of a Bugzilla which returns broken XML."""
    bug_item_file = 'unescaped_control_character.xml'


class TestIssuezilla(TestBugzilla):
    """Test support for Issuezilla, with slightly modified XML."""
    version_file = 'issuezilla_version.xml'
    buglist_file = 'issuezilla_buglist.xml'
    bug_item_file = 'issuezilla_item.xml'

    buglist_page = 'xml.cgi'
    bug_id_form_element = 'id'

    def _getBugsToTest(self):
        return {2000: ('RESOLVED', 'FIXED', 'LOW', 'BLOCKER'),
                123543: ('ASSIGNED', '', 'HIGH', 'BLOCKER')}


class TestOldBugzilla(TestBugzilla):
    """Test support for older Bugzilla versions."""
    version_file = 'ximian_bugzilla_version.xml'
    buglist_file = 'ximian_buglist.xml'
    bug_item_file = 'ximian_bug_item.xml'

    buglist_page = 'xml.cgi'
    bug_id_form_element = 'id'

    def _getBugsToTest(self):
        return {42: ('RESOLVED', 'FIXED', 'LOW', 'BLOCKER'),
                123543: ('ASSIGNED', '', 'HIGH', 'BLOCKER')}


class TestBugzillaXMLRPCTransport(RequestsTransport):
    """A test implementation of the Bugzilla XML-RPC interface."""

    local_datetime = None
    timezone = 'UTC'
    utc_offset = 0
    print_method_calls = False

    _bugs = {
        1: {'alias': '',
            'assigned_to': 'test@canonical.com',
            'component': 'GPPSystems',
            'creation_time': datetime(2008, 6, 10, 16, 19, 53),
            'id': 1,
            'internals': {},
            'is_open': True,
            'last_change_time': datetime(2008, 6, 10, 16, 19, 53),
            'priority': 'P1',
            'product': 'Marvin',
            'resolution': 'FIXED',
            'see_also': [],
            'severity': 'normal',
            'status': 'RESOLVED',
            'summary': "That bloody robot still exists.",
            },
        2: {'alias': 'bug-two',
            'assigned_to': 'marvin@heartofgold.ship',
            'component': 'Crew',
            'creation_time': datetime(2008, 6, 11, 9, 23, 12),
            'id': 2,
            'internals': {},
            'is_open': True,
            'last_change_time': datetime(2008, 6, 11, 9, 24, 29),
            'priority': 'P1',
            'product': 'HeartOfGold',
            'resolution': '',
            'see_also': [],
            'severity': 'high',
            'status': 'NEW',
            'summary': 'Collect unknown persons in docking bay 2.',
            },
        3: {'alias': ['bug-three', 'bad-diodes'],
            'assigned_to': 'marvin@heartofgold.ship',
            'component': 'Crew',
            'creation_time': datetime(2008, 6, 10, 9, 23, 12),
            'id': 3,
            'internals': {},
            'is_open': True,
            'last_change_time': datetime(2008, 6, 10, 9, 24, 29),
            'priority': 'P1',
            'product': 'Marvin',
            'resolution': '',
            'see_also': [],
            'severity': 'high',
            'status': 'NEW',
            'summary': "Pain in all the diodes down my left hand side.",
            },
        }

    # Map aliases onto bugs.
    _bug_aliases = {
        'bug-two': 2,
        'bug-three': 3,
        'bad-diodes': 3,
        }

    # Comments are mapped to bug IDs.
    comment_id_index = 6
    new_comment_time = datetime(2008, 6, 20, 11, 42, 42)
    _bug_comments = {
        1: {
            1: {'author': 'trillian',
                'id': 1,
                'number': 1,
                'text': "I'd really appreciate it if Marvin would "
                        "enjoy life a bit.",
                'time': datetime(2008, 6, 16, 12, 44, 29),
                },
            2: {'author': 'marvin',
                'id': 3,
                'number': 2,
                'text': "Life? Don't talk to me about life.",
                'time': datetime(2008, 6, 16, 13, 22, 29),
                },
            },
        2: {
            1: {'author': 'trillian',
                'id': 2,
                'number': 1,
                'text': "Bring the passengers to the bridge please Marvin.",
                'time': datetime(2008, 6, 16, 13, 8, 8),
                },
             2: {'author': 'Ford Prefect <ford.prefect@h2g2.com>',
                'id': 4,
                'number': 2,
                'text': "I appear to have become a perfectly safe penguin.",
                'time': datetime(2008, 6, 17, 20, 28, 40),
                },
            },
        }

    # Map namespaces onto method names.
    methods = {
        'Launchpad': (
            'add_comment',
            'comments',
            'get_bugs',
            'login',
            'time',
            'set_link',
            ),
        'Test': ['login_required'],
        }

    # Methods that require authentication.
    auth_required_methods = (
        'add_comment',
        'login_required',
        'set_link',
        )

    expired_cookie = None

    def __init__(self, *args, **kwargs):
        """Ensure mutable class data is copied to the instance."""
        # RequestsTransport is not a new-style class so 'super' cannot be
        # used.
        RequestsTransport.__init__(self, *args, **kwargs)
        self.bugs = deepcopy(TestBugzillaXMLRPCTransport._bugs)
        self.bug_aliases = deepcopy(self._bug_aliases)
        self.bug_comments = deepcopy(self._bug_comments)

    def expireCookie(self, cookie):
        """Mark the cookie as expired."""
        self.expired_cookie = cookie

    @property
    def auth_cookie(self):
        if len({cookie.domain for cookie in self.cookie_jar}) > 1:
            raise AssertionError(
                "There should only be cookies for one domain.")

        for cookie in self.cookie_jar:
            if cookie.name == 'Bugzilla_logincookie':
                return cookie
        else:
            return None

    @property
    def has_valid_auth_cookie(self):
        return (self.auth_cookie is not None and
                self.auth_cookie is not self.expired_cookie)

    def request(self, host, handler, request, verbose=None):
        """Call the corresponding XML-RPC method.

        The method name and arguments are extracted from `request`. The
        method on this class with the same name as the XML-RPC method is
        called, with the extracted arguments passed on to it.
        """
        args, method_name = xmlrpc.client.loads(request)
        method_prefix, method_name = method_name.split('.')

        assert method_prefix in self.methods, (
            "All methods should be in one of the following namespaces: %s"
            % self.methods.keys())

        assert method_name in self.methods[method_prefix], (
            "No method '%s' in namespace '%s'." %
            (method_name, method_prefix))

        # If the method requires authentication and we have no auth
        # cookie, throw a Fault.
        if (method_name in self.auth_required_methods and
            not self.has_valid_auth_cookie):
            raise xmlrpc.client.Fault(410, 'Login Required')

        if self.print_method_calls:
            if len(args) > 0:
                arguments = ordered_dict_as_string(args[0])
            else:
                arguments = ''

            print("CALLED %s.%s(%s)" % (method_prefix, method_name, arguments))

        method = getattr(self, method_name)
        return method(*args)

    def time(self):
        """Return a dict of the local time, UTC time and the timezone."""
        local_datetime = self.local_datetime
        if local_datetime is None:
            local_datetime = datetime(2008, 5, 1, 1, 1, 1)

        utc_offset_delta = timedelta(seconds=self.utc_offset)
        utc_date_time = local_datetime - utc_offset_delta

        return {
            'local_time': local_datetime,
            'utc_time': utc_date_time,
            'tz_name': self.timezone,
            }

    def login_required(self):
        # This method only exists to demonstrate login required methods.
        return "Wonderful, you've logged in! Aren't you a clever biped?"

    def _consumeLoginToken(self, token_text):
        """Try to consume a login token."""
        token = getUtility(ILoginTokenSet)[token_text]

        if token.tokentype.name != 'BUGTRACKER':
            raise AssertionError(
                'Invalid token type: %s' % token.tokentype.name)
        if token.date_consumed is not None:
            raise AssertionError("Token has already been consumed.")
        token.consume()

        if self.print_method_calls:
            print("Successfully validated the token.")

    def _handleLoginToken(self, token_text):
        """A wrapper around _consumeLoginToken().

        We can override this method when we need to do things Zopelessly.
        """
        self._consumeLoginToken(token_text)

    def login(self, arguments):
        token_text = arguments['token']
        self._handleLoginToken(token_text)
        self._setAuthCookie()

        # We always return the same user ID.
        # This has to be listified because xmlrpc.client tries to expand
        # sequences of length 1.
        return [{'user_id': 42}]

    def _setAuthCookie(self):
        # Generate some random cookies to use.
        random_cookie_1 = str(random.random())
        random_cookie_2 = str(random.random())

        self.setCookie('Bugzilla_login=%s;' % random_cookie_1)
        self.setCookie('Bugzilla_logincookie=%s;' % random_cookie_2)

    def get_bugs(self, arguments):
        """Return a list of bug dicts for a given set of bug IDs."""
        bug_ids = arguments.get('ids')
        products = arguments.get('products')

        assert bug_ids is not None or products is not None, (
            "One of ('ids', 'products') should be specified")

        bugs_to_return = []

        # We enforce permissiveness, since we'll always call this method
        # with permissive=True in the Real World.
        permissive = arguments.get('permissive', False)
        assert permissive, "get_bugs() must be called with permissive=True"

        # If a changed_since argument is specified, marshall it into a
        # datetime so that we can use it for comparisons. Even though
        # xmlrpclib in Python 2.5 groks datetime, by the time this
        # method is called xmlrpclib has already converted all
        # datetimes to xmlrpclib.DateTime.
        changed_since = arguments.get('changed_since')
        if changed_since is not None:
            changed_since = datetime.strptime(
                changed_since.value, '%Y%m%dT%H:%M:%S')

        # If we have some products but no bug_ids we just get all the
        # bug IDs for those products and stuff them in the bug_ids list
        # for processing below.
        if bug_ids is None:
            bug_ids = [
                bug_id for bug_id, bug in self.bugs.items()
                    if bug['product'] in products]

        for id in bug_ids:
            # If the ID is an int, look up the bug directly. We copy the
            # bug dict into a local variable so we can manipulate the
            # data in it.
            try:
                id = int(id)
                bug_dict = dict(self.bugs[int(id)])
            except ValueError:
                bug_dict = dict(self.bugs[self.bug_aliases[id]])
            except KeyError:
                # We ignore KeyErrors (since permissive == True, which
                # means that we ignore invalid bug IDs).
                continue

            # If changed_since is specified, discard all the bugs whose
            # last_change_time is < changed_since.
            if (changed_since is not None and
                bug_dict['last_change_time'] < changed_since):
                continue

            # If the bug doesn't belong to one of the products in the
            # products list, ignore it.
            if (products is not None and
                bug_dict['product'] not in products):
                continue

            bugs_to_return.append(bug_dict)

        # "Why are you returning a list here?" I hear you cry. Well,
        # dear reader, it's because xmlrpclib:1387 tries to expand
        # sequences of length 1. When you return a dict, that line
        # explodes in your face. Annoying? Insane? You bet.
        return [{'bugs': bugs_to_return}]

    def _copy_comment(self, comment, fields_to_return=None):
        # Copy wanted fields.
        return {
            key: value for (key, value) in comment.items()
            if fields_to_return is None or key in fields_to_return}

    def comments(self, arguments):
        """Return comments for a given set of bugs."""
        # We'll always pass bug IDs when we call comments().
        assert 'bug_ids' in arguments, (
            "Bug.comments() must always be called with a bug_ids parameter.")

        bug_ids = arguments['bug_ids']
        comment_ids = arguments.get('ids')
        fields_to_return = arguments.get('include_fields')
        comments_by_bug_id = {}

        for bug_id in bug_ids:
            comments_for_bug = self.bug_comments[bug_id].values()

            # We stringify bug_id when using it as a dict key because
            # all XML-RPC dict keys are strings (a key for an XML-RPC
            # dict can have a value but no type; hence Python defaults
            # to treating them as strings).
            comments_by_bug_id[str(bug_id)] = [
                self._copy_comment(comment, fields_to_return)
                for comment in comments_for_bug
                if comment_ids is None or comment['id'] in comment_ids]

        # More xmlrpclib:1387 odd-knobbery avoidance.
        return [{'bugs': comments_by_bug_id}]

    def add_comment(self, arguments):
        """Add a comment to a bug."""
        assert 'id' in arguments, (
            "Bug.add_comment() must always be called with an id parameter.")
        assert 'comment' in arguments, (
            "Bug.add_comment() must always be called with a comment "
            "parameter.")

        bug_id = arguments['id']
        comment = arguments['comment']

        # If the bug doesn't exist, raise a fault.
        if int(bug_id) not in self.bugs:
            raise xmlrpc.client.Fault(101, "Bug #%s does not exist." % bug_id)

        # If we don't have comments for the bug already, create an empty
        # comment dict.
        if bug_id not in self.bug_comments:
            self.bug_comments[bug_id] = {}

        # Work out the number for the new comment on that bug.
        if len(self.bug_comments[bug_id]) == 0:
            comment_number = 1
        else:
            comment_numbers = sorted(self.bug_comments[bug_id].keys())
            latest_comment_number = comment_numbers[-1]
            comment_number = latest_comment_number + 1

        # Add the comment to the bug.
        comment_id = self.comment_id_index + 1
        comment_dict = {
            'author': 'launchpad',
            'id': comment_id,
            'number': comment_number,
            'time': self.new_comment_time,
            'text': comment,
            }
        self.bug_comments[bug_id][comment_number] = comment_dict

        self.comment_id_index = comment_id

        # We have to return a list here because xmlrpc.client will try to
        # expand sequences of length 1. Trying to do that on a dict will
        # cause it to explode.
        return [{'comment_id': comment_id}]

    def set_link(self, arguments):
        """Set the Launchpad bug ID for a given Bugzilla bug.

        :returns: The current Launchpad bug ID for the Bugzilla bug or
            0 if one is not set.
        """
        bug_id = int(arguments['id'])
        launchpad_id = arguments['launchpad_id']

        # Extract the current launchpad_id from the bug, then update
        # that field.
        bug = self.bugs[bug_id]
        old_launchpad_id = bug['internals'].get('launchpad_id', 0)
        bug['internals']['launchpad_id'] = launchpad_id

        # We need to return a list here because xmlrpc.client will try to
        # expand sequences of length 1, which will fail horribly when
        # the sequence is in fact a dict.
        return [{'launchpad_id': old_launchpad_id}]


class TestBugzillaAPIXMLRPCTransport(TestBugzillaXMLRPCTransport):
    """A test implementation of the Bugzilla 3.4 XML-RPC API."""

    # Map namespaces onto method names.
    methods = {
        'Bug': [
            'add_comment',
            'comments',
            'get',
            'search',
            'update_see_also',
            ],
        'Bugzilla': [
            'time',
            'version',
            ],
        'Test': ['login_required'],
        'User': ['login'],
        }

    # Methods that require authentication.
    auth_required_methods = [
        'add_comment',
        'login_required',
        ]

    # The list of users that can log in.
    users = [
        {'login': 'foo.bar@canonical.com', 'password': 'test'},
        ]

    # A list of comments on bugs.
    _bug_comments = {
        1: {
            1: {'author': 'trillian',
                'bug_id': 1,
                'id': 1,
                'is_private': False,
                'text': "I'd really appreciate it if Marvin would "
                        "enjoy life a bit.",
                'time': datetime(2008, 6, 16, 12, 44, 29),
                },
            2: {'author': 'marvin',
                'bug_id': 1,
                'id': 3,
                'is_private': False,
                'text': "Life? Don't talk to me about life.",
                'time': datetime(2008, 6, 16, 13, 22, 29),
                },
            },
        2: {
            1: {'author': 'trillian',
                'bug_id': 2,
                'id': 2,
                'is_private': False,
                'text': "Bring the passengers to the bridge please Marvin.",
                'time': datetime(2008, 6, 16, 13, 8, 8),
                },
            2: {'author': 'Ford Prefect <ford.prefect@h2g2.com>',
                'bug_id': 2,
                'id': 4,
                'is_private': False,
                'text': "I appear to have become a perfectly safe penguin.",
                'time': datetime(2008, 6, 17, 20, 28, 40),
                },
            3: {'author': 'arthur.dent@earth.example.com',
                'bug_id': 2,
                'id': 5,
                'is_private': False,
                'text': "I never could get the hang of Thursdays.",
                'time': datetime(2008, 6, 19, 9, 30, 0),
                },
            4: {'creator': 'Slartibartfast <slarti@magrathea.example.net>',
                'bug_id': 2,
                'id': 6,
                'is_private': False,
                'text': (
                    "You know the fjords in Norway?  I got a prize for "
                    "creating those, you know."),
                'time': datetime(2008, 6, 20, 12, 37, 0),
                },
            },
        }

    include_utc_time_fields = True

    def __init__(self, *args, **kwargs):
        """Ensure mutable class data is copied to the instance."""
        TestBugzillaXMLRPCTransport.__init__(self, *args, **kwargs)

    def version(self):
        """Return the version of Bugzilla being used."""
        # This is to work around the old "xmlrpc.client tries to expand
        # sequences of length 1" problem (see above).
        return [{'version': '3.4.1+'}]

    def login(self, arguments):
        login = arguments['login']
        password = arguments['password']

        # Clear the old login cookie for the sake of being thorough.
        self.expireCookie(self.auth_cookie)

        for user in self.users:
            if user['login'] == login and user['password'] == password:
                self._setAuthCookie()
                return [{'id': self.users.index(user)}]
            else:
                raise xmlrpc.client.Fault(
                    300,
                    "The username or password you entered is not valid.")

    def time(self):
        """Return a dict of the local time and associated data."""
        # We cheat slightly by calling the superclass to get the time
        # data. We do this the old fashioned way because XML-RPC
        # Transports don't support new-style classes.
        time_dict = TestBugzillaXMLRPCTransport.time(self)

        if self.include_utc_time_fields:
            # Bugzilla < 5.1.1 (although as of 3.6 the UTC offset is always
            # 0).
            offset_hours = (self.utc_offset / 60) / 60
            offset_string = '+%02d00' % offset_hours
            return {
                'db_time': time_dict['local_time'],
                'tz_name': time_dict['tz_name'],
                'tz_offset': offset_string,
                'tz_short_name': time_dict['tz_name'],
                'web_time': time_dict['local_time'],
                'web_time_utc': time_dict['utc_time'],
                }
        else:
            # Bugzilla >= 5.1.1.
            return {
                'db_time': time_dict['utc_time'],
                'web_time': time_dict['utc_time'],
                }

    def get(self, arguments):
        """Return a list of bug dicts for a given set of bug ids."""
        # This method is actually just a synonym for get_bugs().
        return self.get_bugs(arguments)

    def search(self, arguments):
        """Return a list of bug dicts that match search criteria."""
        assert 'permissive' not in arguments, (
            "You can't pass 'permissive' to Bug.search()")

        search_args = {'permissive': True}

        # Convert the search arguments into something that get_bugs()
        # understands. This may seem like a hack, but since we're only
        # trying to simulate the way Bugzilla behaves it doesn't really
        # matter that we just pass the buck to get_bugs().
        if arguments.get('last_change_time') is not None:
            search_args['changed_since'] = arguments['last_change_time']

        if arguments.get('id') is not None:
            search_args['ids'] = arguments['id']
        else:
            search_args['ids'] = [
                bug_id for bug_id in self.bugs]

        if arguments.get('product') is not None:
            product_list = arguments['product']
            assert isinstance(product_list, list), (
                "product parameter must be a list.")

            search_args['products'] = product_list

        return self.get_bugs(search_args)

    def comments(self, arguments):
        """Return comments for a given set of bugs."""
        # Turn the arguments into something that
        # TestBugzillaXMLRPCTransport.comments() will understand and
        # then pass the buck.
        comments_args = dict(arguments)
        fields_to_return = arguments.get('include_fields')
        if arguments.get('ids') is not None:
            # We nuke the 'ids' argument because it means something
            # different when passed to TestBugzillaXMLRPCTransport.comments.
            del comments_args['ids']
            comments_args['bug_ids'] = arguments['ids']
            [returned_dict] = TestBugzillaXMLRPCTransport.comments(
                self, comments_args)

            # We need to move the comments for each bug in to a
            # 'comments' dict.
            bugs_dict = returned_dict['bugs']
            bug_comments_dict = {}
            for bug_id, comment_list in bugs_dict.items():
                bug_comments_dict[bug_id] = {'comments': comment_list}

            return_dict = {'bugs': bug_comments_dict}
        else:
            return_dict = {'bugs': {}}

        if arguments.get('comment_ids') is not None:
            # We need to return all the comments listed.
            comments_to_return = {}
            for bug_id, comments in self.bug_comments.items():
                for comment_number, comment in comments.items():
                    if comment['id'] in arguments['comment_ids']:
                        comments_to_return[comment['id']] = (
                            self._copy_comment(comment, fields_to_return))

            return_dict['comments'] = comments_to_return

        # Stop xmlrpclib:1387 from throwing a wobbler at having a
        # length-1 dict to deal with.
        return [return_dict]

    def add_comment(self, arguments):
        """Add a comment to a bug."""
        assert 'id' in arguments, (
            "Bug.add_comment() must always be called with an id parameter.")
        assert 'comment' in arguments, (
            "Bug.add_comment() must always be called with an comment "
            "parameter.")

        bug_id = arguments['id']
        comment = arguments['comment']

        # If the bug doesn't exist, raise a fault.
        if int(bug_id) not in self.bugs:
            raise xmlrpc.client.Fault(101, "Bug #%s does not exist." % bug_id)

        # If we don't have comments for the bug already, create an empty
        # comment dict.
        if bug_id not in self.bug_comments:
            self.bug_comments[bug_id] = {}

        # Work out the number for the new comment on that bug.
        if len(self.bug_comments[bug_id]) == 0:
            comment_number = 1
        else:
            comment_numbers = sorted(self.bug_comments[bug_id].keys())
            latest_comment_number = comment_numbers[-1]
            comment_number = latest_comment_number + 1

        # Add the comment to the bug.
        comment_id = self.comment_id_index + 1
        comment_dict = {
            'author': 'launchpad',
            'bug_id': bug_id,
            'id': comment_id,
            'is_private': False,
            'time': self.new_comment_time,
            'text': comment,
            }
        self.bug_comments[bug_id][comment_number] = comment_dict

        self.comment_id_index = comment_id

        # We have to return a list here because xmlrpc.client will try to
        # expand sequences of length 1. Trying to do that on a dict will
        # cause it to explode.
        return [{'id': comment_id}]

    def update_see_also(self, arguments):
        """Update the see_also references for a bug."""
        assert 'ids' in arguments, (
            "You must specify a set of IDs with which to work.")
        assert ('add' in arguments or 'remove' in arguments), (
            "You must specify a list of links to add or remove.")

        changes = {}

        for bug_id in arguments['ids']:
            bug_id = int(bug_id)

            # If the bug ID doesn't exist, raise a Fault.
            if bug_id not in self.bugs:
                raise xmlrpc.client.Fault(
                    101, "Bug #%s does not exist." % bug_id)

            see_also_list = self.bugs[bug_id].get('see_also', [])

            # Remove any items first. That way, if they're also in the
            # 'add' section they'll get re-added.
            for url in arguments.get('remove', []):
                if url not in see_also_list:
                    continue

                if changes.get(bug_id) is None:
                    changes[bug_id] = {}

                if changes[bug_id].get('see_also') is None:
                    changes[bug_id]['see_also'] = {}

                if changes[bug_id]['see_also'].get('removed') is None:
                    changes[bug_id]['see_also']['removed'] = []

                see_also_list.remove(url)
                changes[bug_id]['see_also']['removed'].append(url)

            # Add any items to the list.
            for url in arguments.get('add', []):
                if url in see_also_list:
                    # Ignore existing urls.
                    continue

                if ('launchpad' not in url and
                    'show_bug.cgi' not in url):
                    raise xmlrpc.client.Fault(
                        112, "Bug URL %s is invalid." % url)

                if changes.get(bug_id) is None:
                    changes[bug_id] = {}

                if changes[bug_id].get('see_also') is None:
                    changes[bug_id]['see_also'] = {}

                if changes[bug_id]['see_also'].get('added') is None:
                    changes[bug_id]['see_also']['added'] = []

                see_also_list.append(url)
                changes[bug_id]['see_also']['added'].append(url)

            # Replace the bug's existing see_also list.
            self.bugs[bug_id]['see_also'] = see_also_list

        # We have to return a list here because xmlrpc.client will try to
        # expand sequences of length 1. Trying to do that on a dict will
        # cause it to explode.
        return [{'changes': changes}]


class NoAliasTestBugzillaAPIXMLRPCTransport(TestBugzillaAPIXMLRPCTransport):
    """A TestBugzillaAPIXMLRPCTransport that has no bug aliases."""

    bugs = {
        1: {'assigned_to': 'test@canonical.com',
            'component': 'GPPSystems',
            'creation_time': datetime(2008, 6, 10, 16, 19, 53),
            'id': 1,
            'internals': {},
            'is_open': True,
            'last_change_time': datetime(2008, 6, 10, 16, 19, 53),
            'priority': 'P1',
            'product': 'Marvin',
            'resolution': 'FIXED',
            'see_also': [],
            'severity': 'normal',
            'status': 'RESOLVED',
            'summary': "That bloody robot still exists.",
            },
        }


class TestMantis(BugTrackerResponsesMixin, Mantis):
    """Mantis ExternalBugTracker for use in tests."""

    @staticmethod
    def _getCallback(request):
        url = urlsplit(request.url)
        if url.path == '/csv_export.php':
            body = read_test_file('mantis_example_bug_export.csv')
        elif url.path == '/view.php':
            bug_id = parse_qs(url.query)['id'][0]
            body = read_test_file('mantis--demo--bug-%s.html' % bug_id)
        else:
            body = ''
        return 200, {}, body

    def addResponses(self, requests_mock, get=True, post=True):
        if get:
            requests_mock.add_callback(
                'GET', re.compile(re.escape(self.baseurl)), self._getCallback)
        if post:
            requests_mock.add('POST', re.compile(re.escape(self.baseurl)))


class TestTrac(BugTrackerResponsesMixin, Trac):
    """Trac ExternalBugTracker for testing purposes."""

    # We remove the batch_size limit for the purposes of the tests so
    # that we can test batching and not batching correctly.
    batch_size = None
    batch_query_threshold = 10
    csv_export_file = None

    def getExternalBugTrackerToUse(self):
        return self

    def _getCallback(self, request, supports_single_exports):
        url = urlsplit(request.url)
        if parse_qs(url.query).get('format') == ['csv']:
            mimetype = 'text/csv'
            if url.path.startswith('/ticket/'):
                if not supports_single_exports:
                    return 404, {}, ''
                body = read_test_file('trac_example_single_ticket_export.csv')
            else:
                body = read_test_file('trac_example_ticket_export.csv')
        else:
            mimetype = 'text/html'
            body = ''
        return 200, {'Content-Type': mimetype}, body

    def addResponses(self, requests_mock, supports_single_exports=True,
                     broken=False):
        url_pattern = re.compile(re.escape(self.baseurl))
        if broken:
            requests_mock.add(
                'GET', url_pattern,
                body=read_test_file('trac_example_broken_ticket_export.csv'))
        else:
            requests_mock.add_callback(
                'GET', url_pattern,
                lambda request: self._getCallback(
                    request, supports_single_exports))


class MockTracRemoteBug:
    """A mockup of a remote Trac bug."""

    def __init__(self, id, last_modified=None, status=None, resolution=None,
        comments=None):
        self.id = id
        self.last_modified = last_modified
        self.status = status
        self.resolution = resolution

        if comments is not None:
            self.comments = comments
        else:
            self.comments = []

    def asDict(self):
        """Return the bug's metadata, but not its comments, as a dict."""
        return {
            'id': self.id,
            'status': self.status,
            'resolution': self.resolution,
            }


class TestInternalXMLRPCTransport:
    """Test XML-RPC Transport for the internal XML-RPC server.

    This transport executes all methods as the 'launchpad' db user, and
    then switches back to the 'checkwatches' user.
    """

    def __init__(self, quiet=False):
        self.quiet = quiet

    def request(self, host, handler, request, verbose=None):
        args, method_name = xmlrpc.client.loads(request)
        method = getattr(self, method_name)
        with lp_dbuser():
            return method(*args)

    def newBugTrackerToken(self):
        token_api = ExternalBugTrackerTokenAPI(None, None)

        if not self.quiet:
            print("Using XML-RPC to generate token.")

        return token_api.newBugTrackerToken()


def strip_trac_comment(comment):
    """Tidy up a comment dict and return it as the Trac LP Plugin would."""
    # bug_info() doesn't return comment users, so we delete them.
    if 'user' in comment:
        del comment['user']

    return comment


class TestTracXMLRPCTransport(RequestsTransport):
    """An XML-RPC transport to be used when testing Trac."""

    remote_bugs = {}
    launchpad_bugs = {}
    seconds_since_epoch = None
    local_timezone = 'UTC'
    utc_offset = 0
    expired_cookie = None

    def expireCookie(self, cookie):
        """Mark the cookie as expired."""
        self.expired_cookie = cookie

    @property
    def auth_cookie(self):
        for cookie in self.cookie_jar:
            if (cookie.domain == 'example.com' and cookie.path == '' and
                    cookie.name == 'trac_auth'):
                return cookie
        else:
            return None

    @property
    def has_valid_auth_cookie(self):
        return (self.auth_cookie is not None and
                self.auth_cookie is not self.expired_cookie)

    def request(self, host, handler, request, verbose=None):
        """Call the corresponding XML-RPC method.

        The method name and arguments are extracted from `request`. The
        method on this class with the same name as the XML-RPC method is
        called, with the extracted arguments passed on to it.
        """
        assert handler.endswith('/xmlrpc'), (
            'The Trac endpoint must end with /xmlrpc')
        args, method_name = xmlrpc.client.loads(request)
        prefix = 'launchpad.'
        assert method_name.startswith(prefix), (
            'All methods should be in the launchpad namespace')
        if (self.auth_cookie is None or
            self.auth_cookie == self.expired_cookie):
            # All the Trac XML-RPC methods need authentication.
            raise xmlrpc.client.ProtocolError(
                method_name, errcode=403, errmsg="Forbidden",
                headers=None)

        method_name = method_name[len(prefix):]
        method = getattr(self, method_name)
        return method(*args)

    def bugtracker_version(self):
        """Return the bug tracker version information."""
        return ['0.11.0', '1.0', False]

    def time_snapshot(self):
        """Return the current time."""
        if self.seconds_since_epoch is None:
            local_time = int(time.time())
        else:
            local_time = self.seconds_since_epoch
        utc_time = local_time - self.utc_offset
        return [self.local_timezone, local_time, utc_time]

    @property
    def utc_time(self):
        """Return the current UTC time for this bug tracker."""
        # This is here for the sake of not having to use
        # time_snapshot()[2] all the time, which is a bit opaque.
        return self.time_snapshot()[2]

    def bug_info(self, level, criteria=None):
        """Return info about a bug or set of bugs.

        :param level: The level of detail to return about the bugs
            requested. This can be one of:
            0: Return IDs only.
            1: Return Metadata only.
            2: Return Metadata + comment IDs.
            3: Return all data about each bug.

        :param criteria: The selection criteria by which bugs will be
            returned. Possible keys include:
            modified_since: An integer timestamp. If specified, only
                bugs modified since this timestamp will
                be returned.
            bugs: A list of bug IDs. If specified, only bugs whose IDs are in
                this list will be returned.

        Return a list of [ts, bugs] where ts is a utc timestamp as
        returned by `time_snapshot()` and bugs is a list of bug dicts.
        """
        # XXX 2008-04-12 gmb:
        #     This is only a partial implementation of this; it will
        #     grow over time as implement different methods that call
        #     this method. See bugs 203564, 158703 and 158705.

        # We sort the list of bugs for the sake of testing.
        bug_ids = sorted(bug_id for bug_id in self.remote_bugs.keys())
        bugs_to_return = []
        missing_bugs = []

        for bug_id in bug_ids:
            bugs_to_return.append(self.remote_bugs[bug_id])

        if criteria is None:
            criteria = {}

        # If we have a modified_since timestamp, we return bugs modified
        # since that time.
        if 'modified_since' in criteria:
            # modified_since is an integer timestamp, so we convert it
            # to a datetime.
            modified_since = datetime.fromtimestamp(
                criteria['modified_since'])

            bugs_to_return = [
                bug for bug in bugs_to_return
                if bug.last_modified > modified_since]

        # If we have a list of bug IDs specified, we only return
        # those members of bugs_to_return that are in that
        # list.
        if 'bugs' in criteria:
            bugs_to_return = [
                bug for bug in bugs_to_return
                if bug.id in criteria['bugs']]

            # We make a separate list of bugs that don't exist so that
            # we can return them with a status of 'missing' later.
            missing_bugs = [
                bug_id for bug_id in criteria['bugs']
                if bug_id not in self.remote_bugs]

        # We only return what's required based on the level parameter.
        # For level 0, only IDs are returned.
        if level == LP_PLUGIN_BUG_IDS_ONLY:
            bugs_to_return = [{'id': bug.id} for bug in bugs_to_return]
        # For level 1, we return the bug's metadata, too.
        elif level == LP_PLUGIN_METADATA_ONLY:
            bugs_to_return = [bug.asDict() for bug in bugs_to_return]
        # At level 2, we also return comment IDs for each bug.
        elif level == LP_PLUGIN_METADATA_AND_COMMENTS:
            bugs_to_return = [
                dict(bug.asDict(), comments=[
                    comment['id'] for comment in bug.comments])
                for bug in bugs_to_return]
        # At level 3, we return the full comment dicts along with the
        # bug metadata. Tne comment dicts do not include the user field,
        # however.
        elif level == LP_PLUGIN_FULL:
            bugs_to_return = [
                dict(bug.asDict(),
                     comments=[strip_trac_comment(dict(comment))
                               for comment in bug.comments])
                for bug in bugs_to_return]

        # Tack the missing bugs onto the end of our list of bugs. These
        # will always be returned in the same way, no matter what the
        # value of the level argument.
        missing_bugs = [
            {'id': bug_id, 'status': 'missing'} for bug_id in missing_bugs]

        return [self.utc_time, bugs_to_return + missing_bugs]

    def get_comments(self, comments):
        """Return a list of comment dicts.

        :param comments: The IDs of the comments to return. Comments
            that don't exist will be returned with a type value of
            'missing'.
        """
        # It's a bit tedious having to loop through all the bugs and
        # their comments like this, but it's easier than creating a
        # horribly complex implementation for the sake of testing.
        comments_to_return = []

        for bug in self.remote_bugs.values():
            for comment in bug.comments:
                if comment['id'] in comments:
                    comments_to_return.append(comment)
        comments_to_return.sort(key=itemgetter('id'))

        # For each of the missing ones, return a dict with a type of
        # 'missing'.
        comment_ids_to_return = sorted(
            comment['id'] for comment in comments_to_return)
        missing_comments = [
            {'id': comment_id, 'type': 'missing'}
            for comment_id in comments
            if comment_id not in comment_ids_to_return]

        return [self.utc_time, comments_to_return + missing_comments]

    def add_comment(self, bugid, comment):
        """Add a comment to a bug.

        :param bugid: The integer ID of the bug to which the comment
            should be added.
        :param comment: The comment to be added as a string.
        """
        # Calculate the comment ID from the bug's ID and the number of
        # comments against that bug.
        comments = self.remote_bugs[str(bugid)].comments
        comment_id = "%s-%s" % (bugid, len(comments) + 1)

        comment_dict = {
            'comment': comment,
            'id': comment_id,
            'time': self.utc_time,
            'type': 'comment',
            'user': 'launchpad',
            }

        comments.append(comment_dict)

        return [self.utc_time, comment_id]

    def get_launchpad_bug(self, bugid):
        """Get the Launchpad bug ID for a given remote bug.

        The remote bug to Launchpad bug mappings are stored in the
        launchpad_bugs dict.

        If `bugid` references a remote bug that doesn't exist, raise a
        Fault.

        If a remote bug doesn't have a Launchpad bug mapped to it,
        return 0. Otherwise return the mapped Launchpad bug ID.
        """
        if bugid not in self.remote_bugs:
            raise xmlrpc.client.Fault(
                FAULT_TICKET_NOT_FOUND, 'Ticket does not exist')

        return [self.utc_time, self.launchpad_bugs.get(bugid, 0)]

    def set_launchpad_bug(self, bugid, launchpad_bug):
        """Set the Launchpad bug ID for a remote bug.

        If `bugid` references a remote bug that doesn't exist, raise a
        Fault.

        Return the current UTC timestamp.
        """
        if bugid not in self.remote_bugs:
            raise xmlrpc.client.Fault(
                FAULT_TICKET_NOT_FOUND, 'Ticket does not exist')

        self.launchpad_bugs[bugid] = launchpad_bug

        # Return a list, since xmlrpc.client insists on trying to expand
        # results.
        return [self.utc_time]


class TestRoundup(BugTrackerResponsesMixin, Roundup):
    """Roundup ExternalBugTracker for testing purposes."""

    # We remove the batch_size limit for the purposes of the tests so
    # that we can test batching and not batching correctly.
    batch_size = None

    @staticmethod
    def _getCallback(request):
        url = urlsplit(request.url)
        if url.netloc == 'bugs.python.org':
            body = read_test_file('python_example_ticket_export.csv')
        else:
            body = read_test_file('roundup_example_ticket_export.csv')
        return 200, {}, body

    def addResponses(self, requests_mock):
        """Add test responses."""
        requests_mock.add_callback(
            'GET', re.compile(re.escape(self.baseurl)), self._getCallback)


class TestRequestTracker(BugTrackerResponsesMixin, RequestTracker):
    """A Test-oriented `RequestTracker` implementation."""

    simulate_bad_response = False

    def _getCallback(self, request):
        url = urlsplit(request.url)
        headers = {}
        if url.path == '/':
            params = parse_qs(url.query)
            headers['Set-Cookie'] = 'rt_credentials=%s:%s' % (
                params['user'][0], params['pass'][0])
            body = ''
        else:
            if url.path == '/REST/1.0/search/ticket/':
                body = read_test_file('rt-sample-bug-batch.txt')
            else:
                # Extract the ticket ID from the URL and use that to
                # find the test file we want.
                bug_id = re.match(
                    r'/REST/1\.0/ticket/([0-9]+)/show', url.path).group(1)
                body = read_test_file('rt-sample-bug-%s.txt' % bug_id)
        return 200, headers, body

    def addResponses(self, requests_mock, bad=False):
        """Add test responses."""
        if bad:
            requests_mock.add(
                'GET', re.compile(re.escape(self.baseurl)),
                body=read_test_file('rt-sample-bug-bad.txt'))
        else:
            requests_mock.add_callback(
                'GET', re.compile(re.escape(self.baseurl)), self._getCallback)


class TestSourceForge(BugTrackerResponsesMixin, SourceForge):
    """Test-oriented SourceForge ExternalBugTracker."""

    @staticmethod
    def _getCallback(request):
        url = urlsplit(request.url)
        bug_id = parse_qs(url.query)['aid'][0]
        body = read_test_file('sourceforge-sample-bug-%s.html' % bug_id)
        return 200, {'Content-Type': 'text/html'}, body

    def addResponses(self, requests_mock):
        """Add test responses."""
        requests_mock.add_callback(
            'GET',
            re.compile(
                re.escape(urljoin(self.baseurl, 'support/tracker.php'))),
            self._getCallback)


class TestDebianBug(debbugs.Bug):
    """A debbugs bug that doesn't require the debbugs db."""

    def __init__(self, reporter_email='foo@example.com', package='evolution',
                 summary='Test Summary', description='Test description.',
                 status='open', severity=None, tags=None, id=None):
        if tags is None:
            tags = []
        self.originator = reporter_email
        self.package = package
        self.subject = summary
        self.description = description
        self.status = status
        self.severity = severity
        self.tags = tags
        self.id = id
        self._emails = []

    def __getattr__(self, name):
        # We redefine this method here to as to avoid some of the
        # behaviour of debbugs.Bug from raising spurious errors during
        # testing.
        return getattr(self, name, None)


class TestDebBugsDB:
    """A debbugs db object that doesn't require access to the debbugs db."""

    def __init__(self):
        self._data_path = os.path.join(os.path.dirname(__file__),
            'testfiles')
        self._data_file = 'debbugs-1-comment.txt'
        self.fail_on_load_log = False

    @property
    def data_file(self):
        return os.path.join(self._data_path, self._data_file)

    def load_log(self, bug):
        """Load the comments for a particular debian bug."""
        if self.fail_on_load_log:
            raise debbugs.LogParseFailed(
                'debbugs-log.pl exited with code 512')

        with open(self.data_file, 'rb') as f:
            comment_data = f.read()
        bug._emails = []
        bug.comments = [comment.strip() for comment in
            comment_data.split(b'--\n')]


class TestDebBugs(DebBugs):
    """A Test-oriented Debbugs ExternalBugTracker.

    It allows you to pass in bugs to be used, instead of relying on an
    existing debbugs db.
    """
    sync_comments = False

    def __init__(self, baseurl, bugs):
        super().__init__(baseurl)
        self.bugs = bugs
        self.debbugs_db = TestDebBugsDB()

    def _findBug(self, bug_id):
        if bug_id not in self.bugs:
            raise BugNotFound(bug_id)

        bug = self.bugs[bug_id]
        self.debbugs_db.load_log(bug)
        return bug


def ensure_response_parser_is_expat(transport):
    """Ensure the transport always selects the Expat-based response parser.

    The response parser is chosen by xmlrpc.client at runtime from a number
    of choices, but the main Launchpad production environment selects Expat
    at present.

    Developer's machines could have other packages, `python-reportlab-accel`
    (which provides the `sgmlop` module) for example, that cause different
    response parsers to be chosen.
    """
    def getparser():
        target = xmlrpc.client.Unmarshaller(
            use_datetime=transport._use_datetime)
        parser = xmlrpc.client.ExpatParser(target)
        return parser, target
    transport.getparser = getparser
