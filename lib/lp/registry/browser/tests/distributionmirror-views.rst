DistributionMirror Pages
========================

Registering a mirror
--------------------

Distributions must have mirror support enabled in order to have mirrors.
Other distributions cannot use the form.

    >>> from lp.testing.pages import extract_text, find_tag_by_id

    >>> distribution = factory.makeDistribution(name="youbuntu")
    >>> distribution.supports_mirrors
    False

    >>> ignored = login_person(distribution.owner)
    >>> view = create_initialized_view(
    ...     distribution, "+newmirror", principal=distribution.owner
    ... )
    >>> content = find_tag_by_id(view.render(), "not-full-functionality")
    >>> print(extract_text(content))
    This functionality is not yet available...

Ubuntu has mirror support enabled, so it can have mirrors.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities

    >>> ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    >>> owner = ubuntu.owner.teamowner
    >>> ignored = login_person(owner)
    >>> view = create_initialized_view(ubuntu, "+newmirror", principal=owner)
    >>> content = find_tag_by_id(view.render(), "full-functionality")
    >>> print(extract_text(content))
    To register a new mirror...

The view provides a label, page_title, and cancel_url

    >>> print(view.label)
    Register a new mirror for Ubuntu

    >>> print(view.page_title)
    Register a new mirror for Ubuntu

    >>> print(view.cancel_url)
    http://launchpad.test/ubuntu

A HTTP, HTTPS or FTP URL is required to register a mirror.

    >>> view.field_names
    ['display_name', 'description', 'whiteboard', 'https_base_url',
     'http_base_url', 'ftp_base_url', 'rsync_base_url', 'speed', 'country',
     'content', 'official_candidate']

    >>> form = {
    ...     "field.display_name": "Illuminati",
    ...     "field.description": "description",
    ...     "field.whiteboard": "whiteboard",
    ...     "field.http_base_url": "http://secret.me/",
    ...     "field.https_base_url": "",
    ...     "field.ftp_base_url": "",
    ...     "field.rsync_base_url": "",
    ...     "field.speed": "S128K",
    ...     "field.country": "1",
    ...     "field.content": "ARCHIVE",
    ...     "field.official_candidate": "on",
    ...     "field.actions.create": "Register Mirror",
    ... }
    >>> view = create_initialized_view(ubuntu, "+newmirror", form=form)
    >>> view.errors
    []
    >>> print(view.next_url)
    http://launchpad.test/ubuntu/+mirror/secret.me-archive

    >>> transaction.commit()


Registration constraints
........................

A mirror can only be registered once for a HTTP URL (the trailing slash is
not significant).

    >>> mirror = ubuntu.getMirrorByName("secret.me-archive")
    >>> print(mirror.http_base_url)
    http://secret.me/

    >>> bad_form = dict(form)
    >>> bad_form["field.http_base_url"] = "http://secret.me"
    >>> view = create_initialized_view(ubuntu, "+newmirror", form=bad_form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    ...
    The distribution mirror ... is already registered with this URL.

The same is true for a FTP URL.

    >>> mirror.ftp_base_url = "ftp://now-here.me/"
    >>> bad_form["field.https_base_url"] = ""
    >>> bad_form["field.http_base_url"] = ""
    >>> bad_form["field.ftp_base_url"] = "ftp://now-here.me"
    >>> view = create_initialized_view(ubuntu, "+newmirror", form=bad_form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    ...
    The distribution mirror ... is already registered with this URL.

The same is true for a rsync URL.

    >>> mirror.rsync_base_url = "rsync://nowhere.me/"
    >>> bad_form["field.ftp_base_url"] = "ftp://no-where.me"
    >>> bad_form["field.rsync_base_url"] = "rsync://nowhere.me"
    >>> view = create_initialized_view(ubuntu, "+newmirror", form=bad_form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    ...
    The distribution mirror ... is already registered with this URL.

A mirror must have an ftp, HTTPS or http URL.

    >>> bad_form["field.https_base_url"] = ""
    >>> bad_form["field.http_base_url"] = ""
    >>> bad_form["field.ftp_base_url"] = ""
    >>> view = create_initialized_view(ubuntu, "+newmirror", form=bad_form)
    >>> for message in view.errors:
    ...     print(message)
    ...
    A mirror must have at least an HTTP(S) or FTP URL.

The URL cannot contain a fragment.

    >>> bad_form["field.http_base_url"] = "http://secret.me/#fragement"
    >>> view = create_initialized_view(ubuntu, "+newmirror", form=bad_form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    ...
    URIs with fragment identifiers are not allowed.

The URL cannot contain a query string.

    >>> bad_form["field.http_base_url"] = "http://secret.me/?query=string"
    >>> view = create_initialized_view(ubuntu, "+newmirror", form=bad_form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    ...
    URIs with query strings are not allowed.

The HTTPS URL may not have an HTTP scheme.

    >>> bad_form["field.http_base_url"] = ""
    >>> bad_form["field.https_base_url"] = "http://secret.me/#fragement"
    >>> view = create_initialized_view(ubuntu, "+newmirror", form=bad_form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    ...
    The URI scheme &quot;http&quot; is not allowed.
    Only URIs with the following schemes may be used: https

The HTTPS URL cannot contain a fragment.

    >>> bad_form["field.http_base_url"] = ""
    >>> bad_form["field.https_base_url"] = "https://secret.me/#fragement"
    >>> view = create_initialized_view(ubuntu, "+newmirror", form=bad_form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    ...
    URIs with fragment identifiers are not allowed.

The URL cannot contain a query string.

    >>> bad_form["field.http_base_url"] = ""
    >>> bad_form["field.https_base_url"] = "https://secret.me/?query=string"
    >>> view = create_initialized_view(ubuntu, "+newmirror", form=bad_form)
    >>> for error in view.errors:
    ...     print(error.args[2])
    ...
    URIs with query strings are not allowed.


Reviewing a distribution mirror
-------------------------------

The +review view allows mirror admins to set the status of a given mirror. The
status can be PENDING_REVIEW, UNOFFICIAL and OFFICIAL.  When the status is
changed the person who changed it and the date it was changed.

Only official mirrors are probed.

    >>> print(mirror.status.name)
    PENDING_REVIEW
    >>> print(mirror.date_reviewed, mirror.reviewer)
    None None

The view provides a label, page_title, and cancel_url.

    >>> view = create_initialized_view(mirror, "+review")
    >>> print(view.label)
    Review mirror Illuminati

    >>> print(view.page_title)
    Review mirror Illuminati

    >>> print(view.cancel_url)
    http://launchpad.test/ubuntu/+mirror/secret.me-archive

If the status is not changed, the reviewer and date_reviewed won't be
changed either.

    >>> login("karl@canonical.com")
    >>> review_form = {
    ...     "field.status": mirror.status.name,
    ...     "field.whiteboard": "The site fell off the net.",
    ...     "field.actions.save": "Save",
    ... }
    >>> view = create_initialized_view(mirror, "+review", form=review_form)
    >>> view.errors
    []

    >>> print(mirror.status.name)
    PENDING_REVIEW
    >>> print(mirror.date_reviewed, mirror.reviewer)
    None None

When the status is changed, though, both reviewer and date_reviewed are
changed.

    >>> review_form["field.status"] = "OFFICIAL"
    >>> review_form["field.whiteboard"] = "This site is good."
    >>> view = create_initialized_view(mirror, "+review", form=review_form)
    >>> view.errors
    []
    >>> print(view.next_url)
    http://launchpad.test/ubuntu/+mirror/secret.me-archive

    >>> print(mirror.status.name)
    OFFICIAL
    >>> print(mirror.reviewer.name)
    karl
    >>> print(mirror.whiteboard)
    This site is good.

    # This is to check that the mirror's date_reviewed has just been updated,
    # but since this test could run at 23:59:59 of any given day we can only
    # reliably check that the timedelta from now to the date it was reviewed
    # is less than or equal to 1 day.
    >>> import pytz
    >>> from datetime import datetime
    >>> utc_now = datetime.now(pytz.timezone("UTC"))
    >>> abs((mirror.date_reviewed.date() - utc_now.date()).days) <= 1
    True

Only users with launchpad.Admin can access the view.

    >>> from lp.services.webapp.authorization import check_permission

    >>> check_permission("launchpad.Admin", view)
    True

    >>> login("no-priv@canonical.com")
    >>> check_permission("launchpad.Admin", view)
    False


Edit distribution mirror
-----------------------

The +edit view provides a label, page_title, and cancel_url.

    >>> login("karl@canonical.com")
    >>> view = create_initialized_view(mirror, "+edit")
    >>> print(view.label)
    Edit mirror Illuminati

    >>> print(view.page_title)
    Edit mirror Illuminati

    >>> print(view.cancel_url)
    http://launchpad.test/ubuntu/+mirror/secret.me-archive

The user can edit the mirror fields.

    >>> view.field_names
    ['name', 'display_name', 'description', 'whiteboard', 'https_base_url',
     'http_base_url', 'ftp_base_url', 'rsync_base_url', 'speed', 'country',
     'content', 'official_candidate']

    >>> print(mirror.ftp_base_url)
    None

    >>> form["field.ftp_base_url"] = "ftp://secret.me/"
    >>> form["field.actions.save"] = "Save"
    >>> view = create_initialized_view(mirror, "+edit", form=form)
    >>> view.errors
    []
    >>> print(view.next_url)
    http://launchpad.test/ubuntu/+mirror/secret.me-archive

    >>> print(mirror.ftp_base_url)
    ftp://secret.me/

Only users with launchpad.Edit can access the view.

    >>> check_permission("launchpad.Edit", view)
    True

    >>> login("no-priv@canonical.com")
    >>> check_permission("launchpad.Edit", view)
    False


Reassign distribution mirror
----------------------------

The mirror owner can reassign the mirror to another user. (The view
is the common object reassignment view.)

    >>> login("karl@canonical.com")
    >>> view = create_initialized_view(mirror, "+reassign")
    >>> check_permission("launchpad.Edit", view)
    True

    >>> login("no-priv@canonical.com")
    >>> check_permission("launchpad.Edit", view)
    False


Resubmit distribution mirror
----------------------------

The mirror owner can resubmit a 'Broken' mirror for a new review.

    >>> login("karl@canonical.com")
    >>> review_form["field.status"] = "BROKEN"
    >>> review_form["field.whiteboard"] = "This site is broken."
    >>> view = create_initialized_view(mirror, "+review", form=review_form)
    >>> form["field.actions.resubmit"] = "Resubmit"
    >>> view = create_initialized_view(mirror, "+resubmit", form=form)
    >>> print(mirror.status.name)
    PENDING_REVIEW

The resubmit view should only be available to people with launchpad.Edit.

    >>> login("karl@canonical.com")
    >>> view = create_initialized_view(mirror, "+resubmit")
    >>> check_permission("launchpad.Edit", view)
    True

    >>> login("no-priv@canonical.com")
    >>> check_permission("launchpad.Edit", view)
    False


Delete distribution mirror
--------------------------

The +delete view provides a label, page_title, and cancel_url.

    >>> login("karl@canonical.com")
    >>> view = create_initialized_view(mirror, "+delete")
    >>> print(view.label)
    Delete mirror Illuminati

    >>> print(view.page_title)
    Delete mirror Illuminati

    >>> print(view.cancel_url)
    http://launchpad.test/ubuntu/+mirror/secret.me-archive

A mirror that have been probed cannot be deleted.

    >>> probed_mirror = ubuntu.getMirrorByName("archive-mirror2")
    >>> probed_mirror.last_probe_record is not None
    True

    >>> form = {
    ...     "field.actions.delete": "Delete Mirror",
    ... }
    >>> view = create_initialized_view(probed_mirror, "+delete", form=form)
    >>> view.errors
    []
    >>> for notification in view.request.response.notifications:
    ...     print(notification.message)
    ...
    This mirror has been probed and thus can&#x27;t be deleted.

Only users with launchpad.Admin can access the view.

    >>> check_permission("launchpad.Admin", view)
    True

    >>> login("no-priv@canonical.com")
    >>> check_permission("launchpad.Admin", view)
    False

Deletion is permanent.

    >>> login("karl@canonical.com")
    >>> form = {
    ...     "field.actions.delete": "Delete Mirror",
    ... }
    >>> view = create_initialized_view(mirror, "+delete", form=form)
    >>> view.errors
    []
    >>> print(view.next_url)
    http://launchpad.test/ubuntu/+pendingreviewmirrors

    >>> transaction.commit()
    >>> print(ubuntu.getMirrorByName("secret.me-archive"))
    None


Viewing a mirror
----------------

The archive mirror page summarizes the current state of the mirror.

    >>> from lp.services.webapp.interfaces import ILaunchBag
    >>> from lp.testing.pages import extract_text, find_tag_by_id

    >>> login("no-priv@canonical.com")
    >>> user = getUtility(ILaunchBag).user

    >>> archive_mirror = ubuntu.getMirrorByName("archive-mirror2")
    >>> view = create_initialized_view(
    ...     archive_mirror, "+index", principal=user
    ... )
    >>> content = find_tag_by_id(view.render(), "maincontent")

The page shows the mirror's owner:

    >>> print(extract_text(find_tag_by_id(content, "owner")))
    Owner:
    Mark Shuttleworth

The page shows the mirror status

    >>> print(extract_text(find_tag_by_id(content, "status")))
    Status:
    Official

The page shows which country the mirror is in:

    >>> print(extract_text(find_tag_by_id(content, "country")))
    Country:
    Antarctica

The page shows which kind of mirror a mirror is:

    >>> print(extract_text(find_tag_by_id(content, "type")))
    Type:
    Archive

And which organisation runs a mirror:

    >>> print(extract_text(find_tag_by_id(content, "organisation")))
    Organisation:
    None

The page contains a source list...

    >>> print(extract_text(find_tag_by_id(content, "sources-list-entries")))
    ... # noqa
    deb http://localhost:11375/valid-mirror2/ YOUR_UBUNTU_VERSION_HERE main
    deb-src http://localhost:11375/valid-mirror2/ YOUR_UBUNTU_VERSION_HERE main

and the select control that lets you update them.

    >>> print(extract_text(find_tag_by_id(content, "field.series")))
    Choose your Ubuntu version
      Hoary (5.04)
      Warty (4.10)

The last probed information is present.

    >>> print(extract_text(find_tag_by_id(content, "last-probe")))
    Last probe
    This mirror was last verified ...

The information found is also shown.

    >>> print(extract_text(find_tag_by_id(content, "arches")))
    Version                     Architecture  Status
    The Hoary Hedgehog Release  i386          One hour behind
    The Warty Warthog Release   i386          Two hours behind

    >>> print(extract_text(find_tag_by_id(content, "sources")))
    Version                      Status
    The Hoary Hedgehog Release   Up to date
    The Warty Warthog Release    Six hours behind

The cd mirror page summarizes the current state of the mirror.
The last probed information is present.

    >>> cd_mirror = ubuntu.getMirrorByName("releases-mirror2")
    >>> view = create_initialized_view(cd_mirror, "+index", principal=user)
    >>> content = find_tag_by_id(view.render(), "maincontent")
    >>> print(extract_text(find_tag_by_id(content, "last-probe")))
    Last probe
    This mirror was last verified ...

The information found is also shown.

    >>> print(extract_text(find_tag_by_id(content, "series")))
    Version                     Flavours
    The Hoary Hedgehog Release  Ubuntu, Edubuntu
    The Warty Warthog Release   Ubuntu, Kubuntu

Mirror admins can also see a whiteboard

    >>> login("karl@canonical.com")
    >>> user = getUtility(ILaunchBag).user
    >>> cd_mirror.whiteboard = "This is a good mirror."
    >>> view = create_initialized_view(cd_mirror, "+index", principal=user)
    >>> whiteboard = find_tag_by_id(view.render(), "whiteboard")
    >>> print(extract_text(whiteboard.find("dd")))
    This is a good mirror.

    >>> login("no-priv@canonical.com")
    >>> user = getUtility(ILaunchBag).user
    >>> view = create_initialized_view(cd_mirror, "+index", principal=user)
    >>> print(find_tag_by_id(view.render(), "whiteboard"))
    None


Distribution mirror RSS
-----------------------

Any user can see the RSS for an archive mirror

    >>> login("no-priv@canonical.com")
    >>> user = getUtility(ILaunchBag).user
    >>> view = create_initialized_view(
    ...     ubuntu,
    ...     "+archivemirrors-rss",
    ...     principal=user,
    ...     server_url="http://launchpad.test/ubuntu/+archivemirrors-rss",
    ... )
    >>> print(view().decode("UTF-8"))
    <?xml version="1.0"...?>
    <rss xmlns:mirror="https://launchpad.net/" version="2.0">
      <channel>
        <title>Ubuntu Archive Mirrors Status</title>
        <link>http://launchpad.test/ubuntu/+archivemirrors-rss</link>
        <description>Status of Ubuntu Archive Mirrors</description>
        ...
        <item>
          <title>Archive-mirror</title>
          <link>http://localhost:11375/valid-mirror/</link>
          <description>
          </description>
          <mirror:bandwidth>...</mirror:bandwidth>
          <mirror:location>
            <mirror:continent>Europe</mirror:continent>
            <mirror:country>France</mirror:country>
            <mirror:countrycode>FR</mirror:countrycode>
          </mirror:location>
          <guid>http://localhost:11375/valid-mirror/</guid>
        </item>
        ...
      </channel>
    </rss>

    >>> print(view.request.response.getHeader("content-type"))
    text/xml;charset=utf-8

Any user can see the RSS for an CD mirror

    >>> view = create_initialized_view(
    ...     ubuntu,
    ...     "+cdmirrors-rss",
    ...     principal=user,
    ...     server_url="http://launchpad.test/ubuntu/+cdmirrors-rss",
    ... )
    >>> print(view().decode("UTF-8"))
    <?xml version="1.0"...?>
    <rss ...
      <channel>
        <title>Ubuntu CD Mirrors Status</title>
        <link>...</link>
        <description>...</description>
        ...
        <item>
          <title>Releases-mirror</title>
          <link>http://localhost:11375/valid-mirror/releases/</link>
          <description>...</description>
          <mirror:bandwidth>...</mirror:bandwidth>
          <mirror:location>
            <mirror:continent>Europe</mirror:continent>
            <mirror:country>France</mirror:country>
            <mirror:countrycode>FR</mirror:countrycode>
          </mirror:location>
          <guid>http://localhost:11375/valid-mirror/releases/</guid>
        </item>
        <item>
        ...
        </item>
        <item>
        ...
        </item>
      </channel>
    </rss>

    >>> print(view.request.response.getHeader("content-type"))
    text/xml;charset=utf-8
