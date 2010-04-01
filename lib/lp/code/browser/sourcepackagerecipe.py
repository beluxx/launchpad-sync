# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SourcePackageRecipe views."""

__metaclass__ = type

__all__ = []


from lazr.restful.fields import Reference
from zope.app.form import CustomWidgetFactory
from zope.component import getUtility
from zope.interface import Interface
from zope.schema import Choice, List
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from canonical.widgets.itemswidgets import (
    LabeledMultiCheckBoxWidget, LaunchpadRadioWidgetWithDescription)

from canonical.launchpad.webapp import (
    action, canonical_url, ContextMenu, custom_widget, LaunchpadFormView,
    LaunchpadView, Link)
from canonical.launchpad.webapp.authorization import check_permission
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.code.interfaces.sourcepackagerecipe import ISourcePackageRecipe
from lp.soyuz.browser.archive import make_archive_vocabulary
from lp.soyuz.interfaces.archive import (
    IArchiveSet)
from lp.registry.interfaces.distroseries import (
    IDistroSeries, IDistroSeriesSet)
from lp.registry.interfaces.pocket import PackagePublishingPocket


class SourcePackageRecipeContextMenu(ContextMenu):
    """Context menu for sourcepackage recipes."""

    usedfor = ISourcePackageRecipe

    facet = 'branches'

    links = ('request_builds',)

    def request_builds(self):
        return Link('+request-builds', 'Request build(s)', icon='add')


class SourcePackageRecipeView(LaunchpadView):
    """Default view of a SourcePackageRecipe."""

    @property
    def title(self):
        return self.context.name

    label = title

    @property
    def builds(self):
        """A list of interesting builds.

        All pending builds are shown, as well as 1-5 recent builds.
        Recent builds are ordered by date completed.
        """
        builds = list(self.context.getBuilds(pending=True))
        for build in self.context.getBuilds():
            builds.append(build)
            if len(builds) >= 5:
                break
        builds.reverse()
        return builds




class SourcePackageRecipeRequestBuildsView(LaunchpadFormView):
    """A view for requesting builds of a SourcePackageRecipe."""

    @property
    def initial_values(self):
        return {'distros': self.context.distroseries}

    @property
    def schema(self):
        dsset = getUtility(IDistroSeriesSet).search()
        terms = [SimpleTerm(distro, distro.id, distro.title)
                 for distro in dsset]
        archive_vocab = make_archive_vocabulary(
            ppa
            for ppa in getUtility(IArchiveSet).getPPAsForUser(self.user)
            if check_permission('launchpad.Append', ppa))

        class schema(Interface):
            distros = List(
                Choice(vocabulary=SimpleVocabulary(terms)),
                title=u'Distribution series')
            archive = Choice(title=u'Archive', vocabulary=archive_vocab)

        return schema

    custom_widget('distros', LabeledMultiCheckBoxWidget)

    @property
    def title(self):
        return 'Request builds for %s' % self.context.name

    label = title

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url

    @action('Request builds', name='request')
    def request_action(self, action, data):
        for distroseries in data['distros']:
            self.context.requestBuild(
                data['archive'], self.user, distroseries,
                PackagePublishingPocket.RELEASE)


class SourcePackageRecipeBuildView(LaunchpadView):
    """Default view of a SourcePackageRecipeBuild."""

    @property
    def status(self):
        """A human-friendly status string."""
        if self.context.buildstate == BuildStatus.NEEDSBUILD:
            if self.eta is None:
                return 'No suitable builders'
        return self.context.buildstate.title

    @property
    def eta(self):
        """The datetime when the build job is estimated to begin."""
        if self.context.buildqueue_record is None:
            return None
        return self.context.buildqueue_record.getEstimatedJobStartTime()

    @property
    def date(self):
        """The date when the build complete or will begin."""
        if self.estimate:
            return self.eta
        return self.context.datebuilt

    @property
    def estimate(self):
        """If true, the date value is an estimate."""
        return (self.context.datebuilt is None and self.eta is not None)
