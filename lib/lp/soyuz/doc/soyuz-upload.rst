Soyuz Upload Test
-----------------

This test will:

  * Upload packages
  * Import gpg key for katie
  * Register gpg key for katie
  * Register the katie user in the right team
  * Turn on the test keyserver
  * Include the non_free component in the database
  * Run process-upload.py
  * Check result
  * Mark packages as ACCEPTED
  * Runs process-accepted.py
  * Check results
  * Cleanup


Uploading Packages
------------------


First, let's create a temporary directory where we'll put
uploaded files in.

    >>> import os
    >>> import shutil
    >>> import tempfile
    >>> temp_dir = tempfile.mkdtemp()
    >>> incoming_dir = os.path.join(temp_dir, "incoming")
    >>> accepted_dir = os.path.join(temp_dir, "accepted")
    >>> rejected_dir = os.path.join(temp_dir, "rejected")
    >>> failed_dir = os.path.join(temp_dir, "failed")
    >>> os.mkdir(incoming_dir)


Now let's copy the files into separate upload directories, as if they'd
been uploaded over FTP.

    >>> from lp.services.config import config
    >>> from lp.archiveuploader.tagfiles import (
    ...     parse_tagfile,
    ...     TagFileParseError,
    ... )
    >>> import glob
    >>> test_files_dir = os.path.join(
    ...     config.root, "lib/lp/soyuz/scripts/" "tests/upload_test_files/"
    ... )
    >>> changes = sorted(glob.glob(test_files_dir + "*.changes"))
    >>> sent_filenames = []
    >>> uploads = []
    >>> package_names = []

    >>> seq = 1
    >>> for changes_filepath in changes:
    ...     try:
    ...         tf = parse_tagfile(changes_filepath)
    ...     except TagFileParseError:
    ...         tf = {}
    ...
    ...     if "Source" in tf:
    ...         package_names.append(six.ensure_text(tf["Source"]))
    ...
    ...     send_filepaths = [changes_filepath]
    ...     if "Files" in tf:
    ...         send_filepaths.extend(
    ...             [
    ...                 os.path.join(test_files_dir, line.split()[-1])
    ...                 for line in six.ensure_text(tf["Files"]).splitlines()
    ...                 if line
    ...             ]
    ...         )
    ...
    ...     sent_filenames.extend(
    ...         os.path.basename(filepath) for filepath in send_filepaths
    ...     )
    ...
    ...     upload_dir = os.path.join(
    ...         incoming_dir, "upload-%06d" % seq, "ubuntutest"
    ...     )
    ...     os.makedirs(upload_dir)
    ...
    ...     for filepath in send_filepaths:
    ...         _ = shutil.copyfile(
    ...             filepath,
    ...             os.path.join(upload_dir, os.path.basename(filepath)),
    ...         )
    ...
    ...     uploads.append(send_filepaths)
    ...     seq += 1
    ...

Check that what we've just uploaded (everything in test_files_dir) is
what we were expecting to have uploaded.

    >>> print(pretty(package_names))
    ['drdsl', 'etherwake']

At that point we must have a bunch of directories in the upload base
directory named upload-XXXXXX, as would result from several FTP
sessions.  Below we ensure that, and also that the content of these
files match the uploaded ones.

    >>> import hashlib
    >>> def get_md5(filename):
    ...     with open(filename, "rb") as f:
    ...         return hashlib.md5(f.read()).digest()
    ...

    >>> def get_upload_dir(num, dir=incoming_dir):
    ...     """Return the path to the upload, if found in the dir."""
    ...     for upload_entry in os.scandir(dir):
    ...         if upload_entry.name.endswith("%06d" % num):
    ...             return upload_entry.path
    ...     return None
    ...

    >>> def find_upload_dir(num):
    ...     """Return a tuple (result, path) for the numbered upload."""
    ...     for name, dir in (
    ...         ("incoming", incoming_dir),
    ...         ("accepted", accepted_dir),
    ...         ("rejected", rejected_dir),
    ...         ("failed", failed_dir),
    ...     ):
    ...         result = get_upload_dir(num, dir)
    ...         if result is not None:
    ...             return (name, result)
    ...     return (None, None)
    ...

    >>> def find_upload_dir_result(num):
    ...     """Return the result for the numbered upload."""
    ...     return find_upload_dir(num)[0]
    ...

    >>> def find_upload_dir_path(num):
    ...     """Return the path of the numbered upload."""
    ...     return find_upload_dir(num)[1]
    ...

    >>> for i, sent_filenames in enumerate(uploads):
    ...     upload_dir = get_upload_dir(i + 1)
    ...     distro_upload_dir = os.path.join(upload_dir, "ubuntutest")
    ...     assert len(os.listdir(distro_upload_dir)) == len(sent_filenames)
    ...     for filename in sent_filenames:
    ...         upload_filename = os.path.join(
    ...             distro_upload_dir, os.path.basename(filename)
    ...         )
    ...         assert os.path.isfile(upload_filename)
    ...         assert get_md5(filename) == get_md5(upload_filename)
    ...

Finally, we'll just create an entirely empty upload folder. We rely for
our tests on a txpkgupload-like naming system, ie. that the upload folder
end with 000004 (being our fourth upload).

    >>> os.mkdir("%s/fake_upload_000004" % incoming_dir)


Processing Uploads
------------------

Before asking the system to process the upload, we must prepare the
database to receive it. This consists mainly of adding the katie
user, since that's the email used in the Changed-By field for the
.changes files we are going to process, and the ftpmaster@canonical.com
GPG key, since that's the one used to sign the .changes file.

We don't have to check the .dsc file, since we're using the 'sync'
policy in process-upload.py.

# XXX: gustavo 2005-12-10
#     It might be interesting to move these entries into the sample data
#     rather than leaving it here. On the other hand, it's nice to have
#     it here as we have a good reference of what the uploading
#     procedure depends upon.

So, load the GPG key:

    >>> from zope.component import getUtility
    >>> from lp.services.gpg.interfaces import IGPGHandler
    >>> from lp.testing.gpgkeys import gpgkeysdir
    >>> gpg_handler = getUtility(IGPGHandler)
    >>> key_path = os.path.join(gpgkeysdir, "ftpmaster@canonical.com.pub")
    >>> with open(key_path, "rb") as key_file:
    ...     key_data = key_file.read()
    ...
    >>> key = gpg_handler.importPublicKey(key_data)
    >>> assert key is not None
    >>> print(key.fingerprint)
    33C0A61893A5DC5EB325B29E415A12CAC2F30234


Create the katie user and register it in a team that is allowed to
do uploads:

    >>> from lp.services.identity.interfaces.emailaddress import (
    ...     IEmailAddressSet,
    ... )
    >>> from lp.registry.interfaces.gpg import IGPGKeySet
    >>> from lp.registry.interfaces.person import (
    ...     IPersonSet,
    ...     PersonCreationRationale,
    ... )
    >>> name, address = "Katie", "katie@rockhopper.ubuntu.com"
    >>> user = getUtility(IPersonSet).ensurePerson(
    ...     address, name, PersonCreationRationale.OWNER_CREATED_LAUNCHPAD
    ... )
    >>> assert user is not None
    >>> email = getUtility(IEmailAddressSet).getByEmail(address)
    >>> user.validateAndEnsurePreferredEmail(email)

    >>> uploader_team = getUtility(IPersonSet).getByName("ubuntu-team")
    >>> assert uploader_team is not None

    >>> login("foo.bar@canonical.com")
    >>> unused = uploader_team.addMember(
    ...     user, reviewer=uploader_team.teamowner
    ... )
    >>> login("test@canonical.com")


Assign the loaded GPG key to the katie user.

    >>> key_set = getUtility(IGPGKeySet)
    >>> user_key = key_set.new(
    ...     ownerID=user.id,
    ...     keyid=key.keyid,
    ...     fingerprint=key.fingerprint,
    ...     algorithm=key.algorithm,
    ...     keysize=key.keysize,
    ...     can_encrypt=key.can_encrypt,
    ...     active=True,
    ... )


Now we want to turn on the test key server to provide the key we
just imported. Remember that process-upload.py is running as
a different process.

    >>> from lp.testing.keyserver import KeyServerTac
    >>> keyserver = KeyServerTac()
    >>> keyserver.setUp()


Include non-free in the database. This will be done by the
NascentUpload in the 'sync' policy in the future.

    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> component_set = getUtility(IComponentSet)
    >>> non_free = component_set.new("non-free")
    >>> non_free_firmware = component_set.new("non-free-firmware")
    >>> contrib = component_set.new("contrib")
    >>> import transaction
    >>> transaction.commit()

Now we are ready to process the uploaded packages.
This is done by running process-upload.py on each upload directory.

    >>> import subprocess
    >>> script = os.path.join(config.root, "scripts/process-upload.py")

First, we will test process-upload's -J option, which limits which uploads
should be processed. We'll do this by locating and uploading initially
just upload number 1.

    >>> upload_dir_1_path = get_upload_dir(1)
    >>> upload_dir_1_name = os.path.basename(upload_dir_1_path)
    >>> process = subprocess.Popen(
    ...     [
    ...         script,
    ...         "--no-mails",
    ...         "-vv",
    ...         "-C",
    ...         "sync",
    ...         "-J",
    ...         upload_dir_1_name,
    ...         temp_dir,
    ...     ],
    ...     stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE,
    ...     universal_newlines=True,
    ... )
    >>> stdout, stderr = process.communicate()
    >>> process.returncode
    0

Check the four uploads are all where we expect - number 1 in rejected,
the other three still in incoming.

    >>> for i in range(4):
    ...     print(find_upload_dir_result(i + 1))
    ...
    rejected
    incoming
    incoming
    incoming


Now continue with the real upload.

    >>> process = subprocess.Popen(
    ...     [
    ...         script,
    ...         "--no-mails",
    ...         "-vv",
    ...         "-C",
    ...         "sync",
    ...         temp_dir,
    ...     ],
    ...     stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE,
    ...     universal_newlines=True,
    ... )

    >>> stdout, stderr = process.communicate()
    >>> if process.returncode != 0:
    ...     print(stdout)
    ...     print(stderr)
    ...


Let's check if packages were uploaded correctly.

    >>> from operator import attrgetter
    >>> from lp.registry.model.sourcepackagename import SourcePackageName
    >>> from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
    >>> spn = SourcePackageName.selectOneBy(name="drdsl")
    >>> print(spn.name)
    drdsl
    >>> spr = SourcePackageRelease.selectOneBy(sourcepackagenameID=spn.id)
    >>> print(spr.title)
    drdsl - 1.2.0-0ubuntu1
    >>> print(spr.name)
    drdsl
    >>> print(spr.version)
    1.2.0-0ubuntu1
    >>> print(spr.component.name)
    multiverse
    >>> print(spr.section.name)
    comm
    >>> print(spr.maintainer.displayname)
    Matthias Klose
    >>> for sprf in sorted(spr.files, key=attrgetter("libraryfile.filename")):
    ...     print(sprf.libraryfile.filename)
    ...
    drdsl_1.2.0-0ubuntu1.diff.gz
    drdsl_1.2.0-0ubuntu1.dsc
    drdsl_1.2.0.orig.tar.gz
    >>> spr.format.name
    'DPKG'
    >>> spr.urgency.name
    'LOW'
    >>> print(spr.upload_distroseries.name)
    breezy-autotest


Same thing for etherwake:

    >>> spn = SourcePackageName.selectOneBy(name="etherwake")
    >>> print(spn.name)
    etherwake
    >>> spr = SourcePackageRelease.selectOneBy(sourcepackagenameID=spn.id)
    >>> print(spr.title)
    etherwake - 1.08-1
    >>> print(spr.name)
    etherwake
    >>> print(spr.version)
    1.08-1
    >>> print(spr.component.name)
    universe
    >>> print(spr.section.name)
    net
    >>> print(spr.maintainer.displayname)
    Alain Schroeder
    >>> for sprf in sorted(spr.files, key=attrgetter("libraryfile.filename")):
    ...     print(sprf.libraryfile.filename)
    ...
    etherwake_1.08-1.diff.gz
    etherwake_1.08-1.dsc
    etherwake_1.08.orig.tar.gz
    >>> spr.format.name
    'DPKG'
    >>> spr.urgency.name
    'LOW'
    >>> print(spr.upload_distroseries.name)
    breezy-autotest


Check the four uploads all ended up where we expected.

    >>> for i in range(0, 4):
    ...     print(find_upload_dir_result(i + 1))
    ...
    rejected
    None
    None
    failed

Also check the upload folders contain all the files we uploaded.

# XXX cprov 2006-12-06: hardcoded 'ubuntutest' directory is a hack see
# above around line 313.

    >>> for i, sent_filenames in enumerate(uploads):
    ...     upload_dir = find_upload_dir_path(i + 1)
    ...     if upload_dir is None:
    ...         continue
    ...     distro_upload_dir = os.path.join(upload_dir, "ubuntutest")
    ...     assert len(os.listdir(distro_upload_dir)) == len(sent_filenames)
    ...     for filename in sent_filenames:
    ...         upload_filename = os.path.join(
    ...             distro_upload_dir, os.path.basename(filename)
    ...         )
    ...         assert os.path.isfile(upload_filename)
    ...         assert get_md5(filename) == get_md5(upload_filename)
    ...


Now let's see if all of the valid uploads are in the Upload queue marked
as NEW and RELEASE.

    >>> from lp.services.database.interfaces import IStore
    >>> from lp.soyuz.model.queue import PackageUploadSource
    >>> for name in package_names:
    ...     print(name)
    ...     spn = SourcePackageName.selectOneBy(name=name)
    ...     spr = SourcePackageRelease.selectOneBy(sourcepackagenameID=spn.id)
    ...     us = (
    ...         IStore(PackageUploadSource)
    ...         .find(PackageUploadSource, sourcepackagerelease=spr)
    ...         .one()
    ...     )
    ...     assert us.packageupload.status.name == "NEW"
    ...     assert us.packageupload.pocket.name == "RELEASE"
    ...
    drdsl
    etherwake


Processing NEW Items
----------------------

The processing of NEW-queue-entries checks the integrity of uploads
candidates and promote them to ACCEPTED, the failures are kept
as NEW

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.soyuz.enums import PackageUploadStatus
    >>> from lp.soyuz.interfaces.queue import QueueInconsistentStateError

Since we landed correct security adapters for Upload,
we need to perform further actions logged in as an admins, which have
launchpad.Edit on the records:

    >>> from lp.testing import login
    >>> login("foo.bar@canonical.com")

    >>> distro = getUtility(IDistributionSet).getByName("ubuntutest")
    >>> series = distro["breezy-autotest"]

We use getPackageUploads to inspect the current NEW queue and accept items.

    >>> queue_items = series.getPackageUploads(status=PackageUploadStatus.NEW)
    >>> L = []
    >>> for queue_item in queue_items:
    ...     try:
    ...         queue_item.setAccepted()
    ...     except QueueInconsistentStateError as e:
    ...         L.append("%s %s" % (queue_item.sourcepackagerelease.name, e))
    ...     else:
    ...         L.append(
    ...             "%s %s"
    ...             % (queue_item.sourcepackagerelease.name, "ACCEPTED")
    ...         )
    ...
    >>> L.sort()
    >>> print("\n".join(L))
    drdsl ACCEPTED
    etherwake ACCEPTED

Now we process the accepted queue items, one more time.

    >>> transaction.commit()
    >>> script = os.path.join(config.root, "scripts", "process-accepted.py")
    >>> process = subprocess.Popen([script, "-d", "ubuntutest", "-q"])
    >>> process.wait()
    0

These packages must now be in the publishing history. Let's check it.

    >>> from lp.soyuz.model.publishing import (
    ...     SourcePackagePublishingHistory as SSPPH,
    ... )
    >>> package_names.sort()
    >>> for name in package_names:
    ...     spn = SourcePackageName.selectOneBy(name=name)
    ...     spr = SourcePackageRelease.selectOneBy(sourcepackagenameID=spn.id)
    ...     sspph = SSPPH.selectOneBy(sourcepackagereleaseID=spr.id)
    ...     if sspph:
    ...         print(name, sspph.status.title)
    ...     else:
    ...         print(name, "not Published")
    ...
    drdsl Pending
    etherwake Pending


Invoke Publisher script against the 'ubuntutest' distribution:

    >>> script = os.path.join(config.root, "scripts", "publish-distro.py")
    >>> process = subprocess.Popen(
    ...     [script, "-vvCq", "-d", "ubuntutest"],
    ...     stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE,
    ...     universal_newlines=True,
    ... )
    >>> stdout, stderr = process.communicate()
    >>> print(stdout)
    <BLANKLINE>

    >>> transaction.commit()

Check if the 'etherwake' source package was correctly published and is
in the filesystem archive, we are looking for the DSC, the gzipped
original source and the gzipped package diff:

    >>> len(
    ...     os.listdir(
    ...         "/var/tmp/archive/ubuntutest/pool/universe/e/etherwake"
    ...     )
    ... )
    3

Define a helper for pretty-printing Deb822 objects, based on Deb822.dump but
with sorted output.

    >>> def pprint_deb822(deb822):
    ...     for key in sorted(deb822):
    ...         value = deb822.get_as_string(key)
    ...         if not value or value[0] == "\n":
    ...             print("%s:%s" % (key, value))
    ...         else:
    ...             print("%s: %s" % (key, value))
    ...     print()
    ...

Check the generation of a correct Sources tag file for the main
component of ubuntutest/breezy-autotest, containing the only the
required entry for 'etherwake':

    >>> import gzip
    >>> from debian.deb822 import Sources

    >>> with gzip.open(
    ...     "/var/tmp/archive/ubuntutest/dists/breezy-autotest/universe/"
    ...     "source/Sources.gz"
    ... ) as sources_file:
    ...     for source in Sources.iter_paragraphs(sources_file):
    ...         pprint_deb822(source)
    ...     print("END")
    ... # noqa
    Architecture: any
    Binary: etherwake
    Build-Depends: debhelper (>> 2.0)
    Checksums-Sha1:
     2ddcdc87ab3dc35d5ce8232b0cc76bad8242725f 566 etherwake_1.08-1.dsc
     4d8aa805cf262a613a48597e3638054dae421048 4455 etherwake_1.08.orig.tar.gz
     f0ec9827c3ce66c0e1ea2c2f100ec144cb26b264 4145 etherwake_1.08-1.diff.gz
    Checksums-Sha256:
     0077eb18c0c02e931021e523ae3ae307731726f7b00736f66139fffa7181a915 566 etherwake_1.08-1.dsc
     e309f8a45cab2d9a955efee5423b052bc040df1e9a9b85893682ab8647264495 4455 etherwake_1.08.orig.tar.gz
     330e7f515d2da923d83131a1fbb5868adc4633e98a35d7b0e1787da46b63ffac 4145 etherwake_1.08-1.diff.gz
    Checksums-Sha512:
     51216a36b2ab6fde6ae04d5bcb0b7cefa9a18eb4b2b11552ca8f3abde928159e93729f30c6079e913078e966817368a6095de2cb4239676a3d6ed5d49d9de699 566 etherwake_1.08-1.dsc
     6ab88a579ae3fdbbe0f1904712a3a42fab98fa586c3718243d2380f3cb021158c228312001b0685a77dc7171b0307d591ad971a82cd1ccd3511135b23d95ee21 4455 etherwake_1.08.orig.tar.gz
     814074aa8349936fbec84b3ee703788159a085f0ce4a5e35d2dbef617e1c3c6e60818d155772d47b58e0823ed4bc9af29136f64eac8d643a833660e537145cb1 4145 etherwake_1.08-1.diff.gz
    Directory: pool/universe/e/etherwake
    Files:
     f13711c5b8261fbb77b43ae0e8ba9360 566 etherwake_1.08-1.dsc
     c2dc10f98bac012b900fd0b46721fc80 4455 etherwake_1.08.orig.tar.gz
     95c1e89e3ad7bc8740793bdf7aeb7334 4145 etherwake_1.08-1.diff.gz
    Format: 1.0
    Maintainer: Alain Schroeder <...@...org>
    Package: etherwake
    Section: universe/net
    Standards-Version: 3.5.10.0
    Version: 1.08-1
    <BLANKLINE>
    END

Now we invoke changeOverride on just published etherwake, moving it to
component 'multiverse'.

    >>> ubuntutest = getUtility(IDistributionSet)["ubuntutest"]
    >>> breezy_autotest = ubuntutest["breezy-autotest"]
    >>> etherwake = breezy_autotest.getSourcePackage("etherwake")
    >>> etherwake_drspr = etherwake.currentrelease
    >>> override = etherwake_drspr.publishing_history.first().changeOverride(
    ...     new_component=getUtility(IComponentSet)["multiverse"]
    ... )

Check if we have new pending publishing record as expected

    >>> for pub in SSPPH.selectBy(
    ...     sourcepackagereleaseID=etherwake_drspr.sourcepackagerelease.id,
    ...     orderBy=["id"],
    ... ):
    ...     print(pub.status.name, pub.component.name, pub.pocket.name)
    PUBLISHED universe RELEASE
    PENDING multiverse RELEASE

Force database changes, so they can be used by the external script properly.

    >>> transaction.commit()

Invoke Publisher script again to land our changes in the archive

    >>> script = os.path.join(config.root, "scripts", "publish-distro.py")
    >>> process = subprocess.Popen(
    ...     [script, "-vvCq", "-d", "ubuntutest"],
    ...     stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE,
    ...     universal_newlines=True,
    ... )
    >>> stdout, stderr = process.communicate()
    >>> process.returncode
    0

Check careful publishing took place, as requested with -C. In careful
publishing mode, publish-distro will attempt to publish files which are
already marked as published in the database and, if the files are
already on disk, verify the contents are as expected.

Check the publishing history again

    >>> for pub in SSPPH.selectBy(
    ...     sourcepackagereleaseID=etherwake_drspr.sourcepackagerelease.id,
    ...     orderBy=["id"],
    ... ):
    ...     print(pub.status.name, pub.component.name, pub.pocket.name)
    SUPERSEDED universe RELEASE
    PUBLISHED multiverse RELEASE

Check if the package was moved properly to the component 'multiverse':

    >>> with gzip.open(
    ...     "/var/tmp/archive/ubuntutest/dists/breezy-autotest"
    ...     "/main/source/Sources.gz"
    ... ) as f:
    ...     main_sources = six.ensure_text(f.read())
    >>> print(main_sources + "\nEND")
    <BLANKLINE>
    END

    >>> with gzip.open(
    ...     "/var/tmp/archive/ubuntutest/dists/breezy-autotest"
    ...     "/multiverse/source/Sources.gz"
    ... ) as f:
    ...     multiverse_sources = six.ensure_text(f.read())
    >>> print(multiverse_sources + "\nEND")
    Package: drdsl
    ...
    Package: etherwake
    ...
    END

Release File
------------

The publish-distro.py script will write an appropriate Release file
containing the suite in question and a list of checksums (MD5, SHA1
and SHA256) for each index published.

# XXX cprov 2006-12-13: trailing space on Architectures is a side-effect
# caused by the absence of published binaries in this suite. It should
# no happen in real conditions.

    >>> with open(
    ...     "/var/tmp/archive/ubuntutest/dists/" "breezy-autotest/Release"
    ... ) as f:
    ...     releasefile_contents = f.read()
    >>> print(releasefile_contents + "\nEND")
    ... # noqa
    ... # doctest: -NORMALIZE_WHITESPACE
    Origin: ubuntutest
    Label: ubuntutest
    Suite: breezy-autotest
    Version: 6.6.6
    Codename: breezy-autotest
    Date: ...
    Architectures:
    Components: main restricted universe multiverse
    Description: ubuntutest Breezy Badger Autotest 6.6.6
    MD5Sum:
     a5e5742a193740f17705c998206e18b6              114 main/source/Release
    ...
    SHA1:
     6222b7e616bcc20a32ec227254ad9de8d4bd5557              114 main/source/Release
    ...
    SHA256:
     297125e9b0f5da85552691597c9c4920aafd187e18a4e01d2ba70d8d106a6338              114 main/source/Release
    ...
    END


Nice! That's enough for now.. let's kill the process and clean
everything up.

    >>> import shutil
    >>> shutil.rmtree(temp_dir)

Remove the test archive from filesystem.

    >>> shutil.rmtree("/var/tmp/archive/")
    >>> keyserver.tearDown()


Feito! ;-)


vim:ft=doctest:ts=4:sw=4:et
