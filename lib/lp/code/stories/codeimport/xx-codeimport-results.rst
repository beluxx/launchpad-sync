Code import results
===================

Information about the last ten import runs for a code import are shown
on the branch index page with the other code import details.

    >>> login('test@canonical.com')
    >>> from lp.code.tests.codeimporthelpers import (
    ...     make_all_result_types)
    >>> code_import_1 = factory.makeCodeImport()
    >>> code_import_2 = factory.makeCodeImport()

The make_all_result_types helper method adds a code import result of
each possible status value.  There are more status values than are
shown on the branch page, so we create two imports in order to test
how each result type is rendered.

    >>> odin = factory.makeCodeImportMachine(hostname='odin')
    >>> make_all_result_types(
    ...     code_import_1, factory, machine=odin, start=0, count=7)
    >>> branch_url_1 = canonical_url(code_import_1.branch)
    >>> make_all_result_types(
    ...     code_import_2, factory, machine=odin, start=7, count=7)
    >>> branch_url_2 = canonical_url(code_import_2.branch)
    >>> logout()

For each import result, the start date and finish date is shown along
with the duration.  A link to the log file is shown if there was a log
file stored with the result.

    >>> browser.open(branch_url_1)
    >>> import_results = find_tag_by_id(browser.contents, 'import-results')
    >>> print(extract_text(
    ...     import_results, formatter='html').replace('&mdash;', '--'))
    Import started on 2007-12-07 on odin and finished on 2007-12-07
      taking 7 hours -- see the log
    Import started on 2007-12-06 on odin and finished on 2007-12-06
      taking 6 hours -- see the log
    Import started on 2007-12-05 on odin and finished on 2007-12-05
      taking 5 hours -- see the log
    Import started on 2007-12-04 on odin and finished on 2007-12-04
      taking 4 hours -- see the log
    Import started on 2007-12-03 on odin and finished on 2007-12-03
      taking 3 hours -- see the log
    Import started on 2007-12-02 on odin and finished on 2007-12-02
      taking 2 hours -- see the log
    Import started on 2007-12-01 on odin and finished on 2007-12-01
      taking 1 hour -- see the log

Each of the lines is prefixed with a tick if the result status was
success, or a cross if the status was a failure.  The title of the image
is the text of the failure or success type.

The ordering here is dependent on the order the status values are declared
in the enumeration.

    >>> for img in import_results.find_all('img'):
    ...     print(img)
    <img src="/@@/no" title="Unsupported feature"/>
    <img src="/@@/no" title="Foreign branch invalid"/>
    <img src="/@@/no" title="Internal Failure"/>
    <img src="/@@/no" title="Failure"/>
    <img src="/@@/yes-gray" title="Partial Success"/>
    <img src="/@@/yes" title="Success with no changes"/>
    <img src="/@@/yes" title="Success"/>

    >>> browser.open(branch_url_2)
    >>> import_results = find_tag_by_id(browser.contents, 'import-results')
    >>> for img in import_results.find_all('img'):
    ...     print(img)
    <img src="/@@/no" title="Job killed"/>
    <img src="/@@/no" title="Job reclaimed"/>
    <img src="/@@/no" title="Broken remote branch"/>
    <img src="/@@/no" title="Forbidden URL"/>
