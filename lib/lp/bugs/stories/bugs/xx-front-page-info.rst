A +bugs page for a project shows different information, depending
on whether or not the project uses malone for bug tracking.

By default, projects are created without using any bugtracker, malone
or otherwise.  To demonstrate this, a new project is created.

    >>> from zope.component import getUtility
    >>> from lp.testing import login, logout
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login('foo.bar@canonical.com')
    >>> foobar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
    >>> test_project = factory.makeProduct(
    ...     name='test-project', title='Simple Test Project', owner=foobar)
    >>> logout()

The +bugs page for the project states that the project does
not use Launchpad for bug tracking.

    >>> anon_browser.open(
    ...     'http://bugs.launchpad.test/test-project/+bugs')
    >>> uses_malone_p = find_tag_by_id(anon_browser.contents, 'no-malone')
    >>> print(extract_text(uses_malone_p))
    Test-project must be configured in order for Launchpad to forward bugs to
    the project's developers.

Only users who have permission to do so can enable bug tracking
for a project.

    >>> find_tag_by_id(anon_browser.contents, 'no-malone-edit') is None
    True

    >>> admin_browser.open(
    ...   'http://bugs.launchpad.test/test-project/+bugs')
    >>> enable_tracker = find_tag_by_id(
    ...     admin_browser.contents, 'no-malone-edit')
    >>> print(extract_text(enable_tracker))
    Configure Bugs

The +bugs page for a project using Launchpad for bug tracking
shows controls for setting bug supervisor and states that no
bugs have been filed.

    >>> login('foo.bar@canonical.com')
    >>> uses_malone = factory.makeProduct(
    ...     name='uses-malone', title='Project Uses Malone',
    ...     official_malone=True)
    >>> logout()

    >>> anon_browser.open('http://bugs.launchpad.test/uses-malone/+bugs')
    >>> bug_supervisor = find_tag_by_id(
    ...     anon_browser.contents, 'bug-supervisor')
    >>> print(extract_text(bug_supervisor))
    Bug supervisor:
    None set

    >>> bug_list = find_tag_by_id(
    ...     anon_browser.contents, 'bugs-table-listing')
    >>> print(extract_text(bug_list))
    There are currently no open bugs.

Projects that use an external bug tracker will list the tracker on a
+bugs page.

    >>> login('foo.bar@canonical.com')
    >>> some_tracker = factory.makeBugTracker(
    ...     base_url='http://tracker.example.com/')
    >>> test_project.bugtracker = some_tracker
    >>> logout()
    >>> anon_browser.open(
    ...   'http://bugs.launchpad.test/test-project/+bugs')
    >>> tracker_text = find_tag_by_id(anon_browser.contents, 'bugtracker')
    >>> print(extract_text(tracker_text))
    Bugs are tracked in tracker.example.com/.

Projects that are linked to an Ubuntu distro source package and that
don't use Launchpad for bug tracking will inform the user that a bug can
be reported on the project's source packages.

    >>> login('foo.bar@canonical.com')
    >>> packaging = factory.makePackagingLink(
    ...     productseries=test_project.development_focus,
    ...     sourcepackagename='test-project-package',
    ...     in_ubuntu=True)
    >>> logout()
    >>> anon_browser.open(
    ...   'http://bugs.launchpad.test/test-project/+bugs')
    >>> print(extract_text(
    ...     find_tag_by_id(anon_browser.contents, 'also-in-ubuntu')))
    Ubuntu also tracks bugs for packages derived from this project:
    test-project-package in Ubuntu.
