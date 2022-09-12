Archive dependencies
====================

`ArchiveDependency` records represent build-dependencies between
archives, and are exposed through the API.

Most of the tests live in
lib/lp/soyuz/stories/webservice/xx-archive.rst.

Firstly we need to set some things up: we need a PPA with a dependency.
We'll use Celso's PPA, and give it a custom dependency on the primary
archive, and then create a private PPA for Celso with a similar custom
dependency.

    >>> import simplejson
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.pocket import PackagePublishingPocket
    >>> from lp.soyuz.interfaces.component import IComponentSet
    >>> login("foo.bar@canonical.com")
    >>> cprov_db = getUtility(IPersonSet).getByName("cprov")
    >>> cprov_ppa_db = cprov_db.archive
    >>> dep = cprov_ppa_db.addArchiveDependency(
    ...     cprov_ppa_db.distribution.main_archive,
    ...     PackagePublishingPocket.RELEASE,
    ...     component=getUtility(IComponentSet)["universe"],
    ... )
    >>> cprov_private_ppa_db = factory.makeArchive(
    ...     private=True,
    ...     owner=cprov_db,
    ...     name="p3a",
    ...     distribution=cprov_ppa_db.distribution,
    ...     description="packages to help my friends.",
    ... )
    >>> dep = cprov_private_ppa_db.addArchiveDependency(
    ...     cprov_ppa_db.distribution.main_archive,
    ...     PackagePublishingPocket.RELEASE,
    ...     component=getUtility(IComponentSet)["universe"],
    ... )
    >>> logout()

Any user can retrieve a public PPA's dependencies.

    >>> print(user_webservice.get("/~cprov/+archive/ubuntu/ppa/dependencies"))
    HTTP/1.1 200 Ok
    ...

    >>> print(
    ...     user_webservice.get("/~cprov/+archive/ubuntu/ppa/+dependency/1")
    ... )
    HTTP/1.1 200 Ok
    ...

The dependencies of a private archive are private.  Unprivileged users
can't get a list of the dependencies.

    >>> print(user_webservice.get("/~cprov/+archive/ubuntu/p3a/dependencies"))
    HTTP/1.1 401 Unauthorized
    ...
    (<Archive at ...>, 'dependencies', 'launchpad.SubscriberView')

Nor can said user craft a URL to a dependency.

    >>> print(
    ...     user_webservice.get("/~cprov/+archive/ubuntu/p3a/+dependency/1")
    ... )
    HTTP/1.1 401 Unauthorized
    ...
    (<Archive at ...>, 'getArchiveDependency', 'launchpad.View')

Celso can see them if we grant private permissions, of course.

    >>> from lp.testing.pages import webservice_for_person
    >>> from lp.services.webapp.interfaces import OAuthPermission
    >>> cprov_webservice = webservice_for_person(
    ...     cprov_db, permission=OAuthPermission.WRITE_PRIVATE
    ... )
    >>> print(
    ...     cprov_webservice.get("/~cprov/+archive/ubuntu/p3a/dependencies")
    ... )
    HTTP/1.1 200 Ok
    ...
    >>> print(
    ...     cprov_webservice.get("/~cprov/+archive/ubuntu/p3a/+dependency/1")
    ... )
    HTTP/1.1 200 Ok
    ...

But even he can't write to a dependency.

    >>> mark_ppa = cprov_webservice.get(
    ...     "/~mark/+archive/ubuntu/ppa"
    ... ).jsonBody()
    >>> print(
    ...     cprov_webservice.patch(
    ...         "/~cprov/+archive/ubuntu/ppa/+dependency/1",
    ...         "application/json",
    ...         simplejson.dumps({"archive_link": mark_ppa["self_link"]}),
    ...     )
    ... )
    HTTP/1.1 400 Bad Request
    ...
    archive_link: You tried to modify a read-only attribute.
    <BLANKLINE>

    >>> print(
    ...     cprov_webservice.patch(
    ...         "/~cprov/+archive/ubuntu/ppa/+dependency/1",
    ...         "application/json",
    ...         simplejson.dumps({"dependency_link": mark_ppa["self_link"]}),
    ...     )
    ... )
    HTTP/1.1 400 Bad Request
    ...
    dependency_link: You tried to modify a read-only attribute.
    <BLANKLINE>

    >>> print(
    ...     cprov_webservice.patch(
    ...         "/~cprov/+archive/ubuntu/ppa/+dependency/1",
    ...         "application/json",
    ...         simplejson.dumps({"pocket": "Security"}),
    ...     )
    ... )
    HTTP/1.1 400 Bad Request
    ...
    pocket: You tried to modify a read-only attribute.
    <BLANKLINE>
