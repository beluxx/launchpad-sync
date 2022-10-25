Person Packages
===============

All packages maintained or uploaded by a given person can be seen on
that person's +related-packages page, which is linked to from the
person's home page.

    >>> browser.open("http://launchpad.test/~mark/+related-packages")
    >>> print(browser.title)
    Related packages : Mark Shuttleworth

This page is just a summary of the user's packages and will only
display up to the most recent 30 items in each category.  However, it
has more links that take the user to batched listings in each category
where all items can be perused.

    >>> print(extract_text(find_tag_by_id(browser.contents, "navlinks")))
    Related packages
    Maintained packages
    Uploaded packages
    Related PPA packages
    Related projects
    Owned teams

    >>> print(browser.getLink("Maintained packages").url)
    http://launchpad.test/~mark/+maintained-packages
    >>> print(browser.getLink("Uploaded packages").url)
    http://launchpad.test/~mark/+uploaded-packages
    >>> print(browser.getLink("PPA packages").url)
    http://launchpad.test/~mark/+ppa-packages
    >>> print(browser.getLink("Related projects").url)
    http://launchpad.test/~mark/+related-projects

Each category on the summary page has a heading that shows how many
packages are being displayed.

    >>> browser.open("http://launchpad.test/~mark/+related-packages")
    >>> print(extract_text(find_tag_by_id(browser.contents, "packages")))
    Maintained packages
    Displaying first 5 packages out of 7 total
    ...
    Uploaded packages
    Displaying first 5 packages out of 6 total
    ...
    PPA packages
    1 package
    ...

name16, aka the esteemed Foo Bar, has 9 maintained packages in the sample
data.  The page lists columns of data, "Name", "Uploaded To" and "Version"
that link to a distributionsourcepackage, distroseriessourcepackage and
distrosourcepackagerelease respectively.

The package name column links to the distribution source package page.
The user chooses to see the distribution information for cnews:

    >>> browser.open("http://launchpad.test/~name16/+related-packages")
    >>> link = browser.getLink("cnews")
    >>> print(link)
    <Link text='cnews' url='http://launchpad.test/ubuntu/+source/cnews'>
    >>> link.click()
    >>> browser.title
    '...cnews... package : Ubuntu'

The second column links to the distribution series source package page. The
user follows the "Ubuntu Hoary" link next to cnews:

    >>> browser.open("http://launchpad.test/~name16/+related-packages")
    >>> link = browser.getLink(url="/ubuntu/hoary/+source/cnews")
    >>> print(link)
    <Link text='Ubuntu Hoary' ...>
    >>> link.click()
    >>> browser.title
    'Hoary (5.04) : cnews package : Ubuntu'

The third column links to the distribution source package release page. The
user follows the cnews version link to see the page.

    >>> browser.open("http://launchpad.test/~name16/+related-packages")
    >>> link = browser.getLink(url="/ubuntu/+source/cnews/cr.g7-37")
    >>> print(link)
    <Link ... url='http://launchpad.test/ubuntu/+source/cnews/cr.g7-37'>
    >>> link.click()
    >>> browser.title
    'cr.g7-37 : cnews package : Ubuntu'


Batched listing pages
---------------------

Following the navigation link to "Maintained packages" takes the user
to the page that lists maintained packages in batches.

    >>> browser.open("http://launchpad.test/~mark/+related-packages")
    >>> browser.getLink("Maintained packages").click()
    >>> print(extract_text(find_tag_by_id(browser.contents, "packages")))
    1...5 of 7 results
    ...
    Name        Uploaded to  Version   When        Failures
    alsa-utils  Debian Sid   1.0.9a-4  2005-07-01  None
    ...

The Maintained packages page only has data if the person or team has
maintained packages to show. No-priv does not maintain packages.

    >>> anon_browser.open("http://launchpad.test/~no-priv")
    >>> print_tag_with_id(anon_browser.contents, "ppas")
    Personal package archives
    PPA for No Privileges Person
    >>> anon_browser.open(
    ...     "http://launchpad.test/~no-priv/+maintained-packages"
    ... )
    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "packages")))
    Name...
    No Privileges Person does not maintain any packages.

The navigation link to "Uploaded packages" takes the user to the
page that lists uploaded packages in batches.

    >>> browser.getLink("Uploaded packages").click()
    >>> print(extract_text(find_tag_by_id(browser.contents, "packages")))
    1...5 of 6 results
    ...
    Name    Uploaded to          Version When        Failures
    foobar  Ubuntu Breezy-autotest  1.0  2006-12-01  i386
    ...

The navigation link to "PPA packages" takes the user to the
page that lists PPA packages in batches.

    >>> browser.getLink("PPA packages").click()
    >>> print(extract_text(find_tag_by_id(browser.contents, "packages")))
    1...1 of 1 result
    ...
    Name      Uploaded to           Version  When        Failures
    iceweasel PPA for Mark...Warty  1.0      2006-04-11  None
    1...1 of 1 result
    ...

Private PPA packages
--------------------

Packages listed in the PPA section of this page are filtered so that
if the user is not allowed to see a private package they are not present
in the list.  Private packages are defined as those which are only
published in a private archive; if they are published in a private
archive *and* a non-private archive, they are deemed to be non-private
because if a package is not exclusively in a private PPA it cannot be
really private if someone can see it somewhere else.  This situation is
going to be very rare, however it does cover one important scenario: the
embargoed archive implementation.  Here, private security uploads and
builds will take place in a private archive and once verified will be
simply copied across archives to the primary Ubuntu archive.  At that
point it makes no sense to keep the package private any more, because
it's available to anyone anyway.

Let's make a helper function to print the PPA packages from the page:

    >>> def print_ppa_rows(browser):
    ...     rows = find_tags_by_class(browser.contents, "ppa_row")
    ...     for row in rows:
    ...         print(extract_text(row))
    ...

Make a function to update the cached latest person source package release
records.

    >>> from lp.scripts.garbo import (
    ...     PopulateLatestPersonSourcePackageReleaseCache,
    ... )
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.testing.dbuser import switch_dbuser
    >>> from lp.soyuz.model.archive import Archive
    >>> from lp.services.database.interfaces import IPrimaryStore

    >>> def update_cached_records(delete_all=False):
    ...     store = IPrimaryStore(Archive)
    ...     if delete_all:
    ...         store.execute(
    ...             "delete from latestpersonsourcepackagereleasecache"
    ...         )
    ...     flush_database_updates()
    ...     switch_dbuser("garbo_frequently")
    ...     if delete_all:
    ...         store.execute("delete from garbojobstate")
    ...     job = PopulateLatestPersonSourcePackageReleaseCache(FakeLogger())
    ...     while not job.isDone():
    ...         job(chunk_size=100)
    ...     switch_dbuser("launchpad")
    ...


Create some new source packages, source1 and source2, both created by cprov
so that they appear in his +packages page.

    >>> from storm.expr import SQL
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.services.database.constants import UTC_NOW
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> from lp.soyuz.enums import PackagePublishingStatus

    >>> login("foo.bar@canonical.com")
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> nopriv = getUtility(IPersonSet).getByName("no-priv")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> nopriv_private_ppa = factory.makeArchive(
    ...     owner=nopriv, name="p3a", distribution=ubuntu, private=True
    ... )
    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> test_publisher = SoyuzTestPublisher()
    >>> test_publisher.prepareBreezyAutotest()
    >>> source1 = test_publisher.getPubSource(
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     sourcename="source1",
    ...     archive=cprov.archive,
    ...     distroseries=cprov.archive.distribution.currentseries,
    ...     date_uploaded=UTC_NOW - SQL("INTERVAL '1 second'"),
    ... )
    >>> source1.sourcepackagerelease.creator = cprov
    >>> source1_mark = source1.copyTo(
    ...     source1.distroseries, source1.pocket, mark.archive
    ... )
    >>> source2 = test_publisher.getPubSource(
    ...     status=PackagePublishingStatus.PUBLISHED,
    ...     sourcename="source2",
    ...     archive=nopriv_private_ppa,
    ... )
    >>> source2.sourcepackagerelease.creator = cprov

    >>> update_cached_records()
    >>> logout()

"source1" is now published in cprov and mark's PPA.  "source2" is only
published in no-priv's Private PPA.

Make user_browser a known user that does not conflict with "no-priv":

    >>> user_browser = setupBrowser(auth="Basic test@canonical.com:test")


Cprov's +related-packages page
------------------------------

For unprivileged users, cprov's displayed PPA packages only display
the one in his own public PPA because source2 is only published
in the private PPA of the "no-priv" user.

XXX Michael Nelson 2010-02-26 bug=394276: The following should be
a view test of PersonPPAPAckagesView.filterPPAPackageList(). They
are not always testing what we think they are, as the lines match
more packages than intended.

The logged-in user's case:

    >>> user_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(user_browser)
    source1 PPA for Celso Providelo - Ubuntu Hoary 666 ...ago None

The not logged-in (anonymous) user's case:

    >>> anon_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(anon_browser)
    source1 PPA for Celso Providelo - Ubuntu Hoary 666 ...ago None

However no-priv themselves and any Launchpad Administrator can still see
both packages:

    >>> nopriv_browser = setupBrowser(auth="Basic no-priv@canonical.com:test")
    >>> nopriv_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(nopriv_browser)
    source2 PPA named p3a for No Priv... Ubuntutest Breezy-autotest 666
        ...ago None
    source1 PPA for Celso Providelo - Ubuntu Hoary 666 ...ago None

    >>> admin_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(admin_browser)
    source2 PPA named p3a for No Priv... Ubuntutest Breezy-autotest 666
        ...ago None
    source1 PPA for Celso Providelo - Ubuntu Hoary 666 ...ago None

Let's move the publication of source1 from mark's public archive to his
private one and the view the page again.

    >>> login("admin@canonical.com")
    >>> mark_private_ppa = factory.makeArchive(
    ...     owner=mark, name="p3a", distribution=ubuntu, private=True
    ... )
    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(source1_mark).archive = mark_private_ppa
    >>> logout()

    Update the releases cache table.
    >>> update_cached_records(True)

    >>> user_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(user_browser)
    source1 PPA for Celso Providelo - Ubuntu Hoary 666 ...ago None

    >>> anon_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(anon_browser)
    source1 PPA for Celso Providelo - Ubuntu Hoary 666 ...ago None

Notice that the source1 package is still appearing because it is also
published in some non-private archives, which override the private nature
of mark's archive.

Let's move the publication of source1 from cprov's public archive to
his private one:

    >>> login("admin@canonical.com")
    >>> cprov_private_ppa = factory.makeArchive(
    ...     owner=cprov, name="p3a", distribution=ubuntu, private=True
    ... )
    >>> removeSecurityProxy(source1).archive = cprov_private_ppa
    >>> source1.sourcepackagerelease.upload_archive = cprov_private_ppa
    >>> logout()

    Update the releases cache table.
    >>> update_cached_records(True)

It will now disappear from the listings because it's not published in any
public archives.

    >>> user_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(user_browser)

Now we'll publish it in the primary archive.

    >>> login("foo.bar@canonical.com")
    >>> from lp.soyuz.enums import ArchivePurpose
    >>> from lp.soyuz.interfaces.archive import IArchiveSet
    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> primary = getUtility(IArchiveSet).getByDistroPurpose(
    ...     ubuntu, ArchivePurpose.PRIMARY
    ... )
    >>> source1_ubuntu = source1.copyTo(
    ...     source1.distroseries, source1.pocket, primary
    ... )
    >>> source1_ubuntu.setPublished()
    >>> update_cached_records()
    >>> logout()

This makes the package appear in the listings again because the primary
archive is public.

    >>> user_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(user_browser)
    source1 PPA named p3a for Celso... - Ubuntu Hoary 666 ...ago None

    >>> anon_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(anon_browser)
    source1 PPA named p3a for Celso... - Ubuntu Hoary 666 ...ago None

Even after the package is superseded, the package remains visible in
the listings.

    >>> login("foo.bar@canonical.com")
    >>> discard = source1_ubuntu.supersede()
    >>> update_cached_records()
    >>> logout()

    >>> user_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(user_browser)
    source1 PPA named p3a for Celso... - Ubuntu Hoary 666 ...ago None

    >>> anon_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(anon_browser)
    source1 PPA named p3a for Celso... - Ubuntu Hoary 666 ...ago None


Packages deleted from a PPA
---------------------------

When a package is deleted from a PPA, in contrast to the archive index
it will continue to appear in the related-software packages list.  This
is to be consistent with the other lists on these pages and also helps
some MOTU users in reviewing candidates' packages.

First list the packages in the PPA.

    >>> admin_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(admin_browser)
    source2 PPA named p3a for No Priv... - Ubuntutest Breezy-autotest 666
        ...ago None
    source1 PPA named p3a for Celso... - Ubuntu Hoary 666 ...ago None

Then delete the 'source2' package.

    >>> admin_browser.open(
    ...     "http://launchpad.test/~no-priv/+archive/p3a/+delete-packages"
    ... )
    >>> admin_browser.getControl(name="field.selected_sources").value = [
    ...     "%s" % source2.id
    ... ]
    >>> admin_browser.getControl("Deletion comment").value = "Bug 184490"
    >>> admin_browser.getControl("Request Deletion").click()

    >>> print_feedback_messages(admin_browser.contents)
    Source and binaries deleted by Foo Bar:
    source2 666 in breezy-autotest
    Deletion comment: Bug 184490

    >>> def print_ppa_packages(contents):
    ...     packages = find_tags_by_class(contents, "archive_package_row")
    ...     for pkg in packages:
    ...         print(extract_text(pkg))
    ...     empty_section = find_tag_by_id(contents, "empty-result")
    ...     if empty_section is not None:
    ...         print(extract_text(empty_section))
    ...
    >>> print_ppa_packages(admin_browser.contents)
    Source             Published   Status     Series   Section  Build Status
    source2 - 666...               Deleted    ...
    >>> update_cached_records()

Now re-list the PPA's packages, 'source2' was deleted but still
appears.

    >>> admin_browser.open("http://launchpad.test/~cprov/+related-packages")
    >>> print_ppa_rows(admin_browser)
    source2 PPA named p3a for No Priv... - Ubuntutest Breezy-autotest 666
        ...ago None
    source1 PPA named p3a for Celso... - Ubuntu Hoary 666 ...ago None

Please note also that disabled archives are not viewable by anonymous users.

    >>> def print_archive_package_rows(contents):
    ...     package_table = find_tag_by_id(
    ...         anon_browser.contents, "packages_list"
    ...     )
    ...     for ppa_row in package_table.find_all("tr"):
    ...         print(extract_text(ppa_row))
    ...

    >>> anon_browser.open("http://launchpad.test/~cprov/+archive/ppa")
    >>> print_archive_package_rows(anon_browser)
    Package     Version     Uploaded by
    ...
    pmount      0.1-1       no signer (2007-07-09)

    >>> login("foo.bar@canonical.com")
    >>> cprov.archive.disable()
    >>> update_cached_records()
    >>> logout()
    >>> anon_browser.open("http://launchpad.test/~cprov/+archive/ppa")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized:
    (..., 'browserDefault', 'launchpad.SubscriberView')
