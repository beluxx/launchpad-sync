Branch subscriptions
====================

Set up a branch to be subscribed to.

    >>> login("admin@canonical.com")
    >>> farm = factory.makeProduct(name="farm")
    >>> farmer_joe_db = factory.makePerson(
    ...     name="farmer-joe", displayname="Farmer Joe"
    ... )
    >>> farmer_bob_db = factory.makePerson(
    ...     name="farmer-bob", displayname="Farmer Bob"
    ... )
    >>> farmer_joe_url = "/~farmer-joe"
    >>> corn_db = factory.makeAnyBranch(
    ...     product=farm, owner=farmer_bob_db, name="corn"
    ... )
    >>> corn_url = "/" + corn_db.unique_name
    >>> logout()


Subscribing to branches
=======================

A user can subscribe to a branch through the API.

    >>> joe = webservice.get(farmer_joe_url).jsonBody()
    >>> corn = webservice.get(corn_url).jsonBody()
    >>> subscription = webservice.named_post(
    ...     corn["self_link"],
    ...     "subscribe",
    ...     person=joe["self_link"],
    ...     notification_level="Branch attribute notifications only",
    ...     max_diff_lines="Don't send diffs",
    ...     code_review_level="No email",
    ... )

    >>> from lazr.restful.testing.webservice import pprint_entry
    >>> pprint_entry(subscription.jsonBody())
    branch_link: 'http://.../~farmer-bob/farm/corn'
    max_diff_lines: "Don't send diffs"
    notification_level: 'Branch attribute notifications only'
    person_link: 'http://.../~farmer-joe'
    resource_type_link: 'http://.../#branch_subscription'
    review_level: 'No email'
    self_link: 'http://.../~farmer-bob/farm/corn/+subscription/farmer-joe'
    subscribed_by_link: 'http://.../~salgado'
    web_link: 'http://code.../~farmer-bob/farm/corn/+subscription/farmer-joe'

    >>> def print_subscriber_count(branch):
    ...     subscribers = webservice.get(
    ...         corn["subscribers_collection_link"]
    ...     ).jsonBody()
    ...     print(len(subscribers["entries"]))
    ...
    >>> print_subscriber_count(corn)
    2

    >>> def print_subscriber_names(branch):
    ...     subscribers = webservice.get(
    ...         corn["subscribers_collection_link"]
    ...     ).jsonBody()
    ...     for subscriber in subscribers["entries"]:
    ...         print(subscriber["display_name"])
    ...
    >>> print_subscriber_names(corn)
    Farmer Bob
    Farmer Joe


Get the subscription
====================

Sometimes it's necessary to get a single person's subscriptions through the
API without getting everyone's subscriptions.

    >>> subscription = webservice.named_get(
    ...     corn["self_link"], "getSubscription", person=joe["self_link"]
    ... ).jsonBody()

    >>> print(subscription["self_link"])
    http://.../~farmer-bob/farm/corn/+subscription/farmer-joe


Edit your subscription
======================

Once the subscription is created, it can be edited through the API as well.
The way this works is to just subscribe to the branch again, the same way it
was originally subscribed.

    >>> subscription = webservice.named_post(
    ...     corn["self_link"],
    ...     "subscribe",
    ...     person=joe["self_link"],
    ...     notification_level="No email",
    ...     max_diff_lines="Send entire diff",
    ...     code_review_level="Status changes only",
    ... )

    >>> pprint_entry(subscription.jsonBody())
    branch_link: 'http://.../~farmer-bob/farm/corn'
    max_diff_lines: 'Send entire diff'
    notification_level: 'No email'
    person_link: 'http://.../~farmer-joe'
    resource_type_link: 'http://.../#branch_subscription'
    review_level: 'Status changes only'
    self_link: 'http://.../~farmer-bob/farm/corn/+subscription/farmer-joe'
    subscribed_by_link: 'http://.../~salgado'
    web_link: 'http://code.../~farmer-bob/farm/corn/+subscription/farmer-joe'


We print the count, and even though subscribe was called again, there's still
only one subscription.

    >>> print_subscriber_count(corn)
    2
    >>> print_subscriber_names(corn)
    Farmer Bob
    Farmer Joe


Unsubscribing from a branch
===========================

Sometimes branches get too noisy.  It's possible to unsubscribe from the
branch through the API as well.

    >>> _unused = webservice.named_post(
    ...     corn["self_link"], "unsubscribe", person=joe["self_link"]
    ... )

    >>> print_subscriber_count(corn)
    1

