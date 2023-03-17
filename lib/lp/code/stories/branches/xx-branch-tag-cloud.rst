Projects with active branches
=============================

The tag cloud of projects is one way in which the number and scope of
available bazaar branches is shown to the user.

    >>> login(ANONYMOUS)
    >>> from lp.code.tests.helpers import make_project_cloud_data
    >>> from datetime import datetime, timedelta, timezone
    >>> now = datetime.now(timezone.utc)
    >>> make_project_cloud_data(
    ...     factory,
    ...     [
    ...         ("wibble", 35, 2, now - timedelta(days=2)),
    ...         ("linux", 110, 1, now - timedelta(days=8)),
    ...     ],
    ... )
    >>> logout()

    >>> anon_browser.open("http://code.launchpad.test/projects")
    >>> print(anon_browser.title)
    Projects with active branches

The `Projects with active branches` page shows a link for each project that
has branches associated with it.  The HTML class attribute is used to
control how the link is shown.

    >>> tags = find_tag_by_id(anon_browser.contents, "project-tags")
    >>> for anchor in tags.find_all("a"):
    ...     print(anchor.decode_contents(), " ".join(anchor["class"]))
    ...
    linux cloud-size-largest cloud-medium
    wibble cloud-size-smallest cloud-dark
