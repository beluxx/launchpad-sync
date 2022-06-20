Publishing ACCEPTED Sources
===========================

As recently requested in bug #77853, successfully source-only uploads,
i.e, those uploads that only include a source package and were
processed without errors, will be automatically published as PENDING.

This aggregation of processes are intended to increase the building
throughput, because the will allow the sources to be published on disk
and built within the same publishing cycle. (previously Soyuz requires
two publishing cycles, one for publish the source on disk and another
to build it).

Let's start a new series of ed (0.2-20) and publish it:

    >>> ed_src = getUploadForSource(
    ...     'split-upload-test/ed_0.2-20_source.changes')
    >>> ed_src.process()
    >>> result = ed_src.do_accept()
    >>> ed_src.queue_root.status.name
    'NEW'

    >>> ed_src.queue_root.setAccepted()
    >>> pub_records = ed_src.queue_root.realiseUpload()

Check if the publication is available through the Soyuz package stack:

    >>> from lp.registry.interfaces.distribution import (
    ...     IDistributionSet)

    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> hoary = ubuntu.getSeries('hoary')

    >>> ed_dsp = ubuntu.getSourcePackage('ed')
    >>> ed_dspr = ed_dsp.getVersion('0.2-20')
    >>> ed_dspr.publishing_history.count()
    1
    >>> ed_pub = ed_dspr.publishing_history[0]

    >>> print(ed_pub.sourcepackagerelease.title)
    ed - 0.2-20

    >>> print(ed_pub.distroseries.name)
    hoary

    >>> ed_pub.status.name
    'PENDING'

    >>> ed_pub.archive == hoary.main_archive
    True

Also check if the Soyuz archive file lookup can reach one of the
just-published file:

    >>> ubuntu.main_archive.getFileByName('ed_0.2.orig.tar.gz')
    <LibraryFileAlias...>

We have to commit in order to have new Librarian files available to
server by Librarian Server:

    >>> transaction.commit()

Now let's submit a new source version of ed (0.2-21) which will be
automatically accepted and published resulting in a PackageUpload
record in 'DONE' state:

    >>> ed21_src = getUploadForSource(
    ...     'ed-0.2-21/ed_0.2-21_source.changes')
    >>> ed21_src.process()
    >>> result = ed21_src.do_accept()
    >>> ed21_src.queue_root.status.name
    'DONE'

This is unfortunate, but we have to manually remove the file dumped
from librarian into our tree, otherwise it will remain on disk causing
problems to the next test run.

    >>> import os
    >>> from lp.archiveuploader.tests import datadir
    >>> os.remove(datadir('ed-0.2-21/ed_0.2.orig.tar.gz'))

After the mentioned procedure-shortcut, since ed_0.2-21 was
auto-accepted (i.e, published as PENDING), it should be immediately
available via the package stack:

    >>> ed21_dspr = ed_dsp.getVersion('0.2-21')
    >>> ed21_dspr.publishing_history.count()
    1
    >>> ed21_pub = ed21_dspr.publishing_history[0]

    >>> print(ed21_pub.sourcepackagerelease.title)
    ed - 0.2-21

    >>> print(ed21_pub.distroseries.name)
    hoary

    >>> ed21_pub.status.name
    'PENDING'

    >>> ed21_pub.archive == hoary.main_archive
    True

Same happens for the archive file lookup:

    >>> ubuntu.main_archive.getFileByName('ed_0.2-21.dsc')
    <LibraryFileAlias...>

