If a bugtask is linked to a bug watch, the status and so on is not
editable, since it's pulled from the remote bug. Let's take a look at
the Debian task on bug #1.

    >>> browser.addHeader("Authorization", "Basic test@canonical.com:test")
    >>> browser.open(
    ...     "http://bugs.launchpad.test/debian/+source/mozilla-firefox/"
    ...     "+bug/1/+editstatus"
    ... )

There's currently a bug watch linked to the task.

    >>> bugwatch_control = browser.getControl(
    ...     name="debian_mozilla-firefox.bugwatch"
    ... )
    >>> bugwatch_control.type
    'radio'
    >>> bugwatch_control.displayValue
    ['...Debian...#304014...']

This means that we only display the status, it's not possible to edit it:

    >>> print(browser.contents)
    <!DOCTYPE...

    <label for="debian_mozilla-firefox.status">Status</label>
    ...
    <td><span class="statusConfirmed">Confirmed</span></td>
    ...

    >>> status_control = browser.getControl(
    ...     name="debian_mozilla-firefox.status"
    ... )
    Traceback (most recent call last):
    ...
    LookupError: name ...'debian_mozilla-firefox.status'
    ...

Of course we can't edit the importance or assignee either.

    >>> browser.getControl(name="debian_mozilla-firefox.importance")
    Traceback (most recent call last):
    ...
    LookupError: name ...'debian_mozilla-firefox.importance'
    ...

    >>> browser.getControl(name="debian_mozilla-firefox.assignee")
    Traceback (most recent call last):
    ...
    LookupError: name ...'debian_mozilla-firefox.assignee'
    ...

If we remove the bug watch, we'll be able to edit the status, which has
been reset to New.

    >>> bugwatch_control.displayValue = []
    >>> submit_button = browser.getControl("Save Changes")
    >>> submit_button.click()

    >>> browser.open(
    ...     "http://bugs.launchpad.test/debian/+source/mozilla-firefox/"
    ...     "+bug/1/+editstatus"
    ... )
    >>> status_control = browser.getControl(
    ...     name="debian_mozilla-firefox.status"
    ... )
    >>> status_control.displayValue
    ['New']

    >>> browser.getControl(name="debian_mozilla-firefox.assignee") is not None
    True

Let's try to actually edit the status to see that it works:

    >>> status_control.displayValue = ["Invalid"]
    >>> submit_button = browser.getControl("Save Changes")
    >>> submit_button.click()

    >>> browser.open(
    ...     "http://bugs.launchpad.test/debian/+source/mozilla-firefox/"
    ...     "+bug/1/+editstatus"
    ... )
    >>> status_control = browser.getControl(
    ...     name="debian_mozilla-firefox.status"
    ... )
    >>> status_control.displayValue
    ['Invalid']

From the edit page we can also create a new bug watch:

    >>> browser.open(
    ...     "http://bugs.launchpad.test/debian/+source/mozilla-firefox/"
    ...     "+bug/1/+editstatus"
    ... )
    >>> bugwatch_control = browser.getControl(
    ...     name="debian_mozilla-firefox.bugwatch"
    ... )
    >>> url_control = browser.getControl(name="debian_mozilla-firefox.url")
    >>> bugwatch_control.value = ["NEW"]
    >>> url_control.value = (
    ...     "http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1"
    ... )

    >>> submit_button = browser.getControl("Save Changes")
    >>> submit_button.click()
    >>> browser.url
    'http://bugs.launchpad.test/debian/+source/mozilla-firefox/+bug/1'

The Debian task is linked to the newly created bug watch.

    >>> from lp.bugs.tests.bug import print_bug_affects_table
    >>> print_bug_affects_table(browser.contents, highlighted_only=True)
    mozilla-firefox (Debian) ... debbugs #1


If we try to add an already existing bug watch, a new one won't be
created, instead the old one will be used.

    >>> browser.open(
    ...     "http://bugs.launchpad.test/debian/+source/mozilla-firefox/"
    ...     "+bug/1/+editstatus"
    ... )
    >>> bugwatch_control = browser.getControl(
    ...     name="debian_mozilla-firefox.bugwatch"
    ... )
    >>> url_control = browser.getControl(name="debian_mozilla-firefox.url")
    >>> bugwatch_control.value = ["NEW"]
    >>> url_control.value = (
    ...     "http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1"
    ... )

    >>> submit_button = browser.getControl("Save Changes")
    >>> submit_button.click()
    >>> browser.url
    'http://bugs.launchpad.test/debian/+source/mozilla-firefox/+bug/1'

    >>> bugwatch_portlet = find_portlet(
    ...     browser.contents, "Remote bug watches"
    ... )
    >>> for li_tag in bugwatch_portlet.find_all("li"):
    ...     print(li_tag.find_all("a")[0].string)
    ...
    mozilla.org #123543
    mozilla.org #2000
    mozilla.org #42
    debbugs #1
    debbugs #304014
