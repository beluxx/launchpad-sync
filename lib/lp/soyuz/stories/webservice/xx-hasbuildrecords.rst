Objects that contains build records
===================================

Build records can be looked up in different contexts, they are:

 * `Distribution`;
 * `DistroSeries`;
 * `Archive`.

The method used for looking Build up is 'getBuildRecords' and it
accepts the following optional arguments:

 * 'name': a text for matching source package names;
 * 'build_state': a specific `BuildStatus`;
 * 'pocket': a specific `PackagePublishingPocket`.

If empty, no corresponding filtering is applied.

We will create a helper function to inspect build collections in
different contexts.

    >>> def print_builds(builds):
    ...     for entry in sorted(builds['entries'],
    ...                         key=lambda entry:entry.get('title')):
    ...         print(entry['title'])


Filtering builds
----------------

Celso Providelo PPA builds can be browsed via the API.

    >>> ppa = webservice.get("/~cprov/+archive/ubuntu/ppa").jsonBody()
    >>> ppa_builds = webservice.named_get(
    ...     ppa['self_link'], 'getBuildRecords').jsonBody()

    >>> print_builds(ppa_builds)
    hppa build of mozilla-firefox 0.9 in ubuntu warty RELEASE
    i386 build of cdrkit 1.0 in ubuntu breezy-autotest RELEASE
    i386 build of iceweasel 1.0 in ubuntu warty RELEASE
    i386 build of pmount 0.1-1 in ubuntu warty RELEASE

An entry can be selected in the returned collection.

    >>> from operator import itemgetter
    >>> from lazr.restful.testing.webservice import pprint_entry
    >>> pprint_entry(
    ...     sorted(ppa_builds['entries'], key=itemgetter('title'))[0])
    arch_tag: 'hppa'
    ...
    title: 'hppa build of mozilla-firefox 0.9 in ubuntu warty RELEASE'
    ...

Builds can be filtered by their 'build_state'.

    >>> failed_builds = webservice.named_get(
    ...     ppa['self_link'], 'getBuildRecords',
    ...     build_state='Failed to build').jsonBody()

    >>> print_builds(failed_builds)
    i386 build of cdrkit 1.0 in ubuntu breezy-autotest RELEASE

Or filtered by their corresponding source package name.

    >>> named_builds = webservice.named_get(
    ...     ppa['self_link'], 'getBuildRecords',
    ...     source_name='pmount').jsonBody()

    >>> print_builds(named_builds)
    i386 build of pmount 0.1-1 in ubuntu warty RELEASE

Substring matches can be used as well.

    >>> substring_builds = webservice.named_get(
    ...     ppa['self_link'], 'getBuildRecords',
    ...     source_name='ice').jsonBody()

    >>> print_builds(substring_builds)
    i386 build of iceweasel 1.0 in ubuntu warty RELEASE

Finally, filtering by the target pocket.

    >>> updates_builds = webservice.named_get(
    ...     ppa['self_link'], 'getBuildRecords', pocket='Updates'
    ... ).jsonBody()
    >>> len(updates_builds['entries'])
    0


Distribution builds
-------------------

Distributions, like ubuntu, allow users to call browse builds.

    >>> ubuntu = webservice.get("/ubuntu").jsonBody()
    >>> ubuntu_builds = webservice.named_get(
    ...     ubuntu['self_link'], 'getBuildRecords').jsonBody()

    >>> print_builds(ubuntu_builds)
    hppa build of mozilla-firefox 0.9 in ubuntu warty RELEASE
    i386 build of cdrkit 1.0 in ubuntu breezy-autotest RELEASE
    i386 build of cdrkit 1.0 in ubuntu warty RELEASE
    i386 build of commercialpackage 1.0-1 in ubuntu breezy-autotest RELEASE
    i386 build of pmount 0.1-1 in ubuntu breezy-autotest RELEASE


DistroSeries builds
-------------------

DistroSeries, like ubuntu/hoary, allow users to call browse builds.

    >>> hoary = webservice.get("/ubuntu/hoary").jsonBody()
    >>> hoary_builds = webservice.named_get(
    ...     hoary['self_link'], 'getBuildRecords').jsonBody()

    >>> print_builds(hoary_builds)
    hppa build of pmount 0.1-1 in ubuntu hoary RELEASE
    i386 build of alsa-utils 1.0.9a-4ubuntu1 in ubuntu hoary RELEASE
    i386 build of libstdc++ b8p in ubuntu hoary RELEASE
    i386 build of mozilla-firefox 0.9 in ubuntu hoary RELEASE
    i386 build of pmount 0.1-1 in ubuntu hoary RELEASE

