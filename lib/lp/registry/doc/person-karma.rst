============
People karma
============

In Launchpad, everytime a user performs an action, we give them some karma
points. These karma points are stored in the KarmaAction table and the
assignment to a user is made in the Karma table. The method used to calculate
a users karma is time-dependent, because we want to give more karma points for
actions performed recently. This method is described in
https://launchpad.canonical.com/KarmaImplementation.

Depending on the action a given person performs in Launchpad, that person can
earn some karma points. This is useful to know how active a user is in
Launchpad.

All karma assigned to a person must be associated with a context (either a
product or a distribution), so that we know to what a user contributes to and
what users are the top contributors for a given product/distribution.

    >>> from zope.component import getUtility
    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.karma import IKarma
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet)
    >>> salgado = getUtility(IPersonSet).getByName('salgado')
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> thunderbird = getUtility(ISourcePackageNameSet)['thunderbird']

The assignKarma() method is the one to be used when assigning karma to a
person. It must trigger a KarmaAssignedEvent, notifying that karma was
assigned to a given person.

    >>> from lp.testing.karma import KarmaAssignedEventListener
    >>> karma_helper = KarmaAssignedEventListener()
    >>> karma_helper.register_listener()

    >>> dummy = salgado.assignKarma('specreviewed', product=firefox)
    Karma added: action=specreviewed, product=firefox

    >>> karma_helper.unregister_listener()

Salgado wrote the karma framework. Let's give him some karma points.

  - First, some karma by fixing a bug in firefox
    >>> salgado_firefox_karma = salgado.assignKarma(
    ...     'bugfixed', product=firefox)

  - Then some karma by adding a new spec for Ubuntu
    >>> salgado_ubuntu_karma = salgado.assignKarma(
    ...     'addspec', distribution=ubuntu)

  - And finally some karma by marking a Ubuntu thunderbird bug as a duplicate
    >>> salgado_thunderbird_karma = salgado.assignKarma(
    ...     'bugmarkedasduplicate', distribution=ubuntu,
    ...     sourcepackagename=thunderbird)

assignKarma() must return an object implementing IKarma.

    >>> verifyObject(IKarma, salgado_firefox_karma)
    True

The value that you get through IPerson.karma is a cached value that's
calculated daily. That's why it's still 0.

    >>> salgado.karma
    0

Some Person's are not awarded karma: Teams, and the Launchpad Janitor,
do not receive karma when assignKarma is called. There is no error
or message to indicate nothing happed. The method assignKarma
silently returns, so callsites do not need to know who may be awarded
karma.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> janitor = getUtility(ILaunchpadCelebrities).janitor
    >>> dummy = janitor.assignKarma('specreviewed', product=firefox)
    <BLANKLINE>

    >>> ubuntu_team = getUtility(IPersonSet).getByName('ubuntu-team')
    >>> dummy = janitor.assignKarma('specreviewed', product=firefox)
    <BLANKLINE>


Projects a person is most active on
===================================

Using our karma records we can also tell in which projects a person is most
active on, including the type of work the person does on each project. We only
show the 5 most active projects.

    >>> foobar = getUtility(IPersonSet).getByName('name16')
    >>> for contrib in foobar.getProjectsAndCategoriesContributedTo(None):
    ...     categories = sorted(cat.name for cat in contrib['categories'])
    ...     print(contrib['project'].title, pretty(categories))
    Evolution ['bugs', 'translations']
    Ubuntu ['bugs']
    gnomebaker ['bugs']
    Mozilla Thunderbird ['bugs']
    Mozilla Firefox ['bugs']


Karma Updater
=============

It would be a problem if every time we wanted to see a user's total karma we
had to calculate it, so we decided to cache this total and update it
periodically. This cache is stored in the KarmaCache/KarmaTotalCache table and
is updated by the foaf-update-karma-cache.py cronscript.

    (Let's commit the current transaction because the script will run in
    another transaction and thus it won't see the changes done on this test
    unless we commit)
    >>> import transaction
    >>> transaction.commit()

    >>> import subprocess
    >>> process = subprocess.Popen(
    ...     'cronscripts/foaf-update-karma-cache.py', shell=True,
    ...     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE, universal_newlines=True)
    >>> (out, err) = process.communicate()
    >>> print(err)
    INFO    Creating lockfile: /var/lock/launchpad-karma-update.lock
    INFO    Updating Launchpad karma caches
    INFO    Step A: Calculating individual KarmaCache entries
    INFO    Scaling bugs by a factor of 2.6667 (capped to 2.0000)
    INFO    Scaling translations by a factor of 1.0000
    INFO    Scaling specs by a factor of 1.0000
    INFO    Scaling answers by a factor of 1.0000
    INFO    Step B: Rebuilding KarmaTotalCache
    INFO    Step C: Calculating KarmaCache sums
    INFO    Finished updating Launchpad karma caches
    <BLANKLINE>
    >>> print(out)
    <BLANKLINE>
    >>> process.returncode
    0
    >>> from lp.services.config import config
    >>> config.karmacacheupdater.max_scaling
    2

    (Now we flush the caches, because 'salgado' is an object that was changed
    in another transaction)
    >>> from lp.services.database.sqlbase import flush_database_caches
    >>> flush_database_caches()

Independently of the number of "Bug Management"-related and "Specification
Tracking"-related actions performed by Salgado, the total points he gets on
each of these categories will always be the same. This is so because we use a
scaling factor to balance the total karma of each category and because at this
point, all non-expired karma we have in the database is what we assigned to
Salgado during this test.

However, when a new category is created, its karma pool is dramatically
smaller than the existing ones. This causes the scaling to generate ridiculous
results until the karma pool starts filling up. To work around this problem,
we ensure that the scaling factors never get too high. So as we saw earlier
when running the karma updater script, the scaling factor for the Bug
Management category was calculated to be 2.667, but reduced to 2 because this
was the maximum specified in config.karmacacheupdater.max_scaling.

    >>> for karma in salgado.latestKarma():
    ...     print(karma.action.title, karma.action.points)
    Specification Review     10
    Bug Marked as Fixed      10
    Registered Specification 30
    Bug Marked as Duplicate   5

    >>> for cache in salgado.karma_category_caches:
    ...     print("%s: %d" % (cache.category.title, cache.karmavalue))
    Bug Management: 30
    Specification Tracking: 40

    >>> salgado.karma
    70
