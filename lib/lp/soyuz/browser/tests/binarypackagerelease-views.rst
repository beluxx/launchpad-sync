BinaryPackageRelease Pages
==========================

    >>> from zope.component import getMultiAdapter
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease

    >>> pmount_bin = IStore(BinaryPackageRelease).get(
    ...     BinaryPackageRelease, 15
    ... )
    >>> print(pmount_bin.name)
    pmount
    >>> print(pmount_bin.version)
    0.1-1

Get a "mock" request:
    >>> mock_form = {}
    >>> request = LaunchpadTestRequest(form=mock_form)

Let's instantiate the view for +portlet-details:

    >>> pmount_view = getMultiAdapter(
    ...     (pmount_bin, request), name="+portlet-details"
    ... )

Main functionality of this class is to provide abstracted model of the
stored package relationships. They are provided as a
IPackageRelationshipSet. (see package-relationship.rst).


    >>> pmount_deps = pmount_view.depends()

    >>> from lp.soyuz.interfaces.packagerelationship import (
    ...     IPackageRelationshipSet,
    ... )
    >>> from lp.testing import verifyObject

    >>> verifyObject(IPackageRelationshipSet, pmount_deps)
    True

Let's check the rendering parameters for a specific dep:

Note that the 'url' attribute points to the
IDistroArchSeriesBinaryPackage for 'at'.

Besides that, 'operator' can be null regarding the given relationship,
it automatically means that 'version' will be an empty string.

Another possible case is the binary package mentioned in
package relationship isn't present in the DistroArchSeries in
question. In this case 'url' will be None, which indicates no link
should be rendered for this dependency.

    >>> for dep in pmount_deps:
    ...     print(pretty((dep.name, dep.operator, dep.version, dep.url)))
    ...
    ('at', '>=', '3.14156', 'http://launchpad.test/ubuntu/hoary/i386/at')
    ('linux-2.6.12', None, '',
     'http://launchpad.test/ubuntu/hoary/i386/linux-2.6.12')
    ('tramp-package', None, '', None)

Other relationship groups use the same mechanism.
