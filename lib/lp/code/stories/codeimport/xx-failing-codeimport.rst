Retrying a failed import
========================

Imports that have failed more than the configured
'consecutive_failure_limit' times in a row are no longer attempted.

    >>> login("admin@canonical.com")
    >>> from lp.code.tests.codeimporthelpers import make_finished_import
    >>> from lp.services.config import config
    >>> from lp.code.interfaces.codeimportresult import CodeImportResultStatus
    >>> product = factory.makeProduct(name="imported")
    >>> owner = factory.makePerson(name="import-owner")
    >>> code_import = factory.makeProductCodeImport(
    ...     product=product, branch_name="trunk", registrant=owner
    ... )
    >>> for i in range(config.codeimport.consecutive_failure_limit):
    ...     dummy = make_finished_import(
    ...         code_import, CodeImportResultStatus.FAILURE, factory=factory
    ...     )
    ...
    >>> logout()

This is shown on the branch index page:

    >>> user_browser.open(
    ...     "http://code.launchpad.test/~import-owner/imported/trunk"
    ... )
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(user_browser.contents, "failing-try-again")
    ...     )
    ... )
    The import has been suspended because it failed 5 or more times in
    succession.

Any logged in user will also see a button that can request the import
be tried again.

    >>> user_browser.getControl("Try Again")
    <SubmitControl ...>

Anonymous users do not see this button, however.

    >>> anon_browser.open(
    ...     "http://code.launchpad.test/~import-owner/imported/trunk"
    ... )
    >>> anon_browser.getControl("Try Again")
    Traceback (most recent call last):
      ...
    LookupError: ...

Clicking on the link sets the review status back to REVIEWED and
requests that an import be performed immediately.

    >>> def print_import_details(browser):
    ...     div = find_tag_by_id(browser.contents, "import-details")
    ...     print(extract_text(div))
    ...
    >>> user_browser.getControl("Try Again").click()
    >>> print_import_details(user_browser)
    Import Status: Reviewed
    ...
    The next import is scheduled to run as soon as possible (requested by
    No Privileges Person).
    ...

