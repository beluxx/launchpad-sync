Administrating code imports
===========================

The code import details are displayed on the main branch page for
imported branches.  If the logged in user is an import operator
(member of VCS imports or Launchpad admin) then they can see a link
to edit the details.

    >>> from lp.code.enums import (
    ...     RevisionControlSystems,
    ...     TargetRevisionControlSystems,
    ...     )
    >>> from lp.code.tests.helpers import GitHostingFixture
    >>> from lp.testing import login, logout
    >>> login('test@canonical.com')

    >>> svn_import = factory.makeProductCodeImport(
    ...     svn_branch_url='svn://svn.example.com/fooix/trunk')
    >>> from lp.services.webapp import canonical_url
    >>> svn_import_location = str(canonical_url(svn_import.branch))
    >>> svn_import_branch_unique_name = svn_import.branch.unique_name

    >>> bzr_svn_import = factory.makeProductCodeImport(
    ...     svn_branch_url='svn://svn.example.com/bzr-svn/trunk',
    ...     rcs_type=RevisionControlSystems.BZR_SVN)
    >>> bzr_svn_import_location = str(canonical_url(bzr_svn_import.branch))
    >>> bzr_svn_import_branch_unique_name = bzr_svn_import.branch.unique_name

    >>> cvs_import = factory.makeProductCodeImport(
    ...     cvs_root=":pserver:anonymous@cvs.example.com:/fooix",
    ...     cvs_module="fooix")
    >>> cvs_import_location = str(canonical_url(cvs_import.branch))
    >>> cvs_import_branch_unique_name = cvs_import.branch.unique_name

    >>> git_import = factory.makeProductCodeImport(
    ...     git_repo_url="git://git.example.org/fooix")
    >>> git_import_location = str(canonical_url(git_import.branch))
    >>> git_import_branch_unique_name = git_import.branch.unique_name

    >>> with GitHostingFixture():
    ...     git_to_git_import = factory.makeProductCodeImport(
    ...         git_repo_url="git://git.example.org/fooix2",
    ...         target_rcs_type=TargetRevisionControlSystems.GIT)
    >>> git_to_git_import_location = str(
    ...     canonical_url(git_to_git_import.git_repository))
    >>> git_to_git_repository_unique_name = (
    ...     git_to_git_import.git_repository.unique_name)

    >>> package_import = factory.makePackageCodeImport(
    ...     git_repo_url="http://git.example.org/zap")
    >>> package_import_location = str(canonical_url(package_import.branch))
    >>> package_import_branch_unique_name = package_import.branch.unique_name

    >>> logout()

    >>> import_browser = setupBrowser(
    ...     auth='Basic david.allouche@canonical.com:test')


Editing the import
------------------

Both VCS Imports members and Launchpad administrators can edit the
import:

    >>> def print_import_details(browser):
    ...     details = find_tag_by_id(
    ...         browser.contents, 'branch-import-details')
    ...     if details is None:
    ...         details = find_tag_by_id(
    ...             browser.contents, 'repository-import-details')
    ...     print(extract_text(details.div.div))

    >>> import_browser.open(svn_import_location)
    >>> print_import_details(import_browser)
    Import Status: Reviewed
    This branch is an import of the Subversion branch
    from svn://svn.example.com/fooix/trunk.
    The next import is scheduled to run
    as soon as possible.
    Edit import source or review import

    >>> import_browser.open(git_to_git_import_location)
    >>> print_import_details(import_browser)
    Import Status: Reviewed
    This repository is an import of the Git repository
    at git://git.example.org/fooix2.
    The next import is scheduled to run
    as soon as possible.
    Edit import source or review import


Editing details
---------------

There are a number of buttons shown on the editing page for
import operators.

    >>> import_browser.open(svn_import_location)
    >>> import_browser.getLink('Edit import source or review import').click()
    >>> print_submit_buttons(import_browser.contents)
    Update
    Mark Invalid
    Suspend
    Mark Failing

A cancel link is also shown next to the buttons, that takes the user
back to the main branch details page.

    >>> import_browser.getLink('Cancel').url == svn_import_location
    True

Only the fields that are relevant to the type of import are shown
in the form.

    >>> def print_form_fields(browser):
    ...     tags = find_tags_by_class(browser.contents, 'textType')
    ...     for tag in tags:
    ...         print('%s: %s' % (tag['name'], tag['value']))

    >>> print_form_fields(import_browser)
    field.url: svn://svn.example.com/fooix/trunk

    >>> import_browser.open(cvs_import_location)
    >>> import_browser.getLink('Edit import source or review import').click()
    >>> print_form_fields(import_browser)
    field.cvs_root: :pserver:anonymous@cvs.example.com:/fooix
    field.cvs_module: fooix

    >>> import_browser.open(git_import_location)
    >>> import_browser.getLink('Edit import source or review import').click()
    >>> print_form_fields(import_browser)
    field.url: git://git.example.org/fooix

    >>> import_browser.open(git_to_git_import_location)
    >>> import_browser.getLink('Edit import source or review import').click()
    >>> print_form_fields(import_browser)
    field.url: git://git.example.org/fooix2

    >>> import_browser.open(package_import_location)
    >>> import_browser.getLink('Edit import source or review import').click()
    >>> print_form_fields(import_browser)
    field.url: http://git.example.org/zap


Editing the import location
+++++++++++++++++++++++++++

The +edit-import page allows the import operator to edit the location
an import is from, for example to add a user name and password to the
url.

This is true for Subversion imports,

    >>> import_browser.open(svn_import_location + '/+edit-import')
    >>> import_browser.getControl('URL').value = \
    ...     'svn://user:password@svn-new.example.com/fooix/trunk'
    >>> import_browser.getControl('Update').click()
    >>> print_feedback_messages(import_browser.contents)
    The code import has been updated.

bzr-svn imports,

    >>> import_browser.open(bzr_svn_import_location + '/+edit-import')
    >>> import_browser.getControl('URL').value = \
    ...     'svn://user:password@svn-new.example.com/bzr-svn/trunk'
    >>> import_browser.getControl('Update').click()
    >>> print_feedback_messages(import_browser.contents)
    The code import has been updated.

CVS imports,

    >>> import_browser.open(cvs_import_location + '/+edit-import')
    >>> import_browser.getControl('Repository').value = \
    ...     ':pserver:anonymous@cvs-new.example.com:/fooix'
    >>> import_browser.getControl('Module').value = \
    ...     'fooix2'
    >>> import_browser.getControl('Update').click()
    >>> print_feedback_messages(import_browser.contents)
    The code import has been updated.

Git-to-Bazaar imports,

    >>> import_browser.open(git_import_location + '/+edit-import')
    >>> import_browser.getControl('URL').value = \
    ...     'git://user:password@git-new.example.org/fooix'
    >>> import_browser.getControl('Update').click()
    >>> print_feedback_messages(import_browser.contents)
    The code import has been updated.

Git-to-Git imports,

    >>> import_browser.open(git_to_git_import_location + '/+edit-import')
    >>> import_browser.getControl('URL').value = \
    ...     'git://user:password@git-new.example.org/fooix2'
    >>> import_browser.getControl('Update').click()
    >>> print_feedback_messages(import_browser.contents)
    The code import has been updated.

and imports targetting source packages.

    >>> import_browser.open(package_import_location + '/+edit-import')
    >>> import_browser.getControl('URL').value = \
    ...     'http://metal.example.org/zap'
    >>> import_browser.getControl('Update').click()
    >>> print_feedback_messages(import_browser.contents)
    The code import has been updated.


Invalidating an import
++++++++++++++++++++++

    >>> import_browser.getLink('Edit import source or review import').click()
    >>> import_browser.getControl('Mark Invalid').click()
    >>> print_import_details(import_browser)
    Import Status: Invalid
    ...
    >>> print_feedback_messages(import_browser.contents)
    The code import has been set as invalid.


Suspending an import
++++++++++++++++++++

    >>> import_browser.getLink('Edit import source or review import').click()
    >>> import_browser.getControl('Suspend').click()
    >>> print_import_details(import_browser)
    Import Status: Suspended
    ...
    >>> print_feedback_messages(import_browser.contents)
    The code import has been suspended.


Marking an import as failing
++++++++++++++++++++++++++++

    >>> import_browser.getLink('Edit import source or review import').click()
    >>> import_browser.getControl('Mark Failing').click()
    >>> print_import_details(import_browser)
    Import Status: Failed
    ...
    >>> print_feedback_messages(import_browser.contents)
    The code import has been marked as failing.


Import details for a running job
--------------------------------

If the job for an approved import is running, then the import details
says how long ago since it started.

    >>> import_browser.getLink('Edit import source or review import').click()
    >>> import_browser.getControl('Approve').click()
    >>> print_import_details(import_browser)
    Import Status: Reviewed
    ...
    The next import is scheduled to run as soon as possible.
    Edit import source or review import

Now set the job as running.

    >>> login('david.allouche@canonical.com')
    >>> from lp.code.tests.codeimporthelpers import (
    ...     get_import_for_branch_name, make_running_import)
    >>> code_import = get_import_for_branch_name(
    ...     svn_import_branch_unique_name)

Set the started time to 2h 20m ago, and the approximate datetime
should show this as 2 hours.

    >>> from datetime import datetime, timedelta
    >>> import pytz
    >>> date_started = datetime.now(pytz.UTC) - timedelta(hours=2, minutes=20)
    >>> code_import = make_running_import(
    ...     code_import, date_started=date_started, factory=factory,
    ...     logtail="Changeset 1\nChangeset 2")
    >>> logout()

    >>> import_browser.open(svn_import_location)
    >>> print_import_details(import_browser)
    Import Status: Reviewed
    ...
    An import is currently running on machine-..., and was started 2 hours
    ago.  The last few lines of the job's output were:
        Changeset 1
        Changeset 2
    Edit import source or review import


Import details for a import that has been imported successfully
---------------------------------------------------------------

If a branch has been successfully imported in the past, then the date
that it was last successful is shown, as well as when the next import
will be run -- which is, by default for Subversion, six hours after the
last import completed, and so in this case in about three hours.

    >>> login('david.allouche@canonical.com')
    >>> from lp.code.tests.codeimporthelpers import (
    ...     make_finished_import)
    >>> date_finished = datetime(2007,9,10,12, tzinfo=pytz.UTC)
    >>> code_import = get_import_for_branch_name(
    ...     svn_import_branch_unique_name)
    >>> code_import = make_finished_import(code_import, factory=factory,
    ...                                    date_finished=date_finished)
    >>> logout()

    >>> import_browser.open(svn_import_location)
    >>> print_import_details(import_browser)
    Import Status: Reviewed
    This branch is an import of the Subversion branch from
        svn://user:password@svn-new.example.com/fooix/trunk.
    The next import is scheduled to run in 3 hours.
    Last successful import was on 2007-09-10.
    ...


Requesting an import
--------------------

If an import is waiting for its next update, any logged in user can
click a button to request an immediate import.

    >>> sample_person_browser = setupBrowser(
    ...     auth='Basic test@canonical.com:test')
    >>> sample_person_browser.open(import_browser.url)
    >>> sample_person_browser.getControl('Import Now')
    <SubmitControl ...>

Anonymous users cannot see this button.

    >>> anon_browser.open(import_browser.url)
    >>> anon_browser.getControl('Import Now')
    Traceback (most recent call last):
      ...
    LookupError: label ...'Import Now'
    ...

If the logged in user clicks this button, the import will be scheduled
to run ASAP and the fact that the import has been requested is
displayed.

    >>> sample_person_browser.getControl('Import Now').click()
    >>> print_feedback_messages(sample_person_browser.contents)
    Import will run as soon as possible.
    >>> print_import_details(sample_person_browser)
    Import Status: Reviewed
    This branch is an import of the Subversion branch from
        svn://user:password@svn-new.example.com/fooix/trunk.
    The next import is scheduled to run as soon as possible (requested
    by Sample Person).
    Last successful import was on 2007-09-10.
    ...
