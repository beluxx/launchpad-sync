# Copyright 2016-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snappy series."""

__metaclass__ = type

from testtools.matchers import MatchesStructure
from zope.component import (
    getAdapter,
    getUtility,
    )

from lp.app.interfaces.security import IAuthorization
from lp.services.database.interfaces import IStore
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.interfaces import OAuthPermission
from lp.snappy.interfaces.snap import SNAP_TESTING_FLAGS
from lp.snappy.interfaces.snappyseries import (
    ISnappyDistroSeriesSet,
    ISnappySeries,
    ISnappySeriesSet,
    NoSuchSnappySeries,
    )
from lp.snappy.model.snappyseries import (
    SnappyDistroSeries,
    SnappySeries,
    )
from lp.testing import (
    admin_logged_in,
    api_url,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.testing.pages import webservice_for_person


class TestSnappySeries(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestSnappySeries, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_implements_interface(self):
        # SnappySeries implements ISnappySeries.
        snappy_series = self.factory.makeSnappySeries()
        self.assertProvides(snappy_series, ISnappySeries)

    def test_set_preferred_distro_series(self):
        dses = [self.factory.makeDistroSeries() for _ in range(2)]
        snappy_series = self.factory.makeSnappySeries(
            usable_distro_series=[dses[0]])
        self.assertIsNone(snappy_series.preferred_distro_series)
        snappy_series.preferred_distro_series = dses[1]
        self.assertEqual(dses[1], snappy_series.preferred_distro_series)
        self.assertContentEqual(dses, snappy_series.usable_distro_series)
        snappy_series.preferred_distro_series = dses[0]
        self.assertEqual(dses[0], snappy_series.preferred_distro_series)
        self.assertContentEqual(dses, snappy_series.usable_distro_series)
        snappy_series.preferred_distro_series = None
        self.assertIsNone(snappy_series.preferred_distro_series)
        self.assertContentEqual(dses, snappy_series.usable_distro_series)

    def test_new_no_usable_distro_series(self):
        snappy_series = self.factory.makeSnappySeries()
        self.assertContentEqual([], snappy_series.usable_distro_series)

    def test_set_usable_distro_series(self):
        dses = [self.factory.makeDistroSeries() for _ in range(3)]
        snappy_series = self.factory.makeSnappySeries(
            usable_distro_series=[dses[0]])
        self.assertContentEqual([dses[0]], snappy_series.usable_distro_series)
        snappy_series.usable_distro_series = dses
        self.assertContentEqual(dses, snappy_series.usable_distro_series)
        snappy_series.preferred_distro_series = dses[0]
        snappy_series.usable_distro_series = []
        self.assertContentEqual([], snappy_series.usable_distro_series)
        self.assertIsNone(snappy_series.preferred_distro_series)

    def test_can_infer_distro_series(self):
        # Setting can_infer_distro_series indicates that this snappy series
        # supports inferring the distro series from snapcraft.yaml.
        snappy_series = self.factory.makeSnappySeries()
        sds_set = getUtility(ISnappyDistroSeriesSet)
        self.assertFalse(snappy_series.can_infer_distro_series)
        self.assertIsNone(sds_set.getByBothSeries(snappy_series, None))
        snappy_series.can_infer_distro_series = True
        self.assertTrue(snappy_series.can_infer_distro_series)
        self.assertIsNotNone(sds_set.getByBothSeries(snappy_series, None))
        snappy_series.can_infer_distro_series = False
        self.assertFalse(snappy_series.can_infer_distro_series)
        self.assertIsNone(sds_set.getByBothSeries(snappy_series, None))

    def test_anonymous(self):
        # Anyone can view an `ISnappySeries`.
        series = self.factory.makeSnappySeries(name="dummy")
        authz = getAdapter(series, IAuthorization, name="launchpad.View")
        self.assertTrue(authz.checkUnauthenticated())


class TestSnappySeriesSet(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestSnappySeriesSet, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_getByName(self):
        snappy_series = self.factory.makeSnappySeries(name="foo")
        self.factory.makeSnappySeries()
        snappy_series_set = getUtility(ISnappySeriesSet)
        self.assertEqual(snappy_series, snappy_series_set.getByName("foo"))
        self.assertRaises(
            NoSuchSnappySeries, snappy_series_set.getByName, "bar")

    def test_getAll(self):
        sample_snappy_serieses = list(IStore(SnappySeries).find(SnappySeries))
        snappy_serieses = [self.factory.makeSnappySeries() for _ in range(3)]
        self.assertContentEqual(
            snappy_serieses + sample_snappy_serieses,
            getUtility(ISnappySeriesSet).getAll())


class TestSnappySeriesWebservice(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnappySeriesWebservice, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_new_unpriv(self):
        # An unprivileged user cannot create a SnappySeries.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            "/+snappy-series", "new",
            name="dummy", display_name="dummy", status="Experimental")
        self.assertEqual(401, response.status)

    def test_new(self):
        # A registry expert can create a SnappySeries.
        person = self.factory.makeRegistryExpert()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_post(
            "/+snappy-series", "new",
            name="dummy", display_name="Dummy", status="Experimental")
        self.assertEqual(201, response.status)
        snappy_series = webservice.get(
            response.getHeader("Location")).jsonBody()
        with person_logged_in(person):
            self.assertEqual(
                webservice.getAbsoluteUrl(api_url(person)),
                snappy_series["registrant_link"])
            self.assertEqual("dummy", snappy_series["name"])
            self.assertEqual("Dummy", snappy_series["display_name"])
            self.assertEqual("Experimental", snappy_series["status"])

    def test_new_duplicate_name(self):
        # An attempt to create a SnappySeries with a duplicate name is
        # rejected.
        person = self.factory.makeRegistryExpert()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_post(
            "/+snappy-series", "new",
            name="dummy", display_name="Dummy", status="Experimental")
        self.assertEqual(201, response.status)
        response = webservice.named_post(
            "/+snappy-series", "new",
            name="dummy", display_name="Dummy", status="Experimental")
        self.assertEqual(400, response.status)
        self.assertEqual(
            b"name: dummy is already in use by another series.", response.body)

    def test_getByName(self):
        # lp.snappy_serieses.getByName returns a matching SnappySeries.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with admin_logged_in():
            self.factory.makeSnappySeries(name="dummy")
        response = webservice.named_get(
            "/+snappy-series", "getByName", name="dummy")
        self.assertEqual(200, response.status)
        self.assertEqual("dummy", response.jsonBody()["name"])

    def test_getByName_missing(self):
        # lp.snappy_serieses.getByName returns 404 for a non-existent
        # SnappySeries.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_get(
            "/+snappy-series", "getByName", name="nonexistent")
        self.assertEqual(404, response.status)
        self.assertEqual(
            b"No such snappy series: 'nonexistent'.", response.body)

    def test_collection(self):
        # lp.snappy_serieses is a collection of all SnappySeries.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with admin_logged_in():
            for i in range(3):
                self.factory.makeSnappySeries(name="ss-%d" % i)
        response = webservice.get("/+snappy-series")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            ["ss-0", "ss-1", "ss-2", "15.04-core", "16"],
            [entry["name"] for entry in response.jsonBody()["entries"]])


class TestSnappyDistroSeriesSet(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestSnappyDistroSeriesSet, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_getByBothSeries(self):
        dses = [self.factory.makeDistroSeries() for _ in range(2)]
        snappy_serieses = [self.factory.makeSnappySeries() for _ in range(2)]
        snappy_serieses[0].usable_distro_series = [dses[0]]
        sds_set = getUtility(ISnappyDistroSeriesSet)
        self.assertThat(
            sds_set.getByBothSeries(snappy_serieses[0], dses[0]),
            MatchesStructure.byEquality(
                snappy_series=snappy_serieses[0], distro_series=dses[0],
                title="%s, for %s" % (
                    dses[0].fullseriesname, snappy_serieses[0].title)))
        self.assertIsNone(sds_set.getByBothSeries(snappy_serieses[0], dses[1]))
        self.assertIsNone(sds_set.getByBothSeries(snappy_serieses[1], dses[0]))
        self.assertIsNone(sds_set.getByBothSeries(snappy_serieses[1], dses[1]))
        self.assertIsNone(sds_set.getByBothSeries(snappy_serieses[0], None))
        self.assertIsNone(sds_set.getByBothSeries(snappy_serieses[1], None))
        snappy_serieses[0].can_infer_distro_series = True
        self.assertThat(
            sds_set.getByBothSeries(snappy_serieses[0], None),
            MatchesStructure.byEquality(
                snappy_series=snappy_serieses[0], distro_series=None,
                title=snappy_serieses[0].title))
        self.assertIsNone(sds_set.getByBothSeries(snappy_serieses[1], None))

    def test_getAll(self):
        sdses = list(IStore(SnappyDistroSeries).find(SnappyDistroSeries))
        sds_set = getUtility(ISnappyDistroSeriesSet)
        self.assertContentEqual(sds_set.getAll(), sdses)
