===========================
Karma for uploaded packages
===========================

Uploads through Soyuz will give karma to users when the upload is
accepted.  This means that uploads that are new will not receive karma until
they are accepted from the queue.

Set up test fixtures
====================

Set up an event listener to show when karma gets assigned.

    >>> from lp.testing.karma import KarmaAssignedEventListener
    >>> karma_helper = KarmaAssignedEventListener()
    >>> karma_helper.register_listener()


Uploading new sources
=====================

First, uploading a new source does not assign karma immediately.

    >>> bar_src = getUploadForSource(
    ...	      'suite/bar_1.0-1/bar_1.0-1_source.changes')
    >>> bar_src.process()
    >>> result = bar_src.do_accept()
    >>> bar_src.queue_root.status.name
    'NEW'

Nothing is printed from the listener yet, so no karma was assigned.
We'll accept the upload now.

    >>> transaction.commit()
    >>> bar_src.queue_root.acceptFromQueue()
    Karma added: action=distributionuploadaccepted, distribution=ubuntu

As can be seen, karma was added for the package creator.

If we upload a package that has a different person signing the upload
compared to the package creator, then both will get karma.

    >>> foo_src = getUploadForSource(
    ...       'suite/foo_1.0-1/foo_1.0-1_source.changes')
    >>> foo_src.process()
    >>> result = foo_src.do_accept()

Poke the queue entry so it looks like Foo Bar (name16) uploaded it:

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.registry.interfaces.gpg import IGPGKeySet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> name16 = getUtility(IPersonSet).getByName('name16')
    >>> key = getUtility(IGPGKeySet).getGPGKeysForPerson(name16)[0]
    >>> removeSecurityProxy(foo_src.queue_root).signing_key_owner = (
    ...     key.owner)
    >>> removeSecurityProxy(foo_src.queue_root).signing_key_fingerprint = (
    ...     key.fingerprint)
    >>> transaction.commit()
    >>> foo_src.queue_root.acceptFromQueue()
    Karma added: action=distributionuploadaccepted, distribution=ubuntu
    Karma added: action=sponsoruploadaccepted, distribution=ubuntu

You can see that two karma events occurred.


Uploading auto-accepted sources
===============================

Auto-accepted sources are also given karma in the same way as queued uploads
except that the karma is awarded earlier in the processing cycle.

    >>> bar2_src = getUploadForSource(
    ...     'suite/bar_1.0-2/bar_1.0-2_source.changes')
    >>> bar2_src.process()
    >>> result = bar2_src.do_accept()
    Karma added: action=distributionuploadaccepted, distribution=ubuntu


Uploading to PPAs
=================

PPA uploads are always auto-accepted and we don't care about sponsors.  They
will generate another different karma event for the uploader.

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.soyuz.enums import ArchivePurpose
    >>> from lp.soyuz.interfaces.archive import IArchiveSet
    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> name16_ppa = getUtility(IArchiveSet).new(
    ...     owner=name16, distribution=ubuntu, purpose=ArchivePurpose.PPA)
    >>> bar_ppa_src = getPPAUploadForSource(
    ...     'suite/bar_1.0-1/bar_1.0-1_source.changes', name16_ppa)
    >>> bar_ppa_src.process()
    >>> result = bar_ppa_src.do_accept()
    Karma added: action=ppauploadaccepted, distribution=ubuntu


Clean up
========

Unregister the event listener to make sure we won't interfere in other tests,
and delete a stray uploaded file.

    >>> import os
    >>> from lp.archiveuploader.tests import datadir
    >>> karma_helper.unregister_listener()
    >>> upload_data = datadir('suite/bar_1.0-2')
    >>> os.remove(os.path.join(upload_data, 'bar_1.0.orig.tar.gz'))
