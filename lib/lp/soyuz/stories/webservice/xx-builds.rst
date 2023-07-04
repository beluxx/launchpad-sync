=============
Build Records
=============

Build records encapsulate a request to turn a source into a binary.
The webservice allows builds to be retrieved in the context of a source
publication.

First, we need to insert some fake changes file data in the librarian so that
source publications can be retrieved.

    >>> login("foo.bar@canonical.com")
    >>> from lp.archiveuploader.tests import (
    ...     insertFakeChangesFileForAllPackageUploads,
    ... )
    >>> insertFakeChangesFileForAllPackageUploads()
    >>> from zope.component import getUtility
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.model.gpgkey import GPGKey
    >>> from lp.services.database.interfaces import IStore
    >>> name16 = getUtility(IPersonSet).getByName("name16")
    >>> fake_signer = IStore(GPGKey).find(GPGKey, owner=name16).one()
    >>> ppa = getUtility(IPersonSet).getByName("cprov").archive
    >>> for pub in ppa.getPublishedSources():
    ...     pub = removeSecurityProxy(pub)
    ...     pub.sourcepackagerelease.signing_key_owner = fake_signer.owner
    ...     pub.sourcepackagerelease.signing_key_fingerprint = (
    ...         fake_signer.fingerprint
    ...     )
    ...
    >>> transaction.commit()
    >>> logout()

Retrieve a source publication:

    >>> cprov_archive = webservice.get(
    ...     "/~cprov/+archive/ubuntu/ppa"
    ... ).jsonBody()
    >>> pubs = webservice.named_get(
    ...     cprov_archive["self_link"], "getPublishedSources"
    ... ).jsonBody()
    >>> source_pub = pubs["entries"][0]
    >>> builds = webservice.named_get(
    ...     source_pub["self_link"], "getBuilds"
    ... ).jsonBody()

'builds' is a collection of Build records.  Each Build contains a number
of properties:

    >>> from lazr.restful.testing.webservice import pprint_entry
    >>> pprint_entry(builds["entries"][0])  # noqa
    arch_tag: 'i386'
    archive_link: 'http://.../beta/~cprov/+archive/ubuntu/ppa'
    builder_link: 'http://.../beta/builders/bob'
    can_be_cancelled: False
    can_be_rescored: False
    can_be_retried: True
    changesfile_url: None
    current_source_publication_link:
    'http://.../beta/~cprov/+archive/ubuntu/ppa/+sourcepub/27'
    date_created: '2007-07-08T00:00:00+00:00'
    date_finished: '2007-07-08T00:00:01+00:00'
    date_first_dispatched: None
    dependencies: None
    distribution_link: 'http://.../beta/ubuntu'
    log_url:
    'http://.../~cprov/+archive/ubuntu/ppa/+build/26/+files/netapplet-1.0.0.tar.gz'
    pocket: 'Release'
    resource_type_link: 'http://api.launchpad.test/beta/#build'
    score: None
    self_link: 'http://api.launchpad.test/beta/~cprov/+archive/ubuntu/ppa/+build/26'
    source_package_name: 'cdrkit'
    source_package_version: '1.0'
    status: 'Failed to build'
    title: 'i386 build of cdrkit 1.0 in ubuntu breezy-autotest RELEASE'
    upload_log_url: None
    web_link: 'http://launchpad.../~cprov/+archive/ubuntu/ppa/+build/26'

Whereas the 1.0 webservice for builds maintains the old property names
(without underscores):

    >>> builds_1_0 = webservice.named_get(
    ...     source_pub["self_link"].replace("beta", "1.0"), "getBuilds"
    ... )
    >>> pprint_entry(builds_1_0.jsonBody()["entries"][0])  # noqa
    arch_tag: 'i386'
    archive_link: 'http://.../~cprov/+archive/ubuntu/ppa'
    build_log_url:
    'http://.../~cprov/+archive/ubuntu/ppa/+build/26/+files/netapplet-1.0.0.tar.gz'
    builder_link: 'http://.../builders/bob'
    buildstate: 'Failed to build'
    can_be_cancelled: False
    can_be_rescored: False
    can_be_retried: True
    changesfile_url: None
    current_source_publication_link:
    'http://.../~cprov/+archive/ubuntu/ppa/+sourcepub/27'
    date_first_dispatched: None
    datebuilt: '2007-07-08T00:00:01+00:00'
    datecreated: '2007-07-08T00:00:00+00:00'
    dependencies: None
    distribution_link: 'http://.../ubuntu'
    pocket: 'Release'
    resource_type_link: 'http://.../#build'
    score: None
    self_link: 'http://.../~cprov/+archive/ubuntu/ppa/+build/26'
    source_package_name: 'cdrkit'
    source_package_version: '1.0'
    title: 'i386 build of cdrkit 1.0 in ubuntu breezy-autotest RELEASE'
    upload_log_url: None
    web_link: 'http://launchpad.../~cprov/+archive/ubuntu/ppa/+build/26'

devel webservice also contains build date_started and duration.

    >>> builds_devel = webservice.named_get(
    ...     source_pub["self_link"].replace("beta", "devel"), "getBuilds"
    ... )
    >>> pprint_entry(builds_devel.jsonBody()["entries"][0])  # noqa
    arch_tag: 'i386'
    archive_link: 'http://.../~cprov/+archive/ubuntu/ppa'
    build_log_url:
    'http://.../~cprov/+archive/ubuntu/ppa/+build/26/+files/netapplet-1.0.0.tar.gz'
    builder_link: 'http://.../builders/bob'
    buildstate: 'Failed to build'
    can_be_cancelled: False
    can_be_rescored: False
    can_be_retried: True
    changesfile_url: None
    current_source_publication_link:
    'http://.../~cprov/+archive/ubuntu/ppa/+sourcepub/27'
    date_first_dispatched: None
    date_started: '2007-07-07T23:58:41+00:00'
    datebuilt: '2007-07-08T00:00:01+00:00'
    datecreated: '2007-07-08T00:00:00+00:00'
    dependencies: None
    distribution_link: 'http://.../ubuntu'
    duration: '0:01:20'
    external_dependencies: None
    pocket: 'Release'
    resource_type_link: 'http://.../#build'
    score: None
    self_link: 'http://.../~cprov/+archive/ubuntu/ppa/+build/26'
    source_package_name: 'cdrkit'
    source_package_version: '1.0'
    title: 'i386 build of cdrkit 1.0 in ubuntu breezy-autotest RELEASE'
    upload_log_url: None
    web_link: 'http://launchpad.../~cprov/+archive/ubuntu/ppa/+build/26'


For testing purposes we will set 'buildlog' and 'upload_log' to the
same library file, so both can be verified.

    >>> login("foo.bar@canonical.com")
    >>> from lp.soyuz.interfaces.binarypackagebuild import (
    ...     IBinaryPackageBuildSet,
    ... )
    >>> build = getUtility(IBinaryPackageBuildSet).getByID(26)
    >>> build.storeUploadLog("i am a log")
    >>> logout()

IBinaryPackageBuild 'build_log_url' and 'upload_log_url' are webapp
URLs, relative to the build itself. This way API users can access
private files (stored in the restricted librarian) directly because they
will be proxied by the webapp.

    >>> builds = webservice.named_get(
    ...     source_pub["self_link"], "getBuilds"
    ... ).jsonBody()

    >>> print(builds["entries"][0]["log_url"])
    http://launchpad.test/~cprov/+archive/ubuntu/ppa/+build/26/+files/...

    >>> print(builds["entries"][0]["upload_log_url"])
    http://launchpad.test/~cprov/+archive/ubuntu/ppa/+build/26/+files/...

Re-trying builds
================

If a build is in a retry-able state, the retry method can be invoked
to cause a new build request for that build.  The caller must also have
permission to retry the build.  See doc/binarypackagebuild.rst and
stories/soyuz/xx-build-record.rst for more information.

    >>> a_build = builds["entries"][0]

Plain users have no permission to call retry:

    >>> print(user_webservice.named_post(a_build["self_link"], "retry"))
    HTTP/1.1 401 Unauthorized
    ...

Set up some more webservice users:

    >>> from lp.testing.pages import webservice_for_person
    >>> from lp.services.webapp.interfaces import OAuthPermission
    >>> login("foo.bar@canonical.com")
    >>> admin_person = getUtility(IPersonSet).getByName("mark")
    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> logout()

Admin users can call it:

    >>> admin_webservice = webservice_for_person(
    ...     admin_person, permission=OAuthPermission.WRITE_PUBLIC
    ... )
    >>> print(admin_webservice.named_post(a_build["self_link"], "retry"))
    HTTP/1.1 200 Ok
    ...

As can cprov who owns the PPA for the build:

    >>> cprov_webservice = webservice_for_person(
    ...     cprov, permission=OAuthPermission.WRITE_PUBLIC
    ... )
    >>> print(cprov_webservice.named_post(a_build["self_link"], "retry"))
    HTTP/1.1 400 Bad Request
    ...
    Build ... cannot be retried.

but in this case, although he has permission to retry the build, it
failed because it was already retried by an admin.  This is reflected in the
can_be_retried property:

    >>> builds = webservice.named_get(
    ...     source_pub["self_link"], "getBuilds"
    ... ).jsonBody()
    >>> print(builds["entries"][0]["can_be_retried"])
    False


Rescoring builds
================

When a build is in NEEDSBUILD state, it may be rescored using the 'rescore'
custom operation.  However, the caller must be a member of the buildd admins
team.

    >>> print(
    ...     user_webservice.named_post(
    ...         a_build["self_link"], "rescore", score=1000
    ...     )
    ... )
    HTTP/1.1 401 Unauthorized
    ...

The user cprov is a buildd admin.

    >>> login("foo.bar@canonical.com")
    >>> buildd_admins = getUtility(IPersonSet).getByName(
    ...     "launchpad-buildd-admins"
    ... )

    >>> cprov.inTeam(buildd_admins)
    True

    >>> logout()
    >>> print(
    ...     cprov_webservice.named_post(
    ...         a_build["self_link"], "rescore", score=1000
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...

The job has been rescored

    >>> updated_build = webservice.get(a_build["self_link"]).jsonBody()
    >>> print(updated_build["score"])
    1000

If the build cannot be retried, then a 400 code is returned.  Let's
alter the buildstate to one that cannot be retried:

    >>> login("foo.bar@canonical.com")
    >>> from lp.buildmaster.enums import BuildStatus
    >>> build.updateStatus(BuildStatus.FAILEDTOUPLOAD)
    >>> logout()

    >>> print(
    ...     cprov_webservice.named_post(
    ...         a_build["self_link"], "rescore", score=1000
    ...     )
    ... )
    HTTP/1.1 400 Bad Request
    ...
    Build ... cannot be rescored.
