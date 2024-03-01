Registering an upstream affected by a given bug
===============================================

The test browser does not support javascript
    >>> user_browser.open(
    ...     "http://launchpad.test/firefox/+bug/1/+choose-affected-product"
    ... )
    >>> find_link = user_browser.getLink("Find")
    >>> find_link.url
    'http://launchpad.test/firefox/+bug...'

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/firefox/+bug/1/+affects-new-product"
    ... )
    >>> user_browser.getControl("Bug URL").value = (
    ...     "http://bugs.foo.org/bugs/show_bug.cgi?id=42"
    ... )
    >>> user_browser.getControl("Project name").value = "The Foo Project"
    >>> user_browser.getControl("Project ID").value = "foo"
    >>> user_browser.getControl("Project summary").value = "The Foo Project"
    >>> user_browser.getControl("Continue").click()

We're now redirected to the newly created bugtask page.

    >>> user_browser.title
    'Bug #1 ... : Bugs : The Foo Project'

When creating a new upstream through this page we'll check if there's any
upstream already registered in Launchpad which uses the same bugtracker as
the one specified by the user. If there are any we present them as options
for the user to use as the affected upstream.

    >>> from lp.testing.pages import strip_label

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/tomcat/+bug/2/+affects-new-product"
    ... )
    >>> print(user_browser.title)
    Register project affected by...
    >>> user_browser.getControl("Bug URL").value = (
    ...     "http://bugs.foo.org/bugs/show_bug.cgi?id=421"
    ... )
    >>> user_browser.getControl("Project name").value = "The Bar Project"
    >>> user_browser.getControl("Project ID").value = "bar"
    >>> user_browser.getControl("Project summary").value = "The Bar Project"
    >>> user_browser.getControl("Continue").click()

    >>> print(user_browser.title)
    Register project affected by...

    >>> print_feedback_messages(user_browser.contents)
    There are some projects using the bug tracker you specified. One of
    these may be the one you were trying to register.
    >>> control = user_browser.getControl(name="field.existing_product")
    >>> [strip_label(label) for label in control.displayValue]
    ['The Foo Project']

Now we can either choose to report the bug as affecting our existing Foo
Project or create the new Bar Project.

    >>> user_browser.getControl("Use Existing Project")
    <SubmitControl name='field.actions.use_existing_product' type='submit'>
    >>> user_browser.getControl("Continue")
    <SubmitControl name='field.actions.continue' type='submit'>

First, let's use the existing project.

    >>> user_browser.getControl("Use Existing Project").click()
    >>> user_browser.title
    'Bug #2 (blackhole) ... : Bugs : The Foo Project'

    >>> from lp.bugs.tests.bug import print_remote_bugtasks
    >>> print_remote_bugtasks(user_browser.contents)
    The Foo Project ...    auto-bugs.foo.org #421

If we try using that same existing project again, we'll get an error
explaining we can't because it's already known that it's affected by
this bug.

    >>> user_browser.goBack()
    >>> user_browser.getControl("Use Existing Project").click()
    >>> print(user_browser.title)
    Register project affected by...
    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    ...
    A fix for this bug has already been requested for The Foo Project

Now we'll tell Launchpad to not use the existing upstream as we want to report
the bug as affecting another (unregistered) upstream.

    >>> user_browser.goBack()
    >>> user_browser.getControl("Bug URL").value = (
    ...     "http://bugs.foo.org/bugs/show_bug.cgi?id=123"
    ... )
    >>> user_browser.getControl("Continue").click()
    >>> user_browser.title
    'Bug #2 (blackhole) ... : Bugs : The Bar Project'
    >>> print_remote_bugtasks(user_browser.contents)
    The Bar Project ...   auto-bugs.foo.org #123
    The Bar Project ...   auto-bugs.foo.org #421

Error handling
--------------

If the URL of the remote bug is not recognized by Launchpad, we'll tell the
user and ask them to check if it's correct.

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/firefox/+bug/1/+affects-new-product"
    ... )
    >>> user_browser.getControl("Bug URL").value = (
    ...     "http://foo.org/notabug.cgi?id=42"
    ... )
    >>> user_browser.getControl("Project name").value = "Foo Project"
    >>> user_browser.getControl("Project ID").value = "bazfoo"
    >>> user_browser.getControl("Project summary").value = "The Foo Project"
    >>> user_browser.getControl("Continue").click()
    >>> print(user_browser.title)
    Register project affected by...
    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    Launchpad does not recognize the bug tracker at this URL.

