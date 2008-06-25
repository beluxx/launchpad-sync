# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'get_series_branch_error',
    'ProductSeriesBugsMenu',
    'ProductSeriesDynMenu',
    'ProductSeriesEditView',
    'ProductSeriesFacets',
    'ProductSeriesFileBugRedirect',
    'ProductSeriesLinkBranchView',
    'ProductSeriesLinkBranchFromCodeView',
    'ProductSeriesNavigation',
    'ProductSeriesOverviewMenu',
    'ProductSeriesRdfView',
    'ProductSeriesReviewView',
    'ProductSeriesShortLink',
    'ProductSeriesSOP',
    'ProductSeriesSourceListView',
    'ProductSeriesSourceSetView',
    'ProductSeriesSpecificationsMenu',
    'ProductSeriesTranslationMenu',
    'ProductSeriesTranslationsExportView',
    'ProductSeriesView',
    ]

import cgi
import os.path
from zope.component import getUtility
from zope.app.form.browser import TextAreaWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import FileUpload

from canonical.launchpad import _
from canonical.launchpad.browser.branchref import BranchRef
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.launchpad import (
    DefaultShortLink, StructuralObjectPresentation)
from canonical.launchpad.browser.poexportrequest import BaseExportView
from canonical.launchpad.browser.translations import TranslationsMixin
from canonical.launchpad.helpers import browserLanguages, is_tar_filename
from canonical.launchpad.interfaces import (
    ICodeImportSet, ICountry, ILaunchpadCelebrities, IPOTemplateSet,
    IProductSeries, ISourcePackageNameSet, ITranslationImportQueue,
    ITranslationImporter, ImportStatus, NotFoundError)
from canonical.launchpad.webapp import (
    action, ApplicationMenu, canonical_url, custom_widget,
    enabled_with_permission, LaunchpadEditFormView, LaunchpadView,
    Link, Navigation, StandardLaunchpadFacets, stepto)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.dynmenu import DynMenu
from canonical.launchpad.webapp.menu import structured
from canonical.widgets.textwidgets import StrippedTextWidget


def quote(text):
    return cgi.escape(text, quote=True)


class ProductSeriesNavigation(Navigation, BugTargetTraversalMixin):

    usedfor = IProductSeries

    def breadcrumb(self):
        return 'Series ' + self.context.name

    @stepto('.bzr')
    def dotbzr(self):
        if self.context.series_branch:
            return BranchRef(self.context.series_branch)
        else:
            return None

    @stepto('+pots')
    def pots(self):
        potemplateset = getUtility(IPOTemplateSet)
        return potemplateset.getSubset(productseries=self.context)

    def traverse(self, name):
        return self.context.getRelease(name)


class ProductSeriesSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return self.context.product.displayname + ' series:'

    def getMainHeading(self):
        return self.context.name

    def listChildren(self, num):
        # XXX mpt 2006-10-04: Releases, most recent first.
        return []

    def countChildren(self):
        return 0

    def listAltChildren(self, num):
        return None

    def countAltChildren(self):
        raise NotImplementedError


class ProductSeriesFacets(StandardLaunchpadFacets):

    usedfor = IProductSeries
    enable_only = [
        'overview', 'branches', 'bugs', 'specifications', 'translations']

    def branches(self):
        # Override to go to the branches for the product.
        text = 'Code'
        summary = 'View related branches of code'
        link = canonical_url(self.context.product, rootsite='code')
        return Link(link, text, summary=summary)


class ProductSeriesOverviewMenu(ApplicationMenu):

    usedfor = IProductSeries
    facet = 'overview'
    links = [
        'edit', 'driver', 'link_branch', 'ubuntupkg',
        'add_package', 'add_milestone', 'add_release', 'rdf', 'review',
        'subscribe'
        ]

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def driver(self):
        text = 'Appoint driver'
        summary = 'Someone with permission to set goals this series'
        return Link('+driver', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def link_branch(self):
        text = 'Link to branch'
        return Link('+linkbranch', text, icon='edit')

    def ubuntupkg(self):
        text = 'Link to Ubuntu package'
        return Link('+ubuntupkg', text, icon='edit')

    def add_package(self):
        text = 'Link to other package'
        return Link('+addpackage', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def add_milestone(self):
        text = 'Add milestone'
        summary = 'Register a new milestone for this series'
        return Link('+addmilestone', text, summary, icon='add')

    @enabled_with_permission('launchpad.Edit')
    def add_release(self):
        text = 'Register a release'
        return Link('+addrelease', text, icon='add')

    def rdf(self):
        text = 'Download RDF metadata'
        return Link('+rdf', text, icon='download')

    @enabled_with_permission('launchpad.Admin')
    def review(self):
        text = 'Review details'
        return Link('+review', text, icon='edit')

    def subscribe(self):
        text = 'Subscribe to bug mail'
        return Link('+subscribe', text, icon='edit')

class ProductSeriesBugsMenu(ApplicationMenu):

    usedfor = IProductSeries
    facet = 'bugs'
    links = ['new', 'nominations']

    def new(self):
        return Link('+filebug', 'Report a bug', icon='add')

    def nominations(self):
        return Link('+nominations', 'Review nominations', icon='bug')


class ProductSeriesSpecificationsMenu(ApplicationMenu):
    """Specs menu for ProductSeries.

    This menu needs to keep track of whether we are showing all the
    specs, or just those that are approved/declined/proposed. It should
    allow you to change the set your are showing while keeping the basic
    view intact.
    """

    usedfor = IProductSeries
    facet = 'specifications'
    links = ['listall', 'roadmap', 'table', 'setgoals', 'listdeclined', 'new']

    def listall(self):
        text = 'List all blueprints'
        return Link('+specs?show=all', text, icon='info')

    def listaccepted(self):
        text = 'List approved blueprints'
        return Link('+specs?acceptance=accepted', text, icon='info')

    def listproposed(self):
        text = 'List proposed blueprints'
        return Link('+specs?acceptance=proposed', text, icon='info')

    def listdeclined(self):
        text = 'List declined blueprints'
        summary = 'Show the goals which have been declined'
        return Link('+specs?acceptance=declined', text, summary, icon='info')

    def setgoals(self):
        text = 'Set series goals'
        summary = 'Approve or decline feature goals that have been proposed'
        return Link('+setgoals', text, summary, icon='edit')

    def table(self):
        text = 'Assignments'
        summary = 'Show the assignee, drafter and approver of these specs'
        return Link('+assignments', text, summary, icon='info')

    def roadmap(self):
        text = 'Roadmap'
        summary = 'Show the sequence in which specs should be implemented'
        return Link('+roadmap', text, summary, icon='info')

    def new(self):
        text = 'Register a blueprint'
        summary = 'Register a new blueprint for %s' % self.context.title
        return Link('+addspec', text, summary, icon='add')


class ProductSeriesTranslationMenu(ApplicationMenu):
    """Translation menu for ProductSeries.
    """

    usedfor = IProductSeries
    facet = 'translations'
    links = ['translationupload', 'imports', 'translationdownload']

    def imports(self):
        text = 'See import queue'
        return Link('+imports', text)

    def translationupload(self):
        text = 'Upload translations'
        return Link('+translations-upload', text, icon='add')

    def translationdownload(self):
        text = 'Download translations'
        return Link('+export', text, icon='download')


class ProductSeriesTranslationsExportView(BaseExportView):
    """Request tarball export of productseries' complete translations.

    Only complete downloads are supported for now; there is no option to
    select languages, and templates are always included.
    """

    def processForm(self):
        """Process form submission requesting translations export."""
        pofiles = []
        translation_templates = self.context.getCurrentTranslationTemplates()
        for translation_template in translation_templates:
            pofiles += list(translation_template.pofiles)
        return (translation_templates, pofiles)

    def getDefaultFormat(self):
        templates = self.context.getCurrentTranslationTemplates()
        if len(templates) == 0:
            return None
        return templates[0].source_file_format


def get_series_branch_error(product, branch):
    """Check if the given branch is suitable for the given product.

    Returns an HTML error message on error, and None otherwise.
    """
    if branch.product != product:
        return structured(
            '<a href="%s">%s</a> is not a branch of <a href="%s">%s</a>.',
            canonical_url(branch),
            branch.unique_name,
            canonical_url(product),
            product.displayname)
    return None


# A View Class for ProductSeries
#
# XXX: StuartBishop 2005-05-02:
# We should be using autogenerated add forms and edit forms so that
# this becomes maintainable and form validation handled for us.
# Currently, the pages just return 'System Error' as they trigger database
# constraints.
class ProductSeriesView(LaunchpadView, TranslationsMixin):

    def initialize(self):
        self.form = self.request.form
        self.has_errors = False

        # Whether there is more than one PO template.
        self.has_multiple_templates = len(
            self.context.getCurrentTranslationTemplates()) > 1

        # let's find out what source package is associated with this
        # productseries in the current release of ubuntu
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.curr_ubuntu_series = ubuntu.currentseries
        self.setUpPackaging()

        # Check the form submission.
        self.processForm()

    def processForm(self):
        """Process a form if it was submitted."""
        if not self.request.method == "POST":
            # The form was not posted, we don't do anything.
            return

        dispatch_table = {
            'set_ubuntu_pkg': self.setCurrentUbuntuPackage,
            'translations_upload': self.translationsUpload
        }
        dispatch_to = [(key, method)
                        for key,method in dispatch_table.items()
                        if key in self.form
                      ]
        if len(dispatch_to) == 0:
            # None of the know forms have been submitted.
            # XXX CarlosPerelloMarin 2005-11-29 bug=5244:
            # This 'if' should be removed.
            return
        if len(dispatch_to) != 1:
            raise AssertionError(
                "There should be only one command in the form",
                dispatch_to)
        key, method = dispatch_to[0]
        method()

    def setUpPackaging(self):
        """Ensure that the View class correctly reflects the packaging of
        its product series context."""
        self.curr_ubuntu_package = None
        self.curr_ubuntu_pkgname = ''
        try:
            cr = self.curr_ubuntu_series
            self.curr_ubuntu_package = self.context.getPackage(cr)
            cp = self.curr_ubuntu_package
            self.curr_ubuntu_pkgname = cp.sourcepackagename.name
        except NotFoundError:
            pass
        ubuntu = self.curr_ubuntu_series.distribution
        self.ubuntu_history = self.context.getPackagingInDistribution(ubuntu)

    def setCurrentUbuntuPackage(self):
        """Set the Packaging record for this product series in the current
        Ubuntu distroseries to be for the source package name that is given
        in the form.
        """
        ubuntupkg = self.form.get('ubuntupkg', '')
        if ubuntupkg == '':
            # No package was selected.
            self.request.response.addWarningNotification(
                'Request ignored. You need to select a source package.')
            return
        # make sure we have a person to work with
        if self.user is None:
            self.request.response.addErrorNotification('Please log in first!')
            self.has_errors = True
            return
        # see if the name that is given is a real source package name
        spns = getUtility(ISourcePackageNameSet)
        try:
            spn = spns[ubuntupkg]
        except NotFoundError:
            self.request.response.addErrorNotification(
                'Invalid source package name %s' % ubuntupkg)
            self.has_errors = True
            return
        # set the packaging record for this productseries in the current
        # ubuntu series. if none exists, one will be created
        self.context.setPackaging(self.curr_ubuntu_series, spn, self.user)
        self.setUpPackaging()

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return browserLanguages(self.request)

    def translationsUpload(self):
        """Upload new translatable resources related to this IProductSeries.
        """
        file = self.request.form['file']
        if not isinstance(file, FileUpload):
            if file == '':
                self.request.response.addErrorNotification(
                    "Ignored your upload because you didn't select a file to"
                    " upload.")
            else:
                # XXX: Carlos Perello Marin 2004-12-30 bug=116:
                # Epiphany seems to have an unpredictable bug with upload
                # forms (or perhaps it's launchpad because I never had
                # problems with bugzilla). The fact is that some uploads don't
                # work and we get a unicode object instead of a file-like
                # object in "file". We show an error if we see that behaviour.
                self.request.response.addErrorNotification(
                    "The upload failed because there was a problem receiving"
                    " the data.")
            return

        filename = file.filename
        content = file.read()

        if len(content) == 0:
            self.request.response.addWarningNotification(
                "Ignored your upload because the uploaded file is empty.")
            return

        translation_import_queue_set = getUtility(ITranslationImportQueue)

        root, ext = os.path.splitext(filename)
        translation_importer = getUtility(ITranslationImporter)
        if (ext in translation_importer.supported_file_extensions):
            # Add it to the queue.
            translation_import_queue_set.addOrUpdateEntry(
                filename, content, True, self.user,
                productseries=self.context)

            self.request.response.addInfoNotification(
                structured(
                'Thank you for your upload. The file content will be'
                ' reviewed soon by an admin and then imported into Launchpad.'
                ' You can track its status from the <a href="%s/+imports">'
                'Translation Import Queue</a>' % canonical_url(self.context)))

        elif is_tar_filename(filename):
            # Add the whole tarball to the import queue.
            num = translation_import_queue_set.addOrUpdateEntriesFromTarball(
                content, True, self.user,
                productseries=self.context)

            if num > 0:
                self.request.response.addInfoNotification(
                    structured(
                    'Thank you for your upload. %d files from the tarball'
                    ' will be reviewed soon by an admin and then imported'
                    ' into Launchpad. You can track its status from the'
                    ' <a href="%s/+imports">Translation Import Queue</a>' % (
                        num,
                        canonical_url(self.context))))
            else:
                self.request.response.addWarningNotification(
                    "Nothing has happened. The tarball you uploaded does not"
                    " contain any file that the system can understand.")
        else:
            self.request.response.addWarningNotification(
                "Ignored your upload because the file you uploaded was not"
                " recognised as a file that can be imported.")

    @property
    def request_import_link(self):
        """A link to the page for requesting a new code import."""
        return canonical_url(getUtility(ICodeImportSet), view_name='+new')

    @property
    def user_branch_visible(self):
        """Can the logged in user see the user branch."""
        branch = self.context.user_branch
        return (branch is not None and
                check_permission('launchpad.View', branch))


class ProductSeriesEditView(LaunchpadEditFormView):

    schema = IProductSeries
    field_names = [
        'name', 'summary', 'status', 'user_branch', 'releasefileglob']
    custom_widget('summary', TextAreaWidget, height=7, width=62)
    custom_widget('releasefileglob', StrippedTextWidget, displayWidth=40)

    def validate(self, data):
        branch = data.get('user_branch')
        if branch is not None:
            message = get_series_branch_error(self.context.product, branch)
            if message:
                self.setFieldError('user_branch', message)

    @action(_('Change'), name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)

    @property
    def next_url(self):
        return canonical_url(self.context)


class ProductSeriesLinkBranchView(LaunchpadEditFormView):
    """View to set the bazaar branch for a product series."""

    schema = IProductSeries
    field_names = ['user_branch']

    @property
    def next_url(self):
        return canonical_url(self.context)

    def not_import(self, action=None):
        return self.context.import_branch is None

    @action(_('Update'), name='update', condition=not_import)
    def update_action(self, action, data):
        self.updateContextFromData(data)
        self.request.response.addInfoNotification(
            'Series code location updated.')

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the product series page."""


class ProductSeriesLinkBranchFromCodeView(ProductSeriesLinkBranchView):
    """Set the branch link from the code overview page."""

    @property
    def next_url(self):
        """Take the user back to the code overview page."""
        return canonical_url(self.context.product, rootsite="code")


class ProductSeriesReviewView(SQLObjectEditView):

    def changed(self):
        """Redirect to the productseries page.

        We need this because people can now change productseries'
        product and name, and this will make the canonical_url change too.
        """
        self.request.response.addInfoNotification(
            _('This Series has been changed'))
        self.request.response.redirect(canonical_url(self.context))


class ProductSeriesRdfView(object):
    """A view that sets its mime-type to application/rdf+xml"""

    template = ViewPageTemplateFile(
        '../templates/productseries-rdf.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """Render RDF output, and return it as a string encoded in UTF-8.

        Render the page template to produce RDF output.
        The return value is string data encoded in UTF-8.

        As a side-effect, HTTP headers are set for the mime type
        and filename for download."""
        self.request.response.setHeader('Content-Type', 'application/rdf+xml')
        self.request.response.setHeader('Content-Disposition',
                                        'attachment; filename=%s-%s.rdf' % (
                                            self.context.product.name,
                                            self.context.name))
        unicodedata = self.template()
        encodeddata = unicodedata.encode('utf-8')
        return encodeddata


class ProductSeriesSourceSetView:
    """This is a view class that supports a page listing all the
    productseries upstream code imports. This used to be the SourceSource
    table but the functionality was largely merged into ProductSeries, hence
    the need for this View class.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.text = request.form.get('text', None)
        try:
            self.importstatus = int(request.form.get('state', None))
        except (ValueError, TypeError):
            self.importstatus = None
        # setup the initial values if there was no form submitted
        if request.form.get('search', None) is None:
            self.importstatus = ImportStatus.TESTING.value

        results = self.context.searchImports(
            text=self.text, importstatus=self.importstatus)
        self.batchnav = BatchNavigator(results, request)

    def sourcestateselector(self):
        html = '<select name="state">\n'
        html += '  <option value="ANY"'
        if self.importstatus == None:
            html += ' selected'
        html += '>Any</option>\n'
        for enum in ImportStatus.items:
            html += '<option value="'+str(enum.value)+'"'
            if self.importstatus == enum.value:
                html += ' selected'
            html += '>' + str(enum.title) + '</option>\n'
        html += '</select>\n'
        return html


class ProductSeriesSourceListView(LaunchpadView):
    """A listing of all the running imports.

    See `ICodeImportSet.getActiveImports` for our definition of running.
    """

    def initialize(self):
        self.text = self.request.get('text')
        results = getUtility(ICodeImportSet).getActiveImports(text=self.text)

        self.batchnav = BatchNavigator(results, self.request)


class ProductSeriesShortLink(DefaultShortLink):

    def getLinkText(self):
        return self.context.displayname


class ProductSeriesDynMenu(DynMenu):

    def mainMenu(self):
        for release in self.context.releases:
            yield self.makeLink(release.title, context=release)


class ProductSeriesFileBugRedirect(LaunchpadView):
    """Redirect to the product's +filebug page."""

    def initialize(self):
        filebug_url = "%s/+filebug" % canonical_url(self.context.product)
        self.request.response.redirect(filebug_url)
