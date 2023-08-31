Soyuz Set of Uploads Test
=========================

This test will:

  * Pre-create the directory structure
  * Turn on the test keyserver
  * Run process-upload.py
  * Check result
  * Mark packages as ACCEPTED
  * Runs process-accepted.py
  * Check results
  * Cleanup


Pre-creating directories
------------------------

First, let's create the temporary directory structure where we'll put uploaded
files in.

    >>> import os
    >>> import tempfile
    >>> temp_dir = tempfile.mkdtemp()
    >>> incoming_dir = os.path.join(temp_dir, "incoming")
    >>> accepted_dir = os.path.join(temp_dir, "accepted")
    >>> rejected_dir = os.path.join(temp_dir, "rejected")
    >>> failed_dir = os.path.join(temp_dir, "failed")
    >>> os.mkdir(incoming_dir)


A note about error checking
---------------------------

To be able to process the entire upload and provide the full set of
errors, we need:
  1. A changes file with no syntax errors
  2. A changes file with at least a valid email address for the
     changed-by field or the package signer, both of which must be registered
     in Launchpad.
  3. A changes file with a valid distroseries and pocket (e.g. gutsy-updates)
  4. A changes file that enumerates all the files in the upload, with
     correct md5 sum and file sizes.
  5. Actual files uploaded that match the ones described in the changes file.

 If (1) is not available, the upload silently fails.
 If (2) is not available, the upload silently fails.
 If (3) or (4) is not available, the upload is rejected immediately with
 no further checking.
 If any files in (5) are missing, we report as much information as we can
 about what is available.


Processing Uploads
------------------

Before asking the system to process the upload, we must prepare the
database and services to receive it. Since we're using
'sample.person@canonical.com' as our Changed-By address and their
key has signed all the relevant uploads in the suite of uploads we're
using, this essentially boils down to ensuring that test keyserver and the
librarian are running and making sure that the key is attached to the
relevant launchpad person.

    >>> from lp.testing.keyserver import KeyServerTac
    >>> keyserver = KeyServerTac()
    >>> keyserver.setUp()

Import public keyring into current LPDB.

    >>> from lp.testing.gpgkeys import import_public_test_keys
    >>> import_public_test_keys()

Having set up that infrastructure we need to prepare a breezy distroseries
for the ubuntutest distribution.

    >>> from lp.registry.model.distribution import Distribution
    >>> from lp.soyuz.enums import PackageUploadStatus
    >>> from lp.soyuz.scripts.initialize_distroseries import (
    ...     InitializeDistroSeries,
    ... )
    >>> from lp.services.librarian.model import LibraryFileAlias
    >>> from lp.testing.factory import LaunchpadObjectFactory
    >>> ubuntu = Distribution.byName("ubuntu")
    >>> breezy_autotest = ubuntu["breezy-autotest"]
    >>> ubuntutest = Distribution.byName("ubuntutest")
    >>> breezy = ubuntutest.newSeries(
    ...     "breezy",
    ...     "Breezy Badger",
    ...     "The Breezy Badger",
    ...     "Black and White",
    ...     "Someone",
    ...     "5.10",
    ...     None,
    ...     breezy_autotest.owner,
    ... )
    >>> factory = LaunchpadObjectFactory()
    >>> breezy.previous_series = breezy_autotest
    >>> ids = InitializeDistroSeries(breezy, [breezy_autotest.id])
    >>> ids.initialize()
    INFO:...:Setting distroseries parents.
    INFO:...:Copying distroseries configuration from parents.
    INFO:...:Copying distroarchseries from parents.
    INFO:...:Setting nominated arch-indep configuration.
    INFO:...:Copying packages from parents.
    INFO:...:Copying packagesets from parents.
    INFO:...:Copying permissions from parents.
    INFO:...:Creating DistroSeriesDifferences.
    >>> breezy.changeslist = "breezy-changes@ubuntu.com"
    >>> fake_chroot = LibraryFileAlias.get(1)
    >>> unused = breezy["i386"].addOrUpdateChroot(fake_chroot)

Add disk content for file inherited from ubuntu/breezy-autotest:

    >>> from lp.services.librarianserver.testing.server import (
    ...     fillLibrarianFile,
    ... )
    >>> fillLibrarianFile(54)

Now that the infrastructure is ready, we prepare a set of useful methods.

Firstly, we need a way to copy a test upload into the queue (but skip
lock files, which have names starting with a dot).

    >>> import shutil
    >>> from lp.archiveuploader.tests import datadir
    >>> def punt_upload_into_queue(leaf, distro):
    ...     inc_dir = os.path.join(incoming_dir, leaf, distro)
    ...     os.makedirs(inc_dir)
    ...     for entry in os.scandir(datadir(os.path.join("suite", leaf))):
    ...         shutil.copy(entry.path, inc_dir)
    ...

We need a way to count the items in a queue directory

    >>> def count_items(queue):
    ...     return len(queue)
    ...

And then we need a way to process the uploads from the queue

    >>> import logging
    >>> from lp.archiveuploader.scripts.processupload import ProcessUpload
    >>> from lp.services.config import config
    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.testing.dbuser import switch_dbuser
    >>> from lp.testing.layers import LaunchpadZopelessLayer
    >>> def process_uploads(upload_policy, series, loglevel):
    ...     """Simulate process-upload.py script run.
    ...
    ...     :param upload_policy: context in which to consider the upload
    ...         (equivalent to script's --context option).
    ...     :param series: distro series to give back from.
    ...         (equivalent to script's --series option).
    ...     :param loglevel: logging level (as defined in logging module).
    ...         Any log messages below this level will be suppressed.
    ...     """
    ...     args = [temp_dir, "-C", upload_policy]
    ...     if series is not None:
    ...         args.extend(["-s", series])
    ...     # Run script under 'uploader' DB user.  The dbuser argument to the
    ...     # script constructor is ignored, so we must change DB users here.
    ...     switch_dbuser(config.uploader.dbuser)
    ...     process = ProcessUpload(
    ...         "process-upload", dbuser="ignored", test_args=args
    ...     )
    ...     process.logger = FakeLogger()
    ...     if loglevel is not None:
    ...         process.logger.setLevel(loglevel)
    ...     process.txn = LaunchpadZopelessLayer.txn
    ...     process.main()
    ...     switch_dbuser("launchpad")
    ...

And we need a way to process the accepted queue

    >>> from zope.component import getUtility
    >>> from lp.testing import (
    ...     login,
    ... )
    >>> from lp.registry.interfaces.distribution import IDistributionSet

    >>> login("foo.bar@canonical.com")

    >>> def process_accepted(distro):
    ...     distribution = getUtility(IDistributionSet)[distro]
    ...     for series in distribution.series:
    ...         items = series.getPackageUploads(
    ...             status=PackageUploadStatus.ACCEPTED
    ...         )
    ...         for item in items:
    ...             item.realiseUpload()
    ...


If an upload of ours ends up in the NEW queue, we need a way to process
it into the accepted queue

    >>> def process_new(distro, series):
    ...     distribution = getUtility(IDistributionSet)[distro]
    ...     if series is None:
    ...         series = "breezy"
    ...     dr, pocket = distribution.getDistroSeriesAndPocket(series)
    ...     items = dr.getPackageUploads(status=PackageUploadStatus.NEW)
    ...     for item in items:
    ...         item.setAccepted()
    ...     items = dr.getPackageUploads(
    ...         status=PackageUploadStatus.UNAPPROVED
    ...     )
    ...     for item in items:
    ...         item.setAccepted()
    ...

Finally, as a very simplistic publishing process, we may need to punt any
given upload into the published state, so here's a very simplistic publisher

    >>> from lp.registry.model.distroseries import DistroSeries
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.soyuz.model.distroarchseries import DistroArchSeries
    >>> from lp.soyuz.model.publishing import (
    ...     SourcePackagePublishingHistory as SPPH,
    ...     BinaryPackagePublishingHistory as BPPH,
    ... )
    >>> from lp.soyuz.enums import PackagePublishingStatus as PPS
    >>> from lp.services.database.constants import UTC_NOW
    >>> def simple_publish(distro):
    ...     srcs_to_publish = IStore(SPPH).find(
    ...         SPPH,
    ...         SPPH.distroseries == DistroSeries.id,
    ...         DistroSeries.distribution == Distribution.id,
    ...         Distribution.name == distro,
    ...         SPPH.status == PPS.PENDING,
    ...     )
    ...     bins_to_publish = IStore(BPPH).find(
    ...         BPPH,
    ...         BPPH.distroarchseries == DistroArchSeries.id,
    ...         DistroArchSeries.distroseries == DistroSeries.id,
    ...         DistroSeries.distribution == Distribution.id,
    ...         Distribution.name == distro,
    ...         BPPH.status == PPS.PENDING,
    ...     )
    ...     published_one = False
    ...     for src in srcs_to_publish:
    ...         src.status = PPS.PUBLISHED
    ...         src.datepublished = UTC_NOW
    ...         published_one = True
    ...     for bin in bins_to_publish:
    ...         bin.status = PPS.PUBLISHED
    ...         bin.datepublished = UTC_NOW
    ...         published_one = True
    ...     return published_one
    ...


We'll be doing a lot of uploads with sanity checks, and expect them to
succeed.  A helper function, simulate_upload does that with all the checking.

    >>> from lp.services.mail import stub

    >>> def simulate_upload(
    ...     leafname,
    ...     is_new=False,
    ...     upload_policy="anything",
    ...     series=None,
    ...     distro="ubuntutest",
    ...     loglevel=logging.WARN,
    ... ):
    ...     """Process upload(s).  Options are as for process_uploads()."""
    ...     punt_upload_into_queue(leafname, distro=distro)
    ...     process_uploads(upload_policy, series, loglevel)
    ...     # We seem to be leaving a lock file behind here for some reason.
    ...     # Naturally it doesn't count as an unprocessed incoming file,
    ...     # which is what we're really looking for.
    ...     lockfile = os.path.join(incoming_dir, ".lock")
    ...     if os.access(lockfile, os.F_OK):
    ...         os.remove(lockfile)
    ...     assert (
    ...         len(os.listdir(incoming_dir)) == 0
    ...     ), "Incoming should be empty: %s" % os.listdir(incoming_dir)
    ...
    ...     rejected_contents = os.listdir(rejected_dir)
    ...     if len(rejected_contents) > 0:
    ...         # Clean up rejected entry
    ...         shutil.rmtree(os.path.join(rejected_dir, leafname))
    ...         print("Rejected uploads: %s" % ", ".join(rejected_contents))
    ...         return
    ...
    ...     assert (
    ...         len(os.listdir(failed_dir)) == 0
    ...     ), "Failed upload(s): %s" % os.listdir(failed_dir)
    ...     if is_new:
    ...         process_new(distro=distro, series=series)
    ...     process_accepted(distro=distro)
    ...     assert simple_publish(
    ...         distro=distro
    ...     ), "Should publish at least one item"
    ...     if loglevel is None or loglevel <= logging.INFO:
    ...         print("Upload complete.")

    >>> from lp.testing.mail_helpers import (
    ...     pop_notifications,
    ...     sort_addresses,
    ... )
    >>> def read_email():
    ...     """Pop all emails from the test mailbox, and summarize them.
    ...
    ...     For each message, prints "To:" followed by recipients; "Subject:"
    ...     followed by subject line; and message body followed by a blank
    ...     line.
    ...     """
    ...     for message in pop_notifications(commit=False):
    ...         print("To:", sort_addresses(message["to"]))
    ...         print("Subject:", message["subject"])
    ...         print(
    ...             "Content-Type:", message.get_payload()[0]["content-type"]
    ...         )
    ...         print()
    ...         print(
    ...             message.get_payload()[0]
    ...             .get_payload(decode=True)
    ...             .decode("UTF-8")
    ...         )
    ...         print()
    ...

The 'bar' package' is an arch-all package. We have four stages to the
bar test. Each stage should be simple enough. First we have a new
source, then a new binary, then an overridable source and then an
overridable binary. This tests the simple overriding of both sources
and arch-independent binaries.

    >>> simulate_upload("bar_1.0-1", is_new=True, loglevel=logging.INFO)
    INFO Processing upload
    ...
    Upload complete.

    >>> simulate_upload("bar_1.0-1_binary", is_new=True)

    >>> simulate_upload("bar_1.0-2")

    >>> simulate_upload("bar_1.0-2_binary")

Check the rejection of a malicious version of bar package which refers
to a different 'bar_1.0.orig.tar.gz'.

    >>> stub.test_emails = []
    >>> simulate_upload("bar_1.0-3", loglevel=logging.ERROR)
    Rejected uploads: bar_1.0-3

    >>> read_email()
    To: Daniel Silverstone <daniel.silverstone@canonical.com>
    Subject: [ubuntutest] bar_1.0-3_source.changes (Rejected)
    ...
    To: Foo Bar <foo.bar@canonical.com>
    Subject: [ubuntutest] bar_1.0-3_source.changes (Rejected)
    ...

Force weird behaviour with rfc2047 sentences containing '.' on
bar_1.0-4, which caused bug # 41102.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> name16 = getUtility(IPersonSet).getByName("name16")
    >>> name16.display_name = "Foo B. Bar"

Check the email recipient for displayname containing special chars,
'.', must be rfc2047 compliant:

    >>> simulate_upload("bar_1.0-4")
    >>> read_email()  # noqa
    To: "Foo B. Bar" <foo.bar@canonical.com>
    Subject: [ubuntutest/breezy] bar 1.0-4 (Accepted)
    Content-Type: text/plain; charset="utf-8"
    <BLANKLINE>
    bar (1.0-4) breezy; urgency=low
    <BLANKLINE>
      * Changer using non-preferred email
    <BLANKLINE>
    Date: Tue, 25 Apr 2006 10:36:14 -0300
    Changed-By: cprov@ubuntu.com (Celso R. Providelo)
    Maintainer: Launchpad team <launchpad@lists.canonical.com>
    Signed-By: foo.bar@canonical.com (Foo B. Bar)
    http://launchpad.test/ubuntutest/+source/bar/1.0-4
    <BLANKLINE>
    ==
    <BLANKLINE>
     OK: bar_1.0.orig.tar.gz
     OK: bar_1.0-4.diff.gz
     OK: bar_1.0-4.dsc
         -> Component: universe Section: devel
    <BLANKLINE>
    Announcing to breezy-changes@ubuntu.com
    <BLANKLINE>
    Thank you for your contribution to ubuntutest.
    <BLANKLINE>
    -- 
    You are receiving this email because you made this upload.
    <BLANKLINE>
    <BLANKLINE>
    To: Celso Providelo <celso.providelo@canonical.com>
    ...
    To: breezy-changes@ubuntu.com
    ...

Revert changes:

    >>> name16.display_name = "Foo Bar"

Check if we forcibly add the changer as recipient for "sync" uploads,
which contains unsigned changesfile. Ensure it sends email to the
changer.

    >>> stub.test_emails = []

    >>> simulate_upload("bar_1.0-5", upload_policy="sync")
    >>> read_email()
    To: Celso Providelo <celso.providelo@canonical.com>
    Subject: [ubuntutest/breezy] bar 1.0-5 (Accepted)
    ...


Add a new series of bar sourcepackage, rename its binary package to
'bar-bin', upload the binary and look for a spurious sourcepackagename
created with the binary package name.

    >>> simulate_upload("bar_1.0-6", upload_policy="sync")
    >>> simulate_upload("bar_1.0-6_binary", is_new=True)

    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet,
    ... )
    >>> spn_set = getUtility(ISourcePackageNameSet)
    >>> assert spn_set.queryByName("bar-bin") is None


Source Uploads using epochs
---------------------------

As described in Debian Policy
(http://www.debian.org/doc/debian-policy/ch-controlfields.html)

A package version can be provided as:

[epoch:]upstream_version[-debian_revision]

The 'epoch' allow mistakes in the version numbers of older versions of
a package, and also a package's previous version numbering schemes,
to be left behind.

In few words, it is another mechanism to override upstream version
scheme changes and keep the package sanely versioned.

For instance, if upstream "bar" switched their versioning from
date-based to version based.

An old version '20050304' will always higher than '0.1.2'.

So, when such thing happens, the package maintainer added the epoch to
get '1:0.1.2' which is higher than '20050304', since the epoch is
implied as '0'.

Check if upload system interpret epochs properly, inter-epoch versions
will get compared in this case (see bug #85201):

    >>> simulate_upload("bar_1.0-7", upload_policy="sync")
    >>> read_email()
    To: ...
    Subject: [ubuntutest/breezy] bar 1.0-6 (Accepted)
    ...

    >>> simulate_upload("bar_1.0-8", upload_policy="sync")
    >>> read_email()
    To: ...
    Subject: [ubuntutest/breezy] bar 1:1.0-8 (Accepted)
    ...

Pocket Version Consistency
--------------------------

Check behaviour of upload system for uploads across pockets (see
bug #34089, #58144 and #83976 for further info)

Let's start a new package series by uploading foo_1.0-1  source in
ubututest/breezy-RELEASE:

    >>> simulate_upload(
    ...     "foo_1.0-1",
    ...     upload_policy="sync",
    ...     is_new=True,
    ...     loglevel=logging.DEBUG,
    ... )
    DEBUG Initializing connection.
    ...
    DEBUG Sent a mail:
    DEBUG   Subject: [ubuntutest/breezy] foo 1.0-1 (New)
    DEBUG   Sender: Root <root@localhost>
    DEBUG   Recipients: Daniel Silverstone <daniel.silverstone@canonical.com>
    DEBUG   Bcc: Root <root@localhost>
    DEBUG   Body:
    DEBUG NEW: foo_1.0.orig.tar.gz
    DEBUG NEW: foo_1.0-1.diff.gz
    DEBUG NEW: foo_1.0-1.dsc
    DEBUG
    DEBUG foo (1.0-1) breezy; urgency=low
    DEBUG
    DEBUG   * Initial version
    DEBUG
    DEBUG
    DEBUG Your package contains new components which requires manual editing
    of
    DEBUG the override file.  It is ok otherwise, so please be patient.  New
    DEBUG packages are usually added to the overrides about once a week.
    DEBUG
    DEBUG You may have gotten the distroseries wrong.  If so, you may get
    warnings
    DEBUG above if files already exist in other distroseries.
    DEBUG
    DEBUG --
    DEBUG You are receiving this email because you are the most recent person
    DEBUG listed in this package's changelog.
    INFO  Committing the transaction and any mails associated with this
    upload.
    ...
    Upload complete.

And its binary:

    >>> simulate_upload(
    ...     "foo_1.0-1_i386_binary",
    ...     upload_policy="anything",
    ...     is_new=True,
    ...     loglevel=logging.DEBUG,
    ... )
    DEBUG ...
    DEBUG foo: (binary) NEW
    ...
    Upload complete.

Set ubuntutest/breezy as the "current series" to activate post-release
pockets.

    >>> from lp.registry.interfaces.series import SeriesStatus
    >>> breezy.status = SeriesStatus.CURRENT
    >>> LaunchpadZopelessLayer.txn.commit()

Since we are using 'sync' policy in the following tests the packages
are auto-approved, however, in the real environment the 'insecure'
policy will be used which force packages to wait for approval in the
UNAPPROVED queue.

Upload a newer version of source package "foo" to breezy-backports:

    >>> simulate_upload(
    ...     "foo_2.9-1", upload_policy="sync", loglevel=logging.DEBUG
    ... )
    DEBUG Initializing connection.
    ...
    DEBUG Setting it to ACCEPTED
    ...
    Upload complete.


In order to verify if the binary ancestry lookup algorithm works we
will need to build a new DistroArchSeries for powerpc in
ubuntutest/breezy.

    >>> from lp.buildmaster.model.processor import Processor
    >>> powerpc = Processor(
    ...     name="powerpc", title="PowerPC G3/G4", description="G3/G4"
    ... )
    >>> powerpc_dar = breezy.newArch("powerpc", powerpc, True, breezy.owner)

After having the respective DistroArchSeries in place we will submit a
binary upload for the last source in BACKPORTS. The ancestry should be
found in i386/RELEASE, because it's the only one available.

    >>> simulate_upload(
    ...     "foo_2.9-1_binary",
    ...     upload_policy="anything",
    ...     loglevel=logging.DEBUG,
    ... )
    DEBUG ...
    DEBUG Checking for foo/2.9-1/powerpc binary ancestry
    ...
    DEBUG Setting it to ACCEPTED
    ...
    Upload complete.


Due the constraints relaxation requested by bug #83976, even having
foo_2.9-1 as the current version in BACKPORTS, we should be able to
upload foo_2.9-2 to UPDATES. If it strongly affects the users' system
it should be rejected by the package reviewer, otherwise people can
live with this inconsistency.

    >>> simulate_upload(
    ...     "foo_2.9-2", upload_policy="sync", loglevel=logging.DEBUG
    ... )
    DEBUG Initializing connection.
    ...
    DEBUG Setting it to ACCEPTED
    ...
    Upload complete.


Same behaviour is expected for a version in SECURITY lower than that
in PROPOSED:

    >>> simulate_upload(
    ...     "foo_2.9-4", upload_policy="sync", loglevel=logging.DEBUG
    ... )
    DEBUG Initializing connection.
    ...
    DEBUG Setting it to ACCEPTED
    ...
    Upload complete.

    >>> simulate_upload(
    ...     "foo_2.9-3", upload_policy="sync", loglevel=logging.DEBUG
    ... )
    DEBUG Initializing connection.
    ...
    DEBUG Setting it to ACCEPTED
    ...
    Upload complete.


However, the source upload of a smaller version than the one already
published inside the target pocket should be rejected:

    >>> simulate_upload(
    ...     "foo_1.0-3", upload_policy="sync", loglevel=logging.INFO
    ... )
    INFO ...
    INFO Upload was rejected:
    INFO foo_1.0-3.dsc: Version older than that in the archive. 1.0-3 <= 2.9-2
    ...
    Rejected uploads: foo_1.0-3

Note that the ancestry pointed in the rejection message (2.9-2) is what
we expect.

Set ubuntutest/breezy to 'experimental' state again to not affect the
rest of the test:

    >>> breezy.status = SeriesStatus.EXPERIMENTAL
    >>> IStore(breezy).flush()


Regression test for bug 54039. Currently must be here, see bug 54158.

In bug 54039, we were rewriting all Release files, at a time when, in
unchanged pockets, the uncompressed Sources and Packages files would
be missing, having been deleted at the end of the previous publisher
run. Rewriting the Release files with these files missing produces a
broken distro.

We will make two publisher runs, deleting the uncompressed index files
in between, and verify that the second publisher run doesn't screw up the
release files in the way bug-54039 infected code would.

First a couple helpers.

    >>> import stat
    >>> from lp.testing.script import run_script

    >>> def run_publish_distro(careful=False, careful_publishing=False):
    ...     """Run publish-distro on ubuntutest with given extra args.
    ...
    ...     :param careful: turns on all "careful" options to the
    ...         publish-distro script.  Equivalent to the script's --careful
    ...         option.
    ...     :param careful_publishing: passes the --careful-publishing option
    ...         to the publish-distro script.
    ...     """
    ...     args = ["-v", "-d", "ubuntutest"]
    ...     if careful:
    ...         args.append("-C")
    ...     if careful_publishing:
    ...         args.append("-P")
    ...     script = os.path.join(config.root, "scripts", "publish-distro.py")
    ...     result, stdout, stderr = run_script(script, args)
    ...     print(stderr)
    ...     if result != 0:
    ...         print("Script returned", result)
    ...

    >>> def release_file_has_uncompressed_packages(path):
    ...     """Does the release file include uncompressed Packages?"""
    ...     release_file = open(path)
    ...     release_contents = release_file.read()
    ...     release_file.close()
    ...     target_string = "Packages\n"
    ...     return release_contents.find(target_string) != -1
    ...


First publish the distro carefully, to get everything in place.
Before this can happen we need to set up some dummy librarian files for
files that are published in the sample data.

    >>> fillLibrarianFile(66)
    >>> fillLibrarianFile(67)
    >>> fillLibrarianFile(68)
    >>> fillLibrarianFile(70)

    >>> import transaction
    >>> transaction.commit()
    >>> run_publish_distro(careful=True)
    INFO    Creating lockfile: ...
    DEBUG   Enabled by DEFAULT section
    DEBUG   Distribution: ubuntutest
    ...
    DEBUG   Added
    /var/tmp/archive/ubuntutest/pool/universe/b/bar/bar_1.0-2_i386.deb from
    library
    DEBUG   Added
    /var/tmp/archive/ubuntutest/pool/universe/b/bar/bar_1.0-1_i386.deb from
    library
    ...


Delete the uncompressed Packages and Sources files from the archive folder.
This simulates what cron.daily does between publishing runs.

    >>> os.system(
    ...     'find /var/tmp/archive/ubuntutest \\( -name "Packages" '
    ...     '-o -name "Sources" \\) -exec rm "{}" \\;'
    ... )
    0

Record the timestamp of a release file we expect to be rewritten,
which we'll need later.

    >>> release_timestamp = os.stat(
    ...     "/var/tmp/archive/ubuntutest/dists/" "breezy/Release"
    ... )[stat.ST_MTIME]

Re-publish the distribution, with careful publishing only. This will mean
only pockets into which we've done some publication will have apt-ftparchive
work done.

Check that breezy-autotest is skipped, to ensure that changes to what's
uploaded in the test above don't break the assumptions of this test.

    >>> run_publish_distro(careful_publishing=True)
    INFO    Creating lockfile: ...
    DEBUG   Enabled by DEFAULT section
    DEBUG   Distribution: ubuntutest
    ...
    DEBUG   /var/tmp/archive/ubuntutest/pool/universe/b/bar/bar_1.0-2_i386.deb
    is already in pool with the same content.
    ...
    DEBUG   Skipping a-f stanza for breezy-autotest/RELEASE
    ...
    DEBUG   Skipping release files for breezy-autotest/RELEASE
    ...

Check the breezy-security release file doesn't exhibit bug 54039.

    >>> release_file_has_uncompressed_packages(
    ...     "/var/tmp/archive/ubuntutest/dists/breezy-security/Release"
    ... )
    True

We also need to check the fix for bug 54039 didn't go too far, ie. that
Release files are still generated for those pockets where they should be.
So, check the MTIME has changed for hoary-test/Release.

    >>> new_release_timestamp = os.stat(
    ...     "/var/tmp/archive/ubuntutest/dists/" "breezy/Release"
    ... )[stat.ST_MTIME]

    >>> new_release_timestamp == release_timestamp
    False


Nice! That's enough for now.. let's kill the process and clean
everything up.

    >>> shutil.rmtree("/var/tmp/archive/")
    >>> shutil.rmtree(temp_dir)

    >>> keyserver.tearDown()
