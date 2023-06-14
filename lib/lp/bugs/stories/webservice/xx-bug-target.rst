Introduction
============

Many exposed objects in the API provide IBugTarget, including
projects, distributions, distribution series, and source packages.


bug_reporting_guidelines
------------------------

All bug targets have a read/write bug_reporting_guidelines property.

    >>> product_url = "/firefox"

    >>> product = webservice.get(product_url).jsonBody()
    >>> print(product["bug_reporting_guidelines"])
    None

    >>> import json
    >>> patch = {
    ...     "bug_reporting_guidelines": "Please run `ubuntu-bug -p firefox`."
    ... }
    >>> response = webservice.patch(
    ...     product["self_link"], "application/json", json.dumps(patch)
    ... )

    >>> product = webservice.get(product_url).jsonBody()
    >>> print(product["bug_reporting_guidelines"])
    Please run `ubuntu-bug -p firefox`.

Not everyone can modify it however:

    >>> patch = {
    ...     "bug_reporting_guidelines": (
    ...         "Include your credit-card details, mwuh"
    ...     )
    ... }
    >>> response = user_webservice.patch(
    ...     product["self_link"], "application/json", json.dumps(patch)
    ... )
    >>> print(response)
    HTTP/1.1 401 Unauthorized...
    Content-Length: ...
    Content-Type: text/plain...
    <BLANKLINE>
    (<Product object>, 'bug_reporting_guidelines', 'launchpad.BugSupervisor')


Official Bug Tags
-----------------

We can access official bug tag targets and add and remove tags. We
create a new product, owned by ~salgado.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.testing import login, logout
    >>> login("foo.bar@canonical.com")
    >>> salgado = getUtility(IPersonSet).getByName("salgado")
    >>> product = factory.makeProduct(name="tags-test-product", owner=salgado)
    >>> logout()

The webservice client is logged in as salgado, so we can add a new official
tag.

    >>> print(
    ...     webservice.named_post(
    ...         "/tags-test-product", "addOfficialBugTag", tag="test-bug-tag"
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...
    <BLANKLINE>
    null

And we can remove it.

    >>> print(
    ...     webservice.named_post(
    ...         "/tags-test-product",
    ...         "removeOfficialBugTag",
    ...         tag="test-bug-tag",
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...
    <BLANKLINE>
    null

But a different user can't.

    >>> print(
    ...     user_webservice.named_post(
    ...         "/tags-test-product", "addOfficialBugTag", tag="test-bug-tag"
    ...     )
    ... )
    HTTP/1.1 401 Unauthorized
    ...
    <BLANKLINE>

The bug supervisor of a product can also add tags.

    >>> login("foo.bar@canonical.com")
    >>> salgado = getUtility(IPersonSet).getByName("salgado")
    >>> product = factory.makeProduct(name="tags-test-product2")
    >>> logout()
    >>> ws_salgado = webservice.get("/~salgado").jsonBody()
    >>> print(
    ...     webservice.patch(
    ...         "/tags-test-product2",
    ...         "application/json",
    ...         json.dumps({"bug_supervisor_link": ws_salgado["self_link"]}),
    ...     )
    ... )
    HTTP/1.1 209 Content Returned...

The webservice client is logged in as salgado and he can add a new official
tag.

    >>> print(
    ...     webservice.named_post(
    ...         "/tags-test-product2",
    ...         "addOfficialBugTag",
    ...         tag="test-bug-tag2",
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...
    <BLANKLINE>
    null

Official tags must conform to the same format as ordinary tags.

    >>> print(
    ...     webservice.named_post(
    ...         "/tags-test-product",
    ...         "addOfficialBugTag",
    ...         tag="an invalid tag !!!",
    ...     )
    ... )
    HTTP/1.1 400 Bad Request
    ...
    tag: ...an invalid tag !!!...

We can also access official tags as a list.

    >>> tags_test_product = webservice.get("/tags-test-product").jsonBody()
    >>> tags_test_product["official_bug_tags"]
    []
    >>> print(
    ...     webservice.patch(
    ...         "/tags-test-product",
    ...         "application/json",
    ...         json.dumps({"official_bug_tags": ["foo", "bar"]}),
    ...     )
    ... )
    HTTP/1.1 209 Content Returned...

    >>> tags_test_product = webservice.get("/tags-test-product").jsonBody()
    >>> for tag in tags_test_product["official_bug_tags"]:
    ...     print(tag)
    ...
    bar
    foo

    >>> login("foo.bar@canonical.com")
    >>> distribution = factory.makeDistribution(name="testix")
    >>> logout()
    >>> print(
    ...     webservice.patch(
    ...         "/testix",
    ...         "application/json",
    ...         json.dumps({"official_bug_tags": ["foo", "bar"]}),
    ...     )
    ... )
    HTTP/1.1 209 Content Returned...

bug_supervisor
--------------

We can retrieve or set a person or team as the bug supervisor for projects.

    >>> firefox_project = webservice.get("/firefox").jsonBody()
    >>> print(firefox_project["bug_supervisor_link"])
    None

    >>> print(
    ...     webservice.patch(
    ...         "/firefox",
    ...         "application/json",
    ...         json.dumps(
    ...             {"bug_supervisor_link": firefox_project["owner_link"]}
    ...         ),
    ...     )
    ... )
    HTTP/1.1 209 Content Returned...

    >>> firefox_project = webservice.get("/firefox").jsonBody()
    >>> print(firefox_project["bug_supervisor_link"])
    http://api.launchpad.test/beta/~name12

We can also do this for distributions.

    >>> ubuntutest_dist = webservice.get("/ubuntutest").jsonBody()
    >>> print(ubuntutest_dist["bug_supervisor_link"])
    None

    >>> print(
    ...     webservice.patch(
    ...         "/ubuntutest",
    ...         "application/json",
    ...         json.dumps(
    ...             {"bug_supervisor_link": ubuntutest_dist["owner_link"]}
    ...         ),
    ...     )
    ... )
    HTTP/1.1 209 Content Returned...

    >>> ubuntutest_dist = webservice.get("/ubuntutest").jsonBody()
    >>> print(ubuntutest_dist["bug_supervisor_link"])
    http://api.launchpad.test/beta/~ubuntu-team

Setting the bug supervisor is restricted to owners and launchpad admins.

    >>> print(
    ...     user_webservice.patch(
    ...         "/ubuntutest",
    ...         "application/json",
    ...         json.dumps({"bug_supervisor_link": None}),
    ...     )
    ... )
    HTTP/1.1 401 Unauthorized
    ...
    <BLANKLINE>
