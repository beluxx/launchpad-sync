=============================
Project (nee product) widgets
=============================

Projects (which used to be referred to as 'products') have their own widgets
for specifying their attributes.


Choosing a bugtracker
=====================

When choosing which bug tracker a project uses, there are three possible
options.  A project can use Launchpad, an external bug tracker, or no specific
bug tracker.  This information is captured using two attributes,
'official_malone' and 'bugtracker', and we'll use a custom widget and a custom
field in order to set these values.  This is presented to the user as radio
buttons, where the option for using an external bug tracker includes a drop
down menu for choosing the correct tracker.

Firefox uses Launchpad as its bug tracker.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> firefox.official_malone
    True

The custom field's missing value (i.e. None) represents the 'no bug tracker'
option.  This is displayed by the widget as the project having a bug tracker
in a specified external location.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.app.widgets.product import ProductBugTrackerWidget
    >>> from lp.registry.interfaces.product import IProduct

    >>> product_bugtracker = IProduct['bugtracker'].bind(firefox)
    >>> widget = ProductBugTrackerWidget(
    ...     product_bugtracker, product_bugtracker.vocabulary,
    ...     LaunchpadTestRequest())

Firefox has not yet selected a bug tracker.

    >>> print(firefox.projectgroup.bugtracker)
    None

    >>> from bs4.element import Tag
    >>> from lp.services.beautifulsoup import BeautifulSoup
    >>> from lp.testing.pages import extract_text
    >>> def print_items(html):
    ...     soup = BeautifulSoup(html)
    ...     labels = soup('label')
    ...     for label in labels:
    ...         control = label.previous.previous
    ...         if control['type'] == 'radio' and control.get('checked'):
    ...             print('[X]', extract_text(label))
    ...         elif control['type'] == 'radio':
    ...             print('[ ]', extract_text(label))
    ...         else:
    ...             pass
    >>> print_items(widget())
    [ ] In Launchpad
    [ ] In a registered bug tracker:
    [ ] By emailing an upstream bug contact:
    [X] Somewhere else

Firefox chooses to use the Gnome Bugzilla bug tracker, and the widget displays
this bug tracker as selected.

    >>> from lp.bugs.interfaces.bugtracker import IBugTrackerSet
    >>> tracker_set = getUtility(IBugTrackerSet)

    >>> gnome_bugzilla = tracker_set.getByName('gnome-bugzilla')
    >>> login('foo.bar@canonical.com')
    >>> firefox.projectgroup.bugtracker = gnome_bugzilla

    >>> print_items(widget())
    [ ] In Launchpad
    [ ] In a registered bug tracker:
    [ ] By emailing an upstream bug contact:
    [X] In the The Mozilla Project bug tracker (GnomeGBug GTracker)

On second thought, Firefox has no specified bug tracker.

    >>> old_firefox_projectgroup = firefox.projectgroup
    >>> firefox.projectgroup = None

    >>> print_items(widget())
    [ ] In Launchpad
    [ ] In a registered bug tracker:
    [ ] By emailing an upstream bug contact:
    [X] Somewhere else

Calling the widget's setRenderedValue() with a specific bug tracker overrides
the display of the selected bug tracker.

    >>> mozilla_bugtracker = tracker_set.getByName('mozilla.org')
    >>> widget.setRenderedValue(mozilla_bugtracker)

    >>> print_items(widget())
    [ ] In Launchpad
    [X] In a registered bug tracker:
    [ ] By emailing an upstream bug contact:
    [ ] Somewhere else

When the bug tracker is an Email Address bug tracker, the "By emailing" option
is shown as selected instead.

    >>> email_bugtracker = tracker_set.getByName('email')
    >>> widget.setRenderedValue(email_bugtracker)

    >>> print_items(widget())
    [ ] In Launchpad
    [ ] In a registered bug tracker:
    [X] By emailing an upstream bug contact:
    [ ] Somewhere else

When the bug tracker is the marker attribute representing Launchpad, the
widget is displayed as having the 'In Launchpad' option selected.

    >>> widget.setRenderedValue(widget.context.malone_marker)
    >>> print_items(widget())
    [X] In Launchpad
    [ ] In a registered bug tracker:
    [ ] By emailing an upstream bug contact:
    [ ] Somewhere else

A user selects the Malone bug tracker, indicating that bugs are tracked in
Launchpad.

    >>> form = {
    ...     'field.bugtracker': 'malone',
    ...     'field.bugtracker.bugtracker': 'debbugs',
    ...     }
    >>> widget = ProductBugTrackerWidget(
    ...     product_bugtracker, product_bugtracker.vocabulary,
    ...     LaunchpadTestRequest(form=form))

    # This is just a generic object so there's no other way to test it.
    >>> widget.getInputValue() is product_bugtracker.malone_marker
    True

The bugtracker value passed to the widget caused the sub-widget used to select
the bug tracker to have the correct value.

    >>> print(widget.bugtracker_widget.getInputValue().name)
    debbugs

By indicating an external bug tracker, the selected bug tracker will be
returned.

    >>> form['field.bugtracker'] = 'external'
    >>> widget = ProductBugTrackerWidget(
    ...     product_bugtracker, product_bugtracker.vocabulary,
    ...     LaunchpadTestRequest(form=form))
    >>> debbugs = widget.getInputValue()
    >>> print(debbugs.name)
    debbugs

The sub-widget for selecting the external bug tracker also has debbugs as its
input value.

    >>> print(widget.getInputValue().name)
    debbugs

The project's bug tracker, or no bug tracker, at all is selected.

    >>> form['field.bugtracker'] = 'project'
    >>> widget = ProductBugTrackerWidget(
    ...     product_bugtracker, product_bugtracker.vocabulary,
    ...     LaunchpadTestRequest(form=form))
    >>> print(widget.getInputValue())
    None

We can't use the value returned from getInputValue() to set an attribute on
the project directly.  Instead the custom field ProductBugTracker is used.  It
knows how to deal with the special malone marker when getting and setting the
values.

Firefox still uses Malone officially, which means that the field returns the
marker object.

    >>> firefox.official_malone
    True
    >>> print(firefox.bugtracker)
    None
    >>> product_bugtracker.get(firefox) is product_bugtracker.malone_marker
    True

Passing a bug tracker to the field's set method will unset official_malone and
set the bug tracker.

    >>> login('test@canonical.com')
    >>> product_bugtracker.set(firefox, debbugs)
    >>> firefox.official_malone
    False
    >>> print(firefox.bugtracker.name)
    debbugs

Choosing to use Malone again, the changes above will be reverted.

    >>> product_bugtracker.set(firefox, product_bugtracker.malone_marker)
    >>> firefox.official_malone
    True
    >>> print(firefox.bugtracker)
    None

Passing None to the field's set method, Firefox will once again switch to not
using Malone, and its bug tracker will be set to None.

    >>> product_bugtracker.set(firefox, None)
    >>> firefox.official_malone
    False
    >>> print(firefox.bugtracker)
    None

The ProductBugTrackerWidget renders two fields that are subordinate to
the 4 choices.

    >>> def print_controls(html):
    ...     soup = BeautifulSoup(html)
    ...     controls = soup('input')
    ...     for control in controls:
    ...         if control['type'] != 'hidden':
    ...             if 'subordinate' in control.parent.get('class', ''):
    ...                 print('--')
    ...             print(control['id'], control['type'])

    >>> print_controls(widget())
    field.bugtracker.0 radio
    -- field.enable_bug_expiration checkbox
    field.bugtracker.2 radio
    field.bugtracker.bugtracker text
    -- field.remote_product text
    field.bugtracker.3 radio
    field.bugtracker.upstream_email_address text
    field.bugtracker.1 radio


Choosing a License
==================

A custom widget is used to display a link to the licence policy.

    >>> from lp.app.widgets.product import LicenseWidget

    >>> form = {'field.licenses': []}

    >>> product = getUtility(IProductSet).get(1)
    >>> licenses_field = IProduct['licenses'].bind(product)
    >>> vtype = licenses_field.value_type
    >>> request = LaunchpadTestRequest(form=form)
    >>> license_widget = LicenseWidget(licenses_field, vtype, request)

The widget has one checkbox for each licence, and it also has a link to the
licence policy.  The licences are split up into categories, and they are
presented ordered to appear in a 3 column list.

    >>> from lp.testing.pages import find_tag_by_id

    >>> html = license_widget()
    >>> print(extract_text(find_tag_by_id(html, 'recommended')))
    Apache Licence view licence
    GNU Affero GPL v3 view licence
    GNU LGPL v2.1 view licence
    Simplified BSD Licence view licence
    GNU GPL v2 view licence
    GNU LGPL v3 view licence
    Creative Commons - No Rights Reserved view licence
    GNU GPL v3 view licence
    MIT / X / Expat Licence view licence

    >>> print(extract_text(find_tag_by_id(html, 'more')))
    Academic Free Licence view licence
    Eclipse Public Licence view licence
    PHP Licence view licence
    Artistic Licence 1.0 view licence
    Educational Community Licence view licence
    Public Domain view licence
    Artistic Licence 2.0 view licence
    GNU FDL no options view licence
    Python Licence view licence
    Common Public Licence view licence
    Mozilla Public Licence view licence
    Zope Public Licence view licence
    Creative Commons - Attribution view licence
    Open Font Licence v1.1 view licence
    Creative Commons - Attribution Share Alike view licence
    Open Software Licence v 3.0 view licence


    >>> print(extract_text(find_tag_by_id(html, 'special')))
    I don't know yet
    Other/Proprietary
    Other/Open Source

There is a deprecated section that is generally not visible...

    >>> print(find_tag_by_id(html, 'deprecated'))
    None

...unless the old "Perl licence" is selected.

    >>> form['field.licenses'] = ['PERL']
    >>> request = LaunchpadTestRequest(form=form)
    >>> license_widget = LicenseWidget(licenses_field, vtype, request)
    >>> html = license_widget()
    >>> print(extract_text(find_tag_by_id(html, 'deprecated')))
    Perl Licence

One licence, the GNU GPL v2, is selected.

    >>> form['field.licenses'] = ['GNU_GPL_V2']
    >>> request = LaunchpadTestRequest(form=form)
    >>> license_widget = LicenseWidget(licenses_field, vtype, request)

    >>> def print_checked_items(html, links=False):
    ...     soup = BeautifulSoup(html)
    ...     for label in soup.find_all('label'):
    ...         if not isinstance(label.next, Tag):
    ...             continue
    ...         if label.next.get('checked'):
    ...             print('[X]', end=' ')
    ...         else:
    ...             print('[ ]', end=' ')
    ...         print(extract_text(label), end='')
    ...         if links and label.a is not None:
    ...             print(' <%s>' % label.a.get('href'))
    ...         else:
    ...             print()

    >>> for item in license_widget.getInputValue():
    ...     print(repr(item))
    <DBItem License.GNU_GPL_V2, (130) ...>

    >>> print_checked_items(license_widget())
    [ ] Apache Licence ...
    [ ] GNU Affero GPL v3 view licence
    [ ] GNU LGPL v2.1 view licence
    [ ] Simplified BSD Licence view licence
    [X] GNU GPL v2 view licence
    [ ] GNU LGPL v3 view licence
    [ ] Creative Commons - No Rights Reserved view licence
    [ ] GNU GPL v3 view licence
    ...

A second licence is selected.

    >>> form['field.licenses'] = ['GNU_LGPL_V2_1', 'GNU_GPL_V2']
    >>> request = LaunchpadTestRequest(form=form)
    >>> license_widget = LicenseWidget(licenses_field, vtype, request)

    >>> sorted(license_widget.getInputValue())
    [<DBItem License.GNU_GPL_V2, (130) GNU GPL v2>,
     <DBItem License.GNU_LGPL_V2_1, (150) GNU LGPL v2.1>]

    >>> print_checked_items(license_widget())
    [ ] Apache Licence ...
    [ ] GNU Affero GPL v3 view licence
    [X] GNU LGPL v2.1 view licence
    [ ] Simplified BSD Licence view licence
    [X] GNU GPL v2 view licence
    [ ] GNU LGPL v3 view licence
    [ ] Creative Commons - No Rights Reserved view licence
    [ ] GNU GPL v3 view licence
    ...

Many licences have links to the official pages describing their licences.

    >>> print_checked_items(license_widget(), links=True)
    [ ] Apache Licence ... <http://www.opensource.org/licenses/apache2.0.php>
    ...

But not all of them.

    >>> print_checked_items(license_widget(), links=True)
    [ ] Apache Licence ... <http://www.opensource.org/licenses/apache2.0.php>
    ...
    [ ] I don't know yet
    [ ] Other/Proprietary
    [ ] Other/Open Source


GhostWidget
-----------

The GhostWidget is used to suppress the markup of a field in cases where
another mechanism is used to insert the field's markup into the page. Some
widget for example generate the markup for subordinate fields, but they
do not manage the field itself. The LicenseWidget widget for example
generates the markup for the license_info field; the view must use a
GhostWidget to suppress the markup.

    >>> from lp.app.widgets.product import GhostWidget

    >>> license_info = IProduct['license_info'].bind(firefox)
    >>> ghost_widget = GhostWidget(license_info, LaunchpadTestRequest())
    >>> ghost_widget.visible
    False
    >>> ghost_widget.hidden()
    ''
    >>> ghost_widget()
    ''

Launchpad form macros do not generate table rows for the GhostWidget.

    >>> from lp.services.config import config
    >>> from zope.browserpage import ViewPageTemplateFile
    >>> from lp.app.browser.launchpadform import LaunchpadFormView

    >>> class GhostWidgetView(LaunchpadFormView):
    ...     page_title = 'Test'
    ...     template = ViewPageTemplateFile(
    ...         config.root + '/lib/lp/app/templates/generic-edit.pt')
    ...     schema = IProduct
    ...     field_names = ['license_info']
    ...     custom_widget_license_info = GhostWidget

    >>> request = LaunchpadTestRequest()
    >>> request.setPrincipal(factory.makePerson())
    >>> view = GhostWidgetView(firefox, request)
    >>> view.initialize()
    >>> print(extract_text(find_tag_by_id(
    ...     view.render(), 'launchpad-form-widgets')))
    <BLANKLINE>
