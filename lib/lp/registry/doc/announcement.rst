Announcements
=============

Any IProjectGroup, IProduct or IDistribution can make announcements. These are
listed on the project home page (latest 5) and also in a batched listing of
all announcements since the project was registered in LP.

Each announcement can be published immediately, or left unpublished till a
specified date or until manually approved. Announcements can be retracted
after publishing, and they can be deleted, permanently.

    >>> from zope.component import getUtility
    >>> from datetime import datetime, timedelta
    >>> import pytz
    >>> from lp.services.utils import utc_now
    >>> NOW = utc_now()
    >>> FUTURE = NOW + timedelta(days=10)
    >>> from lp.registry.interfaces.announcement import IAnnouncementSet
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet
    >>> announcements = getUtility(IAnnouncementSet)
    >>> kubuntu = getUtility(IDistributionSet).getByName("kubuntu")
    >>> apache = getUtility(IProjectGroupSet).getByName("apache")
    >>> tomcat = getUtility(IProductSet).getByName("tomcat")
    >>> derby = getUtility(IProductSet).getByName("derby")
    >>> mark = apache.owner
    >>> print(mark.name)
    mark


Creation
--------

To make an announcement, use the announce() method on the relevant project.

This can be done on an IProjectGroup:

In this first example, we will specify a date and time the announcement was
published:

    >>> apache_asia = apache.announce(
    ...     mark,
    ...     "OS Summit Asia 2007 - New Event by Apache and Eclipse",
    ...     summary="""Two of the leading organizations in the
    ...  Open Source community, The Apache Software Foundation and the Eclipse
    ...  Foundation, have announced plans for Asia's largest Open Source
    ...  community conference - the first of its kind in Hong Kong and China.
    ...
    ...  The inaugural OS Summit Asia will be held at the Le Meridian hotel in
    ...  Hong Kong's leading edge Cyberport IT development zone on November
    ...  26th - 30th 2007.""",
    ...     url=(
    ...         "http://www.mail-archive.com/announce@apache.org/msg00369.html"
    ...     ),
    ...     publication_date=datetime(
    ...         2007, 7, 12, 11, 17, 39, tzinfo=pytz.utc
    ...     ),
    ... )


We can also create an announcement that has no specified date of
publication:

    >>> apache_oss = apache.announce(
    ...     mark,
    ...     "Last Call for OSSummit Asia CFP",
    ...     summary="""For all those procrastinating submitting talks and
    ...  tutorials for OS Summit Asia, here's your friendly reminder!  The
    ...  call for papers ends this week, so please submit your proposals
    ...  promptly.""",
    ...     url=(
    ...         "http://www.mail-archive.com/announce@apache.org/msg00367.html"
    ...     ),
    ...     publication_date=None,
    ... )

Announcements can also be made on an IProduct:

    >>> derby_perf = derby.announce(
    ...     mark,
    ...     "ApacheCon Europe 2006  had a Derby session on performance",
    ...     summary="""We just finished an excellent series of discussions on
    ...  performance at ApacheCon, and there is a summary of our current plans
    ...  available online. Please feel free to review and comment!""",
    ...     publication_date=datetime(2006, 6, 30, 9, 0, 0, tzinfo=pytz.utc),
    ... )


And we can also force immediate publication of the announcement:

    >>> tomcat_release = tomcat.announce(
    ...     mark,
    ...     "Apache Tomcat JK 1.2.25 Web Server Connector released",
    ...     summary="""The Apache Tomcat team is pleased to announce the
    ...  immediate availability of version 1.2.25 of the Apache Tomcat
    ...  Connectors.
    ...
    ...  It contains connectors, which allow a web server such as Apache
    ...  HTTPD, Microsoft IIS and Sun Web Server to act as a front end to the
    ...  Tomcat web application server.""",
    ...     publication_date=NOW,
    ... )

And we can set a date in the future for publishing too:

    >>> tomcat_future_release = tomcat.announce(
    ...     mark,
    ...     "The future Tomcat will yawl all night without interruption",
    ...     summary="""Work is under way to ensure that Tomcat is the YAWLiest
    ...  application server around. You won't believe how much yawl we are
    ...  adding to The Cat. We challenge anyone to yawl harder.
    ...  """,
    ...     publication_date=FUTURE,
    ... )


And finally, we can make announcements on an IDistribution, too:

    >>> kubuntu_release = kubuntu.announce(
    ...     mark,
    ...     "Kubuntu 7.10 now available for download" "",
    ...     summary="""The moment you have all been waiting for has arrived! We
    ...  have pushed Kubuntu 7.10 to mirrors and published the final packages
    ...  in the archive. Go ahead and fire up your Torrent client for the
    ...  latest in KDE goodness!""",
    ...     publication_date=datetime(2007, 11, 3, 7, 0, 0, tzinfo=pytz.utc),
    ... )

Let's flush these to the database.

    >>> flush_database_updates()


Emergent properties
-------------------

Announcements can tell you if they are currently published or not:

    >>> apache_asia.published
    True
    >>> apache_oss.published
    False

They can also tell you if they will happen in the future, or have already
happened:

    >>> apache_asia.future
    False

If the publication date is unset, then they are considered to be in the
future:

    >>> apache_oss.future
    True


Listings
--------

Any of the pillars that can make announcements can generate a listing of
announcements. The listings can either include unpublished items, or just be
of published items that are visible to everyone.

Note that products that are part of a project group will show all the
project group announcements, and vice versa.

    >>> import transaction
    >>> transaction.commit()

    >>> for pillar in [tomcat, derby, apache, kubuntu]:
    ...     print(pillar.name)
    ...     for announcement in pillar.getAnnouncements():
    ...         print(announcement.title)
    ...
    tomcat
    Apache Tomcat JK 1.2.25 Web Server Connector released
    OS Summit Asia 2007 - New Event by Apache and Eclipse
    derby
    OS Summit Asia 2007 - New Event by Apache and Eclipse
    ApacheCon Europe 2006  had a Derby session on performance
    apache
    Apache Tomcat JK 1.2.25 Web Server Connector released
    OS Summit Asia 2007 - New Event by Apache and Eclipse
    ApacheCon Europe 2006  had a Derby session on performance
    kubuntu
    Kubuntu 7.10 now available for download

    >>> for announcement in apache.getAnnouncements(published_only=False):
    ...     if announcement.published is False:
    ...         print(announcement.title)
    ...
    Last Call for OSSummit Asia CFP
    The future Tomcat will yawl all night without interruption


Modification
------------

You can change the title, summary or URL of an announcement only through the
modify() method.

    >>> login("mark@example.com")
    >>> kubuntu_release.title = "Foo"
    Traceback (most recent call last):
      ...
    zope.security.interfaces.ForbiddenAttribute: ...
    >>> kubuntu_release.summary = "Foo"
    Traceback (most recent call last):
      ...
    zope.security.interfaces.ForbiddenAttribute: ...
    >>> kubuntu_release.url = "http://Foo.com/foo"
    Traceback (most recent call last):
      ...
    zope.security.interfaces.ForbiddenAttribute: ...
    >>> print(kubuntu_release.date_last_modified)
    None
    >>> kubuntu_release.modify(
    ...     title="Foo!", summary="Foo", url="http://foo.com"
    ... )
    >>> print(kubuntu_release.title)
    Foo!
    >>> print(kubuntu_release.summary)
    Foo
    >>> print(kubuntu_release.url)
    http://foo.com
    >>> print(kubuntu_release.date_last_modified is not None)
    True


Retraction
----------

Announcements can be retracted at any time. Retracting an announcement
updates the date_last_modified and sets the announcement.active flag to False

    >>> from storm.store import Store
    >>> from lp.services.database.sqlbase import get_transaction_timestamp
    >>> transaction_timestamp = get_transaction_timestamp(
    ...     Store.of(apache_asia)
    ... )

    >>> print(apache_asia.date_last_modified)
    None
    >>> print(apache_asia.active)
    True
    >>> apache_asia.retract()
    >>> flush_database_updates()
    >>> apache_asia.date_last_modified == transaction_timestamp
    True
    >>> apache_asia.active
    False


Publishing
----------

Announcements which have been retracted can be published again:

    >>> apache_asia.published
    False
    >>> apache_asia.setPublicationDate(
    ...     datetime(2007, 11, 11, 7, 0, 0, tzinfo=pytz.utc)
    ... )
    >>> apache_asia.published
    True

You can also publish an Announcement by setting the publication date to the
current date and time:

    >>> print(apache_oss.date_announced)
    None
    >>> apache_oss.setPublicationDate(NOW)
    >>> apache_oss.date_announced is not None
    True

And you can reset the date of publication:

    >>> apache_oss.setPublicationDate(None)


Retargeting
-----------

You can move an announcement from one pillar to the next:

    >>> print(apache_asia.target.name)
    apache
    >>> apache_asia.retarget(derby)
    >>> print(apache_asia.target.name)
    derby
    >>> apache_asia.retarget(kubuntu)
    >>> print(apache_asia.target.name)
    kubuntu
    >>> apache_asia.retarget(apache)
    >>> print(apache_asia.target.name)
    apache


Deletion
--------

You can ask an announcement to delete itself permanently.

    >>> old_id = kubuntu_release.id
    >>> kubuntu_release.destroySelf()
    >>> print(kubuntu.getAnnouncement(old_id))
    None


