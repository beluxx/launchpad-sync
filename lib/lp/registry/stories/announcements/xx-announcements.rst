Announcements
=============

Projects can publish a list of news and announcements on Launchpad. The
list is available as a portlet on the project home page, as well as on a
dedicated batched page showing all announcements, and as an RSS/Atom
news feed.

    >>> from datetime import (
    ...     datetime,
    ...     timedelta,
    ... )
    >>> import feedparser
    >>> from lp.services.beautifulsoup import (
    ...     BeautifulSoup,
    ...     SoupStrainer,
    ... )
    >>> from lp.services.feeds.tests.helper import parse_ids, parse_links

    >>> NOANNOUNCE = "no announcements for this project"
    >>> def latest_news(content):
    ...     """The contents of the latest news portlet."""
    ...     return extract_text(find_portlet(content, "Announcements"))
    ...
    >>> def count_show_links(content):
    ...     """Is the "Read more announcements" link shown?"""
    ...     return len(find_tags_by_class(content, "menu-link-announcements"))
    ...
    >>> def no_announcements(content):
    ...     """Verify there are no announcements in page content."""
    ...     return NOANNOUNCE in extract_text(find_main_content(content))
    ...
    >>> def announcements(content):
    ...     """Return the text of the announcement listings."""
    ...     announcements = find_tag_by_id(content, "announcements")
    ...     if announcements is None:
    ...         return ""
    ...     return extract_text(announcements)
    ...


Making an announcement
----------------------

If you are not logged in, you don't see the link to make an
announcement, neither on the pillar page nor on the announcements
page.

    >>> anon_browser.open("http://launchpad.test/firefox")
    >>> anon_browser.getLink("Make announcement")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> anon_browser.getLink("Read all announcements").click()
    >>> anon_browser.getLink("Make announcement")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> anon_browser.open("http://launchpad.test/ubuntu")
    >>> anon_browser.getLink("Make announcement")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> anon_browser.getLink("Read all announcements").click()
    >>> anon_browser.getLink("Make announcement")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError


Logged in users can only see it if they have launchpad.Edit on the
pillar.

    >>> nopriv_browser = setupBrowser(auth="Basic no-priv@canonical.com:test")
    >>> nopriv_browser.open("http://launchpad.test/firefox")
    >>> nopriv_browser.getLink("Make announcement")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> nopriv_browser.getLink("Read all announcements").click()
    >>> nopriv_browser.getLink("Make announcement")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> priv_browser = setupBrowser(auth="Basic mark@example.com:test")
    >>> priv_browser.open("http://launchpad.test/ubuntu")
    >>> link = priv_browser.getLink("Make announcement")
    >>> print(link.text)
    Make announcement

    >>> priv_browser.getLink("Read all announcements").click()
    >>> link = priv_browser.getLink("Make announcement")
    >>> print(link.text)
    Make announcement

    >>> priv_browser.open("http://launchpad.test/firefox")
    >>> link = priv_browser.getLink("Make announcement")
    >>> print(link.text)
    Make announcement

    >>> priv_browser.getLink("Read all announcements").click()
    >>> link = priv_browser.getLink("Make announcement")
    >>> print(link.text)
    Make announcement


Following the action link takes you to a form where you can make the
announcement:

    >>> priv_browser.open("http://launchpad.test/apache")
    >>> priv_browser.getLink("Make announcement").click()
    >>> priv_browser.getControl(
    ...     "Headline"
    ... ).value = "Apache announcement headline"
    >>> priv_browser.getControl(
    ...     "Summary"
    ... ).value = "Apache announcement summary"
    >>> priv_browser.getControl(
    ...     "URL"
    ... ).value = "http://apache.org/announcement/rocking/"
    >>> priv_browser.getControl("Make announcement").click()

Making the announcement takes the user back to the main page for the
project.

    >>> print(priv_browser.url)
    http://launchpad.test/apache
    >>> print(priv_browser.title)
    Apache in Launchpad

We'll repeat the process for Tomcat, an IProduct that is part of the
Apache project, but this time we won't specify a URL, and we will
specify a date the announcement was made:

    >>> priv_browser.open("http://launchpad.test/tomcat")

Because Tomcat is part of the Apache group, it picks up on the Apache
announcement so there is a "Latest news" portlet. Let's render the
portlet, taking care not to render today's date which would timebomb our
script.

    >>> print(backslashreplace(latest_news(priv_browser.contents)))
    Announcements
    Apache announcement headline...
    Read all announcements
    Make announcement

Add another one, this time specifying a date in the past, which should
work too:

    >>> priv_browser.getLink("Make announcement").click()
    >>> priv_browser.getControl(
    ...     "Headline"
    ... ).value = "Tomcat announcement headline"
    >>> priv_browser.getControl(
    ...     "Summary"
    ... ).value = "Tomcat announcement summary"
    >>> priv_browser.getControl("specific date and time").click()
    >>> priv_browser.getControl(
    ...     name="field.publication_date.announcement_date"
    ... ).value = "2007-11-24 09:00:00"
    >>> priv_browser.getControl("Make announcement").click()
    >>> print(priv_browser.title)
    Tomcat in Launchpad

And check out the results:

    >>> print(backslashreplace(latest_news(priv_browser.contents)))
    Announcements
    Apache announcement headline ...
    Tomcat announcement headline on 2007-11-24 ...
    Read all announcements
    Make announcement

Let's make sure that the announcement is presented as a link.

    >>> print(priv_browser.getLink("Tomcat announcement headline").url)
    http://launchpad.test/tomcat/+announcement/...

We'll repeat the process for Derby, an IProduct that is part of the
Apache project, but this time we won't specify a URL, and we'll make the
announcement immediately:

    >>> priv_browser.open("http://launchpad.test/derby")
    >>> "Derby announcement" in latest_news(priv_browser.contents)
    False
    >>> priv_browser.getLink("Make announcement").click()
    >>> priv_browser.getControl(
    ...     "Headline"
    ... ).value = "Derby announcement headline"
    >>> priv_browser.getControl(
    ...     "Summary"
    ... ).value = "Derby announcement summary"
    >>> priv_browser.getControl("Make announcement").click()
    >>> print(priv_browser.title)
    Derby in Launchpad
    >>> "Derby announcement" in latest_news(priv_browser.contents)
    True

We'll repeat the process for Jokosher, an IProduct that is not part of
any project, but this time we won't specify a URL, and we will specify a
date in the future when the announcement will be made:

    >>> priv_browser.open("http://launchpad.test/jokosher")
    >>> priv_browser.getLink("Make announcement").click()
    >>> priv_browser.getControl(
    ...     "Headline"
    ... ).value = "Jokosher announcement headline"
    >>> priv_browser.getControl(
    ...     "Summary"
    ... ).value = "Jokosher announcement summary"
    >>> priv_browser.getControl("specific date and time").click()
    >>> priv_browser.getControl(
    ...     name="field.publication_date.announcement_date"
    ... ).value = (datetime.now() + timedelta(days=1)).isoformat()
    >>> priv_browser.getControl("Make announcement").click()
    >>> print(priv_browser.title)
    Jokosher in Launchpad
    >>> "Jokosher announcement" in latest_news(priv_browser.contents)
    True

And again for Kubuntu, an IDistribution, but this time we won't specify
a date for the announcement at all:

    >>> priv_browser.open("http://launchpad.test/kubuntu")
    >>> priv_browser.getLink("Make announcement").click()
    >>> priv_browser.getControl(
    ...     "Headline"
    ... ).value = "Kubuntu announcement headline"
    >>> priv_browser.getControl(
    ...     "Summary"
    ... ).value = "Kubuntu announcement summary"
    >>> priv_browser.getControl("some time in the future").click()
    >>> priv_browser.getControl("Make announcement").click()
    >>> print(priv_browser.title)
    Kubuntu in Launchpad
    >>> "Kubuntu announcement" in latest_news(priv_browser.contents)
    True

And finally for RedHat, an IDistribution, with immediate announcement:

    >>> priv_browser.open("http://launchpad.test/redhat")
    >>> priv_browser.getLink("Make announcement").click()
    >>> priv_browser.getControl(
    ...     "Headline"
    ... ).value = "RedHat announcement headline"
    >>> priv_browser.getControl(
    ...     "Summary"
    ... ).value = "RedHat announcement summary"
    >>> priv_browser.getControl("Make announcement").click()
    >>> print(priv_browser.title)
    Red Hat in Launchpad
    >>> "RedHat announcement" in latest_news(priv_browser.contents)
    True


Showing announcements
---------------------

Announcements have their own simple page where they are displayed. This
page is visible to anonymous users when the announcement is published.

We will use the privileged user to get the link URL to the page that
shows the Kubuntu announcement, then try to open the page with the
anon_browser.

    >>> priv_browser.open("http://launchpad.test/kubuntu/+announcements")
    >>> priv_browser.getLink("Kubuntu announcement headline").click()
    >>> link_url = priv_browser.url
    >>> anon_browser.open(link_url)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

We will show that the anonymous user can see an announcement that was
published:

    >>> anon_browser.open("http://launchpad.test/apache/+announcements")
    >>> anon_browser.getLink("Derby announcement headline").click()
    >>> print(anon_browser.title)
    Derby announcement headline : Derby

The page shows the announcement and it has a link back to the announcements
page that any user can navigate.

    >>> content = find_main_content(anon_browser.contents)
    >>> print(extract_text(content.h1))
    Derby announcement headline

    >>> print(extract_text(content.find_all("p")[1]))
    Derby announcement summary

    >>> anon_browser.getLink("Read all announcements").click()
    >>> print(anon_browser.title)
    News and announcements...


Listings
--------

There is a listing page, +announcements, for each pillar that has
announcements. We will verify that the page is present and that it works
as expected.

When there are no announcements for a product, there is no link.

    >>> anon_browser.open("http://launchpad.test/netapplet")
    >>> count_show_links(anon_browser.contents)
    0

When there are no announcements for a project, we should not see
any links to show announcements.

    >>> anon_browser.open("http://launchpad.test/gnome")
    >>> count_show_links(anon_browser.contents)
    0

Distribution pages may have the link in the annoucements portlet,

    >>> anon_browser.open("http://launchpad.test/ubuntu")
    >>> count_show_links(anon_browser.contents)
    1

But we do see it when there are published announcements.

    >>> anon_browser.open("http://launchpad.test/apache")
    >>> count_show_links(anon_browser.contents)
    1
    >>> anon_browser.open("http://launchpad.test/tomcat")
    >>> count_show_links(anon_browser.contents)
    1
    >>> anon_browser.open("http://launchpad.test/redhat")
    >>> count_show_links(anon_browser.contents)
    1

Let's make sure the page is useful when there are no announcements!

    >>> anon_browser.open("http://launchpad.test/netapplet/+announcements")
    >>> no_announcements(anon_browser.contents)
    True

Now, let's look at the announcements we created earlier.

First, lets take a look at Kubuntu. The announcement we made there was
to be published "some time in the future" so it should not be visible to
a user who is not logged in:

    >>> anon_browser.open("http://launchpad.test/kubuntu/+announcements")
    >>> no_announcements(anon_browser.contents)
    True
    >>> "Kubuntu announcement" in announcements(anon_browser.contents)
    False

Nor should it be visible to a user who has nothing to do with the
project so does not have any permissions there:

    >>> nopriv_browser.open("http://launchpad.test/kubuntu/+announcements")
    >>> no_announcements(nopriv_browser.contents)
    True
    >>> "Kubuntu announcement" in announcements(nopriv_browser.contents)
    False

However, if we are an admin of the project, then we should see the
announcement, ready to be edited or published:

    >>> priv_browser.open("http://launchpad.test/kubuntu/+announcements")
    >>> no_announcements(priv_browser.contents)
    False
    >>> "Kubuntu announcement" in announcements(priv_browser.contents)
    True

Since this announcement has no confirmed publishing date, we should see
an alert to that effect:

    >>> "No publishing date set" in announcements(priv_browser.contents)
    True

We can publish this announcement immediately.

    >>> priv_browser.getLink("Kubuntu announcement headline").click()
    >>> priv_browser.getLink("Publish announcement").click()
    >>> print(priv_browser.title)
    Publish announcement : Kubuntu announcement headline : Kubuntu
    >>> print(priv_browser.url)
    http://launchpad.test/kubuntu/+announceme.../+publish
    >>> radio = priv_browser.getControl(name="field.publication_date.action")
    >>> radio.value = ["immediately"]
    >>> priv_browser.getControl("Publish").click()

Doing so takes us back to the list of announcements.

    >>> print(priv_browser.title)
    News and announcements...

And since the announcement has been made, the everybody can now see
it too:

    >>> anon_browser.open("http://launchpad.test/kubuntu/+announcements")
    >>> no_announcements(anon_browser.contents)
    False
    >>> "Kubuntu announcement" in announcements(anon_browser.contents)
    True


Now let's check the announcement listings on products and projects.

First, we made an announcement for Jokosher, which is to be made in the
future.

Anonymous users should not see it.

    >>> anon_browser.open("http://launchpad.test/jokosher/+announcements")
    >>> no_announcements(anon_browser.contents)
    True
    >>> "Jokosher announcement" in announcements(anon_browser.contents)
    False

However, we should see it if we have admin permissions for Jokosher:

    >>> priv_browser.open("http://launchpad.test/jokosher/+announcements")
    >>> no_announcements(priv_browser.contents)
    False
    >>> "Jokosher announcement" in announcements(priv_browser.contents)
    True

Now, let's take a look at announcements on the Apache project.

We made three relevant announcements:

  1. On apache, published immediately
  2. On Tomcat, published at a date in the past
  3. On Derby, published immediately

Since a project publishes all the news for itself and for each of the
projects that are part of it, all three should be visible to the public
on Apache's announcements page:

    >>> anon_browser.open("http://launchpad.test/apache/+announcements")
    >>> no_announcements(anon_browser.contents)
    False
    >>> "Apache announcement" in announcements(anon_browser.contents)
    True
    >>> "Tomcat announcement" in announcements(anon_browser.contents)
    True
    >>> "Derby announcement" in announcements(anon_browser.contents)
    True

Let's take a look at the Tomcat page. We should see the Tomcat
announcement, and the Apache (group) announcement, but not the Derby
announcement:

    >>> anon_browser.open("http://launchpad.test/tomcat/+announcements")
    >>> no_announcements(anon_browser.contents)
    False
    >>> "Apache announcement" in announcements(anon_browser.contents)
    True
    >>> "Tomcat announcement" in announcements(anon_browser.contents)
    True
    >>> "Derby announcement" in announcements(anon_browser.contents)
    False

Finally, there is a page for all announcements across all projects
hosted in Launchpad:

    >>> anon_browser.open("http://launchpad.test/+announcements")
    >>> "Announcements from all projects" in anon_browser.title
    True
    >>> "Kubuntu announcement" in announcements(anon_browser.contents)
    True
    >>> "RedHat announcement " in announcements(anon_browser.contents)
    True
    >>> "Derby announcement " in announcements(anon_browser.contents)
    True
    >>> "Apache announcement " in announcements(anon_browser.contents)
    True

The announcements are batched so only the latest four are shown,
leaving Tomcat out:

    >>> print(extract_text(anon_browser.contents))
    Announcements from all projects hosted in Launchpad
    ...
    1...4 of 25 results
    ...

    >>> "Tomcat announcement " in announcements(anon_browser.contents)
    False

It excludes future announcements too:

    >>> "Jokosher announcement" in announcements(anon_browser.contents)
    False


Editing announcements
---------------------

The announcement listing page does not have editing links.  They are
available on the individual announcement pages.

    >>> priv_browser.open("http://launchpad.test/tomcat/+announcements")
    >>> print(priv_browser.getLink("Read more").url)
    http://apache.org/announcement/rocking/
    >>> priv_browser.getLink("Apache announcement headline").click()
    >>> priv_browser.getLink("Modify announcement").click()
    >>> print(priv_browser.title)
    Modify announcement : Apache announcement headline : Apache
    >>> headline = priv_browser.getControl("Headline")
    >>> print(headline.value)
    Apache announcement headline
    >>> headline.value = "Modified headline"
    >>> summary = priv_browser.getControl("Summary")
    >>> print(summary.value)
    Apache announcement summary
    >>> summary.value = "Modified summary"
    >>> url = priv_browser.getControl("URL")
    >>> print(url.value)
    http://apache.org/announcement/rocking/
    >>> url.value = "http://apache.org/modified/url/"
    >>> priv_browser.getControl("Modify").click()
    >>> print(priv_browser.title)
    News and announcements...
    >>> priv_browser.open("http://launchpad.test/tomcat/+announcements")
    >>> "Modified headline" in announcements(priv_browser.contents)
    True
    >>> "Modified summary" in announcements(priv_browser.contents)
    True
    >>> print(priv_browser.getLink("Read more").url)
    http://apache.org/modified/url/


Retractions
-----------

You can retract an announcement which was previously announced.

    >>> priv_browser.open("http://launchpad.test/kubuntu/+announcements")
    >>> "Kubuntu announcement " in announcements(priv_browser.contents)
    True
    >>> "Retracted" in announcements(priv_browser.contents)
    False
    >>> priv_browser.getLink("Kubuntu announcement headline").click()
    >>> priv_browser.getLink("Delete announcement").click()
    >>> priv_browser.getLink("retracting the announcement").click()
    >>> print(priv_browser.title)
    Retract announcement : Kubuntu announcement headline : Kubuntu

Actually clicking "Retract" takes us back to the listing page. The item
is shown as having been retracted if you are a privileged user.

    >>> priv_browser.getControl("Retract").click()
    >>> print(priv_browser.title)
    News and announcements...
    >>> "Kubuntu announcement " in announcements(priv_browser.contents)
    True
    >>> "Retracted" in announcements(priv_browser.contents)
    True

But anonymous users cannot see retracted items:

    >>> anon_browser.open("http://launchpad.test/kubuntu/+announcements")
    >>> no_announcements(anon_browser.contents)
    True
    >>> "Kubuntu announcement" in announcements(anon_browser.contents)
    False

And it has disappeared from the global listing too.

    >>> anon_browser.open("http://launchpad.test/+announcements")
    >>> "Kubuntu announcement" in announcements(anon_browser.contents)
    False

Once something has been retracted, it can be published again.

    >>> priv_browser.getLink("Kubuntu announcement headline").click()
    >>> priv_browser.getLink("Publish announcement").click()
    >>> print(priv_browser.title)
    Publish announcement : Kubuntu announcement headline : Kubuntu
    >>> radio = priv_browser.getControl(name="field.publication_date.action")
    >>> radio.value = ["immediately"]
    >>> priv_browser.getControl(
    ...     name="field.publication_date.announcement_date"
    ... ).value = ""
    >>> priv_browser.getControl("Publish").click()
    >>> print(priv_browser.title)
    News and announcements...

And once again it is visible to unprivileged users:

    >>> anon_browser.open("http://launchpad.test/kubuntu/+announcements")
    >>> no_announcements(anon_browser.contents)
    False
    >>> "Kubuntu announcement" in announcements(anon_browser.contents)
    True


Retargeting
-----------

If an announcement has been made in one project, and it really belongs
in another, then someone who is an administrator in both places can move
it.

    >>> priv_browser.open("http://launchpad.test/kubuntu/+announcements")
    >>> priv_browser.getLink("Kubuntu announcement headline").click()
    >>> priv_browser.getLink("Move announcement").click()
    >>> print(priv_browser.title)
    Move announcement : Kubuntu announcement headline : Kubuntu
    >>> priv_browser.getControl("For").value = "guadalinex"
    >>> priv_browser.getControl("Retarget").click()
    >>> print(priv_browser.title)
    News and announcements...
    >>> "Kubuntu announcement" in announcements(priv_browser.contents)
    True

However, someone who is not an administrator on the target project will
not be able to move it.

    >>> kamion_browser = setupBrowser(
    ...     auth="Basic colin.watson@ubuntulinux.com:test"
    ... )
    >>> kamion_browser.open("http://launchpad.test/guadalinex/+announcements")
    >>> kamion_browser.getLink("Kubuntu announcement headline").click()
    >>> kamion_browser.getLink("Move announcement").click()
    >>> print(kamion_browser.title)
    Move announcement : Kubuntu announcement headline : GuadaLinex
    >>> kamion_browser.getControl("For").value = "kubuntu"
    >>> kamion_browser.getControl("Retarget").click()
    >>> "don't have permission" in extract_text(
    ...     find_main_content(kamion_browser.contents)
    ... )
    True
    >>> print(kamion_browser.title)
    Move announcement : Kubuntu announcement headline : GuadaLinex


Atom/RSS Feeds
--------------

We publish a feed of news for every IProjectGroup, IProduct and
IDistribution.

The feeds are published even when there are no announcements.

    >>> nopriv_browser.open(
    ...     "http://feeds.launchpad.test/netapplet/announcements.atom"
    ... )
    >>> _ = feedparser.parse(nopriv_browser.contents)
    >>> "NetApplet Announcements" in nopriv_browser.contents
    True

The "self" link should point to the original URL, in the feeds.launchpad.test
domain.

    >>> strainer = SoupStrainer("link", rel="self")
    >>> links = parse_links(nopriv_browser.contents, rel="self")
    >>> for link in links:
    ...     print(link)
    ...
    <link href="http://feeds.launchpad.test/netapplet/announcements.atom"
          rel="self"/>

    >>> for id_ in parse_ids(nopriv_browser.contents):
    ...     print(extract_text(id_))
    ...
    tag:launchpad.net,2005-03-10:/netapplet/+announcements

The feeds include only published announcements. The Jokosher
announcement, which is due in the future, does not show up:

    >>> nopriv_browser.open(
    ...     "http://feeds.launchpad.test/jokosher/announcements.atom"
    ... )
    >>> _ = feedparser.parse(nopriv_browser.contents)
    >>> "Jokosher announcement headline" in nopriv_browser.contents
    False

Retracted items do not show up either.

    >>> nopriv_browser.open(
    ...     "http://feeds.launchpad.test/guadalinex/announcements.atom"
    ... )
    >>> _ = feedparser.parse(nopriv_browser.contents)
    >>> "Kubuntu announcement headline" in nopriv_browser.contents
    True
    >>> for id_ in parse_ids(nopriv_browser.contents):
    ...     print(extract_text(id_))
    ...
    tag:launchpad.net,2006-10-16:/guadalinex/+announcements
    tag:launchpad.net,...:/+announcement/...

    >>> priv_browser.open("http://launchpad.test/guadalinex/+announcements")
    >>> "Kubuntu announcement headline" in (
    ...     announcements(priv_browser.contents)
    ... )
    True
    >>> priv_browser.getLink("Kubuntu announcement headline").click()
    >>> priv_browser.getLink("Delete announcement").click()
    >>> priv_browser.getLink("retracting the announcement").click()
    >>> print(priv_browser.title)
    Retract announcement : Kubuntu announcement headline : GuadaLinex
    >>> priv_browser.getControl("Retract").click()
    >>> nopriv_browser.reload()
    >>> "Kubuntu announcement " in nopriv_browser.contents
    False

And once again, project feeds include news from their constituent
products.

    >>> nopriv_browser.open(
    ...     "http://feeds.launchpad.test/apache/announcements.atom"
    ... )
    >>> _ = feedparser.parse(nopriv_browser.contents)
    >>> "Tomcat announcement headline" in nopriv_browser.contents
    True
    >>> "Modified headline" in nopriv_browser.contents  # apache itself
    True
    >>> "Derby announcement headline" in nopriv_browser.contents
    True
    >>> for id_ in parse_ids(nopriv_browser.contents):
    ...     print(extract_text(id_))
    ...
    tag:launchpad.net,2004-09-24:/apache/+announcements
    tag:launchpad.net,...:/+announcement/...
    tag:launchpad.net,...:/+announcement/...
    tag:launchpad.net,...:/+announcement/...

    >>> strainer = SoupStrainer("link", rel="self")
    >>> links = parse_links(nopriv_browser.contents, rel="self")
    >>> for link in links:
    ...     print(link)
    ...
    <link href="http://feeds.launchpad.test/apache/announcements.atom"
          rel="self"/>

Finally, there is a feed for all announcements across all projects
hosted in Launchpad:

    >>> nopriv_browser.open("http://feeds.launchpad.test/announcements.atom")
    >>> _ = feedparser.parse(nopriv_browser.contents)
    >>> "Announcements published via Launchpad" in nopriv_browser.contents
    True
    >>> "[tomcat] Tomcat announcement headline" in nopriv_browser.contents
    True
    >>> "[apache] Modified headline" in nopriv_browser.contents
    True

It excludes retracted and future announcements too:

    >>> "[guadalinex] Kubuntu announcement headline" in (
    ...     nopriv_browser.contents
    ... )
    False
    >>> "[jokosher] Jokosher announcement headline" in nopriv_browser.contents
    False

The announcements are stored as plain text, but the text-to-html formatter
is used to convert urls into links. The FeedTypedData class must escape
all the html to make it a valid payload for the xml document. IE7 won't
let us use a DTD to define the html entities that standard xml is missing.

    >>> nopriv_browser.open(
    ...     "http://feeds.launchpad.test/ubuntu/announcements.atom"
    ... )
    >>> _ = feedparser.parse(nopriv_browser.contents)
    >>> soup = BeautifulSoup(nopriv_browser.contents)
    >>> soup.find("feed").entry.title
    <...>Ampersand="&amp;" LessThan="&lt;" GreaterThan="&gt;"</title>
    >>> print(soup.find("feed").entry.content)  # noqa
    <...
    Ampersand="&amp;amp;"&lt;br/&gt;
    LessThan="&amp;lt;"&lt;br/&gt;
    GreaterThan="&amp;gt;"&lt;br/&gt;
    Newline="&lt;br/&gt;
    "&lt;br/&gt;
    url="&lt;a href="http://www.ubuntu.com"
    rel="nofollow"&gt;http://&lt;wbr/&gt;www.ubuntu.&lt;wbr/&gt;com&lt;/a&gt;"...


Deletion
--------

An owner can permanently delete an announcement.

    >>> kamion_browser.open("http://launchpad.test/guadalinex/+announcements")
    >>> no_announcements(kamion_browser.contents)
    False
    >>> kamion_browser.getLink("Kubuntu announcement headline").click()
    >>> kamion_browser.getLink("Delete announcement").click()
    >>> print(kamion_browser.title)
    Delete announcement : Kubuntu announcement headline : GuadaLinex
    >>> kamion_browser.getControl("Delete").click()
    >>> print(priv_browser.title)
    News and announcements...
    >>> no_announcements(kamion_browser.contents)
    True
