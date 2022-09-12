=============================================
Using the webservice with commercial archives
=============================================

(See also soyuz/stories/webservice/xx-archive.rst)

Software Center Agent
---------------------

Create the P3A where software_center_agent is an owner.

    >>> from zope.component import getUtility
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> login("admin@canonical.com")
    >>> celebrity = getUtility(ILaunchpadCelebrities).software_center_agent
    >>> owner = factory.makePerson()
    >>> ppa_owner = factory.makeTeam(members=[celebrity, owner])
    >>> archive = factory.makeArchive(
    ...     name="commercial",
    ...     private=True,
    ...     owner=ppa_owner,
    ...     suppress_subscription_notifications=True,
    ... )
    >>> url = "/~%s/+archive/ubuntu/commercial" % archive.owner.name
    >>> person = factory.makePerson(name="joe")
    >>> logout()

And fetch our objects:

    >>> from lp.testing.pages import webservice_for_person
    >>> from lp.services.webapp.interfaces import OAuthPermission
    >>> agent = webservice.get("/~software-center-agent").jsonBody()
    >>> joe = webservice.get("/~joe").jsonBody()
    >>> cprov = webservice.get("/~cprov").jsonBody()
    >>> cp3a = webservice.get(url).jsonBody()

Setup webservice handler for the agent and the test user:

    >>> agent_webservice = webservice_for_person(
    ...     celebrity, permission=OAuthPermission.WRITE_PRIVATE
    ... )

    >>> joe_webservice = webservice_for_person(
    ...     person, permission=OAuthPermission.WRITE_PRIVATE
    ... )

When the agent tries to get a URL for accessing the commercial
archive as the test user, an error is returned since there is no
valid subscription for it.

    >>> response = agent_webservice.named_post(
    ...     joe["self_link"],
    ...     "getArchiveSubscriptionURL",
    ...     {},
    ...     archive=cp3a["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 401 Unauthorized
    ...
    This person does not have a valid subscription for the target archive

In order to allow access for the test user, the agent has to subscribe
them first.

    >>> response = agent_webservice.named_post(
    ...     cp3a["self_link"], "newSubscription", subscriber=joe["self_link"]
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...
    Location: http://api.launchpad.test/beta/.../+subscriptions/joe
    ...

Now the agent can query the sources.list entry for an archive for the
the test user (or any other user), which will include an AuthToken,
which is create on demand if necessary:

    >>> response = agent_webservice.named_post(
    ...     joe["self_link"],
    ...     "getArchiveSubscriptionURL",
    ...     {},
    ...     archive=cp3a["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    "http://joe:...@private-ppa.launchpad.test/.../commercial/ubuntu"

The agent can also query all sources.list entries for the test user
(and any other user too):

    >>> response = agent_webservice.named_get(
    ...     joe["self_link"], "getArchiveSubscriptionURLs"
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    ["http://joe:...@private-ppa.launchpad.test/.../commercial/ubuntu"]

Joe can query his own entry:

    >>> response = joe_webservice.named_post(
    ...     joe["self_link"],
    ...     "getArchiveSubscriptionURL",
    ...     {},
    ...     archive=cp3a["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    "http://joe:...@private-ppa.launchpad.test/.../commercial/ubuntu"

But Joe can not query the entry of cprov:

    >>> response = joe_webservice.named_post(
    ...     cprov["self_link"],
    ...     "getArchiveSubscriptionURL",
    ...     {},
    ...     archive=cp3a["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 401 Unauthorized
    ...
    Only the context user can call this method


Archive Subscriptions deactivation
----------------------------------

Archive subscriptions allow users to be part of a private Archive (P3A)
workflow (repository access and notifications, mainly).

The archive publisher invalidates existing authorization tokens (prior
to any publication) for inactive subscriptions on each cycle (~ 10 min).

In order to block access for a person, e.g. when one leaves the company,
its individual subscriptions have to be canceled. Team subscriptions
automatically lose effect when a person leaves the team.

This section requires methods only available in the 'devel' API
version. Let's fetch the corresponding test user references:

    >>> joe = webservice.get("/~joe", api_version="devel").jsonBody()

Active subscriptions for a given person can be obtained from
'getArchiveSubscriptions' named get operation on the person object:

    >>> subscriptions = joe_webservice.named_get(
    ...     joe["self_link"], "getArchiveSubscriptions", api_version="devel"
    ... ).jsonBody()

It returns a collection of `ArchiveSubscriber` objects:

    >>> from lazr.restful.testing.webservice import pprint_collection
    >>> pprint_collection(subscriptions)
    start: 0
    total_size: 1
    ---
    archive_link: 'http://.../+archive/ubuntu/commercial'
    date_created: ...
    date_expires: None
    description: None
    registrant_link: 'http://.../~software-center-agent'
    resource_type_link: 'http://.../#archive_subscriber'
    self_link: 'http://.../+archive/ubuntu/commercial/+subscriptions/joe'
    status: 'Active'
    subscriber_link: 'http://.../~joe'
    web_link: 'http://.../+archive/ubuntu/commercial/+subscriptions/joe'
    ---

Additionally to the person itself, the subscriptions can be inspected
by anyone with 'Edit' permission on the P3A (P3A owner or team members)
and it includes 'commercial-admins' users:

    >>> login("admin@canonical.com")
    >>> commercial_admin = factory.makePerson()
    >>> commercial_celebrity = getUtility(
    ...     ILaunchpadCelebrities
    ... ).commercial_admin
    >>> ignore = commercial_celebrity.addMember(commercial_admin, owner)
    >>> logout()
    >>> commercial_webservice = webservice_for_person(
    ...     commercial_admin, permission=OAuthPermission.WRITE_PRIVATE
    ... )

    >>> subscriptions = commercial_webservice.named_get(
    ...     joe["self_link"], "getArchiveSubscriptions", api_version="devel"
    ... ).jsonBody()
    >>> pprint_collection(subscriptions)
    start: 0
    total_size: 1
    ---
    archive_link: 'http://.../+archive/ubuntu/commercial'
    date_created: ...
    date_expires: None
    description: None
    registrant_link: 'http://.../~software-center-agent'
    resource_type_link: 'http://.../#archive_subscriber'
    self_link: 'http://.../+archive/ubuntu/commercial/+subscriptions/joe'
    status: 'Active'
    subscriber_link: 'http://.../~joe'
    web_link: 'http://.../+archive/ubuntu/commercial/+subscriptions/joe'
    ---

Subscription cancellation can be performed by invoking 'cancel' operation
on it:

    >>> subscription_link = subscriptions["entries"][0]["self_link"]
    >>> response = commercial_webservice.named_post(
    ...     subscription_link, "cancel", api_version="devel"
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

Once canceled, the subscription is not reachable anymore:

    >>> subscriptions = commercial_webservice.named_get(
    ...     joe["self_link"], "getArchiveSubscriptions", api_version="devel"
    ... ).jsonBody()
    >>> pprint_collection(subscriptions)
    start: 0
    total_size: 0
    ---

At this point it is just a matter of waiting the publisher run and
deactivate the corresponding authorization token.
