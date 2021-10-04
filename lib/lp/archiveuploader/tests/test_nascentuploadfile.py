# Copyright 2010-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test NascentUploadFile functionality."""

from functools import partial
import gzip
import hashlib
import io
import lzma
import os
import subprocess
import tarfile
from unittest import mock

from debian.deb822 import (
    Changes,
    Deb822,
    Dsc,
    )
import six
from testtools.matchers import (
    Contains,
    Equals,
    MatchesAny,
    MatchesListwise,
    MatchesRegex,
    MatchesSetwise,
    MatchesStructure,
    )

from lp.archiveuploader.changesfile import ChangesFile
from lp.archiveuploader.dscfile import DSCFile
from lp.archiveuploader.nascentuploadfile import (
    CustomUploadFile,
    DebBinaryUploadFile,
    NascentUploadFile,
    UploadError,
    )
from lp.archiveuploader.tests import AbsolutelyAnythingGoesUploadPolicy
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.log.logger import BufferLogger
from lp.services.osutils import write_file
from lp.soyuz.enums import (
    BinarySourceReferenceType,
    PackagePublishingStatus,
    PackageUploadCustomFormat,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )


class NascentUploadFileTestCase(TestCaseWithFactory):
    """Base class for all tests of classes deriving from NascentUploadFile."""

    def setUp(self):
        super(NascentUploadFileTestCase, self).setUp()
        self.logger = BufferLogger()
        self.policy = AbsolutelyAnythingGoesUploadPolicy()
        self.distro = self.factory.makeDistribution()
        self.policy.pocket = PackagePublishingPocket.RELEASE
        self.policy.archive = self.factory.makeArchive(
            distribution=self.distro)

    def writeUploadFile(self, filename, contents):
        """Write a temporary file but with a specific filename.

        :param filename: Filename to use
        :param contents: Contents of the file
        :return: Tuple with path, md5 and size
        """
        path = os.path.join(self.makeTemporaryDirectory(), filename)
        with open(path, 'wb') as f:
            f.write(contents)
        return (
            path, hashlib.md5(contents).hexdigest(),
            hashlib.sha1(contents).hexdigest(), len(contents))


class TestNascentUploadFile(NascentUploadFileTestCase):

    layer = ZopelessDatabaseLayer

    def test_checkSizeAndCheckSum_validates_size(self):
        (path, md5, sha1, size) = self.writeUploadFile('foo', b'bar')
        nuf = NascentUploadFile(
            path, dict(MD5=md5), size - 1, 'main/devel', None, None, None)
        self.assertRaisesWithContent(
            UploadError,
            'File foo mentioned in the changes has a size mismatch. 3 != 2',
            nuf.checkSizeAndCheckSum)

    def test_checkSizeAndCheckSum_validates_md5(self):
        (path, md5, sha1, size) = self.writeUploadFile('foo', b'bar')
        nuf = NascentUploadFile(
            path, dict(MD5='deadbeef'), size, 'main/devel', None, None, None)
        self.assertRaisesWithContent(
            UploadError,
            'File foo mentioned in the changes has a MD5 mismatch. '
            '37b51d194a7513e45b56f6524f2d51f2 != deadbeef',
            nuf.checkSizeAndCheckSum)

    def test_checkSizeAndCheckSum_validates_sha1(self):
        (path, md5, sha1, size) = self.writeUploadFile('foo', b'bar')
        nuf = NascentUploadFile(
            path, dict(MD5=md5, SHA1='foobar'), size, 'main/devel', None,
            None, None)
        self.assertRaisesWithContent(
            UploadError,
            'File foo mentioned in the changes has a SHA1 mismatch. '
            '62cdb7020ff920e5aa642c3d4066950dd1f01f4d != foobar',
            nuf.checkSizeAndCheckSum)


class CustomUploadFileTests(NascentUploadFileTestCase):
    """Tests for CustomUploadFile."""

    layer = LaunchpadZopelessLayer

    def createCustomUploadFile(self, filename, contents,
                               component_and_section, priority_name):
        """Simple wrapper to create a CustomUploadFile."""
        (path, md5, sha1, size) = self.writeUploadFile(filename, contents)
        uploadfile = CustomUploadFile(
            path, dict(MD5=md5), size, component_and_section, priority_name,
            self.policy, self.logger)
        return uploadfile

    def test_custom_type(self):
        # The mime type gets set according to PackageUploadCustomFormat.
        uploadfile = self.createCustomUploadFile(
            "bla.txt", b"data", "main/raw-installer", "extra")
        self.assertEqual(
            PackageUploadCustomFormat.DEBIAN_INSTALLER,
            uploadfile.custom_type)

    def test_storeInDatabase(self):
        # storeInDatabase creates a library file.
        uploadfile = self.createCustomUploadFile(
            "bla.txt", b"data", "main/raw-installer", "extra")
        self.assertEqual("application/octet-stream", uploadfile.content_type)
        libraryfile = uploadfile.storeInDatabase()
        self.assertEqual("bla.txt", libraryfile.filename)
        self.assertEqual("application/octet-stream", libraryfile.mimetype)

    def test_debian_installer_verify(self):
        # debian-installer uploads are required to have sensible filenames.
        uploadfile = self.createCustomUploadFile(
            "debian-installer-images_20120627_i386.tar.gz", b"data",
            "main/raw-installer", "extra")
        self.assertEqual([], list(uploadfile.verify()))
        uploadfile = self.createCustomUploadFile(
            "bla.txt", b"data", "main/raw-installer", "extra")
        errors = list(uploadfile.verify())
        self.assertEqual(1, len(errors))
        self.assertIsInstance(errors[0], UploadError)

    def test_no_handler_no_verify(self):
        # Uploads without special handlers have no filename checks.
        uploadfile = self.createCustomUploadFile(
            "bla.txt", b"data", "main/raw-meta-data", "extra")
        self.assertEqual([], list(uploadfile.verify()))

    def test_debian_installer_auto_approved(self):
        # debian-installer uploads are auto-approved.
        uploadfile = self.createCustomUploadFile(
            "bla.txt", b"data", "main/raw-installer", "extra")
        self.assertTrue(uploadfile.autoApprove())

    def test_uefi_not_auto_approved(self):
        # UEFI uploads are auto-approved.
        uploadfile = self.createCustomUploadFile(
            "bla.txt", b"data", "main/raw-uefi", "extra")
        self.assertFalse(uploadfile.autoApprove())

    def test_signing_not_auto_approved(self):
        # UEFI uploads are auto-approved.
        uploadfile = self.createCustomUploadFile(
            "bla.txt", b"data", "main/raw-signing", "extra")
        self.assertFalse(uploadfile.autoApprove())


class PackageUploadFileTestCase(NascentUploadFileTestCase):
    """Base class for all tests of classes deriving from PackageUploadFile."""

    def setUp(self):
        super(PackageUploadFileTestCase, self).setUp()
        self.policy.distroseries = self.factory.makeDistroSeries(
            distribution=self.distro)

    def getBaseChanges(self):
        contents = Changes()
        contents["Source"] = "mypkg"
        contents["Binary"] = "binary"
        contents["Architecture"] = "i386"
        contents["Version"] = "0.1"
        contents["Distribution"] = "nifty"
        contents["Description"] = "\n Foo"
        contents["Maintainer"] = "Somebody"
        contents["Changes"] = "Something changed"
        contents["Date"] = "Fri, 25 Jun 2010 11:20:22 -0600"
        contents["Urgency"] = "low"
        contents["Changed-By"] = "Seombody Else <somebody@example.com>"
        contents["Files"] = [{
            "md5sum": "d2bd347b3fed184fe28e112695be491c",
            "size": "1791",
            "section": "python",
            "priority": "optional",
            "name": "dulwich_0.4.1-1.dsc"}]
        return contents

    def createChangesFile(self, filename, changes):
        tempdir = self.makeTemporaryDirectory()
        path = os.path.join(tempdir, filename)
        with open(path, "wb") as changes_fd:
            changes.dump(changes_fd)
        changesfile = ChangesFile(path, self.policy, self.logger)
        self.assertEqual([], list(changesfile.parseChanges()))
        return changesfile


class DSCFileTests(PackageUploadFileTestCase):
    """Tests for DSCFile."""

    layer = LaunchpadZopelessLayer

    def getBaseDsc(self):
        dsc = Dsc()
        dsc["Architecture"] = "all"
        dsc["Version"] = "0.42"
        dsc["Source"] = "dulwich"
        dsc["Binary"] = "python-dulwich"
        dsc["Standards-Version"] = "0.2.2"
        dsc["Maintainer"] = "Jelmer Vernooij <jelmer@ubuntu.com>"
        dsc["Files"] = [{
            "md5sum": "5e8ba79b4074e2f305ddeaf2543afe83",
            "size": "182280",
            "name": "dulwich_0.42.tar.gz"}]
        return dsc

    def createDSCFile(self, filename, dsc, component_and_section,
                      priority_name, package, version, changes):
        (path, md5, sha1, size) = self.writeUploadFile(
            filename, dsc.dump().encode("UTF-8"))
        if changes:
            self.assertEqual([], list(changes.processAddresses()))
        return DSCFile(
            path, dict(MD5=md5), size, component_and_section, priority_name,
            package, version, changes, self.policy, self.logger)

    def test_filetype(self):
        # The filetype attribute is set based on the file extension.
        dsc = self.getBaseDsc()
        uploadfile = self.createDSCFile(
            "foo.dsc", dsc, "main/net", "extra", "dulwich", "0.42", None)
        self.assertEqual(
            "text/x-debian-source-package", uploadfile.content_type)

    def test_storeInDatabase(self):
        # storeInDatabase creates a SourcePackageRelease.
        dsc = self.getBaseDsc()
        dsc["Build-Depends"] = "dpkg, bzr"
        changes = self.getBaseChanges()
        uploadfile = self.createDSCFile(
            "foo.dsc", dsc, "main/net", "extra", "dulwich", "0.42",
            self.createChangesFile("foo.changes", changes))
        uploadfile.changelog = b"DUMMY"
        uploadfile.files = []
        release = uploadfile.storeInDatabase(None)
        self.assertEqual("0.42", release.version)
        self.assertEqual("dpkg, bzr", release.builddepends)

    def test_storeInDatabase_case_sensitivity(self):
        # storeInDatabase supports field names with different cases,
        # confirming to Debian policy.
        dsc = self.getBaseDsc()
        dsc["buIld-depends"] = "dpkg, bzr"
        changes = self.getBaseChanges()
        uploadfile = self.createDSCFile(
            "foo.dsc", dsc, "main/net", "extra", "dulwich", "0.42",
            self.createChangesFile("foo.changes", changes))
        uploadfile.files = []
        uploadfile.changelog = b"DUMMY"
        release = uploadfile.storeInDatabase(None)
        self.assertEqual("dpkg, bzr", release.builddepends)

    def test_user_defined_fields(self):
        # storeInDatabase updates user_defined_fields.
        dsc = self.getBaseDsc()
        dsc["Python-Version"] = "2.5"
        changes = self.getBaseChanges()
        uploadfile = self.createDSCFile(
            "foo.dsc", dsc, "main/net", "extra", "dulwich", "0.42",
            self.createChangesFile("foo.changes", changes))
        uploadfile.changelog = b"DUMMY"
        uploadfile.files = []
        release = uploadfile.storeInDatabase(None)
        # DSCFile lowercases the field names
        self.assertEqual(
            [["Python-Version", u"2.5"]], release.user_defined_fields)

    def test_homepage(self):
        # storeInDatabase updates homepage.
        dsc = self.getBaseDsc()
        dsc["Homepage"] = "http://samba.org/~jelmer/bzr"
        changes = self.getBaseChanges()
        uploadfile = self.createDSCFile(
            "foo.dsc", dsc, "main/net", "extra", "dulwich", "0.42",
            self.createChangesFile("foo.changes", changes))
        uploadfile.changelog = b"DUMMY"
        uploadfile.files = []
        release = uploadfile.storeInDatabase(None)
        self.assertEqual(u"http://samba.org/~jelmer/bzr", release.homepage)

    def test_checkBuild(self):
        # checkBuild() verifies consistency with a build.
        self.policy.distroseries.nominatedarchindep = (
            self.factory.makeDistroArchSeries(
                distroseries=self.policy.distroseries))
        build = self.factory.makeSourcePackageRecipeBuild(
            pocket=self.policy.pocket, distroseries=self.policy.distroseries,
            archive=self.policy.archive)
        dsc = self.getBaseDsc()
        uploadfile = self.createDSCFile(
            "foo.dsc", dsc, "main/net", "extra", "dulwich", "0.42",
            self.createChangesFile("foo.changes", self.getBaseChanges()))
        uploadfile.checkBuild(build)
        # checkBuild() sets the build status to FULLYBUILT and
        # removes the upload log.
        self.assertEqual(BuildStatus.FULLYBUILT, build.status)
        self.assertIs(None, build.upload_log)

    def test_checkBuild_inconsistent(self):
        # checkBuild() raises UploadError if inconsistencies between build
        # and upload file are found.
        distroseries = self.factory.makeDistroSeries()
        distroseries.nominatedarchindep = self.factory.makeDistroArchSeries(
            distroseries=distroseries)
        build = self.factory.makeSourcePackageRecipeBuild(
            pocket=self.policy.pocket, distroseries=distroseries,
            archive=self.policy.archive)
        dsc = self.getBaseDsc()
        uploadfile = self.createDSCFile(
            "foo.dsc", dsc, "main/net", "extra", "dulwich", "0.42",
            self.createChangesFile("foo.changes", self.getBaseChanges()))
        self.assertRaises(UploadError, uploadfile.checkBuild, build)


class DebBinaryUploadFileTests(PackageUploadFileTestCase):
    """Tests for DebBinaryUploadFile."""

    layer = LaunchpadZopelessLayer

    def getBaseControl(self):
        return {
            "Package": b"python-dulwich",
            "Source": b"dulwich",
            "Version": b"0.42",
            "Architecture": b"i386",
            "Maintainer": b"Jelmer Vernooij <jelmer@debian.org>",
            "Installed-Size": b"524",
            "Depends": b"python (<< 2.7), python (>= 2.5)",
            "Provides": b"python2.5-dulwich, python2.6-dulwich",
            "Section": b"python",
            "Priority": b"optional",
            "Homepage": b"http://samba.org/~jelmer/dulwich",
            "Description": b"Pure-python Git library\n"
                b" Dulwich is a Python implementation of the file formats and"
                b" protocols",
            }

    def _writeCompressedFile(self, filename, data):
        if filename.endswith(".gz"):
            open_func = gzip.open
        elif filename.endswith(".xz"):
            open_func = partial(lzma.LZMAFile, format=lzma.FORMAT_XZ)
        else:
            raise ValueError(
                "Unhandled compression extension in '%s'" % filename)
        with open_func(filename, "wb") as f:
            f.write(data)

    def createDeb(self, filename, control, control_format, data_format,
                  members=None):
        """Return the contents of a dummy .deb file."""
        tempdir = self.makeTemporaryDirectory()
        control = {k: six.ensure_text(v) for k, v in control.items()}
        if members is None:
            members = [
                "debian-binary",
                "control.tar.%s" % control_format,
                "data.tar.%s" % data_format,
                ]
        for member in members:
            if member == "debian-binary":
                write_file(os.path.join(tempdir, member), b"2.0\n")
            elif member.startswith("control.tar."):
                with io.BytesIO() as control_tar_buf:
                    with tarfile.open(
                            mode="w", fileobj=control_tar_buf) as control_tar:
                        with io.BytesIO() as control_buf:
                            Deb822(control).dump(
                                fd=control_buf, encoding="UTF-8")
                            control_buf.seek(0)
                            tarinfo = tarfile.TarInfo(name="control")
                            tarinfo.size = len(control_buf.getvalue())
                            control_tar.addfile(tarinfo, fileobj=control_buf)
                    control_tar_bytes = control_tar_buf.getvalue()
                self._writeCompressedFile(
                    os.path.join(tempdir, member), control_tar_bytes)
            elif member.startswith("data.tar."):
                with io.BytesIO() as data_tar_buf:
                    with tarfile.open(mode="w", fileobj=data_tar_buf):
                        pass
                    data_tar_bytes = data_tar_buf.getvalue()
                self._writeCompressedFile(
                    os.path.join(tempdir, member), data_tar_bytes)
            else:
                raise ValueError("Unhandled .deb member '%s'" % member)
        retcode = subprocess.call(
            ["ar", "rc", filename] + members, cwd=tempdir)
        self.assertEqual(0, retcode)
        with open(os.path.join(tempdir, filename), "rb") as f:
            return f.read()

    def createDebBinaryUploadFile(self, filename, component_and_section,
                                  priority_name, package, version, changes,
                                  control=None, control_format=None,
                                  data_format=None, members=None):
        """Create a DebBinaryUploadFile."""
        if (control is not None or control_format is not None or
                data_format is not None or members is not None):
            if control is None:
                control = self.getBaseControl()
            data = self.createDeb(
                filename, control, control_format, data_format,
                members=members)
        else:
            data = b"DUMMY DATA"
        (path, md5, sha1, size) = self.writeUploadFile(filename, data)
        return DebBinaryUploadFile(
            path, dict(MD5=md5), size, component_and_section, priority_name,
            package, version, changes, self.policy, self.logger)

    def test_unknown_priority(self):
        # Unknown priorities automatically get changed to 'extra'.
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/net", "unknown", "mypkg", "0.42", None)
        self.assertEqual("extra", uploadfile.priority_name)

    def test_parseControl(self):
        # parseControl sets various fields on DebBinaryUploadFile.
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None)
        control = self.getBaseControl()
        uploadfile.parseControl(control)
        self.assertEqual("python", uploadfile.section_name)
        self.assertEqual("dulwich", uploadfile.source_name)
        self.assertEqual("0.42", uploadfile.source_version)
        self.assertEqual("0.42", uploadfile.control_version)

    def test_verifyFormat_missing_control(self):
        # verifyFormat rejects .debs with no control member.
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None, members=["debian-binary", "data.tar.gz"])
        self.assertThat(
            ["".join(error.args) for error in uploadfile.verifyFormat()],
            MatchesListwise([
                Equals(
                    "%s: 'dpkg-deb -I' invocation failed." %
                    uploadfile.filename),
                MatchesRegex(
                    r"^ \[dpkg-deb output:\] .* has premature member "
                    r"'data\.tar\.gz'"),
                Equals(
                    "%s: 'dpkg-deb -c' invocation failed." %
                    uploadfile.filename),
                MatchesRegex(
                    r"^ \[dpkg-deb output:\] .* has premature member "
                    r"'data\.tar\.gz'"),
                ]))

    def test_verifyFormat_missing_data(self):
        # verifyFormat rejects .debs with no data member.
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None, members=["debian-binary", "control.tar.gz"])
        self.assertThat(
            ["".join(error.args) for error in uploadfile.verifyFormat()],
            MatchesListwise([
                Equals(
                    "%s: 'dpkg-deb -c' invocation failed." %
                    uploadfile.filename),
                MatchesRegex(
                    r"^ \[dpkg-deb output:\] .* unexpected end of file"),
                ]))

    def test_verifyFormat_control_xz(self):
        # verifyFormat accepts .debs with an xz-compressed control member.
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None, control_format="xz", data_format="gz")
        uploadfile.extractAndParseControl()
        self.assertEqual([], list(uploadfile.verifyFormat()))

    def test_verifyFormat_data_xz(self):
        # verifyFormat accepts .debs with an xz-compressed data member.
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None, control_format="gz", data_format="xz")
        uploadfile.extractAndParseControl()
        self.assertEqual([], list(uploadfile.verifyFormat()))

    @mock.patch("lp.archiveuploader.nascentuploadfile.apt_inst")
    def test_extractAndParseControl_UploadError_message(self, m_apt_inst):
        # extractAndParseControl should yield a reasonable error message if
        # apt_inst.DebFile raises an exception
        m_apt_inst.DebFile.side_effect = KeyError("banana not found")
        uploadfile = self.createDebBinaryUploadFile(
            "empty_0.1_all.deb", "main/admin", "extra", "empty", "0.1", None,
            members=[])
        errors = list(uploadfile.extractAndParseControl())
        self.assertEqual(1, len(errors))
        error = errors[0]
        self.assertIsInstance(error, UploadError)
        self.assertEqual(
            "empty_0.1_all.deb: extracting control file raised "
            "%s: %r. giving up." % (KeyError, "banana not found"), str(error))

    def test_verifyDebTimestamp_SystemError(self):
        # verifyDebTimestamp produces a reasonable error if we provoke a
        # SystemError from apt_inst.DebFile.
        uploadfile = self.createDebBinaryUploadFile(
            "empty_0.1_all.deb", "main/admin", "extra", "empty", "0.1", None,
            members=[])
        self.assertThat(
            ["".join(error.args) for error in uploadfile.verifyDebTimestamp()],
            MatchesListwise([MatchesAny(
                Equals("No debian archive, missing control.tar.gz"),
                Contains("could not locate member control.tar."))]))

    def test_storeInDatabase(self):
        # storeInDatabase creates a BinaryPackageRelease.
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None)
        control = self.getBaseControl()
        uploadfile.parseControl(control)
        build = self.factory.makeBinaryPackageBuild()
        bpr = uploadfile.storeInDatabase(build)
        self.assertEqual(u'python (<< 2.7), python (>= 2.5)', bpr.depends)
        self.assertEqual(
            u" Dulwich is a Python implementation of the file formats and"
            u" protocols", bpr.description)
        self.assertEqual(False, bpr.essential)
        self.assertEqual(524, bpr.installedsize)
        self.assertEqual(True, bpr.architecturespecific)
        self.assertEqual(u"", bpr.recommends)
        self.assertEqual("0.42", bpr.version)

    def test_user_defined_fields(self):
        # storeInDatabase stores user defined fields.
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None)
        control = self.getBaseControl()
        control["Python-Version"] = b"2.5"
        uploadfile.parseControl(control)
        build = self.factory.makeBinaryPackageBuild()
        bpr = uploadfile.storeInDatabase(build)
        self.assertEqual(
            [[u"Python-Version", u"2.5"]], bpr.user_defined_fields)

    def test_user_defined_fields_newlines(self):
        # storeInDatabase stores user defined fields and keeps newlines.
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None)
        control = self.getBaseControl()
        control["RandomData"] = b"Foo\nbar\nbla\n"
        uploadfile.parseControl(control)
        build = self.factory.makeBinaryPackageBuild()
        bpr = uploadfile.storeInDatabase(build)
        self.assertEqual(
            [
                [u"RandomData", u"Foo\nbar\nbla\n"],
            ], bpr.user_defined_fields)

    def test_built_using(self):
        # storeInDatabase parses Built-Using into BinarySourceReference
        # rows, and also adds the unparsed contents to user_defined_fields.
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None)
        control = self.getBaseControl()
        control["Built-Using"] = b"bar (= 0.1)"
        uploadfile.parseControl(control)
        build = self.factory.makeBinaryPackageBuild()
        spph = self.factory.makeSourcePackagePublishingHistory(
            archive=build.archive, distroseries=build.distro_series,
            pocket=build.pocket, sourcepackagename="bar", version="0.1")
        bpr = uploadfile.storeInDatabase(build)
        self.assertThat(
            bpr.built_using_references,
            MatchesSetwise(
                MatchesStructure.byEquality(
                    binary_package_release=bpr,
                    source_package_release=spph.sourcepackagerelease,
                    reference_type=BinarySourceReferenceType.BUILT_USING,
                    )))
        self.assertEqual(
            [[u"Built-Using", u"bar (= 0.1)"]], bpr.user_defined_fields)

    def test_homepage(self):
        # storeInDatabase stores homepage field.
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None)
        control = self.getBaseControl()
        control["Python-Version"] = b"2.5"
        uploadfile.parseControl(control)
        build = self.factory.makeBinaryPackageBuild()
        bpr = uploadfile.storeInDatabase(build)
        self.assertEqual(
            u"http://samba.org/~jelmer/dulwich", bpr.homepage)

    def test_checkBuild(self):
        # checkBuild() verifies consistency with a build.
        das = self.factory.makeDistroArchSeries(
            distroseries=self.policy.distroseries, architecturetag="i386")
        build = self.factory.makeBinaryPackageBuild(
            distroarchseries=das,
            archive=self.policy.archive)
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None)
        uploadfile.checkBuild(build)
        # checkBuild() sets the build status to FULLYBUILT and
        # removes the upload log.
        self.assertEqual(BuildStatus.FULLYBUILT, build.status)
        self.assertIs(None, build.upload_log)

    def test_checkBuild_inconsistent(self):
        # checkBuild() raises UploadError if inconsistencies between build
        # and upload file are found.
        das = self.factory.makeDistroArchSeries(
            distroseries=self.policy.distroseries, architecturetag="amd64")
        build = self.factory.makeBinaryPackageBuild(
            distroarchseries=das,
            archive=self.policy.archive)
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None)
        self.assertRaises(UploadError, uploadfile.checkBuild, build)

    def test_findSourcePackageRelease(self):
        # findSourcePackageRelease finds the matching SourcePackageRelease.
        das = self.factory.makeDistroArchSeries(
            distroseries=self.policy.distroseries, architecturetag="i386")
        self.factory.makeBinaryPackageBuild(
            distroarchseries=das,
            archive=self.policy.archive)
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None)
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.factory.makeSourcePackageName("foo"),
            distroseries=self.policy.distroseries,
            version="0.42", archive=self.policy.archive)
        control = self.getBaseControl()
        control["Source"] = b"foo"
        uploadfile.parseControl(control)
        self.assertEqual(
            spph.sourcepackagerelease, uploadfile.findSourcePackageRelease())

    def test_findSourcePackageRelease_no_spph(self):
        # findSourcePackageRelease raises UploadError if there is no
        # SourcePackageRelease.
        das = self.factory.makeDistroArchSeries(
            distroseries=self.policy.distroseries, architecturetag="i386")
        self.factory.makeBinaryPackageBuild(
            distroarchseries=das,
            archive=self.policy.archive)
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None)
        control = self.getBaseControl()
        control["Source"] = b"foo"
        uploadfile.parseControl(control)
        self.assertRaises(UploadError, uploadfile.findSourcePackageRelease)

    def test_findSourcePackageRelease_multiple_sprs(self):
        # findSourcePackageRelease finds the last uploaded
        # SourcePackageRelease and can deal with multiple pending source
        # package releases.
        das = self.factory.makeDistroArchSeries(
            distroseries=self.policy.distroseries, architecturetag="i386")
        self.factory.makeBinaryPackageBuild(
            distroarchseries=das,
            archive=self.policy.archive)
        uploadfile = self.createDebBinaryUploadFile(
            "foo_0.42_i386.deb", "main/python", "unknown", "mypkg", "0.42",
            None)
        spn = self.factory.makeSourcePackageName("foo")
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=spn,
            distroseries=self.policy.distroseries,
            version="0.42", archive=self.policy.archive,
            status=PackagePublishingStatus.PUBLISHED)
        spph2 = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=spn,
            distroseries=self.policy.distroseries,
            version="0.42", archive=self.policy.archive,
            status=PackagePublishingStatus.PENDING)
        control = self.getBaseControl()
        control["Source"] = b"foo"
        uploadfile.parseControl(control)
        self.assertEqual(
            spph2.sourcepackagerelease, uploadfile.findSourcePackageRelease())
