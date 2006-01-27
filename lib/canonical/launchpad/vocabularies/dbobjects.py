# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Vocabularies pulling stuff from the database.

You probably don't want to use these classes directly - see the
docstring in __init__.py for details.
"""

__metaclass__ = type

__all__ = [
    'IHugeVocabulary',
    'SQLObjectVocabularyBase',
    'NamedSQLObjectVocabulary',
    'BinaryAndSourcePackageNameVocabulary',
    'BinaryPackageNameVocabulary',
    'BountyVocabulary',
    'BugVocabulary',
    'BugTrackerVocabulary',
    'BugWatchVocabulary',
    'CountryNameVocabulary',
    'DistributionVocabulary',
    'DistroReleaseVocabulary',
    'FilteredDistroArchReleaseVocabulary',
    'FilteredDistroReleaseVocabulary',
    'FilteredProductSeriesVocabulary',
    'KarmaCategoryVocabulary',
    'LanguageVocabulary',
    'MilestoneVocabulary',
    'PackageReleaseVocabulary',
    'PersonAccountToMergeVocabulary',
    'POTemplateNameVocabulary',
    'ProcessorVocabulary',
    'ProcessorFamilyVocabulary',
    'ProductReleaseVocabulary',
    'ProductSeriesVocabulary',
    'ProductVocabulary',
    'ProjectVocabulary',
    'SchemaVocabulary',
    'SourcePackageNameVocabulary',
    'SpecificationVocabulary',
    'SpecificationDependenciesVocabulary',
    'SprintVocabulary',
    'TranslationGroupVocabulary',
    'ValidPersonOrTeamVocabulary',
    'ValidTeamMemberVocabulary',
    'ValidTeamOwnerVocabulary',
    ]

from zope.component import getUtility
from zope.interface import implements, Attribute
from zope.schema.interfaces import IVocabulary, IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm
from zope.security.proxy import isinstance as zisinstance

from sqlobject import AND, OR, CONTAINSSTRING

from canonical.lp.dbschema import EmailAddressStatus
from canonical.database.sqlbase import (
    SQLBase, quote_like, quote, sqlvalues, cursor)
from canonical.launchpad.database import (
    Distribution, DistroRelease, Person, SourcePackageRelease,
    SourcePackageName, BugWatch, Sprint, DistroArchRelease, KarmaCategory,
    BinaryPackageName, Language, Milestone, Product, Project, ProductRelease,
    ProductSeries, TranslationGroup, BugTracker, POTemplateName, Schema,
    Bounty, Country, Specification, Bug, Processor, ProcessorFamily)
from canonical.launchpad.interfaces import (
    ILaunchBag, ITeam, IPersonSet, IEmailAddressSet)

class IHugeVocabulary(IVocabulary):
    """Interface for huge vocabularies.

    Items in an IHugeVocabulary should have human readable tokens or the
    default UI will suck.
    """

    displayname = Attribute(
        'A name for this vocabulary, to be displayed in the popup window.')

    def search(query=None):
        """Return an iterable of ITokenizedTerm that match the
        search string.

        Note that what is searched and how the match is the choice of the
        IHugeVocabulary implementation.
        """


class SQLObjectVocabularyBase:
    """A base class for widgets that are rendered to collect values
    for attributes that are SQLObjects, e.g. ForeignKey.

    So if a content class behind some form looks like:

    class Foo(SQLObject):
        id = IntCol(...)
        bar = ForeignKey(...)
        ...

    Then the vocabulary for the widget that captures a value for bar
    should derive from SQLObjectVocabularyBase.
    """
    implements(IVocabulary, IVocabularyTokenized)
    _orderBy = None

    def __init__(self, context=None):
        self.context = context

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.title)

    def __iter__(self):
        params = {}
        if self._orderBy:
            params['orderBy'] = self._orderBy
        for obj in self._table.select(**params):
            yield self._toTerm(obj)

    def __len__(self):
        return len(list(iter(self)))

    def __contains__(self, obj):
        # Sometimes this method is called with an SQLBase instance, but
        # z3 form machinery sends through integer ids. This might be due
        # to a bug somewhere.
        if zisinstance(obj, SQLBase):
            found_obj = self._table.selectOne(self._table.q.id == obj.id)
            return found_obj is not None and found_obj == obj
        else:
            found_obj = self._table.selectOne(self._table.q.id == int(obj))
            return found_obj is not None

    def getQuery(self):
        return None

    def getTerm(self, value):
        # Short circuit. There is probably a design problem here since we
        # sometimes get the id and sometimes an SQLBase instance.
        if zisinstance(value, SQLBase):
            return self._toTerm(value)

        try:
            value = int(value)
        except ValueError:
            raise LookupError(value)

        try:
            obj = self._table.selectOne(self._table.q.id == value)
        except ValueError:
            raise LookupError(value)

        if obj is None:
            raise LookupError(value)

        return self._toTerm(obj)

    def getTermByToken(self, token):
        return self.getTerm(token)


class NamedSQLObjectVocabulary(SQLObjectVocabularyBase):
    """A SQLObjectVocabulary base for database tables that have a unique
    *and* ASCII name column.

    Provides all methods required by IHugeVocabulary, although it
    doesn't actually specify this interface since it may not actually
    be huge and require the custom widgets.

    May still want to override _toTerm to provide a nicer title and
    search to search on titles or descriptions.
    """
    implements(IHugeVocabulary)
    _orderBy = 'name'
    displayname = None

    def __init__(self, context=None):
        SQLObjectVocabularyBase.__init__(self, context)
        if self.displayname is None:
            self.displayname = 'Select %s' % self.__class__.__name__

    def _toTerm(self, obj):
        return SimpleTerm(obj.id, obj.name, obj.name)

    def getTermByToken(self, token):
        objs = list(self._table.selectBy(name=token))
        if not objs:
            raise LookupError(token)
        return self._toTerm(objs[0])

    def search(self, query):
        """Return terms where query is a subtring of the name"""
        if query:
            objs = self._table.select(
                CONTAINSSTRING(self._table.q.name, query),
                orderBy=self._orderBy
                )
            for o in objs:
                yield self._toTerm(o)


class BasePersonVocabulary:
    """This is a base class to be used by all different Person Vocabularies."""
    _table = Person

    def _toTerm(self, obj):
        """Return the term for this object.

        Preference is given to email-based terms, falling back on
        name-based terms when no preferred email exists for the IPerson.
        """
        if obj.preferredemail is not None:
            return SimpleTerm(obj, obj.preferredemail.email, obj.browsername)
        else:
            return SimpleTerm(obj, obj.name, obj.browsername)

    def getTermByToken(self, token):
        """Return the term for the given token.

        If the token contains an '@', treat it like an email. Otherwise,
        treat it like a name.
        """
        if "@" in token:
            # This looks like an email token, so let's do an object
            # lookup based on that.
            email = getUtility(IEmailAddressSet).getByEmail(token)
            if email is None:
                raise LookupError(token)
            return self._toTerm(email.person)
        else:
            # This doesn't look like an email, so let's simply treat
            # it like a name.
            person = getUtility(IPersonSet).getByName(token)
            if person is None:
                raise LookupError(token)
            return self._toTerm(person)


class CountryNameVocabulary(SQLObjectVocabularyBase):
    """A vocabulary for country names."""

    implements(IHugeVocabulary)
    _table = Country
    _orderBy = 'name'
    displayname = 'Select a Country'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.name)


class BinaryAndSourcePackageNameVocabulary(SQLObjectVocabularyBase):
    """A vocabulary for searching for binary and sourcepackage names.

    This is useful for, e.g., reporting a bug on a 'package' when a reporter
    often has no idea about whether they mean a 'binary package' or a 'source
    package'.

    The value returned by a widget using this vocabulary will be either an
    ISourcePackageName or an IBinaryPackageName.
    """
    implements(IHugeVocabulary)

    displayname = 'Select a Package'

    def __contains__(self, name):
        # Is this a source or binary package name?
        return (
            SourcePackageName.selectOneBy(name=name) or
            BinaryPackageName.selectOneBy(name=name))

    def __iter__(self):
        return self.search(query="")

    def getTermByToken(self, token):
        # Try to retrieve the binary package name.
        return self._toTerm(token)

    def search(self, query=None):
        """Find matching source and binary package names."""
        if query is None:
            return

        cur = cursor()

        # Search for matching binary and source package names.
        #
        # When a binary package has the same name as a source package, the
        # binary package name will be returned in the result set, and the
        # source package name will not. This allows the user to select the
        # most specific package name possible, without them having to care
        # about whether that means "source package" or "binary package".
        quoted_package_name = quote_like(query)

        cur.execute((
            "SELECT name "
            "FROM BinaryPackageName "
            "WHERE name ILIKE '%%' || %s || '%%' "
            "UNION "
            "SELECT name FROM SourcePackageName "
            "WHERE name ILIKE '%%' || %s || '%%' "
            "ORDER BY name;") % (
            quoted_package_name, quoted_package_name))

        package_name_rows = cur.fetchall()

        for package_name_row in package_name_rows:
            yield self._toTerm(package_name_row[0])

    def _toTerm(self, name):
        return SimpleTerm(name, name, name)


class BinaryPackageNameVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    _table = BinaryPackageName
    _orderBy = 'name'
    displayname = 'Select a Binary Package'


class BugVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    _table = Bug
    _orderBy = 'id'
    displayname = 'Select a Bug'


class BountyVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    _table = Bounty
    displayname = 'Select a Bounty'


class BugTrackerVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)
    # XXX: 2004/10/06 Brad Bollenbach -- may be broken, but there's
    # no test data for me to check yet. This'll be fixed by the end
    # of the week (2004/10/08) as we get Malone into usable shape.
    _table = BugTracker
    displayname = 'Select a Bug Tracker'


class LanguageVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    _table = Language
    _orderBy = 'englishname'
    displayname = 'Select a Language'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.displayname)


class KarmaCategoryVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    _table = KarmaCategory
    _orderBy = 'name'
    displayname = 'Select a Karma Category'


class ProductVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    _table = Product
    _orderBy = 'displayname'
    displayname = 'Select a Product'

    def __iter__(self):
        params = {}
        if self._orderBy:
            params['orderBy'] = self._orderBy
        for obj in self._table.select("active = 't'", **params):
            yield self._toTerm(obj)

    def __contains__(self, obj):
        # Sometimes this method is called with an SQLBase instance, but
        # z3 form machinery sends through integer ids. This might be due
        # to a bug somewhere.
        where = "active='t' AND id=%d"
        if zisinstance(obj, SQLBase):
            product = self._table.selectOne(where % obj.id)
            return product is not None and product == obj
        else:
            product = self._table.selectOne(where % int(obj))
            return product is not None

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        product = self._table.selectOneBy(name=token, active=True)
        if product is None:
            raise LookupError(token)
        return self._toTerm(product)

    def search(self, query):
        """Returns products where the product name, displayname, title,
        summary, or description contain the given query. Returns an empty list
        if query is None or an empty string.
        """
        if query:
            query = query.lower()
            like_query = "'%%' || %s || '%%'" % quote_like(query)
            fti_query = quote(query)
            sql = "active = 't' AND (name LIKE %s OR fti @@ ftq(%s))" % (
                    like_query, fti_query
                    )
            return [self._toTerm(r)
                for r in self._table.select(sql, orderBy=self._orderBy)]

        return []


class ProjectVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    _table = Project
    _orderBy = 'displayname'
    displayname = 'Select a Project'

    def __iter__(self):
        params = {}
        if self._orderBy:
            params['orderBy'] = self._orderBy
        for obj in self._table.select("active = 't'", **params):
            yield self._toTerm(obj)

    def __contains__(self, obj):
        where = "active='t' and id=%d"
        if zisinstance(obj, SQLBase):
            project = self._table.selectOne(where % obj.id)
            return project is not None and project == obj
        else:
            project = self._table.selectOne(where % int(obj))
            return project is not None

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        project = self._table.selectOneBy(name=token, active=True)
        if project is None:
            raise LookupError(token)
        return self._toTerm(project)

    def search(self, query):
        """Returns projects where the project name, displayname, title,
        summary, or description contain the given query. Returns an empty list
        if query is None or an empty string.
        """
        if query:
            query = query.lower()
            like_query = "'%%' || %s || '%%'" % quote_like(query)
            fti_query = quote(query)
            sql = "active = 't' AND (name LIKE %s OR fti @@ ftq(%s))" % (
                    like_query, fti_query
                    )
            return [self._toTerm(r) for r in self._table.select(sql)]
        return []


class TranslationGroupVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    _table = TranslationGroup
    displayname = 'Select a Translation Group'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)


class PersonAccountToMergeVocabulary(
        BasePersonVocabulary, SQLObjectVocabularyBase):
    """The set of all non-merged people with at least one email address.

    This vocabulary is a very specialized one, meant to be used only to choose
    accounts to merge. You *don't* want to use it.
    """
    implements(IHugeVocabulary)

    _orderBy = ['displayname']
    displayname = 'Select a Person to Merge'

    def __iter__(self):
        for obj in self._select():
            yield self._toTerm(obj)

    def __contains__(self, obj):
        return obj in self._select()

    def _select(self, text=""):
        return getUtility(IPersonSet).findPerson(text)

    def search(self, text):
        """Return people whose fti or email address match :text."""
        if not text:
            return []

        text = text.lower()
        return [self._toTerm(obj) for obj in self._select(text)]


class ValidPersonOrTeamVocabulary(
        BasePersonVocabulary, SQLObjectVocabularyBase):
    """The set of valid Persons/Teams in Launchpad.

    A Person is considered valid if he has a preferred email address,
    a password set and Person.merged is None. Teams have no restrictions
    at all, which means that all teams are considered valid.

    This vocabulary is registered as ValidPersonOrTeam, ValidAssignee,
    ValidMaintainer and ValidOwner, because they have exactly the same
    requisites.
    """
    implements(IHugeVocabulary)

    displayname = 'Select a Person or Team'

    # This is what subclasses must change if they want any extra filtering of
    # results.
    extra_clause = ""

    def __contains__(self, obj):
        return obj in self._doSearch()

    def __iter__(self):
        for person in self._doSearch():
            yield self._toTerm(person)

    def _doSearch(self, extra_clause=None, text=""):
        """Return the people/teams whose name or email address match the given
        text, restricting restricting the results with any given extra_clause.

        If extra_clause is None, then self.extra_clause is used.
        """
        if extra_clause is not None:
            extra_clause = " AND %s" % extra_clause
        elif self.extra_clause:
            extra_clause = " AND %s" % self.extra_clause
        else:
            extra_clause = ""

        if not text:
            query = 'Person.id = ValidPersonOrTeamCache.id' + extra_clause
            return Person.select(query, clauseTables=['ValidPersonOrTeamCache'])

        name_match_query = """
            Person.id = ValidPersonOrTeamCache.id
            AND Person.fti @@ ftq(%s)
            """ % quote(text)
        name_match_query += extra_clause
        name_matches = Person.select(
            name_match_query, clauseTables=['ValidPersonOrTeamCache'])

        email_match_query = """
            EmailAddress.person = Person.id
            AND EmailAddress.person = ValidPersonOrTeamCache.id
            AND EmailAddress.status IN %s
            AND EmailAddress.email ILIKE %s || '%%'
            """ % (sqlvalues(EmailAddressStatus.VALIDATED,
                             EmailAddressStatus.PREFERRED),
                   quote_like(text))
        email_match_query += extra_clause
        email_matches = Person.select(
            email_match_query, 
            clauseTables=['ValidPersonOrTeamCache', 'EmailAddress'])

        return name_matches.union(email_matches)

    def search(self, text):
        """Return people/teams whose fti or email address match :text."""
        if not text:
            return

        text = text.lower()
        for result in self._doSearch(text=text):
            yield self._toTerm(result)


class ValidTeamMemberVocabulary(ValidPersonOrTeamVocabulary):
    """The set of valid members of a given team.

    With the exception of all teams that have this team as a member and the
    team itself, all valid persons and teams are valid members.
    """

    def __init__(self, context):
        if not context:
            raise AssertionError('ValidTeamMemberVocabulary needs a context.')
        if ITeam.providedBy(context):
            self.team = context
        else:
            raise AssertionError(
                "ValidTeamMemberVocabulary's context must implement ITeam."
                "Got %s" % str(context))

        ValidPersonOrTeamVocabulary.__init__(self, context)
        self.extra_clause = """
            Person.id NOT IN (
                SELECT team FROM TeamParticipation 
                WHERE person = %d
                ) AND Person.id != %d
            """ % (self.team.id, self.team.id)


class ValidTeamOwnerVocabulary(ValidPersonOrTeamVocabulary):
    """The set of Persons/Teams that can be owner of a team.

    With the exception of the team itself and all teams owned by that team,
    all valid persons and teams are valid owners for the team.
    """

    def __init__(self, context):
        if not context:
            raise AssertionError('ValidTeamOwnerVocabulary needs a context.')
        if not ITeam.providedBy(context):
            raise AssertionError(
                    "ValidTeamOwnerVocabulary's context must be a team.")
        ValidPersonOrTeamVocabulary.__init__(self, context)
        self.extra_clause = """
            (person.teamowner != %d OR person.teamowner IS NULL) AND
            person.id != %d""" % (context.id, context.id)


class ProductReleaseVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    displayname = 'Select a Product Release'
    _table = ProductRelease
    # XXX carlos Perello Marin 2005-05-16:
    # Sorting by version won't give the expected results, because it's just a
    # text field.  e.g. ["1.0", "2.0", "11.0"] would be sorted as ["1.0",
    # "11.0", "2.0"].
    # See https://launchpad.ubuntu.com/malone/bugs/687
    _orderBy = [Product.q.name, ProductSeries.q.name,
                ProductRelease.q.version]
    _clauseTables = ['Product', 'ProductSeries']

    def __iter__(self):
        for obj in self._table.select(
            AND (ProductRelease.q.productseriesID == ProductSeries.q.id,
                 ProductSeries.q.productID == Product.q.id
                ),
            orderBy=self._orderBy,
            clauseTables=self._clauseTables,
            ):
            yield self._toTerm(obj)

    def _toTerm(self, obj):
        productrelease = obj
        productseries = productrelease.productseries
        product = productseries.product

        # NB: We use '/' as the seperator because '-' is valid in
        # a product.name or productseries.name
        token = '%s/%s/%s' % (
                    product.name, productseries.name, productrelease.version)
        return SimpleTerm(
            obj.id, token, '%s %s %s' % (
                product.name, productseries.name, productrelease.version))

    def getTermByToken(self, token):
        try:
            productname, productseriesname, productreleaseversion = \
                token.split('/', 2)
        except ValueError:
            raise LookupError(token)

        obj = ProductRelease.selectOne(
            AND(ProductRelease.q.productseriesID == ProductSeries.q.id,
                ProductSeries.q.productID == Product.q.id,
                Product.q.name == productname,
                ProductSeries.q.name == productseriesname,
                ProductRelease.q.version == productreleaseversion
                )
            )
        try:
            return self._toTerm(obj)
        except IndexError:
            raise LookupError(token)

    def search(self, query):
        """Return terms where query is a substring of the version or name"""
        if query:
            query = query.lower()
            objs = self._table.select(
                AND(
                    ProductSeries.q.id == ProductRelease.q.productseriesID,
                    Product.q.id == ProductSeries.q.productID,
                    OR(
                        CONTAINSSTRING(Product.q.name, query),
                        CONTAINSSTRING(ProductSeries.q.name, query),
                        CONTAINSSTRING(ProductRelease.q.version, query)
                        )
                    ),
                orderBy=self._orderBy
                )

            for o in objs:
                yield self._toTerm(o)


class ProductSeriesVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    displayname = 'Select a Product Series'
    _table = ProductSeries
    _orderBy = [Product.q.name, ProductSeries.q.name]
    _clauseTables = ['Product']

    def __iter__(self):
        for obj in self._table.select(
                ProductSeries.q.productID == Product.q.id,
                orderBy=self._orderBy,
                clauseTables=self._clauseTables,
                ):
            yield self._toTerm(obj)

    def _toTerm(self, obj):
        # NB: We use '/' as the seperator because '-' is valid in
        # a product.name or productseries.name
        token = '%s/%s' % (obj.product.name, obj.name)
        return SimpleTerm(
            obj, token, '%s %s' % (obj.product.name, obj.name))

    def getTermByToken(self, token):
        try:
            productname, productseriesname = token.split('/', 1)
        except ValueError:
            raise LookupError(token)

        result = ProductSeries.selectOne('''
                    Product.id = ProductSeries.product AND
                    Product.name = %s AND
                    ProductSeries.name = %s
                    ''' % sqlvalues(productname, productseriesname),
                    clauseTables=['Product'])
        if result is not None:
            return self._toTerm(result)
        raise LookupError(token)

    def search(self, query):
        """Return terms where query is a substring of the name"""
        if query:
            query = query.lower()
            objs = self._table.select(
                    AND(
                        Product.q.id == ProductSeries.q.productID,
                        OR(
                            CONTAINSSTRING(Product.q.name, query),
                            CONTAINSSTRING(ProductSeries.q.name, query)
                            )
                        ),
                    orderBy=self._orderBy
                    )
            for o in objs:
                yield self._toTerm(o)


class FilteredDistroReleaseVocabulary(SQLObjectVocabularyBase):
    """Describes the releases of a particular distribution."""
    _table = DistroRelease
    _orderBy = 'version'

    def _toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, '%s %s' % (obj.distribution.name, obj.name))

    def __iter__(self):
        kw = {}
        if self._orderBy:
            kw['orderBy'] = self._orderBy
        launchbag = getUtility(ILaunchBag)
        if launchbag.distribution:
            distribution = launchbag.distribution
            for distrorelease in self._table.selectBy(
                distributionID=distribution.id, **kw):
                yield self._toTerm(distrorelease)


class FilteredDistroArchReleaseVocabulary(SQLObjectVocabularyBase):
    """All arch releases of a particular distribution."""

    _table = DistroArchRelease
    _orderBy = ['DistroRelease.version', 'architecturetag', 'id']
    _clauseTables = ['DistroRelease']

    def _toTerm(self, obj):
        name = "%s %s (%s)" % (obj.distrorelease.distribution.name,
                               obj.distrorelease.name, obj.architecturetag)
        return SimpleTerm(obj, obj.id, name)

    def __iter__(self):
        distribution = getUtility(ILaunchBag).distribution
        if distribution:
            query = """
                DistroRelease.id = distrorelease AND
                DistroRelease.distribution = %s
                """ % sqlvalues(distribution.id)
            results = self._table.select(
                query, orderBy=self._orderBy, clauseTables=self._clauseTables)
            for distroarchrelease in results:
                yield self._toTerm(distroarchrelease)


class FilteredProductSeriesVocabulary(SQLObjectVocabularyBase):
    """Describes ProductSeries of a particular product."""
    _table = ProductSeries
    _orderBy = ['product', 'name']

    def _toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, '%s %s' % (obj.product.name, obj.name))

    def __iter__(self):
        launchbag = getUtility(ILaunchBag)
        if launchbag.product is not None:
            for series in launchbag.product.serieslist:
                yield self._toTerm(series)


class MilestoneVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    displayname = 'Select a Milestone'
    _table = Milestone
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.name)

    def __iter__(self):
        launchbag = getUtility(ILaunchBag)
        product = launchbag.product
        if product is not None:
            target = product

        distribution = launchbag.distribution
        if distribution is not None:
            target = distribution

        if target is not None:
            for ms in target.milestones:
                yield self._toTerm(ms)


class SpecificationVocabulary(NamedSQLObjectVocabulary):
    """List specifications for the current product or distribution in
    ILaunchBag, EXCEPT for the current spec in LaunchBag if one exists.
    """
    implements(IHugeVocabulary)

    displayname = 'Select a Specification'
    _table = Specification
    _orderBy = 'title'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.name)

    def __iter__(self):
        launchbag = getUtility(ILaunchBag)
        product = launchbag.product
        if product is not None:
            target = product

        distribution = launchbag.distribution
        if distribution is not None:
            target = distribution

        if target is not None:
            for spec in sorted(target.specifications(), key=lambda a: a.title):
                # we will not show the current specification in the
                # launchbag
                if spec == launchbag.specification:
                    continue
                # we will not show a specification that is blocked on the
                # current specification in the launchbag. this is because
                # the widget is currently used to select new dependencies,
                # and we do not want to introduce circular dependencies.
                if launchbag.specification is not None:
                    if spec in launchbag.specification.all_blocked():
                        continue
                yield SimpleTerm(spec, spec.name, spec.title)


class SpecificationDependenciesVocabulary(NamedSQLObjectVocabulary):
    """List specifications on which the current specification depends."""
    implements(IHugeVocabulary)

    displayname = 'Select a Specification'
    _table = Specification
    _orderBy = 'title'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def __iter__(self):
        launchbag = getUtility(ILaunchBag)
        curr_spec = launchbag.specification

        if curr_spec is not None:
            for spec in sorted(curr_spec.dependencies, key=lambda a: a.title):
                yield SimpleTerm(spec, spec.name, spec.title)


class SprintVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    displayname = 'Select a Sprint'
    _table = Sprint

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)


class BugWatchVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    displayname = 'Select a Bug Watch'
    _table = BugWatch

    def __iter__(self):
        bug = getUtility(ILaunchBag).bug
        if bug is None:
            raise ValueError('Unknown bug context for Watch list.')

        for watch in bug.watches:
            yield self._toTerm(watch)


class PackageReleaseVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    displayname = 'Select a Package Release'
    _table = SourcePackageRelease
    _orderBy = 'id'

    def _toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, obj.name + " " + obj.version)


class SourcePackageNameVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    displayname = 'Select a Source Package'
    _table = SourcePackageName
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.name)

    def search(self, query):
        """Returns names where the sourcepackage contains the given
        query. Returns an empty list if query is None or an empty string.

        """
        if not query:
            return []
        query = query.lower()
        t = self._table
        objs = [self._toTerm(r)
                   for r in t.select("""
                       sourcepackagename.name like '%%' || %s || '%%'
                       """ % quote_like(query))]
        return objs


class DistributionVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    displayname = 'Select a Distribution'
    _table = Distribution
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        obj = Distribution.selectOne("name=%s" % sqlvalues(token))
        if obj is None:
            raise LookupError(token)
        else:
            return self._toTerm(obj)

    def search(self, query):
        """Return terms where query is a substring of the name"""
        if query:
            query = query.lower()
            like_query = "'%%' || %s || '%%'" % quote_like(query)
            fti_query = quote(query)
            kw = {}
            if self._orderBy:
                kw['orderBy'] = self._orderBy
            objs = self._table.select("name LIKE %s" % like_query, **kw)
            return [self._toTerm(obj) for obj in objs]

        return []


class DistroReleaseVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    displayname = 'Select a Distribution Release'
    _table = DistroRelease
    _orderBy = [Distribution.q.name, DistroRelease.q.name]
    _clauseTables = ['Distribution']

    def __iter__(self):
        for obj in self._table.select(
                DistroRelease.q.distributionID == Distribution.q.id,
                orderBy=self._orderBy,
                clauseTables=self._clauseTables,
                ):
            yield self._toTerm(obj)

    def _toTerm(self, obj):
        # NB: We use '/' as the separator because '-' is valid in
        # a distribution.name
        token = '%s/%s' % (obj.distribution.name, obj.name)
        return SimpleTerm(obj.id, token, obj.title)

    def getTermByToken(self, token):
        try:
            distroname, distroreleasename = token.split('/', 1)
        except ValueError:
            raise LookupError(token)

        obj = DistroRelease.selectOne(AND(Distribution.q.name == distroname,
            DistroRelease.q.name == distroreleasename))
        if obj is None:
            raise LookupError(token)
        else:
            return self._toTerm(obj)

    def search(self, query):
        """Return terms where query is a substring of the name."""
        if query:
            query = query.lower()
            objs = self._table.select(
                    AND(
                        Distribution.q.id == DistroRelease.q.distributionID,
                        OR(
                            CONTAINSSTRING(Distribution.q.name, query),
                            CONTAINSSTRING(DistroRelease.q.name, query)
                            )
                        ),
                    orderBy=self._orderBy
                    )
            for o in objs:
                yield self._toTerm(o)


class POTemplateNameVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    displayname = 'Select a POTemplate'
    _table = POTemplateName
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.translationdomain)


class ProcessorVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    displayname = 'Select a Processor'
    _table = Processor
    _orderBy = 'name'

    def search(self, query):
        """Return terms where query is a substring of the name"""
        if query:
            query = query.lower()
            processors = self._table.select(
                CONTAINSSTRING(Processor.q.name, query),
                orderBy=self._orderBy
                )
            for processor in processors:
                yield self._toTerm(processor)


class ProcessorFamilyVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    displayname = 'Select a Processor Family'
    _table = ProcessorFamily
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)


class SchemaVocabulary(NamedSQLObjectVocabulary):
    """See NamedSQLObjectVocabulary."""
    implements(IHugeVocabulary)

    displayname = 'Select a Schema'
    _table = Schema
