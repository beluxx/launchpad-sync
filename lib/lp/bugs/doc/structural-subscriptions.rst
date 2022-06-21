Structural Subscriptions
------------------------

Structural subscriptions allow a user to subscribe to a launchpad
structure like a product, project, productseries, distribution,
distroseries, milestone or a combination of sourcepackagename and
distribution.

    >>> from lp.testing import person_logged_in
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet

    >>> person_set = getUtility(IPersonSet)
    >>> foobar = person_set.getByEmail('foo.bar@canonical.com')
    >>> sampleperson = person_set.getByEmail('test@canonical.com')
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")

    >>> with person_logged_in(foobar):
    ...     ff_sub = firefox.addBugSubscription(
    ...         subscriber=sampleperson, subscribed_by=foobar)
    >>> ff_sub.target
    <Product at ...>

    >>> with person_logged_in(foobar):
    ...     ubuntu_sub = ubuntu.addBugSubscription(
    ...         subscriber=sampleperson, subscribed_by=foobar)
    >>> ubuntu_sub.target
    <Distribution 'Ubuntu' (ubuntu)>

    >>> evolution = ubuntu.getSourcePackage('evolution')
    >>> with person_logged_in(foobar):
    ...     evolution_sub = evolution.addBugSubscription(
    ...         subscriber=sampleperson, subscribed_by=foobar)
    >>> evolution_sub.target
    <...DistributionSourcePackage object at ...>

    >>> sampleperson.structural_subscriptions.count()
    3


Parent subscription targets
===========================

Some subscription targets relate to other targets hierarchically. An
IDistribution, for example, can be said to be a parent of all
IDistributionSourcePackages for that distribution.

    >>> evolution_package = evolution_sub.target

A target's parent can be retrieved using the
`parent_subscription_target` property.

    >>> print(evolution_package.parent_subscription_target.displayname)
    Ubuntu
    >>> print(ubuntu.parent_subscription_target)
    None
    >>> print(firefox.parent_subscription_target.displayname)
    The Mozilla Project

    >>> ff_milestone = firefox.getMilestone('1.0')
    >>> ff_milestone.parent_subscription_target == firefox
    True
    >>> print(ff_milestone.parent_subscription_target.displayname)
    Mozilla Firefox

    >>> ff_trunk = firefox.getSeries('trunk')
    >>> ff_trunk.parent_subscription_target == firefox
    True
    >>> print(ff_trunk.parent_subscription_target.displayname)
    Mozilla Firefox

    >>> warty = ubuntu.getSeries('warty')
    >>> warty.parent_subscription_target == ubuntu
    True
    >>> print(warty.parent_subscription_target.displayname)
    Ubuntu

When notifying subscribers of bug activity, both subscribers to the
target and to the target's parent are notified.


Target type display
===================

Structural subscription targets have a `target_type_display` attribute, which
can be used to refer to them in display.

    >>> print(firefox.target_type_display)
    project
    >>> print(evolution_package.target_type_display)
    package
    >>> print(ff_milestone.target_type_display)
    milestone
