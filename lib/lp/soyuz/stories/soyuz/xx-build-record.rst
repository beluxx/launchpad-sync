Build pages
===========

We start by creating a brand new build record and adjusting the
sampledata builder.

    >>> login("foo.bar@canonical.com")

    >>> from datetime import datetime, timedelta, timezone
    >>> from zope.component import getUtility
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.buildmaster.interfaces.builder import IBuilderSet
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher

    # Create a new build record.
    >>> stp = SoyuzTestPublisher()
    >>> stp.prepareBreezyAutotest()
    >>> source = stp.getPubSource(sourcename="testing", version="1.0")
    >>> [build] = source.createMissingBuilds()
    >>> build_id = build.id

    # Enable the sampledata builder.
    >>> bob_builder = getUtility(IBuilderSet)["bob"]
    >>> bob_builder.builderok = True

    # Set a known duration for the current job.
    >>> from lp.soyuz.interfaces.binarypackagebuild import (
    ...     IBinaryPackageBuildSet,
    ... )
    >>> build2 = getUtility(IBinaryPackageBuildSet).getByQueueEntry(
    ...     bob_builder.currentjob
    ... )
    >>> in_progress_build = removeSecurityProxy(build2)
    >>> one_minute = timedelta(seconds=60)
    >>> in_progress_build.buildqueue_record.estimated_duration = one_minute

    >>> logout()

A `Build` record represents an attempt to build a specific source
package in a `DistroArchSeries`. There is an individual page for each
individual `Build`, and they can be accessed via the build-farm URL
shortcut.

    >>> build_url = "http://launchpad.test/builders/+build/%d" % build_id

Using the short-cut URL any user can promptly access the build
page. It's title briefly describes the build.

    >>> anon_browser.open(build_url)

    >>> from lp.services.helpers import backslashreplace
    >>> print(backslashreplace(anon_browser.title))
    i386 build : 1.0 : testing package : ubuntutest

In the page body readers can see 2 sections, 'Build status' and 'Build
details'.

Since builds respect a fixed workflow (pending -> building ->
built|failed), readers are mostly interested in their
status. That's why this section comes first.

Besides 'status' readers can see, at a glance, the context and links
to the build context, source package, archive, series, pocket and
component.

    >>> print(extract_text(find_main_content(anon_browser.contents)))
    i386 build of testing 1.0 in ubuntutest breezy-autotest RELEASE
    ...
    Build status
    Needs building
    Start in ...
    Build score:2505 (What's this?)
    Build details
    Source: testing - 1.0
    Archive: Primary Archive for Ubuntu Test
    Series: Breezy Badger Autotest
    Architecture: i386
    Pocket: Release
    Component: main

Let's disable the job associated with the build. This has the side effect
that a dispatch time estimation will not be available for the build in
question.

    >>> login("foo.bar@canonical.com")
    >>> build.buildqueue_record.suspend()
    >>> logout()
    >>> anon_browser.open(build_url)
    >>> print(extract_text(find_main_content(anon_browser.contents)))
    i386 build of testing 1.0 in ubuntutest breezy-autotest RELEASE
    ...
    Build status
    Needs building
    Build score:2505 (What's this?)
    Build details
    Source: testing - 1.0
    Archive: Primary Archive for Ubuntu Test
    Series: Breezy Badger Autotest
    Architecture: i386
    Pocket: Release
    Component: main

Re-enable the build in order to avoid subsequent test breakage.

    >>> login("foo.bar@canonical.com")
    >>> build.buildqueue_record.resume()
    >>> logout()
    >>> anon_browser.open(build_url)

The 'Build details' section exists for all status and contains links
to all the relevant entities involved in this build.

    >>> print(anon_browser.getLink("testing - 1.0").url)
    http://launchpad.test/ubuntutest/+source/testing/1.0

    >>> print(anon_browser.getLink("Primary Archive for Ubuntu Test").url)
    http://launchpad.test/ubuntutest

    >>> print(anon_browser.getLink("Breezy Badger Autotest").url)
    http://launchpad.test/ubuntutest/breezy-autotest

    >>> print(anon_browser.getLink("i386").url)
    http://launchpad.test/ubuntutest/breezy-autotest/i386

Pending build records can be 'rescored', which will directly affect
the time they will get started. A link to the corresponding help text
about 'Build scores' is available.

    >>> print(anon_browser.getLink("What's this").url)
    https://help.launchpad.net/Packaging/BuildScores

Administrators can rescore pending builds in a separate form.

    >>> admin_browser.open(build_url)
    >>> admin_browser.getLink("Rescore build").click()
    >>> admin_browser.getControl("Priority").value = "0"
    >>> admin_browser.getControl("Rescore").click()

Once submitted they are redirected to the build index page where the
new 'score' value is presented.

    >>> print_feedback_messages(admin_browser.contents)
    Build rescored to 0.

    >>> print(extract_text(find_tag_by_id(admin_browser.contents, "status")))
    Build status
    Needs building
    Cancel build
    Start in ...
    Build score:0 Rescore build (What's this?)

Eventually a pending build record will get started, and while it's
building the page will also contain a link to the builder where the
source is being built and the last few lines of the build log
messages.

    # Reset the sampledata in-progress job and start the testing
    # build with an known buildlog 'tail'.
    >>> login("foo.bar@canonical.com")
    >>> from lp.buildmaster.enums import BuildStatus
    >>> in_progress_build.buildqueue_record.reset()
    >>> now = datetime.now(timezone.utc)
    >>> build.updateStatus(
    ...     BuildStatus.BUILDING,
    ...     builder=bob_builder,
    ...     date_started=(now - timedelta(minutes=1)),
    ... )
    >>> build.buildqueue_record.markAsBuilding(bob_builder)
    >>> build.buildqueue_record.logtail = "one line\nanother line"
    >>> logout()

    >>> anon_browser.reload()

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "status")))
    Build status
    Currently building on Bob The Builder
    Build score:0 (What's this?)
    Started ... ago

    >>> print(anon_browser.getLink("Bob The Builder").url)
    http://launchpad.test/builders/bob

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "buildlog")))
    Buildlog
    one line
    another line

When accessed by logged in users, the build page renders the
'buildlog' section with a timestamp at the bottom on the user
timezone. This way they can easily find out if they are reading
outdated information.

    >>> user_browser.open(anon_browser.url)
    >>> print(extract_text(find_tag_by_id(user_browser.contents, "buildlog")))
    Buildlog
    one line
    another line
    Updated on ...

If the build procedure fails, the 'Build Status' section is augmented
with links to the full 'buildlog' and optionally the failed
'uploadlog' additionally to the instant when the process finished and
how long it took.

    # Mark the testing build as failed.
    >>> login("foo.bar@canonical.com")
    >>> build.updateStatus(
    ...     BuildStatus.FAILEDTOUPLOAD, builder=bob_builder, date_finished=now
    ... )
    >>> build.buildqueue_record.destroySelf()
    >>> build.setLog(stp.addMockFile("fake-buildlog"))
    >>> build.storeUploadLog("content")
    >>> logout()

    >>> anon_browser.reload()

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "status")))
    Build status
    Failed to upload on Bob The Builder
    Started ... ago
    Finished ... (took 1 minute, 0.0 seconds)
    buildlog (7 bytes)
    uploadlog (7 bytes)

    >>> print(anon_browser.getLink("Bob The Builder").url)
    http://launchpad.test/builders/bob

    >>> login(ANONYMOUS)
    >>> anon_browser.getLink("buildlog").url == build.log_url
    True
    >>> anon_browser.getLink("uploadlog").url == build.upload_log_url
    True
    >>> logout()

Note that the links to the logs points to their `ProxiedLibrarianFile`
entry points, so users with permission can reach the files even if
they are private.

Administrators can retry failed builds using the 'retry' icon in the
'Build Status' section.

    >>> admin_browser.open(admin_browser.url)
    >>> print(extract_text(find_tag_by_id(admin_browser.contents, "status")))
    Build status
    Failed to upload on Bob The Builder Retry this build
    Started ... ago
    Finished ... (took 1 minute, 0.0 seconds)
    buildlog (7 bytes)
    uploadlog (7 bytes)

    >>> print(admin_browser.getLink("Retry this build").url)
    http://launchpad.test/ubuntutest/+source/testing/1.0/+build/.../+retry

By clicking on the 'Retry this build' link, administrators are informed of
the consequences of this action.

    >>> admin_browser.getLink("Retry this build").click()
    >>> print(extract_text(find_main_content(admin_browser.contents)))
    Retry i386 build of testing 1.0 in ubuntutest breezy-autotest RELEASE
    ...
    The status of i386 build of testing 1.0 in ubuntutest
    breezy-autotest RELEASE is Failed to upload.
    Retrying this build will destroy its history and logs.
    By default, this build will be retried only after other pending
    builds; please contact a build daemon administrator if you need
    special treatment.
    Are you sure ? or Cancel

If cancelled, the form sends the user back to the build page, nothing
is changed.

    >>> admin_browser.getLink("Cancel").click()
    >>> print(extract_text(find_tag_by_id(admin_browser.contents, "status")))
    Build status
    Failed to upload on Bob The Builder Retry this build
    Started ... ago
    Finished ... (took 1 minute, 0.0 seconds)
    buildlog (7 bytes)
    uploadlog (7 bytes)

The user is also sent back to the build page if the 'Retry' is
performed, but then the failed build will be pending again and
retrying the build is not a possibility anymore.

    >>> admin_browser.getLink("Retry this build").click()
    >>> admin_browser.getControl("Retry Build").click()
    >>> print_feedback_messages(admin_browser.contents)
    Build has been queued

    >>> print(extract_text(find_tag_by_id(admin_browser.contents, "status")))
    Build status
    Needs building
    Cancel build
    Start in ...
    Build score:... Rescore build (What's this?)

    >>> admin_browser.getLink("Retry this build").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

In the case of successfully built build records, additionally to the
appropriate 'Build status' section the user will see 2 new sections,
'Binary packages' and 'Built files'.

    # Mark the testing build as FULLYBUILT and upload a corresponding
    # binary package for it which will be awaiting for acceptance.
    >>> login("foo.bar@canonical.com")
    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> build.buildqueue_record.destroySelf()
    >>> build.updateStatus(BuildStatus.FULLYBUILT, builder=bob_builder)
    >>> build.setLog(stp.addMockFile("fake-buildlog"))
    >>> binaries = stp.uploadBinaryForBuild(build, "testing-bin")
    >>> upload = stp.distroseries.createQueueEntry(
    ...     PackagePublishingPocket.RELEASE,
    ...     stp.distroseries.main_archive,
    ...     "testing_1.0_all.changes",
    ...     b"nothing-special",
    ... )
    >>> unused = upload.addBuild(build)
    >>> logout()

    >>> anon_browser.reload()

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "status")))
    Build status
    Successfully built on Bob The Builder
    Started on 2008-01-01
    Finished on 2008-01-01 (took 5 minutes, 0.0 seconds)
    buildlog (7 bytes)
    testing_1.0_all.changes (15 bytes)

    >>> print(anon_browser.getLink("testing_1.0_all.changes").url)
    http://.../+build/.../+files/testing_1.0_all.changes

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "binaries")))
    Binary packages
    Binary packages awaiting approval in NEW queue:
    testing-bin-1.0

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "files")))
    Built files
    Files resulting from this build:
    testing-bin_1.0_all.deb (8 bytes)

Since the binary is still 'awaiting approval', it is not
linkified. That's because its `DistroArchSeriesBinaryPackageRelease`
page does not exist yet.

    >>> print(anon_browser.getLink("testing-bin-1.0"))
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

On the other hand, users interested in testing the resulting binaries
already have access to them.

    >>> print(anon_browser.getLink("testing-bin_1.0_all.deb").url)
    http://.../+build/.../+files/testing-bin_1.0_all.deb

Again, note that the files are `ProxiedLibrarianFile` objects as well.

Binary upload can also be awaiting approval in UNAPPROVED queue

    # Accept the binary upload for the testing build.
    >>> login("foo.bar@canonical.com")
    >>> upload.setUnapproved()
    >>> logout()

    >>> anon_browser.open(anon_browser.url)

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "binaries")))
    Binary packages
    Binary packages awaiting approval in UNAPPROVED queue:
    testing-bin-1.0

    >>> print(anon_browser.getLink("testing-bin-1.0"))
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> print(anon_browser.getLink("testing-bin_1.0_all.deb").url)
    http://.../+build/.../+files/testing-bin_1.0_all.deb

When new binaries are accepted by an archive administrator (See
xx-queue-pages.rst) this condition is presented in the build page.

    # Accept the binary upload for the testing build.
    >>> login("foo.bar@canonical.com")
    >>> upload.setAccepted()
    >>> logout()

    >>> anon_browser.open(anon_browser.url)

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "binaries")))
    Binary packages
    Binary packages awaiting publication:
    testing-bin-1.0

    >>> print(anon_browser.getLink("testing-bin-1.0"))
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> print(anon_browser.getLink("testing-bin_1.0_all.deb").url)
    http://.../+build/.../+files/testing-bin_1.0_all.deb

Once the accepted binary upload is processed by the backend, the
binary reference finally becomes a link to its corresponding page.

    # Publish the binary upload for the testing build.
    >>> login("foo.bar@canonical.com")
    >>> unused = upload.realiseUpload()
    >>> logout()

    >>> anon_browser.open(anon_browser.url)

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "binaries")))
    Binary packages
    Binary packages produced by this build:
    testing-bin 1.0

    >>> print(anon_browser.getLink("testing-bin 1.0").url)
    http://launchpad.test/ubuntutest/breezy-autotest/i386/testing-bin/1.0


PPA builds
==========

Build records for PPAs contain all the features and aspects described
above. The only difference is that source and binary package
references are not linkified, since PPAs do not allow users to
navigate to packages.

    # Create a PPA build.
    >>> login("foo.bar@canonical.com")
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> ppa_source = stp.getPubSource(
    ...     sourcename="ppa-test", version="1.0", archive=cprov.archive
    ... )
    >>> ppa_binaries = stp.getPubBinaries(
    ...     binaryname="ppa-test-bin",
    ...     archive=cprov.archive,
    ...     pub_source=ppa_source,
    ... )
    >>> [ppa_build] = ppa_source.getBuilds()
    >>> ppa_build.updateStatus(BuildStatus.FULLYBUILT, builder=bob_builder)
    >>> ppa_build_url = (
    ...     "http://launchpad.test/builders/+build/%d" % ppa_build.id
    ... )
    >>> logout()

    >>> anon_browser.open(ppa_build_url)

    >>> print(anon_browser.title)
    i386 build of ppa-test 1.0 : PPA for Celso Providelo : Celso Providelo

The 'Build status' section is identical for PPAs.

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "status")))
    Build status
    Successfully built on Bob The Builder
    Build score:...
    Started on ...
    Finished on ... (took 5 minutes, 0.0 seconds)
    buildlog (6 bytes)
    ppa-test-bin_1.0_i386.changes (23 bytes)

    >>> print(anon_browser.getLink("Bob The Builder").url)
    http://launchpad.test/builders/bob

    >>> print(anon_browser.getLink("buildlog").url)  # noqa
    http://launchpad.test/~cprov/+archive/ubuntu/ppa/+build/.../+files/buildlog_...

    >>> print(anon_browser.getLink("ppa-test-bin_1.0_i386.changes").url)
    http://.../+build/.../+files/ppa-test-bin_1.0_i386.changes

'Build details', as mentioned above, doesn't link to the PPA source
packages, since they do not exist.

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "details")))
    Build details
    Source: ppa-test - 1.0
    Archive: PPA for Celso Providelo
    Series: Breezy Badger Autotest
    Architecture: i386
    Pocket: Release
    Component: main

    >>> print(anon_browser.getLink("ppa-test - 1.0").url)
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> print(anon_browser.getLink("PPA for Celso Providelo").url)
    http://launchpad.test/~cprov/+archive/ubuntu/ppa

    >>> print(anon_browser.getLink("Breezy Badger Autotest").url)
    http://launchpad.test/ubuntutest/breezy-autotest

    >>> print(anon_browser.getLink("i386", index=1).url)
    http://launchpad.test/ubuntutest/breezy-autotest/i386

Similarly, binary packages are not linkified in 'Binary packages'
section for PPA builds.

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "binaries")))
    Binary packages
    Binary packages produced by this build:
    ppa-test-bin-1.0

    >>> print(anon_browser.getLink("ppa-test-bin-1.0").url)
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

If the source package was created from a recipe build, link to it.

    >>> login("foo.bar@canonical.com")
    >>> product = factory.makeProduct(name="product")
    >>> branch = factory.makeProductBranch(
    ...     owner=cprov, product=product, name="mybranch"
    ... )
    >>> recipe = factory.makeSourcePackageRecipe(
    ...     owner=cprov, name="myrecipe", branches=[branch]
    ... )
    >>> distroseries = factory.makeDistroSeries(
    ...     distribution=cprov.archive.distribution, name="shiny"
    ... )
    >>> removeSecurityProxy(
    ...     distroseries
    ... ).nominatedarchindep = factory.makeDistroArchSeries(
    ...     distroseries=distroseries
    ... )
    >>> ppa_source.sourcepackagerelease.source_package_recipe_build = (
    ...     factory.makeSourcePackageRecipeBuild(
    ...         recipe=recipe,
    ...         archive=cprov.archive,
    ...         distroseries=distroseries,
    ...     )
    ... )
    >>> logout()
    >>> anon_browser.open(ppa_build_url)
    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "details")))
    Build details
    ...
    Source package recipe build:
    ~cprov/product/mybranch recipe build in ubuntu shiny [~cprov/ubuntu/ppa]
    ...

    >>> print(
    ...     anon_browser.getLink("~cprov/product/mybranch recipe build").url
    ... )
    http://launchpad.test/~cprov/+archive/ubuntu/ppa/+recipebuild/...

Finally, the 'Build files' section is identical for PPA builds.

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "files")))
    Built files
    Files resulting from this build:
    ppa-test-bin_1.0_all.deb (18 bytes)

    >>> print(anon_browser.getLink("ppa-test-bin_1.0_all.deb").url)
    http://.../+build/.../+files/ppa-test-bin_1.0_all.deb


Imported binaries builds
========================

Build for imported binaries despite of having no `PackageUpload`
record always link to its binaries.

    # Create a build for an imported binary.
    >>> login("foo.bar@canonical.com")
    >>> imported_source = stp.getPubSource(sourcename="imported")
    >>> [imported_build] = imported_source.createMissingBuilds()
    >>> unused_binaries = stp.uploadBinaryForBuild(
    ...     imported_build, "imported-bin"
    ... )

    >>> print(imported_build.package_upload)
    None

    >>> imported_build_url = (
    ...     "http://launchpad.test/builders/+build/%d" % imported_build.id
    ... )

    >>> logout()

    >>> anon_browser.open(imported_build_url)

    >>> print(backslashreplace(anon_browser.title))
    i386 build : 666 : imported package : ubuntutest

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "binaries")))
    Binary packages
    Binary packages produced by this build:
    imported-bin 666

    >>> print(anon_browser.getLink("imported-bin 666").url)
    http://launchpad.test/ubuntutest/breezy-autotest/i386/imported-bin/666
