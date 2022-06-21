PackageRelationshipSet Pages
============================

IPackageReleationshipSet provides a single page, '+render-list', via
SimpleView class.
This page is incorporated in parent pages with a specific relationship
group. Some example of pages using it are:

 * +builds/+build/1234/$binaryname
 * $distroseries/+source/$sourcename

Let's fill a IPackageRelationshipSet:

    >>> from lp.soyuz.browser.packagerelationship import (
    ...     PackageRelationshipSet,
    ...     )

    >>> relationship_set = PackageRelationshipSet()
    >>> relationship_set.add(
    ...    name="foobar",
    ...    operator=">=",
    ...    version="1.0.2",
    ...    url="http://whatever/")

    >>> relationship_set.add(
    ...    name="test",
    ...    operator="=",
    ...    version="1.0",
    ...    url=None)

Note that iterations over PackageRelationshipSet are sorted
alphabetically according to the relationship 'name':

    >>> for relationship in relationship_set:
    ...     print(relationship.name)
    foobar
    test

It will cause all the relationship contents to be rendered in this order.

Let's get the view class:

    >>> from zope.component import queryMultiAdapter
    >>> from zope.publisher.browser import TestRequest

    >>> request = TestRequest(form={})
    >>> pkg_rel_view = queryMultiAdapter(
    ...     (relationship_set, request), name="+render-list")

This view has no methods, so just demonstrate that it renders
correctly like:

  <ul>
     <li>
        <a href="package-one-lp-page">package-one [(operator version)]</a>
     </li>
     ...
     <li>
        package-two [(operator version)]
     </li>
  </ul>

    >>> from lp.testing.pages import parse_relationship_section

    >>> parse_relationship_section(pkg_rel_view())
    LINK: "foobar (>= 1.0.2)" -> http://whatever/
    TEXT: "test (= 1.0)"


Note that no link is rendered for IPackageReleationship where 'url' is
None.
