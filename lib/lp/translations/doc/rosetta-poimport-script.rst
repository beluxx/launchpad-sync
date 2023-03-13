PO import script
================

    >>> from lp.translations.model.potemplate import POTemplate
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.translations.enums import RosettaImportStatus
    >>> from lp.translations.interfaces.translationimportqueue import (
    ...     ITranslationImportQueue,
    ... )
    >>> from lp.services.config import config
    >>> from datetime import datetime, timezone
    >>> rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts

Login as an admin to be able to do changes to the import queue.

    >>> login("carlos@canonical.com")

    >>> translation_import_queue = getUtility(ITranslationImportQueue)
    >>> import transaction

We don't care about a POTemplate we are working with, so just pick any.

    >>> potemplate = POTemplate.get(1)

Provide a POFile with Last-Translator set to a user not existing in
the sampledata.

    >>> print(getUtility(IPersonSet).getByEmail("danilo@canonical.com"))
    None

    >>> pofile = potemplate.newPOFile("sr")
    >>> pofile_content = (
    ...     """
    ... msgid ""
    ... msgstr ""
    ... "PO-Revision-Date: 2005-06-04 20:41+0100\\n"
    ... "Last-Translator: Danilo \u0160egan <danilo@canonical.com>\\n"
    ... "Content-Type: text/plain; charset=UTF-8\\n"
    ... "X-Rosetta-Export-Date: %s\\n"
    ...
    ... msgid "Foo %%s"
    ... msgstr "Bar"
    ... """
    ...     % datetime.now(timezone.utc).isoformat()
    ... ).encode()

We clean the import queue.

    >>> for entry in translation_import_queue:
    ...     translation_import_queue.remove(entry)
    ...
    >>> translation_import_queue.countEntries()
    0

Product must have privileges which allow suggestions from those
without special privileges, like "cprov": structured privileges are
enough (but we could go with "open" as well, which would allow not
only suggestions but full translations as well).

    >>> from lp.translations.enums import TranslationPermission
    >>> product = pofile.potemplate.productseries.product
    >>> product.translationpermission = TranslationPermission.STRUCTURED

We add a PO file to the import queue, approving it along the way.

    >>> cprov = getUtility(IPersonSet).getByName("cprov")
    >>> entry = translation_import_queue.addOrUpdateEntry(
    ...     pofile.path,
    ...     pofile_content,
    ...     False,
    ...     cprov,
    ...     sourcepackagename=pofile.potemplate.sourcepackagename,
    ...     distroseries=pofile.potemplate.distroseries,
    ...     productseries=pofile.potemplate.productseries,
    ... )
    >>> entry.pofile = pofile
    >>> entry.setStatus(RosettaImportStatus.APPROVED, rosetta_experts)
    >>> transaction.commit()
    >>> translation_import_queue.countEntries()
    1

Now we run the import script, making sure that the DB user it runs under
has enough privileges for the script to run to completion.

    >>> import os
    >>> import subprocess
    >>> script = os.path.join(
    ...     config.root, "cronscripts", "rosetta-poimport.py"
    ... )
    >>> process = subprocess.Popen(
    ...     [script],
    ...     stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE,
    ...     universal_newlines=True,
    ... )
    >>> stdout, stderr = process.communicate()
    >>> process.returncode
    0
    >>> print(stderr)
    INFO    Creating lockfile: /var/lock/launchpad-rosetta-poimport.lock
    INFO    Importing: Serbian (sr) ... of evolution-2.2 in Evolution trunk
    INFO    Import requests completed.
    <BLANKLINE>
    >>> transaction.commit()

A new Account for 'danilo@canonical.com' is created.

    >>> danilo = getUtility(IPersonSet).getByEmail(
    ...     "danilo@canonical.com", filter_status=False
    ... )
    >>> print(danilo.displayname)
    Danilo Šegan
