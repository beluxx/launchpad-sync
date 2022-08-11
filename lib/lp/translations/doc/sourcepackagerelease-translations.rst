Uploading translations
----------------------

It's time to check the translation upload function.

We need a test tarball uploaded into librarian to run this test. We will
upload the same sampledata tarball twice, one public and one restricted
`LibraryFileAlias` objects.

    >>> import os.path
    >>> import lp.translations
    >>> tarball_path = os.path.join(
    ...     os.path.dirname(lp.translations.__file__),
    ...     'doc/sourcepackagerelease-translations.tar.gz')
    >>> tarball = open(tarball_path, 'rb')
    >>> tarball_size = len(tarball.read())
    >>> _ = tarball.seek(0)

    >>> from lp.services.librarian.interfaces import (
    ...     ILibraryFileAliasSet)
    >>> public_translation = getUtility(ILibraryFileAliasSet).create(
    ...     name='test.tar.gz',
    ...     size=tarball_size,
    ...     file=tarball,
    ...     contentType='application/x-gtar')

    >>> _ = tarball.seek(0)
    >>> restricted_translation = getUtility(ILibraryFileAliasSet).create(
    ...     name='test.tar.gz',
    ...     size=tarball_size,
    ...     file=tarball,
    ...     contentType='application/x-gtar',
    ...     restricted=True)

    >>> tarball.close()

Commit, so uploaded contents are available in the current test.

    >>> transaction.commit()

We will use an arbitrary source package release from the sampledata, and
create a PackageUpload with it.

    >>> from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
    >>> spr_test = SourcePackageRelease.get(20)
    >>> sp_test = spr_test.upload_distroseries.getSourcePackage(
    ...     spr_test.sourcepackagename)
    >>> print(spr_test.title)
    pmount - 0.1-1

    >>> from lp.soyuz.interfaces.packagetranslationsuploadjob import (
    ...     IPackageTranslationsUploadJobSource)
    >>> upload = factory.makePackageUpload(
    ...     distroseries=spr_test.upload_distroseries)
    >>> pus = upload.addSource(spr_test)

Before the final upload, we can see that the translation queue for the
testing source package is empty.

    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue)
    >>> translation_import_queue = getUtility(ITranslationImportQueue)
    >>> translation_import_queue.getAllEntries(target=sp_test).count()
    0

Now we bind both uploaded translations, the public and the restricted
ones, to the testing upload entry, creating an PackageTranslationsUploadJob
for each import.

    >>> importer = factory.makePerson(name="maria")

    >>> job1 = getUtility(IPackageTranslationsUploadJobSource).create(
    ...     upload.distroseries, public_translation,
    ...     spr_test.sourcepackagename, importer)

    >>> job2 = getUtility(IPackageTranslationsUploadJobSource).create(
    ...     upload.distroseries, restricted_translation,
    ...     spr_test.sourcepackagename, importer)

    >>> job1.run()
    >>> job2.run()

And the queue should have 2 entries, with exactly the same contents.

    >>> queue_entries = translation_import_queue.getAllEntries(target=sp_test)

    >>> queue_entries.count()
    1

    >>> for entry in queue_entries:
    ...     print(entry.path, entry.importer.name)
    po/es.po             maria

Commit, so the uploaded translations become available to the scripts.

    >>> transaction.commit()

Now, we need to do the final import. It's done as a two steps procedure.

The first one, approves the import.

    >>> import subprocess
    >>> process = subprocess.Popen([
    ...     'cronscripts/rosetta-approve-imports.py'
    ...     ], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    ...     stderr=subprocess.STDOUT, universal_newlines=True,
    ...     )
    >>> (output, empty) = process.communicate()
    >>> print(output)
    INFO    Creating lockfile:
         /var/lock/launchpad-translations-import-queue-gardener.lock
    INFO    The automatic approval system approved some entries.
    INFO    Removed 2 entries from the queue.
    <BLANKLINE>

The second one, executes the import.

    >>> process = subprocess.Popen([
    ...     'cronscripts/rosetta-poimport.py'
    ...     ], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    ...     stderr=subprocess.STDOUT, universal_newlines=True,
    ...     )
    >>> (output, empty) = process.communicate()
    >>> print(output)
    INFO    Creating lockfile: /var/lock/launchpad-rosetta-poimport.lock
    INFO    Importing: Spanish (es) translation of pmount in Ubuntu Hoary
            package "pmount"
    ...


Translation file names
......................

A callback tells the translations import queue what to do with the file
names found in the tarball:

    >>> from lp.soyuz.model.packagetranslationsuploadjob import (
    ...     _filter_ubuntu_translation_file)

Anything not in the "source/" directory is ignored.

    >>> print(_filter_ubuntu_translation_file('foo/bar.po'))
    None

Files in source/ have that directory stripped off.

    >>> print(_filter_ubuntu_translation_file('source/bar.po'))
    bar.po

Files in source/debian/po/* and a few other paths are ignored.

Ones in debian/po are generally debconf translations, unused in Ubuntu.

    >>> print(_filter_ubuntu_translation_file('source/debian/po/bar.po'))
    None

Ones in d-i are Debian Installer translations.  Ubuntu builds those
translations very differently from how Debian does it, so we don't need
these uploads.

    >>> print(_filter_ubuntu_translation_file('source/d-i/foo.po'))
    None

Then there are some documentation directories whose contents we can't
translate in Launchpad.

    >>> print(_filter_ubuntu_translation_file('source/help/xx.pot'))
    None

    >>> print(_filter_ubuntu_translation_file('source/man/po/yy.po'))
    None

    >>> print(_filter_ubuntu_translation_file('source/man/po4a/zz.pot'))
    None

The match is on a path component boundary, so we don't filter other
uploads whose paths happen to begin with the same words as a directory
we filter.

    >>> print(_filter_ubuntu_translation_file('source/debian/pool.pot'))
    debian/pool.pot

    >>> print(_filter_ubuntu_translation_file('source/d-input.pot'))
    d-input.pot

    >>> print(_filter_ubuntu_translation_file('source/man/positive/nl.po'))
    man/positive/nl.po
