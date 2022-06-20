Monitoring External Bug Trackers in Launchpad Bugs
==================================================

Malone allows you to monitor bugs in external bug tracking systems. This
document discusses the API of external bug trackers. To learn more about
bug watches, the object that represents the link between a Malone bug
and an external bug, see bugwatch.rst.

    >>> import pytz
    >>> from datetime import datetime, timedelta
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.bugs.interfaces.bugtracker import IBugTrackerSet
    >>> bugtracker_set = getUtility(IBugTrackerSet)
    >>> mozilla_bugzilla = bugtracker_set.getByName('mozilla.org')
    >>> now = datetime.now(pytz.UTC)

    >>> def print_watches(bugtracker):
    ...     watches = sorted(
    ...         bugtracker.watches_needing_update,
    ...         key=lambda watch: (watch.remotebug, watch.bug.id))
    ...
    ...     for bug_watch in watches:
    ...         print("Remote bug: %s LP bug: %s" % (
    ...             bug_watch.remotebug, bug_watch.bug.id))

We must be an admin to modify bug watches later on.

    >>> login('foo.bar@canonical.com')

We can get a list of all the bug tracker's bug watches needing to be
updated. A bug watch is considered to be needing an update when its
next_check time is in the past.

    >>> bug_watches = mozilla_bugzilla.watches
    >>> print(bug_watches.count())
    4

    >>> print(bug_watches[0].remotebug, bug_watches[0].bug.id)
    2000 1
    >>> bug_watches[0].next_check = now - timedelta(hours=1)

    >>> print(bug_watches[1].remotebug, bug_watches[1].bug.id)
    123543 1
    >>> bug_watches[1].lastchecked = now - timedelta(hours=12)

Note that bugtracker.watches may produce multiple watches for the same
remote bug.

    >>> print(bug_watches[2].remotebug, bug_watches[2].bug.id)
    42 1
    >>> bug_watches[2].next_check = now - timedelta(hours=36)

    >>> print(bug_watches[3].remotebug, bug_watches[3].bug.id)
    42 2
    >>> bug_watches[3].next_check = now - timedelta(days=1)

The watches needing updating should the ones with old statuses, 2000 and 42:

    >>> flush_database_updates()
    >>> print_watches(mozilla_bugzilla)
    Remote bug: 2000 LP bug: 1
    Remote bug: 42   LP bug: 1
    Remote bug: 42   LP bug: 2

watches_needing_update will also return bug watches that have
un-pushed bug comments that need pushing to remote bug trackers,
regardless of whether they have been checked recently or not. We'll add
a comment to the bug watch against remote bug 123543 to demonstrate
this.

    >>> import transaction
    >>> from lp.testing.factory import LaunchpadObjectFactory
    >>> factory = LaunchpadObjectFactory()
    >>> message = factory.makeMessage(
    ...     'Unpushed comment', '... is unpushed')

    >>> print(bug_watches[1].remotebug)
    123543

    >>> bug_message = bug_watches[1].addComment(None, message)
    >>> transaction.commit()

    >>> print_watches(mozilla_bugzilla)
    Remote bug: 123543 LP bug: 1
    Remote bug: 2000   LP bug: 1
    Remote bug: 42     LP bug: 1
    Remote bug: 42     LP bug: 2

Once the comment has been pushed to the remote bug the bug watch will no
longer appear in the set returned by watches_needing_update.

    >>> bug_message.remote_comment_id = '1'
    >>> transaction.commit()

    >>> print_watches(mozilla_bugzilla)
    Remote bug: 2000 LP bug: 1
    Remote bug: 42   LP bug: 1
    Remote bug: 42   LP bug: 2


Auto-creating bug trackers
--------------------------

The IBugTrackerSet interface provides a method, ensureBugTracker(),
which will retrieve or create a bug tracker for the parameters passed to
it. If this method is not passed a name parameter when it creates a new
bugtracker it will use make_bugtracker_name() to generate a name for the
bug tracker.

    >>> from lp.bugs.interfaces.bugtracker import BugTrackerType
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> sample_person = getUtility(IPersonSet).getByEmail(
    ...     'test@canonical.com')
    >>> a_bugtracker = bugtracker_set.ensureBugTracker(
    ...     baseurl='http://bugs.example.com', owner=sample_person,
    ...     bugtrackertype=BugTrackerType.BUGZILLA,
    ...     title=None, summary=None, contactdetails=None, name=None)
    >>> print(a_bugtracker.name)
    auto-bugs.example.com

ensureBugTracker() also performs collision-avoidance on the names which
it generates using make_bugtracker_name(). If another bug tracker is
created with the same hostname as a_bugtracker above but different URLs,
the new bugtracker's name will be mutated so that the two names do not
collide.

    >>> a_bugtracker = bugtracker_set.ensureBugTracker(
    ...     baseurl='http://bugs.example.com/ni', owner=sample_person,
    ...     bugtrackertype=BugTrackerType.BUGZILLA,
    ...     title=None, summary=None, contactdetails=None, name=None)
    >>> print(a_bugtracker.name)
    auto-bugs.example.com-1


Top Bug Trackers
----------------

The Malone front page shows a list of the top Malone bug trackers, as
ordered by the number of bugs being monitored by Malone in each of
them. Use IBugTrackerSet.getMostActiveBugTrackers to get this list.

    >>> top_trackers = bugtracker_set.getMostActiveBugTrackers(limit=4)
    >>> for tracker in sorted(
    ...         top_trackers, key=lambda tracker: tracker.watches.count()):
    ...     print('%d: %s' % (tracker.watches.count(), tracker.name))
    1: ubuntu-bugzilla
    2: gnome-bugzilla
    4: mozilla.org
    5: debbugs


Getting Bug Trackers
--------------------

You can get a specific bug tracker from the database by querying by
its base URL.

    >>> ubuntu_bugzilla = bugtracker_set.queryByBaseURL(
    ...     u'http://bugzilla.ubuntu.com/bugs/')
    >>> print(ubuntu_bugzilla.baseurl)
    http://bugzilla.ubuntu.com/bugs/

It's necessary to specify the exact URL, differences in the schema
(http vs. https) and trailing slashes are accepted.

    >>> ubuntu_bugzilla = bugtracker_set.queryByBaseURL(
    ...     u'https://bugzilla.ubuntu.com/bugs')
    >>> print(ubuntu_bugzilla.baseurl)
    http://bugzilla.ubuntu.com/bugs/

If no bug tracker can be found None is returned.

    >>> bugtracker_set.queryByBaseURL('http://no/such/bugtracker') is None
    True


Aliases
-------

A bug tracker can have a number of alias URLs associated with it.

    >>> from lp.bugs.interfaces.bugtracker import IBugTrackerAliasSet
    >>> bugtrackeralias_set = getUtility(IBugTrackerAliasSet)

The most natural way to work with aliases is via the aliases attribute
present on IBugTracker. This can be used to query, set or remove
aliases.

    >>> mozilla_bugzilla.aliases = [
    ...     'https://norwich.example.com/',
    ...     'http://cambridge.example.com/']

    >>> for alias in mozilla_bugzilla.aliases:
    ...     print(alias)
    http://cambridge.example.com/
    https://norwich.example.com/

    >>> mozilla_bugzilla.aliases = []
    >>> mozilla_bugzilla.aliases
    ()

You can assign any iterable (of URL strings) to the aliases attribute,
but, when accessed, aliases is always a regular tuple.

Because this attribute is computed on each access, an immutable object
- a tuple - is returned. This defends against mutations of aliases
where the expectation is that the aliases in the database are changed,
but silently are not. For example, if a plain list were returned, it
might be tempting to append() another alias to it. But this would not
be reflected in the database.

You can also assign None to aliases to remove all aliases. This has
the same effect as assigning an empty list.

    >>> mozilla_bugzilla.aliases = None
    >>> mozilla_bugzilla.aliases
    ()

    >>> mozilla_bugzilla.aliases = set([u'http://set.example.com/'])
    >>> for alias in mozilla_bugzilla.aliases:
    ...     print(alias)
    http://set.example.com/

    >>> mozilla_bugzilla.aliases = (u'http://tuple.example.com/',)
    >>> for alias in mozilla_bugzilla.aliases:
    ...     print(alias)
    http://tuple.example.com/

Your ordering is not preserved; aliases are sorted using Python's
standard unicode ordering.

    >>> mozilla_bugzilla.aliases = (
    ...     u'http://%s.example.com/' % domain
    ...     for domain in '111 zzz ccc ZZZ'.split())
    >>> for alias in mozilla_bugzilla.aliases:
    ...     print(alias)
    http://111.example.com/
    http://ZZZ.example.com/
    http://ccc.example.com/
    http://zzz.example.com/

BugTrackerAliases can also be looked up by bug tracker.

    >>> mozilla_bugzilla.aliases = [
    ...     u'http://just.example.com/',
    ...     u'http://magic.example.com/']

Query by bug tracker:

    >>> from operator import attrgetter
    >>> for alias in sorted(
    ...         bugtrackeralias_set.queryByBugTracker(mozilla_bugzilla),
    ...         key=attrgetter('base_url')):
    ...     print(alias.base_url)
    http://just.example.com/
    http://magic.example.com/

The aliases attribute never contains the current baseurl. For example,
if BugTracker.baseurl is changed to an existing alias of itself, the
aliases attribute hides the baseurl, although it is still recorded as
an alias.

    >>> mozilla_bugzilla.baseurl = u'http://magic.example.com/'
    >>> for alias in mozilla_bugzilla.aliases:
    ...     print(alias)
    http://just.example.com/

    >>> for alias in sorted(
    ...         bugtrackeralias_set.queryByBugTracker(mozilla_bugzilla),
    ...         key=attrgetter('base_url')):
    ...     print(alias.base_url)
    http://just.example.com/
    http://magic.example.com/

    >>> mozilla_bugzilla.baseurl = u'https://bugzilla.mozilla.org/'


Pillars for bugtrackers
-----------------------

    >>> trackers = list(bugtracker_set)
    >>> pillars = bugtracker_set.getPillarsForBugtrackers(trackers)
    >>> for t in pillars:
    ...     print(t.name, pretty([p.name for p in pillars[t]]))
    gnome-bugzilla ['gnome-terminal', 'gnome']


Imported bug messages
---------------------

Each BugTracker has an imported_bug_messages property that returns all
bug messages which have been imported for a given bug tracker.

    >>> def print_bug_messages(bug_messages):
    ...     for bug_message in bug_messages:
    ...         print('* bug: %d' % bug_message.bug.id)
    ...         print('- remote bug: %s' % bug_message.bugwatch.remotebug)
    ...         print('- message subject: %s' % bug_message.message.subject)

The Mozilla Bugzilla has only one imported bug message.

    >>> print_bug_messages(mozilla_bugzilla.imported_bug_messages)
    * bug: 1
    - remote bug: 123543
    - message subject: Unpushed comment

We will forge some BugMessage records before trying again:

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.bugs.interfaces.bugmessage import IBugMessageSet

    >>> for num, bug_watch in enumerate(mozilla_bugzilla.watches):
    ...     bug_message = getUtility(IBugMessageSet).createMessage(
    ...         'You are Number %d.' % (num + 1),
    ...         bug_watch.bug, sample_person)
    ...     removeSecurityProxy(bug_message).bugwatch = bug_watch
    >>> flush_database_updates()

    >>> print_bug_messages(mozilla_bugzilla.imported_bug_messages)
    * bug: 1
    - remote bug: 123543
    - message subject: Unpushed comment
    * bug: 1
    - remote bug: 2000
    - message subject: You are Number 1.
    * bug: 1
    - remote bug: 123543
    - message subject: You are Number 2.
    * bug: 1
    - remote bug: 42
    - message subject: You are Number 3.
    * bug: 2
    - remote bug: 42
    - message subject: You are Number 4.


Filing a bug on the remote tracker
----------------------------------

The IBugTracker interface defines a method to convert product,
component, summary, and description strings into URLs for filing and/or
searching bugs.

    >>> def print_links(links_dict):
    ...     for key in sorted(links_dict):
    ...         print("%s: %s" % (key, links_dict[key]))

    >>> links = mozilla_bugzilla.getBugFilingAndSearchLinks(
    ...     remote_product='testproduct', summary="Foo", description="Bar")
    >>> print_links(links)
    bug_filing_url:
    https://.../enter_bug.cgi?product=testproduct&short_desc=Foo&long_desc=Bar
    bug_search_url:
    https://.../query.cgi?product=testproduct&short_desc=Foo

For the RT tracker we specify a Queue in which to file a ticket.

    >>> example_rt = factory.makeBugTracker(
    ...     'http://rt.example.com', BugTrackerType.RT)
    >>> links = example_rt.getBugFilingAndSearchLinks(
    ...     remote_product='42', summary="Foo", description="Bar")
    >>> print_links(links)
    bug_filing_url:
    http://.../Ticket/Create.html?Queue=42&Subject=Foo&Content=Bar
    bug_search_url:
    http://.../Search/Build.html?Query=Queue = '42' AND Subject LIKE 'Foo'

SourceForge and its kin use a Group ID and an ATID to specify which
product a bug should be filed against. These are stored as an
ampersand-separated string and getBugFilingAndSearchLinks() expects them
to be passed to it in that form. SourceForge-type bug trackers don't accept
summary and description parameters for bug filing, so we don't include them in
the URL for the bug filing form.

    >>> example_sourceforge = factory.makeBugTracker(
    ...     'http://forge.example.com', BugTrackerType.SOURCEFORGE)
    >>> links = example_sourceforge.getBugFilingAndSearchLinks(
    ...     remote_product='123&456', summary='Foo', description='Bar')
    >>> print_links(links)
    bug_filing_url: http://...tracker/?func=add&group_id=123&atid=456
    bug_search_url: .../search/?group_id=123&some_word=Foo&type...artifact

The URL returned by the SourceForge celebrity points to the new version
of the SourceForge bug tracker.

    >>> sourceforge = getUtility(IBugTrackerSet).getByName('sf')
    >>> links = sourceforge.getBugFilingAndSearchLinks(
    ...     remote_product='123&456', summary='Foo', description='Bar')
    >>> print_links(links)
    bug_filing_url: http://.../tracker2/?func=add&group_id=123&atid=456
    bug_search_url: .../search/?group_id=123&some_word=Foo&type...artifact

Savane uses a single group URL parameter to specify which product the
bug should be filed against. Savane ignores the summary and description
parameters altogether, so they aren't included in the URL.

    >>> example_savane = factory.makeBugTracker(
    ...     'http://savane.example.com', BugTrackerType.SAVANE)
    >>> links = example_savane.getBugFilingAndSearchLinks('testproduct')
    >>> print_links(links)
    bug_filing_url: http://.../bugs/?func=additem&group=testproduct
    bug_search_url: http://.../bugs/?func=search&group=testproduct

Some bug trackers will ignore the passed remote_product because they use
static URLs or track only one product.

    >>> example_phpproject = factory.makeBugTracker(
    ...     'http://php.example.com', BugTrackerType.PHPPROJECT)
    >>> links = example_phpproject.getBugFilingAndSearchLinks(
    ...     remote_product='testproduct', summary="Foo", description="Bar")
    >>> print_links(links)
    bug_filing_url: http://.../report.php?in[sdesc]=Foo&in[ldesc]=Bar
    bug_search_url: http://php.example.com/search.php?search_for=Foo

Google Code hosts many projects but each project's bug tracker has a
unique URL, so it too ignores the remote_product parameter.

    >>> example_google_code = factory.makeBugTracker(
    ...     'http://code.google.com/p/myproject/issues',
    ...     BugTrackerType.GOOGLE_CODE)
    >>> links = example_google_code.getBugFilingAndSearchLinks(
    ...     remote_product='testproduct', summary="Foo", description="Bar")
    >>> print_links(links)
    bug_filing_url: http://.../issues/entry?summary=Foo&comment=Bar
    bug_search_url: http://.../issues/list?q=Foo

Trac's bug filing form also accepts data in the query string, so we include
it.

    >>> example_trac = factory.makeBugTracker(
    ...     'http://trac.example.com', BugTrackerType.TRAC)
    >>> links = example_trac.getBugFilingAndSearchLinks(
    ...     remote_product='testproduct', summary="Foo", description="Bar")
    >>> print_links(links)
    bug_filing_url:
      http://trac.example.com/newticket?summary=Foo&description=Bar
    bug_search_url: http://trac.example.com/search?ticket=on&q=Foo

    >>> example_roundup = factory.makeBugTracker(
    ...     'http://roundup.example.com', BugTrackerType.ROUNDUP)
    >>> links = example_roundup.getBugFilingAndSearchLinks(
    ...     remote_product='testproduct', summary="Foo", description="Bar")
    >>> print_links(links)
    bug_filing_url: http://.../issue?@template=item&title=Foo&@note=Bar
    bug_search_url: http://.../issue?@template=search&@search_text=Foo

Mantis tends to ignore query string parameters passed to the search
form, so we don't try.

    >>> example_mantis = factory.makeBugTracker(
    ...     'http://mantis.example.com', BugTrackerType.MANTIS)
    >>> links = example_mantis.getBugFilingAndSearchLinks(
    ...     remote_product='testproduct', summary="Foo", description="Bar")
    >>> print_links(links)
    bug_filing_url: .../bug_..._advanced_page.php?summary=Foo&description=Bar
    bug_search_url: .../view_all_bug_page.php

The EMAILADDRESS BugTrackerType is a special case and returns None for
both filing and searching URLs.

    >>> example_emailaddress = factory.makeBugTracker(
    ...     'http://bork.example.com', BugTrackerType.EMAILADDRESS)
    >>> links = example_emailaddress.getBugFilingAndSearchLinks('testproduct')
    >>> print_links(links)
    bug_filing_url: None
    bug_search_url: None

Debbugs - an email-based bug tracker - doesn't provide a bug filing form.
However, it is possible to obtain a bug search URL for Debbugs-using
products.

    >>> debbugs = getUtility(IBugTrackerSet).getByName('debbugs')
    >>> links = debbugs.getBugFilingAndSearchLinks(
    ...     remote_product='testproduct', summary="Foo", description="Bar")
    >>> print_links(links)
    bug_filing_url: None
    bug_search_url: .../search.cgi?phrase=Foo...&attribute_value=testproduct

You can pass None for the summary and description parameters. It will be
converted to an empty string before it's passed to the remote bug tracker.

    >>> links = mozilla_bugzilla.getBugFilingAndSearchLinks(
    ...     'test', None, None)
    >>> print_links(links)
    bug_filing_url: ...?product=test&short_desc=&long_desc=
    bug_search_url: ...?product=test&short_desc=

The remote_product, summary and description values are URL-encoded to ensure
that the returned URL is valid.

    >>> links = mozilla_bugzilla.getBugFilingAndSearchLinks(
    ...     remote_product='@test&', summary="%&", description="()")
    >>> print_links(links)
    bug_filing_url: ...?product=%40test%26&short_desc=%25%26&long_desc=%28%29
    bug_search_url: ...?product=%40test%26&short_desc=%25%26

getBugFilingAndSearchLinks() will also handle unicode values in the
summary and description correctly.

    >>> links = mozilla_bugzilla.getBugFilingAndSearchLinks(
    ...     remote_product='test', summary=u"\xabHi\xa9",
    ...     description=u"\xa8\xa7")
    >>> print_links(links)
    bug_filing_url: ...&short_desc=%C2%ABHi%C2%A9&long_desc=%C2%A8%C2%A7
    bug_search_url: ...?product=test&short_desc=%C2%ABHi%C2%A9


BugTracker.multi_product
------------------------

As described above, some bug trackers don't need to have a remote
product passed to `getBugFilingAndSearchLinks()` in order to be able to
return a bug filing URL because they use static URLs for bug filing or
only track one product.

`IBugTracker` defines an attribute, `multi_product` which can be used to
check whether a given bug tracker can return a bug filing URL without
being passed a remote product.

Our example Trac bug tracker's `multi_product` property will be False,
since it only tracks one product at a time.

    >>> print(example_trac.multi_product)
    False

However, Bugzilla instances require remote products in order to be able
to return a bug filing URL.

    >>> print(mozilla_bugzilla.multi_product)
    True

There is a test in database/tests/test_bugtracker.py that checks that
the constraints of multi_product=True are not violated by any
BugTracker.

If you try passing remote_product=None to a multi product bugtracker's
getBugFilingAndSearchLinks() method you'll get None back for both URLs,
since a product is required to be able to generate URLs for those bug
trackers.

    >>> print_links(mozilla_bugzilla.getBugFilingAndSearchLinks(None))
    bug_filing_url: None
    bug_search_url: None


Custom bug tracker bug filing links
-----------------------------------

Some bug trackers are heavily customised, so their bug filing URLs may
be different from the default URL form for that type of bug tracker.
getBugFilingAndSearchLinks() will handle these cases too, returning the
custom version of the bug filing URL for those bug trackers that don't
use the default setup.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> gnome_bugzilla = getUtility(ILaunchpadCelebrities).gnome_bugzilla

    >>> links = gnome_bugzilla.getBugFilingAndSearchLinks(
    ...     remote_product='testproduct', summary="Foo", description="Bar")

    >>> print_links(links)
    bug_filing_url:
    http://.../enter_bug.cgi?product=testproduct&short_desc=Foo&comment=Bar
    bug_search_url:
    http://.../query.cgi?product=testproduct&short_desc=Foo

