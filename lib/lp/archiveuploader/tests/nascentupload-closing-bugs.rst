Closing Bugs when Publishing Accepted Source
============================================

We have implemented 'premature publication of accepted sources' in
NascentUpload to increase the publishing throughput (see
lib/lp/archiveuploader/tests/nascentupload.rst).

Therefore we also use the available infrastructure to close bugs
mentioned in the source changelog (see close-bugs-from-changelog).

Starting a new series of package, upload and publish the first version
of 'bar' source package in ubuntu/hoary.


Publishing package and creating a bugtask
-----------------------------------------

    >>> bar_src = getUploadForSource(
    ...     "suite/bar_1.0-1/bar_1.0-1_source.changes"
    ... )
    >>> bar_src.process()
    >>> result = bar_src.do_accept()
    >>> bar_src.queue_root.status.name
    'NEW'

    >>> bar_src.queue_root.setAccepted()
    >>> pub_records = bar_src.queue_root.realiseUpload()

Check the current status of the bug we are supposed to fix:

    >>> the_bug_id = 6

    >>> from lp.testing.dbuser import switch_dbuser
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> login("no-priv@canonical.com")
    >>> switch_dbuser("launchpad")

    >>> bugtask_owner = getUtility(IPersonSet).getByName("kinnison")
    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> ubuntu_bar = ubuntu.getSourcePackage("bar")

    >>> the_bug = getUtility(IBugSet).get(the_bug_id)
    >>> bugtask = getUtility(IBugTaskSet).createTask(
    ...     the_bug, bugtask_owner, ubuntu_bar
    ... )

Inspect the current bugtasks for bug #6:

    >>> for bugtask in the_bug.bugtasks:
    ...     print(bugtask.title)
    ...     print(bugtask.status.name)
    ...
    Bug #6 in Mozilla Firefox: "Firefox crashes when ...
    NEW
    Bug #6 in bar (Ubuntu): "Firefox crashes when ...
    NEW

Return to the original test environment:

    >>> from lp.services.config import config
    >>> switch_dbuser(config.uploader.dbuser)
    >>> login("foo.bar@canonical.com")


Testing bug closing
-------------------

Once the base source is published every posterior version will be
automatically published in upload time as described in
nascentupload-publishing-accepted-sources.rst.

    >>> bar2_src = getUploadForSource(
    ...     "suite/bar_1.0-2/bar_1.0-2_source.changes"
    ... )
    >>> bar2_src.process()

This new version fixes bug #6 according its changesfiles:

    >>> print(bar2_src.changes.changed_by["person"].name)
    kinnison

    >>> print(six.ensure_str(bar2_src.changes._dict["Launchpad-bugs-fixed"]))
    6

    >>> print(bar2_src.changes.changes_comment)
    bar (1.0-2) breezy; urgency=low
    <BLANKLINE>
      * A second upload to ensure that binary overrides of _all work
    <BLANKLINE>
      * Also closes Launchpad bug #6
    <BLANKLINE>
    <BLANKLINE>

Do the upload acceptance/publication and expect the bug mentioned to
be processed:

    >>> result = bar2_src.do_accept()
    >>> bar2_src.queue_root.status.name
    'DONE'

Checking the results, the bugtask for 'bar (Ubuntu)' is updated to
FIXRELEASED and bug notification are generated:

    >>> the_bug = getUtility(IBugSet).get(6)

    >>> for bugtask in the_bug.bugtasks:
    ...     print(bugtask.title)
    ...     print(bugtask.status.name)
    ...
    Bug #6 in Mozilla Firefox: "Firefox crashes when ...
    NEW
    Bug #6 in bar (Ubuntu): "Firefox crashes when ...
    FIXRELEASED

And clean up.

    >>> import os
    >>> from lp.archiveuploader.tests import datadir
    >>> upload_data = datadir("suite/bar_1.0-2")
    >>> os.remove(os.path.join(upload_data, "bar_1.0.orig.tar.gz"))
