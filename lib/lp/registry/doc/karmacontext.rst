Karma Context
=============

Now that we track the Product/Distribution in which a given karma-giving
action was performed, we're able to find out who contributes the most to a
given product/project group/distribution.  We can have this on a
per-category (Bug Management, Translations, etc) basis or in general, across
all categories.

    >>> import operator
    >>> from zope.component import getUtility
    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.karma import IKarmaContext
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> salgado = getUtility(IPersonSet).getByName('salgado')
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

    >>> verifyObject(IKarmaContext, firefox)
    True
    >>> verifyObject(IKarmaContext, ubuntu)
    True
    >>> verifyObject(IKarmaContext, firefox.projectgroup)
    True

    >>> for person, karmavalue in firefox.getTopContributors(limit=3):
    ...     print('%s: %d' % (person.name, karmavalue))
    name12: 66
    mark: 27
    name16: 8

    >>> from lp.registry.model.karma import KarmaCategory
    >>> bugs = KarmaCategory.byName('bugs')
    >>> top_bugmasters = firefox.getTopContributors(category=bugs, limit=2)
    >>> for person, karmavalue in top_bugmasters:
    ...     print('%s: %d' % (person.name, karmavalue))
    name12: 66
    name16: 8

    >>> specs = KarmaCategory.byName('specs')
    >>> top_speccers = firefox.getTopContributors(category=specs, limit=1)
    >>> for person, karmavalue in top_speccers:
    ...     print('%s: %d' % (person.name, karmavalue))
    mark: 27

We also have a way of retrieving the top contributors of a given
product/project group/distribution grouped by categories.

    >>> contributors = ubuntu.getTopContributorsGroupedByCategory(limit=2)
    >>> sorted_categories = sorted(contributors.keys(),
    ...                            key=operator.attrgetter('title'))
    >>> for category in sorted_categories:
    ...     people = [(person.name, karmavalue)
    ...               for person, karmavalue in contributors[category]]
    ...     print("%s: %s" % (category.title, pretty(people)))
    Bug Management: [('name16', 26), ('name12', 13)]
    Specification Tracking: [('mark', 37)]

The top contributors of a project group are the ones with the most karma in
all products of that project group.

Note that Foo Bar's karma on the mozilla project group is the sum of Foo
Bar's karma on the firefox and thunderbird products, which are both part of
the mozilla project group.

    >>> for person, karmavalue in firefox.projectgroup.getTopContributors(
    ...         limit=3):
    ...     print('%s: %d' % (person.name, karmavalue))
    name12: 66
    mark: 27
    name16: 23

    >>> for person, karmavalue in firefox.getTopContributors(limit=3):
    ...     print('%s: %d' % (person.name, karmavalue))
    name12: 66
    mark: 27
    name16: 8

    >>> thunderbird = getUtility(IProductSet).getByName('thunderbird')
    >>> thunderbird.projectgroup == firefox.projectgroup
    True
    >>> for person, karmavalue in thunderbird.getTopContributors(limit=3):
    ...     print('%s: %d' % (person.name, karmavalue))
    name16: 15

