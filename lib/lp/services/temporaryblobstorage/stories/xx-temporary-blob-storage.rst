The set of temporary blobs
==========================

The set of temporary blobs in Launchpad is represented by the collection
found at /temporary-blobs. The collection is always empty because there
is no use case for external iteration.

    >>> temporary_blobs = webservice.get("/temporary-blobs").jsonBody()
    >>> len(temporary_blobs["entries"])
    0

If we add a new blob, it will not show up in the temporary_blobs entries set.

    >>> login("foo.bar@canonical.com")
    >>> import os
    >>> from zope.component import getUtility
    >>> from lp.services.config import config
    >>> from lp.services.temporaryblobstorage.interfaces import (
    ...     ITemporaryStorageManager,
    ... )

    >>> testfiles = os.path.join(config.root, "lib/lp/bugs/tests/testfiles")
    >>> with open(
    ...     os.path.join(testfiles, "extra_filebug_data.msg"), "rb"
    ... ) as blob_file:
    ...     blob_data = blob_file.read()
    >>> print(blob_data[307:373].decode("UTF-8"))
    --boundary
    Content-disposition: attachment; filename='attachment1'

    >>> blob_token = getUtility(ITemporaryStorageManager).new(blob_data)

    >>> logout()

    >>> temporary_blobs = webservice.get("/temporary-blobs").jsonBody()
    >>> len(temporary_blobs["entries"])
    0

It is however possible to fetch a blob directly using its token (so that
apport can tell when a bug is ready to file).

    >>> blob_link = "/temporary-blobs/" + blob_token
    >>> blob = webservice.get(blob_link).jsonBody()
    >>> blob["token"] == blob_token
    True

It's also possible to fetch the blob by calling temporary_blobs.fetch()
and passing it a token.

    >>> blob = webservice.named_get(
    ...     "/temporary-blobs", "fetch", token=blob_token
    ... ).jsonBody()
    >>> blob["token"] == blob_token
    True

Checking whether a blob has been processed
------------------------------------------

Launchpad processes blobs after they've been uploaded, so that any data
that can be used whilst filing a bug (or in any other operation,
ostensibly) can be extracted from the blob without affecting the
processing time of web requests.

It's possible to see whether a blob has been processed by calling its
hasBeenProcessed() method. In the case of the blob we created above, it
hasn't been processed because no job was created to process it.

    >>> print(
    ...     webservice.named_get(
    ...         blob["self_link"], "hasBeenProcessed"
    ...     ).jsonBody()
    ... )
    False

However, since the blob has not been processed there will be no
job processed data at this point.

    >>> print(
    ...     webservice.named_get(
    ...         blob["self_link"], "getProcessedData"
    ...     ).jsonBody()
    ... )
    None

Once the blob has been processed, its hasBeenProcessed() method will
return True.

    >>> from lp.bugs.interfaces.apportjob import IProcessApportBlobJobSource
    >>> login("foo.bar@canonical.com")
    >>> job = getUtility(IProcessApportBlobJobSource).create(
    ...     getUtility(ITemporaryStorageManager).fetch(blob_token)
    ... )
    >>> job.job.start()
    >>> job.job.complete()
    >>> job.run()
    >>> logout()

    >>> print(
    ...     webservice.named_get(
    ...         blob["self_link"], "hasBeenProcessed"
    ...     ).jsonBody()
    ... )
    True

And now the blob's parsed-out metadata is now accessible.

    >>> metadata = webservice.named_get(
    ...     blob["self_link"], "getProcessedData"
    ... ).jsonBody()

    >>> print(metadata["extra_description"])
    This should be added to the description.

    >>> print(len(metadata["comments"]))
    2

    >>> attachment = metadata["attachments"][0]
    >>> print(attachment["description"])
    attachment1
