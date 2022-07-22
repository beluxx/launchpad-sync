# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ["Country", "CountrySet", "Continent"]

from zope.interface import implementer

from lp.app.errors import NotFoundError
from lp.services.database.constants import DEFAULT
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import SQLBase
from lp.services.database.sqlobject import (
    ForeignKey,
    SQLRelatedJoin,
    StringCol,
)
from lp.services.worlddata.interfaces.country import (
    IContinent,
    ICountry,
    ICountrySet,
)


@implementer(ICountry)
class Country(SQLBase):
    """A country."""

    _table = "Country"

    # default to listing newest first
    _defaultOrder = "name"

    # db field names
    name = StringCol(dbName="name", unique=True, notNull=True)
    iso3166code2 = StringCol(dbName="iso3166code2", unique=True, notNull=True)
    iso3166code3 = StringCol(dbName="iso3166code3", unique=True, notNull=True)
    title = StringCol(dbName="title", notNull=False, default=DEFAULT)
    description = StringCol(dbName="description")
    continent = ForeignKey(
        dbName="continent", foreignKey="Continent", default=None
    )
    languages = SQLRelatedJoin(
        "Language",
        joinColumn="country",
        otherColumn="language",
        intermediateTable="SpokenIn",
    )


@implementer(ICountrySet)
class CountrySet:
    """A set of countries"""

    def __getitem__(self, iso3166code2):
        country = Country.selectOneBy(iso3166code2=iso3166code2)
        if country is None:
            raise NotFoundError(iso3166code2)
        return country

    def __iter__(self):
        yield from Country.select()

    def getByName(self, name):
        """See `ICountrySet`."""
        return IStore(Country).find(Country, name=name).one()

    def getByCode(self, code):
        """See `ICountrySet`."""
        return IStore(Country).find(Country, iso3166code2=code).one()

    def getCountries(self):
        """See `ICountrySet`."""
        return IStore(Country).find(Country).order_by(Country.iso3166code2)


@implementer(IContinent)
class Continent(SQLBase):
    """See IContinent."""

    _table = "Continent"
    _defaultOrder = ["name", "id"]

    name = StringCol(unique=True, notNull=True)
    code = StringCol(unique=True, notNull=True)
