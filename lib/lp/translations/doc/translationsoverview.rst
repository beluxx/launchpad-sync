TranslationsOverview
====================

This class provides a basic overview of the Launchpad Translations component.
It includes data such as projects which have so far received the most
translations and provides an easy way to figure out which projects a certain
person has most translated for.

In order to make live updates to the KarmaCache table, we sometimes log
in here as testadmin.  In real life the updates would be performed by
cronscripts/foaf-update-karma-cache.py, but that would slow down this
test too much.

    >>> import transaction
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.karma import IKarmaCacheManager
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.model.karma import KarmaCategory
    >>> from lp.registry.model.sourcepackagename import SourcePackageName
    >>> from lp.translations.interfaces.translationsoverview import (
    ...     ITranslationsOverview)
    >>> from lp.testing.dbuser import switch_dbuser

    >>> karmacachemanager = getUtility(IKarmaCacheManager)
    >>> person_set = getUtility(IPersonSet)
    >>> product_set = getUtility(IProductSet)

    >>> overview = getUtility(ITranslationsOverview)

    >>> def start_karma_update():
    ...     """Prepare for update to karma cache."""
    ...     switch_dbuser('testadmin')

    >>> def finish_karma_update():
    ...     """Return to normal after updating karma cache."""
    ...     switch_dbuser('launchpad')

ITranslationOverview defines two constants regulating minimum and maximum
contribution weights.

    >>> overview.MINIMUM_SIZE
    10
    >>> overview.MAXIMUM_SIZE
    18


_normalizeSizes
---------------

This private method accepts a list of tuples (object, size) and
normalizes `size` values into the range [MINIMUM_SIZE, MAXIMUM_SIZE].

    >>> test_list = [('one', 3), ('two', 0), ('three', 1)]
    >>> from zope.security.proxy import removeSecurityProxy
    >>> naked_overview = removeSecurityProxy(overview)
    >>> result = naked_overview._normalizeSizes(test_list, 0, 3)
    >>> for pillar in result:
    ...     print("%s: %d" % (pillar['pillar'], pillar['weight']))
    one: 18
    two: 10
    three: 13


Getting the most translated pillars
-----------------------------------

Set Up
......

The following demo assumes the test data has official_translations set.
Let's set that up.

    >>> from lp.app.enums import ServiceUsage
    >>> evolution = getUtility(IProductSet).getByName('evolution')
    >>> evolution.translations_usage = ServiceUsage.LAUNCHPAD
    >>> alsa = getUtility(IProductSet).getByName('alsa-utils')
    >>> alsa.translations_usage = ServiceUsage.LAUNCHPAD
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    >>> ubuntu.translations_usage = ServiceUsage.LAUNCHPAD
    >>> transaction.commit()

Using getMostTranslatedPillars
..............................

Method getMostTranslatedPillars() returns a list of dicts listing
pillars with most translations karma so far, along with a relative
weight for each of the pillars in the range of [overview.MINIMUM_SIZE,
overview.MAXIMUM_SIZE].

    >>> def display_pillars(pillars):
    ...     for pillar in pillars:
    ...         print("%s: %d" % (
    ...             pillar['pillar'].displayname, pillar['weight']))
    >>> display_pillars(overview.getMostTranslatedPillars())
    Evolution: 14

Adding some translations karma attributed to Carlos will make
alsa-utils displayed among the top translated pillars as well.

    >>> carlos = person_set.getByName('carlos')
    >>> translations = KarmaCategory.byName('translations')
    >>> alsa_utils = product_set.getByName('alsa-utils')

    >>> start_karma_update()
    >>> cache_entry = karmacachemanager.new(
    ...     120, carlos.id, translations.id, product_id=alsa_utils.id)
    >>> finish_karma_update()

    >>> display_pillars(overview.getMostTranslatedPillars())
    alsa-utils: 10
    Evolution: 18

When karma is increased for alsa-utils, it will get more weight than
Evolution.

    >>> start_karma_update()
    >>> cache_entry = karmacachemanager.updateKarmaValue(
    ...     1020, carlos.id, translations.id, product_id=alsa_utils.id)
    >>> finish_karma_update()

    >>> display_pillars(overview.getMostTranslatedPillars())
    alsa-utils: 18
    Evolution: 10

Adding a little bit of karma to upstart will put it in the list as well.

    >>> from lp.app.enums import ServiceUsage

    >>> start_karma_update()
    >>> upstart = product_set.getByName('upstart')
    >>> upstart_id = upstart.id
    >>> naked_upstart = removeSecurityProxy(upstart)
    >>> naked_upstart.translations_usage = ServiceUsage.LAUNCHPAD
    >>> cache_entry = karmacachemanager.new(
    ...     50, carlos.id, translations.id, product_id=upstart_id)
    >>> finish_karma_update()

    >>> display_pillars(overview.getMostTranslatedPillars())
    alsa-utils: 18
    Evolution: 13
    Upstart: 10

Distributions with a lot of translation contributions show in the same
list as well.

    >>> start_karma_update()
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> evolution_sourcepackagename = SourcePackageName.byName("evolution")
    >>> cache_entry = karmacachemanager.new(
    ...     5150, carlos.id, translations.id, distribution_id=ubuntu.id,
    ...     sourcepackagename_id=evolution_sourcepackagename.id)
    >>> finish_karma_update()
    >>> display_pillars(overview.getMostTranslatedPillars())
    alsa-utils: 15
    Evolution: 12
    Ubuntu: 18
    Upstart: 10

Changing the range of the contribution weights relative project weights will
automatically adjust as well.

    >>> removeSecurityProxy(overview).MINIMUM_SIZE = 20
    >>> removeSecurityProxy(overview).MAXIMUM_SIZE = 24
    >>> display_pillars(overview.getMostTranslatedPillars())
    alsa-utils: 23
    Evolution: 21
    Ubuntu: 24
    Upstart: 20

If we pass the `limit` parameter to getMostTranslatedPillars method,
we change the default maximum number of returned entries.

    >>> display_pillars(overview.getMostTranslatedPillars(3))
    alsa-utils: 22
    Evolution: 20
    Ubuntu: 24

Private projects are never included.

    >>> from lp.app.enums import InformationType
    >>> upstart.translations_usage = ServiceUsage.NOT_APPLICABLE
    >>> upstart.information_type = InformationType.PROPRIETARY
    >>> display_pillars(overview.getMostTranslatedPillars())
    alsa-utils: 22
    Evolution: 20
    Ubuntu: 24


Zero karma
----------

Sometimes a pillar appears to be listed in the karma cache with zero
karma.  Our algorithm takes the logarithm of its karma, but it's
properly armoured against the occurrence of karmaless projects.

    >>> start_karma_update()
    >>> from lp.services.database.sqlbase import cursor
    >>> cur = cursor()
    >>> cur.execute("""
    ...     UPDATE KarmaCache
    ...     SET karmavalue = 0
    ...     WHERE product = %d
    ...     """ % upstart_id)
    >>> cur.rowcount
    1
    >>> finish_karma_update()

    >>> display_pillars(overview.getMostTranslatedPillars())
    alsa-utils: ...
    Evolution: ...
    Ubuntu: ...

