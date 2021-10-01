# Copyright 2011-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.bugs.interfaces.bugtaskfilter."""

from testtools.matchers import Equals

from lp.bugs.interfaces.bugtaskfilter import filter_bugtasks_by_context
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount


class TestFilterBugTasksByContext(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_simple_case(self):
        bug = self.factory.makeBug()
        tasks = list(bug.bugtasks)
        self.assertThat(filter_bugtasks_by_context(None, tasks), Equals(tasks))

    def test_multiple_bugs(self):
        bug1 = self.factory.makeBug()
        bug2 = self.factory.makeBug()
        bug3 = self.factory.makeBug()
        tasks = list(bug1.bugtasks)
        tasks.extend(bug2.bugtasks)
        tasks.extend(bug3.bugtasks)
        with StormStatementRecorder() as recorder:
            filtered = filter_bugtasks_by_context(None, tasks)
        self.assertThat(recorder, HasQueryCount(Equals(0)))
        self.assertThat(len(filtered), Equals(3))
        self.assertThat(filtered, Equals(tasks))

    def assertFilterBugtasksByContextNoQueries(self, bug, target, task):
        tasks = list(bug.bugtasks)
        with StormStatementRecorder() as recorder:
            filtered = filter_bugtasks_by_context(target, tasks)
        self.assertThat(recorder, HasQueryCount(Equals(0)))
        self.assertThat(filtered, Equals([task]))

    def test_two_product_tasks_case_no_context(self):
        widget = self.factory.makeProduct()
        bug = self.factory.makeBug(target=widget)
        cogs = self.factory.makeProduct()
        self.factory.makeBugTask(bug=bug, target=cogs)
        self.assertFilterBugtasksByContextNoQueries(
            bug, None, bug.getBugTask(widget))

    def test_two_product_tasks_case(self):
        widget = self.factory.makeProduct()
        bug = self.factory.makeBug(target=widget)
        cogs = self.factory.makeProduct()
        task = self.factory.makeBugTask(bug=bug, target=cogs)
        self.assertFilterBugtasksByContextNoQueries(bug, cogs, task)

    def test_product_context_with_series_task(self):
        bug = self.factory.makeBug()
        widget = self.factory.makeProduct()
        task = self.factory.makeBugTask(bug=bug, target=widget)
        self.factory.makeBugTask(bug=bug, target=widget.development_focus)
        self.assertFilterBugtasksByContextNoQueries(bug, widget, task)

    def test_productseries_context_with_series_task(self):
        bug = self.factory.makeBug()
        widget = self.factory.makeProduct()
        self.factory.makeBugTask(bug=bug, target=widget)
        series = widget.development_focus
        task = self.factory.makeBugTask(bug=bug, target=series)
        self.assertFilterBugtasksByContextNoQueries(bug, series, task)

    def test_productseries_context_with_only_product_task(self):
        bug = self.factory.makeBug()
        widget = self.factory.makeProduct()
        task = self.factory.makeBugTask(bug=bug, target=widget)
        series = widget.development_focus
        self.assertFilterBugtasksByContextNoQueries(bug, series, task)

    def test_distro_context(self):
        bug = self.factory.makeBug()
        mint = self.factory.makeDistribution()
        task = self.factory.makeBugTask(bug=bug, target=mint)
        self.assertFilterBugtasksByContextNoQueries(bug, mint, task)

    def test_distro_context_with_series_task(self):
        bug = self.factory.makeBug()
        mint = self.factory.makeDistribution()
        task = self.factory.makeBugTask(bug=bug, target=mint)
        devel = self.factory.makeDistroSeries(mint)
        self.factory.makeBugTask(bug=bug, target=devel)
        self.assertFilterBugtasksByContextNoQueries(bug, mint, task)

    def test_distroseries_context_with_series_task(self):
        bug = self.factory.makeBug()
        mint = self.factory.makeDistribution()
        self.factory.makeBugTask(bug=bug, target=mint)
        devel = self.factory.makeDistroSeries(mint)
        task = self.factory.makeBugTask(bug=bug, target=devel)
        self.assertFilterBugtasksByContextNoQueries(bug, devel, task)

    def test_distroseries_context_with_no_series_task(self):
        bug = self.factory.makeBug()
        mint = self.factory.makeDistribution()
        task = self.factory.makeBugTask(bug=bug, target=mint)
        devel = self.factory.makeDistroSeries(mint)
        self.assertFilterBugtasksByContextNoQueries(bug, devel, task)

    def test_sourcepackage_context_with_sourcepackage_task(self):
        bug = self.factory.makeBug()
        sp = self.factory.makeSourcePackage()
        task = self.factory.makeBugTask(bug=bug, target=sp)
        self.assertFilterBugtasksByContextNoQueries(bug, sp, task)

    def test_sourcepackage_context_with_distrosourcepackage_task(self):
        bug = self.factory.makeBug()
        sp = self.factory.makeSourcePackage()
        dsp = sp.distribution_sourcepackage
        task = self.factory.makeBugTask(bug=bug, target=dsp)
        self.assertFilterBugtasksByContextNoQueries(bug, sp, task)

    def test_sourcepackage_context_series_task(self):
        bug = self.factory.makeBug()
        sp = self.factory.makeSourcePackage()
        task = self.factory.makeBugTask(bug=bug, target=sp.distroseries)
        self.assertFilterBugtasksByContextNoQueries(bug, sp, task)

    def test_sourcepackage_context_distro_task(self):
        bug = self.factory.makeBug()
        sp = self.factory.makeSourcePackage()
        task = self.factory.makeBugTask(bug=bug, target=sp.distribution)
        self.assertFilterBugtasksByContextNoQueries(bug, sp, task)

    def test_sourcepackage_context_distro_task_with_other_distro_package(self):
        bug = self.factory.makeBug()
        sp = self.factory.makeSourcePackage()
        task = self.factory.makeBugTask(bug=bug, target=sp.distribution)
        other_sp = self.factory.makeSourcePackage(
            sourcepackagename=sp.sourcepackagename)
        self.factory.makeBugTask(bug=bug, target=other_sp)
        self.assertFilterBugtasksByContextNoQueries(bug, sp, task)
