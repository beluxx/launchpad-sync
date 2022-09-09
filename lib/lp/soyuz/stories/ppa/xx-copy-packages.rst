PPA Package Copying
===================

We allow users to copy packages from PPAs they can view to another
that they upload packages to.

A package is copied by accessing a special PPA page that allows a user
to select:

 * One or more source packages from the current PPA;

 * A destination PPA amongst the ones they have access to, including the
   current one;

 * A destination series amongst all ubuntu series;

 * Whether or not to copy the binaries published by the selected
   sources in the current PPA.

The copy occurs immediately in the publishing records domain, so the
packages copied will be visible in the destination PPA page as
PENDING. The files will be published in the destination PPA archive
disk during the next publishing cycle, see `publishing.rst` for more
information.


Who can copy packages?
----------------------

Copying is only permitted for valid users, so Anonymous user can't
access 'Copy package' page from any PPA.

    >>> anon_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> anon_browser.getLink("Copy packages").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> anon_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+copy-packages"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ... 'launchpad.AnyPerson')

James is a valid user, however he doesn't have access to any PPA, he
is allowed to access the copy-packages interface in Celso's PPA, but
the form is not rendered, instead he is advised to activate his own
PPA in order to be able to copy packages.

    >>> jblack_browser = setupBrowser(
    ...     auth="Basic james.blackwell@ubuntulinux.com:test"
    ... )

    >>> jblack_extra_browser = setupBrowser(
    ...     auth="Basic james.blackwell@ubuntulinux.com:test"
    ... )

    >>> jblack_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> jblack_browser.getLink("Copy packages").click()

    >>> print(extract_text(find_main_content(jblack_browser.contents)))
    Copy packages from PPA for Celso Providelo
    ...
    To be able to copy packages you have to participate in at least one
    PPA. Activate your own PPA or join a team with an active PPA.
    Create a new PPA or «back

James will follow the advice and activate his PPA by clicking in the
provided link.

    >>> jblack_browser.getLink("Create a new PPA").click()
    >>> print(jblack_browser.title)
    Activate PPA : James Blackwell

    >>> jblack_browser.getControl(
    ...     name="field.displayname"
    ... ).value = "PPA for James Blackwell"
    >>> jblack_browser.getControl(name="field.accepted").value = True
    >>> jblack_browser.getControl(
    ...     name="field.description"
    ... ).value = "There we go ..."
    >>> jblack_browser.getControl("Activate").click()

    >>> print(jblack_browser.title)
    PPA for James Blackwell : James Blackwell

Now, that James has his own PPA, he navigates back to Celso's PPA
copy package interface can see packages to be copied.

    >>> jblack_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> jblack_browser.getLink("Copy packages").click()

    >>> print_ppa_packages(jblack_browser.contents)
    Source            Published   Status     Series           Section  Build
        Status
    cdrkit - 1.0      2007-07-09  Published  Breezy-autotest  Editors  i386
    iceweasel...(...) 2007-07-09  Published  Warty            Editors  i386
    pmount - 0.1-1    2007-07-09  Published  Warty            Editors


How does this copy-thing work?
------------------------------

As mentioned before, James can select one or more sources to be copied
to a PPA he has permission to upload.

We have to do some preparation in grumpy's sampledata to make it ready
for packages. This is certainly not part of the doctest story.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet

    >>> login("foo.bar@canonical.com")
    >>> from lp.services.librarian.interfaces import ILibraryFileAliasSet
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.buildmaster.interfaces.processor import IProcessorSet

    >>> fake_chroot = getUtility(ILibraryFileAliasSet)[1]

    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")

    >>> hoary = ubuntu.getSeries("hoary")
    >>> trash = hoary["i386"].addOrUpdateChroot(fake_chroot)

    >>> warty = ubuntu.getSeries("warty")
    >>> trash = warty["i386"].addOrUpdateChroot(fake_chroot)

    >>> person_set = getUtility(IPersonSet)
    >>> cprov = person_set.getByName("cprov")
    >>> grumpy = ubuntu.getSeries("grumpy")
    >>> grumpy_i386 = grumpy.newArch(
    ...     "i386", getUtility(IProcessorSet).getByName("386"), False, cprov
    ... )
    >>> grumpy.nominatedarchindep = grumpy_i386
    >>> trash = grumpy_i386.addOrUpdateChroot(fake_chroot)

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> flush_database_updates()
    >>> logout()

Copying packages will create jobs.  Define a simple doctest-friendly runner.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.soyuz.interfaces.packagecopyjob import (
    ...     IPlainPackageCopyJobSource,
    ... )

    >>> def run_copy_jobs():
    ...     login("foo.bar@canonical.com")
    ...     source = getUtility(IPlainPackageCopyJobSource)
    ...     for job in removeSecurityProxy(source).iterReady():
    ...         job.logger = FakeLogger()
    ...         job.start(manage_transaction=True)
    ...         try:
    ...             job.run()
    ...         except Exception:
    ...             job.fail(manage_transaction=True)
    ...         else:
    ...             job.complete(manage_transaction=True)
    ...     logout()
    ...

Let's say James wants to rebuild the Celso's 'pmount' source in his PPA.

He is a little confused by the number of packages presented by
default and wants to refine the options.

    >>> jblack_browser.getControl(name="field.name_filter").value = "pmount"
    >>> jblack_browser.getControl("Filter").click()

There we go, James can be certain about which package to select, only
pmount is presented.

    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    pmount - 0.1-1  2007-07-09  Published  Warty            Editors

James is intrigued and wants to see more information about this
source, thus he expands the hidden details-section area below the
'pmount' row to read its changelog.

In order to be able to get the details section for a specific package
in a PPA page, we have to retrieve the source publication ID. This
helper function will do this job in this test.

    >>> def getPPAPubIDsFor(owner_name, source_name=None, status=None):
    ...     login("foo.bar@canonical.com")
    ...     owner = person_set.getByName(owner_name)
    ...     pubs = owner.archive.getPublishedSources(
    ...         name=source_name, status=status
    ...     )
    ...     pub_ids = [str(pub.id) for pub in pubs]
    ...     logout()
    ...     return pub_ids
    ...

The page section id is built using "pub$ID" notation.

    >>> pmount_pub_id = getPPAPubIDsFor("cprov", "pmount")[0]
    >>> expander_url = jblack_browser.getLink(
    ...     id="pub%s-expander" % pmount_pub_id
    ... ).url
    >>> jblack_extra_browser.open(expander_url)
    >>> print(extract_text(jblack_extra_browser.contents))
    Publishing details
      Published on 2007-07-09
      Copied from ubuntu hoary in Primary Archive for Ubuntu Linux
    Changelog
      pmount (0.1-1) hoary; urgency=low
      * Fix description (Malone #1)
      * Fix debian (Debian #2000)
      * Fix warty (Warty Ubuntu #1)
      -- Sample Person &lt;test@canonical.com&gt;
      Tue, 7 Feb 2006 12:10:08 +0300
    Builds
      i386
    Built packages
      pmount pmount shortdesc
    Package files
      No files published for this package.

James is absolutely sure that's the package he wants, he selects it.

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     pmount_pub_id
    ... ]

Currently, James only has access to his just created PPA, which is the
default form value for 'Destination PPA'.

    >>> print(jblack_browser.getControl("Destination PPA").displayOptions)
    ['PPA for James Blackwell [~jblack/ubuntu/ppa]']

    >>> print(jblack_browser.getControl("Destination PPA").value)
    ['~jblack/ubuntu/ppa']

James notice that Celso's 'pmount' was uploaded and built in Warty,
but he is using Hoary. No problem, because he can select a destination
series while copying.

    >>> print(jblack_browser.getControl("Destination series").displayOptions)
    ['The same series', 'Breezy Badger Autotest', 'Grumpy', 'Hoary', 'Warty']

    >>> print(jblack_browser.getControl("Destination series").value)
    ['']

    >>> jblack_browser.getControl("Destination series").value = ["hoary"]

James may want to copy binaries over, or to do a full rebuild from
source, which is the default option.

    >>> print_radio_button_field(jblack_browser.contents, "include_binaries")
    (*) Rebuild the copied sources
    ( ) Copy existing binaries

James 'pushes the button', copy is done and a summary of the operation
is presented.

    >>> jblack_browser.getControl("Copy Packages").click()

    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    DEBUG Created i386 build of pmount 0.1-1 in ubuntu hoary RELEASE [...]
    in PPA for James Blackwell (...)
    DEBUG Packages copied to PPA for James Blackwell:
    DEBUG pmount 0.1-1 in hoary

James uses the link in the copy summary to go straight to the target
PPA, his own. There he can see the just copied package as PENDING and
also marked as pending build for i386. Note, he is also informed that
there is actually a newer version already available in hoary.

    >>> jblack_browser.getLink("PPA for James Blackwell").click()
    >>> print(jblack_browser.title)
    Packages in “PPA for James Blackwell”...

    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    pmount - 0.1-1 (Newer...)   Pending    Hoary            Editors  i386

Expanding the details area, James can see that the source copied is
indeed the same by checking the changelog, also that the binaries
were not copied and instead a build was already created in his PPA
context.

    >>> pmount_pub_id = getPPAPubIDsFor("jblack", "pmount")[0]
    >>> expander_url = jblack_browser.getLink(
    ...     id="pub%s-expander" % pmount_pub_id
    ... ).url
    >>> jblack_extra_browser.open(expander_url)
    >>> print(extract_text(jblack_extra_browser.contents))
    Publishing details
      Copied from PPA for Celso Providelo by James Blackwell
      Originally uploaded to ubuntu hoary in Primary Archive for Ubuntu Linux
    Changelog
      pmount (0.1-1) hoary; urgency=low
      * Fix description (Malone #1)
      * Fix debian (Debian #2000)
      * Fix warty (Warty Ubuntu #1)
      -- Sample Person &lt;test@canonical.com&gt;
      Tue, 7 Feb 2006 12:10:08 +0300
    Builds
      i386
    Package files
      No files published for this package.

The package was copied from the primary archive and not from a PPA.
Hence the archive's title does not link back to the source archive
(as would be the case with a source PPA).

    >>> jblack_browser.getLink("Primary Archive for Ubuntu Linux")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

James quickly goes to the build page and confirms for himself that the
build created during the copy is ready to be dispatched.

    >>> jblack_browser.getLink("i386").click()
    >>> print(jblack_browser.title)
    i386 build of pmount 0.1-1 : PPA for James Blackwell : James Blackwell

    >>> print(extract_text(find_main_content(jblack_browser.contents)))
    i386 build of pmount 0.1-1 in ubuntu hoary RELEASE
    PPA for James Blackwell i386 build of pmount 0.1-1
    created ...
    Build status Needs building
    Cancel build
    Start
    Build score:...
    Build details
    Source: pmount - 0.1-1
    Archive: PPA for James Blackwell
    Series: Hoary
    Architecture: i386
    Pocket: Release
    Component: main

Very nice, but now James gets really excited about the possibilities ...


Copying packages within the PPA
...............................

James thinks that having Celso's 'pmount' copy in his PPA for hoary is
great, however some of his friends are already using grumpy, the new
and shine ubuntu series.

He is aware that the PPA system would not allow him to download pmount
and simply re-upload it to another series, because the it's files are
already in the pool and can't be overridden.

James, thinks for a minute and realises that he could copy the
'pmount' source already in his PPA from hoary to grumpy.

James goes straight to the copy interface of his PPA.

    >>> jblack_browser.getLink("PPA for James Blackwell").click()
    >>> jblack_browser.getLink("View package details").click()
    >>> print(jblack_browser.title)
    Packages in “PPA for James Blackwell”...

    >>> jblack_browser.getLink("Copy packages").click()
    >>> print(jblack_browser.title)
    Copy packages from PPA for James Blackwell...

    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    pmount - 0.1-1 (Newer...)   Pending    Hoary            Editors  i386

Then selects pmount in hoary.

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     pmount_pub_id
    ... ]

Leave the Destination PPA alone, because it defaults to 'This PPA'.

    >>> print(jblack_browser.getControl("Destination PPA").displayValue)
    ['This PPA']

The destination series always default to 'The same series'.

    >>> jblack_browser.getControl("Destination series").displayValue
    ['The same series']

He uses the default option of rebuilding copied source along the way.

    >>> print_radio_button_field(jblack_browser.contents, "include_binaries")
    (*) Rebuild the copied sources
    ( ) Copy existing binaries

All done and reviewed, James pushes the button.

    >>> jblack_browser.getControl("Copy Packages").click()

'pmount' could not be copied, because since it is building in
hoary, if we allow the source to be copied and built in grumpy the
resulted binaries would conflict (same name and version, but different
contents). So, this copy is not allowed.

    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    INFO ... raised CannotCopy: pmount 0.1-1 in hoary
    (same version already building in the destination archive for Hoary)

Now, knowing that pmount can only be copied within the same PPA if the
binaries go together, James executes the copy including the binaries.

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     pmount_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination series").value = ["grumpy"]
    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]
    >>> jblack_browser.getControl("Copy Packages").click()

But this is also not allowed. Since pmount is still building in hoary,
there are no binaries to be copied.

    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    INFO ... raised CannotCopy:
    pmount 0.1-1 in hoary (source has no binaries to be copied)

We will mark the pmount build completed, to emulate the situation
described in bug #236407 when binaries were built but have to
wait until the next publishing cycle to be published in the archive.

    >>> login("foo.bar@canonical.com")
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> test_publisher = SoyuzTestPublisher()
    >>> jblack = person_set.getByName("jblack")
    >>> pmount_build = jblack.archive.getBuildRecords()[0]
    >>> pmount_binary = test_publisher.uploadBinaryForBuild(
    ...     pmount_build, "pmount-bin"
    ... )
    >>> flush_database_updates()
    >>> logout()

In such situations the source-only copy is still denied because build
records would be created for the copied source record and the binaries
generated would certainly conflict with the ones already generated for
the same source version published in hoary in the same archive.
The new builds would stick in failed-to-upload state because the
binaries could not be published in the PPA.

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     pmount_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination series").value = ["grumpy"]
    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "REBUILD_SOURCES"
    ... ]
    >>> jblack_browser.getControl("Copy Packages").click()

    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    INFO ... raised CannotCopy: pmount 0.1-1 in hoary
    (same version has unpublished binaries in the destination
    archive for Hoary, please wait for them to be published before
    copying)

Including binaries doesn't help either, since the copied source itself
has unpublished binaries.

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     pmount_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination series").value = ["grumpy"]
    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]
    >>> jblack_browser.getControl("Copy Packages").click()

    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    INFO ... raised CannotCopy:
    pmount 0.1-1 in hoary (source has no binaries to be copied)

We will build and publish the architecture independent binary for
pmount ('pmount-bin') and publish it in hoary/i386 and hoary/hppa.

    >>> from lp.soyuz.enums import PackagePublishingStatus
    >>> login("foo.bar@canonical.com")
    >>> jblack = person_set.getByName("jblack")
    >>> pmount_build = jblack.archive.getBuildRecords()[0]
    >>> pmount_binaries = test_publisher.publishBinaryInArchive(
    ...     pmount_binary,
    ...     jblack.archive,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )
    >>> flush_database_updates()

    >>> for binary in pmount_binaries:
    ...     print(binary.displayname)
    ...
    pmount-bin 0.1-1 in hoary hppa
    pmount-bin 0.1-1 in hoary i386

The binaries have now been published, so James requests the copy
including binaries.

    >>> logout()
    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     pmount_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination series").value = ["grumpy"]
    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]
    >>> jblack_browser.getControl("Copy Packages").click()

The page not only renders the copy summary, but also shows the
package copied in the available sources.

    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    DEBUG Packages copied to PPA for James Blackwell:
    DEBUG pmount 0.1-1 in grumpy
    DEBUG pmount-bin 0.1-1 in grumpy i386
    >>> jblack_browser.open(jblack_browser.url)

Note that only the i386 binary got copied to grumpy since it lacks
hppa support.

    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    pmount - 0.1-1              Pending    Grumpy           Editors
    pmount - 0.1-1 (Newer...)   Pending    Hoary            Editors

After the binary package go from PENDING->PUBLISHED, the page reflects the
changes:

    >>> login("foo.bar@canonical.com")
    >>> for binary in pmount_binaries:
    ...     binary.setPublished()
    ...
    >>> flush_database_updates()
    >>> logout()
    >>> jblack_browser.reload()
    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    pmount - 0.1-1              Pending    Grumpy           Editors
    pmount - 0.1-1 (Newer...)   Pending    Hoary            Editors

If James performs exactly the same copy procedure again, no more packages
will be copied.

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     pmount_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination series").value = ["grumpy"]
    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]
    >>> jblack_browser.getControl("Copy Packages").click()

    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()

After some time, James realises that pmount in hoary doesn't make much
sense and simply deletes it, so his users won't be bothered by this
broken package.

James uses the 'delete-packages' interface in his PPA to delete the
'pmount' source in hoary.

    >>> jblack_browser.getLink("Cancel").click()
    >>> jblack_browser.getLink("Delete packages").click()
    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     pmount_pub_id
    ... ]
    >>> jblack_browser.getControl(
    ...     "Deletion comment"
    ... ).value = "Deleted packages can be copied."
    >>> jblack_browser.getControl("Request Deletion").click()

James return to his PPA packages page and checks that the package is
really deleted.

    >>> jblack_browser.getLink("Cancel").click()
    >>> jblack_browser.getControl(name="field.status_filter").value = [""]
    >>> jblack_browser.getControl("Filter", index=0).click()
    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    pmount - 0.1-1              Pending    Grumpy           Editors
    pmount - 0.1-1 (Newer...)   Deleted    Hoary            Editors

In the minute after James had deleted the package, he discovered that
'pmount' might work correctly in warty.

No problem, he goes back to the copy-packages interface in his PPA and
still able to copy the deleted source to the warty series.

By default the copy view presents only PUBLISHED or PENDING packages.

    >>> jblack_browser.getLink("Copy packages").click()
    >>> print(jblack_browser.getControl(name="field.status_filter").value)
    ['published']

    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    pmount - 0.1-1              Pending    Grumpy           Editors

Packages in other status can be browsed by adjusting the status
filter dropdown box.

    >>> jblack_browser.getControl(name="field.status_filter").value = [""]
    >>> jblack_browser.getControl("Filter").click()
    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    pmount - 0.1-1              Pending    Grumpy           Editors
    pmount - 0.1-1 (Newer...)   Deleted    Hoary            Editors

James mistakenly requests the copy without including the binaries
resulting from the hoary build, which are still published in grumpy.
The copy is not allowed, because as mentioned above, if built, the
binaries produced by the copy will conflict with the ones already
published in the archive.

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     pmount_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination series").value = ["warty"]
    >>> jblack_browser.getControl("Copy Packages").click()
    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    INFO ... raised CannotCopy: pmount 0.1-1 in hoary
    (same version already has published binaries in the destination
    archive)

Since pmount was built in his archive, the only alternative is to
copy the binaries too. The copied binaries will be checked against
the ones already published in the archive and the copy will only be
allowed if they are the same.

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     pmount_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination series").value = ["warty"]
    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]
    >>> jblack_browser.getControl("Copy Packages").click()

    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    DEBUG Packages copied to PPA for James Blackwell:
    DEBUG pmount 0.1-1 in warty
    DEBUG pmount-bin 0.1-1 in warty hppa
    DEBUG pmount-bin 0.1-1 in warty i386
    >>> jblack_browser.open(jblack_browser.url)

James sees the just-copied 'pmount' source in warty pending publication.

    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    pmount - 0.1-1              Pending    Warty            Editors
    pmount - 0.1-1              Pending    Grumpy           Editors
    pmount - 0.1-1 (Newer...)   Deleted    Hoary            Editors


Copying packages to other PPAs you participate
..............................................

The Copy-UI excitement is endless for James, he informed his friends
and decided to open a team PPA where he and his friends could work
together.

    >>> jblack_browser.open("http://launchpad.test/people")
    >>> jblack_browser.getLink("Register a team").click()

    >>> jblack_browser.getControl(name="field.name").value = "jblack-friends"

    >>> jblack_browser.getControl(
    ...     "Display Name"
    ... ).value = "James Blackwell Friends"

    >>> jblack_browser.getControl("Create").click()

    >>> jblack_browser.getLink("Create a new PPA").click()
    >>> jblack_browser.getControl(
    ...     name="field.displayname"
    ... ).value = "PPA for James Blackwell Friends"
    >>> jblack_browser.getControl(name="field.accepted").value = True
    >>> jblack_browser.getControl(
    ...     name="field.description"
    ... ).value = "Come friends ..."
    >>> jblack_browser.getControl("Activate").click()

    >>> print(jblack_browser.title)
    PPA for James Blackwell Friends : “James Blackwell Friends” team

PPA created, now James want to populate it with the finest packages he
have ever seen. He goes to Celso's PPA copy interface.

    >>> jblack_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> jblack_browser.getLink("Copy packages").click()

James would like to re-distribute Celso's 'pmount' and 'iceweasel'
packages, thus he selects both.

    >>> pmount_pub_id = getPPAPubIDsFor("cprov", "pmount")[0]
    >>> iceweasel_pub_id = getPPAPubIDsFor("cprov", "iceweasel")[0]

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     iceweasel_pub_id,
    ...     pmount_pub_id,
    ... ]

Now that James have access to more than one PPA, the copy-packages form
allows him to select one of them.

    >>> print(jblack_browser.getControl("Destination PPA").displayOptions)
    ['PPA for James Blackwell Friends [~jblack-friends/ubuntu/ppa]',
     'PPA for James Blackwell [~jblack/ubuntu/ppa]']

James wants to populate the PPA for James Blackwell Friends, he
selects that.

    >>> jblack_browser.getControl("Destination PPA").value = [
    ...     "~jblack-friends/ubuntu/ppa"
    ... ]

James decides that 'hoary' is where the action will be for his friends.

    >>> jblack_browser.getControl("Destination series").value = ["hoary"]

Also, in order to make James Friends' PPA ready to use, this time
James will also copy Celso's binaries for the selected sources.

    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]

Button-pushing time for James again.

    >>> jblack_browser.getControl("Copy Packages").click()

The page not only renders the copy summary, but also shows the
package copied in the available sources.

    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 2 packages to PPA for James Blackwell Friends.
    Please allow some time for these to be processed.
    >>> run_copy_jobs()
    DEBUG Packages copied to PPA for James Blackwell Friends:
    DEBUG iceweasel 1.0 in hoary
    DEBUG mozilla-firefox 1.0 in hoary i386
    DEBUG Packages copied to PPA for James Blackwell Friends:
    DEBUG pmount 0.1-1 in hoary
    DEBUG pmount 0.1-1 in hoary hppa
    DEBUG pmount 0.1-1 in hoary i386

So happy-hacking for James Friends, Celso's 'iceweasel' and 'pmount'
sources and binaries are copied to their PPA.

    >>> jblack_browser.getLink("PPA for James Blackwell Friends").click()
    >>> print(jblack_browser.title)
    Packages in “PPA for James Blackwell Friends”...

    >>> print_ppa_packages(jblack_browser.contents)
    Source            Uploader    Published   Status   Series  Section  Build
        Status
    iceweasel...(...) no signer               Pending  Hoary   Editors
    pmount...(...)    no signer               Pending  Hoary   Editors

James just gives a quick look to the details section of each copied
sources to ensure the binaries are really there.

    >>> pmount_pub_id = getPPAPubIDsFor("jblack-friends", "pmount")[0]
    >>> expander_url = jblack_browser.getLink(
    ...     id="pub%s-expander" % pmount_pub_id
    ... ).url
    >>> jblack_extra_browser.open(expander_url)
    >>> print(extract_text(jblack_extra_browser.contents))
    Publishing details
    ...
    Built packages
      pmount
    ...

    >>> iceweasel_pub_id = getPPAPubIDsFor("jblack-friends", "iceweasel")[0]
    >>> expander_url = jblack_browser.getLink(
    ...     id="pub%s-expander" % iceweasel_pub_id
    ... ).url
    >>> jblack_extra_browser.open(expander_url)
    >>> print(extract_text(jblack_extra_browser.contents))
    Publishing details
    ...
    Built packages
      mozilla-firefox
      ff from iceweasel
    ...

Not using his brain again, James tries to copy the two sources to the
same location within James Blackwell Friends' PPAs, pretty much as if
he was trying to break Launchpad. Poor James, this time he gets
completely ignored.

    >>> jblack_browser.getLink("Copy packages").click()

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     pmount_pub_id,
    ...     iceweasel_pub_id,
    ... ]

    >>> jblack_browser.getControl("Destination series").value = ["hoary"]

    >>> jblack_browser.getControl("Copy Packages").click()
    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 2 packages to PPA for James Blackwell Friends.
    Please allow some time for these to be processed.
    >>> run_copy_jobs()
    INFO ... raised CannotCopy: iceweasel 1.0 in hoary
    (same version already has published binaries in the destination archive)
    INFO ... raised CannotCopy: pmount 0.1-1 in hoary
    (same version already has published binaries in the destination archive)

James goes wild and decided to create a new team PPA for his sandbox
tests.

    >>> jblack_browser.open("http://launchpad.test/people")
    >>> jblack_browser.getLink("Register a team").click()

    >>> jblack_browser.getControl(name="field.name").value = "jblack-sandbox"

    >>> jblack_browser.getControl(
    ...     "Display Name"
    ... ).value = "James Blackwell Sandbox"

    >>> jblack_browser.getControl("Create").click()

    >>> jblack_browser.getLink("Create a new PPA").click()
    >>> jblack_browser.getControl(
    ...     name="field.displayname"
    ... ).value = "PPA for James Blackwell Sandbox"
    >>> jblack_browser.getControl(name="field.accepted").value = True
    >>> jblack_browser.getControl(
    ...     name="field.description"
    ... ).value = "Come friends ..."
    >>> jblack_browser.getControl("Activate").click()

    >>> print(jblack_browser.title)
    PPA for James Blackwell Sandbox : “James Blackwell Sandbox” team

James now goes to his PPA and copy all sources to his Sandbox PPA
for a mass rebuild, including the deleted source. James is going
insane because PPA-copy-ui is so cool.

    >>> jblack_browser.open(
    ...     "http://launchpad.test/~jblack/+archive/ppa/+packages"
    ... )
    >>> jblack_browser.getLink("Copy packages").click()
    >>> jblack_browser.getControl(name="field.status_filter").value = [""]
    >>> jblack_browser.getControl("Filter").click()

    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    pmount - 0.1-1              Pending    Warty            Editors
    pmount - 0.1-1              Pending    Grumpy           Editors
    pmount - 0.1-1 (Newer...)   Deleted    Hoary            Editors

    >>> jblack_pub_ids = getPPAPubIDsFor("jblack")

    >>> jblack_browser.getControl(
    ...     name="field.selected_sources"
    ... ).value = jblack_pub_ids

    >>> jblack_browser.getControl("Destination PPA").value = [
    ...     "~jblack-sandbox/ubuntu/ppa"
    ... ]

    >>> jblack_browser.getControl("Destination series").value = [""]

    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "REBUILD_SOURCES"
    ... ]

    >>> jblack_browser.getControl("Copy Packages").click()

The 'mass-rebuild' is not allowed since only one instance of 'pmount -
0.1-1' source can be built in a archive, so the copy candidates are
conflicts and cannot be allowed.

    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 3 packages to PPA for James Blackwell Sandbox.
    Please allow some time for these to be processed.
    >>> run_copy_jobs()
    DEBUG Created i386 build of pmount 0.1-1 in ubuntu warty RELEASE [...]
    in PPA for James Blackwell Sandbox (...)
    DEBUG Packages copied to PPA for James Blackwell Sandbox:
    DEBUG pmount 0.1-1 in warty
    INFO ... raised CannotCopy: pmount 0.1-1 in grumpy
    (same version already building in the destination archive for Warty)
    INFO ... raised CannotCopy: pmount 0.1-1 in hoary
    (same version already building in the destination archive for Warty)

Due to the copy error, nothing was copied to the destination PPA, not
even the 'warty' source, which was not denied.

    >>> jblack_browser.open("http://launchpad.test/~jblack-sandbox/+archive")
    >>> print(jblack_browser.title)
    PPA for James Blackwell Sandbox : “James Blackwell Sandbox” team

    >>> print_ppa_packages(jblack_browser.contents)

Not yet happy, James goes back to his PPA to check if the copy-packages
interface can be used to resurrect deleted packages.

    >>> jblack_browser.open(
    ...     "http://launchpad.test/~jblack/+archive/ppa/+packages"
    ... )
    >>> jblack_browser.getLink("Copy packages").click()
    >>> jblack_browser.getControl(name="field.status_filter").value = [""]
    >>> jblack_browser.getControl("Filter").click()

    >>> deleted_pub_id = getPPAPubIDsFor(
    ...     "jblack", status=PackagePublishingStatus.DELETED
    ... )[0]

James select the deleted pmount_1.0-1 publication in Hoary and target
it to 'This PPA', 'The same series'.

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     deleted_pub_id
    ... ]

    >>> print(jblack_browser.getControl("Destination PPA").displayValue)
    ['This PPA']

    >>> print(jblack_browser.getControl("Destination series").displayValue)
    ['The same series']

    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]

When he submits the form, he can a pending publication of his selected
source in the wanted destination. So, done, in the next cycle the
deleted files will be re-published in his archive.

    >>> jblack_browser.getControl("Copy Packages").click()
    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    DEBUG Packages copied to PPA for James Blackwell:
    DEBUG pmount 0.1-1 in hoary
    DEBUG pmount-bin 0.1-1 in hoary hppa
    DEBUG pmount-bin 0.1-1 in hoary i386
    >>> jblack_browser.open(jblack_browser.url)

    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    pmount - 0.1-1 (Newer...)   Pending    Hoary            Editors
    pmount - 0.1-1              Pending    Warty            Editors
    pmount - 0.1-1              Pending    Grumpy           Editors
    pmount - 0.1-1 (Newer...)   Deleted    Hoary            Editors

James is not yet satisfied and to create some fun we will publish
different version of foo_1.0 in Mark's and Celso's PPAs and a foo_2.0
in No Privileges' PPA.

    >>> login("foo.bar@canonical.com")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> hoary = ubuntu.getSeries("hoary")

    >>> name16 = person_set.getByName("name16")
    >>> test_publisher.person = name16

    >>> mark = person_set.getByName("mark")
    >>> mark_foo_src = test_publisher.getPubSource(
    ...     version="1.1",
    ...     distroseries=hoary,
    ...     archive=mark.archive,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )
    >>> unused = test_publisher.getPubBinaries(
    ...     distroseries=hoary,
    ...     pub_source=mark_foo_src,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )

    >>> cprov = person_set.getByName("cprov")
    >>> cprov_foo_src = test_publisher.getPubSource(
    ...     version="1.1",
    ...     distroseries=hoary,
    ...     archive=cprov.archive,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )
    >>> unused = test_publisher.getPubBinaries(
    ...     distroseries=hoary,
    ...     pub_source=cprov_foo_src,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )

    >>> no_priv = person_set.getByName("no-priv")
    >>> nopriv_foo_src = test_publisher.getPubSource(
    ...     version="2.0",
    ...     distroseries=hoary,
    ...     archive=no_priv.archive,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )
    >>> unused = test_publisher.getPubBinaries(
    ...     distroseries=hoary,
    ...     pub_source=nopriv_foo_src,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )

    >>> jblack_friends = person_set.getByName("jblack-friends")
    >>> jblack_friends_foo_src = test_publisher.getPubSource(
    ...     version="9.9",
    ...     distroseries=hoary,
    ...     archive=jblack_friends.archive,
    ...     status=PackagePublishingStatus.PUBLISHED,
    ... )
    >>> [build] = jblack_friends_foo_src.createMissingBuilds()
    >>> from lp.buildmaster.enums import BuildStatus
    >>> build.updateStatus(BuildStatus.FAILEDTOBUILD)

    >>> flush_database_updates()
    >>> logout()

Good, now James goes straight to No Privileges' PPA and copies the
foo_2.0 version to his PPA.

    >>> jblack_browser.open(
    ...     "http://launchpad.test/~no-priv/+archive/ppa/+packages"
    ... )
    >>> jblack_browser.getLink("Copy packages").click()

    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    foo - 2.0 (changes file) ... Published  Hoary            Base

    >>> foo_pub_id = getPPAPubIDsFor("no-priv", "foo")[0]
    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     foo_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination PPA").value = [
    ...     "~jblack/ubuntu/ppa"
    ... ]
    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]
    >>> jblack_browser.getControl("Copy Packages").click()
    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    DEBUG Packages copied to PPA for James Blackwell:
    DEBUG foo 2.0 in hoary
    DEBUG foo-bin 2.0 in hoary hppa
    DEBUG foo-bin 2.0 in hoary i386

James tries to copy some of Celso's packages that are older than
the ones in his own PPA. He is not allowed to copy these older
packages since they would not be published in the destination anyway.

    >>> jblack_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+packages"
    ... )
    >>> jblack_browser.getLink("Copy packages").click()

    >>> print_ppa_packages(jblack_browser.contents)
    Source            Published   Status     Series           Section  Build
        Status
    cdrkit - 1.0      2007-07-09  Published  Breezy-autotest  Editors  i386
    foo - 1.1   (...) ...         Published  Hoary            Base
    iceweasel...(...) 2007-07-09  Published  Warty            Editors  i386
    pmount - 0.1-1    2007-07-09  Published  Warty            Editors

    >>> foo_pub_id = getPPAPubIDsFor("cprov", "foo")[0]
    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     foo_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination PPA").value = [
    ...     "~jblack/ubuntu/ppa"
    ... ]
    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]
    >>> jblack_browser.getControl("Copy Packages").click()
    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    INFO ... raised CannotCopy: foo 1.1 in hoary
    (version older than the foo 2.0 in hoary published in hoary)

However if he copies it to another suite is just works (tm) since PPAs
do not enforce coherent version ordering across suites.

    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     foo_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination PPA").value = [
    ...     "~jblack/ubuntu/ppa"
    ... ]
    >>> jblack_browser.getControl("Destination series").value = ["warty"]
    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]
    >>> jblack_browser.getControl("Copy Packages").click()
    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    DEBUG Packages copied to PPA for James Blackwell:
    DEBUG foo 1.1 in warty
    DEBUG foo-bin 1.1 in warty hppa
    DEBUG foo-bin 1.1 in warty i386

    >>> jblack_browser.open(
    ...     "http://launchpad.test/~jblack/+archive/ppa/+packages"
    ... )
    >>> print_ppa_packages(jblack_browser.contents)
    Source          Published   Status     Series           Section  Build
        Status
    foo - 2.0  (changes file)    Pending    Hoary            Base     i386
    foo - 1.1  (changes file)    Pending    Warty            Base
    pmount - 0.1-1 (Newer...)   Pending    Hoary            Editors
    pmount - 0.1-1              Pending    Warty            Editors
    pmount - 0.1-1              Pending    Grumpy           Editors

James have heard that Mark's foo version is really rock'n roll and
since he discovered that PPA allows copying old versions, he decides
to copy the *same* version with different contents to grumpy in his PPA.

    >>> jblack_browser.open(
    ...     "http://launchpad.test/~mark/+archive/ppa/+packages"
    ... )
    >>> jblack_browser.getLink("Copy packages").click()

    >>> print_ppa_packages(jblack_browser.contents)
    Source            Published   Status     Series           Section  Build
        Status
    foo - 1.1 (changes file) ...   Published  Hoary            Base
    iceweasel...(...) 2007-07-09  Published  Breezy-autotest  Editors

    >>> foo_pub_id = getPPAPubIDsFor("mark", "foo")[0]
    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     foo_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination PPA").value = [
    ...     "~jblack/ubuntu/ppa"
    ... ]
    >>> jblack_browser.getControl("Destination series").value = ["grumpy"]
    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]
    >>> jblack_browser.getControl("Copy Packages").click()
    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    INFO ... raised CannotCopy: foo 1.1 in hoary
    (a different source with the same version is published in the
    destination archive)

James thinks that his last chance will be copying the just-uploaded
foo-9.9 source from 'James-Friend's PPA.

    >>> jblack_browser.open(
    ...     "http://launchpad.test/~jblack-friends/+archive/ppa/+packages"
    ... )
    >>> jblack_browser.getLink("Copy packages").click()

    >>> jblack_browser.getControl(name="field.name_filter").value = "foo"
    >>> jblack_browser.getControl("Filter").click()

    >>> print_ppa_packages(jblack_browser.contents)
    Source          Uploader Published Status    Series Section Build Status
    foo - 9.9 (...) name16   ...       Published Hoary  Base    i386

But James doesn't think straight, he sees that foo-9.9 failed to build
in i386, but even though, he tries to copy it including binaries. He
is told that the sources cannot be copied.

    >>> foo_pub_id = getPPAPubIDsFor("jblack-friends", "foo")[0]
    >>> jblack_browser.getControl(name="field.selected_sources").value = [
    ...     foo_pub_id
    ... ]
    >>> jblack_browser.getControl("Destination PPA").value = [
    ...     "~jblack/ubuntu/ppa"
    ... ]
    >>> jblack_browser.getControl("Destination series").value = ["grumpy"]
    >>> jblack_browser.getControl(name="field.include_binaries").value = [
    ...     "COPY_BINARIES"
    ... ]
    >>> jblack_browser.getControl("Copy Packages").click()
    >>> print_feedback_messages(jblack_browser.contents)
    Requested sync of 1 package to PPA for James Blackwell.
    Please allow some time for this to be processed.
    >>> run_copy_jobs()
    INFO ... raised CannotCopy:
    foo 9.9 in hoary (source has no binaries to be copied)

No game, no matter what he tries, James can't break PPAs.

That's all folks, someone has to stop James' craziness.
