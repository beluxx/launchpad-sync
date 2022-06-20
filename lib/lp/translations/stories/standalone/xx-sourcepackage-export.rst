Downloading Source Package Translations
=======================================

Launchpad lets you request a downloadable tarball of all current
templates and translations for a source package.


Where to request
----------------

For qualified users (see below), the option is shown in the Translations
action bar for a source package.  The link is called "Download
translations."

Mark is a qualified user.

    >>> browser = setupBrowser(auth='Basic mark@example.com:test')
    >>> browser.open(
    ...     'http://translations.launchpad.test/ubuntu/hoary/+source/'
    ...     'mozilla/')
    >>> download = browser.getLink('download a full tarball')
    >>> download_url = download.url
    >>> download.click()
    >>> print(browser.url)
    http://translations.launchpad.test/ubuntu/hoary/+source/mozilla/+export


Authorization
-------------

The option to download a package's full translations is restricted to
users who are involved in certain ways, in order to keep load to a
reasonable level.

    >>> from zope.security.interfaces import Unauthorized
    >>> from zope.testbrowser.browser import LinkNotFoundError

    >>> def can_download_translations(browser):
    ...     """Can browser download full package translations?
    ...
    ...     Checks for the "Download" link on an Ubuntu package.
    ...     Also attempts direct access to the same package's download
    ...     page and sees that the two have consistent access rules.
    ...     """
    ...     browser.open(
    ...         'http://translations.launchpad.test/'
    ...         'ubuntu/hoary/+source/mozilla/')
    ...     try:
    ...         browser.getLink('download a full tarball').click()
    ...     except LinkNotFoundError:
    ...         see_link = False
    ...     else:
    ...         see_link = True
    ...
    ...     try:
    ...         browser.open(download_url)
    ...     except Unauthorized:
    ...         have_access = False
    ...     else:
    ...         have_access = True
    ...
    ...     if have_access != see_link:
    ...         if have_access:
    ...             return "Download link not shown, but direct URL works."
    ...         else:
    ...             return "Download link shown to unauthorized user."
    ...
    ...     return have_access

An arbitrary user visiting the package's translations page does not see
the download link for the full package, and cannot download.

    >>> can_download_translations(user_browser)
    False

It's the same for anonymous visitors.

    >>> can_download_translations(anon_browser)
    False

An administrator, of course, can download the full translations.

    >>> can_download_translations(admin_browser)
    True

Oofy Prosser is a Translations expert.  Gussie Fink-Nottle is not an
admin or expert, but he is one of the owners of a translation group.

    >>> from zope.component import getUtility

    >>> from lp.testing import login, logout
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet

    >>> login('foo.bar@canonical.com')
    >>> personset = getUtility(IPersonSet)
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

    >>> carlos = personset.getByName('carlos')
    >>> oofy = factory.makePerson(
    ...     email='oofy@drones.example.com', name='oofy',
    ...     displayname='Oofy Prosser')
    >>> rosetta_admins = personset.getByName('rosetta-admins')
    >>> ignored = rosetta_admins.addMember(oofy, carlos)

    >>> gussie = factory.makePerson(
    ...     email='gussie@drones.example.com', name='gussie',
    ...     displayname='Gussie Fink-Nottle')
    >>> translators = factory.makeTeam(gussie)
    >>> group = factory.makeTranslationGroup(translators)

    >>> logout()

Oofy can download translations; Gussie cannot.

    >>> oofy_browser = setupBrowser(auth='Basic oofy@drones.example.com:test')
    >>> can_download_translations(oofy_browser)
    True

    >>> gussie_browser = setupBrowser(
    ...     auth='Basic gussie@drones.example.com:test')
    >>> can_download_translations(gussie_browser)
    False

Gussie's translation group takes charge of Ubuntu translations.

    >>> login('foo.bar@canonical.com')
    >>> ubuntu.translationgroup = group
    >>> logout()

This change gives Gussie the ability to download full package
translations.

    >>> can_download_translations(gussie_browser)
    True

User "cprov" is neither a member of the translation group nor a Rosetta
expert.

    >>> login('foo.bar@canonical.com')
    >>> cprov = personset.getByName('cprov')
    >>> cprov.inTeam(group.owner)
    False

    >>> rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts
    >>> cprov.inTeam(rosetta_experts)
    False

    >>> logout()

"cprov" is able to download translations as an Ubuntu uploader.

    >>> ubuntu_member_browser = setupBrowser(
    ...     auth='Basic cprov@ubuntu.com:test')
    >>> can_download_translations(ubuntu_member_browser)
    True


Making the request
------------------

The "Download" link leads to a page that lets the user select an export
format, and request the download.

    >>> browser.open(
    ...     'http://translations.launchpad.test/'
    ...     'ubuntu/hoary/+source/mozilla/+export')
    >>> browser.title
    'Download : Hoary (5.04) : Translations : mozilla package : Ubuntu'

    >>> browser.getControl('Request Download').click()

    >>> print(browser.url)
    http://translations.launchpad.test/ubuntu/hoary/+source/mozilla

    >>> print_feedback_messages(browser.contents)
    Your request has been received. Expect to receive an email shortly.


Mixed formats
-------------

We only support exports in a single, chosen file format.  If the source
package has templates in different formats, the request page shows a
warning about this.

Evolution's package in Hoary has two current templates, both with PO as
their native file format.

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.translations.model.potemplate import POTemplateSubset
    >>> from lp.translations.interfaces.translationfileformat import (
    ...     TranslationFileFormat)
    >>> login(ANONYMOUS)
    >>> hoary = ubuntu.getSeries('hoary')
    >>> hoary_subset = POTemplateSubset(distroseries=hoary)
    >>> an_evolution_template = hoary_subset.getPOTemplateByPath(
    ...     'po/evolution-2.2.pot')
    >>> logout()

If the file format for one of these templates were different from the
other's, a warning would appear on the export request form that wasn't
there before.

    >>> browser.open(
    ...     'http://translations.launchpad.test/'
    ...     'ubuntu/hoary/+source/evolution/+export')
    >>> print_feedback_messages(browser.contents)

    >>> an_evolution_template.source_file_format = TranslationFileFormat.MO
    >>> flush_database_updates()

    >>> browser.open(
    ...     'http://translations.launchpad.test/'
    ...     'ubuntu/hoary/+source/evolution/+export')
    >>> print_feedback_messages(browser.contents)
    This package has templates with different native file formats.  If you
    proceed, all translations will be exported in the single format you
    specify.
