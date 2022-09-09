Structural Subscriptions
========================

Structural subscriptions can be obtained from any target: a project,
project series, project group, distribution, distribution series or
distribution source package.

    >>> login("admin@canonical.com")
    >>> eric_db = factory.makePerson(name="eric")
    >>> michael_db = factory.makePerson(name="michael")
    >>> pythons_db = factory.makeTeam(name="pythons", owner=michael_db)
    >>> ignored = pythons_db.addMember(eric_db, michael_db)

    >>> fooix_db = factory.makeProduct(name="fooix", owner=eric_db)
    >>> fooix01_db = fooix_db.newSeries(eric_db, "0.1", "Series 0.1")
    >>> logout()

We can list the structural subscriptions on a target using the
getSubscriptions named operation. There are none just yet.

    >>> from lazr.restful.testing.webservice import (
    ...     pprint_collection,
    ...     pprint_entry,
    ... )
    >>> subscriptions = webservice.named_get(
    ...     "/fooix", "getSubscriptions"
    ... ).jsonBody()
    >>> pprint_collection(subscriptions)
    start: 0
    total_size: 0
    ---

Now Eric subscribes to Fooix's bug notifications.

    >>> from lp.testing.pages import webservice_for_person
    >>> from lp.services.webapp.interfaces import OAuthPermission
    >>> eric_webservice = webservice_for_person(
    ...     eric_db, permission=OAuthPermission.WRITE_PRIVATE
    ... )

    >>> print(eric_webservice.named_post("/fooix", "addBugSubscription"))
    HTTP/1.1 201 Created
    ...
    Location: http://.../fooix/+subscription/eric
    ...

    >>> subscriptions = webservice.named_get(
    ...     "/fooix", "getSubscriptions"
    ... ).jsonBody()
    >>> pprint_collection(subscriptions)
    start: 0
    total_size: 1
    ---
    bug_filters_collection_link: '.../fooix/+subscription/eric/bug_filters'
    date_created: '...'
    date_last_updated: '...'
    resource_type_link: 'http://.../#structural_subscription'
    self_link: 'http://.../fooix/+subscription/eric'
    subscribed_by_link: 'http://.../~eric'
    subscriber_link: 'http://.../~eric'
    target_link: 'http://.../fooix'
    ---

He can examine his subscription directly.

    >>> pprint_entry(
    ...     eric_webservice.named_get(
    ...         "/fooix",
    ...         "getSubscription",
    ...         person=webservice.getAbsoluteUrl("/~eric"),
    ...     ).jsonBody()
    ... )
    bug_filters_collection_link: '.../fooix/+subscription/eric/bug_filters'
    date_created: '...'
    date_last_updated: '...'
    resource_type_link: 'http://.../#structural_subscription'
    self_link: 'http://.../fooix/+subscription/eric'
    subscribed_by_link: 'http://.../~eric'
    subscriber_link: 'http://.../~eric'
    target_link: 'http://.../fooix'

If the subscription doesn't exist, None will be returned.

    >>> print(
    ...     webservice.named_get(
    ...         "/fooix",
    ...         "getSubscription",
    ...         person=webservice.getAbsoluteUrl("/~michael"),
    ...     ).jsonBody()
    ... )
    None

Eric can remove his subscription through the webservice.

    >>> print(eric_webservice.named_post("/fooix", "removeBugSubscription"))
    HTTP/1.1 200 Ok...

    >>> print(
    ...     webservice.named_get(
    ...         "/fooix",
    ...         "getSubscription",
    ...         person=webservice.getAbsoluteUrl("/~eric"),
    ...     ).jsonBody()
    ... )
    None

Teams can be subscribed by passing in the team as an argument. Eric
tries this.

    >>> print(
    ...     eric_webservice.named_post(
    ...         "/fooix",
    ...         "addBugSubscription",
    ...         subscriber=webservice.getAbsoluteUrl("/~pythons"),
    ...     )
    ... )
    HTTP/1.1 401 Unauthorized
    ...
    eric does not have permission to subscribe pythons.

Oops, Eric isn't a team admin. Eric gets Michael to try, since he is an
admin by virtue of his ownership.

    >>> michael_webservice = webservice_for_person(
    ...     michael_db, permission=OAuthPermission.WRITE_PRIVATE
    ... )

    >>> print(
    ...     michael_webservice.named_post(
    ...         "/fooix",
    ...         "addBugSubscription",
    ...         subscriber=webservice.getAbsoluteUrl("/~pythons"),
    ...     )
    ... )
    HTTP/1.1 201 Created
    ...
    Location: http://.../fooix/+subscription/pythons
    ...

    >>> subscriptions = webservice.named_get(
    ...     "/fooix", "getSubscriptions"
    ... ).jsonBody()
    >>> pprint_collection(subscriptions)
    start: 0
    total_size: 1
    ---
    bug_filters_collection_link: '.../fooix/+subscription/pythons/bug_filters'
    date_created: '...'
    date_last_updated: '...'
    resource_type_link: 'http://.../#structural_subscription'
    self_link: 'http://.../fooix/+subscription/pythons'
    subscribed_by_link: 'http://.../~michael'
    subscriber_link: 'http://.../~pythons'
    target_link: 'http://.../fooix'
    ---

Eric can't unsubscribe the team either.

    >>> print(
    ...     eric_webservice.named_post(
    ...         "/fooix",
    ...         "removeBugSubscription",
    ...         subscriber=webservice.getAbsoluteUrl("/~pythons"),
    ...     )
    ... )
    HTTP/1.1 401 Unauthorized
    ...
    eric does not have permission to unsubscribe pythons.

Michael can, though.

    >>> print(
    ...     michael_webservice.named_post(
    ...         "/fooix",
    ...         "removeBugSubscription",
    ...         subscriber=webservice.getAbsoluteUrl("/~pythons"),
    ...     )
    ... )
    HTTP/1.1 200 Ok...

    >>> subscriptions = webservice.named_get(
    ...     "/fooix", "getSubscriptions"
    ... ).jsonBody()
    >>> pprint_collection(subscriptions)
    start: 0
    total_size: 0
    ---
