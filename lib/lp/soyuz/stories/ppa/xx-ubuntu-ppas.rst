Ubuntu PPAs
===========

The Ubuntu page contains a link to get to the Personal Package Archives.

    >>> anon_browser.open("http://launchpad.test/ubuntu")
    >>> anon_browser.getLink("Personal Package Archives").click()
    >>> print_location(anon_browser.contents)
    Hierarchy: Ubuntu
    Tabs:
    * Overview (selected) - http://launchpad.test/ubuntu
    * Code - http://code.launchpad.test/ubuntu
    * Bugs - http://bugs.launchpad.test/ubuntu
    * Blueprints - http://blueprints.launchpad.test/ubuntu
    * Translations - http://translations.launchpad.test/ubuntu
    * Answers - http://answers.launchpad.test/ubuntu
    Main heading: Personal Package Archives for Ubuntu


Distribution PPA main page
--------------------------

Along with the search form this page also presents statistics about
the context PPAs (registered, active, number of sources and binaries
published) and a list of context series and corresponding architectures
supported for PPA.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             anon_browser.contents,
    ...             "supports_virtualized_architectures",
    ...         )
    ...     )
    ... )
    PPA supported series
    Hoary (5.04) - development i386 (official)
    Warty (4.10) - current i386 (official)

Up to 5 latest source publications are also presented in the 'Latest
sources' section.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(anon_browser.contents, "ppa_latest_uploads")
    ...     )
    ... )
    Latest uploads
    cdrkit 1.0 in breezy-autotest  in PPA for Celso Providelo ... ago
    iceweasel 1.0 in breezy-autotest in PPA for Mark Shuttleworth ... ago
    pmount 0.1-1 in warty in PPA for Celso Providelo ... ago
    iceweasel 1.0 in warty in PPA for Celso Providelo ... ago

The 5 most active PPAs are listed in the 'Most active' section. Since
we only have 3 PPAs in sampledata they are all presented.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(anon_browser.contents, "ppa_most_active")
    ...     )
    ... )
    Most active
    PPAs with the highest number of uploads in the last 7 days.


Nothing suitable in the sampledata, check the end of this document for
further tests.

Other distributions PPAs
------------------------

Currently we only support PPAs for a limited number of distros. The
'+ppas' page isn't linked for other distribution.

    >>> anon_browser.open("http://launchpad.test/debian")
    >>> anon_browser.getLink("Personal Package Archives")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

If we enable Debian PPA support, the links appear and the pages present
coherent data for a distribution with no PPAs.

    >>> from zope.component import getUtility
    >>> import transaction
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> login("admin@canonical.com")
    >>> debian = getUtility(IDistributionSet).getByName("debian")
    >>> debian.supports_ppas = True
    >>> logout()
    >>> transaction.commit()

    >>> anon_browser.open("http://launchpad.test/debian")
    >>> anon_browser.getLink("Personal Package Archives").click()
    >>> print(anon_browser.title)
    Personal Package Archives : Debian

PPA supported architectures reflects what we have in sampledata.

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(
    ...             anon_browser.contents,
    ...             "supports_virtualized_architectures",
    ...         )
    ...     )
    ... )
    PPA supported series
    Sarge (3.1) - frozen
    Woody (3.0) - current i386 (official)

'Latest uploads' section is not presented.

    >>> print(find_tag_by_id(anon_browser.contents, "ppa_latest_uploads"))
    None

'Most active' section is not presented.

    >>> print(find_tag_by_id(anon_browser.contents, "ppa_most_active"))
    None

The 'search' form is also suppressed.

    >>> anon_browser.getControl("Search", index=0).click()
    Traceback (most recent call last):
    ...
    LookupError: label ...'Search'
    ...


Searching PPAs
--------------

The search results are presented as a table with the columns Owner,
Description, Sources and Binaries, the latter two being a count.

The default search shows only active (those with, at least one,
PENDING or PUBLISHED source record) PPAs.

    >>> anon_browser.open("http://launchpad.test/ubuntu")
    >>> anon_browser.getLink("Personal Package Archives").click()
    >>> anon_browser.getControl("Search", index=0).click()
    >>> for ppa_row in find_tags_by_class(
    ...     anon_browser.contents, "ppa_batch_row"
    ... ):
    ...     print(extract_text(ppa_row))
    PPA for Celso Providelo
    packages to help my friends.
    3
    3
    PPA for Mark Shuttleworth
    packages to help the humanity (you know, ubuntu)
    1
    1

When a search is requested the information sections are not rendered.

    >>> print(find_tag_by_id(anon_browser.contents, "ppa_most_active"))
    None

    >>> print(find_tag_by_id(anon_browser.contents, "ppa_latest_uploads"))
    None

    >>> print(
    ...     find_tag_by_id(
    ...         anon_browser.contents, "supports_virtualized_architectures"
    ...     )
    ... )
    None

The information section will be only rendered if the page is reloaded
with no 'name_filter' GET argument, in other words, when no search was
request.

    >>> anon_browser.open("http://launchpad.test/ubuntu/+ppas")

    >>> find_tag_by_id(anon_browser.contents, "ppa_most_active") is not None
    True

    >>> find_tag_by_id(
    ...     anon_browser.contents, "ppa_latest_uploads"
    ... ) is not None
    True

    >>> find_tag_by_id(
    ...     anon_browser.contents, "supports_virtualized_architectures"
    ... ) is not None
    True

Back to the search form again anonymous users can click on a checkbox
to allow inactive PPA results.

    >>> anon_browser.getControl(
    ...     "Including descriptions of empty PPAs"
    ... ).selected = True
    >>> anon_browser.getControl("Search", index=0).click()

    >>> for ppa_row in find_tags_by_class(
    ...     anon_browser.contents, "ppa_batch_row"
    ... ):
    ...     print(extract_text(ppa_row))
    PPA for Celso Providelo
    packages to help my friends.
    3
    3
    PPA for Mark Shuttleworth
    packages to help the humanity (you know, ubuntu)
    1
    1
    PPA for No Privileges Person
    I am not allowed to say, I have no privs.
    0
    0

This checkbox value is propagated to subsequent searches:

    >>> anon_browser.getControl(
    ...     "Including descriptions of empty PPAs"
    ... ).selected
    True

No data matches the non-existent search string "bustmybuffers".

    >>> field = anon_browser.getControl("Show PPAs matching:")
    >>> field.value = "bustmybuffers"
    >>> anon_browser.getControl("Search", index=0).click()
    >>> len(find_tags_by_class(anon_browser.contents, "ppa_batch_row"))
    0

We have to update the archive caches, in order to be able to search
them properly, see doc/package-archive.rst.

    >>> login(ANONYMOUS)
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> for archive in ubuntu.getAllPPAs():
    ...     archive.updateArchiveCache()
    ...
    >>> logout()
    >>> transaction.commit()

In the three sample data PPAs, only one matches the search string "Celso".

    >>> field = anon_browser.getControl("Show PPAs matching:")
    >>> field.value = "Celso"
    >>> anon_browser.getControl("Search", index=0).click()
    >>> len(find_tags_by_class(anon_browser.contents, "ppa_batch_row"))
    1


Hand-hacked search URLs
.......................

If the search term is specified more than once by someone hand-hacking the
URL, the page copes gracefully with this by searching for all the terms
specified.

    >>> anon_browser.open(
    ...     "http://launchpad.test/ubuntu/+ppas"
    ...     "?name_filter=packages&name_filter=friends"
    ... )
    >>> [row] = find_tags_by_class(anon_browser.contents, "ppa_batch_row")
    >>> print(extract_text(row))
    PPA for Celso Providelo...


Owner's PPA pages
-----------------

Let's start by adding an extra package to Celso's archive:

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> def publishToPPA(person_name, distroseries_name, name, version):
    ...     person = getUtility(IPersonSet).getByName(person_name)
    ...     distroseries = person.archive.distribution[distroseries_name]
    ...     factory.makeSourcePackagePublishingHistory(
    ...         distroseries=distroseries,
    ...         archive=person.archive,
    ...         sourcepackagename=name,
    ...         version=version,
    ...     )
    ...

    >>> login(ANONYMOUS)
    >>> publishToPPA("cprov", "warty", "commercialpackage", "1.0-1")
    >>> logout()
    >>> transaction.commit()

And now on to the page itself. In the table rows, the PPA
'displayname' is a link to its corresponding page:

    >>> anon_browser.getLink("PPA for Celso Providelo").click()
    >>> print(anon_browser.title)
    PPA for Celso Providelo : Celso Providelo

The first portlet in the PPA index page tell users how to install the
context PPA in their systems.

    >>> install_portlet = find_portlet(
    ...     anon_browser.contents, "Adding this PPA to your system"
    ... )

    >>> print(extract_text(install_portlet))
    Adding this PPA to your system
    You can update your system with unsupported packages from this
    untrusted PPA by adding ppa:cprov/ppa to your system's Software Sources.
    (Read about installing)
    sudo add-apt-repository ppa:cprov/ppa
    sudo apt update
    Technical details about this PPA
    ...
    For questions and bugs with software in this PPA please contact
    Celso Providelo.

There is a link within this section pointing users to the 'help'
wiki, which contains more documentation about the PPA installation
procedure.

    >>> print(anon_browser.getLink("Read about installing").url)
    http://launchpad.test/+help-soyuz/ppa-sources-list.html

The PPA owner reference is a link to its profile page.

    >>> print(anon_browser.getLink("Celso Providelo").url)
    http://launchpad.test/~cprov

The installation details are presented right below the 'Technical
details about this PPA' (in a javascript-expandable area). It consists
basically of an interactive 'sources_list' widget which allows users
to select their Ubuntu series (when it's not detected automatically)
and copy-and-paste the repository URL to their systems.

    >>> tech_details = first_tag_by_class(str(install_portlet), "widget-body")

    >>> print(extract_text(tech_details))
    This PPA can be added to your system manually by copying
    the lines below and adding them to your system's software
    sources.
    Display sources.list entries for:
      Choose your Ubuntu version
      Breezy Badger Autotest (6.6.6)
      Warty (4.10)
    deb http://ppa.launchpad.test/cprov/ppa/ubuntu
      YOUR_UBUNTU_VERSION_HERE main
    deb-src http://ppa.launchpad.test/cprov/ppa/ubuntu
      YOUR_UBUNTU_VERSION_HERE main

When present PPA 'Build dependencies' and 'Signing key' will also be
presented within this section. See below.

The sample data has two packages belonging to Celso. Two table rows
will be presented to user containing:

 * SourcePackageRelease title (<source_name> - <source-version>),
 * Date Published,
 * target DistroSeries,
 * original Section

The table is sortable.

    >>> package_table = find_tag_by_id(anon_browser.contents, "packages_list")
    >>> "sortable" in package_table["class"]
    True

The source packages list is presented publicly.

    >>> def print_archive_package_rows(contents):
    ...     package_table = find_tag_by_id(
    ...         anon_browser.contents, "packages_list"
    ...     )
    ...     for ppa_row in package_table.find_all("tr"):
    ...         print(extract_text(ppa_row))
    ...

    >>> print_archive_package_rows(anon_browser.contents)
    Package             Version         Uploaded by
    cdrkit              1.0             no signer (2007-07-09)
    commercialpackage   1.0-1           no signer
    iceweasel           1.0             no signer (2007-07-09)
    pmount              0.1-1           no signer (2007-07-09)

If a ppa package has been superseded by an package in the primary
archive for the distroseries, this will be indicated with a link
to the newer version.

    # Publish a newer version of iceweasel in hoary.
    >>> login("admin@canonical.com")
    >>> from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
    >>> test_publisher = SoyuzTestPublisher()
    >>> warty = getUtility(IDistributionSet)["ubuntu"]["warty"]
    >>> test_publisher.prepareBreezyAutotest()
    >>> new_version = test_publisher.getPubSource(
    ...     distroseries=warty, version="1.1", sourcename="iceweasel"
    ... )
    >>> transaction.commit()
    >>> logout()

    >>> anon_browser.reload()
    >>> print_archive_package_rows(anon_browser.contents)
    Package             Version         Uploaded by
    cdrkit              1.0             no signer (2007-07-09)
    commercialpackage   1.0-1           no signer
    iceweasel           1.0 (Newer version available)
                                        no signer (2007-07-09)
    pmount              0.1-1           no signer (2007-07-09)

The link itself will point to the newer version in the distribution.

    >>> print(anon_browser.getLink("Newer version").url)
    http://launchpad.test/ubuntu/+source/iceweasel/1.1

A Latest updates portlet is included on the index page indicating the
latest published sources with their states.

    >>> latest_updates = find_portlet(anon_browser.contents, "Latest updates")
    >>> print(extract_text(latest_updates))
    Latest updates
    cdrkit ... ago
    Failed to build: i386
    pmount ... ago
    Successfully built
    iceweasel ... ago
    Successfully built

A statistics portlet is included on the index page.

    >>> stats = find_portlet(anon_browser.contents, "PPA statistics")
    >>> print(extract_text(stats))
    PPA statistics
    Activity
    1 update added during the past month.

If the ppa has some current activity (building or waiting builds) then this
is also included in the statistics portlet.

    >>> from lp.buildmaster.enums import BuildStatus
    >>> from lp.soyuz.interfaces.binarypackagebuild import (
    ...     IBinaryPackageBuildSet,
    ... )
    >>> login("foo.bar@canonical.com")
    >>> cprov_ppa = getUtility(IPersonSet).getByName("cprov").archive
    >>> builds = getUtility(IBinaryPackageBuildSet).getBuildsForArchive(
    ...     cprov_ppa
    ... )
    >>> builds[0].updateStatus(
    ...     BuildStatus.BUILDING, force_invalid_transition=True
    ... )
    >>> logout()

    >>> anon_browser.reload()
    >>> stats = find_portlet(anon_browser.contents, "PPA statistics")
    >>> print(extract_text(stats))
    PPA statistics
    Activity
    1 update added during the past month.
    Currently 1 package building and 0 packages waiting to build.

Current build activity is linked to the builds page with the relevant
filter.

    >>> print(anon_browser.getLink("1 package building").url)  # noqa
    http://launchpad.test/~cprov/+archive/ubuntu/ppa/+builds?build_state=building


Filtering an archive
--------------------

The default series filter is '' which means that by default the
results will include packages from any distro series. A user can
explicitly set the 'Any Series' filter and get the same result:

    >>> anon_browser.getControl(name="field.series_filter").value = [""]
    >>> anon_browser.getControl("Filter", index=0).click()
    >>> print_archive_package_rows(anon_browser.contents)
    Package             Version         Uploaded by
    cdrkit              1.0             no signer (2007-07-09)
    commercialpackage   1.0-1           no signer
    iceweasel           1.0 (Newer version available)
                                        no signer (2007-07-09)
    pmount              0.1-1           no signer (2007-07-09)

If the packages are filtered by a particular series, then the result
will contain only the corresponding packages:

    >>> anon_browser.getControl(name="field.series_filter").value = [
    ...     "breezy-autotest"
    ... ]
    >>> anon_browser.getControl("Filter", index=0).click()
    >>> print_archive_package_rows(anon_browser.contents)
    Package             Version         Uploaded by
    cdrkit              1.0             no signer (2007-07-09)


Empty PPAs
----------

An empty PPA doesn't list any packages and it also doesn't present the
'apt sources lines ' widget and the repository 'URL' since they would
link to a repository that doesn't exist yet.

    >>> anon_browser.open(
    ...     "http://launchpad.test/~no-priv/+archive/ubuntu/ppa"
    ... )
    >>> print(extract_text(find_main_content(anon_browser.contents)))
    PPA for No Privileges Person
    PPA description
    I am not allowed to say, I have no privs.
    Adding this PPA to your system
    This PPA does not contain any packages yet.
    Find more information about how to upload packages in the PPA help page.
    PPA statistics
    ...

It also contains a link to the 'PPA help page'.

    >>> print(anon_browser.getLink("PPA help page").url)
    https://help.launchpad.net/Packaging/PPA

The "sources list" widget isn't presented for empty PPAs either.

    >>> sources_list = find_tag_by_id(
    ...     anon_browser.contents, "sources-list-entries"
    ... )
    >>> print(sources_list)
    None

Users will only be able to see it for PPAs that have, at least, one
published source.

    >>> login(ANONYMOUS)
    >>> publishToPPA("no-priv", "warty", "commercialpackage", "1.0-1")
    >>> logout()

    >>> anon_browser.reload()
    >>> sources_list = find_tag_by_id(
    ...     anon_browser.contents, "sources-list-entries"
    ... )
    >>> print(extract_text(sources_list))
    deb http://ppa.launchpad.test/no-priv/ppa/ubuntu
        warty main
    deb-src http://ppa.launchpad.test/no-priv/ppa/ubuntu
        warty main

Also the repository URL, within the sources.list snippet, is an actual link.

    >>> print(
    ...     anon_browser.getLink(
    ...         "http://ppa.launchpad.test/no-priv/ppa/ubuntu"
    ...     ).url
    ... )
    http://ppa.launchpad.test/no-priv/ppa/ubuntu


Upload hint
-----------

Users who have upload permissions to the PPA can see an 'upload hint'
section in the PPA details table.

    >>> no_priv_browser = setupBrowser(
    ...     auth="Basic no-priv@canonical.com:test"
    ... )
    >>> no_priv_browser.open(
    ...     "http://launchpad.test/~no-priv/+archive/ubuntu/ppa"
    ... )

    >>> print_tag_with_id(no_priv_browser.contents, "upload-hint")
    Uploading packages to this PPA
    You can upload packages to this PPA using:
    dput ppa:no-priv/ppa &lt;source.changes&gt;
    (Read about uploading)

It also has a link pointing to its corresponding help page.

    >>> print(no_priv_browser.getLink("Read about uploading").url)
    https://help.launchpad.net/Packaging/PPA/Uploading

Anonymous access or users with no upload permission cannot see the
upload hint section.

    >>> anon_browser.open(
    ...     "http://launchpad.test/~no-priv/+archive/ubuntu/ppa"
    ... )
    >>> print(find_tag_by_id(anon_browser.contents, "upload-hint"))
    None

    >>> admin_browser.open(
    ...     "http://launchpad.test/~no-priv/+archive/ubuntu/ppa"
    ... )
    >>> print(find_tag_by_id(anon_browser.contents, "upload-hint"))
    None


PPA signing key
---------------

PPA signing keys are automatically generated and set sometime after
the PPA creation. While the signing key isn't available nothing is
presented to the users.

    >>> print(find_tag_by_id(anon_browser.contents, "signing-key"))
    None

We will set a signing key for 'No Privileges' PPA as if it got
generated by our key-generation script (see doc/archive-signing.rst
for more information).

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.registry.interfaces.gpg import IGPGKeySet

    >>> login("foo.bar@canonical.com")
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> a_key = getUtility(IGPGKeySet).getByFingerprint(
    ...     "ABCDEF0123456789ABCDDCBA0000111112345678"
    ... )
    >>> removeSecurityProxy(no_priv.archive).signing_key_fingerprint = (
    ...     a_key.fingerprint
    ... )
    >>> removeSecurityProxy(no_priv.archive).signing_key_owner = a_key.owner
    >>> logout()

Now that 'No privileges' PPA has a signing key, a text with the key
reference (fingerprint) and a pointer to the setup instructions in the
help wiki are presented in the PPA index page.

    >>> anon_browser.reload()

    >>> signing_key_section = find_tag_by_id(
    ...     anon_browser.contents, "signing-key"
    ... )

    >>> print(extract_text(signing_key_section))
    Signing key: 1024D/ABCDEF0123456789ABCDDCBA0000111112345678
                 (What is this?)
    Fingerprint: ABCDEF0123456789ABCDDCBA0000111112345678

The key fingerprint links to the actual key available in the ubuntu
keyserver.

    >>> print(
    ...     anon_browser.getLink(
    ...         "1024D/ABCDEF0123456789ABCDDCBA0000111112345678"
    ...     ).url
    ... )  # noqa
    https://keyserver.ubuntu.com/pks/lookup?fingerprint=on&op=index&search=0xABCDEF0123456789ABCDDCBA0000111112345678

Using software from a PPA can be hard for novices. We offer two
links to the same help pop-up that describes how to add a PPA and
its key to Ubuntu.

    >>> print(anon_browser.getLink("Read about installing").url)
    http://launchpad.test/+help-soyuz/ppa-sources-list.html

And further down, next to the key id, we link to that same pop-up help:

    >>> print(anon_browser.getLink("What is this?").url)
    http://launchpad.test/+help-soyuz/ppa-sources-list.html

Try the same again, but this time using the signing service.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.services.propertycache import get_property_cache
    >>> from lp.services.signing.enums import SigningKeyType
    >>> from lp.testing.gpgkeys import test_pubkey_from_email

    >>> login("foo.bar@canonical.com")
    >>> test_key = test_pubkey_from_email("test@canonical.com")
    >>> signing_key = factory.makeSigningKey(
    ...     SigningKeyType.OPENPGP,
    ...     fingerprint="A419AE861E88BC9E04B9C26FBA2B9389DFD20543",
    ...     public_key=test_key,
    ... )
    >>> removeSecurityProxy(no_priv.archive).signing_key_owner = getUtility(
    ...     ILaunchpadCelebrities
    ... ).ppa_key_guard
    >>> removeSecurityProxy(no_priv.archive).signing_key_fingerprint = (
    ...     signing_key.fingerprint
    ... )
    >>> del get_property_cache(no_priv.archive).signing_key
    >>> del get_property_cache(no_priv.archive).signing_key_display_name
    >>> logout()

    >>> anon_browser.reload()

    >>> signing_key_section = find_tag_by_id(
    ...     anon_browser.contents, "signing-key"
    ... )

    >>> print(extract_text(signing_key_section))
    Signing key: 1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543
                 (What is this?)
    Fingerprint: A419AE861E88BC9E04B9C26FBA2B9389DFD20543

    >>> print(
    ...     anon_browser.getLink(
    ...         "1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543"
    ...     ).url
    ... )  # noqa
    https://keyserver.ubuntu.com/pks/lookup?fingerprint=on&op=index&search=0xA419AE861E88BC9E04B9C26FBA2B9389DFD20543


Single-publication PPAs
-----------------------

Just quickly check if the singular form of this section is handled
properly.

    >>> anon_browser.open("http://launchpad.test/~mark/+archive/ubuntu/ppa")
    >>> print(anon_browser.title)
    PPA for Mark Shuttleworth : Mark Shuttleworth

Mark has sources only published in one archive, so he has no
series-widget-div control to update them:

    >>> print(find_tag_by_id(anon_browser.contents, "series-widget-div"))
    None

And the sources.list entries point to the right distribution release:

    >>> results = find_tag_by_id(
    ...     anon_browser.contents, "sources-list-entries"
    ... )
    >>> text = extract_text(results)
    >>> print(text)
    deb http://ppa.launchpad.test/mark/ppa/ubuntu breezy-autotest main
    deb-src http://ppa.launchpad.test/mark/ppa/ubuntu breezy-autotest main


Populating 'Most Active' section
--------------------------------

Since the sampledata publications are not recent enough to appear in
the 'Most active' section we will create some of them on-the-fly so we
can check how it looks.

    >>> login(ANONYMOUS)
    >>> publishToPPA("cprov", "warty", "commercialpackage", "1.0-1")
    >>> publishToPPA("cprov", "hoary", "commercialpackage", "1.0-1")
    >>> publishToPPA("cprov", "warty", "cdrkit", "1.0")

    >>> publishToPPA("mark", "warty", "commercialpackage", "1.0-1")
    >>> publishToPPA("mark", "breezy-autotest", "commercialpackage", "1.0-1")

    >>> logout()
    >>> transaction.commit()

Publications created, now when any user access the 'Ubuntu PPAs' page,
they will be able to see 4 PPAs where we've added publications listed in
the 'Most active' section.

    >>> anon_browser.open("http://launchpad.test/ubuntu/+ppas")
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(anon_browser.contents, "ppa_most_active")
    ...     )
    ... )
    Most active
    PPAs with the highest number of uploads in the last 7 days.
    PPA for Celso Providelo       4 uploads
    PPA for Mark Shuttleworth     2 uploads
    PPA for No Privileges Person  1 uploads

The user can also in any PPA title listed in that section to visit the
PPA itself.

    >>> anon_browser.getLink("PPA for Celso Providelo").click()
    >>> print(anon_browser.title)
    PPA for Celso Providelo : Celso Providelo


Compatibility URL Redirection
-----------------------------

PPAs are being enhanced to allow multiple named PPAs per owner.  For a
limited transitional period, specifying a URL without the name in it
will redirect to the correct URL with the default PPA name, "ppa".

    >>> admin_browser.open("http://launchpad.test/~cprov/+archive")
    >>> admin_browser.url
    'http://launchpad.test/~cprov/+archive/ubuntu/ppa'

If the user in question doesn't have a PPA, any attempt to access it,
either via the new-style URL or the compatibility redirection, will
result in a NotFound error.

    >>> admin_browser.open("http://launchpad.test/~name16/+archive/ppa")
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound:
    Object: <Person name16 (Foo Bar)>, name: '+archive'

    >>> admin_browser.open("http://launchpad.test/~name16/+archive")
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound:
    Object: <Person name16 (Foo Bar)>, name: '+archive'
