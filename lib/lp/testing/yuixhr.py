# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Fixture code for YUITest + XHR integration testing."""

__metaclass__ = type
__all__ = [
    'login_as_person',
    'make_suite',
    'setup',
    'YUITestFixtureControllerView',
]

from fnmatch import fnmatchcase
import os
import sys
from textwrap import dedent
import traceback
import unittest

from lazr.restful import ResourceJSONEncoder
from lazr.restful.utils import get_current_browser_request
import scandir
import simplejson
from zope.component import getUtility
from zope.exceptions.exceptionformatter import format_exception
from zope.interface import implementer
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.http import IResult
from zope.security.checker import (
    NamesChecker,
    ProxyFactory,
    )
from zope.security.proxy import removeSecurityProxy
from zope.session.interfaces import IClientIdManager

from lp.app import versioninfo
from lp.services.config import config
from lp.services.webapp.interfaces import (
    IOpenLaunchBag,
    IPlacelessAuthUtility,
    )
from lp.services.webapp.login import logInPrincipal
from lp.services.webapp.publisher import LaunchpadView
from lp.testing import AbstractYUITestCase
from lp.testing.layers import (
    DatabaseLayer,
    LaunchpadLayer,
    LayerProcessController,
    LibrarianLayer,
    YUIAppServerLayer,
    )


EXPLOSIVE_ERRORS = (SystemExit, MemoryError, KeyboardInterrupt)


class setup:
    """Decorator to mark a function as a fixture available from JavaScript.

    This makes the function available to call from JS integration tests over
    XHR.  The fixture setup can have one or more cleanups tied to it with
    ``add_cleanup`` decorator/callable and can be composed with another
    function with the ``extend`` decorator/callable.
    """
    def __init__(self, function, extends=None):
        self._cleanups = []
        self._function = function
        self._extends = extends
        # We can't use locals because we want to affect the function's module,
        # not this one.
        module = sys.modules[function.__module__]
        fixtures = getattr(module, '_fixtures_', None)
        if fixtures is None:
            fixtures = module._fixtures_ = {}
        fixtures[function.__name__] = self

    def __call__(self, request, data):
        """Call the originally decorated setup function."""
        if self._extends is not None:
            self._extends(request, data)
        self._function(request, data)

    def add_cleanup(self, function):
        """Add a cleanup function to be executed on teardown, FILO."""
        self._cleanups.append(function)
        return self

    def teardown(self, request, data):
        """Run all registered cleanups.  If no cleanups, a no-op."""
        for f in reversed(self._cleanups):
            f(request, data)
        if self._extends is not None:
            self._extends.teardown(request, data)

    def extend(self, function):
        return setup(function, self)


def login_as_person(person):
    """This is a helper function designed to be used within a fixture.

    Provide a person, such as one generated by LaunchpadObjectFactory, and
    the browser will become logged in as this person.

    Explicit tear-down is unnecessary because the database is reset at the end
    of every test, and the cookie is discarded.
    """
    if person.is_team:
        raise AssertionError("Please do not try to login as a team")
    email = removeSecurityProxy(person.preferredemail).email
    request = get_current_browser_request()
    assert request is not None, "We do not have a browser request."
    authutil = getUtility(IPlacelessAuthUtility)
    principal = authutil.getPrincipalByLogin(email)
    launchbag = getUtility(IOpenLaunchBag)
    launchbag.setLogin(email)
    logInPrincipal(request, principal, email)


@implementer(IResult)
class CloseDbResult:

    # This is machinery, not content.  We specify our security checker here
    # directly for clarity.
    __Security_checker__ = NamesChecker(['next', '__iter__'])

    def __iter__(self):
        try:
            # Reset the session.
            LaunchpadLayer.resetSessionDb()
            # Yield control to asyncore for a second, just to be a
            # little bit nice.  We could be even nicer by moving this
            # whole teardown/setup dance to a thread and waiting for
            # it to be done, but there's not a (known) compelling need
            # for that right now, and doing it this way is slightly
            # simpler.
            yield ''
            DatabaseLayer.testSetUp()
            yield ''
            # Reset the librarian.
            LibrarianLayer.testTearDown()
            yield ''
            # Reset the database.
            DatabaseLayer.testTearDown()
            yield ''
            LibrarianLayer.testSetUp()
        except (SystemExit, KeyboardInterrupt):
            raise
        except:
            print "Hm, serious error when trying to clean up the test."
            traceback.print_exc()
        # We're done, so we can yield the body.
        yield '\n'


class YUITestFixtureControllerView(LaunchpadView):
    """Dynamically loads YUI test along their fixtures run over an app server.
    """

    COMBOFILE = 'COMBOFILE'
    JAVASCRIPT = 'JAVASCRIPT'
    HTML = 'HTML'
    SETUP = 'SETUP'
    TEARDOWN = 'TEARDOWN'
    INDEX = 'INDEX'

    yui_block_combo = dedent("""\
       <script type="text/javascript"
           src="/+yuitest/build/js/yui/yui/yui-min.js"></script>
       <script type="text/javascript"
           src="/+yuitest/build/js/yui/loader/loader-min.js"></script>
       <script type="text/javascript"
           src="/+yuitest/build/js/lp/meta.js"></script>
       <script type="text/javascript">
            YUI.GlobalConfig = {
                combine: false,
                base: '/+yuitest/build/js/yui/',
                debug: true,
                fetchCSS: false,
                groups: {
                    lp: {
                        combine: false,
                        base: '/+yuitest/build/js/lp/',
                        root: 'lp/',
                        debug: true,
                        filter: 'raw',
                        // comes from including lp/meta.js
                        modules: LP_MODULES,
                        fetchCSS: false
                    }
                }
            }
        </script>
        <script type="text/javascript"
            src="/+yuitest/build/js/lp/app/testing/testrunner.js"></script>
    """)

    page_template = dedent("""\
        <!DOCTYPE html>
        <html>
          <head>
            <title>Test</title>
            %(javascript_block)s
            <link rel="stylesheet"
              href="/+yuitest/build/js/yui/console/assets/console-core.css"/>
            <link rel="stylesheet"
              href="/+yuitest/build/js/yui/console/assets/skins/sam/console.css"/>
            <link rel="stylesheet"
              href="/+yuitest/build/js/yui/test/assets/skins/sam/test.css"/>
            <link rel="stylesheet" href="/+icing/rev%(revision)s/combo.css"/>
            <script type="text/javascript" src="%(test_module)s"></script>
          </head>
        <body class="yui3-skin-sam">
          <div id="log"></div>
          <ul id="suites"><li>%(test_namespace)s</li></ul>
          <p>Want to re-run your test?</p>
          <ul>
            <li><a href="?">Reload test JS</a></li>
            <li><a href="?reload=1">Reload test JS and the associated
                                    Python fixtures</a></li>
          </ul>
          <p>Don't forget to run <code>make jsbuild</code> if you change a
             comboloaded file.</p>
          <p>If you change Python code other than the fixtures, you must
             restart the server.  Sorry.</p>
        </body>
        </html>
        """)

    index_template = dedent("""\
        <!DOCTYPE html>
        <html>
          <head>
          <title>YUI XHR Tests</title>
          <link rel="stylesheet" href="/+icing/rev%(revision)s/combo.css"/>
          <style>
          ul {
            text-align: left;
          }
          body, ul, h1 {
            margin: 0.3em;
            padding: 0.3em;
          }
        </style>
        </head>
        <body class="yui3-skin-sam">
          <h1>YUI XHR Tests</h1>
          <ul>%(tests)s</ul>
        </body>
        </html>
        """)

    def __init__(self, context, request):
        super(YUITestFixtureControllerView, self).__init__(context, request)
        self.names = []
        self.action = None
        self.fixtures = []

    @property
    def traversed_path(self):
        return os.path.join(*self.names)

    def initialize(self):
        if not self.names:
            self.action = self.INDEX
            return
        path, ext = os.path.splitext(self.traversed_path)
        # We need to route requests with build/js in them to the combo loader
        # js files so we can load those to bootstap.
        if path.startswith('build/js'):
            self.action = self.COMBOFILE
        else:
            full_path = os.path.join(config.root, 'lib', path)

            if not os.path.exists(full_path + '.py'):
                raise NotFound(self, full_path + '.py', self.request)
            if not os.path.exists(full_path + '.js'):
                raise NotFound(self, full_path + '.js', self.request)

            if ext == '.js':
                self.action = self.JAVASCRIPT
            else:
                if self.request.method == 'GET':
                    self.action = self.HTML
                else:
                    self.fixtures = self.request.form['fixtures'].split(',')
                    if self.request.form['action'] == 'setup':
                        self.action = self.SETUP
                    else:
                        self.action = self.TEARDOWN

    # The following two zope methods publishTraverse and browserDefault
    # allow this view class to take control of traversal from this point
    # onwards.  Traversed names just end up in self.names.
    def publishTraverse(self, request, name):
        """Traverse to the given name."""
        # The two following constraints are enforced by the publisher.
        assert os.path.sep not in name, (
            'traversed name contains os.path.sep: %s' % name)
        assert name != '..', 'traversing to ..'
        if name:
            self.names.append(name)
        return self

    def browserDefault(self, request):
        return self, ()

    @property
    def module_name(self):
        return '.'.join(self.names)

    def get_fixtures(self):
        module = __import__(
            self.module_name, globals(), locals(), ['_fixtures_'], 0)
        return module._fixtures_

    def renderINDEX(self):
        root = os.path.join(config.root, 'lib')
        test_lines = []
        for path in find_tests(root):
            test_path = '/+yuitest/' + '/'.join(path)
            module_name = '.'.join(path)
            try:
                module = __import__(
                    module_name, globals(), locals(), ['test_suite'], 0)
            except ImportError:
                warning = 'cannot import Python fixture file'
            else:
                try:
                    suite_factory = module.test_suite
                except AttributeError:
                    warning = 'cannot find test_suite'
                else:
                    try:
                        suite = suite_factory()
                    except EXPLOSIVE_ERRORS:
                        raise
                    except:
                        warning = 'test_suite raises errors'
                    else:
                        case = None
                        for case in suite:
                            if isinstance(case, YUIAppServerTestCase):
                                root_url = config.appserver_root_url(
                                    case.facet)
                                if root_url != 'None':
                                    test_path = root_url + test_path
                                warning = ''
                                break
                        else:
                            warning = (
                                'test suite is not instance of '
                                'YUIAppServerTestCase')
            link = '<a href="%s">%s</a>' % (test_path, test_path)
            if warning:
                warning = ' <span class="warning">%s</span>' % warning
            test_lines.append('<li>%s%s</li>' % (link, warning))
        return self.index_template % {
            'revision': versioninfo.revision,
            'tests': '\n'.join(test_lines)}

    def renderCOMBOFILE(self):
        """We need to serve the combo files out of the build directory."""
        self.request.response.setHeader('Cache-Control', 'no-cache')
        if self.traversed_path.endswith('js'):
            self.request.response.setHeader('Content-Type', 'text/javascript')
        elif self.traversed_path.endswith('css'):
            self.request.response.setHeader('Content-Type', 'text/css')
        return open(
            os.path.join(config.root, self.traversed_path))

    def renderJAVASCRIPT(self):
        self.request.response.setHeader('Content-Type', 'text/javascript')
        self.request.response.setHeader('Cache-Control', 'no-cache')
        return open(
            os.path.join(config.root, 'lib', self.traversed_path))

    def renderHTML(self):
        self.request.response.setHeader('Content-Type', 'text/html')
        self.request.response.setHeader('Cache-Control', 'no-cache')
        if ('INTERACTIVE_TESTS' in os.environ and
            'reload' in self.request.form):
            # We should try to reload the module.
            module = sys.modules.get(self.module_name)
            if module is not None:
                del module._fixtures_
                reload(module)
        return self.page_template % dict(
            test_module='/+yuitest/%s.js' % self.traversed_path,
            test_namespace=self.traversed_path.replace('/', '.'),
            revision=versioninfo.revision,
            javascript_block=self.renderYUI())

    def renderSETUP(self):
        data = {}
        fixtures = self.get_fixtures()
        try:
            for fixture_name in self.fixtures:
                __traceback_info__ = (fixture_name, data)
                fixtures[fixture_name](self.request, data)
        except EXPLOSIVE_ERRORS:
            raise
        except:
            self.request.response.setStatus(500)
            result = ''.join(format_exception(*sys.exc_info()))
        else:
            self.request.response.setHeader(
                'Content-Type', 'application/json')
            # We use the ProxyFactory so that the restful
            # redaction code is always used.
            result = simplejson.dumps(
                ProxyFactory(data), cls=ResourceJSONEncoder)
        return result

    def renderTEARDOWN(self):
        data = simplejson.loads(self.request.form['data'])
        fixtures = self.get_fixtures()
        try:
            for fixture_name in reversed(self.fixtures):
                __traceback_info__ = (fixture_name, data)
                fixtures[fixture_name].teardown(self.request, data)
        except EXPLOSIVE_ERRORS:
            raise
        except:
            self.request.response.setStatus(500)
            result = ''.join(format_exception(*sys.exc_info()))
        else:
            # Remove the session cookie, in case we have one.
            self.request.response.expireCookie(
                getUtility(IClientIdManager).namespace)
            # Blow up the database once we are out of this transaction
            # by passing a result that will do so when it is iterated
            # through in asyncore.
            self.request.response.setHeader('Content-Length', 1)
            result = CloseDbResult()
        return result

    def renderYUI(self):
        """Render out which YUI block we need based on the combo loader

        If the combo loader is enabled, we need that setup and config and not
        to load launchpad.js, else we need launchpad.js for things to run.

        """
        return self.yui_block_combo % dict(
            revision=versioninfo.revision,
            combo_url=self.combo_url)

    def render(self):
        return getattr(self, 'render' + self.action)()


def find_tests(root):
    for dirpath, dirnames, filenames in scandir.walk(root):
        dirpath = os.path.relpath(dirpath, root)
        for filename in filenames:
            if fnmatchcase(filename, 'test_*.js'):
                name, ext = os.path.splitext(filename)
                if name + '.py' in filenames:
                    names = dirpath.split(os.path.sep)
                    names.append(name)
                    yield names


# This class cannot be imported directly into a test suite because
# then the test loader will sniff and (try to) run it.  Use make_suite
# instead (or import this module rather than this class).
class YUIAppServerTestCase(AbstractYUITestCase):
    "Instantiate this test case with the Python fixture module name."

    layer = YUIAppServerLayer
    _testMethodName = 'runTest'
    # 5 minutes for the suite.  Hopefully we never get close to this.
    suite_timeout = 300000
    # 12 seconds for each test.  Hopefully they are three or less for
    # yuixhr tests, and less than one for pure JS tests, but
    # occasionally buildbot runs over six seconds even for tests that
    # are well-behaved locally and on ec2, so we up the limit to 12..
    incremental_timeout = 12000
    # 45 seconds for the first test, to include warmup time.  These times
    # are wildly large, and they are only necessary on buildbot.  ec2 and
    # local instances are much, much faster.  We have not yet investigated
    # why buildbot is so slow for these.
    initial_timeout = 45000

    def __init__(self, module_name, facet='mainsite'):
        self.module_name = module_name
        self.facet = facet
        # This needs to be done early so the "id" is set correctly.
        self.test_path = self.module_name.replace('.', '/')
        super(YUIAppServerTestCase, self).__init__()

    def setUp(self):
        config = LayerProcessController.appserver_config
        root_url = config.appserver_root_url(self.facet)
        self.html_uri = '%s/+yuitest/%s' % (root_url, self.test_path)
        super(YUIAppServerTestCase, self).setUp()

    runTest = AbstractYUITestCase.checkResults


def make_suite(module_name, facet='mainsite'):
    return unittest.TestSuite([YUIAppServerTestCase(module_name, facet)])
