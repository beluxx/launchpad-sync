ILaunchpadContainer
===================

Some of our content classes may be used as the context of an OAuth
token so that any application using that token will have access only to
things in the scope of that context.  The classes that can be used as
the context of an OAuth token must have ILaunchpadContainer adapters, so
that we have an easy way of finding whether or not any given object is
within the scope of a token's context and grant or deny access to it.

    >>> from lp.services.webapp.interfaces import ILaunchpadContainer
    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.interfaces.distribution import (
    ...     IDistributionSet)
    >>> firefox = getUtility(IProductSet)['firefox']
    >>> mozilla = firefox.projectgroup
    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> evolution = ubuntu.getSourcePackage('evolution')

The ILaunchpadContainer defines only the isWithin(scope_url) method, which
returns True if this context is at the given URL or is within it.

A product is within itself or its project group.

    >>> ILaunchpadContainer(firefox).isWithin('/firefox')
    True
    >>> ILaunchpadContainer(firefox).isWithin('/mozilla')
    True
    >>> ILaunchpadContainer(firefox).isWithin('/ubuntu')
    False
    >>> verifyObject(ILaunchpadContainer, ILaunchpadContainer(firefox))
    True

A project group is only within itself.

    >>> ILaunchpadContainer(mozilla).isWithin('/mozilla')
    True
    >>> ILaunchpadContainer(mozilla).isWithin('/firefox')
    False
    >>> ILaunchpadContainer(mozilla).isWithin('/ubuntu')
    False
    >>> verifyObject(ILaunchpadContainer, ILaunchpadContainer(mozilla))
    True

A distribution is only within itself.

    >>> ILaunchpadContainer(ubuntu).isWithin('/ubuntu')
    True
    >>> ILaunchpadContainer(ubuntu).isWithin('/mozilla')
    False
    >>> ILaunchpadContainer(ubuntu).isWithin('/firefox')
    False
    >>> verifyObject(ILaunchpadContainer, ILaunchpadContainer(ubuntu))
    True

A distribution source package is within itself or its distribution.

    >>> ILaunchpadContainer(evolution).isWithin('/ubuntu/+source/evolution')
    True
    >>> ILaunchpadContainer(evolution).isWithin('/ubuntu')
    True
    >>> ILaunchpadContainer(evolution).isWithin('/firefox')
    False
    >>> ILaunchpadContainer(evolution).isWithin('/mozilla')
    False
    >>> verifyObject(ILaunchpadContainer, ILaunchpadContainer(evolution))
    True

An ILaunchpadContainer will never be within something which doesn't
provide ILaunchpadContainer as well.

    >>> ILaunchpadContainer(firefox).isWithin('/~salgado')
    False


Bugs
----

Bugs are associated to our pillars through their bug tasks, so a bug is
said to be within any of its bugtasks' targets.

    >>> from operator import attrgetter
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.services.webapp.publisher import canonical_url
    >>> bug_1 = getUtility(IBugSet).get(1)
    >>> bugtasks = bug_1.bugtasks
    >>> targets = [task.target for task in bug_1.bugtasks]
    >>> for target in sorted(targets, key=attrgetter('title')):
    ...     print('%s: %s' % (
    ...         target.title, ILaunchpadContainer(bug_1).isWithin(
    ...             canonical_url(target, force_local_path=True))))
    Mozilla Firefox: True
    mozilla-firefox package in Debian: True
    mozilla-firefox package in Ubuntu: True

But it's not within anything other than its tasks' targets.

    >>> evolution in targets
    False
    >>> ILaunchpadContainer(bug_1).isWithin('/ubuntu/+source/evolution')
    False


Branches
--------

A branch is within its target.

    >>> from lp.code.interfaces.branchnamespace import get_branch_namespace
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> sample_person = getUtility(IPersonSet).getByName('name12')
    >>> firefox_main = get_branch_namespace(
    ...     sample_person, product=firefox).getByName('main')
    >>> ILaunchpadContainer(firefox_main).isWithin('/firefox')
    True
    >>> ILaunchpadContainer(firefox_main).isWithin('/mozilla')
    True

But it's not within anything other than its target.

    >>> junk = get_branch_namespace(sample_person).getByName('junk.dev')
    >>> print(junk.product)
    None
    >>> ILaunchpadContainer(junk).isWithin('/firefox')
    False


Git repositories
----------------

A Git repository is within its target.

    >>> sample_person = getUtility(IPersonSet).getByName('name12')
    >>> firefox_git = factory.makeGitRepository(target=firefox)
    >>> ILaunchpadContainer(firefox_git).isWithin('/firefox')
    True
    >>> ILaunchpadContainer(firefox_git).isWithin('/mozilla')
    True

But it's not within anything other than its target.

    >>> ILaunchpadContainer(firefox_git).isWithin('/ubuntu/+source/evolution')
    False
