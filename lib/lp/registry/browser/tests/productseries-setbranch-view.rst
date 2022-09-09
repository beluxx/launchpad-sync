Set branch
----------

The productseries +setbranch view allows the user to set a branch for
this series.  The branch can be one that already exists in Launchpad,
or a new branch in Launchpad can be defined, or it can be a repository
that exists externally in a variety of version control systems.

    >>> from lp.testing.pages import find_tag_by_id
    >>> driver = factory.makePerson()
    >>> from lp.registry.enums import TeamMembershipPolicy
    >>> team = factory.makeTeam(
    ...     owner=driver, membership_policy=TeamMembershipPolicy.MODERATED
    ... )
    >>> product = factory.makeProduct(name="chevy", owner=team)
    >>> series = factory.makeProductSeries(name="impala", product=product)
    >>> transaction.commit()
    >>> ignored = login_person(driver)
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver
    ... )
    >>> content = find_tag_by_id(view.render(), "maincontent")
    >>> print(content)
    <div...
    ...Link to a Bazaar branch already on Launchpad...
    ...Import a branch hosted somewhere else...
    ...Branch name:...
    ...Branch owner:...

The user can see instructions to push a branch.

    >>> instructions = find_tag_by_id(content, "push-instructions-bzr")
    >>> "bzr push lp:" in str(instructions)
    True


Linking to an existing branch
-----------------------------

If linking to an existing branch is selected then the branch location
must be provided.

    >>> form = {
    ...     "field.branch_type": "link-lp",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for error in view.errors:
    ...     print(error)
    ...
    The branch location must be set.

Setting the branch location to an invalid branch results in another
validation error.

    >>> form = {
    ...     "field.branch_type": "link-lp",
    ...     "field.branch_location": "foo",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for error in view.errors:
    ...     print("%s: %r" % (error.error_name, error.original_exception))
    ...
    Invalid value: InvalidValue("token ...'foo' not found in vocabulary")

Providing a valid branch results in a successful linking.

    >>> series.branch is None
    True
    >>> branch = factory.makeBranch(
    ...     name="impala-branch", owner=driver, product=product
    ... )
    >>> form = {
    ...     "field.branch_type": "link-lp",
    ...     "field.branch_location": branch.unique_name,
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for error in view.errors:
    ...     print(error)
    ...
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    Series code location updated.

    >>> print(series.branch.name)
    impala-branch

Revisiting the +setbranch page when the branch is already set will
show the branch location pre-populated with the existing value.

    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> print(view.widgets.get("branch_location")._getFormValue().unique_name)
    ~person.../chevy/impala-branch


Import a branch hosted elsewhere
--------------------------------

Importing an externally hosted branch can either be a mirror, if a
Bazaar branch, or an import, if a git, cvs, or svn branch.

Lots of data are required to create an import.

    >>> series = factory.makeProductSeries(name="blazer", product=product)
    >>> transaction.commit()

    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    >>> for error in view.errors:
    ...     print(error)
    ...
    You must set the external repository URL.
    You must specify the type of RCS for the remote host.
    The branch name must be set.
    The branch owner must be set.

For Bazaar branches the scheme may only be http or https.

    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "BZR",
    ...     "field.branch_name": "blazer-branch",
    ...     "field.branch_owner": team.name,
    ...     "field.repo_url": "bzr+ssh://bzr.com/foo",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    >>> for error in view.errors:
    ...     print(error)
    ...
    ('repo_url'...The URI scheme &quot;bzr+ssh&quot; is not allowed.
    Only URIs with the following schemes may be used: bzr, http,
    https'))

A correct URL is accepted.

    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "BZR",
    ...     "field.branch_name": "blazer-branch",
    ...     "field.branch_owner": team.name,
    ...     "field.repo_url": "http://bzr.com/foo",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> transaction.commit()
    >>> for error in view.errors:
    ...     print(error)
    ...
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    Code import created and branch linked to the series.
    >>> print(series.branch.name)
    blazer-branch
    >>> series.branch.registrant.name == driver.name
    True

External Bazaar imports can not use an Launchpad URL.

    >>> form["field.repo_url"] = "http://bazaar.launchpad.net/firefox/foo"
    >>> form["field.branch_name"] = "chevette-branch"
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> transaction.commit()
    >>> for error in view.errors:
    ...     print(error)
    ...
    You cannot create same-VCS imports for branches or repositories that are
    hosted by Launchpad.

Git imports can use a Launchpad URL.

    >>> form["field.repo_url"] = "https://git.launchpad.net/blazer"
    >>> form["field.rcs_type"] = "GIT"
    >>> form["field.branch_name"] = "blazer-git-branch"
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> transaction.commit()
    >>> for error in view.errors:
    ...     print(error)
    ...
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    Code import created and branch linked to the series.
    >>> print(series.branch.name)
    blazer-git-branch

Git branches cannot use svn.

    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "GIT",
    ...     "field.branch_name": "chevette-branch",
    ...     "field.branch_owner": team.name,
    ...     "field.repo_url": "svn://svn.com/chevette",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    >>> for error in view.errors:
    ...     print(error)
    ...
    ('repo_url'...'The URI scheme &quot;svn&quot; is not allowed.  Only
    URIs with the following schemes may be used: git, http, https'))

But Git branches may use git.

    >>> series = factory.makeProductSeries(name="chevette", product=product)
    >>> transaction.commit()
    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "GIT",
    ...     "field.branch_name": "chevette-branch",
    ...     "field.branch_owner": team.name,
    ...     "field.repo_url": "git://github.com/chevette",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> transaction.commit()
    >>> for error in view.errors:
    ...     print(error)
    ...
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    Code import created and branch linked to the series.
    >>> print(series.branch.name)
    chevette-branch

But Subversion branches cannot use git.

    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "BZR_SVN",
    ...     "field.branch_name": "suburban-branch",
    ...     "field.branch_owner": team.name,
    ...     "field.repo_url": "git://github.com/suburban",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    >>> for error in view.errors:
    ...     print(error)
    ...
    ('repo_url'...'The URI scheme &quot;git&quot; is not allowed.  Only
    URIs with the following schemes may be used: http, https, svn'))

But Subversion branches may use svn as the scheme.

    >>> series = factory.makeProductSeries(name="suburban", product=product)
    >>> transaction.commit()
    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "BZR_SVN",
    ...     "field.branch_name": "suburban-branch",
    ...     "field.branch_owner": team.name,
    ...     "field.repo_url": "svn://svn.com/suburban",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for error in view.errors:
    ...     print(error)
    ...
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    Code import created and branch linked to the series.
    >>> print(series.branch.name)
    suburban-branch

CVS branches must use http or https as the scheme and must have the
CVS module field specified.

    >>> series = factory.makeProductSeries(name="corvair", product=product)
    >>> transaction.commit()
    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "CVS",
    ...     "field.branch_name": "corvair-branch",
    ...     "field.branch_owner": team.name,
    ...     "field.repo_url": "https://cvs.com/branch",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    >>> for error in view.errors:
    ...     print(error)
    ...
    The CVS module must be set.

    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "CVS",
    ...     "field.branch_name": "corvair-branch",
    ...     "field.branch_owner": team.name,
    ...     "field.repo_url": "https://cvs.com/branch",
    ...     "field.cvs_module": "root",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for error in view.errors:
    ...     print(error)
    ...
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    Code import created and branch linked to the series.
    >>> print(series.branch.name)
    corvair-branch

Attempting to import a location that has already been imported results
in an error.

    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "GIT",
    ...     "field.branch_name": "chevette-branch-dup",
    ...     "field.branch_owner": team.name,
    ...     "field.repo_url": "git://github.com/chevette",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for error in view.errors:
    ...     print(error)
    ...
    <BLANKLINE>
    This foreign branch URL is already specified for
    the imported branch
    <a href='http://.../chevy/chevette-branch'>~.../chevy/chevette-branch</a>.
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...

Using a branch name that already exists results in an error.

    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "GIT",
    ...     "field.branch_name": "chevette-branch",
    ...     "field.branch_owner": team.name,
    ...     "field.repo_url": "git://github.com/different/chevette",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for error in view.errors:
    ...     print(error)
    ...
    There is already an existing import for
    <a href="http://.../chevy">chevy</a>
    with the name of
    <a href="http://.../chevy/chevette-branch">chevette-branch</a>.
    >>> print(view.errors_in_action)
    True
    >>> print(view.next_url)
    None

    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...

Bazaar external branches are handled differently but they also give an
error if a duplicate name is used.

    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "BZR",
    ...     "field.branch_name": "blazer-branch",
    ...     "field.branch_owner": team.name,
    ...     "field.repo_url": "http://bzr.com/foo",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for error in view.errors:
    ...     print(error)
    ...
    <BLANKLINE>
    This foreign branch URL is already specified for the imported branch
    <a href='http://.../blazer-branch'>...</a>.
    >>> print(view.errors_in_action)
    False
    >>> print(view.next_url)
    http://launchpad.test/chevy/corvair
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...

If the owner is set to a private team, an error is raised.

    >>> from lp.registry.enums import PersonVisibility
    >>> private_team = factory.makeTeam(
    ...     visibility=PersonVisibility.PRIVATE, members=[driver]
    ... )
    >>> form = {
    ...     "field.branch_type": "import-external",
    ...     "field.rcs_type": "BZR",
    ...     "field.branch_name": "sport-branch",
    ...     "field.branch_owner": private_team.name,
    ...     "field.repo_url": "http://bzr.com/sporty",
    ...     "field.actions.update": "Update",
    ... }
    >>> view = create_initialized_view(
    ...     series, name="+setbranch", principal=driver, form=form
    ... )
    >>> for error in view.errors:
    ...     print(error)
    ...
    Private teams are forbidden from owning external imports.
