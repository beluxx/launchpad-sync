Distribution Arch Series
========================

We can get a distroarchseries object via a distroseries object custom
operation:

    >>> distros = webservice.get("/distros").jsonBody()
    >>> ubuntu = distros['entries'][0]
    >>> print(ubuntu['self_link'])
    http://.../ubuntu

    >>> current_series = webservice.get(
    ...     ubuntu['current_series_link']).jsonBody()
    >>> print(current_series['self_link'])
    http://.../ubuntu/hoary

We'll first set up a buildd chroot, so we can check that its URL is
exposed.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet

    >>> login('foo.bar@canonical.com')
    >>> hoary = getUtility(IDistributionSet)['ubuntu'].getSeries('hoary')
    >>> chroot = factory.makeLibraryFileAlias()
    >>> unused = hoary.getDistroArchSeries('i386').addOrUpdateChroot(chroot)
    >>> logout()

    >>> distroarchseries = webservice.named_get(
    ...     current_series['self_link'], 'getDistroArchSeries',
    ...     archtag='i386').jsonBody()

For a distroarchseries we publish a subset of its attributes.

    >>> from lazr.restful.testing.webservice import pprint_entry
    >>> pprint_entry(distroarchseries)
    architecture_tag: 'i386'
    chroot_url: 'http://.../.../filename...'
    display_name: 'Ubuntu Hoary i386'
    distroseries_link: 'http://.../ubuntu/hoary'
    is_nominated_arch_indep: True
    main_archive_link: 'http://.../ubuntu/+archive/primary'
    official: True
    owner_link: 'http://.../~mark'
    package_count: 1
    processor_link: 'http://.../+processors/386'
    resource_type_link: 'http://.../#distro_arch_series'
    self_link: 'http://.../ubuntu/hoary/i386'
    supports_virtualized: True
    title: 'The Hoary Hedgehog Release for i386 (386)'
    web_link: 'http://launchpad.../ubuntu/hoary/i386'

DistroArchSeries.enabled is published in the API devel version.

    >>> distroarchseries = webservice.get(
    ...     "/ubuntu/hoary/i386", api_version='devel').jsonBody()

    >>> pprint_entry(distroarchseries)
    architecture_tag: 'i386'
    chroot_url: 'http://.../.../filename...'
    display_name: 'Ubuntu Hoary i386'
    distroseries_link: 'http://.../ubuntu/hoary'
    enabled: True
    is_nominated_arch_indep: True
    main_archive_link: 'http://.../ubuntu/+archive/primary'
    official: True
    owner_link: 'http://.../~mark'
    package_count: 1
    processor_link: 'http://.../+processors/386'
    resource_type_link: 'http://.../#distro_arch_series'
    self_link: 'http://.../ubuntu/hoary/i386'
    supports_virtualized: True
    title: 'The Hoary Hedgehog Release for i386 (386)'
    web_link: 'http://launchpad.../ubuntu/hoary/i386'
