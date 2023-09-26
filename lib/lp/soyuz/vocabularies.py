# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the GNU
# Affero General Public License version 3 (see the file LICENSE).

"""Soyuz vocabularies."""

__all__ = [
    "ComponentVocabulary",
    "FilteredDistroArchSeriesVocabulary",
    "make_archive_vocabulary",
    "PackageReleaseVocabulary",
    "PPAVocabulary",
]

from storm.expr import Is
from storm.locals import And, Or
from zope.component import getUtility
from zope.interface import implementer
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from zope.security.interfaces import Unauthorized

from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.person import Person
from lp.services.database.interfaces import IStore
from lp.services.database.stormexpr import fti_search
from lp.services.webapp.interfaces import ILaunchBag
from lp.services.webapp.vocabulary import IHugeVocabulary, StormVocabularyBase
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.model.archive import Archive, get_enabled_archive_filter
from lp.soyuz.model.component import Component
from lp.soyuz.model.distroarchseries import DistroArchSeries
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


class ComponentVocabulary(StormVocabularyBase):
    _table = Component
    _order_by = "name"

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.name)


class FilteredDistroArchSeriesVocabulary(StormVocabularyBase):
    """All arch series of a particular distribution."""

    _table = DistroArchSeries
    _order_by = [
        "DistroSeries.version",
        DistroArchSeries.architecturetag,
        DistroArchSeries.id,
    ]

    def toTerm(self, obj):
        name = "%s %s (%s)" % (
            obj.distroseries.distribution.name,
            obj.distroseries.name,
            obj.architecturetag,
        )
        return SimpleTerm(obj, obj.id, name)

    def __iter__(self):
        distribution = getUtility(ILaunchBag).distribution
        if distribution:
            results = (
                IStore(DistroSeries)
                .find(
                    self._table,
                    DistroSeries.id == DistroArchSeries.distroseries_id,
                    DistroSeries.distribution == distribution,
                )
                .order_by(*self._orderBy)
            )
            for distroarchseries in results:
                yield self.toTerm(distroarchseries)


class PackageReleaseVocabulary(StormVocabularyBase):
    _table = SourcePackageRelease
    _order_by = "id"

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.name + " " + obj.version)


@implementer(IHugeVocabulary)
class PPAVocabulary(StormVocabularyBase):
    _table = Archive
    _order_by = ["Person.name", "Archive.name"]
    # This should probably also filter by privacy, but that becomes
    # problematic when you need to remove a dependency that you can no
    # longer see.
    _clauses = [
        Is(Archive._enabled, True),
        Archive.owner == Person.id,
        Archive.purpose == ArchivePurpose.PPA,
    ]
    displayname = "Select a PPA"
    step_title = "Search"

    def toTerm(self, archive):
        """See `IVocabulary`."""
        summary = "No description available"
        try:
            if archive.description:
                summary = archive.description.splitlines()[0]
        except Unauthorized:
            pass
        return SimpleTerm(archive, archive.reference, summary)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        obj = getUtility(IArchiveSet).getByReference(token)
        if obj is None or not obj.enabled or not obj.is_ppa:
            raise LookupError(token)
        return self.toTerm(obj)

    def search(self, query, vocab_filter=None):
        """Return a resultset of archives.

        This is a helper required by `StormVocabularyBase.searchForTerms`.
        """
        if not query:
            return self.emptySelectResults()

        query = query.lower()

        if query.startswith("~"):
            query = query.strip("~")
        if query.startswith("ppa:"):
            query = query[4:]
        try:
            query_split = query.split("/")
            if len(query_split) == 3:
                owner_name, distro_name, archive_name = query_split
            else:
                owner_name, archive_name = query_split
        except ValueError:
            search_clause = Or(
                fti_search(Archive, query), fti_search(Person, query)
            )
        else:
            search_clause = And(
                Person.name == owner_name, Archive.name == archive_name
            )

        extra_clauses = [
            get_enabled_archive_filter(
                getUtility(ILaunchBag).user,
                purpose=ArchivePurpose.PPA,
                include_public=True,
            ),
            search_clause,
        ]
        return (
            IStore(self._table)
            .find(self._table, *self._clauses, *extra_clauses)
            .order_by(self._order_by)
        )


def make_archive_vocabulary(archives):
    terms = []
    for archive in archives:
        label = "%s [%s]" % (archive.displayname, archive.reference)
        terms.append(SimpleTerm(archive, archive.reference, label))
    terms.sort(key=lambda x: x.value.reference)
    return SimpleVocabulary(terms)
