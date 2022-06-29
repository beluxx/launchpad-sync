# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Processor features."""

from zope.component import getUtility

from lp.buildmaster.interfaces.processor import (
    IProcessor,
    IProcessorSet,
    ProcessorNotFound,
)
from lp.buildmaster.model.processor import Processor
from lp.services.database.interfaces import IStore
from lp.testing import ExpectedException, TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import webservice_for_person


class ProcessorSetTests(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_getByName(self):
        processor_set = getUtility(IProcessorSet)
        q1 = self.factory.makeProcessor(name="q1")
        self.assertEqual(q1, processor_set.getByName("q1"))

    def test_getByName_not_found(self):
        processor_set = getUtility(IProcessorSet)
        with ExpectedException(ProcessorNotFound, "No such processor.*"):
            processor_set.getByName("q1")

    def test_getAll(self):
        processor_set = getUtility(IProcessorSet)
        # Make it easy to filter out sample data
        store = IStore(Processor)
        store.execute("UPDATE Processor SET name = 'sample_data_' || name")
        self.factory.makeProcessor(name="q1")
        self.factory.makeProcessor(name="i686")
        self.factory.makeProcessor(name="g4")
        self.assertEqual(
            ["g4", "i686", "q1"],
            sorted(
                processor.name
                for processor in processor_set.getAll()
                if not processor.name.startswith("sample_data_")
            ),
        )

    def test_new(self):
        proc = getUtility(IProcessorSet).new(
            "avr2001", "The 2001 AVR", "Fast as light."
        )
        self.assertProvides(proc, IProcessor)


class ProcessorSetWebServiceTests(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_getByName(self):
        self.factory.makeProcessor(name="transmeta")

        webservice = webservice_for_person(None)
        processor = webservice.named_get(
            "/+processors", "getByName", name="transmeta", api_version="devel"
        ).jsonBody()
        self.assertEqual("transmeta", processor["name"])

    def test_default_collection(self):
        # Make it easy to filter out sample data
        store = IStore(Processor)
        store.execute("UPDATE Processor SET name = 'sample_data_' || name")
        self.factory.makeProcessor(name="q1")
        self.factory.makeProcessor(name="i686")
        self.factory.makeProcessor(name="g4")

        webservice = webservice_for_person(None)
        collection = webservice.get(
            "/+processors?ws.size=10", api_version="devel"
        ).jsonBody()
        self.assertEqual(
            ["g4", "i686", "q1"],
            sorted(
                processor["name"]
                for processor in collection["entries"]
                if not processor["name"].startswith("sample_data_")
            ),
        )
