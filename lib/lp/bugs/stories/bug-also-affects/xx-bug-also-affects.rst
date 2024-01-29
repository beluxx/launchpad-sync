In the bug page, you could request a fix for an upstream or
distribution.

    >>> browser.addHeader("Authorization", "Basic test@canonical.com:test")
    >>> browser.open("http://localhost/firefox/+bug/6")
    >>> browser.getLink(url="+distrotask").click()
    >>> browser.url
    'http://bugs.launchpad.test/firefox/+bug/6/+distrotask'

On this page we can add distribution task. Just in case we change our
mind, there is a cancel link that points back to the bug page:

    >>> cancel_link = browser.getLink("Cancel")
    >>> cancel_link.url
    'http://bugs.launchpad.test/firefox/+bug/6'

We start by adding an Ubuntu task. Since Ubuntu uses Launchpad as its
bug tracker, the task gets added and we return to the newly created
task's page.

    >>> browser.getControl("Distribution").value = ["ubuntu"]
    >>> browser.getControl("Continue").click()
    >>> browser.url
    'http://bugs.launchpad.test/ubuntu/+bug/6'

It should not be possible to add the same distrotask again.

    >>> browser.getLink(url="+distrotask").click()
    >>> browser.url
    'http://bugs.launchpad.test/ubuntu/+bug/6/+distrotask'

    >>> browser.getControl("Distribution").value = ["ubuntu"]
    >>> browser.getControl("Continue").click()
    >>> browser.url
    'http://bugs.launchpad.test/ubuntu/+bug/6/+distrotask'

    >>> print_feedback_messages(browser.contents)
    There is 1 error.
    This bug is already on Ubuntu. Please specify an affected package
    in which the bug has not yet been reported.

You also can't add another task on a distro source package, when there's
already a distro task open. (Instead, you should target the existing
distro task to an appropriate source package.)

    >>> browser.open("http://localhost/ubuntu/+bug/6/+distrotask")
    >>> browser.getControl("Distribution").value = ["ubuntu"]
    >>> browser.getControl("Source Package Name").value = "mozilla-firefox"
    >>> browser.getControl("Continue").click()
    >>> print_feedback_messages(browser.contents)
    There is 1 error.
    This bug is already open on Ubuntu with no package specified.
    You should fill in a package name for the existing bug.

Let's assign the existing Ubuntu task to mozilla-firefox, then add
another task on Ubuntu evolution.

    >>> browser.open("http://localhost/ubuntu/+bug/6/+editstatus")
    >>> browser.getControl(name="ubuntu.target.package").value = (
    ...     "mozilla-firefox"
    ... )
    >>> browser.getControl("Save Changes").click()

    >>> browser.open(
    ...     "http://localhost/ubuntu/+source/mozilla-firefox"
    ...     "/+bug/6/+distrotask"
    ... )
    >>> browser.getControl("Distribution").value = ["ubuntu"]
    >>> browser.getControl("Source Package Name").value = "evolution"
    >>> browser.getControl("Continue").click()

It's not possible to change the Ubuntu mozilla-firefox task to be on
Ubuntu evolution, because there already is an evolution task open.

    >>> browser.open(
    ...     "http://localhost/ubuntu/+source/mozilla-firefox/+bug/6/"
    ...     "+editstatus"
    ... )
    >>> browser.getControl(
    ...     name="ubuntu_mozilla-firefox.target.package"
    ... ).value = "evolution"
    >>> browser.getControl("Save Changes").click()
    >>> print_feedback_messages(browser.contents)
    There is 1 error in the data you entered...
    A fix for this bug has already been requested for evolution in Ubuntu

Now let's add a Debian task to bug 1. Since Debian doesn't use
Launchpad, we add a bug watch as well.

    >>> browser.open("http://localhost/firefox/+bug/1")
    >>> browser.getLink(url="+distrotask").click()
    >>> print(browser.url)
    http://bugs.launchpad.test/firefox/+bug/1/+distrotask

    >>> browser.getControl(name="field.distribution").value = ["debian"]
    >>> browser.getControl("Source Package Name").value = "alsa-utils"
    >>> browser.getControl("URL").value = (
    ...     "http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=123"
    ... )
    >>> browser.getControl("Continue").click()
    >>> print(browser.url)
    http://bugs.launchpad.test/debian/+source/alsa-utils/+bug/1

If we try to add an Ubuntu task together with a bug watch we get an
error, because Ubuntu uses Launchpad as its bug tracker

    >>> browser.getLink(url="+distrotask").click()
    >>> browser.getControl("Distribution").value = ["ubuntu"]
    >>> browser.getControl("Source Package Name").value = "alsa-utils"
    >>> browser.getControl("URL").value = (
    ...     "https://bugzilla.mozilla.org/show_bug.cgi?id=84"
    ... )
    >>> browser.getControl("Continue").click()
    >>> print(browser.url)
    http://bugs.launchpad.test/debian/+source/alsa-utils/+bug/1/+distrotask

    >>> print_feedback_messages(browser.contents)
    There is 1 error.
    Bug watches can not be added for Ubuntu, as it uses Launchpad as
    its official bug tracker. Alternatives are to add a watch for
    another project, or a comment containing a URL to the related
    bug report.

If we remove the remote bug it will work.

    >>> browser.getControl("URL").value = ""
    >>> browser.getControl("Continue").click()
    >>> print(browser.url)
    http://bugs.launchpad.test/ubuntu/+source/alsa-utils/+bug/1

It's not possible to change a bugtask to a existing one.

    >>> browser.getLink(
    ...     url="ubuntu/+source/mozilla-firefox/+bug/1/+editstatus"
    ... ).click()
    >>> print(browser.url)
    http://bugs.../ubuntu/+source/mozilla-firefox/+bug/1/+editstatus

    >>> browser.getControl(
    ...     name="ubuntu_mozilla-firefox.target.package"
    ... ).value = "alsa-utils"
    >>> browser.getControl("Save Changes").click()
    >>> print(browser.url)
    http://bugs.../ubuntu/+source/mozilla-firefox/+bug/1/+editstatus

    >>> print_feedback_messages(browser.contents)
    There is 1 error in the data you entered...
    A fix for this bug has already been requested for alsa-utils in Ubuntu

    >>> browser.getControl(
    ...     name="ubuntu_mozilla-firefox.target.package"
    ... ).value = "pmount"
    >>> browser.getControl("Save Changes").click()
    >>> print(browser.url)
    http://bugs.launchpad.test/ubuntu/+source/pmount/+bug/1

We want to make people aware of that they should link bugtasks to bug
watches in order to get automatic status updates. So if we try to add a
Debian task without linking it to a bug watch, we have to confirm that
we really want to do this.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> login("foo.bar@canonical.com")
    >>> factory.makeSourcePackage(
    ...     distroseries=getUtility(IDistributionSet)["debian"]["sid"],
    ...     sourcepackagename="pmount",
    ...     publish=True,
    ... )
    <SourcePackage ...>
    >>> logout()
    >>> browser.getLink(url="+distrotask").click()
    >>> browser.getControl("Distribution").value = ["debian"]
    >>> browser.getControl("Source Package Name").value = "pmount"
    >>> browser.getControl("Continue").click()
    >>> print(browser.url)
    http://bugs.launchpad.test/ubuntu/+source/pmount/+bug/1/+distrotask

    >>> print_feedback_messages(browser.contents)
    Debian doesn't use Launchpad as its bug tracker. ...

The form is shown as well, so it's possible to easily change the field
values, in order to add a bug watch.

    >>> browser.getControl("URL") is not None
    True

Of course, if we simply press Continue again, nothing will happen, the
notification will still be displayed.

    >>> browser.getControl("Continue").click()
    >>> print(browser.url)
    http://bugs.launchpad.test/ubuntu/+source/pmount/+bug/1/+distrotask

    >>> print_feedback_messages(browser.contents)
    Debian doesn't use Launchpad as its bug tracker. ...

If we confirm that we indeed want to add an unlinked task, we get
redirected to the bug page.

    >>> browser.getControl("Add Anyway").click()
    >>> print(browser.url)
    http://bugs.launchpad.test/debian/+source/pmount/+bug/1

    >>> print(browser.contents)
    <...
    ...>pmount (Debian)</a>...
    ...

We cannot allow proprietary bugs to affect more than one pillar.

    >>> from lp.services.webapp import canonical_url
    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.bugs.interfaces.bug import CreateBugParams
    >>> from lp.app.enums import InformationType
    >>> from lp.registry.enums import BugSharingPolicy

    >>> def current_user():
    ...     return getUtility(ILaunchBag).user
    ...

    >>> login("test@canonical.com")
    >>> product = factory.makeProduct(
    ...     displayname="Proprietary Product",
    ...     name="proprietary-product",
    ...     bug_sharing_policy=BugSharingPolicy.PROPRIETARY,
    ... )
    >>> other_product = factory.makeProduct(
    ...     official_malone=True,
    ...     bug_sharing_policy=BugSharingPolicy.PROPRIETARY,
    ... )
    >>> other_product_name = other_product.name
    >>> params = CreateBugParams(
    ...     title="a test private bug",
    ...     comment="a description of the bug",
    ...     information_type=InformationType.PROPRIETARY,
    ...     owner=current_user(),
    ... )
    >>> private_bug = product.createBug(params)
    >>> logout()

    >>> browser.open(canonical_url(private_bug, rootsite="bugs"))
    >>> browser.getLink(url="+choose-affected-product").click()
    >>> browser.getControl(name="field.product").value = other_product_name
    >>> browser.getControl("Continue").click()
    >>> print(browser.url)  # noqa
    http://bugs.launchpad.test/proprietary-product/+bug/.../+choose-affected-product

    >>> print_feedback_messages(browser.contents)
    There is 1 error.
    This proprietary bug already affects Proprietary Product.
    Proprietary bugs cannot affect multiple projects.


Forwarding bugs upstream
========================

The +choose-affected-product page is, in fact, a wizard-like page which
allows the user to select the affected product, specify a remote bug URL
and create the actual bugtask/watch (also creating the bugtracker if
necessary).

Trying to add an upstream task to a bug on the evolution package in
Ubuntu will cause the product-selection step to be skipped because the
package is linked to the evolution upstream product.

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/+source/evolution/+bug/6"
    ... )
    >>> user_browser.getLink(url="+choose-affected-product").click()
    >>> user_browser.getControl("Project").value
    Traceback (most recent call last):
    ...
    LookupError: label ...'Project'
    ...

    >>> user_browser.getControl(name="field.product").value
    'evolution'

If this wasn't what we intended, we can go back to choose another
product, though.

    >>> user_browser.getLink("Choose another project").click()
    >>> print(user_browser.url)  # noqa
    http://bugs.launchpad.test/ubuntu/+source/evolution/+bug/6/+choose-affected-product?field.product=evolution

    >>> user_browser.getControl("Project").value
    'evolution'

Just in case we change our mind, there is a cancel link that points back
to the bug page:

    >>> cancel_link = user_browser.getLink("Cancel")
    >>> print(cancel_link.url)
    http://bugs.launchpad.test/ubuntu/+source/evolution/+bug/6

But we'll choose Thunderbird.

    >>> user_browser.getControl("Project").value = "thunderbird"
    >>> user_browser.getControl("Continue").click()

Since Thunderbird doesn't use Launchpad, a form is shown asking for bug
URLs and suchlike:

    >>> from lp.bugs.tests.bug import print_upstream_linking_form
    >>> print_upstream_linking_form(user_browser)
    (*) I have the URL for the upstream bug:
        [          ]
    ( ) I have already emailed an upstream bug contact:
        [          ]
    ( ) I want to add this upstream project to the bug report, but
        someone must find or report this bug in the upstream bug
        tracker.

We can just link upstream without a URL to say that this has been dealt
with, but we can't reference it.

    >>> user_browser.getControl("I want to add this upstream").selected = True
    >>> print_upstream_linking_form(user_browser)
    ( ) I have the URL for the upstream bug:
        [          ]
    ( ) I have already emailed an upstream bug contact:
        [          ]
    (*) I want to add this upstream project to the bug report, but
        someone must find or report this bug in the upstream bug
        tracker.

    >>> user_browser.getControl("Add to Bug Report").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/thunderbird/+bug/6

Let's add the evolution task as well.

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/+source/evolution/+bug/6"
    ... )
    >>> user_browser.getLink(url="+choose-affected-product").click()
    >>> print(user_browser.url)
    http://.../ubuntu/+source/evolution/+bug/6/+choose-affected-product

    >>> user_browser.getControl("Add to Bug Report").click()

    >>> print(user_browser.url)
    http://bugs.launchpad.test/evolution/+bug/6


Error messages
--------------

If we try to add an upstream task without specifying a product:

    >>> user_browser.open(
    ...     "http://launchpad.test/debian/+source/mozilla-firefox/+bug/3"
    ... )
    >>> user_browser.getLink(url="+choose-affected-product").click()
    >>> print(user_browser.url)
    http://.../debian/+source/mozilla-firefox/+bug/3/+choose-affected-product

    >>> user_browser.getControl("Project").value
    ''

    >>> user_browser.getControl("Continue").click()
    >>> print(user_browser.url)
    http://.../debian/+source/mozilla-firefox/+bug/3/+choose-affected-product

We get a nice error message.

    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    Required input is missing.

If we enter a product name that doesn't exist, we inform the user about
this and ask them to search for the product.

    >>> user_browser.getControl("Project").value = "no-such-product"
    >>> user_browser.getControl("Continue").click()
    >>> print(user_browser.url)
    http://.../debian/+source/mozilla-firefox/+bug/3/+choose-affected-product

    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    There is no project in Launchpad named "no-such-product"...

    >>> search_link = user_browser.getLink("search for it")
    >>> print(search_link.url)
    http://bugs.launchpad.test/projects

Since we don't restrict the input, the user can write anything, so we
need to make sure that everything is quoted before displaying the input.

    >>> user_browser.open(
    ...     "http://launchpad.test/debian/+source/mozilla-firefox/+bug/3"
    ...     "/+choose-affected-product"
    ... )

    >>> user_browser.getControl("Project").value = (
    ...     b"N\xc3\xb6 Such Product&<>"
    ... )
    >>> user_browser.getControl("Continue").click()
    >>> print(user_browser.url)
    http://.../debian/+source/mozilla-firefox/+bug/3/+choose-affected-product

    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    There is no project in Launchpad named "N... Such Product&amp;&lt...


Linking to bug watches
----------------------

Now we add an upstream task, while adding this new bugtask we can also
specify a bug watch. If we inadvertently left some leading or trailing
white space in the bug URL it will be stripped.

    >>> user_browser.open(
    ...     "http://launchpad.test/debian/+source/mozilla-firefox/"
    ...     "+bug/3/+choose-affected-product"
    ... )
    >>> user_browser.getControl("Project").value = "alsa-utils"
    >>> user_browser.getControl("Continue").click()

    >>> user_browser.getControl("I have the URL").selected = True
    >>> user_browser.getControl(name="field.bug_url").value = (
    ...     "   https://bugzilla.mozilla.org/show_bug.cgi?id=1234   "
    ... )
    >>> user_browser.getControl("Add to Bug Report").click()

Launchpad redirects to the newly created bugtask page, with a row for
the new bug watch.

    >>> print(user_browser.url)
    http://bugs.launchpad.test/alsa-utils/+bug/3

    >>> affects_table = find_tags_by_class(user_browser.contents, "listing")[
    ...     0
    ... ]
    >>> target_cell = affects_table.tbody.tr.td

    >>> from lp.bugs.tests.bug import print_bug_affects_table
    >>> print_bug_affects_table(user_browser.contents)
    alsa-utils
    ...

And we can check that the remote bug number was stripped.

    >>> user_browser.getLink("mozilla.org #1234")
    <Link text='mozilla.org #1234'
      url='https://bugzilla.mozilla.org/show_bug.cgi?id=1234'>

And now we try to add the same upstream again.

    >>> user_browser.getLink(url="+choose-affected-product").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/alsa-utils/+bug/3/+choose-affected-product

    >>> user_browser.getControl("Project").value = "alsa-utils"
    >>> user_browser.getControl("Continue").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/alsa-utils/+bug/3/+choose-affected-product

We get a nice error message.

    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    A fix for this bug has already been requested for alsa-utils

We can add another upstream to the bug.

    >>> user_browser.getControl("Project").value = "evolution"
    >>> user_browser.getControl("Continue").click()
    >>> user_browser.getControl("Add to Bug Report").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/evolution/+bug/3

But if we try to change it to the target of an existing upstream
bugtask, our validator springs into action.

    >>> user_browser.getLink(url="evolution/+bug/3/+editstatus").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/evolution/+bug/3/+editstatus

    >>> user_browser.getControl(name="evolution.target.product").value = (
    ...     "alsa-utils"
    ... )
    >>> user_browser.getControl("Save Changes").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/evolution/+bug/3/+editstatus

    >>> print_feedback_messages(user_browser.contents)
    There is 1 error in the data you entered...
    A fix for this bug has already been requested for alsa-utils


Adding bugtask with bug watch
=============================


HTTP & HTTPS URLs
-----------------

When adding a bug watch together with a new bugtask, you have to enter
the URL of the remote bug.

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/firefox/+bug/4/"
    ...     "+choose-affected-product"
    ... )
    >>> user_browser.getControl("Project").value = "gnome-terminal"
    >>> user_browser.getControl("Continue").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/firefox/+bug/4/+choose-affected-product

    >>> user_browser.getControl("I have the URL").selected = True
    >>> user_browser.getControl(name="field.bug_url").value = (
    ...     "http://bugzilla.gnome.org/bugs/show_bug.cgi?id=42"
    ... )

At this point, just in case we change our mind, there is a cancel link
that points back to the bug page:

    >>> cancel_link = user_browser.getLink("Cancel")
    >>> print(cancel_link.url)
    http://bugs.launchpad.test/firefox/+bug/4

But we're happy, so we add the bug watch.

    >>> user_browser.getControl("Add to Bug Report").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/gnome-terminal/+bug/4

    >>> bug_watches = find_portlet(
    ...     user_browser.contents, "Remote bug watches"
    ... )
    >>> for li in bug_watches("li"):
    ...     print(li.find_all("a")[0].decode_contents())
    ...
    gnome-bugzilla #42

It's possible to supply an HTTPS URL, even though the bug tracker's base
URL is HTTP.

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/firefox/+bug/4/"
    ...     "+choose-affected-product"
    ... )
    >>> user_browser.getControl("Project").value = "netapplet"
    >>> user_browser.getControl("Continue").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/firefox/+bug/4/+choose-affected-product

    >>> user_browser.getControl("I have the URL").selected = True
    >>> user_browser.getControl(name="field.bug_url").value = (
    ...     "https://bugzilla.gnome.org/bugs/show_bug.cgi?id=84"
    ... )
    >>> user_browser.getControl("Add to Bug Report").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/netapplet/+bug/4

The URL was automatically converted to HTTP:

    >>> bug_watches = find_portlet(
    ...     user_browser.contents, "Remote bug watches"
    ... )
    >>> for li in bug_watches("li"):
    ...     print(li.find_all("a")[0]["href"])
    ...
    http://bugzilla.gnome.org/bugs/show_bug.cgi?id=42
    http://bugzilla.gnome.org/bugs/show_bug.cgi?id=84

If the URL can't be recognised (i.e., we don't even know what bug
tracker type it is), an error message is displayed.

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/firefox/+bug/4/"
    ...     "+choose-affected-product"
    ... )
    >>> user_browser.getControl("Project").value = "alsa-utils"
    >>> user_browser.getControl("Continue").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/firefox/+bug/4/+choose-affected-product

    >>> user_browser.getControl("I have the URL").selected = True
    >>> user_browser.getControl(name="field.bug_url").value = (
    ...     "http://bugs.unknown/42"
    ... )
    >>> user_browser.getControl("Add to Bug Report").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/firefox/+bug/4/+choose-affected-product

    >>> for message in find_tags_by_class(user_browser.contents, "message"):
    ...     print(message.decode_contents())
    ...
    There is 1 error.
    Launchpad does not recognize the bug tracker at this URL.

If the URL can be recognised as a valid bug URL, but no such tracker is
registered in Launchpad, the user will be prompted to register it first.

    >>> user_browser.getControl("I have the URL").selected = True
    >>> user_browser.getControl(name="field.bug_url").value = (
    ...     "http://new.trac/ticket/42"
    ... )
    >>> user_browser.getControl("Add to Bug Report").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/firefox/+bug/4/+choose-affected-product

    >>> print_feedback_messages(user_browser.contents)
    The bug tracker with the given URL is not registered in Launchpad.
    Would you like to register it now?

As before, if we change our mind, we can back out if we want.

    >>> cancel_link = user_browser.getLink("Cancel")
    >>> print(cancel_link.url)
    http://bugs.launchpad.test/firefox/+bug/4

Now the user confirms they want us to register the bug tracker for them
and we do that before creating the new bug watch.

    >>> user_browser.getControl("Register Bug Tracker").click()

The bug watch is linked, and we're redirected to the bug's page.

    >>> print(user_browser.url)
    http://bugs.launchpad.test/alsa-utils/+bug/4

The bug tracker and bug watch were added. We can see that the bugtracker
has a special name, starting with 'auto-', to indicate that it was
registered automatically.

    >>> bug_watches = find_portlet(
    ...     user_browser.contents, "Remote bug watches"
    ... )
    >>> for li in bug_watches("li"):
    ...     print(li.find_all("a")[0].decode_contents())
    ...
    gnome-bugzilla #42
    gnome-bugzilla #84
    auto-new.trac #42

If the user does not specify the base url's schema at all, we complete
it to HTTP on their behalf:

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/firefox/+bug/4/"
    ...     "+choose-affected-product"
    ... )
    >>> user_browser.getControl("Project").value = "thunderbird"
    >>> user_browser.getControl("Continue").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/firefox/+bug/4/+choose-affected-product

    >>> user_browser.getControl("I have the URL").selected = True
    >>> user_browser.getControl(name="field.bug_url").value = (
    ...     "bugzilla.gnome.org/bugs/show_bug.cgi?id=168"
    ... )
    >>> user_browser.getControl("Add to Bug Report").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/thunderbird/+bug/4

    >>> bug_watches = find_portlet(
    ...     user_browser.contents, "Remote bug watches"
    ... )
    >>> for li in bug_watches("li"):
    ...     print(li.find_all("a")[0]["href"])
    ...
    http://bugzilla.gnome.org/bugs/show_bug.cgi?id=168
    http://bugzilla.gnome.org/bugs/show_bug.cgi?id=42
    http://bugzilla.gnome.org/bugs/show_bug.cgi?id=84
    http://new.trac/ticket/42


Email Addresses
---------------

Similar things happen when the upstream link is an email address:

    >>> user_browser.open(
    ...     "http://bugs.launchpad.test/jokosher/+bug/12/"
    ...     "+choose-affected-product"
    ... )
    >>> user_browser.getControl("Project").value = "gnome-terminal"
    >>> user_browser.getControl("Continue").click()

    >>> user_browser.getControl("I have already emailed").selected = True
    >>> user_browser.getControl(
    ...     name="field.upstream_email_address_done"
    ... ).value = "dark-master-o-bugs@mylittlepony.com"

    >>> from lp.bugs.tests.bug import print_upstream_linking_form
    >>> print_upstream_linking_form(user_browser)
    ( ) I have the URL for the upstream bug:
        [          ]
    (*) I have already emailed an upstream bug contact:
        [dark-master-o-bugs@mylittlepony.com]
    ( ) I want to add this upstream project to the bug report, but
        someone must find or report this bug in the upstream bug
        tracker.

The bug tracker is automatically created without asking for
confirmation.

    >>> user_browser.getControl("Add to Bug Report").click()
    >>> print(user_browser.url)
    http://bugs.launchpad.test/gnome-terminal/+bug/12

    >>> def print_remote_bug_watches_portlet(browser):
    ...     bug_watches = find_portlet(browser.contents, "Remote bug watches")
    ...     for li in bug_watches("li"):
    ...         print(" ".join(extract_text(li).splitlines()))
    ...         bug_watch_link = li.find("a", {"class": "link-external"})
    ...         if bug_watch_link is None:
    ...             print("  --> None")
    ...         else:
    ...             print("  --> %s" % bug_watch_link.get("href"))
    ...

    >>> import re
    >>> def print_assigned_bugtasks(browser):
    ...     bugtasks = (
    ...         find_main_content(browser.contents)
    ...         .find("table", attrs={"class": "listing"})
    ...         .tbody("tr", id=re.compile("^tasksummary[0-9]+$"))
    ...     )
    ...     for bugtask in bugtasks:
    ...         cells = bugtask("td", recursive=False)
    ...         if len(cells) != 6:
    ...             continue
    ...         affects = extract_text(cells[1])
    ...         assignee = extract_text(cells[-2])
    ...         if assignee and not "Unassigned" in assignee:
    ...             assignee_link = cells[-2].a
    ...             if assignee_link is None:
    ...                 print("%s -->\n  %s" % (affects, assignee))
    ...             else:
    ...                 print(
    ...                     "%s -->\n  %s\n  %s"
    ...                     % (affects, assignee, assignee_link["href"])
    ...                 )
    ...

    >>> print_remote_bug_watches_portlet(user_browser)
    auto-dark-master-o-bugs...
      --> mailto:dark-master-o-bugs@mylittlepony.com

    >>> print_assigned_bugtasks(user_browser)
    GNOME Terminal ... -->
      auto-dark-master-o-bugs
      mailto:dark-master-o-bugs@mylittlepony.com

    >>> user_browser.contents.count(
    ...     "mailto:dark-master-o-bugs@mylittlepony.com"
    ... )
    3

To evade harvesting, the email address above is obfuscated if you're not
logged in.

    >>> anon_browser.open(user_browser.url)
    >>> print_remote_bug_watches_portlet(anon_browser)
    auto-dark-master-o-bugs...
      --> None

    >>> print_assigned_bugtasks(anon_browser)
    GNOME Terminal -->
      auto-dark-master-o-bugs

    >>> anon_browser.contents.count(
    ...     "mailto:dark-master-o-bugs@mylittlepony.com"
    ... )
    0
