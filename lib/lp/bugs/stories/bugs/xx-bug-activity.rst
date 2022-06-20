Bug Activity
============

The bug activity page is where you find the "changelog" of a bug.

    >>> anon_browser.open(
    ...     'http://bugs.launchpad.test/debian/+source/'
    ...     'mozilla-firefox/+bug/3/+activity')
    >>> main_content = find_main_content(anon_browser.contents)

The page contains a link back to the bug page in the breadcrumbs and
the main heading repeats the bug number for clarity:

    >>> print_location(anon_browser.contents)
    Hierarchy: Debian > mozilla-firefox package > Bug #3...
    Tabs:
    * Overview - http://launchpad.test/debian/+source/mozilla-firefox
    * Code - http://code.launchpad.test/debian/+source/mozilla-firefox
    * Bugs (selected) - http://bugs...test/debian/+source/mozilla-firefox
    * Blueprints - not linked
    * Translations -
      http://translations.launchpad.test/debian/+source/mozilla-firefox
    * Answers - http://answers.launchpad.test/debian/+source/mozilla-firefox
    Main heading: Activity log for bug #3

The activity log itself is presented as a table.

    >>> def print_row(row):
    ...     print(' | '.join(
    ...         extract_text(cell) for cell in row(('th', 'td'))))

    >>> for row in main_content.table('tr'):
    ...     print_row(row)
    Date | Who | What changed | Old value | New value | Message
    2005-08-10 16:30:32 | Sample Person | bug |  |  | assigned to source ...
    2005-08-10 16:30:47 | Sample Person | bug |  |  | assigned to source ...
    2006-02-24 21:34:52 | Foo Bar | mozilla-firefox: statusexplanation |  |  |

The bug page contains a link to the activity log.

    >>> anon_browser.open(
    ...     'http://bugs.launchpad.test/debian/+source/'
    ...     'mozilla-firefox/+bug/3')
    >>> print(anon_browser.getLink('See full activity log').url)
    http://.../+bug/3/+activity


Activity interleaved with comments
----------------------------------

Some bug activity is show interleaved with comments on a bug's main
page.

    >>> def print_comments(page, subset=slice(-1, None)):
    ...     """Print all the comments on the page."""
    ...     comment_divs = find_tags_by_class(page, 'boardComment')
    ...     for div_tag in comment_divs[subset]:
    ...         print(extract_text(div_tag))
    ...         print('-' * 8)

    >>> user_browser.open(
    ...     'http://bugs.launchpad.test/redfish/+bug/15/+addcomment')
    >>> user_browser.getControl(name='field.comment').value = (
    ...     "Here's a comment for testing, like.")
    >>> user_browser.getControl('Post Comment').click()
    >>> print_comments(user_browser.contents, slice(None))
    Revision history for this message
    In...
    Bug Watch Updater (bug-watch-updater)
    on 2007-12-18
    Changed in thunderbird:
    status:
    Unknown → New
    --------
    Revision history for this message
    No Privileges Person (no-priv)
    ...
    #7
    Here's a comment for testing, like.
    ...
    --------

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/redfish/+bug/15/+edit')
    >>> admin_browser.getControl('Summary').value = (
    ...     "A new title for this bug")
    >>> admin_browser.getControl('Change').click()

Alterations to the summary of a bug will show up along with any comments
that have been added.

    >>> user_browser.open('http://launchpad.test/bugs/15')
    >>> print_comments(user_browser.contents, slice(None))
    Revision history for this message
    In...
    Bug
    ...
    --------
    Foo Bar (name16) ... ago
    summary:
    - Nonsensical bugs are useless
    + A new title for this bug
    --------

Changes to the bug's description will simply be displayed as 'description:
updated', since such changes can be quite long.

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/redfish/+bug/15/+edit')
    >>> admin_browser.getControl("Description").value = (
    ...     "I've changed the description, isn't that excellent?")
    >>> admin_browser.getControl("Change").click()

    >>> admin_browser.open('http://launchpad.test/bugs/15')
    >>> print_comments(admin_browser.contents)
    Foo Bar
    ... ago
    summary:
    ...
    description:
    updated
    --------

Changes to the bug's tags will be show in the form tags removed or tags
added.

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/redfish/+bug/15/+edit')
    >>> admin_browser.getControl("Tags").value = "tag1 tag2 tag3"
    >>> admin_browser.getControl("Change").click()

    >>> admin_browser.open('http://launchpad.test/bugs/15')
    >>> print_comments(admin_browser.contents)
    Foo Bar
    ... ago
    summary:
    ...
    tags:
    added: tag1 tag2 tag3
    --------

When two similar activities are grouped into the same comment - like
two sets of tag changes - they are displayed in the order they were
made.

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/redfish/+bug/15/+edit')
    >>> admin_browser.getControl("Tags").value = "tag1 tag2 tag4"
    >>> admin_browser.getControl("Change").click()

    >>> admin_browser.open('http://launchpad.test/bugs/15')
    >>> print_comments(admin_browser.contents)
    Foo Bar (name16)
    ... ago
    summary:
    ...
    tags:
    added: tag1 tag2 tag3
    tags:
    added: tag4
    removed: tag3
    --------

Changes to a BugTask's attributes will show up listed under the task's
target.

We'll add a milestone to Redfish to demonstrate this.

    >>> admin_browser.open(
    ...     'http://launchpad.test/redfish/trunk/+addmilestone')
    >>> admin_browser.getControl('Name').value = 'foo'
    >>> admin_browser.getControl('Register Milestone').click()

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/redfish/+bug/15/+editstatus')
    >>> admin_browser.getControl('Status').value = ['Confirmed']
    >>> admin_browser.getControl('Importance').value = ['High']
    >>> admin_browser.getControl(
    ...     'Milestone').displayValue = ['Redfish foo']

    >>> admin_browser.getControl(
    ...     name='redfish.assignee.option').value = [
    ...         'redfish.assignee.assign_to_me']
    >>> admin_browser.getControl("Save Changes").click()

    >>> print_comments(admin_browser.contents)
    Foo Bar (name16)
    ... ago
    summary:
    ...
    Changed in redfish:
    assignee:
    nobody → Foo Bar (name16)
    importance:
    Undecided → High
    milestone:
    none → foo
    status:
    New → Confirmed
    --------

If a change is made to a bug task which is targeted to a distro source
package, the name of the package and the distro will be displayed.

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/+bug/'
    ...     '1/+editstatus')
    >>> admin_browser.getControl('Status').value = ['Confirmed']
    >>> admin_browser.getControl("Save Changes").click()
    >>> print_comments(admin_browser.contents)
    Foo Bar (name16)
    ... ago
    Changed in mozilla-firefox (Ubuntu):
    status:
    New → Confirmed
    --------

If a change has a comment associated with it it will be displayed in the
footer of that comment. All changes made with a given comment are
bundled with that comment in the UI.

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/+bug/'
    ...     '1/+editstatus')
    >>> admin_browser.getControl('Status').value = ['New']
    >>> admin_browser.getControl('Importance').value = ['Low']
    >>> admin_browser.getControl('Comment').value = "Lookit, a change!"
    >>> admin_browser.getControl("Save Changes").click()

Note that "Lookit, a change!" appears twice: once displaying the message
itself, and once again inside the textarea to edit the message.
    >>> print_comments(admin_browser.contents)
    Revision history for this message
    Foo Bar (name16)
    wrote
    ... ago:
    #2
    Lookit, a change!
    Lookit, a change!
    Changed in mozilla-firefox (Ubuntu):
    status:
    New → Confirmed
    importance:
    Medium → Low
    status:
    Confirmed → New
    Hide
    --------

If a target of a bug task is changed the old and new value will be shown.

    >>> admin_browser.open(
    ...     'http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/+bug/'
    ...     '1/+editstatus')
    >>> admin_browser.getControl(
    ...     name='ubuntu_mozilla-firefox.target.package'
    ...     ).value = 'linux-source-2.6.15'
    >>> admin_browser.getControl("Save Changes").click()
    >>> print_comments(admin_browser.contents)
    Revision history for this message
    Foo Bar (name16)
    wrote
    ... ago:
    #2
    ...
    affects:
    mozilla-firefox (Ubuntu) → linux-source-2.6.15 (Ubuntu)
    Hide
    --------

If a bug task is deleted the pillar no longer affected will be shown.

    >>> admin_browser.open("http://bugs.launchpad.test/firefox/+bug/6")
    >>> admin_browser.getLink(url='+distrotask').click()
    >>> admin_browser.getControl('Distribution').value = ['ubuntu']
    >>> admin_browser.getControl('Continue').click()
    >>> admin_browser.open("http://bugs.launchpad.test/ubuntu/+bug/6/+delete")
    >>> admin_browser.getControl('Delete').click()
    >>> print_comments(admin_browser.contents)
    Foo Bar (name16)
    ... ago
    no longer affects:
    ubuntu
    --------

Changes to information_type are shown.

    >>> admin_browser.open(
    ...     "http://bugs.launchpad.test/evolution/+bug/7/+secrecy")
    >>> admin_browser.getControl("Private", index=1).selected = True
    >>> admin_browser.getControl('Change').click()
    >>> admin_browser.open("http://bugs.launchpad.test/evolution/+bug/7")
    >>> print_comments(admin_browser.contents)
    Foo Bar (name16)
    ... ago
    information type:
    Public → Private
    --------

    >>> admin_browser.open(
    ...     "http://bugs.launchpad.test/jokosher/+bug/14/+secrecy")
    >>> admin_browser.getControl("Private", index=1).selected = True
    >>> admin_browser.getControl('Change').click()
    >>> admin_browser.open("http://bugs.launchpad.test/jokosher/+bug/14")
    >>> print_comments(admin_browser.contents)
    Foo Bar (name16)
    ... ago
    information type:
    Private Security → Private
    --------
