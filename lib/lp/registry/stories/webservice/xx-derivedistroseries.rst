Derive Distributions
--------------------

DistroSeries.initDerivedDistroSeries() allows us to derive one distroseries
from others.


Set Up
======

    >>> from lp.registry.interfaces.person import TeamMembershipPolicy
    >>> from lp.testing.sampledata import ADMIN_EMAIL
    >>> from lp.testing.pages import webservice_for_person
    >>> from lp.services.webapp.interfaces import OAuthPermission
    >>> from zope.security.proxy import removeSecurityProxy

    >>> login(ADMIN_EMAIL)

    >>> soyuz_team = factory.makeTeam(
    ...     name="soyuz-team",
    ...     membership_policy=TeamMembershipPolicy.RESTRICTED,
    ... )
    >>> soyuz_team_owner = soyuz_team.teamowner
    >>> parent_series = factory.makeDistroSeries(name="parentseries")
    >>> arch = factory.makeDistroArchSeries(distroseries=parent_series)
    >>> removeSecurityProxy(parent_series).nominatedarchindep = arch
    >>> child_series = factory.makeDistroSeries(name="child1")
    >>> child_series_with_parent = factory.makeDistroSeries(
    ...     name="child-with-parent"
    ... )
    >>> child_series.driver = soyuz_team
    >>> child_series_with_parent.driver = soyuz_team
    >>> parent_series.driver = soyuz_team
    >>> dsp = factory.makeDistroSeriesParent(
    ...     derived_series=child_series_with_parent,
    ...     parent_series=parent_series,
    ... )
    >>> other_series = factory.makeDistroSeries(name="otherseries")
    >>> other_series.driver = soyuz_team

    >>> distribution = factory.makeDistribution(
    ...     name="deribuntu", owner=soyuz_team
    ... )
    >>> version = "%s.0" % factory.getUniqueInteger()

    >>> logout()

    >>> soyuz_team_webservice = webservice_for_person(
    ...     soyuz_team_owner, permission=OAuthPermission.WRITE_PUBLIC
    ... )


Calling
=======

    >>> from lp.services.webapp import canonical_url
    >>> from lp.services.webapp.servers import WebServiceTestRequest

    >>> def ws_object(webservice, obj):
    ...     api_request = WebServiceTestRequest(
    ...         SERVER_URL=webservice.getAbsoluteUrl("")
    ...     )
    ...     login(ANONYMOUS)
    ...     obj_url = canonical_url(obj, request=api_request)
    ...     logout()
    ...     return webservice.get(obj_url).jsonBody()
    ...

We can't call .initDerivedDistroSeries() on a distroseries that already
has a parent series.

    >>> ws_child_series_with_parent = ws_object(
    ...     soyuz_team_webservice, child_series_with_parent
    ... )

    >>> print(
    ...     soyuz_team_webservice.named_post(
    ...         ws_child_series_with_parent["self_link"],
    ...         "initDerivedDistroSeries",
    ...         parents=[str(other_series.id)],
    ...         rebuild=False,
    ...     )
    ... )
    HTTP/1.1 400 Bad Request
    ...
    DistroSeries ... already has parent series.

If we call it correctly, it works.

    >>> ws_child_series = ws_object(soyuz_team_webservice, child_series)

    >>> print(
    ...     soyuz_team_webservice.named_post(
    ...         ws_child_series["self_link"],
    ...         "initDerivedDistroSeries",
    ...         parents=[str(parent_series.id)],
    ...         rebuild=False,
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...

And we can verify that the job has been created.

    >>> from zope.component import getUtility
    >>> from lp.soyuz.interfaces.distributionjob import (
    ...     IInitializeDistroSeriesJobSource,
    ... )
    >>> login(ADMIN_EMAIL)
    >>> jobs = sorted(
    ...     getUtility(IInitializeDistroSeriesJobSource).iterReady(),
    ...     key=lambda x: x.distroseries.name,
    ... )
    >>> for job in jobs:
    ...     print(job.distroseries.name)
    ...
    child1
