Package Relationship Model
==========================

We call "package relationship" the DSC field which describes relation
between the package in question and others available:

For sources DSC provides:

 * builddepends
 * builddependsindep
 * builddependsarch
 * build_conflicts
 * build_conflicts_indep
 * build_conflicts_arch

For binaries we have:

 * shlibdeps
 * depends
 * recommends
 * suggests
 * conflicts
 * replaces
 * provides

Those lines contain a list of comma-separated relationship where each
element follows this format:

    $NAME [($OPERATOR $VERSION)]

For example:

    >>> relationship_line = (
    ...     "gcc-3.4-base, libc6 (>= 2.3.2.ds1-4), gcc-3.4 ( = 3.4.1-4sarge1)"
    ... )

Launchpad models package relationship elements via the
IPackageRelationship instance. We use deb822 to parse the relationship
lines:

    >>> from debian.deb822 import PkgRelation

PkgRelation.parse_relations returns a 'list of lists of dicts' as:

  [ [{'name': '$NAME', 'version': ('$OPERATOR', '$VERSION')}],
    [{'name': '$NAME', 'version': ('$OPERATOR', '$VERSION')}],
    ... ]

So we need to massage its result into the form we prefer:

    >>> def parse_relations(line):
    ...     for (rel,) in PkgRelation.parse_relations(relationship_line):
    ...         if rel["version"] is None:
    ...             operator, version = "", ""
    ...         else:
    ...             operator, version = rel["version"]
    ...         yield rel["name"], version, operator
    ...
    >>> parsed_relationships = list(parse_relations(relationship_line))
    >>> parsed_relationships
    [('gcc-3.4-base', '', ''), ('libc6', '2.3.2.ds1-4', '>='),
     ('gcc-3.4', '3.4.1-4sarge1', '=')]

Now for each parsed element we can build an IPackageRelationship:

    >>> from lp.soyuz.browser.packagerelationship import PackageRelationship
    >>> from lp.soyuz.interfaces.packagerelationship import (
    ...     IPackageRelationship,
    ... )
    >>> from lp.testing import verifyObject

    >>> name, version, operator = parsed_relationships[1]
    >>> fake_url = "http://host/path"

    >>> pkg_relationship = PackageRelationship(
    ...     name, operator, version, url=fake_url
    ... )

    >>> verifyObject(IPackageRelationship, pkg_relationship)
    True

    >>> pkg_relationship.name
    'libc6'
    >>> pkg_relationship.operator
    '>='
    >>> pkg_relationship.version
    '2.3.2.ds1-4'
    >>> pkg_relationship.url == fake_url
    True
