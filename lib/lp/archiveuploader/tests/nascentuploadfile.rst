NascentUploadFiles
==================

Files related with an Soyuz upload are modelled as:

 * ChangesFile: the upload changesfile;
   * DSCFile: the upload DSC file for source uploads;
     * DSCUploadedFile: used to check consistency of the files
                        mentioned in DSC;
   * SourceUploadFile: source files like ORIG and DIFF;
   * UDebBinaryUploadFile: udeb package file;
   * DebBinaryUploadFile: deb package file;
   * CustomUploadFile: normally a tarball used for custom uploads.

Import the test keys so we have them ready for verification

    >>> from lp.testing.gpgkeys import import_public_test_keys
    >>> import_public_test_keys()

We need to be logged into the security model in order to get any further

    >>> login('foo.bar@canonical.com')
    >>> from lp.archiveuploader.tests import datadir, getPolicy


NascentUploadFile base class
----------------------------

(This base class has many checks in it that are not yet documented here.)

Forbidden character check
.........................
Some characters are forbidden in filenames as per Debian packaging policy, and
this check is performed by the checkNameIsTaintFree() method.  It raises an
UploadError if there is an invalid character found.

Construct the base object with just enough data to do the check:

    >>> from lp.archiveuploader.nascentuploadfile import NascentUploadFile
    >>> upload_file = NascentUploadFile(
    ...     "fake/path/to/file/package-1.1.2-3:0ubuntu4", None, 1,
    ...     "section", None, None, None)

The filename tries to use an epoch in an invalid way:

    >>> upload_file.checkNameIsTaintFree()
    Traceback (most recent call last):
    ...
    lp.archiveuploader.utils.UploadError: Invalid character(s) in filename:
    'package-1.1.2-3:0ubuntu4'.


With a good filename, no exception is raised.

    >>> upload_file = NascentUploadFile(
    ...     "fake/path/to/file/package-1.1.2-1ubuntu1", None, 1,
    ...     "section", None, None, None)

    >>> upload_file.checkNameIsTaintFree()


ChangesFile
-----------

A changesfile contains manifest of what is included (ou should be
considered) for the upload in question.

    >>> modified_insecure_policy = getPolicy(
    ...     name='insecure', distro='ubuntu', distroseries='hoary')

    >>> from lp.archiveuploader.changesfile import ChangesFile
    >>> from lp.services.log.logger import DevNullLogger
    >>> ed_binary_changes = ChangesFile(
    ...     datadir('ed_0.2-20_i386.changes.binary-only'),
    ...     modified_insecure_policy, DevNullLogger())
    >>> len(list(ed_binary_changes.parseChanges()))
    0

    >>> ed_source_changes = ChangesFile(
    ...     datadir('ed_0.2-20_source.changes'),
    ...     modified_insecure_policy, DevNullLogger())
    >>> len(list(ed_source_changes.parseChanges()))
    0

Make sure we are not getting any exceptions due to a malformed changes
file name.

    >>> len(list(ed_binary_changes.checkFileName()))
    0

At this point the changesfile content is already parsed:

    >>> print(ed_binary_changes.source)
    ed

    >>> print(ed_binary_changes.version)
    0.2-20

    >>> for item in ed_binary_changes.architectures:
    ...     print(item)
    i386

    >>> print(ed_binary_changes.suite_name)
    unstable

Push upload targeted suite into policy before the checks, nomally done
by NascentUpload object:

    >>> modified_insecure_policy.setDistroSeriesAndPocket(
    ...      ed_binary_changes.suite_name)


Build contained objects, any error during this process will be stored
in the returned generator. This way all the checks are performed and
we can deal with the errors later:

    >>> errors = ed_binary_changes.processFiles()
    >>> errors
    <generator ...>
    >>> list(errors)
    []

    >>> list(ed_source_changes.processFiles())
    []

At this point we can inspect the list of files contained in the upload.

    >>> for uploaded_file in ed_binary_changes.files:
    ...     print(uploaded_file.filename)
    ed_0.2-20_i386.deb

    >>> for f in ed_binary_changes.binary_package_files:
    ...     print(f.filename)
    ed_0.2-20_i386.deb
    >>> for f in ed_binary_changes.source_package_files:
    ...     print(f.filename)

    >>> for f in ed_source_changes.binary_package_files:
    ...     print(f.filename)
    >>> for f in ed_source_changes.source_package_files:
    ...     print(f.filename)
    ed_0.2-20.dsc
    ed_0.2-20.diff.gz
    ed_0.2.orig.tar.gz

Similar to what we have in 'processFiles' ChangesFile.verify is also
a error generator

    >>> errors = ed_binary_changes.verify()
    >>> len(list(errors))
    0

Make sure malformed changes file names are caught.

We first create a misnamed copy of the changes file.

    >>> import os, shutil
    >>> originalp = datadir('ed_0.2-20_i386.changes.binary-only')
    >>> copyp = datadir('p-m_0.4.12-2~ppa2.changes')
    >>> _ = shutil.copyfile(originalp, copyp)

And then invoke the name check on the changes file with the malformed name.

    >>> wrong_file_name = ChangesFile(
    ...     datadir('p-m_0.4.12-2~ppa2.changes'),
    ...     modified_insecure_policy, DevNullLogger())
    >>> [err] = list(wrong_file_name.checkFileName())
    >>> str(err)
    'p-m_0.4.12-2~ppa2.changes -> inappropriate changesfile name, ...'

Remove the misnamed changes file copy used for testing.

    >>> os.unlink(copyp)


CustomUploadFile identification
...............................

A custom upload is essentially a tarball, so it matches the is_source
regexp, even though it isn't actually a source file:

    >>> from lp.archiveuploader.utils import re_issource
    >>> src_match = re_issource.match('dist-upgrader_1.0.tar.gz')
    >>> print(src_match.group(0))
    dist-upgrader_1.0.tar.gz
    >>> print(src_match.group(1))
    dist-upgrader
    >>> print(src_match.group(2))
    1.0
    >>> print(src_match.group(3))
    tar.gz

That's why we recognize them by identifying a set of custom sections:

 * raw-installer
 * raw-translations
 * raw-dist-upgrader
 * raw-ddtp-tarball

The Changesfile.isCustom receives a 'component_and_section' chunk from
the respective file line in the changesfile and return True if it is
target to a custom section.

We will use the current upload available and test the known
'component_and_section' schemas.

Note that the component_name and section_name are not checked for
sanity, it'll be done later on, this method only checks if the
section_name startswith 'raw-':

    >>> ed_binary_changes.isCustom('foo-bar')
    False
    >>> ed_binary_changes.isCustom('drops/foo-bar')
    False
    >>> ed_binary_changes.isCustom('drops/raw-biscuit')
    True
    >>> ed_binary_changes.isCustom('drops/rawbiscuit')
    False
    >>> ed_binary_changes.isCustom('drops/raw-biscuit/something')
    True
    >>> ed_binary_changes.isCustom('main/raw-installer')
    True
    >>> ed_binary_changes.isCustom('main/law-installer')
    False

See the CustomUploadFile checks below for specific checks on custom
uploads.


ChangesFile Parsing Addresses
.............................

Address parsing is implemented by the SignableTagFile class, which
is base for ChangesFile and DSCFile.

    >>> from lp.archiveuploader.dscfile import SignableTagFile
    >>> sig_file = SignableTagFile()

Note that the policy.{distroseries, pocket} must be already
initialized before issuing any parse request, otherwise we can't
generate proper PERSON_CREATION_RATIONALE_MESSAGES.

    >>> sig_file_policy = getPolicy(name='insecure', distro='ubuntu')
    >>> sig_file_policy.setDistroSeriesAndPocket('hoary')
    >>> sig_file.policy = sig_file_policy

Some fields extracted from the tag_file are required, they are always
present in ChangesFile and DSCFile:

    >>> sig_file._dict = {}
    >>> sig_file._dict['Source'] = 'some-source'
    >>> sig_file._dict['Version'] = '6.6.6'

After initialising sig_file we can parse addresses and look them up in
Launchpad:

    >>> addr = sig_file.parseAddress("Foo Bar <foo.bar@canonical.com>")
    >>> print(addr['person'].displayname)
    Foo Bar
    >>> addr['person'].creation_comment is None
    True

If the address is unparsable, we get an error.

    >>> sig_file.parseAddress("Cannot Parse Me <FOOO>")
    Traceback (most recent call last):
    ...
    lp.archiveuploader.utils.UploadError: Cannot Parse Me <FOOO>: no @ found
    in email address part.

If the email address is not yet registered and policy.create_people is True,
a new Person will be created.

    >>> sig_file.policy.create_people
    True

    >>> addr = sig_file.parseAddress("Baz <baz@canonical.com>")
    >>> addr['person'].creation_rationale.name
    'SOURCEPACKAGEUPLOAD'

    >>> print(addr['person'].creation_comment)
    when the some-source_6.6.6 package was uploaded to hoary/RELEASE

If the use an un-initialized policy to create a launchpad person the
creation_rationale will still be possible, however missing important
information, the upload target:

    >>> sig_file.policy.distroseries = None

    >>> addr = sig_file.parseAddress("Bar <bar@canonical.com>")
    >>> addr['person'].creation_rationale.name
    'SOURCEPACKAGEUPLOAD'

    >>> print(addr['person'].creation_comment)
    when the some-source_6.6.6 package was uploaded to (unknown)

On ChangesFile objects we can have access to the enhanced address_structure
corresponding to the RFC-822 mentioned after performing 'processAddress':

    >>> ed_binary_changes.maintainer is None
    True

    >>> errors = ed_binary_changes.processAddresses()
    >>> len(list(errors))
    0

As we can see, this method also return an error generator.

The built address_structure contains values that will be used during
the upload processing:

    >>> print(ed_binary_changes.maintainer['name'])
    James Troup
    >>> print(ed_binary_changes.maintainer['email'])
    james@nocrew.org
    >>> ed_binary_changes.maintainer['person']
    <Person ...>
    >>> print(ed_binary_changes.maintainer['person'].displayname)
    James Troup


Signature Traces
................

Changes file can be optionally GPG-signed, so ChangesFile has
infrastructure to record this information for later checks with policy
requirements.

The ChangesFile signer IPerson, used to checks upload ACL, normally
know as 'sponsor' or 'mentor':

    >>> print(ed_binary_changes.signer.displayname)
    Foo Bar

The IGPGKey used to sign this ChangesFile:

    >>> print(ed_binary_changes.signingkey.displayname)
    1024D/FD311613D941C6DE55737D310E3498675D147547


DSCFile
-------

DSCFile class models the operations and checks needed for processing
and storing a DSC file in the LP system.

The DSC file itself contains information about what was used to build
the given version of source.

    >>> from lp.archiveuploader.dscfile import (
    ...    DSCFile, DSCUploadedFile)

    >>> ed_source_dsc = DSCFile(
    ...     datadir('ed_0.2-20.dsc'),
    ...     dict(MD5='de8b206f8fc57bd931f6226feac6644a'), 578, 'editors',
    ...     'important', 'ed', '0.2-20', ed_source_changes,
    ...     modified_insecure_policy, DevNullLogger())

    >>> ed_source_dsc
    <lp.archiveuploader.dscfile.DSCFile ...>

So this object is exactly the same than what we already have created
in the ChangesFile instance.

    >>> ed_source_changes.dsc
    <lp.archiveuploader.dscfile.DSCFile ...>

The DSCFile also presents a similar behaviour to access its parsed
contents:

    >>> print(ed_source_dsc.source)
    ed
    >>> print(ed_source_dsc.version)
    0.2-20
    >>> print(ed_source_dsc.architecture)
    any
    >>> print(ed_source_dsc.binary)
    ed

The DSC is GPG-signed most of the time, so we can guarantee who was
the author. The DSCFile class implements the same address parsing
methods found in ChangesFile:

    >>> print(ed_source_dsc.maintainer['person'].displayname)
    James Troup

The DSC signer IPerson:

    >>> print(ed_source_dsc.signer.displayname)
    Foo Bar

The IGPGKey used to sign this DSC, which will be stored as the
ISourcePackageRelease.dscsiginingkey:

    >>> print(ed_source_dsc.signingkey.displayname)
    1024D/340CA3BB270E2716C9EE0B768E7EB7086C64A8C5

A DSCFile provides a verification API similar to what we have in
ChangesFile itself:

    >>> errors = ed_source_dsc.verify()
    >>> errors
    <generator ...>
    >>> len(list(errors))
    0

Apart from other consistency checks, DSCFile is also able to check that
the digest declared in the DSC matches the content of the files on disk:

    >>> ed_broken_dsc = DSCFile(
    ...     datadir('ed_0.2-20.dsc'),
    ...     dict(MD5='e31eeb0b6b3b87e1ea79378df864ffff'), 500, 'editors',
    ...     'important', 'ed', '0.2-20', ed_source_changes,
    ...     modified_insecure_policy, DevNullLogger())

    >>> errors = ed_broken_dsc.verify()
    >>> [str(err) for err in errors]
    ['File ed_0.2-20.dsc mentioned in the changes has a MD5 mismatch.
    de8b206f8fc57bd931f6226feac6644a != e31eeb0b6b3b87e1ea79378df864ffff']

It also verifies the file size when the checksum matches.

    >>> ed_broken_dsc = DSCFile(
    ...     datadir('ed_0.2-20.dsc'),
    ...     dict(MD5='de8b206f8fc57bd931f6226feac6644a'), 500, 'editors',
    ...     'important', 'ed', '0.2-20', ed_source_changes,
    ...     modified_insecure_policy, DevNullLogger())

    >>> errors = ed_broken_dsc.verify()
    >>> [str(err) for err in errors]
    ['File ed_0.2-20.dsc mentioned in the changes has a size mismatch.
    578 != 500']


Sub-DSC files or DSCUploadedFiles
.................................

Sub-DSCFiles are DSCUploadedFile objects.

    >>> ed_source_dsc.files[0]
    <lp.archiveuploader.dscfile.DSCUploadedFile ...>

We can also inspect the list of files declared in this DSC:

    >>> for dsc_file in ed_source_dsc.files:
    ...     print(dsc_file.filename)
    ed_0.2.orig.tar.gz
    ed_0.2-20.diff.gz

The DSCUploadedFile also inherit the ability to verify file sanity:

    >>> ed_broken_dsc_file = DSCUploadedFile(
    ...     datadir('ed_0.2-20.diff.gz'),
    ...     dict(MD5='f9e1e5f13725f581919e9bfd6227ffff'), 500,
    ...     modified_insecure_policy, DevNullLogger())
    >>> errors = ed_broken_dsc_file.verify()
    >>> [str(err) for err in errors]
    ['File ed_0.2-20.diff.gz mentioned in the changes has a MD5 mismatch.
    8343836094fb01ee9b9a1067b23365f1 != f9e1e5f13725f581919e9bfd6227ffff']


DebBinaryUploadFile
-------------------

DebBinaryUploadFile models a binary .deb file.

    >>> from lp.archiveuploader.nascentuploadfile import (
    ...    DebBinaryUploadFile)
    >>> ed_deb_path = datadir('ed_0.2-20_i386.deb')
    >>> ed_binary_deb = DebBinaryUploadFile(
    ...     ed_deb_path, dict(MD5='e31eeb0b6b3b87e1ea79378df864ffff'), 15,
    ...     'main/editors', 'important', 'foo', '1.2', ed_binary_changes,
    ...     modified_insecure_policy, DevNullLogger())

Like the other files it can be verified:

    >>> list(ed_binary_deb.verify())
    []

Verification checks that the specified section matches the section in the
changes file:

    >>> ed_binary_deb = DebBinaryUploadFile(
    ...     ed_deb_path, dict(MD5='e31eeb0b6b3b87e1ea79378df864ffff'), 15,
    ...     'main/net', 'important', 'foo', '1.2', ed_binary_changes,
    ...     modified_insecure_policy, DevNullLogger())
    >>> list(ed_binary_deb.verify())
    [UploadError(...'ed_0.2-20_i386.deb
    control file lists section as main/editors but changes file has
    main/net.'...)]

It also checks the priority against the changes file:

    >>> ed_binary_deb = DebBinaryUploadFile(
    ...     ed_deb_path, dict(MD5='e31eeb0b6b3b87e1ea79378df864ffff'), 15,
    ...     'main/editors', 'extra', 'foo', '1.2', ed_binary_changes,
    ...     modified_insecure_policy, DevNullLogger())
    >>> list(ed_binary_deb.verify())
    [UploadError(...'ed_0.2-20_i386.deb
    control file lists priority as important but changes file has extra.'...)]

The timestamp of the files in the .deb are tested against the policy for
being too new:

    >>> from lp.archiveuploader.uploadpolicy import ArchiveUploadType
    >>> old_only_policy = getPolicy(
    ...     name='insecure', distro='ubuntu', distroseries='hoary')
    >>> old_only_policy.accepted_type = ArchiveUploadType.BINARY_ONLY
    >>> old_only_policy.future_time_grace = -20 * 365 * 24 * 60 * 60

    >>> ed_binary_deb = DebBinaryUploadFile(
    ...     ed_deb_path, dict(MD5='e31eeb0b6b3b87e1ea79378df864ffff'), 15,
    ...     'main/editors', 'important', 'foo', '1.2', ed_binary_changes,
    ...     old_only_policy, DevNullLogger())
    >>> list(ed_binary_deb.verifyDebTimestamp())
    [UploadError(...'ed_0.2-20_i386.deb:
    has 26 file(s) with a time stamp too far into the future
    (e.g. ./ [Thu Jan  3 19:29:00 2008]).'...)]

... as well as for being too old:

    >>> new_only_policy = getPolicy(
    ...     name='insecure', distro='ubuntu', distroseries='hoary')
    >>> new_only_policy.accepted_type = ArchiveUploadType.BINARY_ONLY
    >>> new_only_policy.earliest_year = 2010
    >>> ed_binary_deb = DebBinaryUploadFile(
    ...     ed_deb_path, dict(MD5='e31eeb0b6b3b87e1ea79378df864ffff'), 15,
    ...     'main/editors', 'important', 'foo', '1.2', ed_binary_changes,
    ...     new_only_policy, DevNullLogger())
    >>> list(ed_binary_deb.verify())
    [UploadError(...'ed_0.2-20_i386.deb:
    has 26 file(s) with a time stamp too far in the past
    (e.g. ./ [Thu Jan  3 19:29:00 2008]).'...)]
