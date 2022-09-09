Queue Notify
============

PackageUpload has a notify() method to send emails.

Get a packageupload object for netapplet, which has a relatively intact
set of supporting sample data.  It has rows in distribution,
distroseries, sourcepackagerelease, person and a librarian entry for the
changes file which are all needed for successful operation of notify().

    >>> from lp.soyuz.interfaces.queue import IPackageUploadSet
    >>> netapplet_upload = getUtility(IPackageUploadSet)[3]
    >>> print(netapplet_upload.displayname)
    netapplet

Set up some library files for the netapplet source package.  These are
not already present in the sample data.

    >>> from lp.services.librarian.interfaces import ILibraryFileAliasSet
    >>> from lp.archiveuploader.tests import datadir
    >>> import os
    >>> netapplet_spr = netapplet_upload.sources[0].sourcepackagerelease
    >>> librarian = getUtility(ILibraryFileAliasSet)
    >>> files = [
    ...     "netapplet_1.0-1.dsc",
    ...     "netapplet_1.0.orig.tar.gz",
    ...     "netapplet_1.0-1.diff.gz",
    ... ]
    >>> for file in files:
    ...     filepath = datadir("suite/netapplet_1.0-1/%s" % file)
    ...     fileobj = open(filepath, "rb")
    ...     filesize = os.stat(filepath).st_size
    ...     lfa = librarian.create(file, filesize, fileobj, "dummytype")
    ...     sprf = netapplet_spr.addFile(lfa)
    ...     fileobj.close()
    ...

The notify() method generates one email here on this unsigned package.
It requires an announcement list email address, a "changes_file_object"
that is just an open file object for the original changes file, and a
special logger object that will extract tracebacks for the purposes of
this doctest.

    >>> changes_file_path = datadir(
    ...     "suite/netapplet_1.0-1/netapplet_1.0-1_source.changes"
    ... )
    >>> changes_file = open(changes_file_path, "rb")
    >>> from lp.services.log.logger import FakeLogger
    >>> netapplet_upload.notify(
    ...     changes_file_object=changes_file, logger=FakeLogger()
    ... )
    DEBUG Building recipients list.
    DEBUG Changes file is unsigned; adding changer as recipient.
    ...
    DEBUG Sent a mail:
    ...
    DEBUG   Recipients: ... Silverstone ...
    ...
    DEBUG above if files already exist in other distroseries.
    ...
    DEBUG You are receiving this email because you are the most recent person
    DEBUG listed in this package's changelog.

Helper functions to examine emails that were sent:

    >>> from lp.services.mail import stub
    >>> from lp.testing.mail_helpers import pop_notifications

There's only one email generated from the preceding upload:

    >>> [notification] = pop_notifications()

The mail headers contain our To: as set on the notify() call.  The
subject contains "Accepted", the package name, its version and whether
it's source or binary.  The Bcc field also always contains the
uploader's email address.

    >>> notification["To"]
    'Daniel Silverstone <daniel.silverstone@canonical.com>'

    >>> notification["Bcc"]
    'Root <root@localhost>'

    >>> notification["Subject"]
    '[ubuntu/breezy-autotest] netapplet 0.99.6-1 (New)'

The mail body contains a list of files that were accepted:

    >>> print(
    ...     notification.get_payload(0)
    ...     .get_payload(decode=True)
    ...     .decode("UTF-8")
    ... )  # noqa
    ... # doctest: -NORMALIZE_WHITESPACE
    NEW: netapplet_1.0-1.dsc
    NEW: netapplet_1.0.orig.tar.gz
    NEW: netapplet_1.0-1.diff.gz
    <BLANKLINE>
    ...
    You may have gotten the distroseries wrong.  If so, you may get warnings
    above if files already exist in other distroseries.
    <BLANKLINE>
    -- 
    You are receiving this email because you are the most recent person
    listed in this package's changelog.
    <BLANKLINE>

Now we will process a signed package.  Signed packages will potentially
have a different recipient list to unsigned ones; recipients for signed
package uploads can be the signer, the maintainer and the changer, where
these people are different.  Unsigned packages only send notifications
to the changer.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.registry.interfaces.gpg import IGPGKeySet
    >>> gpgkey = getUtility(IGPGKeySet).getByFingerprint(
    ...     "ABCDEF0123456789ABCDDCBA0000111112345678"
    ... )
    >>> removeSecurityProxy(netapplet_upload).signing_key_owner = gpgkey.owner
    >>> removeSecurityProxy(
    ...     netapplet_upload
    ... ).signing_key_fingerprint = gpgkey.fingerprint

Now request the email:

    >>> changes_file_path = datadir(
    ...     "suite/netapplet_1.0-1-signed/netapplet_1.0-1_source.changes"
    ... )
    >>> changes_file = open(changes_file_path, "rb")
    >>> netapplet_upload.setAccepted()
    >>> netapplet_upload.notify(
    ...     changes_file_object=changes_file, logger=FakeLogger()
    ... )
    DEBUG Building recipients list.
    ...
    DEBUG Sent a mail:
    ...
    DEBUG     Recipients: ... Bar ...
    ...
    DEBUG Announcing to autotest_changes@ubuntu.com
    ...
    DEBUG Sent a mail:
    ...

There are three emails, the upload acknowledgement to the changer, the
upload acknowledgement to the signer, and the announcement, because this
upload is already accepted.

    >>> msgs = pop_notifications()
    >>> len(msgs)
    3

The two upload acknowledgements contain the changer's email and the signer's
email in their respective 'To:' headers.
The announcement email contains the series's changeslist.

    >>> def to_lower(address):
    ...     """Return lower-case version of email address."""
    ...     return address.lower()
    ...

    >>> def extract_addresses(header_field):
    ...     """Extract and sort addresses from an email header field."""
    ...     return sorted(
    ...         [addr.strip() for addr in header_field.split(",")],
    ...         key=to_lower,
    ...     )
    ...

    >>> for msg in msgs:
    ...     print(msg["To"])
    ...
    Daniel Silverstone <daniel.silverstone@canonical.com>
    Foo Bar <foo.bar@canonical.com>
    autotest_changes@ubuntu.com

The mail 'Bcc:' address is the uploader.  The announcement has the
uploader and the Debian derivatives address for the package uploaded.

    >>> for msg in msgs:
    ...     print(pretty(extract_addresses(msg["Bcc"])))
    ...
    ['Root <root@localhost>']
    ['Root <root@localhost>']
    ['netapplet_derivatives@packages.qa.debian.org', 'Root <root@localhost>']

The mail 'From:' addresses are the uploader (for acknowledgements sent to
the uploader and the changer) and the changer.

    >>> for msg in msgs:
    ...     print(msg["From"])
    ...
    Root <root@localhost>
    Root <root@localhost>
    Daniel Silverstone <daniel.silverstone@canonical.com>

    >>> print(msgs[0]["Subject"])
    [ubuntu/breezy-autotest] netapplet 0.99.6-1 (Accepted)

The mail body contains the same list of files again:

    >>> print(msgs[0].get_payload(0).get_payload(decode=True).decode("UTF-8"))
    ... # noqa
    ... # doctest: -NORMALIZE_WHITESPACE
    netapplet (1.0-1) ...
    <BLANKLINE>
     OK: netapplet_1.0-1.dsc
         -> Component: main Section: web
     OK: netapplet_1.0.orig.tar.gz
     OK: netapplet_1.0-1.diff.gz
    <BLANKLINE>
    ...
    -- 
    You are receiving this email because you are the most recent person
    listed in this package's changelog.
    <BLANKLINE>

All the emails have the PGP signature stripped from the .changes file to
avoid replay attacks.

    >>> print(msgs[0].get_payload(1).get_payload(decode=True).decode("UTF-8"))
    Format: 1.7
    ...
    >>> print(msgs[1].get_payload(1).get_payload(decode=True).decode("UTF-8"))
    Format: 1.7
    ...
    >>> print(msgs[2].get_payload(1).get_payload(decode=True).decode("UTF-8"))
    Format: 1.7
    ...

notify() will also work without passing the changes_file_object
parameter provided that everything is already committed to the database
(which is not the case when nascent upload runs).  This example
demonstrates this usage:

    >>> from lp.services.librarianserver.testing.server import (
    ...     fillLibrarianFile,
    ... )
    >>> changes_file = open(changes_file_path, "rb")
    >>> fillLibrarianFile(1, content=changes_file.read())
    >>> changes_file.close()
    >>> from lp.soyuz.enums import PackageUploadStatus
    >>> from lp.soyuz.model.queue import PassthroughStatusValue
    >>> removeSecurityProxy(netapplet_upload).status = PassthroughStatusValue(
    ...     PackageUploadStatus.NEW
    ... )
    >>> netapplet_upload.notify(logger=FakeLogger())
    DEBUG Building recipients list.
    ...
    DEBUG Sent a mail:
    ...
    DEBUG   Recipients: ... Silverstone ...
    ...
    DEBUG above if files already exist in other distroseries.
    ...
    DEBUG You are receiving this email because you are the most recent person
    DEBUG listed in this package's changelog.
    DEBUG Sent a mail:
    ...
    DEBUG   Recipients: ... Bar ...
    ...
    DEBUG above if files already exist in other distroseries.
    ...
    DEBUG You are receiving this email because you made this upload.

Two emails are generated, one to the changer and one to the signer:

    >>> [changer_notification, signer_notification] = pop_notifications()

The mail headers are the same as before:

    >>> print(changer_notification["To"])
    Daniel Silverstone <daniel.silverstone@canonical.com>
    >>> print(signer_notification["To"])
    Foo Bar <foo.bar@canonical.com>

    >>> print(changer_notification["Bcc"])
    Root <root@localhost>
    >>> print(signer_notification["Bcc"])
    Root <root@localhost>

    >>> print(changer_notification["Subject"])
    [ubuntu/breezy-autotest] netapplet 0.99.6-1 (New)
    >>> print(signer_notification["Subject"])
    [ubuntu/breezy-autotest] netapplet 0.99.6-1 (New)

The mail body contains the same list of files again:

    >>> print(
    ...     changer_notification.get_payload(0)
    ...     .get_payload(decode=True)
    ...     .decode("UTF-8")
    ... )  # noqa
    ... # doctest: -NORMALIZE_WHITESPACE
    NEW: netapplet_1.0-1.dsc
    NEW: netapplet_1.0.orig.tar.gz
    NEW: netapplet_1.0-1.diff.gz
    <BLANKLINE>
    ...
    You may have gotten the distroseries wrong.  If so, you may get warnings
    above if files already exist in other distroseries.
    <BLANKLINE>
    -- 
    You are receiving this email because you are the most recent person
    listed in this package's changelog.
    <BLANKLINE>
    >>> print(
    ...     signer_notification.get_payload(0)
    ...     .get_payload(decode=True)
    ...     .decode("UTF-8")
    ... )  # noqa
    ... # doctest: -NORMALIZE_WHITESPACE
    NEW: netapplet_1.0-1.dsc
    NEW: netapplet_1.0.orig.tar.gz
    NEW: netapplet_1.0-1.diff.gz
    <BLANKLINE>
    ...
    You may have gotten the distroseries wrong.  If so, you may get warnings
    above if files already exist in other distroseries.
    <BLANKLINE>
    -- 
    You are receiving this email because you made this upload.
    <BLANKLINE>

notify() will also generate rejection notices if the upload failed.  The
summary_text argument is text that is appended to any auto-generated
text for the summary.  Rejections don't currently auto-generate
anything.

    >>> netapplet_upload.setRejected()
    >>> netapplet_upload.notify(
    ...     summary_text="Testing rejection message", logger=FakeLogger()
    ... )
    DEBUG Building recipients list.
    ...
    DEBUG Sent a mail:
    DEBUG   Subject: [ubuntu/breezy-autotest] netapplet 0.99.6-1 (Rejected)
    DEBUG   Sender: Root <root@localhost>
    DEBUG   Recipients: ... Silverstone ...
    DEBUG   Bcc: Root <root@localhost>
    DEBUG   Body:
    DEBUG Rejected:
    DEBUG Testing rejection message
    ...
    DEBUG If you don't understand why your files were rejected, or if the
    ...
    DEBUG You are receiving this email because you are the most recent person
    DEBUG listed in this package's changelog.
    ...
    DEBUG   Subject: [ubuntu/breezy-autotest] netapplet 0.99.6-1 (Rejected)
    DEBUG   Sender: Root <root@localhost>
    DEBUG   Recipients: ... Bar ...
    DEBUG   Bcc: Root <root@localhost>
    DEBUG   Body:
    DEBUG Rejected:
    DEBUG Testing rejection message
    ...
    DEBUG If you don't understand why your files were rejected, or if the
    ...
    DEBUG You are receiving this email because you made this upload.

Two emails are generated:

    >>> transaction.commit()
    >>> len(stub.test_emails)
    2

Clean up, otherwise stuff is left lying around in /var/tmp.

    >>> from lp.testing.layers import LibrarianLayer
    >>> LibrarianLayer.librarian_fixture.clear()
