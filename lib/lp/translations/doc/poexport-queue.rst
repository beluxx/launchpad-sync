Translation Export Queue
========================

The Translation Export Queue is the functionality that allows us to
export translation resources from the Launchpad portal.


ExportResult
------------

ExportResult class is used to control the list of exported files that
succeed and the ones that failed with the error associated.

    >>> import transaction
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.testing.faketransaction import FakeTransaction
    >>> from lp.testing.mail_helpers import pop_notifications, print_emails
    >>> from lp.translations.scripts.po_export_queue import ExportResult
    >>> import logging
    >>> logger = logging.getLogger()
    >>> fake_transaction = FakeTransaction()

When there is an error, the system will notify it.

To note error messages with the failure file, it should happen inside an
exception handling so we can get the exception error:

    >>> from lp.translations.model.potemplate import POTemplate
    >>> potemplate = POTemplate.get(1)
    >>> pofile = potemplate.getPOFileByLang("es")
    >>> personset = getUtility(IPersonSet)
    >>> carlos = personset.getByName("carlos")

    >>> result = ExportResult(carlos, [potemplate, pofile], logger)

Record the error.

    >>> try:
    ...     raise AssertionError("It's just an error for testing purposes")
    ... except AssertionError:
    ...     result.addFailure()
    ...

In this case, there is an error, so there shouldn't be a URL to download
anything.  If we set it, the system will fail:

    >>> result.url = "http://someplace.com/somefile.tar.gz"

Once we are done, we should notify the user that everything failed, but
given that we set a URL, the notification will detect the programming
error. In this example, 'carlos' will be the one that did the request.

    >>> result.notify()
    Traceback (most recent call last):
    ...
    AssertionError: We cannot have a URL for the export and a failure.

In this case, it should be None, so the notify works.

    >>> result.url = None
    >>> result.notify()

As usual, when there is an error, two emails should be sent:

    >>> test_emails = pop_notifications()
    >>> len(test_emails)
    2

    >>> for email in test_emails:
    ...     if "carlos@canonical.com" in email["to"]:
    ...         carlos_email = email
    ...     else:
    ...         admin_email = email
    ...

One is for the user with the error notification.

    >>> print_emails(notifications=[carlos_email], decode=True)  # noqa
    From: ...
    To: carlos@canonical.com
    Subject: Launchpad translation download: Evolution trunk -
    evolution-2.2 template
    Hello Carlos Perelló Marín,
    <BLANKLINE>
    Launchpad encountered problems exporting the files you requested.
    The Launchpad Translations team has been notified of this problem.
    Please reply to this email for further assistance.
    <BLANKLINE>
    If you want to retry your request, you can do so at
    <BLANKLINE>
      http://translations.launchpad.../trunk/+pots/evolution-2.2/+export.
    <BLANKLINE>
    -- 
    Automatic message from Launchpad.net.
    <BLANKLINE>
    ----------------------------------------

And the other to the admins.  This one lists the files that were being
exported as context to help tracking down any bugs.

    >>> print_emails(notifications=[admin_email], decode=True)  # noqa
    From: ...
    To: launchpad-error-reports@lists.canonical.com
    Subject: Launchpad translation download errors: Evolution trunk -
    evolution-2.2 template
    Hello Launchpad administrators,
    <BLANKLINE>
    Launchpad encountered problems exporting translation files
    requested by Carlos Perelló Marín (carlos) at
    <BLANKLINE>
      http://translations.launchpad.../trunk/+pots/evolution-2.2/+export
    <BLANKLINE>
    This means we have a bug in Launchpad that needs to be fixed
    before this export can proceed.  Here is the error we got:
    <BLANKLINE>
    Traceback (most recent call last):
    ...
    AssertionError: It's just an error for testing purposes
    <BLANKLINE>
    <BLANKLINE>
    Failed export request included:
      * evolution-2.2 in Evolution trunk
      * Spanish (es) translation of evolution-2.2 in Evolution trunk
    <BLANKLINE>
    -- 
    Automatic message from Launchpad.net.
    <BLANKLINE>
    ----------------------------------------

As a special case, some error messages are poisoned with non-ASCII
characters and can't be reported without triggering an error themselves.
Those are specially handled and reported.

    >>> try:
    ...     raise AssertionError(b"Really nasty \xc3 non-ASCII error!")
    ... except AssertionError:
    ...     result.addFailure()
    ...

It's not clear that it's possible to trigger this failure mode normally on
Python 3 at all, because bytes will just be formatted as b'...'.  For now,
inject a mock exception in that case so that the test can pass.

    >>> from unittest import mock
    >>> patcher = mock.patch.object(result, "failure")
    >>> mock_failure = patcher.start()
    >>> mock_failure.__str__.side_effect = lambda: b"\xc3".decode("UTF-8")
    >>> result.notify()
    >>> _ = patcher.stop()

    >>> test_emails = pop_notifications()
    >>> len(test_emails)
    2

    >>> carlos_email = None
    >>> admins_email = None
    >>> for email in test_emails:
    ...     if "carlos@canonical.com" in email["to"]:
    ...         carlos_email = email
    ...     else:
    ...         admin_email = email
    ...

The user's notification looks no different from that for an ordinary
error.

    >>> print_emails(notifications=[carlos_email], decode=True)  # noqa
    From: ...
    To: carlos@canonical.com
    Subject: Launchpad translation download: Evolution trunk -
    evolution-2.2 template
    Hello Carlos Perelló Marín,
    <BLANKLINE>
    Launchpad encountered problems exporting the files you requested.
    The Launchpad Translations team has been notified of this problem.
    Please reply to this email for further assistance.
    <BLANKLINE>
    If you want to retry your request, you can do so at
    <BLANKLINE>
      http://translations.launchpad.../trunk/+pots/evolution-2.2/+export.
    <BLANKLINE>
    -- 
    Automatic message from Launchpad.net.
    <BLANKLINE>
    ----------------------------------------

The one for the administrators, however, does not include the
unprintable exception text.

    >>> print_emails(notifications=[admin_email], decode=True)  # noqa
    From: ...
    To: launchpad-error-reports@lists.canonical.com
    Subject: Launchpad translation download errors: Evolution trunk -
    evolution-2.2 template
    Hello Launchpad administrators,
    <BLANKLINE>
    A UnicodeDecodeError occurred while trying to notify you of a
    failure during a translation export requested by Carlos ...
    (carlos) at
    <BLANKLINE>
      http://translations.launchpad.../trunk/+pots/evolution-2.2/+export
    <BLANKLINE>
    Failed export request included:
      * evolution-2.2 in Evolution trunk
      * Spanish (es) translation of evolution-2.2 in Evolution trunk
    <BLANKLINE>
    -- 
    Automatic message from Launchpad.net.
    <BLANKLINE>
    ----------------------------------------

Finally, there is the case when there are no errors at all. This is the
usual case.

    >>> result = ExportResult(carlos, [potemplate, pofile], logger)

As noted before, result.url should be set to the URL where the user can
download the requested files. If we don't set it, the export will fail:

    >>> result.notify()
    Traceback (most recent call last):
    ...
    AssertionError: On success, an exported URL is expected.

So let's add it and notify the user:

    >>> result.url = "http://someplace.com/somefile.tar.gz"
    >>> result.notify()

In this case, there are no errors, so we should get just a single email

    >>> test_emails = pop_notifications()
    >>> len(test_emails)
    1

    >>> print_emails(notifications=test_emails, decode=True)  # noqa
    From: ...
    To: carlos@canonical.com
    Subject: Launchpad translation download: Evolution trunk -
    evolution-2.2 template
    Hello Carlos Perelló Marín,
    <BLANKLINE>
    The translation files you requested from Launchpad are ready for
    download from the following location:
    <BLANKLINE>
      http://someplace.com/somefile.tar.gz
    <BLANKLINE>
    Note: this link will expire in about 1 week.  If you want to
    download these translations again, you will have to request
    them again at
    <BLANKLINE>
      http://translations.launchpad.../trunk/+pots/evolution-2.2/+export
    <BLANKLINE>
    -- 
    Automatic message from Launchpad.net.
    <BLANKLINE>
    ----------------------------------------


process_queue()
---------------

This method handles entries from the queue of entries to be exported.

    >>> from lp.translations.scripts.po_export_queue import process_queue

First, fill the export queue with entries to be exported.

    >>> from zope.component import getUtility
    >>> from lp.translations.interfaces.poexportrequest import (
    ...     IPOExportRequestSet,
    ... )
    >>> from lp.translations.interfaces.translationfileformat import (
    ...     TranslationFileFormat,
    ... )
    >>> export_request_set = getUtility(IPOExportRequestSet)

The queue is empty by default.

    >>> export_request_set.entry_count
    0

Once a new entry has been added, the queue has content.

    >>> export_request_set.addRequest(
    ...     carlos, potemplates=[potemplate], format=TranslationFileFormat.PO
    ... )
    >>> export_request_set.entry_count
    1

Once the queue is processed, the queue is empty again.

    >>> transaction.commit()
    >>> process_queue(transaction, logging.getLogger())
    INFO:...Stored file at http://.../po_evolution-2.2.pot

    >>> export_request_set.entry_count
    0

And a confirmation email was sent to carlos, the importer.

    >>> test_emails = pop_notifications()
    >>> len(test_emails)
    1

The confirmation email shows no errors at all.

    >>> print_emails(notifications=test_emails, decode=True)  # noqa
    From: ...
    To: carlos@canonical.com
    Subject: Launchpad translation download: Evolution trunk -
    evolution-2.2 template
    Hello Carlos Perelló Marín,
    <BLANKLINE>
    The translation files you requested from Launchpad are ready for
    download from the following location:
    <BLANKLINE>
      http://.../.../po_evolution-2.2.pot
    <BLANKLINE>
    Note: this link will expire in about 1 week.  If you want to
    download these translations again, you will have to request
    them again at
    <BLANKLINE>
      http://translations.launchpad.../trunk/+pots/evolution-2.2/+export
    <BLANKLINE>
    -- 
    Automatic message from Launchpad.net.
    <BLANKLINE>
    ----------------------------------------

Let's have a closer look at what is being exported. Usually all messages
are exported but not all messages are equal. Some messages have been
imported from upstream and then changed, others have been left as they
are. This pofile has both kind of messages.

    >>> package = factory.makeSourcePackage()
    >>> potemplate = factory.makePOTemplate(
    ...     distroseries=package.distroseries,
    ...     sourcepackagename=package.sourcepackagename,
    ... )
    >>> pofile = factory.makePOFile("eo", potemplate=potemplate)
    >>> tm = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile,
    ...     current_other=True,
    ...     translations=["esperanto1"],
    ...     potmsgset=factory.makePOTMsgSet(
    ...         potemplate, singular="english1", sequence=1
    ...     ),
    ... )
    >>> tm = factory.makeCurrentTranslationMessage(
    ...     pofile=pofile,
    ...     current_other=False,
    ...     translations=["esperanto2"],
    ...     potmsgset=factory.makePOTMsgSet(
    ...         potemplate, singular="english2", sequence=2
    ...     ),
    ... )

To see what is being exported we need to retrieve the exported file from
the librarian.

    >>> from lp.testing.librarianhelpers import get_newest_librarian_file

Exporting this pofile yields both messages in the resulting file.

    >>> export_request_set.addRequest(
    ...     carlos, pofiles=[pofile], format=TranslationFileFormat.PO
    ... )
    >>> transaction.commit()
    >>> process_queue(transaction, logging.getLogger())
    INFO:root:Stored file at http://...eo.po

    >>> print(get_newest_librarian_file().read().decode("UTF-8"))
    # Esperanto translation for ...
    ...
    "X-Generator: Launchpad (build ...)\n"
    <BLANKLINE>
    msgid "english1"
    msgstr "esperanto1"
    <BLANKLINE>
    msgid "english2"
    msgstr "esperanto2"
    <BLANKLINE>

Setting the format to POCHANGED yields only the message that was changed
in Ubuntu compared to upstream.

    >>> export_request_set.addRequest(
    ...     carlos, pofiles=[pofile], format=TranslationFileFormat.POCHANGED
    ... )
    >>> transaction.commit()
    >>> process_queue(transaction, logging.getLogger())
    INFO:root:Stored file at http://...eo.po

    >>> print(get_newest_librarian_file().read().decode("UTF-8"))
    # IMPORTANT: This file does NOT contain a complete PO file structure.
    # DO NOT attempt to import this file back into Launchpad.
    ...
    <BLANKLINE>
    msgid "english2"
    msgstr "esperanto2"
    <BLANKLINE>

Two more email notifications were sent, we'd better get rid of them.

    >>> discard = pop_notifications()

If uploading the exported file to the librarian fails, then we send failure
notifications in the same way as we do if the export fails.

    >>> export_request_set.addRequest(
    ...     carlos, pofiles=[pofile], format=TranslationFileFormat.PO
    ... )
    >>> transaction.commit()
    >>> with mock.patch.object(
    ...     ExportResult, "upload", side_effect=Exception("librarian melted")
    ... ):
    ...     process_queue(transaction, logging.getLogger())
    >>> test_emails = pop_notifications()
    >>> len(test_emails)
    2
    >>> for email in test_emails:
    ...     if "carlos@canonical.com" in email["to"]:
    ...         print_emails(notifications=[email], decode=True)  # noqa
    ...
    From: ...
    To: carlos@canonical.com
    Subject: Launchpad translation download: ...
    Hello Carlos Perelló Marín,
    <BLANKLINE>
    Launchpad encountered problems exporting the files you requested.
    The Launchpad Translations team has been notified of this problem.
    Please reply to this email for further assistance.
    <BLANKLINE>
    If you want to retry your request, you can do so at
    <BLANKLINE>
      http://translations.launchpad.../+export.
    <BLANKLINE>
    -- 
    Automatic message from Launchpad.net.
    <BLANKLINE>
    ----------------------------------------

Finally, if we try to do an export with an empty queue, we don't do
anything:

    >>> process_queue(fake_transaction, logging.getLogger())
    >>> len(pop_notifications())
    0
