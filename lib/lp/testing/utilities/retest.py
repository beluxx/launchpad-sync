# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Given an error report, run all of the failed tests again.

For instance, it can be used in the following scenario:

  % bin/test -vvm lp.registry | tee test.out
  % # Oh nos!  Failures!
  % # Fix tests.
  % bin/retest test.out

Or, when run without arguments (or if any argument is "-"), a test
report (or a part of) can be piped in, for example by pasting it:

  % bin/retest
  Tests with failures:
     lib/lp/registry/browser/tests/sourcepackage-views.txt
     lib/lp/registry/tests/../stories/product/xx-product-package-pages.txt
  Total: ... tests, 2 failures, 0 errors in ...

"""

from collections import OrderedDict
import fileinput
from itertools import takewhile
import os
import re
import sys
import tempfile

from lp.services.config import config


# The test script for this branch.
TEST = os.path.join(config.root, "bin/test")

# Regular expression to match numbered stories.
STORY_RE = re.compile(r"(.*)/\d{2}-.*")

# Regular expression to remove terminal color escapes.
COLOR_RE = re.compile(r"\x1b[[][0-9;]+m")


def decolorize(text):
    """Remove all ANSI terminal color escapes from `text`."""
    return COLOR_RE.sub("", text)


def get_test_name(test):
    """Get the test name of a failed test.

    If the test is part of a numbered story,
    e.g. 'stories/gpg-coc/01-claimgpgp.txt', then return the directory name
    since all of the stories must be run together.
    """
    match = STORY_RE.match(test)
    if match:
        return match.group(1)
    else:
        return test


def gen_test_lines(lines):
    def p_start(line):
        return (
            line.startswith('Tests with failures:') or
            line.startswith('Tests with errors:'))

    def p_take(line):
        return not (
            line.isspace() or
            line.startswith('Total:'))

    lines = iter(lines)
    for line in lines:
        if p_start(line):
            for line in takewhile(p_take, lines):
                yield line


def gen_tests(test_lines):
    for test_line in test_lines:
        yield get_test_name(test_line.strip())


def extract_tests(lines):
    # Deduplicate test IDs.  We don't have a convenient ordered set type,
    # but an OrderedDict is good enough.
    tests = OrderedDict()
    for test in gen_tests(gen_test_lines(lines)):
        tests[test] = None
    return list(tests.keys())


def run_tests(tests):
    """Given a set of tests, run them as one group."""
    print("Running tests:")
    for test in tests:
        print("  %s" % test)
    args = ['-vvc'] if sys.stdout.isatty() else ['-vv']
    with tempfile.NamedTemporaryFile(mode='w+') as test_list:
        for test in tests:
            print(test, file=test_list)
        test_list.flush()
        args.extend(['--load-list', test_list.name])
        os.execl(TEST, TEST, *args)


def main():
    lines = map(decolorize, fileinput.input())
    tests = extract_tests(lines)
    if len(tests) >= 1:
        run_tests(tests)
    else:
        sys.stdout.write(
            "Error: no tests found\n"
            "Usage: %s [test_output_file|-] ...\n\n%s\n\n" % (
                sys.argv[0], __doc__.strip()))
        sys.exit(1)
