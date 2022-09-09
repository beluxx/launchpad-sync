Package sets
------------

Package sets facilitate the grouping of packages for purposes like the
control of upload permissions, the calculation of build and runtime package
dependencies etc.

Initially, package sets will be used to enforce upload permissions to source
packages. Later they may be put to other uses as well.

Please note: the purpose of the tests that follow is merely to test the
correctness of exposing package sets on the web services API.

The actual package set *functionality* is tested in much greater detail
here:

    lb/lp/soyuz/tests/test_packageset.py

Please refer to the tests contained in the file above if you are really
interested in package sets and the complete functionality they offer.


General package set properties
==============================

We start off by creating an 'umbrella' package set that will include all
source packages.

    >>> from zope.component import getUtility

    >>> name12 = webservice.get("/~name12").jsonBody()
    >>> response = webservice.named_post(
    ...     "/package-sets",
    ...     "new",
    ...     {},
    ...     distroseries="/ubuntu/hoary",
    ...     name="umbrella",
    ...     description="Contains all source packages",
    ...     owner=name12["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

Let's make sure the newly created package set is present.

    >>> login("foo.bar@canonical.com")
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.soyuz.interfaces.packageset import IPackagesetSet
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> ps_factory = getUtility(IPackagesetSet)
    >>> print(ps_factory.getByName(ubuntu.currentseries, "umbrella").name)
    umbrella

Can we access it via the webservice API as well?

    >>> logout()
    >>> umbrella = webservice.get(
    ...     "/package-sets/ubuntu/hoary/umbrella"
    ... ).jsonBody()
    >>> print(umbrella["self_link"])
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/umbrella

`PackageSet`s can be looked up by name.

    >>> response = webservice.named_get(
    ...     "/package-sets",
    ...     "getByName",
    ...     {},
    ...     distroseries="/ubuntu/hoary",
    ...     name="umbrella",
    ... )
    >>> print(response.jsonBody()["self_link"])
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/umbrella

When a `PackageSet` cannot be found, an error is returned.

    >>> response = webservice.named_get(
    ...     "/package-sets",
    ...     "getByName",
    ...     {},
    ...     distroseries="/ubuntu/hoary",
    ...     name="not-found",
    ... )
    >>> print(response)
    HTTP/1.1 404 Not Found
    ...
    No such package set (in the specified distro series): 'not-found'.

Here's an example with a funny URL concoted by a "smart" user.

    >>> response = webservice.get(
    ...     "/package-sets/ubuntu/lucid-plus-1/umbrella/+pwn"
    ... )
    >>> print(response)
    HTTP/1.1 404 Not Found
    ...

Let's create another set.

    >>> response = webservice.named_post(
    ...     "/package-sets",
    ...     "new",
    ...     {},
    ...     distroseries="/ubuntu/hoary",
    ...     name="shortlived",
    ...     description="An ephemeral packageset",
    ...     owner=name12["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

We can modify it, and even give it away.

    >>> from simplejson import dumps
    >>> name16 = webservice.get("/~name16").jsonBody()
    >>> patch = {
    ...     "name": "renamed",
    ...     "description": "Repurposed packageset",
    ...     "owner_link": name16["self_link"],
    ... }
    >>> response = webservice.patch(
    ...     "/package-sets/ubuntu/hoary/shortlived",
    ...     "application/json",
    ...     dumps(patch),
    ... )
    >>> print(response)
    HTTP/1.1 301 Moved Permanently
    ...

And then delete it.

    >>> response = webservice.delete(
    ...     "/package-sets/ubuntu/hoary/renamed", {}, api_version="devel"
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

Populate the 'umbrella' package set with source packages.

    >>> from lp.services.database.interfaces import IStore
    >>> from lp.registry.model.sourcepackagename import SourcePackageName
    >>> all_spns = IStore(SourcePackageName).find(SourcePackageName)
    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/umbrella",
    ...     "addSources",
    ...     {},
    ...     names=[spn.name for spn in all_spns],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

Note that attempts to add or remove source package names that do not
exist will not fail. Non-existing source package names are *ignored*.

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/umbrella",
    ...     "addSources",
    ...     {},
    ...     names=["does-not-exist"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    null

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/umbrella",
    ...     "removeSources",
    ...     {},
    ...     names=["does-not-exist"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    null

Let's see what we got.

    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/umbrella", "getSourcesIncluded", {}
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    ["a52dec",
     "alsa-utils",
     "at",
     "cdrkit",
     "cnews",
     "commercialpackage",
     "evolution",
     "foobar",
     "iceweasel",
     "language-pack-de",
     "libstdc++",
     "linux-source-2.6.15",
     "mozilla",
     "mozilla-firefox",
     "netapplet",
     "pmount",
     "thunderbird"]

Source package associations can be severed as well. In the example below
the 'foobar' and 'iceweasel' source package associations will be removed
from the 'umbrella' package set.

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/umbrella",
    ...     "removeSources",
    ...     {},
    ...     names=["foobar", "iceweasel"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

Please note that the 'foobar' and 'iceweasel' source packages are absent
from the list below.

    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/umbrella", "getSourcesIncluded", {}
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    ["a52dec",
     "alsa-utils",
     "at",
     "cdrkit",
     "cnews",
     "commercialpackage",
     "evolution",
     "language-pack-de",
     "libstdc++",
     "linux-source-2.6.15",
     "mozilla",
     "mozilla-firefox",
     "netapplet",
     "pmount",
     "thunderbird"]

Accessing the top-level package set URL will return the first 50 package sets
sorted by name.

    >>> def print_payload(response):
    ...     body = response.jsonBody()
    ...     for entry in body["entries"]:
    ...         print(entry["self_link"])
    ...

    >>> response = anon_webservice.get("/package-sets/")
    >>> print_payload(response)
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/umbrella

Package sets may include other package sets (as subsets). At this point,
however, we only have the 'umbrella' package set. It hence has no subsets.

    >>> from lazr.restful.testing.webservice import pprint_collection
    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/umbrella", "setsIncluded", {}
    ... )
    >>> pprint_collection(response.jsonBody())
    start: 0
    total_size: 0
    ---

Let's create a few more package sets and set up a package set hierarchy.

    >>> response = webservice.named_post(
    ...     "/package-sets",
    ...     "new",
    ...     {},
    ...     distroseries="/ubuntu/hoary",
    ...     name="gnome",
    ...     description="Contains all gnome packages",
    ...     owner=name12["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

    >>> response = webservice.named_post(
    ...     "/package-sets",
    ...     "new",
    ...     {},
    ...     distroseries="/ubuntu/hoary",
    ...     name="mozilla",
    ...     description="Contains all mozilla packages",
    ...     owner=name12["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...


Package sets and distro series
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every package set is associated with a distro series.

    >>> from lazr.restful.testing.webservice import pprint_entry
    >>> mozilla = webservice.named_get(
    ...     "/package-sets",
    ...     "getByName",
    ...     {},
    ...     distroseries="/ubuntu/hoary",
    ...     name="mozilla",
    ... ).jsonBody()
    >>> print(mozilla["distroseries_link"])
    http://api.launchpad.test/beta/ubuntu/hoary

    >>> print(mozilla["self_link"])
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/mozilla

A collection of package sets belonging to a given distro series can be
obtained via the `getBySeries` call.

    >>> packagesets = webservice.named_get(
    ...     "/package-sets",
    ...     "getBySeries",
    ...     {},
    ...     distroseries=mozilla["distroseries_link"],
    ... ).jsonBody()
    >>> for entry in packagesets["entries"]:
    ...     print("{entry[name]}: {entry[description]}".format(entry=entry))
    ...
    gnome: Contains all gnome packages
    mozilla: Contains all mozilla packages
    umbrella: Contains all source packages


Related package sets
~~~~~~~~~~~~~~~~~~~~

When adding a package set we can specify that is to be related to another set
that exists already.

    >>> grumpy = webservice.get("/ubuntu/grumpy").jsonBody()
    >>> print(grumpy["self_link"])
    http://api.launchpad.test/beta/ubuntu/grumpy

We are adding a new 'mozilla' package set to the 'grumpy' distro series and
it is related to 'mozilla' in 'hoary'.

    >>> response = webservice.named_post(
    ...     "/package-sets",
    ...     "new",
    ...     {},
    ...     distroseries=grumpy["self_link"],
    ...     name="mozilla",
    ...     owner=name12["self_link"],
    ...     description="Contains all mozilla packages in grumpy",
    ...     related_set=mozilla["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

    >>> grumpy_mozilla = webservice.named_get(
    ...     "/package-sets",
    ...     "getByName",
    ...     {},
    ...     name="mozilla",
    ...     distroseries=grumpy["self_link"],
    ... ).jsonBody()
    >>> print(grumpy_mozilla["distroseries_link"])
    http://api.launchpad.test/beta/ubuntu/grumpy

    >>> print(grumpy_mozilla["self_link"])
    http://api.launchpad.test/beta/package-sets/ubuntu/grumpy/mozilla

    >>> response = webservice.named_get(
    ...     mozilla["self_link"], "relatedSets", {}
    ... )
    >>> print_payload(response)
    http://api.launchpad.test/beta/package-sets/ubuntu/grumpy/mozilla


Package set hierarchy
=====================

More package sets are needed to set up the hierarchy described below.

    >>> response = webservice.named_post(
    ...     "/package-sets",
    ...     "new",
    ...     {},
    ...     distroseries="/ubuntu/hoary",
    ...     name="firefox",
    ...     description="Contains all firefox packages",
    ...     owner=name12["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

    >>> response = webservice.named_post(
    ...     "/package-sets",
    ...     "new",
    ...     {},
    ...     distroseries="/ubuntu/hoary",
    ...     name="thunderbird",
    ...     owner=name12["self_link"],
    ...     description="Contains all thunderbird packages",
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

    >>> response = webservice.named_post(
    ...     "/package-sets",
    ...     "new",
    ...     {},
    ...     distroseries="/ubuntu/hoary",
    ...     name="languagepack",
    ...     owner=name12["self_link"],
    ...     description="Contains all languagepack packages",
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

The 'languagepack' package set will be removed later (in hoary). Let's add a
set with the same name in 'grumpy' to make sure that the right one is found.

    >>> response = webservice.named_post(
    ...     "/package-sets",
    ...     "new",
    ...     {},
    ...     distroseries=grumpy["self_link"],
    ...     name="languagepack",
    ...     owner=name12["self_link"],
    ...     description="Contains all languagepack packages",
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

In order to test whether methods relating to package set hierarchies were
exposed on the Launchpad API correctly we will define the following package
set hierarchy:

    * umbrella
      * gnome
        * languagepack
      * mozilla
        * firefox
        * thunderbird
          * languagepack

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/umbrella",
    ...     "addSubsets",
    ...     {},
    ...     names=["gnome", "mozilla"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/gnome",
    ...     "addSubsets",
    ...     {},
    ...     names=["languagepack"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/thunderbird",
    ...     "addSubsets",
    ...     {},
    ...     names=["languagepack"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/mozilla",
    ...     "addSubsets",
    ...     {},
    ...     names=["firefox", "thunderbird"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

Similarly to 'addSources' and 'removeSources', adding or removing
non-existing package sets will not fail.

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/thunderbird",
    ...     "addSubsets",
    ...     {},
    ...     names=["does-not-exist"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    null

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/thunderbird",
    ...     "removeSubsets",
    ...     {},
    ...     names=["does-not-exist"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    null

The 'umbrella' package set should have plenty of subsets now.

    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/umbrella", "setsIncluded", {}
    ... )
    >>> print_payload(response)
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/firefox
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/gnome
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/languagepack
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/mozilla
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/thunderbird

However only two of the above are direct subsets.

    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/umbrella",
    ...     "setsIncluded",
    ...     {},
    ...     direct_inclusion=True,
    ... )
    >>> print_payload(response)
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/gnome
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/mozilla

Let's ask the question the other way around what package sets are including
a particular subset?

    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/languagepack", "setsIncludedBy", {}
    ... )
    >>> print_payload(response)
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/gnome
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/mozilla
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/thunderbird
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/umbrella

The list of package sets that *directly* include 'languagepack' will be
shorter because the transitive closure is ignored.

    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/languagepack",
    ...     "setsIncludedBy",
    ...     {},
    ...     direct_inclusion=True,
    ... )
    >>> print_payload(response)
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/gnome
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/thunderbird

We can remove subsets as well. In the example below 'thunderbird' will
stop including 'languagepack'.

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/thunderbird",
    ...     "removeSubsets",
    ...     {},
    ...     names=["languagepack"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

And, here we go, now 'languagepack' has only one direct predecessor: 'gnome'.

    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/languagepack",
    ...     "setsIncludedBy",
    ...     {},
    ...     direct_inclusion=True,
    ... )
    >>> print_payload(response)
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/gnome

Let's add a few source packages to the 'firefox' and the 'thunderbird'
package sets.

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/firefox",
    ...     "addSources",
    ...     {},
    ...     names=["at", "mozilla-firefox", "language-pack-de"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/firefox", "getSourcesIncluded", {}
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    ["at", "language-pack-de", "mozilla-firefox"]

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/hoary/thunderbird",
    ...     "addSources",
    ...     {},
    ...     names=["at", "cnews", "thunderbird", "language-pack-de"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/thunderbird", "getSourcesIncluded", {}
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    ["at", "cnews", "language-pack-de", "thunderbird"]

Which package sets include 'mozilla-firefox'?

    >>> response = webservice.named_get(
    ...     "/package-sets/",
    ...     "setsIncludingSource",
    ...     {},
    ...     sourcepackagename="mozilla-firefox",
    ... )
    >>> print_payload(response)
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/firefox
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/mozilla
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/umbrella

Which package sets include the 'mozilla-firefox' source package *directly*?

    >>> response = webservice.named_get(
    ...     "/package-sets/",
    ...     "setsIncludingSource",
    ...     {},
    ...     sourcepackagename="mozilla-firefox",
    ...     direct_inclusion=True,
    ... )
    >>> print_payload(response)
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/firefox
    http://api.launchpad.test/beta/package-sets/ubuntu/hoary/umbrella

If a non-existing source package name is passed it returns an error.

    >>> response = webservice.named_get(
    ...     "/package-sets/",
    ...     "setsIncludingSource",
    ...     {},
    ...     sourcepackagename="does-not-exist",
    ... )
    >>> print(response)
    HTTP/1.1 404 Not Found
    ...
    No such source package: 'does-not-exist'.

What source packages are shared by the 'firefox' and the 'thunderbird'
package sets?

    >>> thunderbird = webservice.get(
    ...     "/package-sets/ubuntu/hoary/thunderbird"
    ... ).jsonBody()
    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/firefox",
    ...     "getSourcesSharedBy",
    ...     {},
    ...     other_package_set=thunderbird["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    ["at", "language-pack-de"]

How about the complement set i.e. the packages not shared?

    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/firefox",
    ...     "getSourcesNotSharedBy",
    ...     {},
    ...     other_package_set=thunderbird["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    ["mozilla-firefox"]

    >>> firefox = webservice.get(
    ...     "/package-sets/ubuntu/hoary/firefox"
    ... ).jsonBody()
    >>> response = webservice.named_get(
    ...     "/package-sets/ubuntu/hoary/thunderbird",
    ...     "getSourcesNotSharedBy",
    ...     {},
    ...     other_package_set=firefox["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    ["cnews", "thunderbird"]


Archive permissions and package sets
====================================

Operating on package set based archive permissions is possible via
the Launchpad API as well.

The newPackagesetUploader() method is a factory function that adds a new
permission for a person to upload source packages included in a given
package set.

    >>> distros = webservice.get("/distros").jsonBody()
    >>> ubuntu = distros["entries"][0]

Grant upload privileges to 'name12' for package set 'firefox' in the Ubuntu
main archive.

    >>> response = webservice.named_post(
    ...     ubuntu["main_archive_link"],
    ...     "newPackagesetUploader",
    ...     {},
    ...     person=name12["self_link"],
    ...     packageset=firefox["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

Let's see what we've got:

    >>> new_permission = webservice.get(
    ...     response.getHeader("Location")
    ... ).jsonBody()
    >>> pprint_entry(new_permission)  # noqa
    archive_link: 'http://.../+archive/primary'
    component_name: None
    date_created: ...
    explicit: False
    package_set_name: 'firefox'
    permission: 'Archive Upload Rights'
    person_link: 'http://.../~name12'
    pocket: None
    resource_type_link: ...
    self_link: 'http://.../+archive/primary/+upload/name12?type=packageset&item=firefox&series=hoary'
    source_package_name: None

Grant upload privileges to 'name12' for package set 'mozilla' in the Ubuntu
main archive.

    >>> response = webservice.named_post(
    ...     ubuntu["main_archive_link"],
    ...     "newPackagesetUploader",
    ...     {},
    ...     person=name12["self_link"],
    ...     packageset=mozilla["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

The following query should only find the permission for the 'firefox'
package set since we're disallowing the use of the package set hierarchy.

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "getUploadersForPackageset",
    ...     {},
    ...     packageset=firefox["self_link"],
    ... )
    >>> print_payload(response)  # noqa
    http://.../+archive/primary/+upload/name12?type=packageset&item=firefox&series=hoary

Same query, this time allowing the use of the package set hierarchy, finds
the permission for the 'mozilla' package set as well.

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "getUploadersForPackageset",
    ...     {},
    ...     packageset=firefox["self_link"],
    ...     direct_permissions=False,
    ... )
    >>> print_payload(response)  # noqa
    http://.../+archive/primary/+upload/name12?type=packageset&item=firefox&series=hoary
    http://.../+archive/primary/+upload/name12?type=packageset&item=mozilla&series=hoary

Let's delete the upload privilege for the 'mozilla' package set.

    >>> response = webservice.named_post(
    ...     ubuntu["main_archive_link"],
    ...     "deletePackagesetUploader",
    ...     {},
    ...     person=name12["self_link"],
    ...     packageset=mozilla["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

Since the privilege for the 'mozilla' package set was deleted the listing
shows only the remaining permission for the 'firefox' package set.

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "getUploadersForPackageset",
    ...     {},
    ...     packageset=firefox["self_link"],
    ...     direct_permissions=False,
    ... )
    >>> print_payload(response)  # noqa
    http://.../+archive/primary/+upload/name12?type=packageset&item=firefox&series=hoary

Let's grant 'cprov' an upload permission to 'mozilla' and 'thunderbird'.

    >>> cprov = webservice.get("/~cprov").jsonBody()
    >>> response = webservice.named_post(
    ...     ubuntu["main_archive_link"],
    ...     "newPackagesetUploader",
    ...     {},
    ...     person=cprov["self_link"],
    ...     packageset=mozilla["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

    >>> response = webservice.named_post(
    ...     ubuntu["main_archive_link"],
    ...     "newPackagesetUploader",
    ...     {},
    ...     person=cprov["self_link"],
    ...     packageset=thunderbird["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

We can view the package set based permissions granted to 'cprov' as follows:

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "getPackagesetsForUploader",
    ...     {},
    ...     person=cprov["self_link"],
    ... )
    >>> print_payload(response)  # noqa
    http://.../+archive/primary/+upload/cprov?type=packageset&item=mozilla&series=hoary
    http://.../+archive/primary/+upload/cprov?type=packageset&item=thunderbird&series=hoary

Let's check what package set based upload permissions 'cprov' has for the
'mozilla-firefox' package.

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "getPackagesetsForSourceUploader",
    ...     {},
    ...     sourcepackagename="thunderbird",
    ...     person=cprov["self_link"],
    ... )
    >>> print_payload(response)  # noqa
    http://.../+archive/primary/+upload/cprov?type=packageset&item=mozilla&series=hoary
    http://.../+archive/primary/+upload/cprov?type=packageset&item=thunderbird&series=hoary

As we expected 'cprov' may upload either via the 'thunderbird' package set
that directly contains the source package in question or via the 'mozilla'
package set that includes the 'thunderbird' set.

How about the 'mozilla-firefox' source package? Is 'cprov' allowed uploads
to it?

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "getPackagesetsForSourceUploader",
    ...     {},
    ...     sourcepackagename="mozilla-firefox",
    ...     person=cprov["self_link"],
    ... )
    >>> print_payload(response)  # noqa
    http://.../+archive/primary/+upload/cprov?type=packageset&item=mozilla&series=hoary

Yes, and, again via the 'mozilla' package set.

Sometimes we don't care about the details. We just want a yes/no answer to
the question: "is person X allowed to upload package P?".

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "isSourceUploadAllowed",
    ...     {},
    ...     sourcepackagename="mozilla-firefox",
    ...     person=cprov["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    true

Archive permissions have distro series scope. We did not specify a distro
series in the query above. Hence the `currentseries` in Ubuntu is assumed
('hoary').
The following query (note the additional 'distroseries' parameter) is
thus equivalent:

    >>> print(ubuntu["current_series_link"])
    http://api.launchpad.test/beta/ubuntu/hoary
    >>> hoary = webservice.get("/ubuntu/hoary").jsonBody()
    >>> print(hoary["self_link"])
    http://api.launchpad.test/beta/ubuntu/hoary

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "isSourceUploadAllowed",
    ...     {},
    ...     sourcepackagename="mozilla-firefox",
    ...     person=cprov["self_link"],
    ...     distroseries=hoary["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    true

Since cprov's upload permission is limited to the current distro series
('hoary') checking the same permission for 'grumpy' will fail.

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "isSourceUploadAllowed",
    ...     {},
    ...     sourcepackagename="mozilla-firefox",
    ...     person=cprov["self_link"],
    ...     distroseries=grumpy["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    false

'name12' should not be allowed to upload the 'thunderbird' source package.

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "isSourceUploadAllowed",
    ...     {},
    ...     sourcepackagename="thunderbird",
    ...     person=name12["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    false

Let's create a (related) package set in 'grumpy' and authorize 'name12' to
upload to it.

This will fail since 'name12' has no permissions applying to 'grumpy' yet.

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "isSourceUploadAllowed",
    ...     {},
    ...     sourcepackagename="thunderbird",
    ...     person=name12["self_link"],
    ...     distroseries=grumpy["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    false

Create a new package set ('thunderbird') in 'grumpy'.

    >>> response = webservice.named_post(
    ...     "/package-sets",
    ...     "new",
    ...     {},
    ...     distroseries=grumpy["self_link"],
    ...     name="thunderbird",
    ...     description="Contains all thunderbird packages in grumpy",
    ...     owner=name12["self_link"],
    ...     related_set=thunderbird["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

    >>> response = webservice.named_get(
    ...     thunderbird["self_link"], "relatedSets", {}
    ... )
    >>> print_payload(response)
    http://api.launchpad.test/beta/package-sets/ubuntu/grumpy/thunderbird

Associate 'thunderbird' with the appropriate source packages.

    >>> response = webservice.named_post(
    ...     "/package-sets/ubuntu/grumpy/thunderbird",
    ...     "addSources",
    ...     {},
    ...     names=["thunderbird", "language-pack-de"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

Grant 'name12' upload permissions to 'thunderbird' in 'grumpy'.

    >>> grouchy_bird = webservice.get(
    ...     "/package-sets/ubuntu/grumpy/thunderbird"
    ... ).jsonBody()

    >>> response = webservice.named_post(
    ...     ubuntu["main_archive_link"],
    ...     "newPackagesetUploader",
    ...     {},
    ...     person=name12["self_link"],
    ...     packageset=grouchy_bird["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 201 Created
    ...

Does the new archive permission show up?

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "getPackagesetsForUploader",
    ...     {},
    ...     person=name12["self_link"],
    ... )
    >>> print_payload(response)  # noqa
    http://...+archive/primary/+upload/name12?type=packageset&item=firefox&series=hoary
    http://...+archive/primary/+upload/name12?type=packageset&item=thunderbird&series=grumpy

And now 'name12' should be authorized to upload source package
'thunderbird' in 'grumpy'.

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "isSourceUploadAllowed",
    ...     {},
    ...     sourcepackagename="thunderbird",
    ...     person=name12["self_link"],
    ...     distroseries=grumpy["self_link"],
    ... )
    >>> print(response)
    HTTP/1.1 200 Ok
    ...
    true

Sometimes it's also interesting to see what package set based upload
permissions apply to a source package irrespective of the principal.

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "getPackagesetsForSource",
    ...     {},
    ...     sourcepackagename="mozilla-firefox",
    ... )
    >>> print_payload(response)  # noqa
    http://.../+archive/primary/+upload/name12?type=packageset&item=firefox&series=hoary

The listing above only shows the *direct* upload permission granted to
'name12' via the 'firefox' package set.

We can ask the same question but this time include the indirect upload
permissions arising from the package set hierarchy as well.

    >>> response = webservice.named_get(
    ...     ubuntu["main_archive_link"],
    ...     "getPackagesetsForSource",
    ...     {},
    ...     sourcepackagename="mozilla-firefox",
    ...     direct_permissions=False,
    ... )
    >>> print_payload(response)  # noqa
    http://.../+archive/primary/+upload/name12?type=packageset&item=firefox&series=hoary
    http://.../+archive/primary/+upload/cprov?type=packageset&item=mozilla&series=hoary

Now we see the upload permission granted to 'cprov' via the 'mozilla' package
set listed as well.


Archive permission URLs
=======================

Archive permissions can be accessed via their URLs in direct fashion.

If we do *not* specify the distro series for package set based archive
permission URLs a 404 will result.

    >>> url = (
    ...     "/ubuntu/+archive/primary/+upload/name12"
    ...     "?type=packageset&item=thunderbird"
    ... )
    >>> response = webservice.get(url)
    >>> print(response)
    HTTP/1.1 404 Not Found
    ...

The same happens if a user tries to doctor an URL with an invalid distro
series.

    >>> url = (
    ...     "/ubuntu/+archive/primary/+upload/name12"
    ...     "?type=packageset&item=thunderbird&series=foobar"
    ... )
    >>> response = webservice.get(url)
    >>> print(response)
    HTTP/1.1 404 Not Found
    ...

The user 'name12' has no upload permission for 'thunderbird' in 'hoary'..

    >>> url = (
    ...     "/ubuntu/+archive/primary/+upload/name12"
    ...     "?type=packageset&item=thunderbird&series=hoary"
    ... )
    >>> response = webservice.get(url)
    >>> print(response)
    HTTP/1.1 404 Not Found
    ...

.. but is allowed to upload to 'thunderbird' in 'grumpy'.

    >>> url = (
    ...     "/ubuntu/+archive/primary/+upload/name12"
    ...     "?type=packageset&item=thunderbird&series=grumpy"
    ... )
    >>> permission = webservice.get(url).jsonBody()
    >>> print(permission["package_set_name"])
    thunderbird
    >>> print(permission["distro_series_name"])
    grumpy

The user 'cprov' has no upload permission for 'thunderbird' in 'hoary'.

    >>> url = (
    ...     "/ubuntu/+archive/primary/+upload/cprov"
    ...     "?type=packageset&item=thunderbird&series=hoary"
    ... )
    >>> permission = webservice.get(url).jsonBody()
    >>> pprint_entry(permission)
    archive_link: 'http://api.launchpad.test/beta/ubuntu/+archive/primary'
    ...
    distro_series_name: 'hoary'
    ...
    package_set_name: 'thunderbird'
    permission: 'Archive Upload Rights'
    person_link: 'http://api.launchpad.test/beta/~cprov'
    ...
