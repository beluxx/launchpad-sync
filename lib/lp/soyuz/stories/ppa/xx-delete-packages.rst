PPA package deletion
====================

The PPA 'Delete packages' view allows users to delete packages form
their PPAs via the web UI. Only the owner of the PPA and Launchpad
administrators may access this page.

Anonymous and an ordinary user cannot access Celso's PPA package
console, even if they try the URL directly.

    >>> anon_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> anon_browser.getLink("Delete packages").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> anon_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+delete-packages"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ..., 'launchpad.Edit')

    >>> user_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> user_browser.getLink("Delete packages").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> user_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+delete-packages"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ..., 'launchpad.Edit')

Only Celso and Foo bar can access the 'Delete packages' page for
Celso's PPA.

    >>> cprov_browser = setupBrowser(
    ...     auth="Basic celso.providelo@canonical.com:test"
    ... )
    >>> cprov_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> cprov_browser.getLink("Delete packages").click()
    >>> print(cprov_browser.title)
    Delete packages from PPA for Celso Providelo...

    >>> admin_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> admin_browser.getLink("Delete packages").click()
    >>> print(admin_browser.title)
    Delete packages from PPA for Celso Providelo...

Once accessed the page provides a way to search for published package
sources and optionally delete one or more matching packages via POST
form.

When the 'Delete packages' page is loaded a list of all published
sources is presented,

    >>> print_ppa_packages(admin_browser.contents)
    Source            Published   Status     Series          Section  Build
        Status
    cdrkit - 1.0      2007-07-09  Published  Breezy-autotest Editors  i386
    iceweasel...(...) 2007-07-09  Published  Warty           Editors  i386
    pmount - 0.1-1    2007-07-09  Published  Warty           Editors

An informational message also directs the user to the PPA delete package help
page via a link:

    >>> admin_browser.getLink("deleting a package").url
    'https://help.launchpad.net/Packaging/PPA/Deleting'

The user can update the form to only list published sources with name
matching the given text.

    >>> admin_browser.getControl(name="field.name_filter").value = (
    ...     "nonexistentpackage"
    ... )
    >>> admin_browser.getControl("Filter").click()
    >>> print_ppa_packages(admin_browser.contents)
    No matching package for 'nonexistentpackage'.

    >>> admin_browser.getControl(name="field.name_filter").value = "pmount"
    >>> admin_browser.getControl("Filter").click()
    >>> print_ppa_packages(admin_browser.contents)
    Source           Published   Status     Series          Section  Build
        Status
    pmount - 0.1-1   2007-07-09  Published  Warty           Editors

The user may delete packages from a PPA without providing a reason
(deletion comment). Let's try it on mark's archive.

    >>> admin_browser.open(
    ...     "http://launchpad.test/~mark/+archive/ppa/+packages"
    ... )
    >>> admin_browser.getLink("Delete packages").click()
    >>> print_ppa_packages(admin_browser.contents)
    Source            Published   Status     Series          Section  Build
        Status
    iceweasel...(...) 2007-07-09  Published  Breezy-autotest Editors

Please note that the 'deletion_comment' field (which is optional) is empty.

    >>> admin_browser.getControl("Deletion comment").value
    ''

    >>> admin_browser.getControl(name="field.name_filter").value = ""
    >>> admin_browser.getControl(name="field.selected_sources").value = ["31"]
    >>> admin_browser.getControl("Request Deletion").click()
    >>> print_feedback_messages(admin_browser.contents)
    Source and binaries deleted by Foo Bar:
    iceweasel 1.0 in breezy-autotest
    Deletion comment: None

The single package in mark's archive was deleted successfully.

    >>> print_ppa_packages(admin_browser.contents)
    Source             Published   Status     Series   Section  Build Status
    iceweasel...(...)  2007-07-09  Deleted    ...

Now back to cprov's archive for the remaining tests.

    >>> admin_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> admin_browser.getLink("Delete packages").click()

Deletion requires, at least, one selected a source, otherwise an error
is issued.

    >>> admin_browser.getControl("Deletion comment").value = "DO IT"
    >>> admin_browser.getControl("Request Deletion").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    No sources selected.

Once the deletion is successfully requested, Foo Bar sees an
informational message containing the summary of the action
performed. The results should not include the just-deleted source.

Note that we will also include a unquoted portion of text in the
deletion comment, simulating a XSS attack. The current code will
automatically quote the text entered by the user resulting in an
entirely readable content.

    >>> admin_browser.getControl("Filter").click()
    >>> admin_browser.getControl(name="field.selected_sources").value = ["27"]
    >>> admin_browser.getControl("Deletion comment").value = (
    ...     "DO <where is my XSS ?> IT"
    ... )
    >>> admin_browser.getControl("Request Deletion").click()

    >>> print_feedback_messages(admin_browser.contents)
    Source and binaries deleted by Foo Bar:
    cdrkit 1.0 in breezy-autotest
    Deletion comment: DO &lt;where is my XSS ?&gt; IT

    >>> print_ppa_packages(admin_browser.contents)
    Source             Published   Status     Series   Section  Build Status
    cdrkit - 1.0       2007-07-09  Deleted    ...      Editors  i386
    iceweasel...(...)  2007-07-09  Published  Warty    Editors  i386
    pmount - 0.1-1     2007-07-09  Published  Warty    Editors

Here we can check for maliciously submitted forms containing
invalid data.

An nonexistent source:

    >>> admin_browser.getControl(name="field.selected_sources").value = [
    ...     "100"
    ... ]
    >>> admin_browser.getControl("Request Deletion").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    No sources selected.

An invalid value.

    >>> admin_browser.getControl(name="field.selected_sources").value = [
    ...     "blah"
    ... ]
    >>> admin_browser.getControl("Request Deletion").click()
    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    No sources selected.

The deleted record is now presented accordingly in the +index page. We
will use another browser to inspect the results of our deletions.

    >>> cprov_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> print_ppa_packages(cprov_browser.contents)
    Source            Published   Status     Series          Section  Build
        Status
    iceweasel...(...) 2007-07-09  Published  Warty           Editors  i386
    pmount - 0.1-1    2007-07-09  Published  Warty           Editors

    >>> cprov_browser.getControl(name="field.status_filter").value = [
    ...     "superseded"
    ... ]
    >>> cprov_browser.getControl("Filter", index=0).click()
    >>> print_ppa_packages(cprov_browser.contents)
    Source           Published   Status     Series          Section  Build
        Status
    cdrkit - 1.0     2007-07-09  Deleted    Breezy-autotest Editors  i386

    >>> cprov_browser.getControl(name="field.status_filter").value = [""]
    >>> cprov_browser.getControl("Filter", index=0).click()
    >>> print_ppa_packages(cprov_browser.contents)
    Source            Published   Status     Series          Section  Build
        Status
    cdrkit - 1.0      2007-07-09  Deleted    Breezy-autotest Editors  i386
    iceweasel...(...) 2007-07-09  Published  Warty           Editors  i386
    pmount - 0.1-1    2007-07-09  Published  Warty           Editors

Before deleting the remaining sources we will save a in this state for
the form re-submission tests.

    >>> re_post_browser = setupBrowser(
    ...     auth="Basic foo.bar@canonical.com:test"
    ... )
    >>> re_post_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> re_post_browser.getLink("Delete packages").click()

Multiple packages can be deleted in one single batch.

    >>> admin_browser.getControl("Filter").click()

    >>> admin_browser.getControl(name="field.selected_sources").value = [
    ...     "28",
    ...     "29",
    ... ]
    >>> admin_browser.getControl("Deletion comment").value = "DO IT AGAIN !"
    >>> admin_browser.getControl("Request Deletion").click()

    >>> print_feedback_messages(admin_browser.contents)
    Source and binaries deleted by Foo Bar:
    iceweasel 1.0 in warty
    pmount 0.1-1 in warty
    Deletion comment: DO IT AGAIN !

    >>> from lp.services.database.constants import UTC_NOW
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.soyuz.model.publishing import SourcePackagePublishingHistory
    >>> IStore(SourcePackagePublishingHistory).find(
    ...     SourcePackagePublishingHistory,
    ...     SourcePackagePublishingHistory.id.is_in([27, 28, 29]),
    ... ).set(scheduleddeletiondate=UTC_NOW)
    >>> transaction.commit()

The page doesn't present the form anymore, since there are no sources
available for deletion.

    >>> admin_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+delete-packages"
    ... )
    >>> main_content = find_main_content(admin_browser.contents)
    >>> print(
    ...     extract_text(
    ...         find_tags_by_class(str(main_content), "top-portlet")[0]
    ...     )
    ... )
    This PPA does not contain any source packages published.

All the packages were deleted via the admin_browser, now we will
re-POST the same deletion request via the browser saved in the
previous state to check if the bug 185922 is really fixed.

    >>> re_post_browser.getControl(name="field.selected_sources").value = [
    ...     "28",
    ...     "29",
    ... ]
    >>> re_post_browser.getControl("Deletion comment").value = "DO IT AGAIN !"
    >>> re_post_browser.getControl("Request Deletion").click()

    >>> print(extract_text(find_main_content(re_post_browser.contents)))
    Delete packages from PPA for Celso Providelo
    ...
    This PPA does not contain any source packages published.
    There is 1 error.

Any user can see that all packages present in Celso's PPA are deleted.

    >>> cprov_browser.getControl(name="field.status_filter").value = [""]
    >>> cprov_browser.getControl("Filter", index=0).click()
    >>> print_ppa_packages(cprov_browser.contents)
    Source            Published   Status     Series          Section  Build
        Status
    cdrkit - 1.0      2007-07-09  Deleted    Breezy-autotest Editors  i386
    iceweasel...(...) 2007-07-09  Deleted    Warty           Editors
    pmount - 0.1-1    2007-07-09  Deleted    Warty           Editors

PPAs that don't contain any published source packages, do not present
the 'Delete packages' link.

    >>> admin_browser.open(
    ...     "http://launchpad.test/~no-priv/+archive/ppa/+packages"
    ... )
    >>> admin_browser.getLink("Delete packages").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

Even when accessed manually the 'Delete packages' form is not rendered
for PPAs that do not contain any published packages, instead a clear
message is presented.

    >>> admin_browser.open(
    ...     "http://launchpad.test/~no-priv/+archive/ppa/+delete-packages"
    ... )
    >>> print(admin_browser.title)
    Delete packages from PPA for No Privileges Person...

    >>> print(extract_text(find_main_content(admin_browser.contents)))
    Delete packages from PPA for No Privileges Person
    ...
    This PPA does not contain any source packages published.

Removing source partially deleted
---------------------------------

The 'delete-packages' interface should allow users to enforce removal
of packages partially removed or superseded. It happens, for instance,
when:

 1. A source got deleted before it was completely built;

 2. The new source version in the series builds a smaller set of
    binaries than the previous version.

In order to reproduce this we will use SoyuzTestPublisher to create a
SUPERSEDED source with a PUBLISHED binary in No Privileged Person's PPA.

    >>> from zope.component import getUtility

    >>> from lp.services.database.constants import UTC_NOW
    >>> from lp.services.librarian.interfaces import ILibraryFileAliasSet
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.soyuz.enums import PackagePublishingStatus
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher

    >>> login("foo.bar@canonical.com")

    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> hoary = ubuntu.getSeries("hoary")

    >>> fake_chroot = getUtility(ILibraryFileAliasSet)[1]
    >>> trash = hoary["i386"].addOrUpdateChroot(fake_chroot)

    >>> test_publisher = SoyuzTestPublisher()

    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> name16 = getUtility(IPersonSet).getByName("name16")
    >>> test_publisher.person = name16

    >>> foo_pub_src = test_publisher.getPubSource(
    ...     version="1.0",
    ...     architecturehintlist="i386",
    ...     distroseries=hoary,
    ...     archive=no_priv.archive,
    ...     status=PackagePublishingStatus.SUPERSEDED,
    ... )
    >>> foo_pub_src.datesuperseded = UTC_NOW
    >>> foo_pub_src.datemadepending = UTC_NOW

    >>> foo_pub_binaries = test_publisher.getPubBinaries(
    ...     distroseries=hoary,
    ...     pub_source=foo_pub_src,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )

    >>> logout()
    >>> import transaction
    >>> transaction.commit()

The SUPERSEDED source we have just added is listed in the PPA
overview page.

    >>> user_browser.open(
    ...     "http://launchpad.test/~no-priv/+archive/ppa/+packages"
    ... )
    >>> user_browser.getControl(name="field.status_filter").value = [
    ...     "superseded"
    ... ]
    >>> user_browser.getControl("Filter", index=0).click()
    >>> print_ppa_packages(user_browser.contents)
    Source           Published   Status     Series          Section  Build
        Status
    foo - 1.0  (changes file)     Superseded Hoary           Base

We don't show the publishing details for binary packages, but the
presence of 'Built packages' and the binary filename in the 'Files'
section indicates to the user that it is still published.

    >>> expander_url = user_browser.getLink(
    ...     id="pub%s-expander" % foo_pub_src.id
    ... ).url
    >>> anon_browser.open(expander_url)
    >>> print(extract_text(anon_browser.contents))
    Publishing details
    Created ... ago by Foo Bar
    Changelog
    Builds
      i386
    Built packages
      foo-bin Foo app is great
    Package files
      foo-bin_1.0_i386.deb (18 bytes)
      foo_1.0.dsc (28 bytes)

Even if the source added is recorded as SUPERSEDED, it is still
available for deletion because it contains a PUBLISHED binary.

    >>> user_browser.getLink("Delete packages").click()
    >>> print(user_browser.title)
    Delete packages from PPA for No Privileges Person...

    >>> print_ppa_packages(user_browser.contents)
    Source           Published   Status     Series          Section  Build
        Status
    foo - 1.0  (changes file)     Superseded Hoary           Base

    >>> expander_url = user_browser.getLink(
    ...     id="pub%s-expander" % foo_pub_src.id
    ... ).url
    >>> anon_browser.open(expander_url)
    >>> print(extract_text(anon_browser.contents))
    Publishing details
    Created ... ago by Foo Bar
    Changelog
    Builds
      i386
    Built packages
      foo-bin Foo app is great
    Package files
      foo-bin_1.0_i386.deb (18 bytes)
      foo_1.0.dsc (28 bytes)

The list of 'deletable' sources can be filtered by status. The default
filter is 'Any Status', but the user can choose another.

    >>> print(user_browser.getControl(name="field.status_filter").value)
    ['']

When the user selects 'Published' filter and update the results, no
records are presented. No error message should be shown, since no text
filter was added.

    >>> user_browser.getControl(name="field.status_filter").value = [
    ...     "published"
    ... ]
    >>> user_browser.getControl("Filter").click()
    >>> print_ppa_packages(user_browser.contents)


When they select 'Superseded' the SUPERSEDED source shows up again.

    >>> user_browser.getControl(name="field.status_filter").value = [
    ...     "superseded"
    ... ]
    >>> user_browser.getControl("Filter").click()
    >>> print_ppa_packages(user_browser.contents)
    Source           Published   Status     Series          Section  Build
        Status
    foo - 1.0  (changes file)     Superseded Hoary           Base

The deletion works exactly as it does for PUBLISHED sources, both,
source and binaries are marked as DELETED and the corresponding
'datesuperseded' as set to 'now'.

    >>> deletion_comment = (
    ...     "Deletion of a number of base pairs that is not evenly "
    ...     "divisible by three will lead to a frameshift mutation."
    ... )
    >>> user_browser.getControl(name="field.selected_sources").value = [
    ...     str(foo_pub_src.id)
    ... ]
    >>> user_browser.getControl("Deletion comment").value = deletion_comment
    >>> user_browser.getControl("Request Deletion").click()

    >>> print_feedback_messages(user_browser.contents)
    Source and binaries deleted by No Privileges Person:
    foo 1.0 in hoary
    Deletion comment: Deletion of a number of base pairs that is ...

After the deletion, any user accessing No-privileges' PPA page can see
a row representing 'foo' and it is marked as 'superseded'. In its
corresponding expandable area, they can see that the 'Built packages'
section is omitted, however the source and binary files can be
downloaded from librarian.

Please note also how the deletion comment is displayed in its entirety as
opposed to being truncated after the first 20 characters.

    >>> user_browser.open(
    ...     "http://launchpad.test/~no-priv/+archive/ppa/+packages"
    ... )
    >>> user_browser.getControl(name="field.status_filter").value = [
    ...     "superseded"
    ... ]
    >>> user_browser.getControl("Filter", index=0).click()
    >>> print_ppa_packages(user_browser.contents)
    Source           Published   Status     Series          Section  Build
        Status
    foo - 1.0 (changes file)      Deleted    Hoary           Base

    >>> expander_url = user_browser.getLink(
    ...     id="pub%s-expander" % foo_pub_src.id
    ... ).url
    >>> anon_browser.open(expander_url)
    >>> print(extract_text(anon_browser.contents))
    Publishing details
    Deleted ... ago by No Privileges Person
    Deletion of a number of base pairs that is not evenly divisible by three
    will lead to a frameshift mutation.
    Changelog
    Builds
      i386
    Package files
      foo-bin_1.0_i386.deb (18 bytes)
      foo_1.0.dsc (28 bytes)

Once a deleted package gets removed from disk we render a message in
the "Publishing Status" section pointing to the users that even if the
package files were removed from the archive disk, it is still possible
to download them directly from librarian and the links are below.

Remove the just deleted publication from disk setting its
'dateremoved' attribute.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> login("foo.bar@canonical.com")
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> deleted_pub = no_priv.archive.getPublishedSources(
    ...     status=PackagePublishingStatus.DELETED
    ... ).first()
    >>> removeSecurityProxy(deleted_pub).dateremoved = deleted_pub.datecreated
    >>> logout()

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> flush_database_updates()

Now the 'Removed from disk' notice is rendered inside the expandable
area.

    >>> user_browser.getControl(name="field.status_filter").value = [
    ...     "superseded"
    ... ]
    >>> user_browser.getControl("Filter", index=0).click()

    >>> expander_url = user_browser.getLink(
    ...     id="pub%s-expander" % foo_pub_src.id
    ... ).url
    >>> anon_browser.open(expander_url)
    >>> print(extract_text(anon_browser.contents))
    Publishing details
    Removed from disk ... ago.
    Deleted ... ago by No Privileges Person
    Deletion of a number of base pairs that is not evenly divisible by ...
    Changelog
    Builds
      i386
    Package files
      foo-bin_1.0_i386.deb (18 bytes)
      foo_1.0.dsc (28 bytes)

The message for the file links does not appear for non-PPA publishings
as it would refer to non-existent links.

    >>> user_browser.open("http://launchpad.test/ubuntu/+source/foobar/1.0")
    >>> user_browser.getLink("See full publishing history").click()
    >>> print(extract_text(find_main_content(user_browser.contents)))
    Publishing history of foobar 1.0 source package in Ubuntu
    ...
    1.0
    Removed from disk on 2006-12-02.
    Deleted by Celso Providelo
    I do not like it.
    Published on 2006-12-01
    Copied from ubuntu breezy-autotest in Primary Archive for Ubuntu Linux
    ...
    «back
