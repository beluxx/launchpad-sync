Gina Test
---------

This file is a simple test for gina. It uses a test archive (kept in
lp.soyuz.scripts.tests.archive_for_gina) and runs gina in
quiet mode over it.

Get the current counts of stuff in the database:

    >>> from lp.services.database.interfaces import IStore
    >>> from lp.services.identity.model.emailaddress import EmailAddress
    >>> from lp.soyuz.interfaces.publishing import active_publishing_status
    >>> from lp.soyuz.model.publishing import (
    ...     BinaryPackagePublishingHistory,
    ...     SourcePackagePublishingHistory,
    ... )
    >>> from lp.registry.model.person import Person
    >>> from lp.registry.model.teammembership import TeamParticipation
    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
    >>> from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
    >>> from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
    >>> SSPPH = SourcePackagePublishingHistory
    >>> SBPPH = BinaryPackagePublishingHistory

    >>> orig_spr_count = SourcePackageRelease.select().count()
    >>> orig_sspph_count = SSPPH.select().count()
    >>> orig_person_count = Person.select().count()
    >>> orig_tp_count = TeamParticipation.select().count()
    >>> orig_email_count = EmailAddress.select().count()
    >>> orig_bpr_count = BinaryPackageRelease.select().count()
    >>> orig_build_count = BinaryPackageBuild.select().count()
    >>> orig_sbpph_count = SBPPH.select().count()
    >>> orig_sspph_main_count = SSPPH.selectBy(
    ...     component_id=1, pocket=PackagePublishingPocket.RELEASE
    ... ).count()

Create a distribution release and an arch release for breezy:

    >>> from lp.buildmaster.interfaces.processor import IProcessorSet
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> celebs = getUtility(ILaunchpadCelebrities)
    >>> ubuntu = celebs.ubuntu
    >>> hoary = ubuntu.getSeries("hoary")

    # Only the distro owner and admins can create a new series.
    >>> ignored = login_person(ubuntu.owner.activemembers[0])
    >>> breezy = ubuntu.newSeries(
    ...     "breezy",
    ...     "Breezy Badger",
    ...     "My title",
    ...     "My summary",
    ...     "My description",
    ...     "5.10",
    ...     hoary,
    ...     celebs.launchpad_developers,
    ... )
    >>> login(ANONYMOUS)

    >>> breezy_i386 = breezy.newArch(
    ...     processor=getUtility(IProcessorSet).getByName("386"),
    ...     architecturetag="i386",
    ...     official=True,
    ...     owner=celebs.launchpad_developers,
    ... )
    >>> import transaction
    >>> transaction.commit()

Now, lets run gina on hoary and breezy. This test imports a few
packages successfully (at least partially):

   * archive-copier, a source package which generates one udeb
     in debian-installer. Its maintainer has a name which contains a ","
   * archive-copier, again, with a different version number to see that
     both versions get correctly imported.
   * db1-compat, source package what generates 1 binary package. The same
     version was included in both hoary and breezy, but its source
     package's section and its binary package's priority were changed in
     breezy.
   * gcc-defaults, a source package that generates 8 binary packages with
     differing versions.
   * x11proto-damage, a package which is only present in breezy
   * libcap, a source package which generates 3 binary packages, and
     whose version number contains an epoch. It is not in the Breezy
     Sources list, but some binaries are in the Packages file. However, these
     binaries are unchaged in Breezy.
   * ubuntu-meta, a source package that generates 3 binary packages in
     Hoary and 5 in breezy. However, its breezy version is /not/ listed in the
     Sources list, so the binary packages will need to discover it.
   * ed, a source package what generates one binary package and
     misses a section entry in Sources. The same version exists in
     breezy, this time with a defined section. Its hoary binary package
     lacks a Priority.
   * python-sqllite, an arch-independent source package that generates
     one binary package. Its breezy packages are missing from the archive.
   * python-pam, an arch-independent source package that generates one
     binary package, whose changelog contains a busted urgency. Its hoary
     binary package contains lacks a Section. Its breezy packages are missing
     from the archive.
   * mkvmlinuz, a source package that generates one binary package,
     but which is missing a version field in its Sources file.
     Its breezy package has a version but is missing copyright and changelog.
   * 3dchess, a source package that generates a binary package.
   * 9wm, a source package that generates a binary package, and whose
     changelog file name starts with the binary package name.
   * rioutil, a source package that generates a binary package, and
     whose source contains a shlibs file. Its current binary package is
     actually an evil bin-only-NMU!

And two completely broken packages:

   * util-linux, a source package that is missing from the pool. It
     generates 4 binary packages, all missing. It's correctly listed in
     Sources and Packages, though.

   * clearlooks, a source package with no binaries listed, and which has
     a DSC file that refers to an inexistant tar.gz.

Let's set up the filesystem:

    >>> import subprocess, os
    >>> try:
    ...     os.unlink("/var/lock/launchpad-gina.lock")
    ... except OSError:
    ...     pass
    ...
    >>> try:
    ...     os.remove("/tmp/gina_test_archive")
    ... except OSError:
    ...     pass
    ...
    >>> relative_path = "lib/lp/soyuz/scripts/tests/gina_test_archive"
    >>> path = os.path.join(os.getcwd(), relative_path)
    >>> os.symlink(path, "/tmp/gina_test_archive")

And give it a spin:

    >>> gina_proc = ["scripts/gina.py", "-q", "hoary", "breezy"]
    >>> proc = subprocess.Popen(
    ...     gina_proc, stderr=subprocess.PIPE, universal_newlines=True
    ... )

Check STDERR for the errors we expected:

    >>> print(proc.stderr.read())
    ERROR   Error processing package files for clearlooks
    ...
    ...ExecutionError: Error 2 unpacking source
    WARNING Invalid format in db1-compat, assumed '1.0'
    WARNING Source package ed lacks section, assumed 'misc'
    ERROR   Unable to create SourcePackageData for mkvmlinuz
    ...
    ...InvalidVersionError: mkvmlinuz has an invalid version: None
    WARNING Invalid urgency in python-pam, None, assumed 'low'
    ERROR   Error processing package files for util-linux
    ...
    ...PoolFileNotFound: File util-linux_2.12p-2ubuntu2.2.dsc not in archive
    ERROR   Error processing package files for bsdutils
    ...
    ...PoolFileNotFound: .../bsdutils_2.12p-2ubuntu2_i386.deb not found
    WARNING Binary package ed lacks valid priority, assumed 'extra'
    ERROR   Unable to create BinaryPackageData for mount
    ...
    ...InvalidVersionError: mount has an invalid version: -ewePP2.12p-2ubuntu2
    WARNING Binary package python-pam lacks a section, assumed 'misc'
    ERROR   Error processing package files for python2.4-pam
    ...
    ...PoolFileNotFound: .../python2.4-pam_0.4.2-10.1ubuntu3_i386.deb not
    found
    ERROR   Error processing package files for python2.4-sqlite
    ...
    ...PoolFileNotFound: .../python2.4-sqlite_1.0.1-1ubuntu1_i386.deb not
    found
    WARNING No source package rioutil (1.4.4-1.0.1) listed for rioutil
            (1.4.4-1.0.1), scrubbing archive...
    WARNING Nope, couldn't find it. Could it be a bin-only-NMU? Checking...
    ERROR   Error processing package files for util-linux
    ...
    ...PoolFileNotFound: .../util-linux_2.12p-2ubuntu2_i386.deb not found
    ERROR   Unable to create BinaryPackageData for util-linux-locales
    ...
    ...MissingRequiredArguments: ['installed_size']
    ERROR   Invalid Sources stanza in /tmp/tmp...
    ...
    WARNING No changelog file found for mkvmlinuz in mkvmlinuz-14ubuntu1
    WARNING No copyright file found for mkvmlinuz in mkvmlinuz-14ubuntu1
    WARNING Invalid urgency in mkvmlinuz, None, assumed 'low'
    ERROR   Error processing package files for python-sqlite
    ...
    ...PoolFileNotFound: File python-sqlite_1.0.1-2ubuntu1.dsc not in archive
    ERROR   Error processing package files for util-linux
    ...
    ...PoolFileNotFound: File util-linux_2.12p-6ubuntu5.dsc not in archive
    ERROR   Error processing package files for python-sqlite
    ...
    ...PoolFileNotFound: .../python-sqlite_1.0.1-2ubuntu1_all.deb not found
    WARNING No source package ubuntu-meta (0.80) listed for ubuntu-base
            (0.80), scrubbing archive...
    <BLANKLINE>

The exit status must be 0, for success:

    >>> proc.wait()
    0
    >>> transaction.commit()


Testing Source Package Results
..............................

We should have more source packages in the database:

    >>> existing = 9

Two packages fail.

    >>> hc = 13 - 2

Three packages are the same as in hoary; two fail; one is imported
forcefully (ubuntu-meta).

    >>> bc = 9 - 3 - 2 + 1

    >>> hc + bc
    16
    >>> count = SourcePackageRelease.select().count()
    >>> count - orig_spr_count
    17

Check that x11proto-damage has its Build-Depends-Indep value correctly set:

    >>> from lp.registry.model.sourcepackagename import SourcePackageName
    >>> n = SourcePackageName.selectOneBy(name="x11proto-damage")
    >>> x11p = SourcePackageRelease.selectOneBy(
    ...     sourcepackagenameID=n.id, version="6.8.99.7-2"
    ... )

    >>> print(x11p.builddependsindep)
    debhelper (>= 4.0.0)

Check if the changelog message was stored correcly:

    >>> print(x11p.changelog_entry)
    ... # noqa
    ... # doctest: -NORMALIZE_WHITESPACE
    x11proto-damage (6.8.99.7-2) breezy; urgency=low
    <BLANKLINE>
      * Add dependency on x11proto-fixes-dev.
    <BLANKLINE>
     -- Daniel Stone <daniel.stone@ubuntu.com>  Mon, 11 Jul 2005 19:11:11 +1000

    >>> from lp.registry.interfaces.sourcepackage import SourcePackageUrgency
    >>> x11p.urgency == SourcePackageUrgency.LOW
    True

Check that the changelog was uploaded to the librarian correctly:

    >>> print(six.ensure_text(x11p.changelog.read()))
    ... # noqa
    x11proto-damage (6.8.99.7-2) breezy; urgency=low
    <BLANKLINE>
      * Add dependency on x11proto-fixes-dev.
    <BLANKLINE>
     -- Daniel Stone <daniel.stone@ubuntu.com>  Mon, 11 Jul 2005 19:11:11 +1000
    <BLANKLINE>
    x11proto-damage (6.8.99.7-1) breezy; urgency=low
    <BLANKLINE>
      * First x11proto-damage release.
    <BLANKLINE>
     -- Daniel Stone <daniel.stone@ubuntu.com>  Mon, 16 May 2005 22:10:17 +1000

Same for the copyright:

    >>> print(x11p.copyright)
    $Id: COPYING,v 1.2 2003/11/05 05:39:58 keithp Exp $
    <BLANKLINE>
    Copyright ... 2003 Keith Packard
    ...
    PERFORMANCE OF THIS SOFTWARE.

Check that the dsc on the libcap package is correct, and that we
only imported one:

    >>> n = SourcePackageName.selectOneBy(name="libcap")
    >>> cap = SourcePackageRelease.selectOneBy(sourcepackagenameID=n.id)
    >>> print(cap.dsc)
    -----BEGIN PGP SIGNED MESSAGE-----
    Hash: SHA1
    <BLANKLINE>
    Format: 1.0
    Source: libcap
    Version: 1:1.10-14
    Binary: libcap-dev, libcap-bin, libcap1
    Maintainer: Michael Vogt <mvo@debian.org>
    Architecture: any
    Standards-Version: 3.6.1
    Build-Depends: debhelper
    Files:
     291be97b78789f331499a0ab22d9d563 28495 libcap_1.10.orig.tar.gz
     b867a0c1db9e8ff568415bbcd1fa65dc 12928 libcap_1.10-14.diff.gz
    <BLANKLINE>
    -----BEGIN PGP SIGNATURE-----
    Version: GnuPG v1.2.4 (GNU/Linux)
    <BLANKLINE>
    iD8DBQFAfGV8liSD4VZixzQRAlHoAJ4hD8yDp/VIJUcdQLLr9KH/XQSczQCfQH/D
    FVJMGmGr+2YLZfF+oRUKcug=
    =bw+A
    -----END PGP SIGNATURE-----
    >>> print(cap.maintainer.displayname)
    Michael Vogt
    >>> print(cap.dsc_binaries)
    libcap-dev, libcap-bin, libcap1

Test ubuntu-meta in breezy, which was forcefully imported.

    >>> n = SourcePackageName.selectOneBy(name="ubuntu-meta")
    >>> um = SourcePackageRelease.selectOneBy(
    ...     sourcepackagenameID=n.id, version="0.80"
    ... )
    >>> print(
    ...     um.section.name,
    ...     um.architecturehintlist,
    ...     um.upload_distroseries.name,
    ... )
    base any breezy

And check that its files actually ended up in the librarian (these sha1sums
were calculated directly on the files):

    >>> from lp.soyuz.model.files import SourcePackageReleaseFile
    >>> files = SourcePackageReleaseFile.selectBy(
    ...     sourcepackagereleaseID=cap.id, orderBy="libraryfile"
    ... )
    >>> for f in files:
    ...     print(f.libraryfile.content.sha1)
    ...
    107d5478e72385f714523bad5359efedb5dcc8b2
    0083da007d44c02fd861c1d21579f716490cab02
    e6661aec051ccb201061839d275f2282968d8b93

Check that the section on the python-pam package is correct, and that we
only imported one:

    >>> n = SourcePackageName.selectOneBy(name="python-pam")
    >>> pp = SourcePackageRelease.selectOneBy(sourcepackagenameID=n.id)
    >>> print(pp.component.name)
    main

In the hoary Sources, its section is listed as underworld/python. Ensure
this is cut up correctly:

    >>> print(pp.section.name)
    python

Make sure that we only imported one db1-compat source package.

    >>> n = SourcePackageName.selectOneBy(name="db1-compat")
    >>> db1 = SourcePackageRelease.selectOneBy(sourcepackagenameID=n.id)
    >>> print(db1.section.name)
    libs


Testing Source Package Publishing
.................................

We check that the source package publishing override facility works:

    >>> for pub in SSPPH.selectBy(
    ...     sourcepackagereleaseID=db1.id, orderBy="distroseries"
    ... ):
    ...     print(
    ...         "%s %s %s"
    ...         % (
    ...             pub.distroseries.name,
    ...             pub.section.name,
    ...             pub.archive.purpose.name,
    ...         )
    ...     )
    hoary libs PRIMARY
    breezy oldlibs PRIMARY

We should have one entry for each package listed in Sources that was
successfully processed.

    - We had 2 errors (out of 10 Sources stanzas) in hoary: mkvmlinuz and
      util-linux.

    - We had 2 errors (out of 10 Sources stanzas) in breezy: python-sqllite
      and util-linux (again, poor thing).

    >>> print(SSPPH.select().count() - orig_sspph_count)
    21

    >>> new_count = SSPPH.selectBy(
    ...     component_id=1, pocket=PackagePublishingPocket.RELEASE
    ... ).count()
    >>> print(new_count - orig_sspph_main_count)
    21


Testing Binary Package Results
..............................

We have 26 binary packages in hoary. The 4 packages for util-linux fail, and 1
package fails for each of python-sqlite and python-pam. We should publish one
entry for each package listed in Releases.

We have 23 binary packages in breezy. db1-compat, ed, the 3 libcap packages
and python-pam is unchanged.  python-sqlite fails. The 5 ubuntu-meta packages
work.

    >>> BinaryPackageRelease.select().count() - orig_bpr_count
    40
    >>> BinaryPackageBuild.select().count() - orig_build_count
    13
    >>> SBPPH.select().count() - orig_sbpph_count
    46

Check that the shlibs parsing and bin-only-NMU version handling works as
expected:

    >>> from lp.soyuz.model.binarypackagename import BinaryPackageName
    >>> n = BinaryPackageName.selectOneBy(name="rioutil")
    >>> rio = BinaryPackageRelease.selectOneBy(binarypackagenameID=n.id)
    >>> print(rio.shlibdeps)
    librioutil 1 rioutil
    >>> print(rio.version)
    1.4.4-1.0.1
    >>> print(rio.build.source_package_release.version)
    1.4.4-1

Test all the data got to the ed BPR intact, and that the missing
priority was correctly munged to "extra":

    >>> n = BinaryPackageName.selectOneBy(name="ed")
    >>> ed = BinaryPackageRelease.selectOneBy(binarypackagenameID=n.id)
    >>> print(ed.version)
    0.2-20
    >>> print(ed.build.processor.name)
    386
    >>> print(ed.build.status)
    Successfully built
    >>> print(ed.build.distro_arch_series.processor.name)
    386
    >>> print(ed.build.distro_arch_series.architecturetag)
    i386
    >>> print(ed.priority)
    Extra
    >>> print(ed.section.name)
    editors
    >>> print(ed.summary)
    The classic unix line editor.

We now check if the Breezy publication record has the correct priority:

    >>> ed_pub = SBPPH.selectOneBy(
    ...     binarypackagereleaseID=ed.id, distroarchseriesID=breezy_i386.id
    ... )
    >>> print(ed_pub.priority)
    Standard

Check binary package libgjc-dev in Breezy. Its version number must differ from
its source version number.

    >>> n = BinaryPackageName.selectOneBy(name="libgcj-dev")
    >>> lib = BinaryPackageRelease.selectOneBy(
    ...     binarypackagenameID=n.id, version="4:4.0.1-3"
    ... )
    >>> print(lib.version)
    4:4.0.1-3
    >>> print(lib.build.source_package_release.version)
    1.28
    >>> print(lib.build.source_package_release.maintainer.displayname)
    Debian GCC maintainers

Check if the udeb was properly parsed and identified:

    >>> n = BinaryPackageName.selectOneBy(name="archive-copier")
    >>> ac = BinaryPackageRelease.selectOneBy(
    ...     binarypackagenameID=n.id, version="0.1.5"
    ... )
    >>> print(ac.version)
    0.1.5
    >>> print(ac.priority)
    Standard
    >>> print(ac.section.name)
    debian-installer
    >>> print(ac.build.source_package_release.version)
    0.1.5
    >>> print(ac.build.source_package_release.maintainer.name)
    cjwatson
    >>> print(ac.build.processor.name)
    386

We check that the binary package publishing override facility works:

    >>> n = BinaryPackageName.selectOneBy(name="libdb1-compat")
    >>> db1 = BinaryPackageRelease.selectOneBy(
    ...     binarypackagenameID=n.id, version="2.1.3-7"
    ... )
    >>> for pub in (
    ...     IStore(BinaryPackagePublishingHistory)
    ...     .find(BinaryPackagePublishingHistory, binarypackagerelease=db1)
    ...     .order_by("distroarchseries")
    ... ):
    ...     print(
    ...         "%s %s %s"
    ...         % (
    ...             pub.distroarchseries.distroseries.name,
    ...             pub.priority,
    ...             pub.archive.purpose.name,
    ...         )
    ...     )
    hoary Required PRIMARY
    breezy Optional PRIMARY

XXX: test package with invalid source version
XXX: test package with maintainer with non-ascii name


Testing People Created
......................

Ensure only one Kamion was created (he's an uploader on multiple packages),
and that we imported exactly 9 people (13 packages with 3 being uploaded by
Kamion, 2 being uploaded by mdz and 2 by doko).

    >>> from lp.services.database.sqlobject import LIKE
    >>> p = Person.selectOne(LIKE(Person.q.name, "cjwatson%"))
    >>> print(p.name)
    cjwatson
    >>> print(Person.select().count() - orig_person_count)
    13
    >>> print(TeamParticipation.select().count() - orig_tp_count)
    13
    >>> print(EmailAddress.select().count() - orig_email_count)
    13


Re-run Gina
...........

The second run of gina uses a test archive that is a copy of the first
one, but with updated Packages and Sources files for breezy that do
three important changes, implemented as publishing entries (or
overrides):

    - Binary package ed changed priority from 30 to 10 (extra) in i386
    - Source package x11proto-damage changed section from "x11" to "net"
    - Source package archive-copier has been moved from component "main"
      to "universe".

Link to the "later" archive:

    >>> os.remove("/tmp/gina_test_archive")
    >>> relative_path = (
    ...     "lib/lp/soyuz/scripts/" "tests/gina_test_archive_2nd_run"
    ... )
    >>> path = os.path.join(os.getcwd(), relative_path)
    >>> os.symlink(path, "/tmp/gina_test_archive")

We do a re-run over the same components. We should get ERRORs indicating
packages that failed to import the last time. Overrides should also have
been updated for packages in breezy which have changed since the last
run.

    >>> gina_proc = ["scripts/gina.py", "-q", "hoary", "breezy"]
    >>> proc = subprocess.Popen(
    ...     gina_proc, stderr=subprocess.PIPE, universal_newlines=True
    ... )
    >>> print(proc.stderr.read())
    ERROR   Error processing package files for clearlooks
    ...
    ...ExecutionError: Error 2 unpacking source
    WARNING Source package ed lacks section, assumed 'misc'
    ERROR   Unable to create SourcePackageData for mkvmlinuz
    ...
    ...InvalidVersionError: mkvmlinuz has an invalid version: None
    ERROR   Error processing package files for util-linux
    ...
    ...PoolFileNotFound: File util-linux_2.12p-2ubuntu2.2.dsc not in archive
    ERROR   Error processing package files for bsdutils
    ...
    ...PoolFileNotFound: .../bsdutils_2.12p-2ubuntu2_i386.deb not found
    WARNING Binary package ed lacks valid priority, assumed 'extra'
    ERROR   Unable to create BinaryPackageData for mount
    ...
    ...InvalidVersionError: mount has an invalid version: -ewePP2.12p-2ubuntu2
    WARNING Binary package python-pam lacks a section, assumed 'misc'
    ERROR   Error processing package files for python2.4-pam
    ...
    ...PoolFileNotFound: .../python2.4-pam_0.4.2-10.1ubuntu3_i386.deb not
    found
    ERROR   Error processing package files for python2.4-sqlite
    ...
    ...PoolFileNotFound: .../python2.4-sqlite_1.0.1-1ubuntu1_i386.deb not
    found
    ERROR   Error processing package files for util-linux
    ...
    ...PoolFileNotFound: .../util-linux_2.12p-2ubuntu2_i386.deb not found
    ERROR   Unable to create BinaryPackageData for util-linux-locales
    ...
    ...MissingRequiredArguments: ['installed_size']
    ERROR   Invalid Sources stanza in /tmp/tmp...
    ...
    ERROR   Error processing package files for python-sqlite
    ...
    ...PoolFileNotFound: File python-sqlite_1.0.1-2ubuntu1.dsc not in archive
    ERROR   Error processing package files for util-linux
    ...
    ...PoolFileNotFound: File util-linux_2.12p-6ubuntu5.dsc not in archive
    ERROR   Error processing package files for python-sqlite
    ...
    ...PoolFileNotFound: .../python-sqlite_1.0.1-2ubuntu1_all.deb not found
    <BLANKLINE>
    >>> proc.wait()
    0
    >>> transaction.commit()

Nothing should happen to most of our data -- no counts should have
changed, etc.

    >>> SourcePackageRelease.select().count() - orig_spr_count
    17
    >>> print(Person.select().count() - orig_person_count)
    13
    >>> print(TeamParticipation.select().count() - orig_tp_count)
    13
    >>> print(EmailAddress.select().count() - orig_email_count)
    13
    >>> BinaryPackageRelease.select().count() - orig_bpr_count
    40
    >>> BinaryPackageBuild.select().count() - orig_build_count
    13

But the overrides do generate extra publishing entries:

    >>> SBPPH.select().count() - orig_sbpph_count
    47
    >>> print(SSPPH.select().count() - orig_sspph_count)
    23

Check that the overrides we did were correctly issued. We can't use
selectOneBy because, of course, there may be multiple rows published for that
package -- that's what overrides actually do.

    >>> from lp.services.database.sqlbase import sqlvalues
    >>> x11_pub = SSPPH.select(
    ...     """
    ...     sourcepackagerelease = %s AND
    ...     distroseries = %s AND
    ...     status in %s
    ...     """
    ...     % sqlvalues(x11p, breezy, active_publishing_status),
    ...     orderBy=["-datecreated"],
    ... )[0]
    >>> print(x11_pub.section.name)
    net
    >>> ed_pub = SBPPH.select(
    ...     """
    ...     binarypackagerelease = %s AND
    ...     distroarchseries = %s AND
    ...     status in %s
    ...     """
    ...     % sqlvalues(ed, breezy_i386, active_publishing_status),
    ...     orderBy=["-datecreated"],
    ... )[0]
    >>> print(ed_pub.priority)
    Extra
    >>> n = SourcePackageName.selectOneBy(name="archive-copier")
    >>> ac = SourcePackageRelease.selectOneBy(
    ...     sourcepackagenameID=n.id, version="0.3.6"
    ... )
    >>> ac_pub = SSPPH.select(
    ...     """
    ...     sourcepackagerelease = %s AND
    ...     distroseries = %s AND
    ...     status in %s
    ...     """
    ...     % sqlvalues(ac, breezy, active_publishing_status),
    ...     orderBy=["-datecreated"],
    ... )[0]
    >>> print(ac_pub.component.name)
    universe


Partner archive import
......................

Importing the partner archive requires overriding the component to
"partner", which also makes the archive on any publishing records the
partner archive.

First get a set of existing publishings for both source and binary:

    >>> comm_archive = ubuntu.getArchiveByComponent("partner")
    >>> hoary = ubuntu["hoary"]
    >>> hoary_i386 = hoary["i386"]
    >>> partner_source_set = set(
    ...     SSPPH.select("distroseries = %s" % sqlvalues(hoary))
    ... )

    >>> partner_binary_set = set(
    ...     SBPPH.select("distroarchseries = %s" % sqlvalues(hoary_i386))
    ... )

Now run gina to import packages and convert them to partner:

    >>> gina_proc = ["scripts/gina.py", "-q", "partner"]
    >>> proc = subprocess.Popen(
    ...     gina_proc, stderr=subprocess.PIPE, universal_newlines=True
    ... )
    >>> proc.wait()
    0
    >>> transaction.commit()

There will now be a number of publishings in the partner archive:

    >>> partner_source_set_after = set(
    ...     SSPPH.select("distroseries = %s" % sqlvalues(hoary))
    ... )

    >>> partner_binary_set_after = set(
    ...     SBPPH.select("distroarchseries = %s" % sqlvalues(hoary_i386))
    ... )

    >>> source_difference = partner_source_set_after - partner_source_set
    >>> len(source_difference)
    12

    >>> binary_difference = partner_binary_set_after - partner_binary_set
    >>> len(binary_difference)
    24

All the publishings will also have the 'partner' component and the
partner archive:

    >>> for name in set(sspph.component.name for sspph in source_difference):
    ...     print(name)
    ...
    partner

    >>> for name in set(sbpph.component.name for sbpph in binary_difference):
    ...     print(name)
    ...
    partner

    >>> for name in set(
    ...     sspph.archive.purpose.name for sspph in source_difference
    ... ):
    ...     print(name)
    PARTNER

    >>> for name in set(
    ...     sbpph.archive.purpose.name for sbpph in binary_difference
    ... ):
    ...     print(name)
    PARTNER


Source-only imports
...................

Gina has a 'source-only' configuration option which allows it to
import only sources from the configured archive.

That's how we intend to start importing all debian source releases to
the launchpad system. This way we would have precise records of
"Ubuntu-Debian" packages relationships and expose this information,
not only in Soyuz (package managing) but also in Bugs and Blueprints,
for instance.

We will restore the initial 'gina_test_archive' because it contains a
entry for a suite called 'testing' which contains only the source
indexes from the 'hoary' suite.

    >>> os.remove("/tmp/gina_test_archive")
    >>> relative_path = "lib/lp/soyuz/scripts/tests/gina_test_archive"
    >>> path = os.path.join(os.getcwd(), relative_path)
    >>> os.symlink(path, "/tmp/gina_test_archive")

We will also create the target distroseries for the imported
sources. We will import them into Debian/Lenny distroseries as
specified in the testing configuration.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> debian = getUtility(IDistributionSet).getByName("debian")

    # Only the distro owner and admins can create a new series.
    >>> login("mark@example.com")
    >>> lenny = debian.newSeries(
    ...     "lenny",
    ...     "lenny",
    ...     "Lenny",
    ...     "---",
    ...     "!!!",
    ...     "8.06",
    ...     hoary,
    ...     celebs.launchpad_developers,
    ... )
    >>> login(ANONYMOUS)

Note that we will create a Lenny/i386 port (DistroArchSeries) to check
if no binaries get imported by mistake. However this is not required
in production, i.e., just creating 'lenny' should suffice for the
source-only import to happen.

    >>> lenny_i386 = lenny.newArch(
    ...     processor=getUtility(IProcessorSet).getByName("386"),
    ...     architecturetag="i386",
    ...     official=True,
    ...     owner=celebs.launchpad_developers,
    ... )

We will also store the number of binaries already published in debian
PRIMARY archive, so we can check later it was unaffected by the
import.

    >>> debian_binaries = SBPPH.selectBy(archive=debian.main_archive)
    >>> number_of_debian_binaries = debian_binaries.count()

Commit the changes and run the importer script.

    >>> transaction.commit()

    >>> gina_proc = ["scripts/gina.py", "-q", "lenny"]
    >>> proc = subprocess.Popen(
    ...     gina_proc, stderr=subprocess.PIPE, universal_newlines=True
    ... )
    >>> proc.wait()
    0

    >>> transaction.commit()

There is now a number of source publications in PUBLISHED status for the
targetted distroseries, 'lenny'.

    >>> lenny_sources = SSPPH.select("distroseries = %s" % sqlvalues(lenny))
    >>> lenny_sources.count()
    12

    >>> for name in set([pub.status.name for pub in lenny_sources]):
    ...     print(name)
    ...
    PUBLISHED

As mentioned before, lenny/i386 is empty, no binaries were imported.
Also, the number of binaries published in the whole debian distribution
hasn't changed.

    >>> lenny_binaries = SBPPH.selectBy(distroarchseries=lenny_i386)
    >>> lenny_binaries.count()
    0

    >>> debian_binaries = SBPPH.selectBy(archive=debian.main_archive)
    >>> debian_binaries.count() == number_of_debian_binaries
    True


Processing multiple suites in the same batch
............................................

Both, 'lenny' and 'hoary' (as partner) will be processed in the same
batch.

    >>> gina_proc = ["scripts/gina.py", "lenny", "partner"]
    >>> proc = subprocess.Popen(
    ...     gina_proc, stderr=subprocess.PIPE, universal_newlines=True
    ... )

    >>> print(proc.stderr.read())
    INFO    Creating lockfile: /var/lock/launchpad-gina.lock
    ...
    INFO    === Processing debian/lenny/release ===
    ...
    INFO    === Processing ubuntu/hoary/release ===
    ...

    >>> proc.wait()
    0


Other tests
...........

For kicks, finally, run gina on a configured but incomplete archive:

    >>> gina_proc = ["scripts/gina.py", "-q", "bogus"]
    >>> proc = subprocess.Popen(
    ...     gina_proc, stderr=subprocess.PIPE, universal_newlines=True
    ... )
    >>> print(proc.stderr.read())
    ERROR   Failed to analyze archive for bogoland
    ...
    ...MangledArchiveError: No archive directory for bogoland/main
    <BLANKLINE>
    >>> proc.wait()
    1


Wrap up
.......

Remove the tmp link to the gina_test_archive
    >>> os.remove("/tmp/gina_test_archive")

