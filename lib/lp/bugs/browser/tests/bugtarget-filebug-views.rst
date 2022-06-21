Filebug view classes
====================

The base class used for all the filebug pages is FileBugViewBase. It
contains enough functionality to file bug, the classes inheriting from
it only adds some more functionality, like adding fields, searching for
similar bug reports, etc.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.bugs.browser.bugtarget import FileBugViewBase
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> ubuntu_firefox = ubuntu.getSourcePackage('mozilla-firefox')
    >>> bug_data = dict(
    ...     title='Test Title', comment='Test description.')

We define a helper method here so that we can instantiate
FileBugViewBase and use it without any errors occuring, since we're
bypassing most of the view machinery. We also define a mock widget class
for the same purpose.

    >>> class MockWidget:
    ...     def __init__(self, name):
    ...         self.name = name

    >>> def create_view(context, request):
    ...     view = FileBugViewBase(context, request)
    ...     view.widgets = {
    ...         'filecontent': MockWidget(name='filecontent')}
    ...     return view

The validate and action don't use the request when filing the bug, so we
can pass an empty request and pass the data dict to the methods
directly.

    >>> login('no-priv@canonical.com')
    >>> filebug_view = create_view(ubuntu_firefox, LaunchpadTestRequest())
    >>> filebug_view.validate(bug_data) is None
    True

    >>> filebug_view.submit_bug_action.success(bug_data)
    >>> print(filebug_view.added_bug.title)
    Test Title

    >>> print(filebug_view.added_bug.description)
    Test description.


URLs to additional FileBug elements
-----------------------------------

FileBugViewBase provides properties that return the URLs of useful parts of
the +filebug process.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> filebug_view = create_initialized_view(
    ...     firefox, '+filebug')

The inline_filebug_form_url property returns the URL of the inline
filebug form so that it may be loaded asynchronously.

    >>> print(filebug_view.inline_filebug_form_url)
    http://launchpad.test/firefox/+filebug-inline-form

Similarly, the duplicate_search_url property returns the base URL for
the duplicate search view, which can be used to load the list of
possible duplicates for a bug asynchronously.

    >>> print(filebug_view.duplicate_search_url)
    http://launchpad.test/firefox/+filebug-show-similar


Adding tags to filed bugs
-------------------------

    >>> bug_data = dict(
    ...     title=u'Test Title', comment=u'Test description.',
    ...     tags=[u'foo', u'bar'])

The validate and action don't use the request when filing the bug, so we
can pass an empty request and pass the data dict to the methods
directly.

    >>> login('no-priv@canonical.com')
    >>> filebug_view = create_initialized_view(ubuntu_firefox, '+filebug')
    >>> filebug_view.validate(bug_data) is None
    True

    >>> filebug_view.submit_bug_action.success(bug_data)
    >>> print(filebug_view.added_bug.title)
    Test Title

    >>> print(filebug_view.added_bug.description)
    Test description.

    >>> for tag in filebug_view.added_bug.tags:
    ...     print(tag)
    bar
    foo


Filing security bugs
--------------------

The base class allows security bugs to be filed.

    >>> bug_data = dict(
    ...     title=u'Security bug', comment=u'Test description.',
    ...     security_related=u'on')

    >>> filebug_view = create_initialized_view(ubuntu_firefox, '+filebug')
    >>> filebug_view.validate(bug_data) is None
    True

    >>> filebug_view.submit_bug_action.success(bug_data)
    >>> print(filebug_view.added_bug.title)
    Security bug

    >>> filebug_view.added_bug.security_related
    True


Extra fields for privileged users
---------------------------------

Privileged users are offered several extra options when filing bugs.

    >>> owner = factory.makePerson(name=u'bug-superdude')
    >>> person = factory.makePerson()
    >>> product = factory.makeProduct(owner=owner)

    >>> ignored = login_person(person)
    >>> filebug_view = create_initialized_view(product, '+filebug')
    >>> normal_fields = set(filebug_view.field_names)
    >>> ignored = login_person(owner)
    >>> filebug_view = create_initialized_view(product, '+filebug')
    >>> owner_fields = set(filebug_view.field_names)
    >>> product.bug_supervisor = owner
    >>> supervisor_fields = set(filebug_view.field_names)

Privileged users get most of the same fields as normal users, plus a few
extra.  The security_related checkbox is replaced by an information_type
radio group.

    >>> normal_fields.remove('security_related')
    >>> owner_fields == supervisor_fields
    True
    >>> supervisor_fields.issuperset(normal_fields)
    True

    >>> for field in sorted(supervisor_fields - normal_fields):
    ...     print(field)
    assignee
    importance
    information_type
    milestone
    status

Bugs can be filed with settings for all these extra fields.

    >>> from lp.bugs.interfaces.bugtask import (
    ...     BugTaskImportance, BugTaskStatus)

    >>> milestone = factory.makeMilestone(
    ...     product=product, name=u'bug-superdude-milestone')

    >>> bug_data = dict(
    ...     title=u'Extra Fields Bug', comment=u'Test description.',
    ...     assignee=owner, importance=BugTaskImportance.HIGH,
    ...     milestone=milestone, status=BugTaskStatus.TRIAGED)
    >>> print(filebug_view.validate(bug_data))
    None

    >>> filebug_view.submit_bug_action.success(bug_data)
    >>> [added_bugtask] = filebug_view.added_bug.bugtasks

    >>> print(added_bugtask.status.title)
    Triaged

    >>> print(added_bugtask.importance.title)
    High

    >>> print(added_bugtask.assignee.name)
    bug-superdude

    >>> print(added_bugtask.milestone.name)
    bug-superdude-milestone
