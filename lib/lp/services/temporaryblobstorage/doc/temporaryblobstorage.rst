Temporary Blob Storage
======================

Launchpad allows users to upload a BLOB, which will be stored for a short
time, before being deleted. This upload can be done anonymously, and the
user is given a "ticket" that is unique and which allows them to point at
that blob during a subsequent transaction.

For example, a system that needs to file a bug, and attach a file to the
bug, could submit a structured BLOB to Launchpad, then start the bug filing
process with a pointer to that BLOB. The bug filing code could then
retrieve, parse and include the contents of the BLOB in the bug report,
perhaps as attachments.

    >>> from zope.component import getUtility
    >>> from lp.services.temporaryblobstorage.interfaces import (
    ...     ITemporaryStorageManager,
    ... )
    >>> tsm = getUtility(ITemporaryStorageManager)

To create a new TemporaryBlob, use ITemporaryStorageManager.new:

    >>> data = b"abcdefg"
    >>> uuid = tsm.new(data)
    >>> uuid is not None
    True

Because the blob is stored in the Librarian, we cannot retrieve it in the
same transaction as we stored it in:

    >>> import transaction
    >>> transaction.commit()

To retrieve a blob, we can also use the tsm.

    >>> blob = tsm.fetch(uuid)
    >>> blob.blob == b"abcdefg"
    True

We can delete a blob by UUID too:

    >>> print(tsm.delete(uuid))
    None

Size limits can be enforced, although this is turned off by default:

    >>> from lp.services.config import config
    >>> config.launchpad.max_blob_size
    0
    >>> max_blob_size = """
    ...     [launchpad]
    ...     max_blob_size: 6
    ...     """
    >>> config.push("max_blob_size", max_blob_size)
    >>> uuid = tsm.new(data)
    Traceback (most recent call last):
    ...
    lp.services.temporaryblobstorage.interfaces.BlobTooLarge: 7
    >>> config_data = config.pop("max_blob_size")


Checking blob processing status
-------------------------------

A blob has an hasBeenProcessed() method which returns True if the
ProcessApportBlobJob for the blob has been completed.

The hasBeenProcessed() of a  newly created blob, with no
associated ProcessApportBlobJob, will return False.

    >>> blob_token = getUtility(ITemporaryStorageManager).new(b"Blob data")
    >>> blob = getUtility(ITemporaryStorageManager).fetch(blob_token)
    >>> print(blob.hasBeenProcessed())
    False

We'll create a ProcessApportBlobJob for the blob.

    >>> from lp.bugs.interfaces.apportjob import IProcessApportBlobJobSource
    >>> processing_job = getUtility(IProcessApportBlobJobSource).create(blob)

    >>> blob = getUtility(ITemporaryStorageManager).fetch(blob_token)
    >>> processing_job.blob == blob
    True

Before the job is run, the blob's hasBeenProcessed() method will return
False.

    >>> print(blob.hasBeenProcessed())
    False

Whilst the job is running, the blob's hasBeenProcessed() method will
return False.

    >>> processing_job.job.start()
    >>> print(blob.hasBeenProcessed())
    False

Once the job is complete, the blob's hasBeenProcessed() method will
return True.

    >>> processing_job.job.complete()
    >>> print(blob.hasBeenProcessed())
    True
