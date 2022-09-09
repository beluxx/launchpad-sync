Karma Cache
===========

To be able to get the total karma of a given person, the karma of a given
type or the karma in a given context, we use our KarmaCache table. We need
it because there are too many entries in the Karma table, making it extremely
expensive to do these calculations on the fly.

The KarmaCache table is maintained by our foaf-update-karma-cache.py script,
which runs daily. The script does that by using the IKarmaCacheManager API.

    >>> from zope.component import getUtility
    >>> from lp.testing.dbuser import switch_dbuser
    >>> from lp.registry.interfaces.karma import IKarmaCacheManager
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.model.karma import KarmaCategory
    >>> from lp.services.database.interfaces import IStore

    >>> switch_dbuser("karma")
    >>> karmacachemanager = getUtility(IKarmaCacheManager)

Creating new KarmaCache entries
-------------------------------

This is done using the new() method:

    >>> value = 199
    >>> person = getUtility(IPersonSet).getByName("salgado")
    >>> bugs = IStore(KarmaCategory).find(KarmaCategory, name="bugs").one()

    # The 'karma' dbuser doesn't have access to the Product table, so we'll
    # use firefox's id directly instead of trying to fetch the product from
    # the database.
    >>> firefox_id = 4
    >>> cache_entry = karmacachemanager.new(
    ...     value, person.id, bugs.id, product_id=firefox_id
    ... )


Updating existing entries
-------------------------

Since our script has only the person ID, category ID and context ID of
the KarmaCache entry it wants to update, we provide a method
that will find the KarmaCache with the given person/category/context IDs
and update it.

    >>> new_value = 19
    >>> karmacachemanager.updateKarmaValue(
    ...     new_value, person.id, bugs.id, product_id=firefox_id
    ... )
    >>> cache_entry.karmavalue
    19


If we try to update an unexistent KarmaCache entry, we'll get a
NotFoundError.

    >>> karmacachemanager.updateKarmaValue(
    ...     new_value, person.id, bugs.id, product_id=9999
    ... )
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...
