TranslationImportQueueEntry
===========================

The TranslationImportQueueEntry is an entry of the queue that will be imported
into Rosetta.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.registry.interfaces.distroseries import IDistroSeries
    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue)
    >>> from lp.translations.model.translationimportqueue import (
    ...     TranslationImportQueueEntry)

    >>> translationimportqueue = getUtility(ITranslationImportQueue)

    >>> def clear_queue(queue):
    ...     """Remove all entries off the import queue."""
    ...     store = IStore(TranslationImportQueueEntry)
    ...     store.find(TranslationImportQueueEntry).remove()

    >>> def get_target_names(status=None):
    ...     """Call getRequestTargets, return list of names/titles."""
    ...     result = []
    ...     queue = translationimportqueue.getRequestTargets(
    ...         user=None,status=status)
    ...     for object in queue:
    ...         if IDistroSeries.providedBy(object):
    ...             name = "%s/%s" % (object.distribution.name, object.name)
    ...         else:
    ...             name = object.name
    ...         result.append("%s %s" % (name, object.displayname))
    ...     return result

    >>> def print_list(strings):
    ...     """Print list of strings as list of lines."""
    ...     for string in strings:
    ...         print(string)


getGuessedPOFile
----------------

This property gives us the IPOFile where we think we should import this entry.

To test it, we need to add an entry to the queue.

Here we have some imports and utility fetch.

    >>> import transaction
    >>> from zope.component import getUtility
    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.interfaces.sourcepackagename import (
    ...     ISourcePackageNameSet)
    >>> from lp.translations.enums import RosettaImportStatus
    >>> from lp.registry.model.distroseries import DistroSeries
    >>> from lp.registry.model.productseries import ProductSeries
    >>> from lp.registry.model.sourcepackagename import SourcePackageName
    >>> from lp.testing import login

    >>> rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts

    >>> distroset = getUtility(IDistributionSet)
    >>> packageset = getUtility(ISourcePackageNameSet)
    >>> productset = getUtility(IProductSet)


Login as a user without privileges.

    >>> login('no-priv@canonical.com')

First, we are going to try to do the guess against the Evolution product. That
means that we are going to use the ProductSeries.id = 3

    >>> evolution_productseries = ProductSeries.get(3)

Attach the file to the product series, without associating it with any
potemplate.

    >>> entry = translationimportqueue.addOrUpdateEntry(
    ...     u'po/sr.po', b'foo', True, rosetta_experts,
    ...      productseries=evolution_productseries)

This entry has no information about the IPOFile where it should be attached
to:

    >>> entry.import_into is None
    True

And the guessing algorithm will not be able to guess anything as there is no
IPOFiles on the same path and we have two IPOTemplates on the same path where
this IPOFile is located ('po/')

    >>> entry.getGuessedPOFile() is None
    True

Now let's try the same against the evolution sourcepackage that only has an
IPOTemplate.

    >>> hoary_distroseries = DistroSeries.get(3)
    >>> evolution_sourcepackagename = SourcePackageName.get(9)
    >>> entry = translationimportqueue.addOrUpdateEntry(
    ...     u'po/sr.po', b'foo', True, rosetta_experts,
    ...      distroseries=hoary_distroseries,
    ...      sourcepackagename=evolution_sourcepackagename)
    >>> transaction.commit()

This entry has no information about the IPOFile where it should be attached
to:

    >>> entry.import_into is None
    True

And the guessing algorithm is able to give us an IPOFile where it should be
imported.

    >>> entry.getGuessedPOFile() is None
    False

    >>> print(entry.getGuessedPOFile().title)
    Serbian (sr) ... of evolution-2.2 in Ubuntu Hoary package "evolution"


Let's try now to update the entries.

We need to know the status that the entry has.

    >>> entry.status.title
    'Needs Review'

And store current creation and status change date:

    >>> previous_dateimported = entry.dateimported
    >>> previous_date_status_changed = entry.date_status_changed

Now, we do a new upload.

    >>> entry = translationimportqueue.addOrUpdateEntry(
    ...     u'po/sr.po', b'foo', True, rosetta_experts,
    ...      distroseries=hoary_distroseries,
    ...      sourcepackagename=evolution_sourcepackagename)
    >>> transaction.commit()

And the new status is

    >>> entry.status.title
    'Needs Review'

The dateimported remains the same as it was already waiting to be imported.

    >>> entry.dateimported == previous_dateimported
    True

And the date_status_changed is newer

    >>> entry.date_status_changed > previous_date_status_changed
    True

Let's change now its status to imported and see what happens. To do it,
we need to be logged in as an admin and set an import target.

    >>> login('carlos@canonical.com')
    >>> entry.pofile = factory.makePOFile('sr')
    >>> entry.setStatus(RosettaImportStatus.IMPORTED, rosetta_experts)

The status change updates date_status_changed as well.

    >>> entry.date_status_changed > previous_date_status_changed
    True

    >>> transaction.commit()
    >>> previous_date_status_changed = entry.date_status_changed

Do the new upload. It will be an upload by the maintainer.

    >>> by_maintainer = True
    >>> po_sr_entry = translationimportqueue.addOrUpdateEntry(
    ...     u'po/sr.po', b'foo', by_maintainer, rosetta_experts,
    ...      distroseries=hoary_distroseries,
    ...      sourcepackagename=evolution_sourcepackagename)

And the new status is

    >>> print(po_sr_entry.status.title)
    Needs Review

The dateimported remains the same as it was already waiting to be imported.

    >>> po_sr_entry.dateimported > previous_dateimported
    True

However the date_status_changed is still updated.

    >>> po_sr_entry.date_status_changed > previous_date_status_changed
    True

First, we import a new .pot file.

    >>> pot_entry = translationimportqueue.addOrUpdateEntry(
    ...     'po/evolution-2.2.pot', b'foo', True, rosetta_experts,
    ...      distroseries=hoary_distroseries,
    ...      sourcepackagename=evolution_sourcepackagename)

Change pofile.path value to a value that will help to prepare next test.
Basically, we prevent that it's found by its path.

    >>> pofile = po_sr_entry.getGuessedPOFile()
    >>> print(pofile.path)
    po/sr.po
    >>> pofile.path = u'po/sr-old.po'

Reset any pofile/potemplate information we have for the po_sr_entry.

    >>> po_sr_entry.potemplate = None
    >>> po_sr_entry.pofile = None

    >>> transaction.commit()

Now, let's check that we cannot find the pot_entry as a POTemplate because
the way our code works, we cannot guess it while we have a .pot file pending
to be imported.

    >>> pot_entry.status.title
    'Needs Review'
    >>> po_sr_entry.getGuessedPOFile() is None
    True

But if that entry is imported, the guessing algorithm works.

    >>> pot_entry.potemplate = factory.makePOTemplate()
    >>> pot_entry.setStatus(RosettaImportStatus.IMPORTED, rosetta_experts)
    >>> guessed_pofile = po_sr_entry.getGuessedPOFile()
    >>> guessed_pofile is None
    False

We can see that we got the same POFile as before:

    >>> guessed_pofile == pofile
    True

And because it's an upload by the maintainer, the IPOFile in our database got
its path changed to the one noted by this upload instead of having the
one we set a couple of lines ago (u'po/sr-old.pot'):

    >>> po_sr_entry.by_maintainer
    True
    >>> pofile.path == po_sr_entry.path
    True
    >>> print(pofile.path)
    po/sr.po

getGuessedPOFile with KDE
.........................

Official KDE packages have a non standard layout where the .pot files are
stored inside the sourcepackage with the binaries that will use it and the
translations are stored in external packages following the same language pack
ideas that we use with Ubuntu. This layout breaks completely Rosetta because
we don't have a way to link the .po and .pot files coming from different
packages. For this case, we use some extra information to get that link
between different sourcepackages.

The info we use is:
    - The sourcepackagename: All KDE language packs have
      the sourcepackagename following this pattern:
      kde-i18n-LANGCODE or kde-l10n-LANGCODE. We get from here the
      language where the .po files belong.
    - The .po filename: All .po files are stored using the translation
      domain as its filename. This information helps us to get the
      IPOTemplate where we should associate this .po file.

To do this test, we are going to do all in a single transaction and will
rollback it when it's finished.

First, we are going to add three new sourcepackagenames for this test,
kdebase, kde-i18n-es and kde-l10n-sr-latin. The first is from where the .pot
file come and the others have .po files.

    >>> sourcepackagenameset = getUtility(ISourcePackageNameSet)
    >>> kdebase = sourcepackagenameset.new('kdebase')
    >>> kde_i18n_es = sourcepackagenameset.new('kde-i18n-es')
    >>> kde_l10n_sr_latin = sourcepackagenameset.new('kde-i18n-sr-latin')

Let's attach the .pot file

    >>> kde_pot_entry = translationimportqueue.addOrUpdateEntry(
    ...     'po/kdebugdialog.pot', b'foo content', True, rosetta_experts,
    ...      distroseries=hoary_distroseries,
    ...      sourcepackagename=kdebase)

Create the template name and attach this new import to it.

    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> potemplateset = getUtility(IPOTemplateSet)
    >>> subset = potemplateset.getSubset(
    ...     distroseries=hoary_distroseries, sourcepackagename=kdebase)
    >>> kde_pot_entry.potemplate = subset.new(
    ...     'kdebugdialog', 'kdebugdialog', 'po/kdebugdialog.pot',
    ...     rosetta_experts)
    >>> print(kde_pot_entry.potemplate.title)
    Template "kdebugdialog" in Ubuntu Hoary package "kdebase"

And set this entry as already imported.

    >>> kde_pot_entry.setStatus(RosettaImportStatus.IMPORTED, rosetta_experts)
    >>> flush_database_updates()

Let's attach a .po file from kde-i18n-es

    >>> es_entry = translationimportqueue.addOrUpdateEntry(
    ...     'messages/kdebase/kdebugdialog.po', b'foo content', True,
    ...     rosetta_experts, distroseries=hoary_distroseries,
    ...      sourcepackagename=kde_i18n_es)

And we will get the right IPOFile.

    >>> print(es_entry.getGuessedPOFile().title)
    Spanish (es) ... of kdebugdialog in Ubuntu Hoary package "kdebase"

The kde-i18n-sr-latin is a bit special, the language is sr@latin and we should
be able to know that.

    >>> sr_latin = factory.makeLanguage('sr@latin', 'Serbian Latin')
    >>> sr_latin_entry = translationimportqueue.addOrUpdateEntry(
    ...     'messages/kdebase/kdebugdialog.po', b'foo content', True,
    ...     rosetta_experts, distroseries=hoary_distroseries,
    ...      sourcepackagename=kde_l10n_sr_latin)

And we will get the right IPOFile.

    >>> print(sr_latin_entry.getGuessedPOFile().title)
    Serbian Latin (sr@latin) ... of kdebugdialog ... package "kdebase"

Now, we are going to see what happens if we get a .po file for a template
that is not yet imported.

    >>> es_without_potemplate_entry = translationimportqueue.addOrUpdateEntry(
    ...     'messages/kdebase/konqueror.po', b'foo content', True,
    ...     rosetta_experts, distroseries=hoary_distroseries,
    ...      sourcepackagename=kde_i18n_es)

We don't know the IPOFile where it should be imported.

    >>> es_without_potemplate_entry.getGuessedPOFile() is None
    True

Sometimes, a translation domain is not following the restrictions we have for
name fields, and thus, we need to be sure that we look for KDE .pot files
using the translation domain instead the name.

We will see it working here with this example:

    >>> kde_pot_entry = translationimportqueue.addOrUpdateEntry(
    ...     'po/kio_sftp.pot', b'foo content', True, rosetta_experts,
    ...      distroseries=hoary_distroseries,
    ...      sourcepackagename=kdebase)

Create the template name and attach this new import to it.

    >>> potemplateset = getUtility(IPOTemplateSet)
    >>> subset = potemplateset.getSubset(
    ...     distroseries=hoary_distroseries, sourcepackagename=kdebase)
    >>> kde_pot_entry.potemplate = subset.new(
    ...     'kio-sftp', 'kio_sftp', 'po/kio_sftp.pot', rosetta_experts)
    >>> print(kde_pot_entry.potemplate.title)
    Template "kio-sftp" in Ubuntu Hoary package "kdebase"

And set this entry as already imported.

    >>> kde_pot_entry.setStatus(RosettaImportStatus.IMPORTED, rosetta_experts)
    >>> flush_database_updates()

Let's attach a .po file from kde-i18n-es

    >>> es_entry = translationimportqueue.addOrUpdateEntry(
    ...     'messages/kdebase/kio_sftp.po', b'foo content', True,
    ...     rosetta_experts, distroseries=hoary_distroseries,
    ...      sourcepackagename=kde_i18n_es)

And we will get the right IPOFile.

    >>> print(es_entry.getGuessedPOFile().title)
    Spanish (es) translation of kio-sftp in Ubuntu Hoary package "kdebase"

Finally, we abort the transaction to undo all changes done.

    >>> transaction.abort()


getGuessedPOFile with KOffice
.............................

Like official KDE packages, KOffice stores the .pot and .po files in different
packages, the only difference it has is that there is just one source package
and the language information is stored as part of the path, but hidden with
more text. The source package with translations is koffice-l10n, and
the layout is:

koffice-i18n-LANGCODE-VERSION/messages/koffice/TRANSLATIONDOMAIN.po

To do this test, we are going to do all in a single transaction and will
rollback it when it's finished.

First, we are going to add two new sourcepackagenames for this test,
koffice and koffice-l10n. The first is from where the .pot
file come and the other for the .po files.

    >>> sourcepackagenameset = getUtility(ISourcePackageNameSet)
    >>> koffice = sourcepackagenameset.new('koffice')
    >>> koffice_l10n = sourcepackagenameset.new('koffice-l10n')

Let's attach the .pot file

    >>> koffice_pot_entry = translationimportqueue.addOrUpdateEntry(
    ...     'po/koffice.pot', b'foo content', True, rosetta_experts,
    ...      distroseries=hoary_distroseries,
    ...      sourcepackagename=koffice)

Create the template name and attach this new import to it.

    >>> potemplateset = getUtility(IPOTemplateSet)
    >>> subset = potemplateset.getSubset(
    ...     distroseries=hoary_distroseries, sourcepackagename=koffice)
    >>> koffice_pot_entry.potemplate = subset.new(
    ...     'koffice', 'koffice', 'po/koffice.pot', rosetta_experts)
    >>> print(koffice_pot_entry.potemplate.title)
    Template "koffice" in Ubuntu Hoary package "koffice"

And set this entry as already imported.

    >>> koffice_pot_entry.setStatus(
    ...     RosettaImportStatus.IMPORTED,
    ...     rosetta_experts)
    >>> flush_database_updates()

Let's attach a .po file from koffice-l10n

    >>> es_entry = translationimportqueue.addOrUpdateEntry(
    ...     'koffice-i18n-es-1.5.2/messages/koffice/koffice.po',
    ...     b'foo content', True, rosetta_experts,
    ...     distroseries=hoary_distroseries, sourcepackagename=koffice_l10n)

And we will get the right IPOFile.

    >>> print(es_entry.getGuessedPOFile().title)
    Spanish (es) translation of koffice in Ubuntu Hoary package "koffice"

Let's try now a language with variant information like sr@latin.

    >>> sr_latin = factory.makeLanguage('sr@latin', 'Serbian Latin')
    >>> sr_latin_entry = translationimportqueue.addOrUpdateEntry(
    ...     'koffice-i18n-sr@latin-1.5.2/messages/koffice/koffice.po',
    ...     b'foo content', True, rosetta_experts,
    ...     distroseries=hoary_distroseries, sourcepackagename=koffice_l10n)

And we will get the right IPOFile.

    >>> print(sr_latin_entry.getGuessedPOFile().title)
    Serbian Latin (sr@latin) ... koffice in Ubuntu Hoary package "koffice"

Now, we are going to see what happens if we get a .po file for a template
that is not yet imported.

    >>> es_without_potemplate_entry = translationimportqueue.addOrUpdateEntry(
    ...     'koffice-i18n-es-1.5.2/messages/koffice/kchart.po',
    ...     b'foo content', True, rosetta_experts,
    ...     distroseries=hoary_distroseries, sourcepackagename=koffice_l10n)

We don't know the IPOFile where it should be imported.

    >>> es_without_potemplate_entry.getGuessedPOFile() is None
    True

Finally, we abort the transaction to undo all changes done.

    >>> transaction.abort()


getGuessedPOFile with .po files in different directories
........................................................

Some packages have translations and templates inside the same package, but
they don't have them inside the same directory. The layout is:

DIRECTORY/TRANSLATION_DOMAIN.pot
DIRECTORY/LANG_CODE/TRANSLATION_DOMAIN.po

sometimes the layout changes a bit, for instance in ktorrent, and looks like:

DIRECTORY/TRANSLATION_DOMAIN.pot
DIRECTORY/LANG_CODE/messages/TRANSLATION_DOMAIN.po

Or in the zope packages:

DIRECTORY/TRANSLATION_DOMAIN.pot
DIRECTORY/LANG_CODE/LC_MESSAGES/TRANSLATION_DOMAIN.po

We have also packages like k3b that has its translations in its own k3b-i18n
package, but with a layout quite similar to the ones here:

LANG_CODE/messages/TRANSLATION_DOMAIN.po

Also, there is the layout used with GNOME documentation:

DIRECTORY/help/TRANSLATION_DOMAIN.pot
DIRECTORY/help/LANG_CODE/LANG_CODE.po

Let's test every know layout. For the first one, we create an adept
sourcepackagename to test that layout.

    >>> adept = sourcepackagenameset.new('adept')

Let's attach the .pot file

    >>> adept_pot_entry = translationimportqueue.addOrUpdateEntry(
    ...     'po/adept.pot', b'foo content', True, rosetta_experts,
    ...      distroseries=hoary_distroseries,
    ...      sourcepackagename=adept)

Create the template name and attach this new import to it.

    >>> subset = potemplateset.getSubset(
    ...     distroseries=hoary_distroseries, sourcepackagename=adept)
    >>> adept_pot_entry.potemplate = subset.new(
    ...     'adept', 'adept', 'po/adept.pot', rosetta_experts)
    >>> print(adept_pot_entry.potemplate.title)
    Template "adept" in Ubuntu Hoary package "adept"

And set this entry as already imported.

    >>> adept_pot_entry.setStatus(
    ...     RosettaImportStatus.IMPORTED,
    ...     rosetta_experts)
    >>> flush_database_updates()

Let's attach a .po file now.

    >>> es_entry = translationimportqueue.addOrUpdateEntry(
    ...     'po/es/adept.po', b'foo content', True,
    ...     rosetta_experts, distroseries=hoary_distroseries,
    ...      sourcepackagename=adept)

And we will get the right IPOFile.

    >>> print(es_entry.getGuessedPOFile().title)
    Spanish (es) translation of adept in Ubuntu Hoary package "adept"

Now, we are going to see what happens if we get a .po file for a template
that is not yet imported.

    >>> es_without_potemplate_entry = translationimportqueue.addOrUpdateEntry(
    ...     'po/es/adept-foo.po', b'foo content', True,
    ...     rosetta_experts, distroseries=hoary_distroseries,
    ...      sourcepackagename=adept)

We don't know the IPOFile where it should be imported.

    >>> es_without_potemplate_entry.getGuessedPOFile() is None
    True

Let's move to the second case, to test it, we create a ktorrent
sourcepackagename and test that layout.

    >>> ktorrent = sourcepackagenameset.new('ktorrent')

Let's attach the .pot file

    >>> ktorrent_pot_entry = translationimportqueue.addOrUpdateEntry(
    ...     'po/ktorrent.pot', b'foo content', True, rosetta_experts,
    ...      distroseries=hoary_distroseries,
    ...      sourcepackagename=ktorrent)

Create the template name and attach this new import to it.

    >>> subset = potemplateset.getSubset(
    ...     distroseries=hoary_distroseries, sourcepackagename=ktorrent)
    >>> ktorrent_pot_entry.potemplate = subset.new(
    ...     'ktorrent', 'ktorrent', 'po/ktorrent.pot', rosetta_experts)
    >>> print(ktorrent_pot_entry.potemplate.title)
    Template "ktorrent" in Ubuntu Hoary package "ktorrent"

And set this entry as already imported.

    >>> ktorrent_pot_entry.setStatus(
    ...     RosettaImportStatus.IMPORTED,
    ...     rosetta_experts)
    >>> flush_database_updates()

Let's attach a .po file now.

    >>> es_entry = translationimportqueue.addOrUpdateEntry(
    ...     'translations/es/messages/ktorrent.po', b'foo content', True,
    ...     rosetta_experts, distroseries=hoary_distroseries,
    ...      sourcepackagename=ktorrent)

And we will get the right IPOFile.

    >>> print(es_entry.getGuessedPOFile().title)
    Spanish (es) translation of ktorrent in Ubuntu Hoary package "ktorrent"

Now, we are going to see what happens if we get a .po file for a template
that is not yet imported.

    >>> es_without_potemplate_entry = translationimportqueue.addOrUpdateEntry(
    ...     'translations/es/messages/ktorrent-foo.po', b'foo content', True,
    ...     rosetta_experts, distroseries=hoary_distroseries,
    ...      sourcepackagename=ktorrent)

We don't know the IPOFile where it should be imported.

    >>> es_without_potemplate_entry.getGuessedPOFile() is None
    True

Now, let's move to the third case, to test it, we create a zope
sourcepackagename and test that layout.

    >>> zope = sourcepackagenameset.new('zope')

Let's attach the .pot file

    >>> zope_pot_entry = translationimportqueue.addOrUpdateEntry(
    ...     'debian/zope3/usr/lib/python2.4/site-packages/zope/app/'
    ...     'locales/zope.pot',
    ...     b'foo content', True, rosetta_experts,
    ...     distroseries=hoary_distroseries, sourcepackagename=zope)

Create the template name and attach this new import to it.

    >>> subset = potemplateset.getSubset(
    ...     distroseries=hoary_distroseries, sourcepackagename=zope)
    >>> zope_pot_entry.potemplate = subset.new(
    ...     'zope', 'zope',
    ...     'debian/zope3/usr/lib/python2.4/site-packages/zope/app/'
    ...     'locales/zope.pot',
    ...     rosetta_experts)
    >>> print(zope_pot_entry.potemplate.title)
    Template "zope" in Ubuntu Hoary package "zope"

And set this entry as already imported.

    >>> zope_pot_entry.setStatus(
    ...     RosettaImportStatus.IMPORTED, rosetta_experts)
    >>> flush_database_updates()

Let's attach a .po file now.

    >>> es_entry = translationimportqueue.addOrUpdateEntry(
    ...     'debian/zope3/usr/lib/python2.4/site-packages/zope/app/locales'
    ...     '/es/LC_MESSAGES/zope.po',
    ...     b'foo content', True, rosetta_experts,
    ...     distroseries=hoary_distroseries, sourcepackagename=zope)

And we will get the right IPOFile.

    >>> print(es_entry.getGuessedPOFile().title)
    Spanish (es) translation of zope in Ubuntu Hoary package "zope"

Now, we are going to see what happens if we get a .po file for a template
that is not yet imported.

    >>> es_without_potemplate_entry = translationimportqueue.addOrUpdateEntry(
    ...     'debian/zope3/usr/lib/python2.4/site-packages/zope/app/'
    ...     'locales/es/LC_MESSAGES/zope-test.po',
    ...     b'foo content', True, rosetta_experts,
    ...     distroseries=hoary_distroseries, sourcepackagename=zope)

We don't know the IPOFile where it should be imported.

    >>> es_without_potemplate_entry.getGuessedPOFile() is None
    True

Now, let's move to the fourth case, to test it, we create a k3b
sourcepackagename from where the .pot file comes and a k3b-i18n one
from where the translations come.

    >>> k3b = sourcepackagenameset.new('k3b')
    >>> k3b_i18n = sourcepackagenameset.new('k3b-i18n')

Let's attach the .pot file

    >>> k3b_pot_entry = translationimportqueue.addOrUpdateEntry(
    ...     'po/k3b.pot', b'foo content', True, rosetta_experts,
    ...     distroseries=hoary_distroseries, sourcepackagename=k3b)

Create the template name and attach this new import to it.

    >>> subset = potemplateset.getSubset(
    ...     distroseries=hoary_distroseries, sourcepackagename=k3b)
    >>> k3b_pot_entry.potemplate = subset.new(
    ...     'k3b', 'k3b', 'po/k3b.pot', rosetta_experts)
    >>> print(k3b_pot_entry.potemplate.title)
    Template "k3b" in Ubuntu Hoary package "k3b"

And set this entry as already imported.

    >>> k3b_pot_entry.setStatus(RosettaImportStatus.IMPORTED, rosetta_experts)
    >>> flush_database_updates()

Let's attach a .po file now.

    >>> es_entry = translationimportqueue.addOrUpdateEntry(
    ...     'es/messages/k3b.po', b'foo content', True, rosetta_experts,
    ...     distroseries=hoary_distroseries, sourcepackagename=k3b_i18n)

And we will get the right IPOFile.

    >>> print(es_entry.getGuessedPOFile().title)
    Spanish (es) translation of k3b in Ubuntu Hoary package "k3b"

Now, we are going to see what happens if we get a .po file for a template
that is not yet imported.

    >>> es_without_potemplate_entry = translationimportqueue.addOrUpdateEntry(
    ...     'es/messages/libk3b.po', b'foo content', True, rosetta_experts,
    ...     distroseries=hoary_distroseries, sourcepackagename=k3b_i18n)

We don't know the IPOFile where it should be imported.

    >>> es_without_potemplate_entry.getGuessedPOFile() is None
    True

Finally, let's move to the last case, to test it, we create a gnome-terminal
sourcepackagename that will host the .pot and .po files.

    >>> gnome_terminal = sourcepackagenameset.new('gnome-terminal')

Let's attach the .pot file

    >>> terminal_pot_entry = translationimportqueue.addOrUpdateEntry(
    ...     'drivemount/help/drivemount.pot', b'foo content', True,
    ...     rosetta_experts, distroseries=hoary_distroseries,
    ...     sourcepackagename=gnome_terminal)

Create the template name and attach this new import to it.

    >>> subset = potemplateset.getSubset(
    ...     distroseries=hoary_distroseries,
    ...     sourcepackagename=gnome_terminal)
    >>> terminal_pot_entry.potemplate = subset.new(
    ...     'help', 'help', 'drivemount/help/drivemount.pot', rosetta_experts)
    >>> print(terminal_pot_entry.potemplate.title)
    Template "help" in Ubuntu Hoary package "gnome-terminal"

And set this entry as already imported.

    >>> k3b_pot_entry.setStatus(RosettaImportStatus.IMPORTED, rosetta_experts)
    >>> flush_database_updates()

Let's attach a .po file now.

    >>> es_entry = translationimportqueue.addOrUpdateEntry(
    ...     'drivemount/help/es/es.po', b'foo content', True, rosetta_experts,
    ...     distroseries=hoary_distroseries,
    ...     sourcepackagename=gnome_terminal)

And we will get the right IPOFile.

    >>> print(es_entry.getGuessedPOFile().title)
    Spanish (es) ... of help in Ubuntu Hoary package "gnome-terminal"

Now, we are going to see what happens if we get a .po file for a template
that is not yet imported.

    >>> es_without_potemplate_entry = translationimportqueue.addOrUpdateEntry(
    ...     'wanda/help/es/es.po', b'foo content', True, rosetta_experts,
    ...     distroseries=hoary_distroseries, sourcepackagename=gnome_terminal)

We don't know the IPOFile where it should be imported.

    >>> es_without_potemplate_entry.getGuessedPOFile() is None
    True


Finally, we abort the transaction to undo all changes done.

    >>> transaction.abort()


executeOptimisticBlock
----------------------

This method looks on the queue to find entries to block based on other .pot
entries that are stored on the same directory and are already blocked.

Check the number of entries on the queue. We have the two sample data entries
plus the ones added in this test.

    >>> translationimportqueue.countEntries()
    5

First, let's check the status of the existing entries.

    >>> from operator import attrgetter
    >>> entries = sorted(
    ...     translationimportqueue.getAllEntries(), key=attrgetter('id'))

    >>> entry1 = entries[0]
    >>> print(entry1.path)
    po/evolution-2.2-test.pot
    >>> entry1.status == RosettaImportStatus.IMPORTED
    True

    >>> entry2 = entries[1]
    >>> print(entry2.path)
    po/pt_BR.po
    >>> entry2.status == RosettaImportStatus.IMPORTED
    True

    >>> entry3 = entries[2]
    >>> print(entry3.path)
    po/sr.po
    >>> entry3.status == RosettaImportStatus.NEEDS_REVIEW
    True

    >>> entry4 = entries[3]
    >>> print(entry4.path)
    po/sr.po
    >>> entry4.status == RosettaImportStatus.NEEDS_REVIEW
    True

    >>> entry5 = entries[4]
    >>> print(entry5.path)
    po/evolution-2.2.pot

We need it blocked for this test.

    >>> entry5.setStatus(RosettaImportStatus.BLOCKED, rosetta_experts)
    >>> transaction.commit()

Let's see how many entries are blocked.

    >>> translationimportqueue.executeOptimisticBlock()
    1

Now is time to check that we only have one item on the NeedsReview status.

    >>> print(entry3.path)
    po/sr.po

This entry is for a productseries, and it's not blocked because the blocked
.pot entry is for a distroseries-sourcepackagename.

    >>> entry3.status == RosettaImportStatus.NEEDS_REVIEW
    True

On the other hand, this other one is for the same
distroseries/sourcepackagename than the .pot file we have so it's also
blocked.

    >>> print(entry4.path)
    po/sr.po
    >>> entry4.status == RosettaImportStatus.BLOCKED
    True

And the .pot entry is still blocked.

    >>> print(entry5.path)
    po/evolution-2.2.pot
    >>> entry5.status == RosettaImportStatus.BLOCKED
    True


getElapsedTimeText
-----------------

This method returns a string representing the elapsed time since the entry
was added to the queue.

We need to attach a new entry to play with:

    >>> productseries = ProductSeries.get(1)
    >>> entry = translationimportqueue.addOrUpdateEntry(
    ...     'foo/bar.po', b'foo content', True,
    ...     rosetta_experts, productseries=productseries)

When we just import it, this method tells us that it's "just requested"

    >>> print(entry.getElapsedTimeText())
    just requested

Now, we need to update the 'dateimported' field to check that we get a good
value when takes more time since the import. We need to force the date here
because doing it with sample data would be a time bomb.

To edit this field, we need to have Edit permissions.

    >>> login('carlos@canonical.com')

Let's change the field with a date 2 days, 13 hours and 5 minutes ago.

    >>> import pytz
    >>> import datetime
    >>> UTC = pytz.timezone('UTC')
    >>> delta = datetime.timedelta(days=2, hours=13, minutes=5)
    >>> entry = removeSecurityProxy(entry)
    >>> entry.dateimported = datetime.datetime.now(UTC) - delta

And this method gets the right text.

    >>> print(entry.getElapsedTimeText())
    2 days 13 hours 5 minutes ago


TranslationImportQueue
======================

The translation import queue is the place where the new translation imports
end before being imported into Rosetta.


getTemplatesOnSameDirectory
---------------------------

This method allows us to get the set of .pot files we have on the same
directory that a given entry.

For the third entry, we have one .pot file on that directory, which is already
in sample data.

    >>> entry3.setStatus(RosettaImportStatus.NEEDS_REVIEW, rosetta_experts)
    >>> entries = entry3.getTemplatesOnSameDirectory()
    >>> entries.count()
    1
    >>> entries[0].status == RosettaImportStatus.IMPORTED
    True
    >>> entries[0].id
    1

For the fourth entry, we have one.

    >>> entry4.setStatus(RosettaImportStatus.NEEDS_REVIEW, rosetta_experts)
    >>> entries = entry4.getTemplatesOnSameDirectory()
    >>> entries.count()
    1

Which is blocked.

    >>> entries[0].status == RosettaImportStatus.BLOCKED
    True

And finally, the .pot entry doesn't have other .pot in the same directory and
obviously, we are not returning it as being at the same directory as it makes
no sense at all.

    >>> entry5.setStatus(RosettaImportStatus.NEEDS_REVIEW, rosetta_experts)
    >>> entries = entry5.getTemplatesOnSameDirectory()
    >>> entries.count()
    0


addOrUpdateEntry()
------------------

addOrUpdateEntry adds a new entry to the import queue so we can handle it
later with poimport script.

    >>> from lp.services.tarfile_helpers import LaunchpadWriteTarFile
    >>> potemplate_set = getUtility(IPOTemplateSet)
    >>> potemplate_subset = potemplate_set.getSubset(
    ...     productseries=evolution_productseries)
    >>> evolution_22_test_template = potemplate_subset.getPOTemplateByName(
    ...     'evolution-2.2-test')
    >>> evolution_22_template = potemplate_subset.getPOTemplateByName(
    ...     'evolution-2.2')

We get a sample tarball to be uploaded into the system.

    >>> test_tar_content = {
    ...     'foo.pot': b'Foo template',
    ...     'es.po': b'Spanish translation',
    ...     'fr.po': b'French translation',
    ...     }
    >>> tarfile_content = LaunchpadWriteTarFile.files_to_bytes(
    ...     test_tar_content)
    >>> by_maintainer = True

We will need this helper function to print the queue content.

    >>> def print_queue_entries(translationimportqueue):
    ...     for entry in translationimportqueue:
    ...         if entry.productseries is not None:
    ...             context = entry.productseries.product.name
    ...         else:
    ...             context = '%s %s' % (
    ...                 entry.distroseries.name, entry.sourcepackagename.name)
    ...         template = 'None'
    ...         if entry.potemplate is not None:
    ...             template = entry.potemplate.name
    ...         print('%s | %s | %s' % (context, template, entry.path))

Current entries in the queue are:

    >>> queue = getUtility(ITranslationImportQueue)
    >>> print_queue_entries(queue)
    evolution       | evolution-2.2-test | po/evolution-2.2-test.pot
    evolution       | evolution-2.2-test | po/pt_BR.po
    firefox         | None               | foo/bar.po
    evolution       | None               | po/sr.po
    hoary evolution | None               | po/sr.po
    hoary evolution | None               | po/evolution-2.2.pot

Attach the sample tarball to the 'evolution-2.2-test' template in evolution
product. We can ask to only upload the template from the tarball and ignore
the other files.

    >>> translationimportqueue.addOrUpdateEntriesFromTarball(
    ...     tarfile_content, by_maintainer, rosetta_experts,
    ...     productseries=evolution_productseries,
    ...     potemplate=evolution_22_test_template,
    ...     only_templates=True)
    (1, [])

And this new entry in the queue appears in the list.

    >>> print_queue_entries(queue)
    evolution       | evolution-2.2-test | po/evolution-2.2-test.pot
    evolution       | evolution-2.2-test | po/pt_BR.po
    firefox         | None               | foo/bar.po
    evolution       | None               | po/sr.po
    hoary evolution | None               | po/sr.po
    hoary evolution | None               | po/evolution-2.2.pot
    evolution       | evolution-2.2-test | foo.pot


But we really want all files from the tarball, so we upload them all.
There will be three new entries from the tarball.

    >>> translationimportqueue.addOrUpdateEntriesFromTarball(
    ...     tarfile_content, by_maintainer, rosetta_experts,
    ...     productseries=evolution_productseries,
    ...     potemplate=evolution_22_test_template)
    (3, [])

And those new entries in the queue appear in the list.

    >>> print_queue_entries(queue)
    evolution       | evolution-2.2-test | po/evolution-2.2-test.pot
    evolution       | evolution-2.2-test | po/pt_BR.po
    firefox         | None               | foo/bar.po
    evolution       | None               | po/sr.po
    hoary evolution | None               | po/sr.po
    hoary evolution | None               | po/evolution-2.2.pot
    evolution       | evolution-2.2-test | foo.pot
    evolution       | evolution-2.2-test | es.po
    evolution       | evolution-2.2-test | fr.po

It is possible to update the content of an entry in the queue.

    >>> def getFirstEvoEntryByPath(queue,path):
    ...     for entry in queue.getAllEntries(evolution_productseries):
    ...         if entry.path == path:
    ...             return entry
    ...     return None
    >>> transaction.commit()

    >>> existing_entry = getFirstEvoEntryByPath(queue, 'foo.pot')
    >>> existing_entry = removeSecurityProxy(existing_entry)
    >>> print(existing_entry.content.read().decode('UTF-8'))
    Foo template

    >>> entry = translationimportqueue.addOrUpdateEntry(
    ...     "foo.pot", b"New content", by_maintainer, rosetta_experts,
    ...     productseries=evolution_productseries,
    ...     potemplate=evolution_22_test_template)
    >>> entry = removeSecurityProxy(entry)
    >>> transaction.commit()
    >>> entry is existing_entry
    True
    >>> print(entry.content.read().decode('UTF-8'))
    New content

Not specifying the potemplate in this situation still selects the same entry
on a best match basis. The entry is updated.

    >>> entry = translationimportqueue.addOrUpdateEntry(
    ...     "foo.pot", b"Even newer content", by_maintainer, rosetta_experts,
    ...     productseries=evolution_productseries)
    >>> entry = removeSecurityProxy(entry)
    >>> transaction.commit()
    >>> entry is existing_entry
    True
    >>> print(entry.content.read().decode('UTF-8'))
    Even newer content

Same goes for pofile entries.

    >>> existing_entry = getFirstEvoEntryByPath(queue, 'es.po')
    >>> existing_entry = removeSecurityProxy(existing_entry)
    >>> print(existing_entry.content.read().decode('UTF-8'))
    Spanish translation

    >>> entry = removeSecurityProxy(translationimportqueue.addOrUpdateEntry(
    ...     "es.po", b"New po content", by_maintainer, rosetta_experts,
    ...     productseries=evolution_productseries))
    >>> transaction.commit()
    >>> entry is existing_entry
    True
    >>> print(entry.content.read().decode('UTF-8'))
    New po content

Now, attaching the same layout to a different template for the same product,
we get again three more entries.

    >>> translationimportqueue.addOrUpdateEntriesFromTarball(
    ...     tarfile_content, by_maintainer, rosetta_experts,
    ...     productseries=evolution_productseries,
    ...     potemplate=evolution_22_template)
    (3, [])

And the import queue gets three new entries too. This part of the test is
important to prevent problems like bug #133611, in which case were not getting
the extra three entries.

    >>> print_queue_entries(queue)
    evolution ...
    hoary ...
    ...
    evolution       | evolution-2.2-test | foo.pot
    evolution       | evolution-2.2-test | es.po
    evolution       | evolution-2.2-test | fr.po
    evolution       | evolution-2.2      | es.po
    evolution       | evolution-2.2      | foo.pot
    evolution       | evolution-2.2      | fr.po

Not specifying the potemplate now is ambiguous and so no entry is added or
updated.

    >>> print(queue.addOrUpdateEntry(
    ...     "foo.pot", b"Latest content", by_maintainer, rosetta_experts,
    ...     productseries=evolution_productseries))
    None

Ambiguity is also resolved when a file is uploaded to the product first and
then to a specific template.

    >>> existing_entry = queue.addOrUpdateEntry(
    ...     "bar.pot", b"Bar content", by_maintainer, rosetta_experts,
    ...     productseries=evolution_productseries)
    >>> existing_entry = removeSecurityProxy(existing_entry)
    >>> entry = queue.addOrUpdateEntry(
    ...     "bar.pot", b"Bar content", by_maintainer, rosetta_experts,
    ...     productseries=evolution_productseries,
    ...     potemplate=evolution_22_template)

These files are put into different entries.

    >>> print_queue_entries(queue)
    evolution ...
    hoary ...
    ...
    evolution       | evolution-2.2      | fr.po
    evolution       | None               | bar.pot
    evolution       | evolution-2.2      | bar.pot

When uploading to the prouct now, the best matching entry is updated.

    >>> entry = queue.addOrUpdateEntry(
    ...     "bar.pot", b"New bar content", by_maintainer, rosetta_experts,
    ...     productseries=evolution_productseries)
    >>> entry = removeSecurityProxy(entry)
    >>> transaction.commit()
    >>> entry is existing_entry
    True
    >>> print(entry.content.read().decode('UTF-8'))
    New bar content

Filename filters
================

A tarball doesn't always have everything in quite the right place.  If
you need to manipulate the file paths within a tarball before the files
go into the import queue, there's no need to mess with the tarball.

Instead, a filter callback to addOrUpdateEntryFromTarball lets you play
with the filenames, defining how the import code will pretend they are
named.  It can also tell addOrUpdateEntryFromTarball to ignore a file by
not returning a name for it.

    >>> import os.path
    >>> netapplet = productset['netapplet']
    >>> netapplet_trunk = netapplet.getSeries('trunk')

In this example, we create a filename filter that ignores templates, and
places all other files in a directory "new-directory."

    >>> def swizzle_filename(path):
    ...     if path.endswith('.pot'):
    ...         return None
    ...     return os.path.join('new-directory', path)

The template file is ignored, as per the instructions of the path
filter, so there seem to be only 2 files in the tarball.

    >>> translationimportqueue.addOrUpdateEntriesFromTarball(
    ...     tarfile_content, by_maintainer, rosetta_experts,
    ...     productseries=netapplet_trunk,
    ...     filename_filter=swizzle_filename)
    (2, [])

To all intents and purposes, it's as if the files' paths inside the
tarball were exactly as the filename filter returned them.

    >>> print_queue_entries(queue)
    evolution ...
    hoary evolution | ...
    ...
    evolution       | evolution-2.2      | bar.pot
    netapplet       | None               | new-directory/es.po
    netapplet       | None               | new-directory/fr.po


Invalid data
============

If administrators fail to correct certain errors in requests while approving
them, and the admin user interface mistakenly accepts the approval, we may
end up with an approved but incomplete entry that has no place to go (see
bug 138650 for an example).

If such bad requests do end up on the import queue, the import queue code will
raise errors about them.

    >>> import six

    >>> def print_import_failures(import_script):
    ...     """List failures recorded in an import script instance."""
    ...     for reason, entries in six.iteritems(script.failures):
    ...         print(reason)
    ...         for entry in entries:
    ...             print("-> " + entry)

    >>> clear_queue(translationimportqueue)

    >>> entry = translationimportqueue.addOrUpdateEntry(
    ...     u'po/sr.po', b'foo', True, rosetta_experts,
    ...      productseries=evolution_productseries)

    >>> entry.import_into is None
    True

Set the entry to approved, which is only possible if we don't use setStatus.
    >>> removeSecurityProxy(entry).status = RosettaImportStatus.APPROVED

    >>> import logging
    >>> from lp.services.log.logger import FakeLogger
    >>> from lp.translations.scripts.po_import import TranslationsImport

    >>> script = TranslationsImport('poimport', test_args=[])
    >>> script.logger = FakeLogger()
    >>> script.main()
    DEBUG Starting...
    ERROR Entry is approved but has no place to import to.
    ...
    DEBUG Finished the import process.

    >>> print_import_failures(script)
    Entry is approved but has no place to import to.
    -> 'po/sr.po' (id ...) in Evolution trunk series

The entry is marked as Failed.

    >>> print(entry.status.name)
    FAILED

This happens for distribution packages as well as products.

    >>> clear_queue(translationimportqueue)

    >>> entry = translationimportqueue.addOrUpdateEntry(
    ...     u'po/th.po', b'bar', False, rosetta_experts,
    ...     distroseries=hoary_distroseries,
    ...     sourcepackagename=evolution_sourcepackagename)

    >>> entry.import_into is None
    True

Set the entry to approved, which is only possible if we don't use setStatus.
    >>> removeSecurityProxy(entry).status = RosettaImportStatus.APPROVED

    >>> script = TranslationsImport('poimport', test_args=[])
    >>> script.logger.setLevel(logging.FATAL)
    >>> script.main()
    >>> print_import_failures(script)
    Entry is approved but has no place to import to.
    -> 'po/th.po' (id ...) in ubuntu Hoary package evolution

    >>> print(entry.status.name)
    FAILED

    >>> clear_queue(translationimportqueue)


cleanUpQueue
------------

The queue is cleaned up regularly.

Here we start out with an empty queue.

    >>> for entry in translationimportqueue:
    ...     translationimportqueue.remove(entry)
    >>> print_queue_entries(translationimportqueue)

cleanUpQueue() returns the number of entries it purges.  If there is
nothing to purge, it returns zero.

    >>> translationimportqueue.cleanUpQueue()
    0


State and Age
.............

Entries can be cleaned up because they have been in a specific state for
at least a specified period of time.

For instance, successfully imported entries are cleaned up after a few
days.

    >>> entry = translationimportqueue.addOrUpdateEntry(
    ...     u'po/nl.po', b'hoi', True, rosetta_experts,
    ...      productseries=evolution_productseries)
    >>> entry.pofile = factory.makePOFile('nl')
    >>> entry.setStatus(RosettaImportStatus.IMPORTED, rosetta_experts)
    >>> print_queue_entries(translationimportqueue)
    evolution   | None        | po/nl.po

Such requests are deleted after a few days.

    >>> delta = datetime.timedelta(days=4)
    >>> entry.date_status_changed = datetime.datetime.now(UTC) - delta
    >>> flush_database_updates()
    >>> translationimportqueue.cleanUpQueue()
    1

    >>> print_queue_entries(translationimportqueue)


Deactivated Products
....................

Another reason for deleting entries is that they belong to products that
have been deactivated.

A user sets up Jokosher for translation, and uploads a template.

    >>> from lp.app.enums import ServiceUsage

    >>> def create_product_request(product_name, template_name):
    ...     """Enqueue an import request for given product and template."""
    ...     product = productset[product_name]
    ...     series = product.primary_translatable
    ...     assert series is not None, (
    ...         "Product %s has no translatable series." % product_name)
    ...     template = series.getPOTemplate(template_name)
    ...     # In another completely arbitrary move, we make all import
    ...     # requests for products non-imported.
    ...     return translationimportqueue.addOrUpdateEntry('messages.pot',
    ...         b'dummy file', False, rosetta_experts, productseries=series,
    ...         potemplate=template)

    >>> jokosher = productset['jokosher']
    >>> jokosher_trunk = jokosher.getSeries('trunk')
    >>> jokosher.translations_usage = ServiceUsage.LAUNCHPAD
    >>> jokosher_subset = potemplateset.getSubset(
    ...     productseries=jokosher_trunk)
    >>> template = jokosher_subset.new(
    ...     'jokosher', 'jokosher', 'jokosher.pot', rosetta_experts)
    >>> entry = create_product_request('jokosher', 'jokosher')
    >>> print_queue_entries(translationimportqueue)
    jokosher    | jokosher    | messages.pot

The entry sits on the queue; there is no reason for anyone to purge it.

    >>> translationimportqueue.cleanUpQueue()
    0
    >>> print_queue_entries(translationimportqueue)
    jokosher    | jokosher    | messages.pot

An administrator finds that this registration of the Jokosher project
does not satisfy Launchpad policy, and disables it.

    >>> jokosher.active = False

The request is now eligible for purging.  Since the Jokosher product is
no longer usable, there is no point in keeping the entry on the queue.

    >>> translationimportqueue.cleanUpQueue()
    1
    >>> print_queue_entries(translationimportqueue)

