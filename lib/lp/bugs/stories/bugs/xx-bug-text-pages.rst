Bug Text Pages
==============

Launchpad provides a way for users to view textual descriptions of bug
reports, as an alternative to the graphical user interface.

To demonstrate this feature, we'll use bug 1.

We'll start by adding some attachments to the bug:

    >>> from io import BytesIO
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.testing import login, logout
    >>> from lp.bugs.model.bug import Bug
    >>> from lp.registry.model.person import Person
    >>> login("foo.bar@canonical.com")
    >>> mark = Person.selectOneBy(name="mark")
    >>> mark.display_name = "M\xe1rk Sh\xfattlew\xf2rth"
    >>> bug = Bug.get(1)
    >>> content = BytesIO(b"<html><body>bogus</body></html>")
    >>> a1 = bug.addAttachment(
    ...     mark,
    ...     content,
    ...     "comment for file a",
    ...     "file_a.txt",
    ...     url=None,
    ...     content_type="text/html",
    ... )
    >>> content = BytesIO(b"do we need to")
    >>> a2 = bug.addAttachment(
    ...     mark,
    ...     content,
    ...     "comment for file with space",
    ...     "file with space.txt",
    ...     url=None,
    ...     content_type='text/plain;\n  name="file with space.txt"',
    ... )
    >>> content = BytesIO(b"Yes we can!")
    >>> a3 = bug.addAttachment(
    ...     mark,
    ...     content,
    ...     "comment for patch",
    ...     "bug-patch.diff",
    ...     url=None,
    ...     is_patch=True,
    ...     content_type="text/plain",
    ...     description="a patch",
    ... )

Next, we'll cycle through all statuses so the dates are present (to
toggle away from Fix Released we must be the target owner):

    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> t0 = bug.bugtasks[0]
    >>> t0.transitionToStatus(BugTaskStatus.INCOMPLETE, mark)
    >>> t0.transitionToStatus(BugTaskStatus.CONFIRMED, mark)
    >>> t0.transitionToStatus(BugTaskStatus.INPROGRESS, mark)
    >>> t0.transitionToStatus(BugTaskStatus.FIXRELEASED, mark)
    >>> t0.transitionToStatus(BugTaskStatus.NEW, t0.target.owner)
    >>> t0.transitionToStatus(BugTaskStatus.FIXRELEASED, mark)
    >>> logout()
    >>> flush_database_updates()


Text Pages from a Bug Context
-----------------------------

Users can view a textual description of any bug at that bug's text page,
according to the following URL pattern:

    http://launchpad.test/bugs/<bug-number>/+text

For example, users can view a textual description of bug 1:

    >>> anon_browser.open("http://launchpad.test/bugs/1/+text")
    >>> anon_browser.url
    'http://launchpad.test/bugs/1/+text'
    >>> print(anon_browser.headers["content-type"])
    text/plain;charset=utf-8

The textual description contains basic information about that bug, along with
all tasks related to that bug, presented in an easy-to-digest format:

    >>> text_bug = anon_browser.contents
    >>> print(text_bug)
    bug: 1
    title: Firefox does not support SVG
    date-reported: Thu, 01 Jan 2004 20:58:04 -0000
    date-updated: ...
    reporter: Sample Person (name12)
    duplicate-of:
    duplicates:
    attachments:
       http://bugs.launchpad.test/.../+files/file_a.txt text/html
       http://bugs.launchpad.test/.../+files/file%20with%20space.txt
         text/plain; name="file with space.txt"
    patches:
        http://.../bug-patch.diff text/plain
    tags:
    subscribers:
        Steve Alexander (stevea)
        Sample Person (name12)
    <BLANKLINE>
    task: firefox
    status: Fix Released
    date-created: Fri, 02 Jan 2004 03:49:22 -0000
    date-left-new: ...
    date-confirmed: ...
    date-triaged: ...
    date-assigned: Sun, 02 Jan 2005 11:07:20 -0000
    date-inprogress: ...
    date-closed: ...
    date-fix-committed: ...
    date-fix-released: ...
    date-left-closed: ...
    reporter: Sample Person (name12)
    importance: Low
    assignee: Márk Shúttlewòrth (mark)
    milestone:
    <BLANKLINE>
    task: mozilla-firefox (Ubuntu)
    status: New
    date-created: Sat, 17 Jan 2004 01:15:48 -0000
    date-assigned: Mon, 17 Jan 2005 01:15:48 -0000
    reporter: Foo Bar (name16)
    importance: Medium
    component: main
    assignee:
    milestone:
    <BLANKLINE>
    task: mozilla-firefox (Debian)
    status: Confirmed
    date-created: Sun, 04 Jan 2004 03:49:22 -0000
    date-assigned: Tue, 04 Jan 2005 11:07:20 -0000
    reporter: Sample Person (name12)
    watch: http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=304014
    importance: Low
    assignee:
    milestone:
    <BLANKLINE>
    Content-Type: multipart/mixed; boundary="...

The multiple white spaces in the mime type of the second attachment
are replaced by a single space.

    >>> attachments_text = text_bug[text_bug.find("attachments:") :]
    >>> attachment_2 = attachments_text.split("\n")[2]
    >>> attachment_2
    ' http://bugs.launchpad.test/.../file%20with%20space.txt text/plain;
    name="file with space.txt"'

The comments are represented as a MIME message.

    >>> import email
    >>> from email.header import decode_header
    >>> comments = email.message_from_string(
    ...     text_bug[text_bug.find("Content-Type:") :]
    ... ).get_payload()

    >>> print(comments[0]["Content-Type"])
    text/plain; charset="utf-8"
    >>> "Author" in comments[0]
    False
    >>> "Date" in comments[0]
    False
    >>> "Message-Id" in comments[0]
    False
    >>> print(comments[0].get_payload())
    Firefox needs to support embedded SVG images, now that the standard has
    been finalised.
    <BLANKLINE>
    The SVG standard 1.0 is complete, and draft implementations for Firefox
    exist. One of these implementations needs to be integrated with the base
    install of Firefox. Ideally, the implementation needs to include support
    for the manipulation of SVG objects from JavaScript to enable interactive
    and dynamic SVG drawings.

    >>> print(comments[3]["Content-Type"])
    text/plain; charset="utf-8"
    >>> [(author_bytes, author_charset)] = decode_header(
    ...     comments[3]["Author"]
    ... )
    >>> print(author_bytes.decode(author_charset))
    Márk Shúttlewòrth (mark)
    >>> "Date" in comments[3]
    True
    >>> "Message-Id" in comments[3]
    True
    >>> print(comments[3].get_payload())
    comment for file with space


Text Pages from a Bug Task Context
----------------------------------

Users can also view a textual description of a bug from the context of a task
relating to that bug, according to the following URL pattern:

   http://launchpad.test/<target>/+bug/<number>/+text

For example, since bug 1 affects Mozilla Firefox, users can view the textual
description of bug 1 directly from the Mozilla Firefox-specific text page:

    >>> anon_browser.open("http://launchpad.test/firefox/+bug/1/+text")
    >>> anon_browser.url
    'http://launchpad.test/firefox/+bug/1/+text'

    >>> print(anon_browser.headers["content-type"])
    text/plain;charset=utf-8

The textual report contains the same information as the report provided by the
parent bug context:

    >>> text_bug_task = anon_browser.contents
    >>> print(text_bug_task)
    bug: 1
    title: Firefox does not support SVG
    ...

Although the bug task's textual report contains identical information to the
parent bug's textual report, it's not possible to show this by comparing the
response strings to one another directly. This is because each report contains
multiple sections separated by a pseudo-random string that changes from one
request to another.

However, we can show that the reports are identical by comparing the sections
that comprise them. First, we use a regular expression to extract the pseudo-
random separator string for each report:

    >>> import re
    >>> separator_regex = re.compile(
    ...     'Content-Type: multipart/mixed; boundary\\="([^"]+)"'
    ... )

    >>> separator_bug = separator_regex.findall(text_bug)[0]
    >>> separator_bug_task = separator_regex.findall(text_bug_task)[0]

Now we can show that the individual sections are identical for each report.
The only differences are the download URLs of bug attachments:

    >>> text_bug_chunks = text_bug.split(separator_bug)
    >>> text_bug_task_chunks = text_bug_task.split(separator_bug_task)
    >>> len(text_bug_chunks) == len(text_bug_task_chunks)
    True

    >>> for chunk_no in range(len(text_bug_task_chunks)):
    ...     if text_bug_task_chunks[chunk_no] != text_bug_chunks[chunk_no]:
    ...         bug_task_lines = text_bug_task_chunks[chunk_no].split("\n")
    ...         bug_lines = text_bug_chunks[chunk_no].split("\n")
    ...         assert len(bug_task_lines) == len(bug_lines)
    ...         for line_no in range(len(bug_task_lines)):
    ...             if bug_lines[line_no] != bug_task_lines[line_no]:
    ...                 print(bug_lines[line_no])
    ...                 print(bug_task_lines[line_no])
    ... # noqa
    ...
    http://bugs.launchpad.test/bugs/1/+attachment/.../+files/file_a.txt text/html
    http://bugs.launchpad.test/firefox/+bug/.../+files/file_a.txt text/html
    http://bugs.launchpad.test/bugs/1/.../+files/file%20with%20space.txt...
    http://bugs.launchpad.test/firefox/+bug/.../+files/file%20with%20space.txt...
    http://bugs.launchpad.test/bugs/1/.../+files/bug-patch.diff text/plain
    http://bugs.launchpad.test/firefox/+bug/.../+files/bug-patch.diff text/plain

Duplicate Bugs
--------------

When one bug duplicates another bug, the textual description includes the
duplicated bug's ID:

    >>> anon_browser.open("http://launchpad.test/bugs/6/+text")
    >>> anon_browser.url
    'http://launchpad.test/bugs/6/+text'
    >>> print(anon_browser.headers["content-type"])
    text/plain;charset=utf-8

    >>> print(anon_browser.contents)
    bug: 6
    ...
    duplicate-of: 5
    ...

When a bug has duplicate bugs, the textual description includes a list of the
duplicate bug IDs:

    >>> anon_browser.open("http://launchpad.test/bugs/5/+text")
    >>> anon_browser.url
    'http://launchpad.test/bugs/5/+text'
    >>> print(anon_browser.headers["content-type"])
    text/plain;charset=utf-8

    >>> print(anon_browser.contents)
    bug: 5
    ...
    duplicate-of:
    duplicates: 6
    ...


Bug Lists
---------

Users can also see a list of all bug IDs for a given target by viewing that
product's bugs text page, according to the following URL pattern:

   http://launchpad.test/<target>/+bugs-text

For example, users can see the IDs of open bugs on Mozilla Firefox:

    >>> anon_browser.open("http://launchpad.test/firefox/+bugs-text")
    >>> anon_browser.url
    'http://launchpad.test/firefox/+bugs-text'
    >>> print(anon_browser.headers["content-type"])
    text/plain;charset=utf-8

    >>> print(anon_browser.contents)
    5
    4

The textual bugs page supports advanced searches in the same way as the
graphical bugs page. To perform an advanced search, users can append any
of the standard set of search parameters to a textual bugs page URL:

    >>> base_url = "http://launchpad.test/firefox/+bugs-text"
    >>> search_parameters = "field.status:list=FIXRELEASED"
    >>> url = base_url + "?" + search_parameters
    >>> anon_browser.open(url)
    >>> print(anon_browser.headers["content-type"])
    text/plain;charset=utf-8

    >>> print(anon_browser.contents)
    1

Searching for bugs in a component of a distribution works too.

    >>> base_url = "http://launchpad.test/ubuntu/+bugs-text"
    >>> search_parameters = "field.component=1"
    >>> url = base_url + "?" + search_parameters
    >>> anon_browser.open(url)
    >>> print(anon_browser.headers["content-type"])
    text/plain;charset=utf-8

    >>> print(anon_browser.contents)
    10

This page is also available for project groups.

    >>> anon_browser.open("http://launchpad.test/mozilla/+bugs-text")
    >>> print(anon_browser.contents)
    15
    5
    4


Private bugs
------------

When a bug is private, the textual description reflects this:

    >>> admin_browser.open("http://launchpad.test/bugs/14/+text")
    >>> print(admin_browser.contents)
    bug: 14
    title: jokosher exposes personal details in its actions portlet
    date-reported: Thu, 09 Aug 2007 11:39:16 -0000
    date-updated: Thu, 09 Aug 2007 11:39:16 -0000
    reporter: Karl Tilbury (karl)
    duplicate-of:
    duplicates:
    private: yes
    security: yes
    attachments:
    patches:
    tags: lunch-money
    subscribers:
        Karl Tilbury (karl)
        Dafydd Harries (daf)
    <BLANKLINE>
    task: jokosher
    status: New
    date-created: Thu, 09 Aug 2007 11:39:16 -0000
    reporter: Karl Tilbury (karl)
    importance: Undecided
    assignee:
    milestone:
    <BLANKLINE>
    Content-Type: multipart/mixed; boundary="...
    MIME-Version: 1.0
    <BLANKLINE>
    --...
    Content-Type: text/plain; charset="utf-8"
    Content-Transfer-Encoding: quoted-printable
    <BLANKLINE>
    Jokosher discloses to any passerby the fact that I am single and unwed
    in its actions portlet. Please fix this blatant violacion of privacy
    now!!
    --...

