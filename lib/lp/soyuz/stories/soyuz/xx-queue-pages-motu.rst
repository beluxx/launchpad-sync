MOTU administration of the Upload Queue Pages
=============================================

(see also xx-queue-pages.rst)

Queue administration has a permissioning mechanism that allows certain
users to work within component boundaries.  That is, given a right in
a certain component or components, the user may override components
between those components, and accept or reject uploads for those
components.  These rights are assigned to those components only so
the user is not able to change uploads outside of their remit.

Before we can accept anything, the librarian needs to be loaded with
fake changes files (so it doesn't OOPS when trying to send emails).

    >>> from lp.archiveuploader.tests import (
    ...     insertFakeChangesFileForAllPackageUploads,
    ... )
    >>> insertFakeChangesFileForAllPackageUploads()


MOTU upload-admin role
----------------------

In our sample data, there is a user 'no-team-memberships' who has
rights to administer the queue in the universe and multiverse
components only.  We'll set up a browser for them:

    >>> motu_browser = setupBrowser(
    ...     auth="Basic no-team-memberships@test.com:test"
    ... )

The current breezy NEW queue contains a few items all in the "main"
component:

    >>> def print_queue(contents):
    ...     queue_rows = find_tags_by_class(contents, "queue-row")
    ...     for row in queue_rows:
    ...         print(extract_text(row))
    ...

    >>> motu_browser.open("http://launchpad.test/ubuntu/breezy-autotest/")
    >>> motu_browser.getLink("All uploads").click()
    >>> print_queue(motu_browser.contents)  # noqa
    Package             Version     Component Section Priority Sets Pocket  When
    netapplet...ddtp... -                                           Release 2006...
    netapplet...dist... -                                           Release 2006...
    alsa-utils (source) 1.0.9a-4... main      base    low           Release 2006...
    netapplet (source)  0.99.6-1    main      web     low           Release 2006...
    pmount (i386)       0.1-1                                       Release 2006...
    moz...irefox (i386) 0.9                                         Release 2006...

If we try and accept "alsa-utils" it will fail because our user does
not have permission to accept items in "main":

    >>> motu_browser.getControl(name="QUEUE_ID").value = ["4"]
    >>> motu_browser.getControl(name="Accept").click()
    >>> print_feedback_messages(motu_browser.contents)
    FAILED: alsa-utils (You have no rights to accept component(s) 'main')

The same applies to the binary upload "pmount" because its build
produced a package in main:

    >>> motu_browser.getControl(name="QUEUE_ID").value = ["2"]
    >>> motu_browser.getControl(name="Accept").click()
    >>> print_feedback_messages(motu_browser.contents)
    FAILED: pmount (You have no rights to accept component(s) 'main')

Let's change the components on some uploads so that the user has
permission to manipulate them.

    >>> from zope.component import getUtility
    >>> login("foo.bar@canonical.com")
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet,
    ... )
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.soyuz.interfaces.binarypackagename import (
    ...     IBinaryPackageNameSet,
    ... )
    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
    >>> from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
    >>> universe = getUtility(IComponentSet)["universe"]
    >>> alsa_utils = getUtility(ISourcePackageNameSet).queryByName(
    ...     "alsa-utils"
    ... )
    >>> pmount = getUtility(IBinaryPackageNameSet).queryByName("pmount")
    >>> mozilla = getUtility(IBinaryPackageNameSet).queryByName(
    ...     "mozilla-firefox"
    ... )
    >>> for source in SourcePackageRelease.selectBy(
    ...     sourcepackagename=alsa_utils
    ... ):
    ...     source.component = universe
    >>> for binary in IStore(BinaryPackageRelease).find(
    ...     BinaryPackageRelease, binarypackagename=pmount
    ... ):
    ...     binary.component = universe
    >>> for binary in IStore(BinaryPackageRelease).find(
    ...     BinaryPackageRelease, binarypackagename=mozilla
    ... ):
    ...     binary.component = universe
    >>> import transaction
    >>> transaction.commit()
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> flush_database_updates()
    >>> logout()

So now our user will be able to manipulate the alsa-utils source and
the pmount binary.  However, they are still constrained with any component
override that is applied; this must still be one of their permitted
components.

If they try to override back to main, it will fail:

    >>> motu_browser.getControl(name="QUEUE_ID").value = ["4"]
    >>> motu_browser.getControl(name="component_override").displayValue = [
    ...     "main"
    ... ]
    >>> motu_browser.getControl(name="Accept").click()
    >>> print_feedback_messages(motu_browser.contents)
    FAILED: alsa-utils (No rights to override to main)

The same applies to the binary:

    >>> motu_browser.getControl(name="QUEUE_ID").value = ["2"]
    >>> motu_browser.getControl(name="component_override").displayValue = [
    ...     "main"
    ... ]
    >>> motu_browser.getControl(name="Accept").click()
    >>> print_feedback_messages(motu_browser.contents)
    FAILED: pmount (No rights to override to main)

Our user is able to override to multiverse, however.  Let's do that
with pmount:

    >>> motu_browser.getControl(name="QUEUE_ID").value = ["2"]
    >>> motu_browser.getControl(name="component_override").displayValue = [
    ...     "multiverse"
    ... ]
    >>> motu_browser.getControl(name="Accept").click()
    >>> print_feedback_messages(motu_browser.contents)
    OK: pmount(multiverse/(unchanged)/(unchanged))

Our user is also able to reject, let's reject alsa-utils:

    >>> motu_browser.getControl(name="QUEUE_ID").value = ["4"]
    >>> motu_browser.getControl(name="rejection_comment").value = "Foo"
    >>> motu_browser.getControl(name="Reject").click()
    >>> print_feedback_messages(motu_browser.contents)
    OK: alsa-utils

In some cases the user might select more than one item at once, but they
only have permission to change a subset of those items.  In this case,
the items they have permission to change will be processed, but the others
will be left alone.

    >>> motu_browser.getControl(name="QUEUE_ID").value = ["1", "3"]
    >>> motu_browser.getControl(name="component_override").displayValue = [
    ...     "multiverse"
    ... ]
    >>> motu_browser.getControl(name="Accept").click()
    >>> print_feedback_messages(motu_browser.contents)
    FAILED: netapplet (You have no rights to accept component(s) 'main')
    OK: mozilla-firefox(multiverse/(unchanged)/(unchanged))
