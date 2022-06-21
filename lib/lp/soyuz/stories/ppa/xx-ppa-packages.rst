=====================
The PPA packages page
=====================

The PPA packages page is accessible from the PPA page.

    >>> anon_browser.open('http://launchpad.test/~cprov/+archive/ubuntu/ppa')
    >>> anon_browser.getLink('View package details').click()
    >>> print(anon_browser.url)
    http://launchpad.test/~cprov/+archive/ubuntu/ppa/+packages

    >>> print(anon_browser.title)
    Packages in...


Page structure
==============

The PPA packages page uses the 'Overview' application button and displays
a descriptive main heading.

    >>> print_location(anon_browser.contents)
    Hierarchy: Celso Providelo > PPA for Celso Providelo > Packages in...
    Tabs:
    * Overview (selected) - http://launchpad.test/~cprov
    * Code - http://code.launchpad.test/~cprov
    * Bugs - http://bugs.launchpad.test/~cprov
    * Blueprints - http://blueprints.launchpad.test/~cprov
    * Translations - http://translations.launchpad.test/~cprov
    * Answers - http://answers.launchpad.test/~cprov
    Main heading: Packages in ...PPA for Celso Providelo...

You can see the build details of the packages in the archive by using
the 'View all builds' link.

    >>> anon_browser.getLink('View all builds').click()
    >>> print(anon_browser.title)
    Builds : PPA for Celso Providelo : Celso Providelo

    >>> print(anon_browser.url)
    http://launchpad.test/~cprov/+archive/ubuntu/ppa/+builds

The rest of the builds page functionality is tested generically at
in xx-builds-pages.rst.


Package totals
==============

A summary of the package totals is presented in a portlet (although the
actual values are loaded in asynchronously.

    >>> anon_browser.open(
    ...     'http://launchpad.test/~cprov/+archive/ubuntu/ppa/+packages')
    >>> package_totals = find_portlet(
    ...     anon_browser.contents, "Package totals")
    >>> print(extract_text(package_totals))
    Package totals
    ...
    Package counters and estimated archive size temporarily
    unavailable.


Package build summary
=====================

A summary of the builds for the PPA is also presented.

    >>> build_summary = find_portlet(
    ...     anon_browser.contents, "View all builds Package build summary")
    >>> print(extract_text(build_summary))
    View...
    A total of 4 builds have been created for this PPA.
    Completed builds
    3 successful
    1 failed

Successful builds link directly to the builds filter.

    >>> successful_builds_link = anon_browser.getLink('3 successful')
    >>> print(successful_builds_link.url)
    http://launchpad.test/~cprov/+archive/ubuntu/ppa/+builds?build_state=built


The detailed Packages list
==========================

    >>> def print_archive_package_rows(contents):
    ...     package_table = find_tag_by_id(
    ...         contents, 'packages_list')
    ...     for ppa_row in package_table.find_all('tr'):
    ...         print(extract_text(ppa_row))

    >>> print_archive_package_rows(anon_browser.contents)
    Source              Published   Status     Series      Section  Build
        Status
    cdrkit - 1.0        2007-07-09  Published  Breezy-a... Editors  i386
    ice...(changes file) 2007-07-09  Published  Warty       Editors  i386
    pmount - 0.1-1      2007-07-09  Published  Warty       Editors

Each data row is expandable to contain some sections containing:

 * Publishing details
 * The source package's changelog
 * Any built packages and their description
 * The list of files for this package

    >>> expander_url = anon_browser.getLink(id='pub29-expander').url
    >>> anon_browser.open(expander_url)
    >>> print(extract_text(anon_browser.contents))
    Publishing details
      Published on 2007-07-09
      Copied from ubuntu hoary in Primary Archive for Ubuntu Linux
    Changelog
      pmount (0.1-1) hoary; urgency=low
      * Fix description (Malone #1)
      * Fix debian (Debian #2000)
      * Fix warty (Warty Ubuntu #1)
      -- Sample Person...
    Builds
      i386
    Built packages
      pmount
      pmount shortdesc
    Package files
      No files published for this package.

If a the binaries for a package are fully built, but have not yet been
published, this will be indicated to the viewer:

    # First, we'll update the binary publishing history for the i386
    # record so that it is pending publication.
    >>> login('foo.bar@canonical.com')
    >>> from zope.component import getUtility
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> cprov = getUtility(IPersonSet).getByName('cprov')
    >>> cprov_ppa = cprov.archive
    >>> pmount_i386_pub = cprov_ppa.getAllPublishedBinaries(
    ...     name=u'pmount', version='0.1-1')[1]
    >>> print(pmount_i386_pub.displayname)
    pmount 0.1-1 in warty i386
    >>> from lp.soyuz.enums import PackagePublishingStatus
    >>> naked_pub = removeSecurityProxy(pmount_i386_pub)
    >>> naked_pub.status = PackagePublishingStatus.PENDING
    >>> naked_pub.datepublished = None
    >>> transaction.commit()
    >>> logout()

    # Now, to re-display the pmount expanded section:
    >>> anon_browser.open(expander_url)
    >>> print(extract_text(anon_browser.contents))
    Note: Some binary packages for this source are not yet published in the
    repository.
    Publishing details
      Published on 2007-07-09
      Copied from ubuntu hoary in Primary Archive for Ubuntu Linux
    Changelog
      pmount (0.1-1) hoary; urgency=low
      * Fix description (Malone #1)
      * Fix debian (Debian #2000)
      * Fix warty (Warty Ubuntu #1)
      -- Sample Person...
    Builds
      i386 - Pending publication
    Built packages
      pmount
      pmount shortdesc
    Package files
      No files published for this package.

When the package is copied from a PPA, the archive title will link
back to the source PPA.

    >>> anon_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/ppa/+packages")
    >>> expander_url = anon_browser.getLink(id='pub28-expander').url
    >>> anon_browser.open(expander_url)
    >>> anon_browser.getLink("PPA for Mark Shuttleworth").url
    'http://launchpad.test/~mark/+archive/ubuntu/ppa'

This link is not present if the user does not have permission to view
the PPA.  We create a private PPA with a published source and then copy
the source into a public PPA to demonstrate this.

    >>> login('foo.bar@canonical.com')
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName(
    ...     'ubuntu')
    >>> warty = ubuntu.getSeries('warty')
    >>> private_ppa = factory.makeArchive(
    ...     name='p3a', private=True, owner=cprov,
    ...     distribution=ubuntu)
    >>> joe = factory.makePerson(name="joe")
    >>> public_ppa = factory.makeArchive(
    ...     owner=joe, distribution=ubuntu, name='ppa')
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> test_publisher = SoyuzTestPublisher()
    >>> test_publisher.prepareBreezyAutotest()
    >>> source = test_publisher.getPubSource(
    ...     sourcename='foo', archive=private_ppa, distroseries=warty)
    >>> copied_source = source.copyTo(
    ...     source.distroseries, source.pocket, public_ppa)
    >>> expander_link_id = "pub%s-expander" % copied_source.id
    >>> logout()


We can view the link on the public PPA to Celso's private PPA when logged
in as Celso.

    >>> cprov_browser = setupBrowser(
    ...     auth="Basic celso.providelo@canonical.com:test")
    >>> cprov_browser.open(
    ...     "http://launchpad.test/~joe/+archive/ubuntu/ppa/+packages")
    >>> expander_url = cprov_browser.getLink(id=expander_link_id).url
    >>> cprov_browser.open(expander_url)
    >>> print(cprov_browser.getLink("PPA named p3a for Celso Providelo").url)
    http://launchpad.test/~cprov/+archive/ubuntu/p3a

But Joe himself will not see the link.

    >>> joe_browser = setupBrowser(
    ...     auth="Basic joe@example.com:test")
    >>> joe_browser.open(expander_url)
    >>> joe_browser.getLink("PPA named p3a for Celso Providelo")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

And neither can an anonymous user.

    >>> anon_browser.open(expander_url)
    >>> anon_browser.getLink("PPA named p3a for Celso Providelo")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

While we are there, we can also see that the private PPA's 'repository-size'
pagelet isn't publicly available.

    >>> anon_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/p3a/"
    ...     "+repository-size")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: (..., 'launchpad.View')


Searching the packages list
===========================

We can search a PPA for a particular package.  A non-existent package shows
no results.

    >>> anon_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/ppa/+packages")
    >>> field = anon_browser.getControl(name='field.name_filter')
    >>> field.value = 'nonexistentpackage'
    >>> anon_browser.getControl('Filter', index=0).click()
    >>> len(find_tags_by_class(anon_browser.contents, 'archive_package_row'))
    0

Searching for the package iceweasel shows that Celso is providing this.

    >>> field = anon_browser.getControl(name='field.name_filter')
    >>> field.value = 'iceweasel'
    >>> anon_browser.getControl('Filter', index=0).click()
    >>> len(find_tags_by_class(anon_browser.contents, 'archive_package_row'))
    2

In order to have a wider coverage in search status filter we will
modify some publication in Celso's PPA to SUPERSEDED and DELETED
states. Note, for consistency we have to create the binary publishing records
for iceweasel before marking it as superseded.

    >>> login('celso.providelo@canonical.com')
    >>> cprov = getUtility(IPersonSet).getByName('cprov')
    >>> iceweasel_pub = cprov.archive.getPublishedSources(
    ...     name=u'iceweasel').first()
    >>> bpr = test_publisher.uploadBinaryForBuild(
    ...     iceweasel_pub.getBuilds()[0], 'bar-bin')
    >>> pub_bins = test_publisher.publishBinaryInArchive(
    ...     bpr, cprov.archive, status=PackagePublishingStatus.PUBLISHED)
    >>> iceweasel_pub.supersede()
    >>> pmount_pub = cprov.archive.getPublishedSources(name=u'pmount').first()
    >>> pmount_pub.requestDeletion(cprov, 'nhack !')
    >>> logout()
    >>> transaction.commit()

The default status filter is 'published', which means that, by
default, PPA pages will only present PUBLISHED or PENDING packages.

    >>> field = anon_browser.getControl(name='field.name_filter')
    >>> field.value = ''
    >>> anon_browser.getControl('Filter', index=0).click()
    >>> print_archive_package_rows(anon_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    cdrkit - 1.0    2007-07-09  Published  Breezy-autotest  Editors  i386

Use can explicitly select 'published' filter and will get the same result.

    >>> anon_browser.getControl(
    ...     name='field.status_filter').value = ['published']
    >>> anon_browser.getControl('Filter', index=0).click()
    >>> print_archive_package_rows(anon_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    cdrkit - 1.0    2007-07-09  Published  Breezy-autotest  Editors  i386

When needed the users can select the 'superseded' filter and the
result will only contain packages SUPERSEDED or DELETED.

    >>> anon_browser.getControl(
    ...     name='field.status_filter').value = ['superseded']
    >>> anon_browser.getControl('Filter', index=0).click()
    >>> print_archive_package_rows(anon_browser.contents)
    Source            Published    Status        Series   Section  Build
        Status
    i...(changes file) 2007-07-09   Superseded    Warty    Editors
    pmount - 0.1-1    2007-07-09   Deleted       Warty    Editors

The 'Any Status' filter is also available, so the user can search over
any package ever published in the context PPA.

    >>> anon_browser.getControl(name='field.status_filter').value = ['']
    >>> anon_browser.getControl('Filter', index=0).click()
    >>> print_archive_package_rows(anon_browser.contents)
    Source             Published    Status     Series      Section  Build
        Status
    cdrkit - 1.0       2007-07-09   Published  Breezy-a... Editors  i386
    ic...(changes file) 2007-07-09   Superseded Warty       Editors
    pmount - 0.1-1     2007-07-09   Deleted    Warty       Editors


Team PPA package pages
======================

Team PPA package pages contain an extra column showing which team member
uploaded the package. First we need to set up a team PPA and publish
something to it.

    >>> foo_browser = setupBrowser(auth="Basic foo.bar@canonical.com:test")
    >>> foo_browser.open("http://launchpad.test/~ubuntu-team/+activate-ppa")
    >>> foo_browser.getControl(name="field.displayname").value = (
    ...     'PPA for Ubuntu team')
    >>> foo_browser.getControl(name="field.accepted").value = True
    >>> foo_browser.getControl('Activate').click()
    >>> ubuntu_ppa_url = foo_browser.url

Publish mozilla-firefox to ubuntu-team's PPA and ensure that it is signed
by name16 (Foo Bar) who is a member - the signer is presented as the uploader
in the list.

    >>> from lp.registry.interfaces.sourcepackage import SourcePackageFileType
    >>> from lp.testing.sampledata import UBUNTU_UPLOAD_TEAM_NAME
    >>> login(ANONYMOUS)
    >>> team = getUtility(IPersonSet).getByName(UBUNTU_UPLOAD_TEAM_NAME)
    >>> key = factory.makeGPGKey(team.teamowner)
    >>> pub = factory.makeSourcePackagePublishingHistory(
    ...     archive=team.archive, dscsigningkey=key)
    >>> lfa = factory.makeLibraryFileAlias(filename='foo.orig.tar.gz')
    >>> ign = factory.makeSourcePackageReleaseFile(
    ...     sourcepackagerelease=pub.sourcepackagerelease, library_file=lfa,
    ...     filetype=SourcePackageFileType.ORIG_TARBALL)
    >>> logout()
    >>> transaction.commit()

Access ubuntu-team's PPA page:

    >>> foo_browser.open(ubuntu_ppa_url)
    >>> foo_browser.getLink('View package details').click()

The package row data shows the uploader:

    >>> print_archive_package_rows(foo_browser.contents)
    Source              Uploader ... Status   Series  Section  Build Status
    unique-from...      mark         Pending  Distroseries... Section...

Links from files go to their on-archive locations:

    >>> expander_id = find_tags_by_class(
    ...     foo_browser.contents, 'expander')[0]['id']
    >>> expander_url = foo_browser.getLink(id=expander_id).url
    >>> anon_browser.open(expander_url)
    >>> print(anon_browser.getLink("orig").url)
    http://.../+sourcefiles/.../foo.orig.tar.gz

The uploader name is linkified to that user's home page:

    >>> foo_browser.getLink(url="~mark").click()
    >>> foo_browser.url
    'http://launchpad.test/~mark'


PPA Build Status column
=======================

Each row in the PPA package list contains a special column that
summarises its 'build status'. It contains the following information
for each published source:

 * Completely built: green 'yes' icon only;

 * Build in progress: 'processing' icon, followed by the
   architecture tags being built linking to the corresponding build
   page

 * Build failures: red 'no' icon, followed by the architecture tags
   which have failed to build linking to the corresponding build page.

Anyone can see the build status for package in Celso's PPA.

    >>> anon_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/ppa/+packages")

    >>> def print_build_status(contents):
    ...     rows = find_tags_by_class(contents, 'archive_package_row')
    ...     headers = rows[0].find_all('th')
    ...     print(extract_text(headers[0]), extract_text(headers[-1]))
    ...     for row in rows[1:]:
    ...         columns = row.find_all('td')
    ...         name = extract_text(columns[0])
    ...         built_icon = columns[-1].img['src']
    ...         built_text = columns[-1].a
    ...         if built_text is not None:
    ...             built_text = built_text.decode_contents()
    ...         print(name, built_icon, built_text)

    >>> print_build_status(anon_browser.contents)
    Source                    Build Status
    cdrkit - 1.0              /@@/no i386

As mentioned before anyone can visualise 'at a glance' that there was
a failure while building 'cdrkit' source in Celso's PPA. They can also
easily see that the failure was in the i386 build, and optionally
click in the link to visit the build-record page (to check the dates
of downloading the buildlog).

    >>> anon_browser.getLink('i386').click()

    >>> print(anon_browser.title)
    i386 build of cdrkit 1.0 : PPA for Celso Providelo : Celso Providelo

This feature is also useful from the PPA owner perspective. When Celso
sees that there was a failure while building 'cdrkit' on i386 he can
quickly 'retry' the failure.

    >>> cprov_browser = setupBrowser(
    ...     auth='Basic celso.providelo@canonical.com:test')
    >>> cprov_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/ppa/+packages")

    >>> cprov_browser.getLink('i386').click()
    >>> cprov_browser.getLink("Retry this build").click()
    >>> cprov_browser.getControl("Retry Build").click()

At this point anyone can also visualise that 'cdrkit' source is being
built in Celso's PPA.

    >>> anon_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ubuntu/ppa/+packages")
    >>> print_build_status(anon_browser.contents)
    Source                    Build Status
    cdrkit - 1.0              /@@/build-needed i386

Again the architecture tags listed on the 'built' column link to the
corresponding build page.

    >>> anon_browser.getLink('i386').click()
    >>> print(anon_browser.title)
    i386 build of cdrkit 1.0 : PPA for Celso Providelo : Celso Providelo
