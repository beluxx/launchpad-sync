# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Infrastructure for setting up doctests."""

__all__ = [
    'default_optionflags',
    'LayeredDocFileSuite',
    'PrettyPrinter',
    'setUp',
    'setGlobs',
    'stop',
    'strip_prefix',
    'tearDown',
    ]

import doctest
from functools import partial
import logging
import os
import pdb
import pprint
import sys

import six
import transaction
from zope.component import getUtility
from zope.testing.loggingsupport import Handler

from lp.services.config import config
from lp.services.database.sqlbase import flush_database_updates
from lp.services.helpers import backslashreplace
from lp.services.webapp.interfaces import ILaunchBag
from lp.testing import (
    ANONYMOUS,
    launchpadlib_credentials_for,
    launchpadlib_for,
    login,
    login_person,
    logout,
    oauth_access_token_for,
    reset_logging,
    verifyObject,
    )
from lp.testing.factory import LaunchpadObjectFactory
from lp.testing.fixture import CaptureOops
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


default_optionflags = (doctest.REPORT_NDIFF |
                       doctest.NORMALIZE_WHITESPACE |
                       doctest.ELLIPSIS)


def strip_prefix(path):
    """Return path with the Launchpad tree root removed."""
    prefix = config.root
    if not prefix.endswith(os.path.sep):
        prefix += os.path.sep

    if path.startswith(prefix):
        return path[len(prefix):]
    else:
        return path


class FilePrefixStrippingDocTestParser(doctest.DocTestParser):
    """A DocTestParser that strips a prefix from doctests."""

    def get_doctest(self, string, globs, name, filename, lineno):
        filename = strip_prefix(filename)
        return doctest.DocTestParser.get_doctest(
            self, string, globs, name, filename, lineno)


default_parser = FilePrefixStrippingDocTestParser()


class StdoutHandler(Handler):
    """A logging handler that prints log messages to sys.stdout.

    This causes log messages to become part of the output captured by
    doctest, making the test cover the logging behaviour of the code
    being run.
    """
    def emit(self, record):
        Handler.emit(self, record)
        print('%s:%s:%s' % (
            record.levelname, record.name, self.format(record)))


def setUpStdoutLogging(test, prev_set_up=None,
                       stdout_logging_level=logging.INFO):
    if prev_set_up is not None:
        prev_set_up(test)
    log = StdoutHandler('')
    log.setLoggerLevel(stdout_logging_level)
    log.install()
    test.globs['log'] = log
    # Store as instance attribute so we can uninstall it.
    test._stdout_logger = log


def tearDownStdoutLogging(test, prev_tear_down=None):
    if prev_tear_down is not None:
        prev_tear_down(test)
    reset_logging()
    test._stdout_logger.uninstall()


def setUpOopsCapturing(test, prev_set_up=None):
    oops_capture = CaptureOops()
    oops_capture.setUp()
    test.globs['oops_capture'] = oops_capture
    # Store as instance attribute so we can clean it up.
    test._oops_capture = oops_capture
    if prev_set_up is not None:
        prev_set_up(test)


def tearDownOopsCapturing(test, prev_tear_down=None):
    if prev_tear_down is not None:
        prev_tear_down(test)
    test._oops_capture.cleanUp()


def LayeredDocFileSuite(paths, id_extensions=None, **kw):
    """Create a DocFileSuite, optionally applying a layer to it.

    In addition to the standard DocFileSuite arguments, the following
    optional keyword arguments are accepted:

    :param stdout_logging: If True, log messages are sent to the
      doctest's stdout (defaults to True).
    :param stdout_logging_level: The logging level for the above.
    :param layer: A Zope test runner layer to apply to the tests (by
      default no layer is applied).
    """
    if not isinstance(paths, (tuple, list)):
        paths = [paths]
    if id_extensions is None:
        id_extensions = []
    kw.setdefault('optionflags', default_optionflags)
    kw.setdefault('parser', default_parser)

    # Make sure that paths are resolved relative to our caller
    kw['package'] = doctest._normalize_module(kw.get('package'))

    # Set stdout_logging keyword argument to True to make
    # logging output be sent to stdout, forcing doctests to deal with it.
    stdout_logging = kw.pop('stdout_logging', True)
    stdout_logging_level = kw.pop('stdout_logging_level', logging.INFO)

    if stdout_logging:
        kw['setUp'] = partial(
            setUpStdoutLogging, prev_set_up=kw.get('setUp'),
            stdout_logging_level=stdout_logging_level)
        kw['tearDown'] = partial(
            tearDownStdoutLogging, prev_tear_down=kw.get('tearDown'))

    kw['setUp'] = partial(setUpOopsCapturing, prev_set_up=kw.get('setUp'))
    kw['tearDown'] = partial(
        tearDownOopsCapturing, prev_tear_down=kw.get('tearDown'))

    layer = kw.pop('layer', None)
    suite = doctest.DocFileSuite(*paths, **kw)
    if layer is not None:
        suite.layer = layer

    for i, test in enumerate(suite):
        # doctest._module_relative_path() does not normalize paths. To make
        # test selection simpler and reporting easier to read, normalize here.
        test._dt_test.filename = os.path.normpath(test._dt_test.filename)
        # doctest.DocFileTest insists on using the basename of the file as the
        # test ID. This causes conflicts when two doctests have the same
        # filename, so we patch the id() method on the test cases.
        try:
            ext = id_extensions[i]
            newid = os.path.join(
                os.path.dirname(test._dt_test.filename),
                ext)
            test.id = partial(lambda x: x, newid)
        except IndexError:
            test.id = partial(lambda test: test._dt_test.filename, test)

    return suite


def ordered_dict_as_string(dict):
    """Return the contents of a dict as an ordered string.

    The output will be ordered by key, so {'z': 1, 'a': 2, 'c': 3} will
    be printed as {'a': 2, 'c': 3, 'z': 1}.

    We do this because dict ordering is not guaranteed.
    """
    return '{%s}' % ', '.join(
        "%r: %r" % (key, value) for key, value in sorted(dict.items()))


def stop():
    # Temporarily restore the real stdout.
    old_stdout = sys.stdout
    sys.stdout = sys.__stdout__
    try:
        pdb.set_trace()
    finally:
        sys.stdout = old_stdout


class PrettyPrinter(pprint.PrettyPrinter):
    """A pretty-printer that formats text in the Python 3 style.

    This should only be used when the resulting ambiguities between str and
    unicode representation and between int and long representation on Python
    2 are not a problem.
    """

    def format(self, obj, contexts, maxlevels, level):
        if isinstance(obj, str):
            obj = obj.encode('unicode_escape').decode('ASCII')
            if "'" in obj and '"' not in obj:
                return '"%s"' % obj, True, False
            else:
                return "'%s'" % obj.replace("'", "\\'"), True, False
        else:
            return super().format(obj, contexts, maxlevels, level)

    # Disable wrapping of long strings on Python >= 3.5, which is unhelpful
    # in doctests.  There seems to be no reasonable public API for this.
    _dispatch = dict(pprint.PrettyPrinter._dispatch)
    del _dispatch[str.__repr__]
    del _dispatch[bytes.__repr__]
    del _dispatch[bytearray.__repr__]


def setGlobs(test):
    """Add the common globals for testing system documentation."""
    test.globs['ANONYMOUS'] = ANONYMOUS
    test.globs['login'] = login
    test.globs['login_person'] = login_person
    test.globs['logout'] = logout
    test.globs['ILaunchBag'] = ILaunchBag
    test.globs['getUtility'] = getUtility
    test.globs['transaction'] = transaction
    test.globs['flush_database_updates'] = flush_database_updates
    test.globs['create_view'] = create_view
    test.globs['create_initialized_view'] = create_initialized_view
    test.globs['factory'] = LaunchpadObjectFactory()
    test.globs['ordered_dict_as_string'] = ordered_dict_as_string
    test.globs['verifyObject'] = verifyObject
    test.globs['pretty'] = PrettyPrinter(width=1).pformat
    test.globs['stop'] = stop
    test.globs['launchpadlib_for'] = launchpadlib_for
    test.globs['launchpadlib_credentials_for'] = launchpadlib_credentials_for
    test.globs['oauth_access_token_for'] = oauth_access_token_for
    test.globs['six'] = six
    test.globs['backslashreplace'] = backslashreplace


def setUp(test):
    """Setup the common globals and login for testing system documentation."""
    setGlobs(test)
    # Set up an anonymous interaction.
    login(ANONYMOUS)


def tearDown(test):
    """Tear down the common system documentation test."""
    logout()
