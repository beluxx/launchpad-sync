Editing PPA dependencies
========================

The PPA 'Edit dependency' view allows users to remove or add
dependencies to their PPAs via the web UI.

Only the owner of the PPA and Launchpad administrators may access this page.

Anonymous and unprivileged users cannot access Celso's PPA interface to
edit dependencies, even if they try the URL directly.

    >>> anon_browser.open("http://launchpad.test/~cprov/+archive/ubuntu/ppa")
    >>> anon_browser.getLink("Edit PPA dependencies").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> anon_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/ppa/"
    ...     "+edit-dependencies"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ..., 'launchpad.Edit')

    >>> user_browser.open("http://launchpad.test/~cprov/+archive/ubuntu/ppa")
    >>> user_browser.getLink("Edit PPA dependencies").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> user_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/ppa/"
    ...     "+edit-dependencies"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ..., 'launchpad.Edit')

Users are able to change dependencies of their PPAs before uploading
any sources.

    >>> no_priv_browser = setupBrowser(
    ...     auth="Basic no-priv@canonical.com:test"
    ... )
    >>> no_priv_browser.open(
    ...     "http://launchpad.test/~no-priv/+archive/ubuntu/ppa"
    ... )

    >>> no_priv_browser.getLink("Edit PPA dependencies").click()
    >>> print(no_priv_browser.url)
    http://launchpad.test/~no-priv/+archive/ubuntu/ppa/+edit-dependencies

    >>> print(no_priv_browser.title)
    Edit PPA dependencies : PPA for No Privileges Person :
    No Privileges Person

Only Celso and an administrator can access the 'Edit PPA dependencies'
page for Celso's PPA.

    >>> cprov_browser = setupBrowser(
    ...     auth="Basic celso.providelo@canonical.com:test"
    ... )
    >>> cprov_browser.open("http://launchpad.test/~cprov/+archive/ubuntu/ppa")
    >>> cprov_browser.getLink("Edit PPA dependencies").click()
    >>> print(cprov_browser.url)
    http://launchpad.test/~cprov/+archive/ubuntu/ppa/+edit-dependencies
    >>> print(cprov_browser.title)
    Edit PPA dependencies : PPA for Celso Providelo : Celso Providelo

    >>> admin_browser.open("http://launchpad.test/~cprov/+archive/ubuntu/ppa")
    >>> admin_browser.getLink("Edit PPA dependencies").click()
    >>> print(admin_browser.url)
    http://launchpad.test/~cprov/+archive/ubuntu/ppa/+edit-dependencies
    >>> print(admin_browser.title)
    Edit PPA dependencies : PPA for Celso Providelo : Celso Providelo

Once accessed the page provides a way to remove recorded dependencies
via the POST form.

    >>> def print_ppa_dependencies(contents):
    ...     empty_dep = find_tag_by_id(contents, "empty-dependencies")
    ...     if empty_dep is not None:
    ...         print(extract_text(empty_dep))
    ...     dependencies = find_tags_by_class(contents, "ppa-dependencies")
    ...     for dep in dependencies:
    ...         print(extract_text(dep))
    ...

When the 'Edit dependencies' page is loaded it will list all dependencies.

    >>> print_ppa_dependencies(admin_browser.contents)
    No dependencies recorded for this PPA yet.


Adding dependencies
-------------------

As we can see Celso's PPA contains no dependencies, let's try
to add some.

The adding dependency input offers a interface to look for PPAs based
on the PPA fti and/or the PPA owner's fti via a IHugeVocabulary
popup. A valid term is the owner username.

An empty request doesn't change anything.

    >>> admin_browser.getControl("Add PPA dependency").value = ""
    >>> admin_browser.getControl("Save").click()

    >>> print_ppa_dependencies(admin_browser.contents)
    No dependencies recorded for this PPA yet.

An unknown term results in an error.

    >>> admin_browser.getControl("Add PPA dependency").value = "whatever"
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    Invalid value

When a valid PPA is chosen the dependency is added, a notification
is rendered on top of the page and the list of dependencies available
for removal is updated.

    >>> admin_browser.getControl("Add PPA dependency").value = (
    ...     "~mark/ubuntu/ppa"
    ... )
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    Dependency added: PPA for Mark Shuttleworth

    >>> admin_browser.reload()
    >>> print_ppa_dependencies(admin_browser.contents)
    PPA for Mark Shuttleworth

Trying to add a dependency that is already recorded results in a error.

    >>> admin_browser.getControl("Add PPA dependency").value = (
    ...     "~mark/ubuntu/ppa"
    ... )
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    This dependency is already registered.

Trying to add a dependency for the context PPA itself also results in
a error.

    >>> admin_browser.getControl("Add PPA dependency").value = (
    ...     "~cprov/ubuntu/ppa"
    ... )
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    An archive should not depend on itself.

If it's a new dependency everything is fine.

    >>> admin_browser.getControl("Add PPA dependency").value = (
    ...     "~no-priv/ubuntu/ppa"
    ... )
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    Dependency added: PPA for No Privileges Person

Now Celso's PPA will list Mark's and No-Priv's PPA as its dependencies.
Reloading will set old form values.

    >>> admin_browser.open(admin_browser.url)
    >>> print_ppa_dependencies(admin_browser.contents)
    PPA for Mark Shuttleworth
    PPA for No Privileges Person

The dependencies are presented in a separated section (below the
sources.list widget).

    >>> user_browser.open("http://launchpad.test/~cprov/+archive/ubuntu/ppa")
    >>> print_tag_with_id(user_browser.contents, "archive-dependencies")
    Dependencies:
    PPA for Mark Shuttleworth (included ... ago)
    PPA for No Privileges Person (included ... ago)

The dependency entries are links to their target archives.

    >>> print(user_browser.getLink("PPA for Mark Shuttleworth").url)
    http://launchpad.test/~mark/+archive/ubuntu/ppa

    >>> print(user_browser.getLink("PPA for No Privileges Person").url)
    http://launchpad.test/~no-priv/+archive/ubuntu/ppa

If, by any chance, a dependency gets disabled, the link is turned off
and the text '[disabled]' is appended to it. So PPA users will be
aware of this condition.

    # Disable Mark's PPA.
    >>> login("foo.bar@canonical.com")
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> mark.archive.disable()
    >>> logout()

    >>> anon_browser.open("http://launchpad.test/~cprov/+archive/ubuntu/ppa")
    >>> print_tag_with_id(anon_browser.contents, "archive-dependencies")
    Dependencies:
    PPA for Mark Shuttleworth [disabled] (included ... ago)
    PPA for No Privileges Person (included ... ago)

    >>> anon_browser.getLink("PPA for Mark Shuttleworth")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> print(anon_browser.getLink("PPA for No Privileges Person").url)
    http://launchpad.test/~no-priv/+archive/ubuntu/ppa

When accessed by their owners, a PPA depending on disabled archives
will additionally show an warning for uploaders. This way a PPA
maintainer can react to this problem.

    >>> cprov_browser.open("http://launchpad.test/~cprov/+archive/ubuntu/ppa")
    >>> upload_hint = find_tag_by_id(cprov_browser.contents, "upload-hint")
    >>> print(
    ...     extract_text(
    ...         first_tag_by_class(str(upload_hint), "message warning")
    ...     )
    ... )
    This PPA depends on disabled archives. it may cause spurious
    build failures or binaries with unexpected contents.

Re-enable Mark's PPA for subsequent tests.

    >>> login("foo.bar@canonical.com")
    >>> mark.archive.enable()
    >>> logout()


Removing dependencies
---------------------

One or more dependencies can be removed via this page, they are
presented as a vertical array of check-boxes labelled by dependency PPA
title.

If no dependency is selected and the configuration is save, no
dependencies get removed.

    >>> admin_browser.getControl("Save").click()

    >>> print_ppa_dependencies(admin_browser.contents)
    PPA for Mark Shuttleworth
    PPA for No Privileges Person

On successful removals, a notification is rendered and the list of
dependencies is refreshed.

    >>> admin_browser.getControl(name="field.selected_dependencies").value = [
    ...     "~mark/ubuntu/ppa",
    ...     "~no-priv/ubuntu/ppa",
    ... ]
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    Dependencies removed:
    PPA for Mark Shuttleworth
    PPA for No Privileges Person

    >>> print_ppa_dependencies(admin_browser.contents)
    No dependencies recorded for this PPA yet.

Once the dependencies are removed, the 'archive-dependencies' section
is omitted from the PPA overview page for user without permission to
add new dependencies.

    >>> user_browser.open("http://launchpad.test/~cprov/+archive/ubuntu/ppa")
    >>> print(find_tag_by_id(user_browser.contents, "archive-dependencies"))
    None

    >>> anon_browser.open("http://launchpad.test/~cprov/+archive/ubuntu/ppa")
    >>> print(find_tag_by_id(user_browser.contents, "archive-dependencies"))
    None

We should also make sure that a user is unable to add a disabled PPA as a
dependency.

    # Disable Mark's PPA.
    >>> login("foo.bar@canonical.com")
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> mark.archive.disable()
    >>> logout()

    # Attempt to add Mark's PPA
    >>> admin_browser.getControl("Add PPA dependency").value = (
    ...     "~mark/ubuntu/ppa"
    ... )
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    Invalid value

    # When the page is reloaded, there shouldn't be any dependencies.
    >>> admin_browser.reload()
    >>> print_ppa_dependencies(admin_browser.contents)
    No dependencies recorded for this PPA yet.

Re-enable Mark's PPA for subsequent tests.

    >>> login("foo.bar@canonical.com")
    >>> mark.archive.enable()
    >>> logout()

Clear the page.

    >>> admin_browser.getControl("Add PPA dependency").value = ""
    >>> admin_browser.getControl("Save").click()
    >>> admin_browser.reload()
    >>> print_ppa_dependencies(admin_browser.contents)
    No dependencies recorded for this PPA yet.

Primary dependencies
--------------------

A user can modify how a PPA depends on its corresponding
primary archive.

A set of predefined options is presented as a radio button
selection.

When the page is loaded the selected option for 'Ubuntu dependencies'
field represents the current state of the PPA.

    >>> print_radio_button_field(
    ...     admin_browser.contents, "primary_dependencies"
    ... )
    ( ) Basic (only released packages).
    ( ) Security (basic dependencies and important security updates).
    (*) Default (security dependencies and recommended updates).
    ( ) Proposed (default dependencies and proposed updates).
    ( ) Backports (default dependencies and unsupported updates).

Same for the 'Ubuntu components' field:

    >>> print_radio_button_field(admin_browser.contents, "primary_components")
    (*) Use all Ubuntu components available.
    ( ) Use the same components used for each source in the Ubuntu
        primary archive.

The user can modify this aspect by selecting a different option and
clicking on 'Save'.

They will see a notification containing a summary of what was changed.

    >>> admin_browser.getControl(
    ...     "Proposed (default dependencies and proposed updates"
    ... ).selected = True
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    Primary dependency added: Primary Archive for Ubuntu Linux -
    PROPOSED (main, restricted, universe, multiverse)

The option submitted by the user is now selected when the page loads.

    >>> print_radio_button_field(
    ...     admin_browser.contents, "primary_dependencies"
    ... )
    ( ) Basic (only released packages).
    ( ) Security (basic dependencies and important security updates).
    ( ) Default (security dependencies and recommended updates).
    (*) Proposed (default dependencies and proposed updates).
    ( ) Backports (default dependencies and unsupported updates).

We will override the primary dependency configuration to only RELEASE
pocket.

    >>> admin_browser.getControl(
    ...     "Basic (only released packages)."
    ... ).selected = True
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    Primary dependency added: Primary Archive for Ubuntu Linux -
    RELEASE (main, restricted, universe, multiverse)

Now we see a PPA configured to depend only on RELEASE pocket.

    >>> print_radio_button_field(
    ...     admin_browser.contents, "primary_dependencies"
    ... )
    (*) Basic (only released packages).
    ( ) Security (basic dependencies and important security updates).
    ( ) Default (security dependencies and recommended updates).
    ( ) Proposed (default dependencies and proposed updates).
    ( ) Backports (default dependencies and unsupported updates).

    >>> print_radio_button_field(admin_browser.contents, "primary_components")
    (*) Use all Ubuntu components available.
    ( ) Use the same components used for each source in the Ubuntu
        primary archive.

In order to make the PPA use the default dependencies again the user
can simply select this pre-defined option and the form will restore
the default dependencies for them.

    >>> admin_browser.getControl(
    ...     "Default (security dependencies and recommended updates"
    ... ).selected = True
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    Default primary dependencies restored.

The default option is now selected.

    >>> print_radio_button_field(
    ...     admin_browser.contents, "primary_dependencies"
    ... )
    ( ) Basic (only released packages).
    ( ) Security (basic dependencies and important security updates).
    (*) Default (security dependencies and recommended updates).
    ( ) Proposed (default dependencies and proposed updates).
    ( ) Backports (default dependencies and unsupported updates).

    >>> print_radio_button_field(admin_browser.contents, "primary_components")
    (*) Use all Ubuntu components available.
    ( ) Use the same components used for each source in the Ubuntu
        primary archive.

Now we can simply change the primary archive components field.

    >>> admin_browser.getControl(
    ...     "Use the same components used for each source in the Ubuntu "
    ...     "primary archive."
    ... ).selected = True
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    Primary dependency added: Primary Archive for Ubuntu Linux - UPDATES

    >>> print_radio_button_field(
    ...     admin_browser.contents, "primary_dependencies"
    ... )
    ( ) Basic (only released packages).
    ( ) Security (basic dependencies and important security updates).
    (*) Default (security dependencies and recommended updates).
    ( ) Proposed (default dependencies and proposed updates).
    ( ) Backports (default dependencies and unsupported updates).

    >>> print_radio_button_field(admin_browser.contents, "primary_components")
    ( ) Use all Ubuntu components available.
    (*) Use the same components used for each source in the Ubuntu
        primary archive.

If we set the primary dependency to just main, which can only be done via the
API or the objects themselves, the form will show it to allow the user to
change it.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> from lp.testing import login_celebrity
    >>> ignored = login_celebrity("admin")
    >>> archive = factory.makeArchive()
    >>> main = getUtility(IComponentSet)["main"]
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu").main_archive
    >>> ignored = archive.addArchiveDependency(
    ...     ubuntu, PackagePublishingPocket.RELEASE, component=main
    ... )
    >>> url = canonical_url(archive)
    >>> logout()
    >>> admin_browser.open(url)
    >>> admin_browser.getLink("Edit PPA dependencies").click()
    >>> print_radio_button_field(admin_browser.contents, "primary_components")
    ( ) Use all Ubuntu components available.
    ( ) Use the same components used for each source in the Ubuntu
        primary archive.
    (*) Unsupported component (main)
    >>> admin_browser.open("http://launchpad.test/~cprov/+archive/ubuntu/ppa")
    >>> admin_browser.getLink("Edit PPA dependencies").click()


Everything in one click
-----------------------

The form can perform multiple actions in a single submit.

First we will create a PPA dependency for 'No privileged' PPA.

    >>> admin_browser.getControl("Add PPA dependency").value = (
    ...     "~no-priv/ubuntu/ppa"
    ... )
    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    Dependency added: PPA for No Privileges Person

Now the PPA uses the default primary dependency configuration and
contains a extra dependency.

    >>> print_radio_button_field(
    ...     admin_browser.contents, "primary_dependencies"
    ... )
    ( ) Basic (only released packages).
    ( ) Security (basic dependencies and important security updates).
    (*) Default (security dependencies and recommended updates).
    ( ) Proposed (default dependencies and proposed updates).
    ( ) Backports (default dependencies and unsupported updates).

    >>> print_radio_button_field(admin_browser.contents, "primary_components")
    ( ) Use all Ubuntu components available.
    (*) Use the same components used for each source in the Ubuntu
        primary archive.

    >>> print_ppa_dependencies(admin_browser.contents)
    PPA for No Privileges Person

In a single submit we will remove the PPA dependency, add another one
from 'Mark Shuttleworth' PPA and modify the primary dependency to
RELEASE.

    >>> admin_browser.getControl(name="field.selected_dependencies").value = [
    ...     "~no-priv/ubuntu/ppa"
    ... ]

    >>> admin_browser.getControl(
    ...     "Use all Ubuntu components available."
    ... ).selected = True

    >>> admin_browser.getControl("Add PPA dependency").value = (
    ...     "~mark/ubuntu/ppa"
    ... )

    >>> admin_browser.getControl(
    ...     "Basic (only released packages)."
    ... ).selected = True

    >>> admin_browser.getControl("Save").click()
    >>> print_feedback_messages(admin_browser.contents)
    Primary dependency added:
       Primary Archive for Ubuntu Linux - RELEASE
       (main, restricted, universe, multiverse)
    Dependency added:
       PPA for Mark Shuttleworth
    Dependencies removed:
       PPA for No Privileges Person

All the modifications are immediately visible once the form is
processed.

    >>> print_radio_button_field(
    ...     admin_browser.contents, "primary_dependencies"
    ... )
    (*) Basic (only released packages).
    ( ) Security (basic dependencies and important security updates).
    ( ) Default (security dependencies and recommended updates).
    ( ) Proposed (default dependencies and proposed updates).
    ( ) Backports (default dependencies and unsupported updates).

    >>> print_radio_button_field(admin_browser.contents, "primary_components")
    (*) Use all Ubuntu components available.
    ( ) Use the same components used for each source in the Ubuntu
        primary archive.

    >>> print_ppa_dependencies(admin_browser.contents)
    PPA for Mark Shuttleworth


Primary dependencies in the PPA index page
------------------------------------------

Primary dependencies are presented with pocket information in the PPA
index page (see `IArchivedependency.title`).

    >>> admin_browser.open("http://launchpad.test/~cprov/+archive/ubuntu/ppa")
    >>> print(admin_browser.title)
    PPA for Celso Providelo : Celso Providelo

    >>> print_tag_with_id(admin_browser.contents, "archive-dependencies")
    Dependencies:
    PPA for Mark Shuttleworth (included ... ago)
    Primary Archive for Ubuntu Linux - RELEASE
    (main, restricted, universe, multiverse) (included ... ago)

Cancelling a form request
-------------------------

At anytime the form can be cancelled and the user will be taken to the
PPA context page and the action won't be executed.

    >>> admin_browser.getLink("Edit PPA dependencies").click()

    >>> admin_browser.getControl("Add PPA dependency").value = (
    ...     "~no-priv/ubuntu/ppa"
    ... )
    >>> admin_browser.getControl(name="field.selected_dependencies").value = [
    ...     "~mark/ubuntu/ppa"
    ... ]
    >>> admin_browser.getControl(
    ...     "Default (security dependencies and recommended updates)."
    ... ).selected = True

    >>> admin_browser.getLink("Cancel").click()
    >>> print(admin_browser.title)
    PPA for Celso Providelo : Celso Providelo

The dependencies were not modified.

    >>> print_tag_with_id(admin_browser.contents, "archive-dependencies")
    Dependencies:
    PPA for Mark Shuttleworth (included ... ago)
    Primary Archive for Ubuntu Linux - RELEASE
    (main, restricted, universe, multiverse) (included ... ago)

