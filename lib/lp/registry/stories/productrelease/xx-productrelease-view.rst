Any user can see a release for a series.

    >>> anon_browser.open("http://launchpad.test/firefox/trunk/0.9.2")
    >>> print(anon_browser.title)
    0.9.2 "One (secure) Tree Hill" : Series trunk : Mozilla Firefox

    >>> content = find_main_content(anon_browser.contents)
    >>> print(extract_text(find_tag_by_id(content, "Release-details")))
    Milestone information
    Project: Mozilla Firefox
    Series: trunk
    Version: 0.9.2
    Code name: One (secure) Tree Hill
    Released: 2004-10-15
    Registrant: Foo Bar
    Release registered: 2005-06-06
    Active: No. Drivers cannot target bugs and blueprints to this milestone.
    Download RDF metadata

Any user can see a table describing the files that are associated with the
release. Each file is linked.

    >>> table = find_tag_by_id(content, "downloads")
    >>> print(extract_text(table))
    File                            Description  Downloads
    firefox_0.9.2.orig.tar.gz (md5)              -

    >>> print(table.a)
    <a href=".../firefox/trunk/0.9.2/+download/firefox_0.9.2.orig.tar.gz"
       title="firefox_0.9.2.orig.tar.gz (9.5 MiB)">...

There is an link about how to verify downloaded files.

    >>> anon_browser.getLink("How do I verify a download?")
    <Link ...
    url='http://launchpad.test/+help-registry/verify-downloads.html'>

If the file had been downloaded, we'd see the number of times it was
downloaded and the date of the last download on that table as well.

    # Manually update the download counter for that file above so that we can
    # test it.
    >>> from datetime import date, datetime
    >>> from lp.services.librarian.model import LibraryFileAlias
    >>> lfa = LibraryFileAlias.selectOne(
    ...     LibraryFileAlias.q.filename == "firefox_0.9.2.orig.tar.gz"
    ... )
    >>> lfa.updateDownloadCount(date(2006, 5, 4), None, 1)

    >>> anon_browser.reload()
    >>> print(
    ...     extract_text(find_tag_by_id(anon_browser.contents, "downloads"))
    ... )
    File                            Description  Downloads
    firefox_0.9.2.orig.tar.gz (md5)              1 last downloaded ...
                              Total downloads:   1

When a file has been downloaded on the present day, all we can say is that
it's been downloaded "today".  That's because we don't have the time it was
downloaded, so we can't say it was downloaded a few minutes/hours ago.

    >>> import pytz
    >>> lfa.updateDownloadCount(datetime.now(pytz.utc).date(), None, 4356)
    >>> anon_browser.reload()
    >>> print(
    ...     extract_text(find_tag_by_id(anon_browser.contents, "downloads"))
    ... )
    File                            Description  Downloads
    firefox_0.9.2.orig.tar.gz (md5)              4,357 last downloaded today
                              Total downloads:   4,357
